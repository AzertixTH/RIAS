import os
import subprocess

from agents.base import BaseAgent
from config import CODE_MODEL

_READ_ROOTS = (
    os.path.expanduser("~/Dev"),
    os.path.expanduser("~/Obsidian"),
)

_WRITE_BLOCKED = (
    os.path.realpath(os.path.expanduser("~/Dev/project AI")),
)

_DESTRUCTIVE = ("rm ", "rmdir", "mv ", "shred", "truncate", "dd ", "git reset", "git clean",
                "git push --force", "git push -f", "chmod", "chown", "kill ", "pkill")


def _is_allowed(path: str) -> bool:
    abs_path = os.path.realpath(path)
    return any(abs_path.startswith(root) for root in _READ_ROOTS)


def _is_write_allowed(path: str) -> bool:
    abs_path = os.path.realpath(path)
    if not any(abs_path.startswith(root) for root in _READ_ROOTS):
        return False
    if any(abs_path.startswith(blocked) for blocked in _WRITE_BLOCKED):
        return False
    return True


CODING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates the file if it doesn't exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command and return the output.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories at a path.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
    }
]


class CodingAgent(BaseAgent):
    model = CODE_MODEL
    tools = CODING_TOOLS
    max_tokens = 8096

    def _execute_tool(self, name: str, args: dict) -> str:
        if name == "read_file":
            if not _is_allowed(args["path"]):
                return "Geblokkeerd: valt buiten ~/Dev en ~/Obsidian"
            try:
                with open(args["path"]) as f:
                    return f.read()
            except Exception as e:
                return f"Error: {e}"

        if name == "write_file":
            path, content = args["path"], args["content"]
            if not _is_write_allowed(path):
                return f"Geblokkeerd: schrijven naar {path} is niet toegestaan."
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                with open(path, "w") as f:
                    f.write(content)
                return f"Written to {path}"
            except Exception as e:
                return f"Error: {e}"

        if name == "run_shell":
            command = args["command"]
            if any(kw in command for kw in _DESTRUCTIVE):
                from core.background import request_confirm
                if not request_confirm(f"Destructief commando:\n  {command}"):
                    return "Geannuleerd."
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                return result.stdout or result.stderr or "No output"
            except subprocess.TimeoutExpired:
                return "Timeout"
            except Exception as e:
                return f"Error: {e}"

        if name == "list_dir":
            if not _is_allowed(args["path"]):
                return "Geblokkeerd: valt buiten ~/Dev en ~/Obsidian"
            try:
                return "\n".join(sorted(os.listdir(args["path"])))
            except Exception as e:
                return f"Error: {e}"

        return f"Unknown tool: {name}"
