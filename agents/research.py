from .base import BaseAgent
from tools.search import web_search
from config import RESEARCH_MODEL

RESEARCH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information on a topic.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    }
]


class ResearchAgent(BaseAgent):
    model = RESEARCH_MODEL
    tools = RESEARCH_TOOLS

    def _execute_tool(self, name: str, args: dict) -> str:
        if name == "web_search":
            return web_search(args["query"])
        return f"Unknown tool: {name}"
