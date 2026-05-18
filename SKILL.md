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
tono: inspiracional | educativo | personal        (optional — applies to BOTH platforms)
tono-linkedin: inspiracional | educativo | personal     (optional — overrides `tono:` for LinkedIn only)
tono-instagram: inspiracional | educativo | personal    (optional — overrides `tono:` for Instagram only)
objetivo: awareness | engagement | trafico        (optional — applies to BOTH platforms)
objetivo-linkedin: awareness | engagement | trafico     (optional — overrides `objetivo:` for LinkedIn only)
objetivo-instagram: awareness | engagement | trafico    (optional — overrides `objetivo:` for Instagram only)
idioma: es | en | auto                            (optional — default: auto, detected from transcript)
solo: linkedin | instagram                        (optional — publish to only one platform)
dry-run: si                                       (optional — generate everything but DO NOT publish)
publicar: ahora | mañana 9am | viernes 18h | YYYY-MM-DDTHH:MM:SSZ  (optional — default: ahora)
```

Parse each field from the message. `youtube-link` is required. All others are optional.

**Parsing rules:**
- `images:` → comma-separated list of file paths or URLs; used in place of AI-generated visuals.
- `formato-instagram:` → `imagen-unica` (default) or `carrusel`.
- `tono:` / `objetivo:` → **global defaults** applied to both platforms unless overridden by their per-platform variant.
- `tono-linkedin:` / `tono-instagram:` / `objetivo-linkedin:` / `objetivo-instagram:` → **per-platform overrides**. They always win over the global `tono:` / `objetivo:`.
- Resolved values per platform (used by Steps 3 + 4):
  - `tono_linkedin   = tono-linkedin   ?? tono   ?? <ask>`
  - `tono_instagram  = tono-instagram  ?? tono   ?? <ask>`
  - `objetivo_linkedin   = objetivo-linkedin   ?? objetivo   ?? <ask>`
  - `objetivo_instagram  = objetivo-instagram  ?? objetivo   ?? <ask>`
  - If, after applying overrides, a value is missing for any platform that will actually publish (respecting `solo:`), **ask only the missing slot(s)** in Step 3.
- `idioma:` → `auto` (default) means detect from the transcript in Step 1; `es` or `en` forces that language.
- `solo:` → if present, run the full flow only for the specified platform; skip the other entirely (no posts, no visuals, no publishing).
- `dry-run: si` → run all the steps up to and including Step 6 (final approval), but **never call `bc.publish_post`**. Instead, print the final summary as "[aviso] dry-run activado — no se publicó nada".
- `publicar:` → accepts `ahora`, an ISO-8601 timestamp, or **natural language in Spanish** ("mañana a las 9", "viernes 18h", "el 3 de junio a las 10am", etc.). If natural, interpret it relative to today's date and convert to ISO-8601 UTC before passing it to `bc.publish_post`. Confirm the resolved date with the user in the Step 6 approval block.

If the format is present but the YouTube URL is missing or malformed, tell the user and stop.

You are an expert AI social media manager. Given that URL, you will:
1. Extract the video's content (yt-dlp + youtube-transcript-api) and detect language
2. Ask quality questions to tailor the posts (only if `tono:` / `objetivo:` not in command)
3. Write optimized posts for LinkedIn and Instagram in the detected/forced language
4. Humanize the posts (remove AI tells, preserve fidelity)
5. Generate a platform-appropriate visual for each with Freepik Mystic
6. Final approval (covers posts + visuals + edits), then publish (or schedule) both posts

## Setup

The helper scripts are at:
- `C:\Users\User\.claude\skills\repurpose-youtube-video\scripts\blotato_client.py` — publishing + video extraction + media upload
- `C:\Users\User\.claude\skills\repurpose-youtube-video\scripts\freepik_client.py` — image generation (Mystic)
- `C:\Users\User\.claude\skills\repurpose-youtube-video\scripts\image_overlay.py` — text overlay (Pillow) used for Instagram visuals

Load them in all Python commands with:
```python
import sys
sys.path.insert(0, r'C:\Users\User\.claude\skills\repurpose-youtube-video\scripts')
import blotato_client as bc
import freepik_client as fp
import image_overlay as ov
```

Read credentials via `bc.load_config()`. Returns: `api_key` (Blotato), `linkedin_account_id`, `instagram_account_id`, `freepik_api_key`.

- If `BLOTATO_API_KEY` is missing, `load_config()` exits with a warning — relay it and stop.
- If `FREEPIK_API_KEY` is missing (empty string) AND the user did NOT pass `images:` in the command, warn and skip visual generation — publish text-only.
- `image_overlay` requires **Pillow** (`python -m pip install Pillow`). If the import fails, catch it, warn, and fall back to publishing the Mystic image with no overlay.

## Workflow

Print a short status line before each step (e.g. `[...] Extrayendo video...`) so the user can follow along.

**Use this standardized set of status-line tags in every user-facing print:**

| Tag | Meaning | Example |
|---|---|---|
| `[...]` | Paso en curso | `[...] Generando visual para LinkedIn...` |
| `[ok]` | Paso completado / éxito menor | `[ok] Idioma detectado: es` |
| `[aviso]` | Warning recuperable (sigue el flujo) | `[aviso] FREEPIK_API_KEY ausente — se publicará solo texto.` |
| `[error]` | Fallo (puede detener el flujo o no) | `[error] La fecha programada es en el pasado.` |
| `[cancelado]` | El usuario abortó en Step 6 | `[cancelado] No se publicó nada.` |
| `[listo]` | Resumen final del Step 8 | `[listo] Publicado exitosamente:` |

No mezcles checkmarks (`✓`, `✗`), mayúsculas (`WARNING`, `DONE`) ni otros estilos.

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
   [aviso] No se pudo extraer el transcript del video (puede que no tenga subtítulos o el video es privado).
           Continuaré con la información disponible del título.
   ```
   Then fetch the video title from the YouTube page with WebFetch and proceed using that alone.

