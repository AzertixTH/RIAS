from rich.console import Console
from rich.text import Text
from .theme import ASSISTANT_THEME
from config import MAIN_MODEL

console = Console(theme=ASSISTANT_THEME)

MODEL_DISPLAY = MAIN_MODEL.split("/")[-1]


def _format_elapsed(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _format_tokens(tokens: int) -> str:
    if tokens >= 1000:
        return f"{tokens / 1000:.1f}K"
    return str(tokens)


def print_status_bar(total_tokens: int, elapsed_seconds: int):
    used_str = _format_tokens(total_tokens)
    time_str = _format_elapsed(elapsed_seconds)

    bar = Text()
    bar.append(f" {MODEL_DISPLAY} ", style="#5C0F1A")
    bar.append("│ ", style="#2a2a2a")
    bar.append(f"{used_str} tokens ", style="#4a4a4a")
    bar.append("│ ", style="#2a2a2a")
    bar.append(f"{time_str} ", style="#4a4a4a")

    console.rule(bar, style="#3a0a10")
