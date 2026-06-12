import os
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax

_console = Console()

_ALLOWED_ROOTS = (
    os.path.expanduser("~/Dev"),
    os.path.expanduser("~/Obsidian"),
)


def _is_allowed(path: str) -> bool:
    abs_path = os.path.realpath(path)
    return any(abs_path.startswith(root) for root in _ALLOWED_ROOTS)


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"\n{prompt} [j/n] ").strip().lower()
        return answer in ("j", "ja", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def _show_preview(title: str, content: str, lexer: str = "text"):
    preview = content if len(content) <= 800 else content[:800] + "\n…"
    try:
        _console.print(Panel(
            Syntax(preview, lexer, theme="monokai", line_numbers=False),
            title=Text(title, style="bold #C41E3A"),
            border_style="#5C0F1A",
            padding=(0, 1),
        ))
    except Exception:
        _console.print(Panel(preview, title=title, border_style="#5C0F1A"))


def read_file(path: str) -> str:
    abs_path = os.path.abspath(path)
    if not _is_allowed(abs_path):
        return f"Geblokkeerd: {abs_path} valt buiten ~/Dev en ~/Obsidian"
    try:
        with open(abs_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Fout bij lezen: {e}"


def list_dir(path: str) -> str:
    abs_path = os.path.abspath(path)
    if not _is_allowed(abs_path):
        return f"Geblokkeerd: {abs_path} valt buiten ~/Dev en ~/Obsidian"
    try:
        entries = sorted(os.listdir(abs_path))
        lines = []
        for e in entries:
            full = os.path.join(abs_path, e)
            lines.append(f"{'📁' if os.path.isdir(full) else '📄'} {e}")
        return "\n".join(lines)
    except Exception as e:
        return f"Fout bij lezen: {e}"


def write_file(path: str, content: str) -> str:
    abs_path = os.path.abspath(path)
    if not _is_allowed(abs_path):
        return f"Geblokkeerd: {abs_path} valt buiten ~/Dev en ~/Obsidian"
    exists = os.path.exists(abs_path)
    action = "Overschrijven" if exists else "Aanmaken"

    _console.print(f"\n[bold #C41E3A]write_file[/] — {action}: [#888888]{abs_path}[/#888888]")
    ext = os.path.splitext(path)[1].lstrip(".") or "text"
    _show_preview("Inhoud", content, lexer=ext)

    if not _confirm("Doorgaan?"):
        return "Geannuleerd."

    try:
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Geschreven: {abs_path}"
    except Exception as e:
        return f"Fout bij schrijven: {e}"


def patch_file(path: str, old_string: str, new_string: str) -> str:
    abs_path = os.path.abspath(path)
    if not _is_allowed(abs_path):
        return f"Geblokkeerd: {abs_path} valt buiten ~/Dev en ~/Obsidian"

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            original = f.read()
    except FileNotFoundError:
        return f"Bestand niet gevonden: {abs_path}"
    except Exception as e:
        return f"Fout bij lezen: {e}"

    if old_string not in original:
        return f"Tekst niet gevonden in {abs_path}."

    count = original.count(old_string)
    if count > 1:
        return f"Tekst komt {count}x voor — maak de zoekstring specifieker zodat hij uniek is."

    _console.print(f"\n[bold #C41E3A]patch_file[/] — [#888888]{abs_path}[/#888888]")
    _console.print(Panel(
        Text(old_string[:600] + ("…" if len(old_string) > 600 else ""), style="#ff6b6b"),
        title=Text("Verwijderen", style="#ff6b6b"),
        border_style="#5C0F1A",
        padding=(0, 1),
    ))
    _console.print(Panel(
        Text(new_string[:600] + ("…" if len(new_string) > 600 else ""), style="#69db7c"),
        title=Text("Toevoegen", style="#69db7c"),
        border_style="#5C0F1A",
        padding=(0, 1),
    ))

    if not _confirm("Patch toepassen?"):
        return "Geannuleerd."

    try:
        patched = original.replace(old_string, new_string, 1)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(patched)
        return f"Patch toegepast: {abs_path}"
    except Exception as e:
        return f"Fout bij schrijven: {e}"


_SEARCH_EXTENSIONS = (
    "*.py", "*.md", "*.txt", "*.json", "*.ts", "*.tsx",
    "*.js", "*.jsx", "*.html", "*.css", "*.yaml", "*.toml",
)


def search_files(query: str, path: str = None, mode: str = "content") -> str:
    base = os.path.realpath(os.path.expanduser(path or "~/Dev"))
    if not any(base.startswith(os.path.expanduser(r)) for r in ("~/Dev", "~/Obsidian")):
        return "Geblokkeerd: valt buiten ~/Dev en ~/Obsidian"

    try:
        if mode == "name":
            result = subprocess.run(
                ["find", base, "-name", f"*{query}*",
                 "-not", "-path", "*/__pycache__/*",
                 "-not", "-path", "*/.git/*"],
                capture_output=True, text=True, timeout=15,
            )
        else:
            include_args = []
            for ext in _SEARCH_EXTENSIONS:
                include_args += ["--include", ext]
            result = subprocess.run(
                ["grep", "-r", "-l", "-I", query, base] + include_args,
                capture_output=True, text=True, timeout=15,
            )

        lines = [l for l in result.stdout.strip().split("\n") if l]
        if not lines:
            return "Geen resultaten gevonden."
        if len(lines) > 50:
            lines = lines[:50] + [f"... ({len(lines) - 50} meer resultaten)"]
        return "\n".join(lines)
    except subprocess.TimeoutExpired:
        return "Timeout bij zoeken."
    except Exception as e:
        return f"Fout: {e}"
