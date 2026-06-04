from .base import BaseAgent
from config import MAIN_MODEL


class CreativeAgent(BaseAgent):
    model = MAIN_MODEL
    max_tokens = 8096
