import subprocess, os
from tools.obsidian import AetherTool
from tools.project import set_project, update_project_file
from tools.map import map_show, map_route, map_clear, geocode
from tools.browser import browser_open, browser_click, browser_type, browser_press, browser_screenshot, browser_read, browser_close, browser_scroll, browser_back, browser_console, browser_get_images, browser_vision
from tools.trading_db import get_accuracy, get_recent
from tools.trading_watcher import watcher_status
from tools.shell import run_command
from tools.search import web_search
from tools.filesystem import read_file, list_dir, write_file, patch_file, search_files
from tools.skills import list_skills, load_skill, write_skill
from tools.discord_tools import discord_create_category, discord_create_channel, discord_list_channels, discord_send_to_channel
from tools.executor import execute_code
from tools.vision import vision_analyze
from tools.process_manager import process
from tools.todo import todo
from tools.session_search import session_search
from tools.home_assistant import ha_get_state, ha_call_service, ha_list_entities
from tools.claude_cli import open_claude, send_to_claude, read_claude_output, stop_claude
from agents.research import ResearchAgent
from agents.trading import TradingAgent
from core import background
from config import USER_NAME

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "project",
            "description": "Actief project beheren. set = activeer project directory en laad context. update = schrijf RIAS.md in het actieve project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["set", "update"]},
                    "path": {"type": "string", "description": "Absoluut of ~ pad naar de project directory (verplicht bij set)"},
                    "content": {"type": "string", "description": "Volledige markdown inhoud voor de project file (verplicht bij update)"}
                },
                "required": ["action"]
            }
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
            "name": "aether",
            "description": f"{USER_NAME}'s Aether Obsidian vault. read = lees een note. list = ontdek beschikbare notes. write/patch = enkel op expliciete vraag van {USER_NAME}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["read", "list", "write", "patch"]},
                    "path": {"type": "string", "description": "Relatief pad in Aether, bv. 'Projects.md' (verplicht bij read/write/patch)"},
                    "content": {"type": "string", "description": "Volledige markdown inhoud (verplicht bij write)"},
                    "old_string": {"type": "string", "description": "Exacte tekst om te vervangen (verplicht bij patch)"},
                    "new_string": {"type": "string", "description": "Vervangende tekst (verplicht bij patch)"}
                },
                "required": ["action"]
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
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "research",
            "description": "Echo research agent. delegate = resultaat direct in gesprek. queue = silent op achtergrond, niet onderbreken. get_results = haal gehouden resultaten op.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["delegate", "queue", "get_results"]},
                    "task": {"type": "string", "description": "Volledige onderzoekstaak (verplicht bij delegate en queue)"}
                },
                "required": ["action"]
            }
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
                    "command": {"type": "string", "description": "The shell command to execute"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discord",
            "description": "RIAS Discord server beheer. list_channels = overzicht. create_category/create_channel = structuur aanmaken. send = bericht sturen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list_channels", "create_category", "create_channel", "send"]},
                    "name": {"type": "string", "description": "Naam voor category of channel"},
                    "category_id": {"type": "string", "description": "Parent category ID (optioneel bij create_channel)"},
                    "topic": {"type": "string", "description": "Channel topic (optioneel bij create_channel)"},
                    "channel_id": {"type": "string", "description": "Channel ID (verplicht bij send)"},
                    "message": {"type": "string", "description": "Bericht om te sturen (verplicht bij send)"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "skill",
            "description": "Saga skills beheren. list = beschikbare skills. load = laad een skill voor domein-specifieke taken. write = sla nieuwe of bijgewerkte skill op.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "load", "write"]},
                    "name": {"type": "string", "description": "Skill naam (verplicht bij load en write)"},
                    "content": {"type": "string", "description": "Volledige markdown inhoud van de skill (verplicht bij write)"}
                },
                "required": ["action"]
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
                    "path": {"type": "string", "description": "Absolute or relative file path to write to"},
                    "content": {"type": "string", "description": "Full content to write to the file"}
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
                    "path": {"type": "string", "description": "Absolute or relative file path to patch"},
                    "old_string": {"type": "string", "description": "The exact text to find and replace. Must be unique in the file."},
                    "new_string": {"type": "string", "description": "The text to replace it with"}
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
            "name": "browser_scroll",
            "description": "Scroll de pagina omhoog of omlaag.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "description": "'down' of 'up'", "enum": ["down", "up"]},
                    "amount": {"type": "integer", "description": "Pixels om te scrollen (default 400)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_back",
            "description": "Ga terug in de browsergeschiedenis.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_console",
            "description": "Voer JavaScript uit in de browser en geef het resultaat terug. Gebruik voor DOM-inspectie, data extractie of paginamanipulatie.",
            "parameters": {
                "type": "object",
                "properties": {
                    "js": {"type": "string", "description": "JavaScript expressie om uit te voeren, bv. 'document.title'"}
                },
                "required": ["js"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_images",
            "description": "Geef een lijst van alle images op de huidige pagina met hun URL en alt-tekst.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_vision",
            "description": "Neem een screenshot van de huidige pagina en analyseer die visueel met AI. Gebruik wanneer browser_read onvoldoende is (complexe UI, charts, afbeeldingen).",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Wat moet de AI analyseren op de pagina? (default: algemene beschrijving)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "map",
            "description": "Kaart operaties. geocode = plaatsnaam naar coördinaten. show = toon locaties. route = bereken route. clear = verwijder alles. Gebruik geocode eerst bij plaatsnamen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["geocode", "show", "route", "clear"]},
                    "place": {"type": "string", "description": "Plaatsnaam of adres (verplicht bij geocode)"},
                    "locations": {
                        "type": "array",
                        "description": "Lijst van locaties (verplicht bij show)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lon": {"type": "number"},
                                "label": {"type": "string"}
                            },
                            "required": ["lat", "lon"]
                        }
                    },
                    "start_lat": {"type": "number"},
                    "start_lon": {"type": "number"},
                    "end_lat": {"type": "number"},
                    "end_lon": {"type": "number"},
                    "start_label": {"type": "string"},
                    "end_label": {"type": "string"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Voer een Python script uit. Heeft toegang tot RIAS tools via imports (bv. from tools.search import web_search). Gebruik voor data verwerking, berekeningen, of scripts die meerdere tools combineren.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code om uit te voeren"},
                    "timeout": {"type": "integer", "description": "Timeout in seconden (default 30)"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "process",
            "description": "Beheer background processen. Start langlopende commando's en poll hun output zonder te blokkeren.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "start | poll | log | wait | kill | write | list",
                        "enum": ["start", "poll", "log", "wait", "kill", "write", "list"]
                    },
                    "pid": {"type": "string", "description": "Process ID (verkregen via start)"},
                    "command": {"type": "string", "description": "Shell commando (verplicht voor start)"},
                    "name": {"type": "string", "description": "Beschrijvende naam voor het process"},
                    "lines": {"type": "integer", "description": "Aantal log regels om te tonen (default 50)"},
                    "timeout": {"type": "integer", "description": "Wachttijd in seconden voor wait (default 30)"},
                    "text": {"type": "string", "description": "Tekst om naar stdin te sturen (voor write)"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Zoek in bestandsinhoud (grep) of vind bestanden op naam (find). Werkt binnen ~/Dev en ~/Obsidian.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Zoekterm of bestandsnaam patroon"},
                    "path": {"type": "string", "description": "Startmap om in te zoeken (default ~/Dev)"},
                    "mode": {
                        "type": "string",
                        "description": "'content' voor grep in bestandsinhoud, 'name' voor bestandsnaam",
                        "enum": ["content", "name"]
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "todo",
            "description": "Beheer de sessie task lijst. Gebruik om bij te houden wat er gedaan moet worden tijdens een taak.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "add | list | done | remove | clear",
                        "enum": ["add", "list", "done", "remove", "clear"]
                    },
                    "text": {"type": "string", "description": "Taak omschrijving (verplicht voor add)"},
                    "id": {"type": "integer", "description": "Taak ID (verplicht voor done en remove)"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "text_to_speech",
            "description": "Spreek tekst uit via de stem van RIAS. Gebruik voor korte antwoorden, alerts of wanneer de user om spraak vraagt. Gebruik NIET voor lange tekst of code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Tekst om uit te spreken"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vision_analyze",
            "description": "Analyseer een afbeelding met AI. Geef een lokaal bestandspad of een URL. Gebruik voor screenshots, foto's of diagrammen die visueel geïnterpreteerd moeten worden.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Absoluut bestandspad of https:// URL naar de afbeelding"},
                    "prompt": {"type": "string", "description": "Wat moet de AI analyseren? (default: algemene beschrijving)"}
                },
                "required": ["source"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "session_search",
            "description": f"Zoek in eerdere gesprekken met {USER_NAME}. Gebruik om te herinneren wat er in het verleden besproken is.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Zoekterm"},
                    "limit": {"type": "integer", "description": "Max aantal sessies om terug te geven (default 5)"}
                },
                "required": ["query"]
            }
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
    {
        "type": "function",
        "function": {
            "name": "home_assistant",
            "description": "Home Assistant entities en services. get_state = huidige staat van een entity. call_service = voer een actie uit (licht, thermostaat, ...). list_entities = overzicht van beschikbare entities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["get_state", "call_service", "list_entities"]},
                    "entity_id": {"type": "string", "description": "Entity ID, bv. 'light.woonkamer' (verplicht bij get_state en optioneel bij call_service)"},
                    "domain": {"type": "string", "description": "Service domain (verplicht bij call_service), bv. 'light', 'switch', 'climate'"},
                    "service": {"type": "string", "description": "Service naam (verplicht bij call_service), bv. 'turn_on', 'turn_off'"},
                    "data": {"type": "object", "description": "Extra parameters, bv. {\"brightness_pct\": 80} of {\"temperature\": 21}"},
                    "domain_filter": {"type": "string", "description": "Optioneel domain filter voor list_entities, bv. 'light', 'sensor'"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "command_claude",
            "description": f"Claude Code CLI. open = toon terminal venster (enkel als {USER_NAME} wil meekijken). send = stuur opdracht, start sessie automatisch. read = lees huidige output. stop = beëindig sessie. Na send: altijd read uitvoeren voor je iets claimt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["open", "send", "read", "stop"]},
                    "message": {"type": "string", "description": "Opdracht of bericht voor Claude (verplicht bij send)"},
                    "lines": {"type": "integer", "description": "Aantal regels output (optioneel bij read, default 50)"}
                },
                "required": ["action"]
            }
        }
    },
]


