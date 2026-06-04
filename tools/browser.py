import os
import tempfile
import queue
import threading
from playwright.sync_api import sync_playwright

_PROFILE_DIR = os.path.expanduser("~/.rias/chromium-profile")

_task_queue: queue.Queue = queue.Queue()
_browser_thread: threading.Thread | None = None


def _browser_worker():
    os.makedirs(_PROFILE_DIR, exist_ok=True)
    pw = sync_playwright().start()
    # persistent context: bewaart cookies, sessies en ingelogde accounts
    context = pw.chromium.launch_persistent_context(
        _PROFILE_DIR,
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--start-maximized",
        ],
        no_viewport=True,
    )
    def _active_page():
        pages = [p for p in context.pages if not p.is_closed()]
        if not pages:
            p = context.new_page()
            p.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return p
        return pages[-1]  # meest recente/actieve pagina

    # init script op alle toekomstige paginas
    context.on("page", lambda p: p.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    ))

    while True:
        task = _task_queue.get()
        if task is None:
            break
        fn, result_holder = task
        try:
            result_holder["result"] = fn(_active_page())
        except Exception as e:
            result_holder["result"] = f"browser error: {e}"
        finally:
            result_holder["done"].set()

    context.close()
    pw.stop()


def _run_in_browser(fn) -> str:
    global _browser_thread
    if _browser_thread is None or not _browser_thread.is_alive():
        _browser_thread = threading.Thread(target=_browser_worker, daemon=True)
        _browser_thread.start()

    result_holder = {"result": None, "done": threading.Event()}
    _task_queue.put((fn, result_holder))
    result_holder["done"].wait(timeout=20)
    return result_holder["result"] or "timeout"


def browser_open(url: str) -> str:
    def fn(page):
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return f"Geopend: {page.title()} — {page.url}"
    return _run_in_browser(fn)


def browser_click(selector: str) -> str:
    def fn(page):
        if selector == "Enter":
            page.keyboard.press("Enter")
            return "Enter ingedrukt"
        # probeer eerst normaal, dan via JS als fallback
        try:
            page.click(selector, timeout=8000)
            return f"Geklikt: {selector}"
        except Exception:
            try:
                page.eval_on_selector(selector, "el => el.click()")
                return f"Geklikt via JS: {selector}"
            except Exception as e:
                return f"browser_click error: element niet gevonden — {e}"
    return _run_in_browser(fn)


def browser_type(selector: str, text: str) -> str:
    def fn(page):
        page.fill(selector, text, timeout=8000)
        return f"Getypt in {selector}: {text}"
    return _run_in_browser(fn)


def browser_screenshot() -> str:
    def fn(page):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        page.screenshot(path=tmp.name)
        return tmp.name
    return _run_in_browser(fn)


def browser_press(selector: str, key: str = "Enter") -> str:
    def fn(page):
        page.press(selector, key)
        return f"{key} ingedrukt op {selector}"
    return _run_in_browser(fn)


def browser_read() -> str:
    def fn(page):
        text = page.inner_text("body")
        return text[:2000] if len(text) > 2000 else text
    return _run_in_browser(fn)


def browser_url() -> str:
    def fn(page):
        return f"{page.title()} — {page.url}"
    return _run_in_browser(fn)


def browser_close() -> str:
    global _browser_thread
    _task_queue.put(None)
    if _browser_thread:
        _browser_thread.join(timeout=5)
        _browser_thread = None
    return "Browser gesloten."