From the result use: `title`, `description`, `transcript`, `tags`, `chapters`, `channel`.
`summary` and `keyPoints` will be empty strings — **you** (Claude) should derive them from the transcript.

**Detect content language** (used by Steps 4 and 5):

- If the user passed `idioma: es` or `idioma: en` in the command → use that.
- If `idioma: auto` or absent → look at `transcript` (or fall back to `title` + `description` if transcript is empty) and pick `es` or `en` based on which dominates. Both Spanish and English are supported as output languages; for any other source language, default to `es` and tell the user:
  ```
  [aviso] El video parece estar en <idioma> — escribiré los posts en español. Si prefieres otro idioma, vuelve a lanzar el comando con `idioma: en` o `idioma: es`.
  ```

Save the result as `lang` (`"es"` or `"en"`). Print:
```
[ok] Idioma detectado: <es|en>
```

---

### Step 2 — Get account IDs

If the user passed `solo: linkedin` or `solo: instagram`, only resolve the account for that platform and skip the other from this step onwards.

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
`[aviso] No hay cuenta de LinkedIn conectada — omitiendo LinkedIn`

---

### Step 3 — Quality questions (ask before writing)

Tone and objective are resolved **per platform** using the precedence defined in the Parsing rules. After applying overrides:

- If both platforms have a resolved tone AND a resolved objective, **skip this step entirely** and move on to Step 4.
- If one or more slots are still missing (and the affected platform is not excluded by `solo:`), ask **only the missing slots** in a single message.

Use this question template, including only the rows that are missing (collapse the rest):

```
Antes de escribir los posts necesito definir el estilo de cada red.
Cada red puede tener tono y objetivo distintos — puedes elegir lo mismo para las dos si prefieres.

LINKEDIN
1. Tono:
   a) Inspiracional / motivacional
   b) Educativo / insights del sector
   c) Personal / storytelling

2. Objetivo:
   a) Awareness (alcance y visibilidad)
   b) Engagement (comentarios y conversación)
   c) Tráfico (llevar gente al video)

INSTAGRAM
3. Tono:
   a) Inspiracional / motivacional
   b) Educativo / insights del sector
   c) Personal / storytelling

4. Objetivo:
   a) Awareness (alcance y visibilidad)
   b) Engagement (comentarios y conversación)
   c) Tráfico (llevar gente al video)

Responde con el formato `1.b 2.b 3.a 4.b`, o describe lo que prefieres en lenguaje natural
(por ejemplo: "LinkedIn educativo/engagement, Instagram inspiracional/awareness").
```

