import os
import asyncio
import tempfile
from concurrent.futures import ThreadPoolExecutor

import discord
from dotenv import load_dotenv

load_dotenv()

from core.llm import Conversation
from agents.code import CodeAgent
from agents.research import ResearchAgent
from agents.trading import TradingAgent
from agents.monitor import MonitorAgent
from agents.creative import CreativeAgent
from config import ASSISTANT_NAME

DISCORD_TOKEN       = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID    = int(os.getenv("DISCORD_GUILD_ID", "0"))
ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "7hSjFLTqJTvdLPxYg8Mj")

_tts_channels: set[int] = set()

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


def _transcribe_audio(audio_path: str) -> str:
    import requests as _req
    stt_url = os.getenv("STT_URL", "http://100.98.53.100:10300/v1/audio/transcriptions")
    try:
        with open(audio_path, "rb") as f:
            resp = _req.post(stt_url, files={"file": (os.path.basename(audio_path), f)}, data={"language": "nl"}, timeout=60)
        resp.raise_for_status()
        return resp.json().get("text", "").strip()
    except Exception as e:
        return f"[STT error: {e}]"
    finally:
        try:
            os.unlink(audio_path)
        except Exception:
            pass


def _sync_chat(session: object, user_message: str, image_paths: list[str] = []) -> str:
    import base64
    images = []
    for path in image_paths:
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")
        with open(path, "rb") as f:
            images.append(f"data:{mime};base64,{base64.b64encode(f.read()).decode()}")
        try:
            os.unlink(path)
        except Exception:
            pass
    reply = ""
    for kind, data in session.chat_stream(user_message, images=images or None):
        if kind == "reply":
            reply = data
    return reply


async def _send_long(channel, text: str):
    for i in range(0, len(text), 1990):
        await channel.send(text[i:i + 1990])


def _generate_tts(text: str) -> str | None:
    if not ELEVENLABS_API_KEY:
        return None
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        from elevenlabs import VoiceSettings
        response = client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text[:2500],
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.75, speed=1.15),
        )
        with open(tmp.name, "wb") as f:
            for chunk in response:
                f.write(chunk)
        return tmp.name
    except Exception:
        return None


@client.event
async def on_ready():
    print(f"{ASSISTANT_NAME} Discord bot online als {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if DISCORD_GUILD_ID and message.guild and message.guild.id != DISCORD_GUILD_ID:
        return

    image_paths = []
    voice_text = ""
    for att in message.attachments:
        ext = os.path.splitext(att.filename)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            await att.save(tmp.name)
            image_paths.append(tmp.name)
        elif ext in (".ogg", ".mp3", ".wav", ".m4a", ".webm"):
            tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            await att.save(tmp.name)
            loop = asyncio.get_event_loop()
            voice_text = await loop.run_in_executor(_executor, _transcribe_audio, tmp.name)

    user_text = message.content
    if voice_text:
        user_text = f"{user_text} {voice_text}".strip()

    if not user_text:
        return

    if user_text.strip().lower() == "!tts":
        cid = message.channel.id
        if cid in _tts_channels:
            _tts_channels.discard(cid)
            await message.channel.send("🔇 TTS uitgeschakeld.")
        else:
            _tts_channels.add(cid)
            await message.channel.send("🔊 TTS ingeschakeld.")
        return

    session = _get_session(message.channel)

    async with message.channel.typing():
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(_executor, _sync_chat, session, user_text, image_paths)

    if reply:
        await _send_long(message.channel, reply)
        if message.channel.id in _tts_channels:
            audio_path = await loop.run_in_executor(_executor, _generate_tts, reply)
            if audio_path:
                try:
                    await message.channel.send(file=discord.File(audio_path, filename="rias.mp3"))
                finally:
                    try:
                        os.unlink(audio_path)
                    except Exception:
                        pass


def run():
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN niet gevonden in .env")
    client.run(DISCORD_TOKEN)


if __name__ == "__main__":
    run()
