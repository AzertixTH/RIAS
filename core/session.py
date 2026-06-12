import os
from datetime import datetime
from config import SAGA_PATH, ASSISTANT_NAME


class Session:
    def __init__(self):
        self.start_time = datetime.now()
        self.exchanges = []

    def add(self, user_message: str, assistant_reply: str):
        self.exchanges.append({
            "time": datetime.now().strftime("%H:%M"),
            "user": user_message,
            "assistant": assistant_reply
        })

    def save(self):
        if not self.exchanges:
            return
        sessions_dir = os.path.join(SAGA_PATH, "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        timestamp = self.start_time.strftime("%Y-%m-%d_%H-%M")
        path = os.path.join(sessions_dir, f"{timestamp}.md")
        lines = [f"# Session {timestamp}\n"]
        for ex in self.exchanges:
            lines.append(f"**[{ex['time']}] You:** {ex['user']}")
            lines.append(f"**{ASSISTANT_NAME}:** {ex['assistant']}\n")
        lines.append("\nLinks: [[📅 Sessions]]")
        with open(path, "w") as f:
            f.write("\n".join(lines))
        from core.deriver import tick
        tick()
