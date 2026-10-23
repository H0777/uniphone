"""Cross-platform phone control.

Core helpers live here; the agent-editable layer lives in
agent-workspace/agent_helpers.py and is auto-loaded below. Everything works
in driver coordinates - screen_info() tells you that space's bounds.
"""
from __future__ import annotations

import hashlib, importlib.util, logging, os, time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .drivers.base import DeviceDriver

from . import ocr as _ocr
from .drivers import get_driver

_log = logging.getLogger("uniphone.helpers")

CORE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CORE_DIR.parent.parent
AGENT_WORKSPACE = Path(
    os.environ.get("UNIPHONE_AGENT_WORKSPACE", REPO_ROOT / "agent-workspace"))

_DRIVER = None


def driver() -> DeviceDriver:
    """The active DeviceDriver (UNIPHONE_DRIVER=android|ios-mirror, else auto)."""
    global _DRIVER
    if _DRIVER is None:
        _DRIVER = get_driver()
    return _DRIVER


def set_driver(name: str) -> DeviceDriver:
    global _DRIVER
    _DRIVER = get_driver(name)
    return _DRIVER


# --- session / state ---

# Text on the iOS not-connected interstitials. Reconnecting is a PHYSICAL
# action only the user can do - never tap through these.
_BLOCKED_MARKERS = ("iphone in use", "lock your iphone", "mirroring ended",
                    "to connect")


def connection_state() -> str:
    """'ready' | 'blocked' | driver state ('no-device', 'unauthorized',
    'not-running', 'no-window', ...)."""
    state = driver().connection_state()
    if state != "ready":
        _log.debug("connection state: %s", state)
        return state
    if driver().has_ui_tree:
        _log.debug("connection state: ready")
        return "ready"  # real tree: no interstitial OCR needed
    path, b = driver().screenshot()
    texts = " ".join(o["text"] for o in _ocr.recognize(path, b)).lower()
    res = "blocked" if any(m in texts for m in _BLOCKED_MARKERS) else "ready"
    _log.debug("connection state: %s", res)
    return res


def ensure_device() -> None:
    """Raise with user-facing instructions unless the phone is ready."""
    state = connection_state()
    if state == "ready":
        return
    if driver().name == "android":
        msgs = {
            "no-adb": "adb not found. Install Android platform-tools and make "
                      "sure `adb` is on PATH.",
            "no-device": "No Android device. Plug the phone in (or `adb connect "
                         "ip:port`), enable USB debugging, then retry.",
            "unauthorized": "The phone hasn't authorized this computer. Check the "
                            "phone and tap Allow on the USB debugging prompt.",
            "offline": "The device is offline. Replug or run `adb reconnect`.",
        }
        raise RuntimeError(msgs.get(state, f"adb state: {state}"))
    msgs = {
        "not-running": "iPhone Mirroring isn't running. Open the app and connect "
                       "your phone, then retry - reconnecting is physical.",
        "no-window": "iPhone Mirroring is open but no phone is connected. Connect "
                     "your phone in the app, then retry.",
        "blocked": "Mirroring is paused (connect / 'iPhone in Use' screen). Open "
                   "iPhone Mirroring, connect, and if it says 'iPhone in Use', "
                   "LOCK your iPhone. Then retry.",
    }
    raise RuntimeError(msgs.get(state, f"state: {state}"))


# --- eyes ---

def screenshot(path: str | None = None) -> tuple[str, dict[str, float]]:
    """(path, bounds). View the PNG to see the phone."""
    return driver().screenshot(path)


def screen_info() -> dict[str, Any]:
    path, b = driver().screenshot()
    w, h = _ocr.image_size(path)
    return {"driver": driver().name, "bounds": b, "img_px": [w, h]}


def ui_tree() -> list[dict[str, Any]]:
    """The element tree: real accessibility nodes on Android, OCR boxes on
    iOS. [{text, x, y, w, h, (clickable)}] in driver coordinates."""
    tree = driver().ui_tree()
    return tree if tree is not None else ocr()


def ocr(min_confidence: float = 0.3) -> list[dict[str, Any]]:
    path, b = driver().screenshot()
    return [o for o in _ocr.recognize(path, b) if o["confidence"] >= min_confidence]


def find_text(query: str, exact: bool = False) -> list[dict[str, Any]]:
    q = query.lower()
    return [o for o in ui_tree()
            if (o["text"].lower() == q if exact else q in o["text"].lower())]


def tap_text(query: str, index: int = 0, exact: bool = False) -> dict[str, Any]:
    """Find text on screen and tap its center. Raises with what IS visible."""
    hits = find_text(query, exact=exact)
    if not hits:
        visible = [o["text"] for o in ui_tree()][:30]
        raise RuntimeError(f"no visible text matches {query!r}; saw: {visible}")
    hit = hits[index]
    driver().tap(hit["x"], hit["y"])
    return hit


# --- hands ---

def tap(x: float, y: float) -> None:
    driver().tap(x, y)


def long_press(x: float, y: float, duration: float = 0.8) -> None:
    driver().long_press(x, y, duration)


def type_text(text: str) -> None:
    driver().type_text(text)


def press(key: str) -> None:
    """press('home'|'back'|'enter'|'delete'|'app_switcher'|...)."""
    driver().press_key(key)


def home() -> None:
    driver().home()
    time.sleep(0.8)


def back() -> None:
    driver().back()
    time.sleep(0.8)


def open_app(name: str) -> str:
    return driver().open_app(name)


