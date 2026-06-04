import os
import re
import json
import time as _time
from openai import OpenAI
from dotenv import load_dotenv
from tools.obsidian import SagaTool
from tools.registry import TOOL_SCHEMAS, execute as execute_tool
from tools.vision import build_content
from core.curator import curate_async
from config import MAIN_MODEL

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

def _sanitize(text: str) -> str:
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text) if text else text

_DAYS_NL = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]

def _date_prefix() -> str:
    from datetime import datetime
    now = datetime.now()
    day = _DAYS_NL[now.weekday()]
    return f"Now: {day} {now.strftime('%Y-%m-%d')}  {now.strftime('%H:%M')}\n\n"

def _load_system_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "persona", "persona.md")
    with open(path, "r") as f:
        return f.read()

def _build_system_prompt(agent_persona: str = None) -> str:
    from tools.project import read_project_context
    prefix = _date_prefix()
    if agent_persona:
        path = os.path.join(os.path.dirname(__file__), "..", "persona", "agents", f"{agent_persona}.md")
        if os.path.exists(path):
            with open(path, "r") as f:
                return prefix + f.read()
    persona = _load_system_prompt()
    saga_context = SagaTool().read_context()
    project_context = read_project_context()

    parts = [prefix + persona]
    if saga_context:
        parts.append(f"---\n\n{saga_context}")
    if project_context:
        from config import ASSISTANT_NAME
        parts.append(f"---\n\n## Actief project ({ASSISTANT_NAME}.md)\n\n{project_context}")
    return "\n\n".join(parts)


class Conversation:
    def __init__(self, agent_persona: str = None):
        system_prompt = _build_system_prompt(agent_persona)
        self.history = [{"role": "system", "content": system_prompt}]
        self.total_tokens = 0
        self._last_msg_ts: float = 0.0

    def _time_annotate(self, user_message: str) -> str:
        from datetime import datetime
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        if self._last_msg_ts > 0:
            gap_h = (_time.time() - self._last_msg_ts) / 3600
            if gap_h >= 5:
                note = f"[{time_str} — {gap_h:.0f}u geleden laatste bericht, waarschijnlijk nieuwe dag]"
            else:
                note = f"[{time_str}]"
        else:
            note = f"[{time_str}]"
        self._last_msg_ts = _time.time()
        return f"{note} {user_message}"

    _MAX_EXCHANGES = 30  # user+assistant paren bewaard (exclusief system prompt)

    def _clean_history(self):
        # Trim terug tot het laatste geldige eindpunt: een assistant bericht zonder tool_calls.
        while len(self.history) > 1:
            last = self.history[-1]
            if last["role"] == "assistant" and not last.get("tool_calls"):
                break
            self.history.pop()

        # Trim oude exchanges als history te lang wordt.
        # Bewaar system prompt (index 0) + laatste MAX_EXCHANGES * 2 berichten.
        system = self.history[0]
        rest = self.history[1:]
        # Zoek volledige user/assistant paren van achter naar voor
        pairs = []
        i = len(rest) - 1
        while i >= 0:
            if rest[i]["role"] == "assistant" and not rest[i].get("tool_calls"):
                # zoek de bijhorende user message (sla tool rounds ertussen over)
                j = i - 1
                while j >= 0 and rest[j]["role"] != "user":
                    j -= 1
                if j >= 0:
                    pairs.append(rest[j:i + 1])
                    i = j - 1
                else:
                    i -= 1
            else:
                i -= 1
        if len(pairs) > self._MAX_EXCHANGES:
            kept = pairs[:self._MAX_EXCHANGES]
            kept.reverse()
            self.history = [system] + [msg for pair in kept for msg in pair]

    def chat_stream(self, user_message: str, images: list[str] | None = None):
        self._clean_history()
        user_message = _sanitize(user_message)
        annotated = self._time_annotate(user_message)
        if images:
            content = [{"type": "text", "text": annotated}] if annotated else []
            for img in images:
                content.append({"type": "image_url", "image_url": {"url": img}})
            self.history.append({"role": "user", "content": content})
        else:
            self.history.append({"role": "user", "content": build_content(annotated)})

        # Tool loop — non-streaming to avoid Groq delta parsing issues
        while True:
            try:
                response = _client.chat.completions.create(
                    model=MAIN_MODEL,
                    max_tokens=4096,
                    messages=self.history,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                )
            except Exception as e:
                err = str(e)
                if "tool call id" in err.lower() or "invalid_request_message_order" in err.lower():
                    self._clean_history()
                    yield ("reply", "OpenRouter provider wissel — history geleegd. Herhaal je vraag.")
                    return
                if "rate" in err.lower() or "429" in err.lower():
                    yield ("reply", "Rate limit — even wachten en opnieuw proberen.")
                    return
                raise

            message = response.choices[0].message

            if response.usage:
                self.total_tokens += response.usage.total_tokens

            if not message.tool_calls:
                break

            self.history.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in message.tool_calls
                ],
            })
            for tool_call in message.tool_calls:
                yield ("tool", tool_call.function.name)
                args = json.loads(tool_call.function.arguments)
                result = execute_tool(tool_call.function.name, args)
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        reply = message.content or ""
        self.history.append({"role": "assistant", "content": reply})
        yield ("reply", reply)
        curate_async(user_message, reply)

    def inject_agent_result(self, agent_name: str, result: str):
        self.history.append({
            "role": "user",
            "content": f"[{agent_name} is klaar]\n\n{result}"
        })

        response = _client.chat.completions.create(
            model=MAIN_MODEL,
            max_tokens=512,
            messages=self.history,
        )

        message = response.choices[0].message
        if response.usage:
            self.total_tokens += response.usage.total_tokens

        reply = message.content or ""
        self.history.append({"role": "assistant", "content": reply})
        yield ("reply", reply)
