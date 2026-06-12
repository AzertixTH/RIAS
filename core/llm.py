import os
import re
import json
import time as _time
import threading
import requests
from dotenv import load_dotenv
from tools.obsidian import SagaTool
from tools.registry import TOOL_SCHEMAS, execute as execute_tool
from tools.vision import build_content
from core.curator import curate_async
from core.usage import log_usage
from core.session import Session
from config import MAIN_MODEL, LLM_BASE_URL, LLM_API_KEY, CONTEXT_SIZE

load_dotenv()

_IS_OLLAMA = LLM_BASE_URL and "openrouter" not in LLM_BASE_URL and "ollama.com" not in LLM_BASE_URL
_OLLAMA_URL = LLM_BASE_URL.rstrip("/").replace("/v1", "") if _IS_OLLAMA else None

_stream_cancel = threading.Event()

def cancel_stream():
    _stream_cancel.set()

def _sanitize(text: str) -> str:
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text) if text else text

def _estimate_tokens(msg: dict) -> int:
    total = 4  # per-message overhead
    content = msg.get("content")
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                total += len(part.get("text", "")) // 4
            elif part.get("type") == "image_url":
                total += 1100
    elif isinstance(content, str):
        total += len(content) // 4
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function", {})
        total += (len(fn.get("name", "")) + len(fn.get("arguments", ""))) // 4
    return total

def _execute_tool_safe(name: str, args: dict) -> str:
    try:
        return execute_tool(name, args)
    except KeyError as e:
        return f"Error: tool '{name}' is missing required argument {e}."
    except Exception as e:
        return f"Error: tool '{name}' failed — {type(e).__name__}: {e}"

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


def _to_ollama_messages(messages: list) -> list:
    result = []
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            result.append(msg)
            continue
        text_parts = []
        images = []
        for part in content:
            if part.get("type") == "text":
                text_parts.append(part["text"])
            elif part.get("type") == "image_url":
                url = part["image_url"]["url"]
                if ";base64," in url:
                    images.append(url.split(";base64,", 1)[1])
        new_msg = {**msg, "content": " ".join(text_parts)}
        if images:
            new_msg["images"] = images
        result.append(new_msg)
    return result


def _ollama_chat(messages: list, tools: list = None) -> dict:
    payload = {
        "model": MAIN_MODEL,
        "messages": _to_ollama_messages(messages),
        "stream": False,
        "think": False,
        "options": {"num_predict": 4096},
    }
    if tools:
        payload["tools"] = tools
    resp = requests.post(
        f"{_OLLAMA_URL}/api/chat",
        json=payload,
        timeout=600,
    )
    resp.raise_for_status()
    return resp.json()


