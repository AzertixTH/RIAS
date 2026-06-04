import time
from textual.app import App, ComposeResult
from textual.widgets import Static, TextArea, Markdown
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.binding import Binding
from textual import events, work
from rich.text import Text

from config import ASSISTANT_NAME, MAIN_MODEL, USER_NAME
from core.llm import Conversation
from core.session import Session
from core import background
from core.voice import listen_and_transcribe, speak

PRIMARY   = "#C41E3A"
MUTED     = "#666666"
FG        = "#d4d4d4"
GREEN     = "#3DB84A"
SECONDARY = "#888888"
BG        = "#12121a"

MODEL_DISPLAY = MAIN_MODEL.split("/")[-1]

LOGO_LINES = [
    " ·:·. .·:·",
    " ·:·.·.·:·",
    "  ·:···:· ",
]

TOOL_LABELS = {
    "open_ui":                  "opening UI",
    "agent_status":             "checking agents",
    "web_search":               "searching the web",
    "run_shell":                "running shell",
    "read_aether":              "reading aether",
    "list_aether":              "listing aether",
    "read_file":                "reading file",
    "list_dir":                 "listing directory",
    "write_file":               "writing file",
    "patch_file":               "patching file",
    "list_skills":              "listing skills",
    "load_skill":               "loading skill",
    "write_skill":              "writing skill",
    "delegate_code":            "delegating → Kage",
    "delegate_research":        "delegating → Echo",
    "queue_research":           "queuing → Echo",
    "get_queued_results":       "retrieving queued research",
    "delegate_trading":         "delegating → Loki",
    "discord_list_channels":    "listing channels",
    "discord_create_category":  "creating category",
    "discord_create_channel":   "creating channel",
    "discord_send_to_channel":  "sending message",
    "map_show":                 "showing map",
    "map_route":                "calculating route",
    "map_clear":                "clearing map",
    "browser_open":             "browser_open",
    "browser_click":            "browser_click",
    "browser_type":             "browser_type",
    "browser_press":            "browser_press",
    "browser_screenshot":       "browser_screenshot",
    "browser_read":             "browser_read",
    "browser_close":            "browser_close",
}


class Banner(Horizontal):
    DEFAULT_CSS = f"""
    Banner {{
        height: auto;
        width: 100%;
        padding: 1 1 0 0;
        background: transparent;
    }}
    #logo {{
        width: 14;
        height: auto;
        color: {PRIMARY};
        background: transparent;
    }}
    #info {{
        width: 1fr;
        height: auto;
        background: transparent;
        padding: 0;
    }}
    """

    def compose(self) -> ComposeResult:
        yield Static("\n".join(LOGO_LINES), id="logo")
        info = Text()
        info.append(f"{ASSISTANT_NAME} ", style=f"bold {PRIMARY}")
        info.append("v4.0  ·  ", style=MUTED)
        info.append(MODEL_DISPLAY, style=SECONDARY)
        info.append("  ·  OpenRouter\n", style=MUTED)
        info.append("5 agents  ·  14 tools  ·  Saga actief\n", style=MUTED)
        info.append("Type ", style=MUTED)
        info.append("/help", style=SECONDARY)
        info.append(" for more information", style=MUTED)
        yield Static(info, id="info")


class UserMessage(Vertical):
    DEFAULT_CSS = f"""
    UserMessage {{
        height: auto;
        width: 100%;
        background: transparent;
        margin-top: 1;
    }}
    .sep {{ height: 1; width: 100%; color: {MUTED}; background: transparent; }}
    .content {{ width: 1fr; height: auto; text-style: bold; color: {FG}; background: transparent; }}
    .row {{ height: auto; width: 100%; background: transparent; }}
    """

    def __init__(self, text: str):
        super().__init__()
        self._text = text

    def compose(self) -> ComposeResult:
        with Horizontal(classes="row"):
            yield Static(f"> {self._text}", classes="content")
        yield Static("─" * 300, classes="sep")


class ToolMessage(Static):
    DEFAULT_CSS = f"""
    ToolMessage {{
        height: auto;
        width: 100%;
        color: {MUTED};
        text-style: italic;
        background: transparent;
    }}
    """

    def __init__(self, label: str):
        super().__init__(f"⟳ {label}")


class ReasoningMessage(Static):
    DEFAULT_CSS = f"""
    ReasoningMessage {{
        height: auto;
        width: 100%;
        color: {MUTED};
        text-style: italic;
        background: transparent;
    }}
    """

    def __init__(self, label: str = "Thought"):
        super().__init__(f"✓ {label} ▶")


