import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

import discord

from core.llm import Conversation
from agents.code import CodeAgent
from agents.research import ResearchAgent
from agents.trading import TradingAgent
from agents.monitor import MonitorAgent
from agents.creative import CreativeAgent
from config import ASSISTANT_NAME

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
_executor = ThreadPoolExecutor(max_workers=4)

# Channel name → agent class (direct connection, own model + tools)
_AGENT_CHANNELS = {
    "kage-coding":      CodeAgent,
    "echo-research":    ResearchAgent,
    "heimdall-monitor": MonitorAgent,
    "nami-creative":    CreativeAgent,
    "loki-trading":     TradingAgent,
}

# Per-channel session: channel_id → Conversation or BaseAgent instance
_sessions: dict[int, object] = {}


def _get_session(channel: discord.TextChannel) -> object:
    cid = channel.id
    if cid not in _sessions:
        name = channel.name.lower()
        cls = _AGENT_CHANNELS.get(name)
        _sessions[cid] = cls() if cls else Conversation()
    return _sessions[cid]


def _sync_chat(session: object, user_message: str) -> str:
    reply = ""
    for kind, data in session.chat_stream(user_message):
        if kind == "reply":
            reply = data
    return reply


async def _send_long(channel, text: str):
    for i in range(0, len(text), 1990):
        await channel.send(text[i:i + 1990])


@client.event
async def on_ready():
    print(f"{ASSISTANT_NAME} Discord bot online als {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    session = _get_session(message.channel)

    async with message.channel.typing():
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(_executor, _sync_chat, session, message.content)

    if reply:
        await _send_long(message.channel, reply)
