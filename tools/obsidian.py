import os
from datetime import datetime
from config import SAGA_PATH, AETHER_PATH

class SagaTool:
    def read_context(self) -> str:
        parts = []
        for filename in ("USER.md", "MEMORY.md"):
            path = os.path.join(SAGA_PATH, filename)
            if os.path.exists(path):
                with open(path, "r") as f:
                    parts.append(f.read())
        return "\n\n".join(parts)
    
    def write_session(self, summary: str):
        sessions_dir = os.path.join(SAGA_PATH, "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        path = os.path.join(sessions_dir, f"{timestamp}.md")
        with open(path, "w") as f:
            f.write(f"# Session {timestamp}\n\n{summary}")

class AetherTool:
    def read_note(self, relative_path: str) -> str:
        path = os.path.join(AETHER_PATH, relative_path)
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read()

        # Case-insensitive fallback
        search = relative_path.lower()
        for filename in os.listdir(AETHER_PATH):
            if filename.lower() == search or filename.lower().endswith(search):
                with open(os.path.join(AETHER_PATH, filename), "r") as f:
                    return f.read()
        return ""

    def list_notes(self) -> str:
        files = [f for f in os.listdir(AETHER_PATH) if f.endswith(".md")]
        return "\n".join(sorted(files))