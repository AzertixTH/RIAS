import subprocess, os
from tools.obsidian import AetherTool
from tools.project import set_project, update_project_file
from tools.map import map_show, map_route, map_clear, geocode
from tools.browser import browser_open, browser_click, browser_type, browser_press, browser_screenshot, browser_read, browser_close
from tools.trading_db import get_accuracy, get_recent
from tools.trading_watcher import watcher_status
from tools.shell import run_command
from tools.search import web_search
from tools.filesystem import read_file, list_dir, write_file, patch_file
from tools.skills import list_skills, load_skill, write_skill
from tools.discord_tools import discord_create_category, discord_create_channel, discord_list_channels, discord_send_to_channel
from agents.code import CodeAgent
from agents.research import ResearchAgent
from agents.trading import TradingAgent
from core import background
from config import USER_NAME

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "set_project",
            "description": f"Set the active project directory. Loads or creates {'{ASSISTANT_NAME}'}.md with project context. Use when switching between projects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or ~ path to the project directory"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_project_file",
            "description": f"Write or update the {'{ASSISTANT_NAME}'}.md file in the active project with new context, decisions or status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Full markdown content for the project file"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_ui",
            "description": "Open de RIAS visuele interface (sphere UI) in de browser.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "agent_status",
            "description": "Check which background agents are currently active. Use this before claiming an agent is or isn't running.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_aether",
            "description": f"Read a note from {USER_NAME}'s Aether Obsidian vault. Use when asked about projects, notes, or information {USER_NAME} has written down.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the note, e.g. 'Projects.md' or 'Homelab/Server.md'"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_code",
            "description": "Delegate a coding task to the code agent. Use for writing, reviewing, or debugging code, creating files, or running code-related shell commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Full description of the coding task to complete"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_aether",
            "description": f"List all available notes in {USER_NAME}'s Aether Obsidian vault. Use this to discover exact filenames before reading.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Use for factual questions, news, or anything not in memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_research",
            "description": "Delegate a deep research task to the research agent. Use when a question requires multiple searches, synthesis, or thorough investigation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Full description of what to research"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "queue_research",
            "description": "Queue a research task silently in the background. Result is held and NOT shown until the user explicitly asks for it with get_queued_results. Use when the user wants to run multiple research tasks in parallel without being interrupted.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Full description of what to research"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_queued_results",
            "description": "Retrieve all held research results queued with queue_research. Use when the user asks to see their queued research.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command on the local machine. Use for checking system status, disk usage, processes, network.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discord_list_channels",
            "description": "List all channels and categories in the RIAS Discord server.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discord_create_category",
            "description": "Create a new category in the RIAS Discord server.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Category name"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discord_create_channel",
            "description": "Create a new text channel in the RIAS Discord server, optionally under a category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Channel name (lowercase, no spaces)"},
                    "category_id": {"type": "string", "description": "ID of the parent category (optional)"},
                    "topic": {"type": "string", "description": "Channel topic/description (optional)"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discord_send_to_channel",
            "description": "Send a message to a specific Discord channel by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "Discord channel ID"},
                    "message": {"type": "string", "description": "Message to send"}
                },
                "required": ["channel_id", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List all available skills in Saga. Use this to discover what skills can be loaded.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": "Load a skill from Saga to get detailed instructions for a specific domain (e.g. python, trading, homelab, obsidian). Load relevant skills before tackling domain-specific tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the skill to load, e.g. 'python', 'trading', 'homelab'"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_skill",
            "description": "Write or update a skill in Saga. Use this to capture reusable workflows, learned patterns, or domain knowledge after completing a task. Skills persist across sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name, e.g. 'browser_automation', 'youtube_navigation'"
                    },
                    "content": {
                        "type": "string",
                        "description": "Full markdown content of the skill — include when to use it, instructions, and learned patterns."
                    }
                },
                "required": ["name", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file on the local machine. Only works within ~/Dev and ~/Obsidian.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative path to the file"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and folders in a directory. Use this to explore project structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative path to the directory"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": f"Write or overwrite a file on {USER_NAME}'s machine. Always shows a preview and asks for confirmation before writing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative file path to write to"
                    },
                    "content": {
                        "type": "string",
                        "description": "Full content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "patch_file",
            "description": f"Replace a specific string in a file on {USER_NAME}'s machine. Shows old and new content and asks for confirmation. The old_string must be unique in the file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative file path to patch"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "The exact text to find and replace. Must be unique in the file."
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The text to replace it with"
                    }
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open",
            "description": "Open a URL in a browser. Use for web automation tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to open"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click an element in the browser using a CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the element to click"}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_type",
            "description": "Type text into an input field in the browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the input field"},
                    "text": {"type": "string", "description": "Text to type"}
                },
                "required": ["selector", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_press",
            "description": "Press a key on a specific element. Use after browser_type to submit a search (key='Enter').",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the element"},
                    "key": {"type": "string", "description": "Key to press, e.g. 'Enter', 'Tab'"}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Take a screenshot of the current browser page. Returns the file path — use with vision to analyze it.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_read",
            "description": "Read the visible text content of the current browser page.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_close",
            "description": "Close the browser.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "Zet een plaatsnaam om naar coördinaten via OpenStreetMap. Gebruik dit altijd voor map_show of map_route wanneer je een plaatsnaam hebt in plaats van coördinaten.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place": {"type": "string", "description": "Plaatsnaam, adres of locatie, bv. 'Ninove', 'Gent', 'Brussel'"}
                },
                "required": ["place"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "map_show",
            "description": "Toon één of meerdere locaties op de kaart. Gebruik voor plaatsen aanduiden zonder route.",
            "parameters": {
                "type": "object",
                "properties": {
                    "locations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lon": {"type": "number"},
                                "label": {"type": "string"}
                            },
                            "required": ["lat", "lon"]
                        }
                    }
                },
                "required": ["locations"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "map_route",
            "description": "Bereken een route tussen twee punten en toon op de kaart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_lat": {"type": "number"},
                    "start_lon": {"type": "number"},
                    "end_lat": {"type": "number"},
                    "end_lon": {"type": "number"},
                    "start_label": {"type": "string"},
                    "end_label": {"type": "string"}
                },
                "required": ["start_lat", "start_lon", "end_lat", "end_lon"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "map_clear",
            "description": "Verwijder alle markers en routes van de kaart.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_trading",
            "description": "Delegate a trading analysis task to Loki, the trading agent. Use for market analysis, signal generation, or reviewing recent predictions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Full description of the trading task"}
                },
                "required": ["task"]
            }
        }
    },
]


