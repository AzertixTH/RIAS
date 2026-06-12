import os
import subprocess
import tempfile

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def execute_code(code: str, timeout: int = 30) -> str:
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{_PROJECT_ROOT}:{existing}" if existing else _PROJECT_ROOT
        result = subprocess.run(
            ["python3", path],
            capture_output=True, text=True,
            timeout=timeout,
            env=env,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}" if output else result.stderr
        return output.strip() or "(geen output)"
    except subprocess.TimeoutExpired:
        return f"Timeout na {timeout}s"
    except Exception as e:
        return f"Fout: {e}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
