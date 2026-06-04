from agents.base import BaseAgent
from config import CODE_REVIEWER_MODEL


class ReviewerAgent(BaseAgent):
    model = CODE_REVIEWER_MODEL
    persona_name = "code/reviewer"
    tools = []
    max_tokens = 4096
