from agents.code.base import CodingAgent, CODING_TOOLS
from config import CODE_FRONTEND_MODEL
from tools.ui_design import ui_search, ui_design_system

UI_DESIGN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ui_search",
            "description": (
                "Search the UI/UX design database. "
                "Use for styles (glassmorphism, brutalism, minimalism...), colors, typography, "
                "UX guidelines, chart types, landing patterns, or product type recommendations. "
                "Domain options: style, color, typography, ux, product, landing, chart, prompt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query, e.g. 'glassmorphism dark mode'"},
                    "domain": {
                        "type": "string",
                        "description": "style | color | typography | ux | product | landing | chart | prompt",
                        "enum": ["style", "color", "typography", "ux", "product", "landing", "chart", "prompt"]
                    },
                    "n": {"type": "integer", "description": "Max results (default 3)", "default": 3}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ui_design_system",
            "description": (
                "Generate a complete design system for a project: style, colors, typography, "
                "effects, landing pattern, and anti-patterns. "
                "Use when starting a new UI or component from scratch."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Project description, e.g. 'fintech dashboard dark modern'"},
                    "project_name": {"type": "string", "description": "Optional project name"}
                },
                "required": ["query"]
            }
        }
    }
]


class FrontendAgent(CodingAgent):
    model = CODE_FRONTEND_MODEL
    persona_name = "code/frontend"
    tools = CODING_TOOLS + UI_DESIGN_TOOLS

    def _execute_tool(self, name: str, args: dict) -> str:
        if name == "ui_search":
            return ui_search(args["query"], args.get("domain"), args.get("n", 3))
        if name == "ui_design_system":
            return ui_design_system(args["query"], args.get("project_name"))
        return super()._execute_tool(name, args)