**Rules when asking:**
- If `solo: linkedin` was set, omit the INSTAGRAM section (and vice versa).
- If only one slot is missing (e.g. only LinkedIn tono is unresolved), show **only that row** — don't ask things you already know.
- If the user is vague or doesn't answer, default each missing slot to **(a)**.

> Each platform adapts its resolved tone to the platform's voice — LinkedIn skews conversacional-autoritativo, Instagram skews directo y visual — but the underlying register comes from each platform's own resolved value, not a shared one.

---

### Step 4 — Write the posts

Write posts using the extracted content AND each platform's resolved tone/goal (Step 3). Do NOT call an external LLM — write the posts yourself. Write in the language stored in `lang` (`es` or `en`) from Step 1.

Use `tono_linkedin` + `objetivo_linkedin` to drive the LinkedIn post, and `tono_instagram` + `objetivo_instagram` to drive the Instagram post. Each platform can end up with a different combination.

**LinkedIn post** — professional, insightful, value-driven:
- 150–300 words
- Strong hook in the first line (never start with "En este video..." / "In this video...")
- 3–5 key insights or takeaways with → or bullet formatting
- Conversational but authoritative tone, adapted to `tono_linkedin` + `objetivo_linkedin`
- **Always include the original YouTube URL** (the cleaned `clean_url` from Step 1, without `&t=...` timestamps) on its own line. Place it just before the hashtags, prefixed with a short CTA: `▶ Mira el video completo aquí: <url>` (ES) or `▶ Watch the full video here: <url>` (EN). LinkedIn auto-unfurls YouTube links; do not wrap them in markdown.
- 3–5 relevant hashtags at the end
- End with a question to spark engagement (the question goes **after** the URL line, before or among the hashtags — whichever reads more naturally)

**Instagram post** — visual, punchy, engaging:
- 80–150 words
- Bold opening hook (1 sentence)
- Bullet points or short sentences for scannability
- 3–6 emojis woven in naturally (not stacked at the end)
- Tone + intent driven by `tono_instagram` + `objetivo_instagram`
- Clear call-to-action ("Link en bio", "Guarda esto", "Etiqueta a alguien"). **Do not paste the raw YouTube URL** in the caption — Instagram does not make links clickable in captions, so it adds noise. Refer to "link en bio" / "link in bio" instead.
- **Maximum 5 hashtags** (Instagram hard limit — Blotato rejects more)

**Faithful citations — strict rule:**

If a post includes a verbatim quote, a number, a percentage, a name, or a specific claim, that exact element MUST appear in `transcript` (or, if transcript is empty, in `title` + `description`). Before writing each post, build a mental list of the facts you intend to use; for each, verify the source text contains it literally (numbers as digits, names spelled the same). If you can't find it, either rephrase as a non-specific insight or drop the claim. **Never invent figures, attributions, or quotes** — paraphrasing is fine, fabricating is not.

**Smart hashtags from video metadata:**

Build the hashtag pool primarily from the video's own `tags` and `chapters` (returned by Step 1), not from generic invention:

1. Start with `tags` — pick 2-3 that fit the platform's audience (filter out anything too generic like `#video` or too long like `#bestvideosof2025`).
2. Add 1-2 hashtags derived from `chapters` titles (camelCase or PascalCase the relevant nouns).
3. Only if the pool is still under the minimum (3 for LinkedIn, 3 for Instagram), invent 1-2 extra hashtags from the post's core topic — keep them concrete, not aspirational ("#productivityTips" over "#successMindset").
4. Cap at the platform limit: LinkedIn 3-5, Instagram **max 5**.

If `tags` and `chapters` are both empty, fall back entirely to invented hashtags — but keep them topic-specific.

**Do not show the posts yet** — they go through Step 4.5 (humanization) first.

---

### Step 4.5 — Humanizar los textos (sutil, preservando fidelidad)

Antes de pasar a la generación de visuales, **revisa los posts tú mismo y elimina las marcas típicas de texto generado por IA**. El objetivo es que parezcan escritos por una persona, **sin reescribirlos** ni añadir información que no esté en el video. Mantén la calidad y la fidelidad a la transcripción — solo pules lo robótico.

