# repurpose-youtube-video

Un skill de [Claude Code](https://claude.com/claude-code) que transforma un video de YouTube en posts listos para publicar en **LinkedIn** e **Instagram**, con textos optimizados por plataforma y visuales generados con IA — todo en una sola conversación, con aprobación humana obligatoria antes de publicar.

Publicación vía la API de [Blotato](https://blotato.com).

---

## Qué hace

A partir de una URL de YouTube, el skill:

1. Extrae metadata y transcript del video (sin coste de API, usando `yt-dlp` + `youtube-transcript-api`).
2. Te pregunta tono y objetivo de los posts.
3. Redacta el copy adaptado a cada plataforma (LinkedIn 150–300 palabras, Instagram 80–150).
4. Genera un visual con IA (o usa imágenes que tú le pases).
5. Te muestra todo en bloque y espera tu aprobación explícita.
6. Publica o programa los posts vía Blotato.

> **Regla de oro:** el skill nunca publica sin una confirmación manual `sí` en el paso 6. Está hardcodeado en `SKILL.md`.

---

## Requisitos previos

- **Claude Code** instalado y funcionando ([guía oficial](https://claude.com/claude-code))
- **Python 3.9+** disponible en el PATH
- Cuenta en **[Blotato](https://my.blotato.com)** con plan que incluya API + generación de visuales
- Al menos una cuenta de LinkedIn y/o Instagram **conectada en Blotato**

---

## Instalación

### 1. Clona el repositorio en tu carpeta de skills

Claude Code carga automáticamente los skills que viven en `~/.claude/skills/`.

**Windows (PowerShell):**
```powershell
git clone https://github.com/Zoen-DEV/repurpuse-youtube-video.git "$env:USERPROFILE\.claude\skills\repurpose-youtube-video"
```

**macOS / Linux:**
```bash
git clone https://github.com/Zoen-DEV/repurpuse-youtube-video.git ~/.claude/skills/repurpose-youtube-video
```

### 2. Instala las dependencias de Python

```bash
python -m pip install yt-dlp youtube-transcript-api
```

No hay más dependencias: el cliente HTTP de Blotato usa solo `urllib` de la stdlib.

### 3. Configura tus credenciales de Blotato

1. Obtén tu API key en https://my.blotato.com/settings/api
2. Copia la plantilla a `.env` y rellénala:

**Windows (PowerShell):**
```powershell
cd $env:USERPROFILE\.claude\skills\repurpose-youtube-video
Copy-Item .env.example .env
notepad .env
```

**macOS / Linux:**
```bash
cd ~/.claude/skills/repurpose-youtube-video
cp .env.example .env
nano .env
```

Contenido mínimo del `.env`:
```ini
BLOTATO_API_KEY=tu_api_key_aqui
BLOTATO_LINKEDIN_ACCOUNT_ID=            # opcional — déjalo vacío la primera vez
BLOTATO_INSTAGRAM_ACCOUNT_ID=           # opcional — déjalo vacío la primera vez
```

> **¿Dónde colocar el `.env`?** El cliente busca en dos sitios, en este orden:
>
> 1. **CWD** — la carpeta desde la que se lanzó Claude Code.
> 2. **Raíz del skill** — `~/.claude/skills/repurpose-youtube-video/.env` (fallback).
>
> **Recomendado para nuevos usuarios:** opción 2 — pon el `.env` directamente en la raíz del skill. Es lo más simple: clonas, rellenas, listo.
>
> **Setup avanzado:** si prefieres mantener las credenciales fuera del repo (por ejemplo para evitar cualquier riesgo de commit accidental, o porque manejas varias API keys), crea una carpeta de workspace separada y pon ahí tu `.env`. Lanza Claude Code desde esa carpeta y su `.env` ganará sobre el del skill.
>
> **Importante:** el `.env` está incluido en `.gitignore`, pero verifica con `git status` antes de cualquier `git push` que no aparece como modificado o nuevo. Una API key leakeada en un commit público es una mala tarde.

### 4. Conecta tus cuentas sociales en Blotato

En el dashboard de Blotato, conecta tus perfiles de LinkedIn e Instagram. La primera vez que corras el skill sin los `*_ACCOUNT_ID`, el skill listará las cuentas conectadas y te pedirá copiar los IDs al `.env`.

---

## Uso

Una vez instalado, dile a Claude Code exactamente esto (el formato del trigger es **estricto** a propósito):

```
Crear post para Instagram y LinkedIn:

youtube-link: https://www.youtube.com/watch?v=XXXXXXXXXXX
```

Cualquier otro fraseo ("repurpose this video", "summarize this YouTube clip", etc.) **no** dispara el skill. Esto evita activaciones accidentales.

### Parámetros opcionales

Puedes añadir cualquiera de estos campos al comando:

| Campo | Valores | Default |
|---|---|---|
| `images:` | rutas locales o URLs separadas por coma | (se genera visual con IA) |
| `formato-instagram:` | `imagen-unica` \| `carrusel` | `imagen-unica` |
| `publicar:` | `ahora` \| `YYYY-MM-DDTHH:MM:SSZ` (UTC) | `ahora` |

### Ejemplos

**Caso básico** (visuales generados por IA, publicación inmediata):
```
Crear post para Instagram y LinkedIn:

youtube-link: https://youtu.be/dQw4w9WgXcQ
```

**Con imágenes propias + carrusel en Instagram:**
```
Crear post para Instagram y LinkedIn:

youtube-link: https://youtu.be/dQw4w9WgXcQ
images: C:\imagenes\slide1.jpg, C:\imagenes\slide2.jpg, C:\imagenes\slide3.jpg
formato-instagram: carrusel
```

**Publicación programada:**
```
Crear post para Instagram y LinkedIn:

youtube-link: https://youtu.be/dQw4w9WgXcQ
publicar: 2026-06-01T14:00:00Z
```

---

## Cómo funciona (los 8 pasos)

1. **Extraer video** — metadata + transcript con `yt-dlp` y `youtube-transcript-api`. Sin API key.
2. **Cuentas** — usa los IDs del `.env`, o los pide vía la API de Blotato si están vacíos.
3. **Preguntas de calidad** — tono (inspiracional / educativo / personal) y objetivo (awareness / engagement / tráfico).
4. **Escribir posts** — Claude redacta directamente LinkedIn e Instagram (no se llama a otro LLM externo).
5. **Visuales** — usa imágenes propias si las pasaste, o genera con plantillas de Blotato.
6. **Aprobación final OBLIGATORIA** — bloque consolidado con posts + visuales + timing. Espera `sí` / `editar` / `cancelar`.
7. **Publicar** — inmediato o programado (`scheduledAt` ISO-8601).
8. **Resumen** — URLs públicas + status de cada post.

El detalle completo (prompts exactos, manejo de errores, edge cases) está en [SKILL.md](SKILL.md).

---

## Estructura del proyecto

```
repurpose-youtube-video/
├── SKILL.md                  # Instrucciones que ejecuta Claude Code
├── README.md                 # Este archivo
├── .env.example              # Plantilla de credenciales
├── .gitignore                # Excluye .env y otros artefactos
├── scripts/
│   └── blotato_client.py     # Cliente HTTP de Blotato + extractor de YouTube
└── evals/
    └── evals.json            # Casos de evaluación del trigger
```

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `BLOTATO_API_KEY not found` | `.env` no existe o está en otra carpeta | Verifica que `.env` esté en la raíz del skill o en tu CWD |
| `401 Unauthorized` | API key inválida o revocada | Regenera en https://my.blotato.com/settings/api |
| `422 too many hashtags` (Instagram) | Más de 5 hashtags en el post | El skill ya los recorta; si vuelve a pasar, edítalo en el paso 4 |
| `429 Too Many Requests` | Rate limit de Blotato | El skill reintenta una vez automáticamente tras 10s |
| `Multiple LinkedIn accounts found` | Más de una cuenta conectada en Blotato | Copia el ID deseado al `.env` y vuelve a correr |
| Transcript vacío / falla la extracción | Video sin subtítulos, privado o con región bloqueada | El skill continúa solo con el título (warning visible en consola) |
| Visual no se genera | Timeout o template caído en Blotato | El skill publica solo el texto (warning) |

---

## Limitaciones conocidas

- **Solo dos plataformas** por ahora: LinkedIn e Instagram. Twitter/X, Threads y TikTok están en backlog.
- **Template IDs hardcodeados** en `SKILL.md`. Si Blotato rota los IDs, el skill genera visuales con un fallback genérico (o falla en silencio). Issue abierto.
- **Instagram limita a 5 hashtags**; otros límites pueden cambiar sin aviso del lado de Blotato.
- **El trigger está en español**. Si quieres adaptarlo a otro idioma, edita el `description` en `SKILL.md` y el bloque de `Command format`.

---

## Contribuir

Pull requests bienvenidos. Antes de abrir uno:

1. No cambies el formato del trigger sin coordinar — romperia compatibilidad hacia atrás con usuarios existentes.
2. Si añades dependencias de Python, documéntalas en este README y en `SKILL.md`.
3. Mantén la regla obligatoria de aprobación del paso 6. Es la garantía principal del skill.
4. Si tocas `blotato_client.py`, conserva el principio de "sin dependencias HTTP externas" — solo `urllib`.

Para reportar bugs, abre un issue con: comando exacto que disparó el error, output completo, y versión de Python.

---

## Licencia

MIT — ver [LICENSE](LICENSE).

---

## Créditos

- API de publicación: [Blotato](https://blotato.com)
- Extracción de YouTube: [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
- Construido con [Claude Code](https://claude.com/claude-code)
