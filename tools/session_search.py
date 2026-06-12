import os
import subprocess
from config import SAGA_PATH


def session_search(query: str, limit: int = 5) -> str:
    sessions_dir = os.path.join(SAGA_PATH, "sessions")
    if not os.path.isdir(sessions_dir):
        return "Geen sessions directory gevonden."

    try:
        result = subprocess.run(
            ["grep", "-r", "-l", "-i", query, sessions_dir],
            capture_output=True, text=True, timeout=10,
        )
        files = [f for f in result.stdout.strip().split("\n") if f]
        if not files:
            return f"Geen sessies gevonden met '{query}'."

        files = sorted(files, reverse=True)[:limit]
        parts = []
        for filepath in files:
            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                matches = [l.strip() for l in content.split("\n") if query.lower() in l.lower()]
                filename = os.path.basename(filepath)
                excerpt = "\n".join(matches[:5])
                parts.append(f"**{filename}**\n{excerpt}")
            except Exception:
                continue

        return "\n\n---\n\n".join(parts) if parts else "Geen leesbare resultaten."
    except subprocess.TimeoutExpired:
        return "Timeout bij zoeken."
    except Exception as e:
        return f"Fout: {e}"
