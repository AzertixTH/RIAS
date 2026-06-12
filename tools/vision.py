import re
import base64
import os

_IMAGE_EXTENSIONS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

_EXT = '|'.join(re.escape(e) for e in _IMAGE_EXTENSIONS)
_PATH_PATTERN = re.compile(
    r"""['"]((/[^'"]+(?:""" + _EXT + r""")))['"]|(/\S+(?:""" + _EXT + r"""))""",
    re.IGNORECASE
)


def _encode(path: str) -> tuple[str, str] | None:
    ext = os.path.splitext(path)[1].lower()
    mime = _IMAGE_EXTENSIONS.get(ext)
    if not mime or not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return mime, data


def vision_analyze(source: str, prompt: str = "Beschrijf wat je ziet.") -> str:
    import os
    from openai import OpenAI
    from config import LLM_API_KEY, LLM_BASE_URL, MAIN_MODEL

    if source.startswith("http://") or source.startswith("https://"):
        image_block = {"type": "image_url", "image_url": {"url": source}}
    else:
        encoded = _encode(source)
        if not encoded:
            return f"Kon afbeelding niet lezen: {source}"
        mime, data = encoded
        image_block = {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}

    try:
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        response = client.chat.completions.create(
            model=MAIN_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    image_block,
                ]
            }]
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"Vision analyse mislukt: {e}"


def build_content(text: str) -> str | list:
    paths = [g for m in _PATH_PATTERN.finditer(text) for g in (m.group(1) or m.group(3),) if g]
    images = []
    clean_text = text

    for path in paths:
        encoded = _encode(path)
        if encoded:
            mime, data = encoded
            images.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{data}"}
            })
            clean_text = re.sub(r"""['"]?""" + re.escape(path) + r"""['"]?""", "", clean_text).strip()

    if not images:
        return text

    content = []
    if clean_text:
        content.append({"type": "text", "text": clean_text})
    content.extend(images)
    return content