**No muestres los posts al usuario en este paso ni pidas aprobación todavía.** La única aprobación es la del Step 6, que cubre posts + visuales + timing en un solo bloque. Aquí solo aplicas los cambios en silencio.

**Aplica este chequeo a cada post (LinkedIn e Instagram):**

1. **Elimina muletillas y conectores de IA.** Borra o sustituye expresiones como:
   - **ES:** "En conclusión", "En resumen", "En definitiva", "En este sentido", "Es importante destacar/mencionar/señalar que…", "Cabe destacar/mencionar/recordar", "No obstante" → "pero" / "aunque", "Asimismo", "Por consiguiente", "En última instancia", "Sin lugar a dudas", "Definitivamente". Aperturas tipo "En el mundo actual…", "Hoy en día…", "Vivimos en una era…".
   - **EN:** "In conclusion", "It's important to note that…", "Furthermore", "Moreover", "That said,", "Needless to say", "At the end of the day", "In today's fast-paced world…", "In the ever-evolving landscape of…".

2. **Quita el vocabulario inflado de IA.** Sustituye o elimina:
   - **ES:** "revolucionario", "transformador", "disruptivo", "imprescindible", "fundamental" (cuando no aporta), "esencialmente", "fundamentalmente", "particularmente", "navegar por", "desbloquear el potencial", "potenciar", "delve into" / "profundizar en" (cuando es genérico).
   - **EN:** "game-changer", "leverage", "unlock", "harness", "elevate", "delve into", "navigate", "robust", "seamless", "cutting-edge", "synergy", "empower", "supercharge", "skyrocket".

3. **Varía la longitud de las frases.** Si detectas 3+ frases seguidas de longitud similar, corta una o alarga otra. Mezcla cortas (3-6 palabras) con medias y alguna larga.

4. **Rompe paralelismos perfectos en las bullets.** Si todas las viñetas empiezan con el mismo verbo conjugado o tienen la misma estructura sintáctica, reescribe 1-2 con otra construcción (sustantivo inicial, pregunta, frase nominal, etc.). No todas deben ser perfectamente simétricas.

5. **Modera los em-dashes (`—`).** El uso intensivo de em-dashes es hoy una marca clara de texto IA. Límite: **máximo 1 em-dash por post**, idealmente cero. Sustituye por comas, dos puntos, paréntesis, o simplemente parte la frase en dos. Esto aplica tanto al em-dash propiamente (`—`) como al en-dash usado como sustituto (`–`).

6. **Vigila los emojis decorativos típicos de IA.** Estos son aceptables si encajan con el contenido específico, pero **prohibidos como decoración genérica**: 🚀 🎯 💡 🌟 ✨ 🔥 💪 🌱 (cuando aparecen como adorno y no aportan significado al texto). **Nunca apiles emojis al inicio** (`💡✨🚀 …`) — es el sello más obvio de copy IA. Si un emoji puede sustituirse por otro más concreto al tema del video (p.ej. 🎬 para cine, 📊 para datos, 🏋️ para fitness), prefiere ese.

7. **Evita las contracciones forzadas y coloquialismos artificiales.** No metas "pa'", "tas", "to'" ni similares — suenan a IA imitando un registro casual. Mejor un español/inglés natural, con frases incompletas ocasionales y guiones aclaratorios moderados.

8. **Verifica el hook (primera línea).** No debe sonar a apertura de IA. Prohibido empezar con:
   - **ES:** "En este video / post / artículo…", "Descubre cómo…", "¿Alguna vez te has preguntado…?", "Imagina que…", "¿Sabías que…?", "Hoy te voy a contar…".
   - **EN:** "In this video / post / article…", "Discover how…", "Have you ever wondered…?", "Imagine if…", "Did you know that…?".

   Si el hook actual encaja con alguno de esos patrones, reescríbelo a algo concreto y específico al contenido del video (un dato, una afirmación contraintuitiva, una pregunta no genérica).

9. **No inventes ni añadas info que no esté en la transcripción.** La humanización es cosmética/estilística — el contenido, datos, cifras y afirmaciones se quedan tal cual están en el video. Si pasas por aquí y detectas un dato que **no** está en `transcript`, bórralo o suavízalo a una afirmación general.

