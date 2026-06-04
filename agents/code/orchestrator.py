from concurrent.futures import ThreadPoolExecutor

from agents.code.base import CodingAgent
from config import CODE_MODEL


class CodeAgent(CodingAgent):
    model = CODE_MODEL
    persona_name = "code/orchestrator"

    def run(self, task: str) -> str:
        from agents.code.frontend import FrontendAgent
        from agents.code.backend import BackendAgent
        from agents.code.reviewer import ReviewerAgent

        specialist = self._classify(task)

        # Non-coding / meta tasks — orchestrator answers directly
        if specialist == "direct":
            return super().run(task)

        if specialist == "frontend":
            result = FrontendAgent().run(self._enrich(task, "frontend"))
        elif specialist == "both":
            with ThreadPoolExecutor(max_workers=2) as pool:
                fe_fut = pool.submit(FrontendAgent().run, self._enrich(task, "frontend"))
                be_fut = pool.submit(BackendAgent().run, self._enrich(task, "backend"))
            result = f"[Frontend]\n{fe_fut.result()}\n\n[Backend]\n{be_fut.result()}"
        else:
            result = BackendAgent().run(self._enrich(task, "backend"))

        return ReviewerAgent().run(
            f"Task:\n{task}\n\n"
            f"Handled by: {specialist} specialist(s)\n\n"
            f"Produced output:\n{result}\n\n"
            f"Review and finalize."
        )

    def _enrich(self, task: str, role: str) -> str:
        descriptions = {
            "frontend": "the frontend specialist (UI, UX, components, styling, accessibility)",
            "backend":  "the backend specialist (logic, APIs, data flow, reliability, security)",
        }
        return (
            f"You are {descriptions[role]} in a coding team. "
            f"The orchestrator has routed this task to you. "
            f"Handle your domain's portion completely.\n\n"
            f"Task: {task}"
        )

    def _classify(self, task: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            max_tokens=10,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify the coding task. Reply with exactly one word:\n"
                        "- frontend: UI, CSS, components, design, styling\n"
                        "- backend: API, logic, database, server, data\n"
                        "- both: requires both frontend and backend work\n"
                        "- direct: not a coding task (questions, explanations, meta-questions, architecture)"
                    )
                },
                {"role": "user", "content": task[:500]}
            ]
        )
        answer = (resp.choices[0].message.content or "").strip().lower()
        if "direct" in answer:
            return "direct"
        if "both" in answer:
            return "both"
        if "frontend" in answer:
            return "frontend"
        return "backend"
