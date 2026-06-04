"""
Deriver — periodieke patroon analyse geïnspireerd op Honcho.

Werkt anders dan de Curator:
- Curator: na elke exchange, één feit/conclusie
- Deriver: elke N sessies, analyseert batch van recente logs, extraheert patronen

Output: Saga/INSIGHTS.md — patronen en gedragsconlusies die de Curator mist
        omdat die per exchange werkt zonder bredere context.
"""

import os
import threading
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from config import SAGA_PATH, CURATOR_MODEL, USER_NAME, ASSISTANT_NAME

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

_INSIGHTS_PATH = os.path.join(SAGA_PATH, "INSIGHTS.md")
_SESSIONS_DIR  = os.path.join(SAGA_PATH, "sessions")
_SESSIONS_SINCE_LAST = 0
_DERIVE_EVERY = 5  # elke 5 sessies
_lock = threading.Lock()


DERIVER_PROMPT = f"""You are a behavioral pattern analyst for {ASSISTANT_NAME}, an AI assistant.

You receive a batch of recent conversation sessions between {USER_NAME} and {ASSISTANT_NAME}.
Your task: identify recurring patterns, implicit preferences, and behavioral insights
that only become visible across multiple conversations — not in a single exchange.

Look for:
- Recurring topics or concerns that suggest underlying priorities
- Communication patterns (how does {USER_NAME} ask for things, what frustrates him)
- Implicit preferences revealed by repeated choices
- Contradictions or shifts in behavior over time
- What {USER_NAME} avoids mentioning but keeps returning to

Output format — structured markdown sections:
## Behavioral Patterns
- [pattern with reasoning]

## Implicit Preferences
- [preference inferred from behavior, not stated directly]

## Communication Style
- [how he communicates, what works]

## Shifts / Contradictions
- [anything that changed or seems inconsistent]

Only include sections with genuine findings. If a section has nothing, omit it.
Be specific and concrete. No generic observations.

Sessions:
{{sessions}}"""


def _load_recent_sessions(n: int = 10) -> str:
    try:
        files = sorted([
            f for f in os.listdir(_SESSIONS_DIR)
            if f.endswith(".md") and not f.startswith("recap_")
        ])[-n:]
        parts = []
        for fname in files:
            path = os.path.join(_SESSIONS_DIR, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            parts.append(f"=== {fname} ===\n{content[:2000]}")
        return "\n\n".join(parts)
    except Exception:
        return ""


def _load_existing_insights() -> str:
    if not os.path.exists(_INSIGHTS_PATH):
        return ""
    with open(_INSIGHTS_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _run_deriver():
    sessions_text = _load_recent_sessions(10)
    if not sessions_text:
        return

    try:
        response = _client.chat.completions.create(
            model=CURATOR_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": DERIVER_PROMPT.format(
                sessions=sessions_text
            )}]
        )
    except Exception:
        return

    insights = response.choices[0].message.content.strip()
    if not insights or len(insights) < 50:
        return

    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n\n---\n_Analyse: {date}_\n\n{insights}"

    with open(_INSIGHTS_PATH, "a", encoding="utf-8") as f:
        if not os.path.exists(_INSIGHTS_PATH) or os.path.getsize(_INSIGHTS_PATH) == 0:
            f.write(f"# INSIGHTS\n\nPatroon analyses gegenereerd door de Deriver.\n")
        f.write(entry)


def tick():
    """Roep aan na elke sessie. Triggert deriver elke DERIVE_EVERY sessies."""
    global _SESSIONS_SINCE_LAST
    with _lock:
        _SESSIONS_SINCE_LAST += 1
        should_run = _SESSIONS_SINCE_LAST >= _DERIVE_EVERY
        if should_run:
            _SESSIONS_SINCE_LAST = 0

    if should_run:
        threading.Thread(target=_run_deriver, daemon=True).start()


def run_now():
    """Forceer een deriver run — voor /derive CLI commando."""
    threading.Thread(target=_run_deriver, daemon=True).start()
    return "Deriver gestart — analyseert recente sessies op de achtergrond."
