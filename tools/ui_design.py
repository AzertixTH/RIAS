import subprocess
import os

_SEARCH_SCRIPT = os.path.join(
    os.path.dirname(__file__),
    "ui_ux_skill", "src", "ui-ux-pro-max", "scripts", "search.py"
)


def ui_search(query: str, domain: str = None, n: int = 3) -> str:
    cmd = ["python3", _SEARCH_SCRIPT, query, "-n", str(n)]
    if domain:
        cmd += ["--domain", domain]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.stdout or result.stderr or "No results."
    except Exception as e:
        return f"Error: {e}"


def ui_design_system(query: str, project_name: str = None) -> str:
    cmd = ["python3", _SEARCH_SCRIPT, query, "--design-system"]
    if project_name:
        cmd += ["-p", project_name]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.stdout or result.stderr or "No results."
    except Exception as e:
        return f"Error: {e}"