def execute(name: str, args: dict) -> str:
    if name == "delegate_code":
        return background.run("Code Agent", CodeAgent().run, args["task"])

    if name == "delegate_research":
        return background.run("Research Agent", ResearchAgent().run, args["task"])

    if name == "queue_research":
        return background.run("Echo", ResearchAgent().run, args["task"], hold=True)

    if name == "get_queued_results":
        active = background.get_active()
        echo_active = [a for a in active if a["name"] == "Echo"]
        items = background.drain_held()
        if not items:
            if echo_active:
                return f"Nog geen resultaten klaar — {len(echo_active)} Echo taak(en) nog bezig."
            return "Geen gehouden resultaten."
        parts = []
        for i, item in enumerate(items, 1):
            parts.append(f"## Resultaat {i}\n\n{item['result']}")
        return "\n\n---\n\n".join(parts)

    if name == "web_search":
        return web_search(args["query"])

    if name == "list_aether":
        return AetherTool().list_notes()

    if name == "read_aether":
        result = AetherTool().read_note(args["path"])
        return result if result else f"Note not found: {args['path']}"

    if name == "set_project":
        return set_project(args["path"])

    if name == "update_project_file":
        return update_project_file(args["content"])

    if name == "open_ui":
        path = os.path.expanduser("~/Dev/RIAS-UI/sphere.html")
        subprocess.Popen(["firefox", f"file://{path}"])
        return "RIAS UI geopend."

    if name == "agent_status":
        active = background.get_active()
        if not active:
            return "Geen actieve agents."
        import time
        lines = []
        for a in active:
            elapsed = int(time.time() - a["started"])
            lines.append(f"{a['name']} — bezig sinds {elapsed}s")
        return "\n".join(lines)

    if name == "run_shell":
        return run_command(args["command"])

    if name == "discord_create_category":
        return discord_create_category(args["name"])

    if name == "discord_create_channel":
        return discord_create_channel(args["name"], args.get("category_id"), args.get("topic", ""))

    if name == "discord_list_channels":
        return discord_list_channels()

    if name == "discord_send_to_channel":
        return discord_send_to_channel(args["channel_id"], args["message"])

    if name == "geocode":
        try:
            lat, lon = geocode(args["place"])
            return f"{args['place']}: lat={lat}, lon={lon}"
        except ValueError as e:
            return str(e)

    if name == "map_show":
        return map_show(args["locations"])
    if name == "map_route":
        return map_route(args["start_lat"], args["start_lon"], args["end_lat"], args["end_lon"],
                         args.get("start_label", "Start"), args.get("end_label", "Einde"))
    if name == "map_clear":
        return map_clear()

    if name == "list_skills":
        return list_skills()

    if name == "load_skill":
        return load_skill(args["name"])

    if name == "write_skill":
        return write_skill(args["name"], args["content"])

    if name == "read_file":
        return read_file(args["path"])

    if name == "list_dir":
        return list_dir(args["path"])

    if name == "write_file":
        return write_file(args["path"], args["content"])

    if name == "patch_file":
        return patch_file(args["path"], args["old_string"], args["new_string"])

    if name == "delegate_trading":
        return background.run("Trading Agent", TradingAgent().run, args["task"])

    if name == "trading_accuracy":
        return get_accuracy()

    if name == "trading_recent":
        return get_recent(args.get("n", 10))

    if name == "browser_open":
        return browser_open(args["url"])
    if name == "browser_click":
        return browser_click(args["selector"])
    if name == "browser_type":
        return browser_type(args["selector"], args["text"])
    if name == "browser_press":
        return browser_press(args["selector"], args.get("key", "Enter"))

    if name == "browser_screenshot":
        return browser_screenshot()
    if name == "browser_read":
        return browser_read()
    if name == "browser_close":
        return browser_close()

    return f"Unknown tool: {name}"