class AssistantMessage(Markdown):
    DEFAULT_CSS = f"""
    AssistantMessage {{
        height: auto;
        width: 100%;
        background: transparent;
        padding: 0 0 0 2;
        margin: 0 0 2 0;
        color: {FG};
    }}
    AssistantMessage > * {{
        background: transparent;
        margin-top: 0;
    }}
    """

    def __init__(self, text: str):
        super().__init__(text)


class AgentResult(Static):
    DEFAULT_CSS = f"""
    AgentResult {{
        height: auto;
        width: 100%;
        color: {PRIMARY};
        background: transparent;
        margin-top: 1;
    }}
    """

    def __init__(self, name: str):
        super().__init__(f"◆ {name} klaar")


class ThinkingIndicator(Static):
    DEFAULT_CSS = f"""
    ThinkingIndicator {{
        height: 1;
        width: 100%;
        color: {MUTED};
        background: transparent;
        text-style: italic;
    }}
    """

    _FRAMES = ["◌  nadenken", "◎  nadenken", "●  nadenken", "◎  nadenken"]
    _frame: int = 0

    def on_mount(self) -> None:
        self.update(self._FRAMES[0])
        self.set_interval(0.4, self._tick_frame)

    def _tick_frame(self) -> None:
        self._frame = (self._frame + 1) % len(self._FRAMES)
        self.update(self._FRAMES[self._frame])


class SystemMessage(Static):
    DEFAULT_CSS = f"""
    SystemMessage {{
        height: auto;
        width: 100%;
        color: {MUTED};
        background: transparent;
        text-style: italic;
    }}
    """


class ChatInput(TextArea):
    DEFAULT_CSS = f"""
    ChatInput {{
        width: 1fr;
        height: auto;
        min-height: 1;
        max-height: 8;
        background: transparent;
        border: none;
        padding: 0;
        color: {FG};
        scrollbar-visibility: hidden;
    }}
    ChatInput:focus {{ border: none; }}
    """

    class Submitted(TextArea.Changed):
        def __init__(self, widget, text: str):
            super().__init__(widget)
            self.submitted_text = text

    def _on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+v":
            from tools.clipboard import get_clipboard_image
            img_path = get_clipboard_image()
            if img_path:
                event.prevent_default()
                current = self.text.strip()
                self.load_text(f"{current} {img_path}".strip())
                return

        if event.key == "enter":
            event.prevent_default()
            text = self.text.strip()
            self.post_message(self.Submitted(self, text))
            if text:
                self.load_text("")
            return

        super()._on_key(event)