def swipe(direction: str, distance: float = 0.4) -> None:
    """swipe('up'|'down'|'left'|'right') - finger motion; 'up' scrolls down."""
    b = driver().bounds()
    cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    dx = {"left": -1, "right": 1}.get(direction, 0) * b["w"] * distance
    dy = {"up": -1, "down": 1}.get(direction, 0) * b["h"] * distance
    if not dx and not dy:
        raise ValueError(f"unknown direction {direction!r}")
    driver().swipe(cx - dx / 2, cy - dy / 2, cx + dx / 2, cy + dy / 2,
                   duration=0.12)


def scroll(amount: float = 0.6) -> None:
    """Scroll at screen center; amount is a fraction of screen height.
    Positive reveals content below."""
    b = driver().bounds()
    driver().scroll(b["h"] * amount)


# --- scrolling through lists ---

def _content_texts(top_frac: float = 0.06, bottom_frac: float = 0.92) -> list[dict[str, Any]]:
    """Element tree of the scrollable content area, excluding the status bar
    at top and the nav strip at bottom."""
    b = driver().bounds()
    top = b["y"] + b["h"] * top_frac
    bot = b["y"] + b["h"] * bottom_frac
    return [o for o in ui_tree() if top < o["y"] < bot]


def _text_set(boxes: list[dict[str, Any]]) -> frozenset[str]:
    return frozenset(o["text"].strip() for o in boxes if o["text"].strip())


def _overlap(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard overlap: ~1.0 = same screen, low = it moved."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def scroll_screen(direction: str = "up", amount: float = 0.6, settle: float = 2.5,
                  moved_thresh: float = 0.6) -> dict[str, Any]:
    """One scroll, then wait for the screen to settle (so lazy-load resolves
    before judging movement). direction 'up' reveals content below.

    Returns {moved, overlap, before, after, boxes}. `moved` is decided by
    whether the SCREEN moved, never by the caller's parser."""
    sign = {"up": 1, "down": -1}.get(direction)
    if sign is None:
        raise ValueError(f"direction must be 'up' or 'down', got {direction!r}")
    before = _text_set(_content_texts())
    b = driver().bounds()
    driver().scroll(sign * b["h"] * amount)
    time.sleep(0.4)
    prev_boxes, prev = None, None
    deadline = time.time() + settle
    while time.time() < deadline:
        boxes = _content_texts()
        cur = _text_set(boxes)
        if cur == prev:
            break
        prev, prev_boxes = cur, boxes
        time.sleep(0.35)
    after = prev or frozenset()
    return {"moved": _overlap(before, after) < moved_thresh,
            "overlap": round(_overlap(before, after), 3),
            "before": before, "after": after, "boxes": prev_boxes or []}


def scroll_until(done: Callable[[list[dict[str, Any]]], Any], direction: str = "up",
                 amount: float = 0.6, max_scrolls: int = 60, settle: float = 2.5) -> Any:
    """Scroll until done(boxes) is truthy or the list stops moving."""
    boxes = _content_texts()
    hit = done(boxes)
    if hit:
        return hit
    stale = 0
    for _ in range(max_scrolls):
        res = scroll_screen(direction, amount, settle)
        hit = done(res["boxes"])
        if hit:
            return hit
        stale = 0 if res["moved"] else stale + 1
        if stale >= 2:
            return None
        time.sleep(0.8)
    return None


def scroll_collect(extract: Callable[[list[dict[str, Any]]], list[Any]] | None = None,
                   key: Callable[[Any], Any] | None = None, direction: str = "up",
                   amount: float = 0.6, max_scrolls: int = 400, end_after: int = 3,
                   settle: float = 2.5, on_progress: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Scroll a list top-to-bottom, extracting and de-duping items each
    screen, until the list reaches its true end.

    Returns {items, stop, scrolls}; stop is 'reached-end' or 'max-scrolls'."""
    extract = extract or (lambda boxes: [o["text"].strip() for o in boxes
                                         if o["text"].strip()])
    key = key or (lambda x: x)
    seen, order = set(), []

    def ingest(boxes):
        new = 0
        for item in extract(boxes):
            k = key(item)
            if k in seen:
                continue
            seen.add(k)
            order.append(item)
            new += 1
        return new

    ingest(_content_texts())
    stale = 0
    for i in range(1, max_scrolls + 1):
        res = scroll_screen(direction, amount, settle)
        new = ingest(res["boxes"])
        if on_progress:
            on_progress(i, len(order), new, res["moved"], res["overlap"])
        stale = 0 if res["moved"] else stale + 1
        if stale >= end_after:
            return {"items": order, "stop": "reached-end", "scrolls": i}
        time.sleep(0.8)
    return {"items": order, "stop": "max-scrolls", "scrolls": max_scrolls}


# --- timing ---

def wait(seconds: float = 1.0) -> None:
    time.sleep(seconds)


def wait_stable(timeout: float = 6.0, interval: float = 0.5, settle: int = 2) -> bool:
    """Wait until `settle` consecutive captures are identical (animation done)."""
    prev, same = None, 0
    deadline = time.time() + timeout
    while time.time() < deadline:
        path, _ = driver().screenshot()
        digest = hashlib.md5(Path(path).read_bytes()).hexdigest()
        same = same + 1 if digest == prev else 0
        if same >= settle - 1:
            return True
        prev = digest
        time.sleep(interval)
    return False


def _load_agent_helpers():
    p = AGENT_WORKSPACE / "agent_helpers.py"
    if not p.exists():
        return
    spec = importlib.util.spec_from_file_location("uniphone_agent_helpers", p)
    if not spec or not spec.loader:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, value in vars(module).items():
        if not name.startswith("_"):
            globals()[name] = value
    _log.debug("loaded agent helpers from %s", p)


_load_agent_helpers()
