import os
from dotenv import load_dotenv

load_dotenv()

ASSISTANT_NAME     = os.getenv("ASSISTANT_NAME")
ASSISTANT_SUBTITLE = os.getenv("ASSISTANT_SUBTITLE")
USER_NAME          = os.getenv("USER_NAME", "User")

SAGA_PATH   = os.getenv("SAGA_PATH",   os.path.expanduser("~/Obsidian/Saga/"))
AETHER_PATH = os.getenv("AETHER_PATH", os.path.expanduser("~/Obsidian/Aether/"))

LLM_BASE_URL        = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_API_KEY         = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")

MAIN_MODEL          = os.getenv("MAIN_MODEL")
CURATOR_MODEL       = os.getenv("CURATOR_MODEL")
STT_MODEL           = os.getenv("STT_MODEL")
TTS_MODEL           = os.getenv("TTS_MODEL")
VOICE_ID            = os.getenv("VOICE_ID")
CODE_MODEL          = os.getenv("CODE_MODEL")
CODE_FRONTEND_MODEL = os.getenv("CODE_FRONTEND_MODEL") or CODE_MODEL
CODE_BACKEND_MODEL  = os.getenv("CODE_BACKEND_MODEL")  or CODE_MODEL
CODE_REVIEWER_MODEL = os.getenv("CODE_REVIEWER_MODEL") or CODE_MODEL
RESEARCH_MODEL      = os.getenv("RESEARCH_MODEL")
TRADING_MODEL       = os.getenv("TRADING_MODEL")

CONTEXT_SIZE = int(os.getenv("CONTEXT_SIZE", "256000"))

