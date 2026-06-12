import pyfiglet
from textual.app import App, ComposeResult
from textual.widgets import TextArea, RichLog, Static, Footer
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.message import Message
from textual import work, events
from rich.text import Text
from rich.markdown import Markdown
from rich.console import Group

from config import ASSISTANT_NAME, ASSISTANT_SUBTITLE, MAIN_MODEL, USER_NAME
from core.llm import Conversation
from core import background
from core.voice import listen_and_transcribe, speak

MODEL_DISPLAY = MAIN_MODEL.split("/")[-1]

_TOOL_LABELS = {
    "web_search":              "searching the web...",
    "run_shell":               "running shell command...",
    "read_aether":             "reading Aether...",
    "list_aether":             "listing Aether...",
    "write_file":              "writing file...",
    "patch_file":              "patching file...",
    "read_file":               "reading file...",
    "list_dir":                "listing directory...",
    "delegate_code":           "delegating → Kage...",
    "delegate_research":       "delegating → Echo...",
    "delegate_trading":        "delegating → Loki...",
    "discord_list_channels":   "listing Discord channels...",
    "discord_send_to_channel": "sending Discord message...",
    "list_skills":             "listing skills...",
    "load_skill":              "loading skill...",
    "trading_accuracy":        "checking Loki accuracy...",
    "trading_recent":          "reading Loki signals...",
}


class Header(Static):
    DEFAULT_CSS = """
    Header {
        height: auto;
        border-bottom: solid #3a0a10;
        padding: 1 3 0 3;
    }
    """

    def render(self) -> Text:
        try:
            fig = pyfiglet.figlet_format(ASSISTANT_NAME, font="colossal").rstrip()
        except Exception:
            fig = ASSISTANT_NAME

        t = Text()
        for line in fig.split("\n"):
            t.append(line + "\n", style="#C41E3A")
        t.append(f"\n  {ASSISTANT_SUBTITLE}\n", style="#555555")
        return t


class Sidebar(Vertical):
    DEFAULT_CSS = """
    Sidebar {
        width: 22;
        border-right: solid #3a0a10;
    }
    """


class SidebarInfo(Static):
    DEFAULT_CSS = """
    SidebarInfo {
        padding: 1 2;
    }
    """

    _AGENTS = [
        ("Kage",     "Code Agent",     "#A8A8A8"),  # zilver
        ("Echo",     "Research Agent", "#38BDF8"),  # licht blauw
        ("Loki",     "Trading Agent",  "#F59E0B"),  # goud
        ("Heimdall", "Monitor",        "#9B59B6"),  # paars
        ("Nami",     "Creative",       "#F97316"),  # oranje
    ]

    def render(self) -> Text:
        t = Text()

        t.append("MODEL\n", style="#666666")
        t.append(f"{MODEL_DISPLAY}\n\n", style="#C41E3A")

        t.append("AGENTS\n", style="#666666")
        active_names = {a["name"] for a in background.get_active()}
        for agent, bg_name, color in self._AGENTS:
            if bg_name in active_names:
                t.append(f"⟳ {agent}\n", style=f"bold {color}")
            else:
                t.append(f"  {agent}\n", style=color)

        t.append("\nTOOLS\n", style="#666666")
        for tool in ("web_search", "run_shell", "read_aether", "write_file", "delegate_*", "trading_*"):
            t.append(f"· {tool}\n", style="#555555")

        return t


class ChatLog(RichLog):
    DEFAULT_CSS = """
    ChatLog {
        scrollbar-color: #3a0a10;
        padding: 0 2;
        height: 1fr;
    }
    """


