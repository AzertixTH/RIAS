import threading
import queue
import time
import json
import os

_results = queue.Queue()
_notified: set = set()
_active = {}
_held: list = []
_lock = threading.Lock()
_counter = 0

from config import SAGA_PATH as _SAGA_PATH
_STATE_FILE = os.path.join(_SAGA_PATH, "agents_state.json")


def _write_state():
    with _lock:
        state = list(_active.values())
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump({"updated": time.time(), "active": state}, f)
    except Exception:
        pass

# Confirmation queue: agent stuurt (prompt, response_queue) naar main loop
_confirm_requests: queue.Queue = queue.Queue()


def request_confirm(prompt: str) -> bool:
    """Vraag bevestiging aan de main loop. Blokkeert agent thread tot antwoord."""
    response_q: queue.Queue = queue.Queue()
    _confirm_requests.put((prompt, response_q))
    try:
        return response_q.get(timeout=120)
    except queue.Empty:
        return False  # geen antwoord na 2 min → weigeren


def has_pending_confirms() -> bool:
    return not _confirm_requests.empty()

def drain_confirms() -> list:
    """Main loop roept dit aan om openstaande bevestigingen te verwerken."""
    confirms = []
    while True:
        try:
            confirms.append(_confirm_requests.get_nowait())
        except queue.Empty:
            break
    return confirms


def _next_id() -> int:
    global _counter
    _counter += 1
    return _counter


def run(display_name: str, fn, *args, hold: bool = False) -> str:
    task_id = _next_id()

    with _lock:
        _active[task_id] = {"name": display_name, "started": time.time()}
    _write_state()

    def worker():
        try:
            result = fn(*args)
        except Exception as e:
            result = f"Agent fout: {e}"
        finally:
            with _lock:
                _active.pop(task_id, None)
                if hold:
                    _held.append({"name": display_name, "result": result})
            _write_state()
            if not hold:
                _results.put({"name": display_name, "result": result})

    threading.Thread(target=worker, daemon=True).start()
    if hold:
        return f"{display_name} gestart — resultaat bewaard tot je het opvraagt."
    return f"{display_name} gestart — ik geef bescheid wanneer het klaar is."


def drain_held() -> list:
    with _lock:
        items = list(_held)
        _held.clear()
    return items


def held_count() -> int:
    with _lock:
        return len(_held)


def get_active() -> list:
    with _lock:
        return list(_active.values())


def peek_results() -> list:
    """Geeft nieuwe resultaten zonder ze te verwijderen — enkel voor notificaties."""
    items = list(_results.queue)
    new = [t for t in items if id(t) not in _notified]
    for t in new:
        _notified.add(id(t))
    return new


def drain_results() -> list:
    results = []
    while True:
        try:
            item = _results.get_nowait()
            _notified.discard(id(item))
            results.append(item)
        except queue.Empty:
            break
    return results
