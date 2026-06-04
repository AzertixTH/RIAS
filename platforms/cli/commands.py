import os
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.markdown import Markdown
from config import SAGA_PATH, ASSISTANT_NAME

_COMMANDS = {
    "help":    "Toon alle beschikbare slash commands",
    "clear":   "Scherm wissen en header opnieuw tonen",
    "agents":  "Toon actieve en recente agent taken",
    "memory":  "Toon Saga long-term memory (MEMORY.md)",
    "history": "Toon de laatste N berichten  (bv. /history 5)",
    "reset":   "Start een nieuwe conversatie (history gewist)",
    "tokens":  "Toon huidig token gebruik",
    "tts":     "Spraakuitvoer aan/uitzetten",
}


def handle(cmd: str, args: str, ctx: dict) -> bool:
    """
    ctx verwacht: console, conversation, print_header, print_rias, background
    Returns True als command afgehandeld, False als onbekend.
    """
    console: Console = ctx["console"]
    conversation     = ctx["conversation"]

    if cmd == "help":
        t = Table.grid(padding=(0, 3))
        t.add_column(style="bold #C41E3A", min_width=12)
        t.add_column(style="#888888")
        for name, desc in _COMMANDS.items():
            t.add_row(f"/{name}", desc)
        console.print(Panel(t, title=Text(" ✦ Commands", style="bold #C41E3A"),
                            title_align="left", border_style="#3a0a10", padding=(1, 2)))
        return True

    if cmd == "clear":
        console.clear()
        ctx["print_header"]()
        console.print()
        return True

    if cmd == "agents":
        from core import background as bg
        active = bg.get_active()
        recent = bg.drain_results()  # peek without consuming — zie note

        lines = Text()
        if active:
            lines.append("Actief:\n", style="bold #C41E3A")
            for a in active:
                lines.append(f"  ⟳ {a['name']}\n", style="#D4D4D4")
        else:
            lines.append("Geen actieve agents.\n", style="#666666")

        console.print(Panel(lines, title=Text(" ✦ Agents", style="bold #C41E3A"),
                            title_align="left", border_style="#3a0a10", padding=(1, 2)))
        return True

    if cmd == "memory":
        path = os.path.join(SAGA_PATH, "MEMORY.md")
        if not os.path.exists(path):
            console.print("[#666666]Geen MEMORY.md gevonden.[/#666666]")
            return True
        with open(path) as f:
            content = f.read()
        console.print(Panel(Markdown(content), title=Text(" ✦ Memory", style="bold #C41E3A"),
                            title_align="left", border_style="#3a0a10", padding=(1, 2)))
        return True

    if cmd == "history":
        try:
            n = int(args) if args.strip() else 6
        except ValueError:
            n = 6
        messages = [m for m in conversation.history if m["role"] != "system"]
        recent = messages[-(n * 2):]
        lines = Text()
        for m in recent:
            role = m["role"]
            content = m.get("content") or ""
            if isinstance(content, list):
                content = next((c["text"] for c in content if c.get("type") == "text"), "")
            if role == "user":
                lines.append(f"YOU  ", style="bold #3DB84A")
            elif role == "assistant":
                lines.append(f"RIAS ", style="bold #C41E3A")
            else:
                continue
            snippet = content[:200].replace("\n", " ")
            if len(content) > 200:
                snippet += "…"
            lines.append(f"{snippet}\n\n", style="#888888")
        console.print(Panel(lines or Text("Geen history.", style="#666666"),
                            title=Text(" ✦ History", style="bold #C41E3A"),
                            title_align="left", border_style="#3a0a10", padding=(1, 2)))
        return True

    if cmd == "reset":
        from core.llm import Conversation
        ctx["conversation_ref"][0] = Conversation()
        console.print(Panel(Text("Conversatie gereset. Nieuwe sessie gestart.", style="#888888"),
                            title=Text(" ✦ Reset", style="bold #C41E3A"),
                            title_align="left", border_style="#3a0a10", padding=(0, 2)))
        return True

    if cmd == "tokens":
        from platforms.cli.components import _format_tokens
        from config import GROQ_DAILY_TOKEN_LIMIT
        used = conversation.total_tokens
        pct = round(used / GROQ_DAILY_TOKEN_LIMIT * 100, 1)
        console.print(Panel(
            Text(f"{_format_tokens(used)} / {_format_tokens(GROQ_DAILY_TOKEN_LIMIT)} tokens gebruikt ({pct}%)",
                 style="#888888"),
            title=Text(" ✦ Tokens", style="bold #C41E3A"),
            title_align="left", border_style="#3a0a10", padding=(0, 2)))
        return True

    if cmd == "tts":
        tts_ref = ctx.get("tts_ref")
        if tts_ref is not None:
            tts_ref[0] = not tts_ref[0]
            status = "aan" if tts_ref[0] else "uit"
            console.print(f"[#666666]TTS {status}[/#666666]")
        return True

    return False
