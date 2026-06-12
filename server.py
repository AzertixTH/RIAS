import threading
import uvicorn
from tools.trading_watcher import start_watcher
from platforms.discord_bot import run as run_discord
from platforms.api import app as api_app

if __name__ == "__main__":
    start_watcher()

    threading.Thread(
        target=uvicorn.run,
        kwargs={"app": api_app, "host": "0.0.0.0", "port": 8000, "log_level": "warning"},
        daemon=True,
    ).start()

    run_discord()
