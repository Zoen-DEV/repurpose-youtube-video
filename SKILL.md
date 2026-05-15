---
name: repurpose-youtube-video
description: >
  AI social media manager that transforms a YouTube video into ready-to-publish LinkedIn and Instagram posts, each with an AI-generated platform-optimized visual. ALWAYS trigger this skill when the user's message starts with "Crear post para Instagram y LinkedIn:" followed by a "youtube-link:" line containing a YouTube URL. This is the exact command format for this skill -- trigger on it unconditionally, even if no other context is provided.
---

# Repurpose YouTube Video -> LinkedIn + Instagram

## REGLA OBLIGATORIA

> **NUNCA publiques sin aprobación explícita del usuario.**
> Antes de cualquier acción de publicación (inmediata o programada), muestra el contenido final completo y espera confirmación:
>
> ```
> ¿Apruebas este contenido? (sí/editar/cancelar)
> ```
>
> - **sí** → procede a publicar
> - **editar** → pide qué cambiar, aplica los cambios y vuelve a mostrar el contenido para aprobación
> - **cancelar** → detente y confirma al usuario que no se publicó nada
>
> Esta regla aplica siempre, sin excepciones, incluso si el usuario ya aprobó los textos en pasos anteriores.

## Command format

```
Crear post para Instagram y LinkedIn:

youtube-link: https://www.youtube.com/example
images: /ruta/imagen1.jpg, /ruta/imagen2.jpg     (optional — skips AI visual generation)
formato-instagram: carrusel                       (optional — default: imagen-unica)
publicar: ahora | YYYY-MM-DDTHH:MM:SSZ           (optional — default: ahora)
```

Parse each field from the message. `youtube-link` is required. All others are optional.
If `images:` is provided, parse the comma-separated list of file paths or URLs — these will be used instead of AI-generated visuals.
If the format is present but the YouTube URL is missing or malformed, tell the user and stop.

You are an expert AI social media manager. Given that URL, you will:
1. Extract the video's content via Blotato
2. Ask quality questions to tailor the posts
3. Write optimized posts for LinkedIn and Instagram
4. Source or generate a platform-appropriate visual for each
5. Publish (or schedule) both posts

## Setup

The helper script is at:
`C:\Users\User\.claude\skills\repurpose-youtube-video\scripts\blotato_client.py`

Load it in all Python commands with:
```python
import sys
sys.path.insert(0, r'C:\Users\User\.claude\skills\repurpose-youtube-video\scripts')
import blotato_client as bc
```

Read credentials via `bc.load_config()`. If the key is missing it prints a warning and exits -- relay that message to the user and stop.

## Workflow

Print a short status line before each step ("[...] Extracting video...", etc.) so the user can follow along.

---

### Step 1 — Extract video content

Use `bc.extract_youtube_local()` — does not require the Blotato API key.

```python
cfg = bc.load_config()
clean_url = re.sub(r'[&?]t=\d+s?', '', url)
content = bc.extract_youtube_local(clean_url)
```

This uses **yt-dlp** for metadata and **youtube-transcript-api** for the transcript.
No API key needed. Both packages must be installed (`python -m pip install yt-dlp youtube-transcript-api`).

If `extract_youtube_local` raises an exception:
1. Try stripping to the bare `?v=` URL and call it again.
2. If still failing, tell the user:
   ```
   [WARNING] No se pudo extraer el transcript del video (puede que no tenga subtítulos o el video es privado).
             Continuaré con la información disponible del título.
   ```
   Then fetch the video title from the YouTube page with WebFetch and proceed using that alone.

From the result use: `title`, `description`, `transcript`, `tags`, `chapters`.
`summary` and `keyPoints` will be empty strings — **you** (Claude) should derive them from the transcript.

---

### Step 2 — Get account IDs

Read IDs from `cfg`:
- `cfg["linkedin_account_id"]` and `cfg["instagram_account_id"]`

**If both are set:** use them directly and proceed.

**If either is missing or blank:** call `bc.get_accounts(platform, api_key=cfg["api_key"])`.

If only one account exists for a platform, use it automatically and note it to the user.

If multiple accounts exist, print the list and stop:
```
Multiple LinkedIn accounts found. Add one of these IDs to your .env:

  BLOTATO_LINKEDIN_ACCOUNT_ID=<id>   (Full Name 1)
  BLOTATO_LINKEDIN_ACCOUNT_ID=<id>   (Full Name 2)

Then run the command again.
```

If a platform has no connected account at all, warn and skip it:
`[WARNING] No hay cuenta de LinkedIn conectada — omitiendo LinkedIn`

---

### Step 3 — Quality questions (ask before writing)

Ask the user these two questions **in a single message** before writing any posts:

```
Antes de escribir los posts, necesito dos datos:

1. ¿Cuál es el tono para LinkedIn?
   a) Inspiracional / motivacional
   b) Educativo / insights del sector
   c) Personal / storytelling

2. ¿Cuál es el objetivo principal de estos posts?
   a) Awareness (alcance y visibilidad)
   b) Engagement (comentarios y conversación)
   c) Tráfico (llevar gente al video)
```

Wait for the user's answer. Use `(a)` as default if the user doesn't specify.

---

### Step 4 — Write the posts

Write posts using the extracted content AND the user's chosen tone/goal. Do NOT call an external LLM — write the posts yourself.

**LinkedIn post** — professional, insightful, value-driven:
- 150–300 words
- Strong hook in the first line (never start with "En este video..." or "In this video...")
- 3–5 key insights or takeaways with → or bullet formatting
- Conversational but authoritative tone (adjust to chosen style from Step 3)
- 3–5 relevant hashtags at the end
- End with a question to spark engagement