Aplica todos los cambios en silencio y deja los posts listos en memoria. **Continúa directamente al Step 5** (visuales). El ciclo de revisión/edición con el usuario ocurre en el Step 6.

---

### Step 5 — Generate visuals (Freepik Mystic + overlay para LinkedIn + Instagram)

Skip the visuals for any platform excluded by `solo:` — only generate for the platform(s) that actually need posting.

**Tanto LinkedIn como Instagram llevan overlay de texto** sobre la imagen base de Mystic (vía `image_overlay.py`). El overlay de LinkedIn es el **hook del post** — así el feed se detiene en la imagen antes de leer el caption. Si el usuario pasó `images:` en el comando, se respeta lo que entregó y **no** se aplica overlay (ni a LinkedIn ni a Instagram).

#### 5.A — Si el usuario pasó `images:` en el comando

- Parse the comma-separated list of paths/URLs.
- For Instagram with `formato-instagram: carrusel`, use all of them as the carousel.
- For Instagram without carousel flag, use only the first image.
- For LinkedIn, use only the first image.
- Skip AI generation **and skip the overlay** — respeta lo que el usuario entregó.
- Si las rutas son **locales**, súbelas a Blotato con `bc.upload_media_local()` para obtener URLs públicas; si ya son URLs, déjalas tal cual.
- Print: `[ok] Usando imágenes proporcionadas por el usuario.`

#### 5.B — Si no se pasó `images:`

Si `cfg["freepik_api_key"]` está vacío:
```
[aviso] FREEPIK_API_KEY no configurado en .env — se publicará solo texto.
```
y salta directamente al Step 6 con `media_urls = []` en ambas plataformas.

Si la key está presente y el comando **ya incluye** `formato-instagram:`, usa ese valor y NO preguntes nada. Si el comando NO trae el flag y vas a generar visual de Instagram, pregunta:
```
¿Qué formato prefieres para el visual de Instagram?
  a) Imagen única (con título overlay)
  b) Carrusel de 3 imágenes (Hook / Info / Créditos)
```

**Crafting de prompts (lo hace Claude, no se llama a otro LLM):**

A partir del `title`, `transcript`, `keyPoints` y `chapters` del Step 1, redacta prompts visuales que **estén relacionados con el contenido del video** — concepto principal, tema, objetos, ambiente. Cada prompt debe describir una escena/composición concreta, no una idea abstracta.

Reglas para todos los prompts:
- En **inglés** (Mystic rinde mejor en inglés).
- **NO pedir texto en la imagen** — Mystic no renderiza copy fiable; el texto lo añade `image_overlay`. Añade siempre el modificador: `"no text, no typography, no logos, no watermarks"`.
- Mantén espacio para overlay: indica `"composition with negative space for overlay text"` (LinkedIn 4:5 = espacio al pie; IG single = espacio en la mitad inferior; carrusel slide 1 = centrado; slide 3 = centrado).
- Especifica estilo, iluminación, composición y paleta. Ej: `"editorial photography, soft natural lighting, shallow depth of field, muted warm palette"`.
- Mantén el prompt bajo 300 caracteres por imagen.

##### LinkedIn (1 imagen 4:5 + hook overlay)

1. Genera la base 4:5 con Mystic.
2. Destila el **hook overlay**: una frase de máx. 8-12 palabras que reproduzca o sintetice la primera línea del post de LinkedIn — el objetivo es que quien ve el feed se detenga en la imagen y quiera leer el resto. Tiene que respetar la regla de **citas fieles** (no inventar datos que no estén en `transcript` / `title` / `description`).
3. Renderiza con `ov.render_linkedin_hook(base_url, hook_overlay, lang=lang)`.
4. Sube el PNG a Blotato con `bc.upload_media_local()` → URL pública.

Prompt visual: igual de profesional que antes pero ahora **dejando negative space al pie** para el overlay del hook:

