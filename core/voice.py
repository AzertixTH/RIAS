import os
import asyncio
import tempfile
import subprocess
import numpy as np
import sounddevice as sd
import soundfile as sf
import edge_tts
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

from config import LLM_BASE_URL, STT_MODEL, VOICE_ID

ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "7qdUFMklKPaaAVMsBTBt")

_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

_mistral_client = OpenAI(
    api_key=os.getenv("MISTRAL_AI_API_KEY"),
    base_url="https://api.mistral.ai/v1",
)

sd.default.device = 'pipewire'

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.02
SILENCE_DURATION = 1.5


def record_audio(max_seconds: int = 30) -> str | None:
    print("🎙️  Luisteren...", flush=True)

    chunk_duration = 0.1
    chunk_samples = int(SAMPLE_RATE * chunk_duration)
    silence_limit = int(SILENCE_DURATION / chunk_duration)

    recording = []
    silent_chunks = 0
    started = False

    while True:
        chunk = sd.rec(chunk_samples, samplerate=SAMPLE_RATE, channels=1, dtype="float32")
        sd.wait()
        rms = float(np.sqrt(np.mean(chunk ** 2)))

        if rms > SILENCE_THRESHOLD:
            started = True
            silent_chunks = 0
        elif started:
            silent_chunks += 1

        if started:
            recording.append(chunk)

        if started and silent_chunks >= silence_limit:
            break
        if len(recording) * chunk_duration >= max_seconds:
            break

    if not recording:
        return None

    sd.stop()
    audio = np.concatenate(recording, axis=0)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio, SAMPLE_RATE)
    return tmp.name


def transcribe(audio_path: str) -> str:
    try:
        with open(audio_path, "rb") as f:
            response = _mistral_client.audio.transcriptions.create(
                model="voxtral-mini-2507",
                file=("audio.wav", f, "audio/wav"),
            )
        return response.text.strip()
    except Exception as e:
        return f"STT error: {e}"
    finally:
        try:
            os.unlink(audio_path)
        except Exception:
            pass


async def _tts_edge(text: str, path: str):
    communicate = edge_tts.Communicate(text, voice=VOICE_ID, rate="-10%")
    await communicate.save(path)


def _speak_elevenlabs(text: str, path: str) -> bool:
    if not ELEVENLABS_API_KEY:
        print("[EL] geen API key", flush=True)
        return False
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        response = client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.75, speed=1.15),
        )
        with open(path, "wb") as f:
            for chunk in response:
                f.write(chunk)
        print("[EL] OK", flush=True)
        return True
    except Exception as e:
        print(f"[EL] fout: {e}", flush=True)
        return False


_speak_proc: subprocess.Popen | None = None


def stop_speaking():
    global _speak_proc
    if _speak_proc and _speak_proc.poll() is None:
        _speak_proc.kill()
        _speak_proc = None


def speak(text: str):
    global _speak_proc
    stop_speaking()
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    try:
        if not _speak_elevenlabs(text, tmp.name):
            asyncio.run(_tts_edge(text, tmp.name))
        _speak_proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp.name],
            close_fds=True,
        )
        _speak_proc.wait()
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def listen_and_transcribe() -> str:
    path = record_audio()
    if not path:
        return ""
    return transcribe(path)
