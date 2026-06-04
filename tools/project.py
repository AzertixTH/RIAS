import os
from config import ASSISTANT_NAME

_PROJECT_FILE = f"{ASSISTANT_NAME}.md"
_current_path: str | None = None


def get_project() -> str | None:
    return _current_path


def set_project(path: str) -> str:
    global _current_path
    path = os.path.expanduser(path)

    if not os.path.isdir(path):
        return f"Map niet gevonden: {path}"

    _current_path = path
    md_path = os.path.join(path, _PROJECT_FILE)

    if not os.path.exists(md_path):
        _create_template(path, md_path)
        return f"Project ingesteld op {path}\n{_PROJECT_FILE} aangemaakt — vul aan met project context."

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    return f"Project ingesteld op {path}\n\n--- {_PROJECT_FILE} ---\n{content}"


def read_project_context() -> str | None:
    if not _current_path:
        return None
    md_path = os.path.join(_current_path, _PROJECT_FILE)
    if not os.path.exists(md_path):
        return None
    with open(md_path, "r", encoding="utf-8") as f:
        return f.read()


def update_project_file(content: str) -> str:
    if not _current_path:
        return "Geen actief project — gebruik set_project eerst."
    md_path = os.path.join(_current_path, _PROJECT_FILE)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"{_PROJECT_FILE} bijgewerkt in {_current_path}"


def _create_template(path: str, md_path: str):
    project_name = os.path.basename(path)
    template = f"""# {project_name}

## Wat is dit project
<!-- Korte omschrijving -->

## Stack
<!-- Talen, frameworks, libraries -->

## Mapstructuur
<!-- Belangrijkste bestanden/mappen -->

## Status
<!-- Wat werkt, wat niet, wat in progress -->

## Conventies
<!-- Code stijl, naamgeving, architectuur keuzes -->

## Aandachtspunten
<!-- Bekende bugs, limitaties, TODO's -->
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(template)