def _ollama_chat_stream(messages: list, tools: list = None):
    payload = {
        "model": MAIN_MODEL,
        "messages": _to_ollama_messages(messages),
        "stream": True,
        "think": False,
        "options": {"num_predict": 4096},
    }
    if tools:
        payload["tools"] = tools
    full_content = ""
    collected_tool_calls = []
    _stream_cancel.clear()
    with requests.post(f"{_OLLAMA_URL}/api/chat", json=payload, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if _stream_cancel.is_set():
                return
            if not line:
                continue
            data = json.loads(line)
            tc = data.get("message", {}).get("tool_calls")
            if tc:
                collected_tool_calls.extend(tc)
            chunk = data.get("message", {}).get("content") or ""
            if chunk:
                full_content += chunk
                yield ("token", chunk)
            if data.get("done"):
                yield ("done", {
                    "tool_calls": collected_tool_calls,
                    "content": full_content,
                    "eval_count": data.get("eval_count", 0),
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                })
                return


def _openai_chat_stream(messages: list, tools: list = None):
    from openai import OpenAI
    client = OpenAI(api_key=LLM_API_KEY or "sk", base_url=LLM_BASE_URL)
    kwargs = dict(
        model=MAIN_MODEL,
        max_tokens=4096,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
    )
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    full_content = ""
    tool_calls_acc = {}
    total_tokens = 0
    _stream_cancel.clear()

    with client.chat.completions.create(**kwargs) as stream:
        for chunk in stream:
            if _stream_cancel.is_set():
                return
            if chunk.usage:
                total_tokens = chunk.usage.total_tokens
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                full_content += delta.content
                yield ("token", delta.content)
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc_delta.id:
                        tool_calls_acc[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls_acc[idx]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc_delta.function.arguments

    tool_calls = []
    for idx in sorted(tool_calls_acc):
        v = tool_calls_acc[idx]
        if v["name"]:
            tc = type("TC", (), {
                "id": v["id"],
                "type": "function",
                "function": type("F", (), {"name": v["name"], "arguments": v["arguments"]})(),
            })()
            tool_calls.append(tc)

    yield ("done", {
        "tool_calls": tool_calls,
        "content": full_content,
        "total_tokens": total_tokens,
    })


def _openai_chat(messages: list, tools: list = None, max_tokens: int = 4096) -> dict:
    from openai import OpenAI
    client = OpenAI(
        api_key=LLM_API_KEY or "ollama",
        base_url=LLM_BASE_URL,
    )
    kwargs = dict(model=MAIN_MODEL, max_tokens=max_tokens, messages=messages)
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    response = client.chat.completions.create(**kwargs)
    return response


class Conversation:
    def __init__(self, agent_persona: str = None):
        system_prompt = _build_system_prompt(agent_persona)
        self.history = [{"role": "system", "content": system_prompt}]
        self.total_tokens = 0
        self._last_msg_ts: float = 0.0
        self.session = Session()
        if _IS_OLLAMA:
            import threading
            threading.Thread(target=self._warmup, daemon=True).start()

    def _add_tokens(self, n: int):
        self.total_tokens += n
        log_usage(n)

    def _warmup(self):
        try:
            _ollama_chat([
                {"role": "system", "content": self.history[0]["content"]},
                {"role": "user", "content": "."},
            ])
        except Exception:
            pass

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

    _CONTEXT_MARGIN = 16_000  # reserved for response + estimation slack

    def _clean_history(self):
        while len(self.history) > 1:
            last = self.history[-1]
            if last["role"] == "assistant" and not last.get("tool_calls"):
                break
            self.history.pop()

        system = self.history[0]
        rest = self.history[1:]
        pairs = []
        i = len(rest) - 1
        while i >= 0:
            if rest[i]["role"] == "assistant" and not rest[i].get("tool_calls"):
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

        budget = CONTEXT_SIZE - self._CONTEXT_MARGIN - _estimate_tokens(system)
        kept = []
        used = 0
        for pair in pairs:  # newest first
            pair_tokens = sum(_estimate_tokens(m) for m in pair)
            if kept and used + pair_tokens > budget:
                break
            kept.append(pair)
            used += pair_tokens

        if len(kept) < len(pairs):
            kept.reverse()
            self.history = [system] + [msg for pair in kept for msg in pair]

    def chat_stream(self, user_message: str, images: list[str] | None = None, stream_tokens: bool = False):
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

        _first_call = True
        while True:
            try:
                if stream_tokens and _first_call:
                    reply_content = ""
                    tool_calls_raw = []
                    _stream_fn = _ollama_chat_stream if _IS_OLLAMA else _openai_chat_stream
                    for ev_type, ev_data in _stream_fn(self.history, tools=TOOL_SCHEMAS):
                        if ev_type == "token":
                            yield ("token", ev_data)
                            reply_content += ev_data
                        elif ev_type == "done":
                            tool_calls_raw = ev_data["tool_calls"]
                            if ev_data["tool_calls"]:
                                reply_content = ev_data["content"]
                            if _IS_OLLAMA:
                                self._add_tokens(ev_data["eval_count"] + ev_data["prompt_eval_count"])
                            else:
                                self._add_tokens(ev_data.get("total_tokens", 0))
                elif _IS_OLLAMA:
                    data = _ollama_chat(self.history, tools=TOOL_SCHEMAS if _first_call else None)
                    message = data.get("message", {})
                    reply_content = message.get("content", "") or ""
                    tool_calls_raw = message.get("tool_calls") or []
                    if data.get("eval_count"):
                        self._add_tokens(data.get("eval_count", 0) + data.get("prompt_eval_count", 0))
                else:
                    response = _openai_chat(self.history, tools=TOOL_SCHEMAS)
                    message = response.choices[0].message
                    reply_content = message.content or ""
                    tool_calls_raw = message.tool_calls or []
                    if response.usage:
                        self._add_tokens(response.usage.total_tokens)

            except Exception as e:
                err = str(e)
                if "tool call id" in err.lower() or "invalid_request_message_order" in err.lower():
                    self._clean_history()
                    yield ("reply", "Provider wissel — history geleegd. Herhaal je vraag.")
                    return
                if "rate" in err.lower() or "429" in err.lower():
                    yield ("reply", "Rate limit — even wachten en opnieuw proberen.")
                    return
                raise

            _first_call = False

            if not tool_calls_raw:
                break

            if _IS_OLLAMA:
                tc_list = [
                    {
                        "id": f"call_{i}",
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": json.dumps(tc["function"].get("arguments", {})),
                        },
                    }
                    for i, tc in enumerate(tool_calls_raw)
                ]
            else:
                tc_list = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls_raw
                ]

            if not _IS_OLLAMA:
                self.history.append({
                    "role": "assistant",
                    "content": reply_content or None,
                    "tool_calls": tc_list,
                })

            tool_results = []
            for tc in tc_list:
                yield ("tool", tc["function"]["name"])
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                result = _execute_tool_safe(tc["function"]["name"], args)
                tool_results.append((tc["function"]["name"], _sanitize(result or "")))
                if not _IS_OLLAMA:
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": _sanitize(result or ""),
                    })

            if _IS_OLLAMA:
                combined = "\n".join(
                    f"[{name}]: {res}" for name, res in tool_results
                )
                self.history.append({
                    "role": "user",
                    "content": combined,
                })

        reply = reply_content
        self.history.append({"role": "assistant", "content": reply})
        yield ("reply", reply)
        self.session.add(user_message, reply)
        self.session.save()
        curate_async(user_message, reply)

    def inject_agent_result(self, agent_name: str, result: str):
        self.history.append({
            "role": "user",
            "content": f"[{agent_name} is klaar]\n\n{result}"
        })

        while True:
            if _IS_OLLAMA:
                data = _ollama_chat(self.history, tools=TOOL_SCHEMAS)
                message = data.get("message", {})
                reply = message.get("content", "") or ""
                tool_calls_raw = message.get("tool_calls") or []
                if data.get("eval_count"):
                    self._add_tokens(data.get("eval_count", 0) + data.get("prompt_eval_count", 0))
            else:
                response = _openai_chat(self.history, tools=TOOL_SCHEMAS, max_tokens=4096)
                message = response.choices[0].message
                reply = message.content or ""
                tool_calls_raw = message.tool_calls or []
                if response.usage:
                    self._add_tokens(response.usage.total_tokens)

            if not tool_calls_raw:
                break

            if _IS_OLLAMA:
                tc_list = [
                    {"id": f"call_{i}", "type": "function", "function": {
                        "name": tc["function"]["name"],
                        "arguments": json.dumps(tc["function"].get("arguments", {})),
                    }}
                    for i, tc in enumerate(tool_calls_raw)
                ]
            else:
                tc_list = [
                    {"id": tc.id, "type": "function", "function": {
                        "name": tc.function.name, "arguments": tc.function.arguments,
                    }}
                    for tc in tool_calls_raw
                ]

            if not _IS_OLLAMA:
                self.history.append({"role": "assistant", "content": reply or None, "tool_calls": tc_list})

            tool_results = []
            for tc in tc_list:
                yield ("tool", tc["function"]["name"])
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                tc_result = _execute_tool_safe(tc["function"]["name"], args)
                tool_results.append((tc["function"]["name"], _sanitize(tc_result or "")))
                if not _IS_OLLAMA:
                    self.history.append({"role": "tool", "tool_call_id": tc["id"], "content": _sanitize(tc_result or "")})

            if _IS_OLLAMA:
                combined = "\n".join(f"[{name}]: {res}" for name, res in tool_results)
                self.history.append({"role": "user", "content": combined})

        self.history.append({"role": "assistant", "content": reply})
        yield ("reply", reply)
        self.session.add(f"[{agent_name} is klaar]\n\n{result}", reply)
        self.session.save()
