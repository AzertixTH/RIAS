import os
import sys
import time
from rich.console import Console
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from .theme import ASSISTANT_THEME
from .components import MODEL_DISPLAY, _format_tokens
from config import ASSISTANT_NAME, USER_NAME, LLM_BASE_URL
from core.llm import Conversation
from core import background
from core.voice import listen_and_transcribe, speak

console = Console(theme=ASSISTANT_THEME)

PROMPT_STYLE = Style.from_dict({
    "prompt":          "#C41E3A bold",
    "bottom-toolbar":  "bg:#0A0A0B #333333 noreverse",
})

COMMANDS = {
    "/help":    "toon alle commands",
    "/tools":   "toon beschikbare tools",
    "/agents":  "toon agents en status",
    "/memory":  "toon Saga memory",
    "/history": "toon recente berichten  (bv. /history 5)",
    "/reset":   "nieuwe conversatie starten",
    "/clear":   "scherm wissen",
    "/tokens":  "toon token gebruik",
    "/tts":     "spraakuitvoer aan/uitzetten",
}


def print_header():
    console.print()
    name = Text(f"  {ASSISTANT_NAME}", style="bold #C41E3A")
    _provider = "OpenRouter" if not LLM_BASE_URL or "openrouter" in LLM_BASE_URL else "Valhalla"
    rest = Text(f"  v4.0  ·  {MODEL_DISPLAY}  ·  {_provider}", style="#555555")
    console.print(Text.assemble(name, rest))
    from tools.registry import TOOL_SCHEMAS
    tool_count = len(TOOL_SCHEMAS)
    console.print(Text(f"  5 agents · {tool_count} tools · Saga actief", style="#444444"))
    console.print(Text("  Typ /help voor meer info\n", style="#333333"))


def print_user(text: str):
    console.print(Text.assemble(
        Text(f"\n  {USER_NAME.upper()}  ", style="bold #3DB84A"),
        Text(text, style="#D4D4D4"),
    ))


def print_rias(reply: str, tools: list[str]):
    console.rule(Text("  ✦  ", style="#C41E3A"), align="right", style="#2a2a2a")
    console.print()
    if tools:
        tools_line = "  ⟳ " + "  ·  ".join(tools)
        console.print(Text(tools_line, style="dim #555555 italic"))
        console.print()
    console.print(Text(f"  {reply}", style="#D4D4D4"))
    console.print()
    console.rule(Text("  session  ", style="#333333"), align="right", style="#1a1a1a")
    console.print()


def print_error(text: str):
    console.print(Text(f"  fout: {text}", style="bold red"))


def handle_stream(gen) -> tuple[str, list[str]]:
    reply = ""
    tools_used = []
    for kind, data in gen:
        if kind == "tool" and not data.startswith("delegate_"):
            tools_used.append(data)
        elif kind == "reply":
            reply = data
    return reply, tools_used


def handle_stream_live(gen) -> tuple[str, list[str]]:
    import sys
    tools_used = []
    reply_parts = []
    header_printed = False

    for kind, data in gen:
        if kind == "tool" and not data.startswith("delegate_"):
            tools_used.append(data)
        elif kind == "token":
            if not header_printed:
                console.rule(Text("  ✦  ", style="#C41E3A"), align="right", style="#2a2a2a")
                console.print()
                if tools_used:
                    console.print(Text("  ⟳ " + "  ·  ".join(tools_used), style="dim #555555 italic"))
                    console.print()
                sys.stdout.write("  ")
                sys.stdout.flush()
                header_printed = True
            sys.stdout.write(f"\033[38;2;212;212;212m{data}\033[0m")
            sys.stdout.flush()
            reply_parts.append(data)
        elif kind == "reply":
            if not header_printed:
                print_rias(data, tools_used)
            else:
                sys.stdout.write("\n\n")
                sys.stdout.flush()
                console.rule(Text("  session  ", style="#333333"), align="right", style="#1a1a1a")
                console.print()
            return data, tools_used

    return "".join(reply_parts), tools_used


def cmd_help():
    console.print()
    for cmd, desc in COMMANDS.items():
        console.print(Text.assemble(
            Text(f"  {cmd:<12}", style="#C41E3A"),
            Text(f"  {desc}", style="#666666"),
        ))
    console.print()


def cmd_tools():
    from tools.registry import TOOL_SCHEMAS
    console.print()
    names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    for name in names:
        console.print(Text(f"  · {name}", style="#555555"))
    console.print()


def cmd_agents():
    active = {a["name"] for a in background.get_active()}
    agents = [
        ("Kage",     "code agent"),
        ("Echo",     "research agent"),
        ("Loki",     "trading agent"),
        ("Heimdall", "monitor"),
        ("Nami",     "creative"),
    ]
    console.print()
    for name, role in agents:
        spinning = "⟳ " if role in active else "  "
        status = "#C41E3A" if role in active else "#444444"
        console.print(Text.assemble(
            Text(f"  {spinning}{name:<10}", style=status),
            Text(f"  {role}", style="#555555"),
        ))
    console.print()


