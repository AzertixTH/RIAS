import subprocess
import tempfile


def get_clipboard_image() -> str | None:
    """Probeert een afbeelding uit het clipboard te halen. Geeft temp pad terug of None."""

    # Wayland
    try:
        result = subprocess.run(
            ["wl-paste", "--type", "image/png"],
            capture_output=True, timeout=2
        )
        if result.returncode == 0 and result.stdout:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(result.stdout)
            tmp.close()
            return tmp.name
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # X11 fallback
    try:
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
            capture_output=True, timeout=2
        )
        if result.returncode == 0 and result.stdout:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(result.stdout)
            tmp.close()
            return tmp.name
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None
