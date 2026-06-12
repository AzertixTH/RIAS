import os
import subprocess
import time
from tools.project import get_project
from config import ASSISTANT_NAME

_SESSION = f"{ASSISTANT_NAME.lower()}-claude"


def _ensure_session() -> None:
    cwd = get_project() or os.path.expanduser("~/Dev")
    existing = subprocess.run(
        ["tmux", "has-session", "-t", _SESSION],
        capture_output=True
    )
    if existing.returncode != 0:
        subprocess.run(["tmux", "new-session", "-d", "-s", _SESSION, "-c", cwd])
        subprocess.run(["tmux", "send-keys", "-t", _SESSION, "claude", "Enter"])
        time.sleep(2)


def open_claude() -> str:
    _ensure_session()

    terminals = [
        ["gnome-terminal", "--window", "--", "tmux", "attach", "-t", _SESSION],
        ["kitty", "-e", "tmux", "attach", "-t", _SESSION],
        ["alacritty", "-e", "tmux", "attach", "-t", _SESSION],
        ["xterm", "-e", f"tmux attach -t {_SESSION}"],
    ]
    for cmd in terminals:
        try:
            subprocess.Popen(cmd)
            return f"Claude geopend in nieuw venster. Sessie: {_SESSION}."
        except FileNotFoundError:
            continue

    return "Claude sessie actief (geen terminal gevonden om te openen)."


def send_to_claude(message: str) -> str:
    _ensure_session()
    subprocess.run(["tmux", "send-keys", "-t", _SESSION, message, "Enter"])
    return f"Verstuurd naar Claude: {message}"


def read_claude_output(lines: int = 50) -> str:
    status = subprocess.run(
        ["tmux", "has-session", "-t", _SESSION],
        capture_output=True
    )
    if status.returncode != 0:
        return "Geen actieve Claude sessie."

    result = subprocess.run(
        ["tmux", "capture-pane", "-t", _SESSION, "-p", "-S", f"-{lines}"],
        capture_output=True, text=True
    )
    return result.stdout.strip() or "(leeg)"


def stop_claude() -> str:
    result = subprocess.run(
        ["tmux", "kill-session", "-t", _SESSION],
        capture_output=True
    )
    if result.returncode == 0:
        return "Claude sessie gestopt."
    return "Geen actieve Claude sessie."