def cmd_memory():
    from config import SAGA_PATH
    path = os.path.join(SAGA_PATH, "MEMORY.md")
    try:
        with open(path) as f:
            content = f.read()
        console.print()
        console.print(Text(content, style="#888888"))
        console.print()
    except FileNotFoundError:
        console.print(Text("  geen MEMORY.md gevonden", style="#555555"))


def cmd_history(conversation: Conversation, n: int = 6):
    messages = [m for m in conversation.history if m["role"] != "system"]
    recent = messages[-(n * 2):]
    console.print()
    for m in recent:
        role = m["role"]
        content = m.get("content") or ""
        if isinstance(content, list):
            content = next((c["text"] for c in content if c.get("type") == "text"), "")
        snippet = content[:200].replace("\n", " ")
        if len(content) > 200:
            snippet += "…"
        if role == "user":
            console.print(Text.assemble(Text(f"  {USER_NAME.upper()}  ", style="bold #3DB84A"), Text(snippet, style="#666666")))
        elif role == "assistant":
            console.print(Text.assemble(Text(f"  {ASSISTANT_NAME}  ", style="bold #C41E3A"), Text(snippet, style="#666666")))
    console.print()


def cmd_tokens(conversation: Conversation):
    used = conversation.total_tokens
    console.print(Text(f"\n  {_format_tokens(used)} tokens gebruikt\n", style="#555555"))


def run():
    print_header()

    conversation_ref = [Conversation()]
    _tts_ref = [False]

    kb = KeyBindings()

    def voice_trigger(event):
        text = listen_and_transcribe()
        if text:
            event.app.current_buffer.text = text
            event.app.current_buffer.cursor_position = len(text)

    kb.add("c-@")(voice_trigger)
    kb.add("c-space")(voice_trigger)

    completer = WordCompleter(
        list(COMMANDS.keys()),
        pattern=r"^/\S*",
        sentence=True,
    )

    def toolbar():
        used = _format_tokens(conversation_ref[0].total_tokens)
        active = background.get_active()
        agent_str = ""
        if active:
            names = list({a["name"] for a in active})
            agent_str = f" · ⟳ {', '.join(names)}"
        tts_str = " · ● tts" if _tts_ref[0] else ""
        return HTML(f" {MODEL_DISPLAY}{agent_str}{tts_str} · {used} tokens")

    while True:
        for prompt_text, response_q in background.drain_confirms():
            console.print(Text(f"\n  [agent] {prompt_text}", style="#FFB300"))
            try:
                answer = prompt([("class:prompt", "  doorgaan? [j/n] ")], style=PROMPT_STYLE).strip().lower()
                response_q.put(answer in ("j", "ja", "y", "yes"))
            except (EOFError, KeyboardInterrupt):
                response_q.put(False)

        for task in background.drain_results():
            console.print(Text(f"\n  ◆ {task['name']} klaar", style="#5C0F1A"))
            try:
                reply, tools = handle_stream(conversation_ref[0].inject_agent_result(task["name"], task["result"]))
                if reply:
                    print_rias(reply, tools)
            except Exception as e:
                print_error(str(e))

        try:
            user_input = prompt(
                [("class:prompt", "\n  > ")],
                bottom_toolbar=toolbar,
                style=PROMPT_STYLE,
                refresh_interval=1,
                completer=completer,
                complete_while_typing=True,
                reserve_space_for_menu=4,
                key_bindings=kb,
            )
        except (KeyboardInterrupt, EOFError):
            console.print(Text("\n  shutting down.\n", style="#444444"))
            break

        user_input = user_input.strip()

        if user_input.lower() in ("exit", "quit"):
            console.print(Text("\n  shutting down.\n", style="#444444"))
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            parts = user_input[1:].split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "help":
                cmd_help()
            elif cmd == "tools":
                cmd_tools()
            elif cmd == "agents":
                cmd_agents()
            elif cmd == "memory":
                cmd_memory()
            elif cmd == "history":
                try:
                    n = int(arg) if arg else 6
                except ValueError:
                    n = 6
                cmd_history(conversation_ref[0], n)
            elif cmd == "reset":
                conversation_ref[0] = Conversation()
                console.print(Text("\n  conversatie gereset.\n", style="#555555"))
            elif cmd == "clear":
                console.clear()
                print_header()
            elif cmd == "tokens":
                cmd_tokens(conversation_ref[0])
            elif cmd == "tts":
                _tts_ref[0] = not _tts_ref[0]
                status = "aan" if _tts_ref[0] else "uit"
                console.print(Text(f"\n  tts {status}\n", style="#555555"))
            else:
                console.print(Text(f"\n  onbekend commando: /{cmd}  —  /help\n", style="#444444"))
            continue

        print_user(user_input)

        try:
            reply, tools = handle_stream_live(conversation_ref[0].chat_stream(user_input, stream_tokens=True))
                if _tts_ref[0]:
                    try:
                        speak(reply)
                    except Exception as e:
                        print_error(f"tts: {e}")
        except Exception as e:
            print_error(str(e))
            reply = ""
