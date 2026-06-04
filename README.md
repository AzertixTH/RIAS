# RIAS

**Refined Intelligent Agentic System** — a personal agentic OS built around a local orchestrator, specialized sub-agents, and a persistent memory layer.

Inspired by projects like Jarvis, OpenClaw, and Hermes Agent. RIAS is not a chatbot — it's an always-on system that delegates, remembers, and acts.

---

## What it is

RIAS runs as a persistent orchestrator that routes tasks to specialized agents, executes tools, and writes to long-term memory after every exchange. It's accessible via CLI, Discord (mobile), or API.

```
User
 └── RIAS (orchestrator)
       ├── Kage      — code & file operations
       ├── Echo      — deep research
       ├── Loki      — trading & market analysis
       ├── Nami      — creative & text
       └── Heimdall  — homelab monitoring
```

---

## Features

- **5 specialized agents** — each with their own model and toolset
- **35 tools** — filesystem, shell, browser automation, maps, Discord, Obsidian, web search, and more
- **Persistent memory** — Saga vault with Curator (per-exchange) and Deriver (cross-session pattern analysis)
- **Background execution** — agents run async, results injected back into conversation
- **Voice** — push-to-talk input (Voxtral STT) + TTS output (ElevenLabs / edge-tts)
- **Multi-platform** — CLI (primary), Discord bot (mobile), FastAPI (for web frontends)

---

## Setup

```bash
cp .env.example .env
# fill in your API keys

pip install -r requirements.txt
playwright install chromium

python main.py
```

### Required keys

| Key | Used for |
|---|---|
| `OPENROUTER_API_KEY` | RIAS core + all agents |
| `MISTRAL_AI_API_KEY` | Voice STT (Voxtral) |
| `ELEVENLABS_API_KEY` | TTS |
| `DISCORD_BOT_TOKEN` | Discord bot platform |

---

## Platforms

| Platform | How to run |
|---|---|
| CLI | `python main.py` |
| Discord bot | `python -m platforms.discord_bot` |
| API | `uvicorn platforms.api:app` |

---

## Memory — Saga

RIAS writes to an Obsidian vault (`SAGA_PATH`) — not the repo. Set the path in `.env`.

```
Saga/
├── USER.md       ← behavioral profile
├── MEMORY.md     ← project decisions, environment facts
├── INSIGHTS.md   ← cross-session pattern analysis (Deriver)
├── sessions/     ← conversation logs
└── skills/       ← reusable workflows
```

---

## CLI commands

| Command | |
|---|---|
| `/agents` | show active agents |
| `/tools` | list available tools |
| `/memory` | read Saga memory |
| `/history [n]` | show last n exchanges |
| `/tts` | toggle voice output |
| `/reset` | new conversation |
| `Ctrl+Space` | voice input |
