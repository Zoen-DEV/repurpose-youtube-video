"""
Freepik API client - image generation for repurpose-youtube-video skill.
Uses Freepik Mystic (text-to-image, high quality).

Endpoints used:
  POST /v1/ai/mystic                 -> creates task, returns task_id
  GET  /v1/ai/mystic/{task_id}       -> poll, status: CREATED | IN_PROGRESS | COMPLETED | FAILED
                                        on COMPLETED, payload contains list of image URLs

Auth header: x-freepik-api-key: <key>

Aspect ratios in use:
  - "square_1_1"      -> Instagram (single image y slides de carrusel)
  - "social_post_4_5" -> LinkedIn (4:5 vertical, render optimo en feed)

The generated images do NOT carry text overlays (Mystic is unreliable at rendering
copy). El texto del post lo lleva el caption en cada plataforma; la imagen aporta
unicamente el componente visual relacionado con el contenido del video.
"""

import json
import time
import urllib.request
import urllib.error

BASE_URL = "https://api.freepik.com/v1"


def _request(method: str, path: str, body: dict | None = None, *, api_key: str) -> dict:
    url = path if path.startswith("http") else BASE_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"x-freepik-api-key": api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        if e.code == 429:
            print("   [freepik rate-limit] Waiting 10s and retrying...")
            time.sleep(10)
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        raise RuntimeError(f"Freepik HTTP {e.code} {method} {path}: {body_text}") from e


def _extract_urls(payload: dict) -> list[str]:
    """Mystic responses have varied across versions; try the common shapes."""
    for key in ("generated", "images", "image_urls", "urls"):
        val = payload.get(key)
        if isinstance(val, list) and val:
            return [u if isinstance(u, str) else u.get("url", "") for u in val if u]
    if isinstance(payload.get("image"), str):
        return [payload["image"]]
    return []


def _poll_task(task_id: str, *, api_key: str, interval: int = 4, max_attempts: int = 60) -> list[str]:
    for _ in range(max_attempts):
        resp = _request("GET", f"/ai/mystic/{task_id}", api_key=api_key)
        data = resp.get("data", resp)
        status = (data.get("status") or "").upper()
        if status == "COMPLETED":
            urls = _extract_urls(data)
            if not urls:
                raise RuntimeError(f"Freepik task {task_id} completed but no image URLs found: {data}")
            return urls
        if status in ("FAILED", "ERROR"):
            raise RuntimeError(f"Freepik task {task_id} failed: {data.get('message', data)}")
        time.sleep(interval)
    raise TimeoutError(f"Freepik task {task_id} timed out after {max_attempts * interval}s")


def generate_image(
    prompt: str,
    *,
    api_key: str,
    aspect_ratio: str = "square_1_1",
    model: str = "realism",
) -> list[str]:
    """
    Generate one image with Freepik Mystic and return the resulting URL(s).

    Args:
        prompt: Detailed visual description. Avoid asking for embedded text -
                Mystic does not render copy reliably; the social caption carries the text.
        aspect_ratio: "square_1_1" | "social_post_4_5" | "widescreen_16_9" | ...
        model: "realism" | "fluid" | "zen"
    """
    body = {
        "prompt": prompt[:1000],
        "aspect_ratio": aspect_ratio,
        "model": model,
        "creative_detailing": 33,
        "engine": "automatic",
        "filter_nsfw": True,
    }
    resp = _request("POST", "/ai/mystic", body, api_key=api_key)
    data = resp.get("data", resp)
    task_id = data.get("task_id") or data.get("id")
    if not task_id:
        raise RuntimeError(f"Freepik: no task_id in response: {resp}")
    return _poll_task(task_id, api_key=api_key)


def generate_carousel(
    prompts: list[str],
    *,
    api_key: str,
    aspect_ratio: str = "square_1_1",
) -> list[str]:
    """
    Generate N images sequentially - one per prompt - for an Instagram carousel.
    Returns a flat list of URLs in input order, skipping any prompt whose
    generation failed (so a single bad slide does not break the whole carousel).
    """
    urls: list[str] = []
    for i, p in enumerate(prompts, 1):
        print(f"   [freepik] Generating carousel image {i}/{len(prompts)}...")
        try:
            result = generate_image(p, api_key=api_key, aspect_ratio=aspect_ratio)
            if result:
                urls.append(result[0])
        except Exception as e:
            print(f"   [freepik] Image {i} failed: {e}")
    return urls