```python
linkedin_prompt = (
    f"<descripción visual del concepto principal del video, "
    f"profesional, sobrio, relacionado con: {tema}>. "
    f"Editorial photography style, clean composition, soft natural lighting, "
    f"muted professional palette, composition with negative space at the bottom for overlay text. "
    f"No text, no typography, no logos, no watermarks."
)
base_urls = fp.generate_image(
    linkedin_prompt,
    api_key=cfg["freepik_api_key"],
    aspect_ratio="social_post_4_5",
)
hook_overlay = "<hook destilado a 8-12 palabras>"

try:
    png_bytes = ov.render_linkedin_hook(base_urls[0], hook_overlay, lang=lang)
    public_url = bc.upload_media_local(png_bytes, "linkedin-hook.png", api_key=cfg["api_key"])
    linkedin_media_urls = [public_url]
except Exception as e:
    print(f"[aviso] Overlay/upload falló para LinkedIn ({e}) — uso la imagen limpia de Mystic.")
    linkedin_media_urls = base_urls[:1]
```

##### Instagram — imagen única (1 imagen 1:1 + título overlay)

1. Genera la base con Mystic.
2. Decide el **título overlay**: una frase de máx. 8-10 palabras que sintetice el hook del post (no copies el primer renglón del caption — destila la idea central).
3. Renderiza con `ov.render_single(base_url, title, lang=lang)`.
4. Sube el PNG a Blotato con `bc.upload_media_local()` → URL pública.

```python
ig_prompt = (
    f"<descripción visual atractiva y bold del tema central: {tema}>. "
    f"Modern editorial style, vibrant but tasteful, high contrast, "
    f"strong focal point, composition with negative space at the bottom for overlay text. "
    f"No text, no typography, no logos, no watermarks."
)
base_urls = fp.generate_image(ig_prompt, api_key=cfg["freepik_api_key"], aspect_ratio="square_1_1")
overlay_title = "<hook destilado a 8-10 palabras>"

try:
    png_bytes = ov.render_single(base_urls[0], overlay_title, lang=lang)
    public_url = bc.upload_media_local(png_bytes, "ig-single.png", api_key=cfg["api_key"])
    instagram_media_urls = [public_url]
except Exception as e:
    print(f"[aviso] Overlay/upload falló para IG single ({e}) — uso la imagen limpia de Mystic.")
    instagram_media_urls = base_urls[:1]
```

##### Instagram — carrusel (formato fijo de 3 slides: Hook / Info / Créditos)

Cuando se usa carrusel **el formato es siempre 3 slides con roles fijos**:

| Slide | Rol | Contenido overlay |
|---|---|---|
| 1 | **Hook** | Título grande centrado (máx 10 palabras) + "Desliza →" |
| 2 | **Argumento** | Encabezado generado (específico al video) + 2-3 frases cortas que cuentan el argumento central |
| 3 | **Créditos** | "VIDEO ORIGINAL" + título del video + canal + "Link en bio 🔗" |

1. Genera 3 bases visuales con Mystic, manteniendo coherencia (mismo estilo/paleta/iluminación) y reservando negative space según el rol:
   - Slide 1: composición centrada (espacio en el medio para título).
   - Slide 2: composición lateral/desplazada o textura general (texto cubre toda la imagen con gradiente fuerte).
   - Slide 3: composición simple, baja saturación (créditos en el centro).
2. Para cada slide, llama al renderer correspondiente con los textos que destilaste del transcript:
   - `ov.render_hook(base_urls[0], hook_title, lang=lang)`
   - `ov.render_info(base_urls[1], argument_sentences, heading=argument_heading, lang=lang)` — ver instrucciones de contenido abajo.
   - `ov.render_credits(base_urls[2], channel_name, video_title, lang=lang)` — `channel_name` viene de `content["channel"]` del Step 1.
3. Sube cada PNG a Blotato y arma `instagram_media_urls` en orden.

