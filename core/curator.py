import os
import threading
from openai import OpenAI
from dotenv import load_dotenv
from config import SAGA_PATH, CURATOR_MODEL, USER_NAME, ASSISTANT_NAME

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

CURATOR_PROMPT = f"""You are a memory curator for {ASSISTANT_NAME}, an AI assistant.

You receive one exchange between {USER_NAME} and {ASSISTANT_NAME}.
Your task: extract explicit atomic conclusions — not raw facts, but derived insights.

Long-term memory files:
- USER.md: who {USER_NAME} is — behavioral patterns, implicit preferences, communication style, emotional signals
- MEMORY.md: project decisions, environment facts, technical context

The difference between a fact and a conclusion:
- Fact: "User has two dogs"
- Conclusion: "User assigns high emotional value to their pets — they appear in casual context as a priority"

Rules:
- FIRST read current memory. If already captured in any form, respond NOTHING.
- Extract conclusions, not just stated facts. Look for implicit signals in how {USER_NAME} communicates.
- Only save durable patterns — not one-off observations, not temporary state, not secrets.
- One or two bullet points max. Self-contained sentences that make sense without context.
- If nothing worth saving, respond exactly: NOTHING
- Otherwise use this format:
FILE: USER.md or MEMORY.md
SECTION: section header
CONTENT: the conclusion (one or two bullet points)

Current memory:
{{current_memory}}

Exchange:
User: {{user_message}}
{ASSISTANT_NAME}: {{assistant_reply}}"""


def _curate(user_message: str, assistant_reply: str):
    parts = []
    for filename in ("USER.md", "MEMORY.md"):
        path = os.path.join(SAGA_PATH, filename)
        if os.path.exists(path):
            with open(path, "r") as f:
                parts.append(f"=== {filename} ===\n{f.read()}")

    current_memory = "\n\n".join(parts)

    try:
        response = _client.chat.completions.create(
            model=CURATOR_MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": CURATOR_PROMPT.format(
                user_message=user_message,
                assistant_reply=assistant_reply,
                current_memory=current_memory
            )}]
        )
    except Exception:
        return

    result = response.choices[0].message.content.strip()
    if result == "NOTHING":
        return

    file_name, section, content = None, None, []
    mode = None

    for line in result.split("\n"):
        if line.startswith("FILE:"):
            if file_name is not None:
                break  # tweede FILE: blok — model herhaalt zich, eerste blok is compleet
            file_name = line.replace("FILE:", "").strip()
        elif line.startswith("SECTION:"):
            if section is not None:
                break
            section = line.replace("SECTION:", "").strip()
        elif line.startswith("CONTENT:"):
            if mode == "content":
                break
            mode = "content"
            first = line.replace("CONTENT:", "").strip()
            if first:
                content.append(first)
        elif mode == "content":
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.startswith(("-", "*")):
                break  # geen bullet meer — model is terug aan het redeneren
            content.append(line)

    if not file_name or not content:
        return

    path = os.path.join(SAGA_PATH, file_name)
    if not os.path.exists(path):
        return

    with open(path, "r") as f:
        existing = f.read()

    # Sla over als de kern van de content al in het bestand staat
    new_text = "\n".join(content).strip()
    key_phrases = [line.strip("- *").strip() for line in new_text.splitlines() if len(line.strip()) > 20]
    if any(phrase.lower() in existing.lower() for phrase in key_phrases):
        return

    section_header = f"## {section}"
    if section_header in existing:
        # Sectie bestaat — voeg toe aan bestaande sectie
        lines = existing.split("\n")
        new_lines = []
        i = 0
        while i < len(lines):
            new_lines.append(lines[i])
            if lines[i].strip() == section_header:
                # Zoek einde van sectie (volgende ## of einde bestand)
                i += 1
                while i < len(lines) and not lines[i].startswith("## "):
                    new_lines.append(lines[i])
                    i += 1
                new_lines.append(new_text)
                continue
            i += 1
        with open(path, "w") as f:
            f.write("\n".join(new_lines))
    else:
        # Nieuwe sectie — append
        with open(path, "a") as f:
            f.write(f"\n\n{section_header}\n{new_text}")


def curate_async(user_message: str, assistant_reply: str):
    thread = threading.Thread(
        target=_curate,
        args=(user_message, assistant_reply),
        daemon=True
    )
    thread.start()
