from agents.code.base import CodingAgent
from config import CODE_BACKEND_MODEL


class BackendAgent(CodingAgent):
    model = CODE_BACKEND_MODEL
    persona_name = "code/backend"