```python
carousel_prompts = [
    "<hook visual del tema, composición centrada, negative space en el medio>. Modern editorial, ...",
    "<visual del insight/idea principal, textura o composición lateral>. Same style as previous, ...",
    "<visual minimalista de cierre, baja saturación, composición simple>. Same style, low saturation, ...",
]
base_urls = fp.generate_carousel(
    carousel_prompts,
    api_key=cfg["freepik_api_key"],
    aspect_ratio="square_1_1",
)

# Textos destilados del transcript (no inventar — siguen la regla de citas fieles del Step 4)
hook_title         = "<8-10 palabras que capturen la idea madre>"
argument_heading   = "<3-5 palabras específicas al tema del video — no genéricas como 'La idea' o 'Resumen'>"
argument_sentences = [
    "<frase 1: plantea el problema o contexto — ≤ 15 palabras>",
    "<frase 2: el argumento o solución central del video — ≤ 15 palabras>",
    # frase 3 opcional: consecuencia o matiz relevante
]
video_title  = content["title"]
channel_name = content.get("channel", "")

slides_payload = [
    ("ig-carousel-1-hook.png",    lambda u: ov.render_hook(u, hook_title, lang=lang)),
    ("ig-carousel-2-info.png",    lambda u: ov.render_info(u, argument_sentences, heading=argument_heading, lang=lang)),
    ("ig-carousel-3-credits.png", lambda u: ov.render_credits(u, channel_name, video_title, lang=lang)),
]

instagram_media_urls = []
for (fname, render_fn), base_url in zip(slides_payload, base_urls):
    if base_url is None:
        print(f"[aviso] {fname} no se generó — se omite esta slide.")
        continue
    try:
        png = render_fn(base_url)
        public_url = bc.upload_media_local(png, fname, api_key=cfg["api_key"])
        instagram_media_urls.append(public_url)
    except Exception as e:
        print(f"[aviso] Overlay/upload falló para {fname} ({e}) — uso la base limpia.")
        instagram_media_urls.append(base_url)
```

**Cómo escribir el argumento central (slide 2):**

El objetivo de esta slide es que quien la vea entienda *de qué va el video* en 5 segundos — no un resumen genérico, sino el argumento o tesis específica que desarrolla el autor.

- **`argument_heading`**: 3-5 palabras que nombren el tema concreto del video. Tiene que ser específico — si el video es sobre por qué los horarios matutinos dañan la creatividad, el encabezado podría ser "EL MITO DEL MADRUGADOR". Prohibido usar encabezados genéricos como "LA IDEA", "EN RESUMEN", "DE QUÉ VA" (solo úsalos como último recurso si el video es demasiado vago). Siempre en mayúsculas.
- **`argument_sentences`**: 2-3 frases que cuenten el argumento del video con estructura narrativa natural:
  - Frase 1: el problema, pregunta o contexto que el video aborda.
  - Frase 2: la tesis, solución o insight central que el autor defiende.
  - Frase 3 (opcional): una consecuencia, matiz o dato que refuerce la idea.
  - Cada frase ≤ 15 palabras. No usar gerundios encadenados ni listas disfrazadas de frases.
  - La primera frase se renderiza en color acento (amarillo) para anclarse visualmente — que sea la más impactante o la que planta el problema.
  - Respeta la regla de citas fieles del Step 4: no fabricar claims que no estén en el transcript.

**Si menos de 2 slides se generaron con éxito**, descarta el carrusel y degrada a imagen única (mejor 1 buena que un carrusel cojo):
```python
if len([u for u in instagram_media_urls if u]) < 2:
    print("[aviso] El carrusel quedó incompleto — degradando a imagen única con la primera slide disponible.")
    instagram_media_urls = instagram_media_urls[:1]
```

#### 5.C — Manejo de errores (todas las variantes)

| Falla | Acción |
|---|---|
| `fp.generate_image` lanza excepción | Captura, avisa, pon `media_urls = []` para esa plataforma |
| `import PIL` falla (Pillow no instalado) | `[aviso] Pillow no instalado — publicando la base limpia de Mystic sin overlay.` Sigue con `media_urls = [base_url]` |
| `ov.render_*` lanza excepción | Avisa, usa la URL limpia de Mystic como fallback |
| `bc.upload_media_local` falla | Avisa, usa la URL de Freepik directamente (puede caducar antes; aceptable como fallback) |
| Carrusel con < 2 slides exitosos | Degrada a imagen única |

#### 5.D — Resolver timing (antes de mostrar el Step 6)

Resuelve `schedule_time` ahora, para que el bloque de aprobación lo muestre ya fijo:

