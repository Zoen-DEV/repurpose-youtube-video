# repurpose-youtube-video

Un skill de [Claude Code](https://claude.com/claude-code) que transforma un video de YouTube en posts listos para publicar en **LinkedIn** e **Instagram**, con textos optimizados por plataforma y visuales generados con IA — todo en una sola conversación, con aprobación humana obligatoria antes de publicar.

Publicación vía la API de [Blotato](https://blotato.com).

---

## Qué hace

A partir de una URL de YouTube, el skill:

1. Extrae metadata y transcript del video (sin coste de API, usando `yt-dlp` + `youtube-transcript-api`) y **detecta el idioma** (es/en) para redactar en consecuencia.
2. Te pregunta tono y objetivo **por red** (LinkedIn e Instagram pueden tener registros distintos) — salvo que ya los hayas pasado en el comando.
3. Redacta el copy adaptado a cada plataforma (LinkedIn 150–300 palabras, Instagram 80–150), nutriendo los hashtags desde los `tags` y `chapters` del propio video y exigiéndose **fidelidad a la transcripción** (no inventa datos, citas ni cifras).
4. Humaniza los textos eliminando muletillas, vocabulario inflado y otras marcas típicas de IA (em-dashes, emojis decorativos, hooks genéricos…), en español y en inglés.
5. Genera un visual con IA (o usa imágenes que tú le pases).
6. Te muestra **todo en un único bloque de aprobación** (posts + visuales + timing) y espera tu confirmación explícita.
7. Publica o programa los posts vía Blotato — o no publica nada si pasaste `dry-run: si`.

> **Regla de oro:** el skill nunca publica sin una confirmación manual `sí` en el paso 6. Está hardcodeado en `SKILL.md`. Es el único punto de aprobación.

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
git clone https://github.com/Zoen-DEV/repurpose-youtube-video.git "$env:USERPROFILE\.claude\skills\repurpose-youtube-video"
```

**macOS / Linux:**
```bash
git clone https://github.com/Zoen-DEV/repurpose-youtube-video.git ~/.claude/skills/repurpose-youtube-video
```

### 2. Instala las dependencias de Python

```bash
python -m pip install yt-dlp youtube-transcript-api Pillow
```

- `yt-dlp` + `youtube-transcript-api` → extracción del video.
- `Pillow` → text overlay sobre las imágenes de LinkedIn (hook 4:5) e Instagram (título en single, Hook/Info/Créditos en carrusel). Si Pillow falla al importar, el skill avisa y publica la imagen limpia de Freepik sin overlay.

El cliente HTTP de Blotato usa solo `urllib` de la stdlib — sin otras dependencias.

**Fuente del overlay (opcional):** `image_overlay.py` busca, en este orden: la env var `OVERLAY_FONT_PATH`, un `font.ttf` / `font-bold.ttf` junto al script, las fuentes del sistema (Arial / Helvetica / DejaVu / Liberation), y como último recurso una bitmap default. Si quieres tu propia tipografía, copia el `.ttf` al directorio `scripts/` con esos nombres.

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

| Campo | Valores | Default | Efecto |
|---|---|---|---|
| `images:` | rutas locales o URLs separadas por coma | (se genera visual con IA) | Salta la generación de visual con IA y usa esas imágenes (sin overlay) |
| `formato-instagram:` | `imagen-unica` \| `carrusel` | `imagen-unica` | Si se pasa, el skill no pregunta el formato |
| `tono:` | `inspiracional` \| `educativo` \| `personal` | (pregunta en Step 3) | **Default global** aplicado a las dos plataformas; los overrides por red ganan |
| `tono-linkedin:` | `inspiracional` \| `educativo` \| `personal` | (toma `tono:` o se pregunta) | **Override solo para LinkedIn** |
| `tono-instagram:` | `inspiracional` \| `educativo` \| `personal` | (toma `tono:` o se pregunta) | **Override solo para Instagram** |
| `objetivo:` | `awareness` \| `engagement` \| `trafico` | (pregunta en Step 3) | **Default global** aplicado a las dos plataformas; los overrides por red ganan |
| `objetivo-linkedin:` | `awareness` \| `engagement` \| `trafico` | (toma `objetivo:` o se pregunta) | **Override solo para LinkedIn** |
| `objetivo-instagram:` | `awareness` \| `engagement` \| `trafico` | (toma `objetivo:` o se pregunta) | **Override solo para Instagram** |
| `idioma:` | `es` \| `en` \| `auto` | `auto` | `auto` detecta del transcript; ES/EN soportados |
| `solo:` | `linkedin` \| `instagram` | (ambas) | Publica solo en una plataforma; salta la otra entera |
| `dry-run:` | `si` | `no` | Genera y muestra todo, pero **no publica nada** |
| `publicar:` | `ahora` \| ISO-8601 \| **lenguaje natural** ("mañana 9am", "viernes 18h", "el 3 de junio a las 10am") | `ahora` | El natural se convierte a ISO-8601 UTC y se confirma en el Step 6 |

> Precedencia: `tono-<red>:` > `tono:` > pregunta al usuario. Idem para `objetivo:`. Step 3 pregunta **solo** las ranuras que queden sin resolver.

### Ejemplos

**Caso básico** (visuales generados por IA, publicación inmediata, idioma auto):
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

**Sin preguntas, todo predefinido + scheduling en lenguaje natural:**
```
Crear post para Instagram y LinkedIn:

youtube-link: https://youtu.be/dQw4w9WgXcQ
tono: educativo
objetivo: engagement
publicar: mañana 9am
```

**Tono y objetivo distintos por red** (LinkedIn más educativo, Instagram más inspiracional):
```
Crear post para Instagram y LinkedIn:

youtube-link: https://youtu.be/dQw4w9WgXcQ
tono-linkedin: educativo
objetivo-linkedin: engagement
tono-instagram: inspiracional
objetivo-instagram: awareness
```

**Publicar solo en LinkedIn, en inglés:**
```
Crear post para Instagram y LinkedIn:

youtube-link: https://youtu.be/dQw4w9WgXcQ
solo: linkedin
idioma: en
```

**Dry-run para revisar sin publicar:**
```
Crear post para Instagram y LinkedIn:

youtube-link: https://youtu.be/dQw4w9WgXcQ
dry-run: si
```

**Publicación programada con timestamp explícito:**
```
Crear post para Instagram y LinkedIn:

youtube-link: https://youtu.be/dQw4w9WgXcQ
publicar: 2026-06-01T14:00:00Z
```

---

## Cómo funciona (los 8 pasos)

1. **Extraer video + detectar idioma** — metadata + transcript con `yt-dlp` y `youtube-transcript-api`, sin API key. Claude detecta automáticamente si el video está en español o inglés (override con `idioma:`).
2. **Cuentas** — usa los IDs del `.env`, o los pide vía la API de Blotato si están vacíos. Respeta `solo:` y omite la plataforma excluida.
3. **Preguntas de calidad — POR RED** — tono y objetivo se resuelven por plataforma (precedencia `tono-<red>:` > `tono:` > pregunta). Solo se pregunta lo que falta. Si Step 3 corre porque falta algo, muestra **solo las ranuras no resueltas** (LinkedIn / Instagram / ambas).
4. **Escribir posts** — Claude redacta directamente LinkedIn e Instagram en el idioma detectado (no se llama a otro LLM externo) usando el `tono` y `objetivo` resueltos por red. Citas y datos: solo lo que esté literal en el transcript. Hashtags: derivados de los `tags` y `chapters` del video. **LinkedIn incluye la URL del video original** justo antes de los hashtags (LinkedIn auto-unfurla la preview); Instagram refiere a "link en bio" en lugar de pegar la URL.
4.5. **Humanizar** — Claude limpia las marcas típicas de IA (muletillas y vocabulario inflado en ES y EN, em-dashes excesivos, emojis decorativos apilados, hooks genéricos…) en silencio. No hay aprobación intermedia.
5. **Visuales** — usa imágenes propias si las pasaste (subiéndolas a Blotato vía presigned upload si son rutas locales; sin overlay), o genera con Freepik Mystic. Si `formato-instagram:` ya viene en el comando, no se pregunta nada.
   - **LinkedIn → hook overlay** sobre la imagen 4:5 (1080×1350) — el primer renglón del post se imprime al pie de la imagen para detener el scroll.
   - **Instagram single → título overlay** al pie de la imagen (1:1).
   - **Instagram carrusel → 3 slides con roles fijos** (1:1):
     - Slide 1 = **Hook**: título grande centrado + "Desliza →".
     - Slide 2 = **Info**: encabezado + 3-5 bullets cortos con las ideas clave.
     - Slide 3 = **Créditos**: canal del video + título + "Link en bio 🔗".
   - El texto lo aplica `image_overlay.py` (Pillow). Si Pillow no está disponible o falla el upload, se cae a la imagen limpia de Mystic.
6. **Aprobación final OBLIGATORIA (única)** — bloque consolidado con posts + visuales + timing. Espera `sí` / `editar` / `cancelar`. En `editar`, los cambios se re-humanizan y se vuelve a mostrar el bloque.
7. **Publicar** — inmediato, programado en ISO-8601, o programado en lenguaje natural ("mañana 9am") que el skill convierte a UTC. Si `dry-run: si`, **se omite la llamada de publicación**.
8. **Resumen** — URLs públicas + status de cada post. En dry-run, `Status: dry-run (no se envió)`.

El detalle completo (prompts exactos, manejo de errores, edge cases, checklist completa de humanización) está en [SKILL.md](SKILL.md).

---

## Estructura del proyecto

```
repurpose-youtube-video/
├── SKILL.md                  # Instrucciones que ejecuta Claude Code
├── README.md                 # Este archivo
├── .env.example              # Plantilla de credenciales
├── .gitignore                # Excluye .env y otros artefactos
├── scripts/
│   ├── blotato_client.py     # Cliente HTTP de Blotato + extractor de YouTube + media upload
│   ├── freepik_client.py     # Cliente HTTP de Freepik Mystic (text-to-image)
│   └── image_overlay.py      # Text overlay con Pillow para visuales de LinkedIn e Instagram
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
| Visual no se genera | Timeout o template caído en Blotato/Freepik | El skill publica solo el texto (warning) |
| Carrusel se publica sin texto | Pillow no instalado o `ov.render_*` falló | Instala `Pillow` (`python -m pip install Pillow`); el skill ya usa la imagen limpia como fallback |
| Tipografía del overlay se ve fea | El sistema no tiene Arial/Helvetica/DejaVu y se usó la bitmap default | Coloca un `.ttf` en `scripts/font-bold.ttf` (y opcional `font.ttf`) o exporta `OVERLAY_FONT_PATH=ruta/a/tu/font.ttf` |
| Upload del PNG a Blotato falla | Endpoint `/v2/media/uploads` rate-limited (10/min) o presigned URL caducada | Reintenta; si insiste, el skill cae a la URL directa de Freepik como fallback |

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
