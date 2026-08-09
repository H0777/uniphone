"""uniphone --doctor: walk the dependency ladder; fix the first FAIL."""
import sys


def run_doctor():
    failed = False
    for check in (_python, _driver, _device, _capture, _ocr, _ollama):
        for ok, label, hint in check():
            print(f"[{'PASS' if ok else 'FAIL'}] {label}"
                  + (f"\n       -> {hint}" if not ok and hint else ""))
            failed = failed or not ok
        if failed:
            print("\nFix the first FAIL and re-run: uniphone --doctor")
            return 1
    print('\nAll good. Try:  uniphone agent "open the Settings app"')
    return 0


def _python():
    ok = sys.version_info >= (3, 10)
    yield ok, f"Python {sys.version.split()[0]} (need 3.10+)", "upgrade Python"


def _driver():
    try:
        from .drivers import detect
        yield True, f"driver detected: {detect()}", None
    except Exception as e:
        yield False, "no driver detected", str(e)


def _device():
    from . import helpers
    try:
        state = helpers.connection_state()
    except Exception as e:
        yield False, "connection check failed", str(e)
        return
    hints = {
        "no-adb": "install platform-tools (developer.android.com/tools/releases/platform-tools)",
        "no-device": "plug the phone, enable Developer options + USB debugging",
        "unauthorized": "tap Allow on the phone's USB-debugging prompt",
        "offline": "replug the cable or run `adb reconnect`",
        "not-running": "open iPhone Mirroring and connect the phone",
        "no-window": "connect the phone in iPhone Mirroring",
        "blocked": "connect the phone; if it says 'iPhone in Use', lock the iPhone",
    }
    yield state == "ready", f"connection state: {state}", hints.get(state)


def _capture():
    import os
    from . import helpers
    try:
        path, b = helpers.screenshot()
        size = os.path.getsize(path)
        yield size > 10000, f"screenshot ok ({size} bytes, bounds {b})", \
            "blank capture - grant Screen Recording to the terminal, then restart it"
    except Exception as e:
        yield False, "screenshot failed", str(e)


def _ocr():
    from . import helpers
    if helpers.driver().has_ui_tree:
        yield True, "element tree: uiautomator (OCR not needed)", None
        return
    try:
        from . import ocr
        yield True, f"OCR backend: {ocr.backend()}", None
    except Exception as e:
        yield False, "no OCR backend", str(e)


def _ollama():
    try:
        import ollama
    except ImportError:
        yield False, "ollama python package", "pip install ollama"
        return
    try:
        models = ollama.list()
        if isinstance(models, dict):
            names = [m.get("name", "") for m in models.get("models", [])]
        else:
            names = [getattr(m, "model", "") for m in models.models]
    except Exception as e:
        yield False, "ollama server", f"is `ollama serve` running? {e}"
        return
    vision = [n for n in names if "vision" in n or "vl" in n.lower()]
    yield bool(vision), f"ollama models: {', '.join(names) or '(none)'}", \
        "pull a vision model: ollama pull qwen2.5vl:7b  (or llama3.2-vision:11b)"
