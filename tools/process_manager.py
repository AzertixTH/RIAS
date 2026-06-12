import subprocess
import threading
import time
import uuid

_processes: dict = {}


class _ManagedProcess:
    def __init__(self, proc: subprocess.Popen, name: str):
        self.proc = proc
        self.name = name
        self.log: list[str] = []
        self.started = time.time()
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self):
        for line in self.proc.stdout:
            with self._lock:
                self.log.append(line.rstrip())
            if len(self.log) > 1000:
                with self._lock:
                    self.log = self.log[-500:]

    def get_log(self, n: int = 50) -> list[str]:
        with self._lock:
            return self.log[-n:]

    @property
    def alive(self) -> bool:
        return self.proc.poll() is None

    @property
    def returncode(self):
        return self.proc.poll()


def process(action: str, pid: str = None, command: str = None,
            name: str = None, lines: int = 50, timeout: int = 30, text: str = None) -> str:

    if action == "start":
        if not command:
            return "command is verplicht voor start"
        short_id = uuid.uuid4().hex[:6]
        label = name or command[:30]
        try:
            proc = subprocess.Popen(
                command, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True, bufsize=1,
            )
            _processes[short_id] = _ManagedProcess(proc, label)
            return f"Process gestart: {short_id} [{label}] (PID {proc.pid})"
        except Exception as e:
            return f"Fout bij starten: {e}"

    if action in ("poll", "list") and not pid:
        if not _processes:
            return "Geen actieve processes."
        parts = []
        for p_id, p in _processes.items():
            status = "actief" if p.alive else f"gestopt (exit {p.returncode})"
            elapsed = int(time.time() - p.started)
            parts.append(f"{p_id} [{p.name}] — {status} ({elapsed}s)")
        return "\n".join(parts)

    p = _processes.get(pid) if pid else None
    if pid and not p:
        return f"Onbekend process: {pid}"

    if action == "poll":
        if p.alive:
            return f"{pid} [{p.name}] — actief ({int(time.time() - p.started)}s)"
        return f"{pid} [{p.name}] — gestopt (exit {p.returncode})"

    if action == "log":
        if not pid:
            return "pid is verplicht voor log"
        log = p.get_log(lines)
        return "\n".join(log) if log else "(geen output)"

    if action == "wait":
        if not pid:
            return "pid is verplicht voor wait"
        try:
            p.proc.wait(timeout=timeout)
            return f"{pid} [{p.name}] — klaar (exit {p.returncode})"
        except subprocess.TimeoutExpired:
            return f"Timeout na {timeout}s — process nog actief"

    if action == "kill":
        if not pid:
            return "pid is verplicht voor kill"
        p.proc.terminate()
        try:
            p.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.proc.kill()
        del _processes[pid]
        return f"{pid} [{p.name}] — gestopt"

    if action == "write":
        if not pid or text is None:
            return "pid en text zijn verplicht voor write"
        if not p.alive:
            return f"Process {pid} is al gestopt."
        try:
            p.proc.stdin.write(text + "\n")
            p.proc.stdin.flush()
            return f"Geschreven naar {pid}: {text}"
        except Exception as e:
            return f"Fout bij schrijven: {e}"

    return f"Onbekende actie: {action}. Gebruik: start, poll, log, wait, kill, write, list"
