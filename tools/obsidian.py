import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from config import SAGA_PATH, AETHER_PATH

_console = Console()


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"\n{prompt} [j/n] ").strip().lower()
        return answer in ("j", "ja", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False

class SagaTool:
    def read_context(self) -> str:
        parts = []
        for filename in ("USER.md", "MEMORY.md"):
            path = os.path.join(SAGA_PATH, filename)
            if os.path.exists(path):
                with open(path, "r") as f:
                    parts.append(f.read())
        return "\n\n".join(parts)
    
    def write_session(self, summary: str):
        sessions_dir = os.path.join(SAGA_PATH, "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        path = os.path.join(sessions_dir, f"{timestamp}.md")
        with open(path, "w") as f:
            f.write(f"# Session {timestamp}\n\n{summary}")

class AetherTool:
    def read_note(self, relative_path: str) -> str:
        path = os.path.join(AETHER_PATH, relative_path)
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read()

        # Case-insensitive fallback
        search = relative_path.lower()
        for filename in os.listdir(AETHER_PATH):
            if filename.lower() == search or filename.lower().endswith(search):
                with open(os.path.join(AETHER_PATH, filename), "r") as f:
                    return f.read()
        return ""

    def list_notes(self) -> str:
        files = [f for f in os.listdir(AETHER_PATH) if f.endswith(".md")]
        return "\n".join(sorted(files))

    def write_note(self, relative_path: str, content: str) -> str:
        if not relative_path.endswith(".md"):
            relative_path += ".md"
        path = os.path.join(AETHER_PATH, relative_path)
        exists = os.path.exists(path)
        action = "Overschrijven" if exists else "Aanmaken"

        _console.print(f"\n[bold #C41E3A]Aether — {action}:[/] [#888888]{path}[/#888888]")
        _console.print(Panel(
            Markdown(content),
            title=Text("Inhoud", style="bold #C41E3A"),
            border_style="#3a0a10",
            padding=(1, 2),
        ))

        if not _confirm("Schrijven naar Aether?"):
            return "Geannuleerd."

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Aether note {'bijgewerkt' if exists else 'aangemaakt'}: {relative_path}"
        except Exception as e:
            return f"Fout bij schrijven: {e}"

    def patch_note(self, relative_path: str, old_string: str, new_string: str) -> str:
        if not relative_path.endswith(".md"):
            relative_path += ".md"
        path = os.path.join(AETHER_PATH, relative_path)

        try:
            with open(path, "r", encoding="utf-8") as f:
                original = f.read()
        except FileNotFoundError:
            return f"Note niet gevonden: {relative_path}"

        if old_string not in original:
            return "Tekst niet gevonden in de note."
        if original.count(old_string) > 1:
            return "Tekst komt meerdere keren voor — maak de zoekstring specifieker."

        _console.print(f"\n[bold #C41E3A]Aether patch:[/] [#888888]{relative_path}[/#888888]")
        _console.print(Panel(
            Text(old_string[:400] + ("…" if len(old_string) > 400 else ""), style="#ff6b6b"),
            title=Text("Verwijderen", style="#ff6b6b"), border_style="#3a0a10", padding=(0, 1),
        ))
        _console.print(Panel(
            Text(new_string[:400] + ("…" if len(new_string) > 400 else ""), style="#69db7c"),
            title=Text("Toevoegen", style="#69db7c"), border_style="#3a0a10", padding=(0, 1),
        ))

        if not _confirm("Patch toepassen?"):
            return "Geannuleerd."

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(original.replace(old_string, new_string, 1))
            return f"Note gepatcht: {relative_path}"
        except Exception as e:
            return f"Fout bij schrijven: {e}"