class StatusBar(Static):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        border-top: solid #3a0a10;
        padding: 0 2;
    }
    """

    def render(self) -> Text:
        app = self.app
        tokens = app.conversation.total_tokens if hasattr(app, "conversation") else 0
        tk = f"{tokens / 1000:.1f}K" if tokens >= 1000 else str(tokens)
        active = background.get_active()

        t = Text()
        t.append(f"{MODEL_DISPLAY}", style="#C41E3A")
        t.append("  ·  ", style="#555555")
        t.append(f"{tk} tokens", style="#666666")

        if active:
            t.append("  ·  ", style="#555555")
            for a in active:
                t.append(f"⟳ {a['name']}", style="#C41E3A")
                t.append("  ", "")

        t.append("    ← agents  ctrl+a  ", style="#444444")
        return t



class ChatInput(TextArea):
    DEFAULT_CSS = """
    ChatInput {
        border: solid #3a0a10;
        color: #D4D4D4;
        padding: 0 1;
        min-height: 3;
        max-height: 8;
        height: auto;
    }
    ChatInput:focus {
        border: solid #C41E3A;
    }
    ChatInput .text-area--cursor {
        color: #C41E3A;
    }
    """

    class Submitted(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.prevent_default()
            text = self.text.strip()
            if text:
                self.post_message(self.Submitted(text))
                self.load_text("")
            return
        if event.key == "left" and not self.text.strip():
            event.prevent_default()
            self.app.action_toggle_sidebar()
            return
        super()._on_key(event)


class RIASApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    #main {
        layout: horizontal;
        height: 1fr;
    }

    #chat-col {
        layout: vertical;
        height: 1fr;
    }

    Footer {
        color: #555555;
    }

    Footer > .footer--key {
        background: #3a0a10;
        color: #C41E3A;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+a", "toggle_sidebar", "Agents"),
        Binding("ctrl+r", "reset_conv", "Reset"),
        Binding("ctrl+space", "voice_input", "Voice"),
        Binding("escape", "focus_input", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.conversation = Conversation()
        self._sidebar_visible = True
        self._tts_enabled = False

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main"):
            with Sidebar(id="sidebar"):
                yield SidebarInfo(id="sidebar-info")

            with Vertical(id="chat-col"):
                yield ChatLog(id="chat", wrap=True, highlight=True, markup=True)
                yield StatusBar(id="status")
                yield ChatInput(id="input")

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#input", ChatInput).focus()
        self.query_one("#chat", ChatLog).write(
            Text.assemble(
                ("\n  ✦ ", "#C41E3A"),
                (ASSISTANT_NAME, "bold #C41E3A"),
                (" klaar.\n", "#666666"),
            )
        )
        self.set_interval(2.0, self._tick)

    def _tick(self) -> None:
        self.query_one("#status", StatusBar).refresh()
        self.query_one("#sidebar-info", SidebarInfo).refresh()
        self._drain_agent_results()

    def _drain_agent_results(self) -> None:
        for task in background.drain_results():
            self.query_one("#chat", ChatLog).write(
                Text(f"\n  ◆ {task['name']} klaar\n", style="#5C0F1A")
            )
            self.run_worker(
                self._inject_result(task["name"], task["result"]),
                exclusive=False,
            )

    async def _inject_result(self, name: str, result: str) -> None:
        reply = ""
        for kind, data in self.conversation.inject_agent_result(name, result):
            if kind == "reply":
                reply = data
        if reply:
            self._write_reply(reply, via=name)

    def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        user_input = event.text.strip()
        if not user_input:
            return

        if user_input.lower() in ("exit", "quit"):
            self.exit()
            return

        self.query_one("#chat", ChatLog).write(
            Text.assemble(
                (f"\n  {USER_NAME.upper()}  ", "bold #3DB84A"),
                (user_input, "#D4D4D4"),
                ("\n", ""),
            )
        )

        if user_input.startswith("/"):
            self._run_command(user_input[1:])
            return

        inp = self.query_one("#input", ChatInput)
        inp.disabled = True
        self._stream_chat(user_input)

    @work(thread=True)
    def _stream_chat(self, user_input: str) -> None:
        self.call_from_thread(self._write_thinking)
        try:
            reply = ""
            for kind, data in self.conversation.chat_stream(user_input):
                if kind == "tool":
                    label = _TOOL_LABELS.get(data, f"{data}...")
                    self.call_from_thread(self._write_tool, label)
                elif kind == "reply":
                    reply = data
            self.call_from_thread(self._write_reply, reply)
            if self._tts_enabled and reply:
                try:
                    speak(reply)
                except Exception as e:
                    self.call_from_thread(self._write_error, f"TTS: {e}")
        except Exception as e:
            self.call_from_thread(self._write_error, str(e))
        finally:
            self.call_from_thread(self._unlock_input)

    def _write_thinking(self) -> None:
        self.query_one("#chat", ChatLog).write(
            Text("  ✦ thinking...", style="italic #555555")
        )

    def _write_tool(self, label: str) -> None:
        self.query_one("#chat", ChatLog).write(
            Text.assemble(("  ⟳ ", "#5C0F1A"), (label, "#666666"))
        )

    def _write_reply(self, reply: str, via: str = "") -> None:
        chat = self.query_one("#chat", ChatLog)
        suffix = Text(f" via {via}", style="#5C0F1A") if via else Text("")
        header = Text.assemble(
            ("\n  ✦ ", "#C41E3A"),
            (ASSISTANT_NAME, "bold #C41E3A"),
            suffix,
        )
        chat.write(header)
        chat.write(Markdown(reply))
        chat.write(Text(""))
        self.query_one("#status", StatusBar).refresh()

    def _write_error(self, msg: str) -> None:
        self.query_one("#chat", ChatLog).write(
            Text(f"\n  Fout: {msg}\n", style="bold red")
        )

    def _unlock_input(self) -> None:
        inp = self.query_one("#input", ChatInput)
        inp.disabled = False
        inp.focus()

    def _run_command(self, cmd_str: str) -> None:
        parts = cmd_str.strip().split(None, 1)
        cmd = parts[0].lower()
        chat = self.query_one("#chat", ChatLog)

        if cmd == "clear":
            chat.clear()
        elif cmd == "reset":
            self.conversation = Conversation()
            chat.clear()
            chat.write(Text("  Conversatie gereset.\n", style="#666666"))
        elif cmd == "tts":
            self._tts_enabled = not self._tts_enabled
            status = "aan" if self._tts_enabled else "uit"
            chat.write(Text(f"  TTS {status}\n", style="#666666"))
        elif cmd == "help":
            chat.write(
                Text.assemble(
                    ("\n  Commands:\n", "#666666"),
                    ("  /clear  /reset  /history  /tts  /help\n", "#C41E3A"),
                )
            )
        elif cmd == "history":
            msgs = [m for m in self.conversation.history if m["role"] != "system"]
            for m in msgs[-12:]:
                role = m["role"]
                content = m.get("content") or ""
                if isinstance(content, list):
                    content = next((c["text"] for c in content if c.get("type") == "text"), "")
                if role == "user":
                    chat.write(Text.assemble(("  YOU  ", "bold #3DB84A"), (content[:140], "#888888")))
                elif role == "assistant":
                    chat.write(Text.assemble(("  RIAS ", "bold #C41E3A"), (content[:140], "#888888")))
        else:
            chat.write(Text(f"  Onbekend: /{cmd}  —  /help\n", style="#666666"))

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", Sidebar)
        self._sidebar_visible = not self._sidebar_visible
        sidebar.display = self._sidebar_visible

    def action_focus_input(self) -> None:
        self.query_one("#input", ChatInput).focus()

    def action_reset_conv(self) -> None:
        self.conversation = Conversation()
        chat = self.query_one("#chat", ChatLog)
        chat.clear()
        chat.write(Text("  Conversatie gereset.\n", style="#666666"))

    def action_voice_input(self) -> None:
        self.run_worker(self._voice_worker, thread=True)

    @work(thread=True)
    def _voice_worker(self) -> None:
        text = listen_and_transcribe()
        if text:
            def _fill():
                inp = self.query_one("#input", ChatInput)
                inp.load_text(text)
                inp.focus()
            self.call_from_thread(_fill)
