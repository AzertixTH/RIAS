import os
from config import SAGA_PATH

_SKILLS_DIR = os.path.join(SAGA_PATH, "skills")


def list_skills() -> str:
    try:
        files = [f[:-3] for f in os.listdir(_SKILLS_DIR) if f.endswith(".md")]
        if not files:
            return "Geen skills gevonden."
        return "Beschikbare skills: " + ", ".join(sorted(files))
    except Exception as e:
        return f"Fout: {e}"


def write_skill(name: str, content: str) -> str:
    os.makedirs(_SKILLS_DIR, exist_ok=True)
    path = os.path.join(_SKILLS_DIR, f"{name.lower().replace(' ', '_')}.md")
    if not content.endswith("\n"):
        content += "\n"
    if "[[🛠️ Skills]]" not in content:
        content += "\nLinks: [[🛠️ Skills]]"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Skill '{name}' opgeslagen in {path}"


def load_skill(name: str) -> str:
    path = os.path.join(_SKILLS_DIR, f"{name}.md")
    if not os.path.exists(path):
        # case-insensitive fallback
        try:
            for f in os.listdir(_SKILLS_DIR):
                if f.lower() == f"{name.lower()}.md":
                    path = os.path.join(_SKILLS_DIR, f)
                    break
        except Exception:
            pass
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Skill '{name}' niet gevonden. Gebruik list_skills om beschikbare skills te zien."
    except Exception as e:
        return f"Fout bij laden skill: {e}"
