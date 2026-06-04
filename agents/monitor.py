from .base import BaseAgent
from tools.shell import run_command
from config import MAIN_MODEL

MONITOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command to check system status, processes, disk, memory, or network.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    }
]


class MonitorAgent(BaseAgent):
    model = MAIN_MODEL
    tools = MONITOR_TOOLS

    def _execute_tool(self, name: str, args: dict) -> str:
        if name == "run_shell":
            return run_command(args["command"])
        return f"Unknown tool: {name}"
