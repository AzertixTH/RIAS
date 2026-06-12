import os
import urllib.request
import urllib.error
import sqlite3

from config import SAGA_PATH, AETHER_PATH, MAIN_MODEL, CODE_MODEL, CURATOR_MODEL, ASSISTANT_NAME


def _ok(msg):  return f"  ✓  {msg}"
def _warn(msg): return f"  ⚠  {msg}"
def _fail(msg): return f"  ✗  {msg}"


def _check_env() -> list[str]:
    lines = ["ENV & CONFIG"]
    key = os.getenv("OPENROUTER_API_KEY", "")
    if key:
        lines.append(_ok(f"OPENROUTER_API_KEY aanwezig ({key[:8]}…)"))
    else:
        lines.append(_fail("OPENROUTER_API_KEY ontbreekt — stel in in .env"))

    lines.append(_ok(f"MAIN_MODEL: {MAIN_MODEL}"))
    lines.append(_ok(f"CODE_MODEL: {CODE_MODEL}"))
    lines.append(_ok(f"CURATOR_MODEL: {CURATOR_MODEL}"))
    return lines


def _check_saga() -> list[str]:
    lines = ["SAGA MEMORY"]
    for filename in ("USER.md", "MEMORY.md"):
        path = os.path.join(SAGA_PATH, filename)
        if os.path.exists(path):
            size = os.path.getsize(path)
            lines.append(_ok(f"{filename} ({size} bytes)"))
        else:
            lines.append(_fail(f"{filename} niet gevonden in {SAGA_PATH}"))

    sessions = os.path.join(SAGA_PATH, "sessions")
    count = len(os.listdir(sessions)) if os.path.isdir(sessions) else 0
    lines.append(_ok(f"sessions/ — {count} bestanden"))

    trading_db = os.path.join(SAGA_PATH, "trading", "signals.db")
    if os.path.exists(trading_db):
        try:
            con = sqlite3.connect(trading_db)
            (n,) = con.execute("SELECT COUNT(*) FROM signals").fetchone()
            con.close()
            lines.append(_ok(f"trading/signals.db — {n} signals"))
        except Exception as e:
            lines.append(_warn(f"trading/signals.db — {e}"))
    else:
        lines.append(_warn("trading/signals.db niet gevonden"))
    return lines


def _check_aether() -> list[str]:
    lines = ["AETHER VAULT"]
    if os.path.isdir(AETHER_PATH):
        count = len([f for f in os.listdir(AETHER_PATH) if f.endswith(".md")])
        lines.append(_ok(f"{AETHER_PATH} — {count} notes"))
    else:
        lines.append(_fail(f"Aether niet gevonden op {AETHER_PATH}"))
    return lines


def _check_browser() -> list[str]:
    lines = ["BROWSER"]
    profile = os.path.expanduser(f"~/.{ASSISTANT_NAME.lower()}/chromium-profile")
    if os.path.isdir(profile):
        lines.append(_ok(f"Chromium profiel aanwezig"))
    else:
        lines.append(_warn("Chromium profiel nog niet aangemaakt — opent automatisch bij eerste gebruik"))
    try:
        import playwright  # noqa
        lines.append(_ok("Playwright geïnstalleerd"))
    except ImportError:
        lines.append(_fail("Playwright niet geïnstalleerd — pip install playwright"))
    return lines


def _check_sentinel() -> list[str]:
    lines = ["SENTINEL"]
    try:
        urllib.request.urlopen("http://127.0.0.1:5731/state", timeout=2)
        lines.append(_ok("Sentinel draait op http://127.0.0.1:5731"))
    except Exception:
        lines.append(_warn("Sentinel niet bereikbaar — start met: cd ~/Dev/Sentinel && python server.py"))
    return lines


def _check_openrouter() -> list[str]:
    lines = ["OPENROUTER API"]
    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        lines.append(_fail("Geen API key — kan niet testen"))
        return lines
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status == 200:
                lines.append(_ok("OpenRouter bereikbaar en key geldig"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            lines.append(_fail("OpenRouter API key ongeldig"))
        else:
            lines.append(_warn(f"OpenRouter HTTP {e.code}"))
    except Exception as e:
        lines.append(_warn(f"OpenRouter niet bereikbaar: {e}"))
    return lines


def _check_ollama() -> list[str]:
    lines = ["OLLAMA (lokaal model)"]
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        lines.append(_ok("Ollama draait op localhost:11434"))
    except Exception:
        lines.append(_warn("Ollama niet actief — niet vereist voor cloud modus"))
    return lines


def run_doctor() -> str:
    sections = [
        _check_env(),
        _check_saga(),
        _check_aether(),
        _check_browser(),
        _check_sentinel(),
        _check_openrouter(),
        _check_ollama(),
    ]

    lines = ["RIAS DOCTOR", ""]
    for section in sections:
        lines.append(section[0])
        lines.extend(section[1:])
        lines.append("")

    ok    = sum(1 for s in sections for l in s[1:] if l.startswith("  ✓"))
    warns = sum(1 for s in sections for l in s[1:] if l.startswith("  ⚠"))
    fails = sum(1 for s in sections for l in s[1:] if l.startswith("  ✗"))

    lines.append(f"  {ok} ok  ·  {warns} waarschuwingen  ·  {fails} fouten")
    return "\n".join(lines)
