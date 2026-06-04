import subprocess

_BLOCKED = [
    "rm -rf",
    "rm -r /",
    "rm -r ~",
    "dd if=",
    "> /dev/sd",
    "mkfs",
    "chmod -R 777",
    ":(){ :|:& };:",
    "sudo rm",
    "shred",
    "wipefs",
    "truncate",
]


def _is_blocked(command: str) -> bool:
    low = command.lower()
    return any(pattern in low for pattern in _BLOCKED)


def run_command(command: str) -> str:
    if _is_blocked(command):
        return f"Geblokkeerd: commando bevat een gevaarlijk patroon — '{command}'"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout or result.stderr or "No output"
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error: {e}"
