import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class BaseAgent:
    model: str = "mistralai/ministral-14b-2512"
    tools: list = []
    max_tokens: int = 4096

    def __init__(self):
        self.persona = self._load_persona()
        self.history = [{"role": "system", "content": self.persona}]
        self._client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

    persona_name: str = None

    def _load_persona(self) -> str:
        from datetime import datetime
        _DAYS = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
        now = datetime.now()
        prefix = f"Now: {_DAYS[now.weekday()]} {now.strftime('%Y-%m-%d')}  {now.strftime('%H:%M')}\n\n"
        name = self.persona_name or self.__class__.__name__.lower()
        path = os.path.join(os.path.dirname(__file__), "..", "persona", "agents", f"{name}.md")
        if os.path.exists(path):
            with open(path) as f:
                return prefix + f.read()
        return prefix

    def _execute_tool(self, name: str, args: dict) -> str:
        return f"Unknown tool: {name}"

    def chat_stream(self, user_message: str):
        """Multi-turn stateful chat — used by Discord channels."""
        self.history.append({"role": "user", "content": user_message})

        while True:
            kwargs = dict(model=self.model, max_tokens=self.max_tokens, messages=self.history)
            if self.tools:
                kwargs["tools"] = self.tools
                kwargs["tool_choice"] = "auto"

            response = self._client.chat.completions.create(**kwargs)
            if not response.choices:
                yield ("reply", "")
                return

            message = response.choices[0].message

            if not message.tool_calls:
                break

            self.history.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in message.tool_calls
                ],
            })
            for tc in message.tool_calls:
                yield ("tool", tc.function.name)
                result = self._execute_tool(tc.function.name, json.loads(tc.function.arguments))
                import re as _re
                result = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', result or '')
                self.history.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        reply = message.content or ""
        self.history.append({"role": "assistant", "content": reply})
        yield ("reply", reply)

    max_iterations: int = 50

    def run(self, task: str) -> str:
        """One-shot — used for background delegation from RIAS."""
        messages = [
            {"role": "system", "content": self.persona},
            {"role": "user", "content": task},
        ]

        for _ in range(self.max_iterations):
            kwargs = dict(model=self.model, max_tokens=self.max_tokens, messages=messages)
            if self.tools:
                kwargs["tools"] = self.tools
                kwargs["tool_choice"] = "auto"

            response = self._client.chat.completions.create(**kwargs)
            if not response.choices:
                return ""

            message = response.choices[0].message
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in message.tool_calls
                ] if message.tool_calls else None,
            })

            if not message.tool_calls:
                return message.content or ""

            for tc in message.tool_calls:
                result = self._execute_tool(tc.function.name, json.loads(tc.function.arguments))
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        return "Max iteraties bereikt."