**Instagram post** — visual, punchy, engaging:
- 80–150 words
- Bold opening hook (1 sentence)
- Bullet points or short sentences for scannability
- 3–6 emojis woven in naturally (not stacked at the end)
- Clear call-to-action ("Link en bio", "Guarda esto", "Etiqueta a alguien")
- **Maximum 5 hashtags** (Instagram hard limit — Blotato rejects more)

Show both posts to the user and ask:
```
¿Te gustaría editar alguno de estos posts antes de continuar? (sí/no)
Si sí, indícame qué cambiar.
```

If yes, apply their edits and show the updated version. Ask again until they confirm.

> Note: this is a preliminary review of the text only. There will be a final approval step (Step 6) that covers posts + visuals together before anything is published.

---

### Step 5 — Source visuals

**If the user provided `images:` in the command:**
- Parse the comma-separated list of paths/URLs.
- For Instagram with `formato-instagram: carrusel`, use all of them as the carousel.
- For Instagram without carousel flag, use only the first image.
- For LinkedIn, use only the first image.
- Skip AI visual generation entirely.
- Print: `[✓] Usando imágenes proporcionadas por el usuario.`

**If no images were provided:**

Ask the user before generating:
```
¿Qué formato prefieres para el visual de Instagram?
  a) Imagen única (más rápido)
  b) Carrusel de imágenes (más engagement)
```

Then generate visuals in parallel for both platforms.

First, get available templates:
```python
templates = bc.get_templates(api_key=cfg["api_key"])
```

Choose templates:
- **LinkedIn**: `9f4e66cd-b784-4c02-b2ce-e6d0765fd4c0` (Single Centered Text Quote) — clean, professional
- **Instagram single**: `8fa8545e-8955-4a89-a868-cf45023d6cc5` (Futuristic Flyer) — bold, visual
- **Instagram carousel**: `53cfec04-2500-41cf-8cc1-ba670d2c341a` (Instagram Carousel Slideshow)

Create each visual:
```python
result = bc.create_visual(template_id, prompt, title, api_key=cfg["api_key"])
# result["imageUrls"] is a list; result["mediaUrl"] may also be set
urls = result.get("imageUrls") or ([result["mediaUrl"]] if result.get("mediaUrl") else [])
```

For carousel: pass all `imageUrls` from the result as `media_urls`.
For single: pass only the first URL.

If visual generation fails, continue without it:
`[WARNING] No se pudo generar el visual — se publicará solo texto.`

---

### Step 6 — Aprobación final (OBLIGATORIO antes de publicar)

Show the complete final content in a single message — posts and visuals together:

```
─────────────────────────────────────────
CONTENIDO LISTO PARA PUBLICAR
─────────────────────────────────────────

[LinkedIn] — <Nombre de cuenta>
<texto completo del post>
Visual: <url de la imagen o "ninguno">
Timing: ahora | programado para <fecha>

─────────────────────────────────────────

[Instagram] — @<username>
<texto completo del post>
Visual: <url(s) de la(s) imagen(es) o "ninguno">
Formato: imagen única | carrusel (<N> imágenes)
Timing: ahora | programado para <fecha>

─────────────────────────────────────────

¿Apruebas este contenido? (sí/editar/cancelar)
```

**Wait for the user's response before doing anything else.**

- **sí** → proceed to Step 7 (Publish)
- **editar** → ask what to change, apply edits, show this approval block again from the top
- **cancelar** → print `[Cancelado] No se publicó nada.` and stop

Do not proceed to publishing under any other circumstance.

---

### Step 7 — Publish

**If the user provided `publicar: YYYY-MM-DDTHH:MM:SSZ`**, use that as `schedule_time`. Otherwise publish immediately.

If `publicar:` key is absent, ask:
```
¿Cuándo quieres publicar?
  a) Ahora
  b) Programar para más tarde (responde con: YYYY-MM-DDTHH:MM:SSZ)
```

Publish LinkedIn:
```python
resp = bc.publish_post(
    cfg["linkedin_account_id"], "linkedin",
    linkedin_text, linkedin_media_urls,
    api_key=cfg["api_key"],
    schedule_time=schedule_time,  # None if publishing now
)
li_status = bc.poll_post_status(resp["postSubmissionId"], api_key=cfg["api_key"])
```

Publish Instagram:
```python
resp = bc.publish_post(
    cfg["instagram_account_id"], "instagram",
    instagram_text, instagram_media_urls,
    api_key=cfg["api_key"],
    schedule_time=schedule_time,
    share_to_feed=True,
)
ig_status = bc.poll_post_status(resp["postSubmissionId"], api_key=cfg["api_key"])
```

---

### Step 8 — Summary

```
[DONE] Publicado exitosamente:

[LinkedIn]
   Post: "<primeros 80 caracteres>"...
   Visual: <url o "ninguno">
   Status: published | scheduled for <time>
   URL: <publicUrl>

[Instagram]
   Post: "<primeros 80 caracteres>"...
   Visual: <url o "ninguno">
   Formato: imagen única | carrusel (<N> imágenes)
   Status: published | scheduled for <time>
   URL: <publicUrl>
```

---

## Error handling

| Code | Action |
|------|--------|
| 401 | API key inválida — pide al usuario que revise `.env` |
| 422 | Error de validación — muestra el mensaje de Blotato (ej: demasiados hashtags) |
| 429 | Rate limit — espera 10s y reintenta una vez (manejado en `_request`) |
| No accounts | Avisa y omite esa plataforma |
| Visual timeout | Continúa sin visual, publica solo texto |

## Helper script

All API calls go through `bc` functions. See:
[scripts/blotato_client.py](scripts/blotato_client.py)

The script auto-loads credentials from `.env` in the working directory.
Never hardcode or print API keys.