- Si el usuario pasó `publicar: ahora` o no pasó `publicar:` → **pregunta**:
  ```
  ¿Cuándo quieres publicar?
    a) Ahora
    b) Programar para más tarde (fecha en lenguaje natural — "mañana 9am",
       "viernes 18h" — o en formato ISO-8601: YYYY-MM-DDTHH:MM:SSZ)
  ```
  Si responde `a` o no responde → `schedule_time = None`.
- Si el usuario pasó un **timestamp ISO-8601** → úsalo directamente.
- Si el usuario pasó **lenguaje natural** en español → conviértelo tú a ISO-8601 UTC relativo a `currentDate`. Si la fecha resultante está en el pasado, avisa con `[error] La fecha programada es en el pasado: <fecha>.` y vuelve a preguntar.
- Guarda el resultado como `schedule_time` (string ISO-8601 o `None`).

---

### Step 6 — Aprobación final (OBLIGATORIO antes de publicar)

This is the **only** approval gate. It covers posts + visuals + timing together. Show the complete final content in a single message:

```
─────────────────────────────────────────
CONTENIDO LISTO PARA PUBLICAR
─────────────────────────────────────────

[LinkedIn] — <Nombre de cuenta>
<texto completo del post>
Visual: <url de la imagen o "ninguno">
Timing: ahora | programado para <fecha ISO-8601 UTC>  ← si fue lenguaje natural, muestra también lo que entendiste: "mañana 9am → 2026-05-16T09:00:00Z"

─────────────────────────────────────────

[Instagram] — @<username>
<texto completo del post>
Visual: <url(s) de la(s) imagen(es) o "ninguno">
Formato: imagen única | carrusel (<N> imágenes)
Timing: ahora | programado para <fecha ISO-8601 UTC>

─────────────────────────────────────────

¿Apruebas este contenido? (sí/editar/cancelar)
```

**Rules for what to show:**
- If `solo: linkedin` was passed, omit the Instagram block. Same for `solo: instagram` and the LinkedIn block.
- If `dry-run: si` was passed, add this line at the top of the block:
  ```
  [aviso] DRY-RUN ACTIVADO — esta aprobación no publicará nada, solo cierra el flujo.
  ```

**Wait for the user's response before doing anything else.**

- **sí** → proceed to Step 7 (Publish or dry-run summary).
- **editar** → ask what to change. The user may target a specific piece ("cambia el hook de LinkedIn", "quita el último hashtag de Instagram", "regenera el visual de Instagram"). Apply the edits:
  - Text edits → re-run the **Step 4.5 humanization checklist** on the modified text before showing it again.
  - Visual edits → regenerate only the affected image(s) via Freepik (or accept a new path/URL the user provides).
  - Timing edits → re-parse and convert if natural language.
  Then show this approval block again from the top. Repeat until the user replies `sí` or `cancelar`.
- **cancelar** → print `[cancelado] No se publicó nada.` and stop.

Do not proceed to publishing under any other circumstance.

---

### Step 7 — Publish

**Dry-run guard:** If `dry-run: si` was passed in the command, **skip every `bc.publish_post` call** in this step. Jump straight to Step 8 and present the summary, marking each platform with `Status: dry-run (no se envió)`.

Use the `schedule_time` already resolved in Step 5.D. If the user edited timing during Step 6, re-apply the same conversion rules.

**Platform filter:** If `solo: linkedin` was passed, only execute the LinkedIn publish block (skip Instagram entirely). Same for `solo: instagram`.

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

Show one block per platform that actually ran (respect `solo:`). If `dry-run: si`, use the dry-run header and mark each `Status:` accordingly.

```
[listo] Publicado exitosamente:        ← o "[listo] DRY-RUN finalizado — no se publicó nada:" si dry-run

[LinkedIn]
   Post: "<primeros 80 caracteres>"...
   Visual: <url o "ninguno">
   Status: published | scheduled for <time> | dry-run (no se envió)
   URL: <publicUrl o "—" en dry-run>

[Instagram]
   Post: "<primeros 80 caracteres>"...
   Visual: <url o "ninguno">
   Formato: imagen única | carrusel (<N> imágenes)
   Status: published | scheduled for <time> | dry-run (no se envió)
   URL: <publicUrl o "—" en dry-run>
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