class InputBox(Vertical):
    DEFAULT_CSS = f"""
    InputBox {{
        height: auto;
        width: 100%;
        background: transparent;
        border: none;
        border-top: solid {MUTED};
    }}
    #prompt {{
        width: auto;
        height: auto;
        color: {PRIMARY};
        text-style: bold;
        padding: 0 1 0 0;
        background: transparent;
    }}
    #input {{
        width: 1fr;
        height: auto;
        min-height: 3;
        max-height: 8;
        background: transparent;
        border: none;
        padding: 0;
        color: {FG};
        scrollbar-visibility: hidden;
    }}
    #input:focus {{ border: none; }}
    #input-row {{
        height: auto;
        background: transparent;
    }}
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="input-row"):
            yield Static(">", id="prompt")
            yield ChatInput(id="input")

    def on_mount(self) -> None:
        self.styles.border_title_align = "left"
        self.styles.border_title_color = MUTED


class BottomBar(Horizontal):
    DEFAULT_CSS = f"""
    BottomBar {{
        height: auto;
        width: 100%;
        background: transparent;
        padding: 0;
    }}
    #path {{
        width: auto;
        height: auto;
        color: {MUTED};
        background: transparent;
    }}
    #spacer {{
        width: 1fr;
        height: auto;
        background: transparent;
    }}
    #ctx {{
        width: auto;
        height: auto;
        color: {MUTED};
        background: transparent;
    }}
    """

    def compose(self) -> ComposeResult:
        yield Static("~/Dev/project AI", id="path")
        yield Static("", id="spacer")


class Chat(VerticalScroll):
    DEFAULT_CSS = f"""
    Chat {{
        height: 1fr;
        width: 100%;
        background: transparent;
        border: none;
        scrollbar-size: 1 1;
        scrollbar-color: #222222;
        align-vertical: bottom;
    }}
    """


class RIASApp(App):
    CSS = f"""
    Screen {{ background: {BG}; layout: vertical; }}
    AssistantMessage MarkdownH1,
    AssistantMessage MarkdownH2,
    AssistantMessage MarkdownH3,
    AssistantMessage MarkdownH4 {{
        color: {PRIMARY};
        background: transparent;
        text-style: bold;
    }}
    AssistantMessage .code_inline {{
        color: {PRIMARY};
        background: transparent;
    }}
    AssistantMessage MarkdownTableHeader {{
        color: {PRIMARY};
        background: transparent;
    }}
    AssistantMessage MarkdownBullet {{
        color: {PRIMARY};
    }}
    """


    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+r", "reset", "Reset"),
        Binding("f2", "voice", "Voice"),
    ]

    def __init__(self):
        super().__init__()
        self.conversation = Conversation()
        self.session = Session()
        self._tts_enabled = False

    def compose(self) -> ComposeResult:
        with Chat(id="chat"):
            yield Banner()
        yield InputBox(id="input-box")
        yield BottomBar()

    def on_mount(self) -> None:
        self.query_one("#input", TextArea).focus()
        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        self._update_tokens()
        self._notify_agent_results()

    _SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def _update_tokens(self) -> None:
        tokens = self.conversation.total_tokens
        tk = f"{tokens / 1000:.1f}K" if tokens >= 1000 else str(tokens)
        active = background.get_active()
        try:
            box = self.query_one("#input-box", InputBox)
            if active:
                frame = self._SPINNER[int(time.time() * 8) % len(self._SPINNER)]
                names = "  ·  ".join({a["name"] for a in active})
                box.border_title = f" {tk} tokens  ·  {names} {frame}"
            else:
                box.border_title = f" {tk} tokens"
        except Exception:
            pass

    def _notify_agent_results(self) -> None:
        for task in background.peek_results():
            chat = self.query_one("#chat", Chat)
            chat.mount(AgentResult(task["name"]))
            chat.mount(SystemMessage("↵ druk Enter om te verwerken"))
            chat.scroll_end(animate=False)
            self.query_one("#input", TextArea).focus()

    def _drain_agent_results(self) -> None:
        for task in background.drain_results():
            chat = self.query_one("#chat", Chat)
            self.run_worker(self._inject_result(task["name"], task["result"]))

    async def _inject_result(self, name: str, result: str) -> None:
        chat = self.query_one("#chat", Chat)
        thinking = ThinkingIndicator()
        await chat.mount(thinking)
        chat.scroll_end(animate=False)

        tools_used = []
        reply = ""
        for kind, data in self.conversation.inject_agent_result(name, result):
            if kind == "tool":
                tools_used.append(TOOL_LABELS.get(data, data))
            elif kind == "reply":
                reply = data

        thinking.remove()
        if tools_used:
            chat.mount(ToolMessage("  ·  ".join(tools_used)))
        if reply:
            chat.mount(AssistantMessage(reply))
            chat.scroll_end(animate=False)
            if self._tts_enabled:
                try:
                    speak(reply)
                except Exception:
                    pass

    def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        self._handle_input(event.submitted_text)

    def _handle_input(self, text: str) -> None:
        chat = self.query_one("#chat", Chat)

        if not text:
            self._drain_agent_results()
            return

        _COMMANDS = {"clear", "reset", "tts", "history", "memory", "help", "tokens", "recap", "restart", "doctor", "status", "tools", "derive"}
        if text.startswith("/") and text[1:].split()[0].lower() in _COMMANDS:
            self._run_command(text[1:].strip(), chat)
            return

        from core.voice import stop_speaking
        stop_speaking()
        chat.mount(UserMessage(text))
        chat.scroll_end(animate=False)
        self._stream_chat(text)

    _PENDING_PHRASES = (
        "ik ga even", "ik kijk even", "ik zal even", "ik ga nu",
        "ik check even", "laat me even", "ik ga de ", "ik ga dit",
        "ik ga eerst", "ik ga proberen", "ik ga er even",
    )

    def _needs_continuation(self, reply: str, tools_used: list) -> bool:
        if tools_used:
            return False
        lower = reply.lower()
        return any(phrase in lower for phrase in self._PENDING_PHRASES)

    @work(thread=True, exclusive=True)
    def _stream_chat(self, user_input: str) -> None:
        chat = self.query_one("#chat", Chat)
        thinking = ThinkingIndicator()
        self.call_from_thread(chat.mount, thinking)
        self.call_from_thread(chat.scroll_end, animate=False)

        tools_used = []
        reply = ""

        for kind, data in self.conversation.chat_stream(user_input):
            if kind == "tool" and not data.startswith("delegate_"):
                label = TOOL_LABELS.get(data, data)
                if label not in tools_used:
                    tools_used.append(label)
            elif kind == "reply":
                reply = data

        needs_cont = self._needs_continuation(reply, tools_used)

        def _show():
            thinking.remove()
            if tools_used:
                chat.mount(ToolMessage("  ·  ".join(tools_used)))
            if reply:
                chat.mount(AssistantMessage(reply))
                chat.scroll_end(animate=False)
            if needs_cont:
                self.set_timer(0.5, self._do_continuation)

        self.call_from_thread(_show)
        self.call_from_thread(self.session.add, user_input, reply)

        if self._tts_enabled and reply:
            try:
                speak(reply)
            except Exception:
                pass

    @work(thread=True)
    def _do_continuation(self) -> None:
        chat = self.query_one("#chat", Chat)
        thinking = ThinkingIndicator()
        self.call_from_thread(chat.mount, thinking)
        self.call_from_thread(chat.scroll_end, animate=False)

        tools_used = []
        reply = ""
        for kind, data in self.conversation.chat_stream("ga door"):
            if kind == "tool" and not data.startswith("delegate_"):
                label = TOOL_LABELS.get(data, data)
                if label not in tools_used:
                    tools_used.append(label)
            elif kind == "reply":
                reply = data

        def _show():
            thinking.remove()
            if tools_used:
                chat.mount(ToolMessage("  ·  ".join(tools_used)))
            if reply:
                chat.mount(AssistantMessage(reply))
                chat.scroll_end(animate=False)

        self.call_from_thread(_show)

    def _run_command(self, cmd_str: str, chat: Chat) -> None:
        parts = cmd_str.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "clear":
            chat.remove_children()
            chat.mount(Banner())
            self.conversation = Conversation()
        elif cmd == "reset":
            self.conversation = Conversation()
            chat.mount(SystemMessage("conversatie gereset."))
        elif cmd == "recap":
            self._do_recap(chat)
        elif cmd == "restart":
            self._do_restart(chat)
        elif cmd == "tts":
            self._tts_enabled = not self._tts_enabled
            status = "aan" if self._tts_enabled else "uit"
            chat.mount(SystemMessage(f"tts {status}"))
        elif cmd == "tools":
            from tools.registry import TOOL_SCHEMAS
            groups = {
                "Memory":    ["read_aether", "list_aether", "list_skills", "load_skill", "write_skill"],
                "Filesystem":["read_file", "list_dir", "write_file", "patch_file"],
                "System":    ["run_shell", "agent_status", "open_ui"],
                "Browser":   ["browser_open", "browser_click", "browser_type", "browser_press", "browser_screenshot", "browser_read", "browser_close"],
                "Map":       ["map_show", "map_route", "map_clear"],
                "Discord":   ["discord_list_channels", "discord_create_category", "discord_create_channel", "discord_send_to_channel"],
                "Web":       ["web_search"],
                "Agents":    ["delegate_code", "delegate_research", "delegate_trading"],
            }
            names = {s["function"]["name"] for s in TOOL_SCHEMAS}
            lines = [f"  {len(names)} tools\n"]
            for group, tools in groups.items():
                active = [t for t in tools if t in names]
                if active:
                    lines.append(f"  {group}")
                    for t in active:
                        lines.append(f"    · {t}")
            chat.mount(SystemMessage("\n".join(lines)))
        elif cmd == "derive":
            from core.deriver import run_now
            chat.mount(SystemMessage(run_now()))
        elif cmd == "doctor":
            from tools.doctor import run_doctor
            chat.mount(SystemMessage(run_doctor()))
        elif cmd == "status":
            import subprocess, time
            from core.background import get_active
            lines = []
            try:
                uptime = subprocess.check_output("uptime -p", shell=True, text=True).strip()
                mem = subprocess.check_output("free -h | awk '/^Mem:/{print $3\"/\"$2}'", shell=True, text=True).strip()
                load = subprocess.check_output("cat /proc/loadavg | awk '{print $1,$2,$3}'", shell=True, text=True).strip()
                import socket
                hostname = socket.gethostname()
                lines.append(f"  {hostname}  ·  {uptime}  ·  RAM {mem}  ·  load {load}")
            except Exception:
                lines.append("  systeem info niet beschikbaar")
            lines.append(f"  model  ·  {self.conversation.history[0]['content'][:0] or ''}{__import__('config').MAIN_MODEL}")
            lines.append(f"  tokens  ·  {self.conversation.total_tokens:,}")
            active = get_active()
            if active:
                import time as _t
                for a in active:
                    elapsed = int(_t.time() - a["started"])
                    lines.append(f"  ⟳ {a['name']}  ·  {elapsed}s")
            else:
                lines.append("  agents  ·  geen actief")
            chat.mount(SystemMessage("\n".join(lines)))
        elif cmd == "help":
            t = Text()
            t.append("  /clear   /reset   /tts   /history   /memory   /recap   /restart   /doctor   /status   /tools   /derive   /help", style=SECONDARY)
            chat.mount(SystemMessage(t.plain))
        elif cmd == "history":
            msgs = [m for m in self.conversation.history if m["role"] != "system"]
            for m in msgs[-12:]:
                content = m.get("content") or ""
                if isinstance(content, list):
                    content = next((c["text"] for c in content if c.get("type") == "text"), "")
                snippet = content[:120].replace("\n", " ")
                prefix = USER_NAME if m["role"] == "user" else ASSISTANT_NAME
                chat.mount(SystemMessage(f"  {prefix}: {snippet}"))
        elif cmd == "memory":
            import os
            from config import SAGA_PATH
            path = os.path.join(SAGA_PATH, "MEMORY.md")
            try:
                with open(path) as f:
                    chat.mount(SystemMessage(f.read()[:800]))
            except Exception:
                chat.mount(SystemMessage("geen MEMORY.md gevonden"))
        else:
            chat.mount(SystemMessage(f"onbekend: /{cmd}  —  /help"))

        chat.scroll_end(animate=False)

    def _do_recap(self, chat: Chat) -> None:
        import os, threading
        from datetime import datetime
        from config import SAGA_PATH
        from core.llm import Conversation as Conv

        msgs = [m for m in self.conversation.history if m["role"] in ("user", "assistant")]
        if not msgs:
            chat.mount(SystemMessage("geen gesprek om samen te vatten."))
            chat.scroll_end(animate=False)
            return

        chat.mount(SystemMessage("recap wordt geschreven..."))
        chat.scroll_end(animate=False)

        def write():
            try:
                from openai import OpenAI
                from dotenv import load_dotenv
                from config import MAIN_MODEL
                load_dotenv()
                client = OpenAI(
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    base_url="https://openrouter.ai/api/v1",
                )
                history_text = "\n".join(
                    f"{m['role'].upper()}: {m['content'][:300]}"
                    for m in msgs[-30:]
                    if isinstance(m.get("content"), str)
                )
                resp = client.chat.completions.create(
                    model=MAIN_MODEL,
                    max_tokens=600,
                    messages=[{
                        "role": "user",
                        "content": f"Maak een beknopte samenvatting van dit gesprek. Noteer beslissingen, acties en belangrijke feiten. Schrijf in het Nederlands.\n\n{history_text}"
                    }]
                )
                summary = resp.choices[0].message.content or ""
                date = datetime.now().strftime("%Y-%m-%d_%H-%M")
                path = os.path.join(SAGA_PATH, "sessions", f"recap_{date}.md")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(f"# Recap {date}\n\n{summary}\n")
                self.call_from_thread(chat.mount, SystemMessage(f"recap opgeslagen: {path}"))
                self.call_from_thread(chat.scroll_end, animate=False)
            except Exception as e:
                self.call_from_thread(chat.mount, SystemMessage(f"recap fout: {e}"))

        threading.Thread(target=write, daemon=True).start()

    def _do_restart(self, chat: Chat) -> None:
        import os, sys
        chat.mount(SystemMessage("RIAS herstart..."))
        chat.scroll_end(animate=False)
        self.set_timer(0.5, lambda: os.execv(sys.executable, [sys.executable] + sys.argv))

    def action_reset(self) -> None:
        self.conversation = Conversation()
        chat = self.query_one("#chat", Chat)
        chat.mount(SystemMessage("conversatie gereset."))
        chat.scroll_end(animate=False)

    def action_voice(self) -> None:
        from core.voice import stop_speaking
        stop_speaking()
        self.run_worker(self._voice_worker, thread=True)

    @work(thread=True)
    def _voice_worker(self) -> None:
        text = listen_and_transcribe()
        if text:
            def _fill():
                ta = self.query_one("#input", TextArea)
                ta.load_text(text)
                ta.focus()
            self.call_from_thread(_fill)

    def on_unmount(self) -> None:
        self.session.save()