def execute(name: str, args: dict) -> str:
    if name == "project":
        action = args["action"]
        if action == "set":
            return set_project(args["path"])
        if action == "update":
            return update_project_file(args["content"])

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

    if name == "aether":
        action = args["action"]
        tool = AetherTool()
        if action == "list":
            return tool.list_notes()
        if action == "read":
            result = tool.read_note(args["path"])
            return result if result else f"Note not found: {args['path']}"
        if action == "write":
            return tool.write_note(args["path"], args["content"])
        if action == "patch":
            return tool.patch_note(args["path"], args["old_string"], args["new_string"])

    if name == "web_search":
        return web_search(args["query"])

    if name == "research":
        action = args["action"]
        if action == "delegate":
            return background.run("Research Agent", ResearchAgent().run, args["task"])
        if action == "queue":
            return background.run("Echo", ResearchAgent().run, args["task"], hold=True)
        if action == "get_results":
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

    if name == "run_shell":
        return run_command(args["command"])

    if name == "discord":
        action = args["action"]
        if action == "list_channels":
            return discord_list_channels()
        if action == "create_category":
            return discord_create_category(args["name"])
        if action == "create_channel":
            return discord_create_channel(args["name"], args.get("category_id"), args.get("topic", ""))
        if action == "send":
            return discord_send_to_channel(args["channel_id"], args["message"])

    if name == "skill":
        action = args["action"]
        if action == "list":
            return list_skills()
        if action == "load":
            return load_skill(args["name"])
        if action == "write":
            return write_skill(args["name"], args["content"])

    if name == "read_file":
        return read_file(args["path"])

    if name == "list_dir":
        return list_dir(args["path"])

    if name == "write_file":
        return write_file(args["path"], args["content"])

    if name == "patch_file":
        return patch_file(args["path"], args["old_string"], args["new_string"])

    if name == "map":
        action = args["action"]
        if action == "geocode":
            try:
                lat, lon = geocode(args["place"])
                return f"{args['place']}: lat={lat}, lon={lon}"
            except ValueError as e:
                return str(e)
        if action == "show":
            return map_show(args["locations"])
        if action == "route":
            return map_route(
                args["start_lat"], args["start_lon"],
                args["end_lat"], args["end_lon"],
                args.get("start_label", "Start"),
                args.get("end_label", "Einde")
            )
        if action == "clear":
            return map_clear()

    if name == "execute_code":
        return execute_code(args["code"], args.get("timeout", 30))

    if name == "process":
        return process(
            action=args["action"],
            pid=args.get("pid"),
            command=args.get("command"),
            name=args.get("name"),
            lines=args.get("lines", 50),
            timeout=args.get("timeout", 30),
            text=args.get("text"),
        )

    if name == "search_files":
        return search_files(args["query"], args.get("path"), args.get("mode", "content"))

    if name == "todo":
        return todo(args["action"], args.get("text"), args.get("id"))

    if name == "text_to_speech":
        import threading
        from core.voice import speak
        threading.Thread(target=speak, args=(args["text"],), daemon=True).start()
        return "Spraak gestart."

    if name == "vision_analyze":
        return vision_analyze(args["source"], args.get("prompt", "Beschrijf wat je ziet."))

    if name == "session_search":
        return session_search(args["query"], args.get("limit", 5))

    if name == "delegate_trading":
        return background.run("Trading Agent", TradingAgent().run, args["task"])

    if name == "home_assistant":
        action = args["action"]
        if action == "get_state":
            return ha_get_state(args["entity_id"])
        if action == "call_service":
            entity_id = args.get("entity_id") or args.get("target", {}).get("entity_id")
            return ha_call_service(args["domain"], args["service"], entity_id, args.get("data"))
        if action == "list_entities":
            return ha_list_entities(args.get("domain_filter"))

    if name == "command_claude":
        action = args["action"]
        if action == "open":
            return open_claude()
        if action == "send":
            return send_to_claude(args["message"])
        if action == "read":
            return read_claude_output(args.get("lines", 50))
        if action == "stop":
            return stop_claude()

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
    if name == "browser_scroll":
        return browser_scroll(args.get("direction", "down"), args.get("amount", 400))
    if name == "browser_back":
        return browser_back()
    if name == "browser_console":
        return browser_console(args["js"])
    if name == "browser_get_images":
        return browser_get_images()
    if name == "browser_vision":
        return browser_vision(args.get("prompt", "Wat zie je op deze pagina?"))

    return f"Unknown tool: {name}"
