import os
from datetime import datetime, timezone

_SAGA_TRADING = os.path.expanduser("~/Obsidian/Saga/trading")
_PREDICTIONS = os.path.join(_SAGA_TRADING, "predictions.md")
_PERFORMANCE = os.path.join(_SAGA_TRADING, "performance.md")


def _ensure_dir():
    os.makedirs(_SAGA_TRADING, exist_ok=True)


def log_signal(
    symbol: str,
    interval: str,
    direction: str,
    horizon: str,
    confidence: str,
    reasoning: str,
    indicators: str,
) -> str:
    _ensure_dir()
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")

    entry = (
        f"\n## {timestamp} — {symbol} {interval}\n"
        f"**Richting:** {direction}  \n"
        f"**Horizon:** {horizon}  \n"
        f"**Confidence:** {confidence}  \n"
        f"**Redenering:** {reasoning}  \n"
        f"\n**Indicatoren:**\n{indicators}\n"
        f"\n---\n"
    )

    if not os.path.exists(_PREDICTIONS):
        with open(_PREDICTIONS, "w") as f:
            f.write("# Trading Predictions Log\n")

    with open(_PREDICTIONS, "a") as f:
        f.write(entry)

    return f"Signaal gelogd: {symbol} {direction} ({horizon}, {confidence}) — {timestamp}"


def read_recent_signals(n: int = 10) -> str:
    if not os.path.exists(_PREDICTIONS):
        return "Geen signalen gelogd."
    with open(_PREDICTIONS, "r") as f:
        content = f.read()
    sections = [s.strip() for s in content.split("---") if s.strip() and not s.strip().startswith("#")]
    recent = sections[-n:] if len(sections) >= n else sections
    return "\n\n---\n\n".join(recent) if recent else "Geen signalen gevonden."
