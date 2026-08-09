"""iOS driver via the macOS iPhone Mirroring window (macOS Sequoia+).

The window is a video stream: macOS accessibility sees nothing inside it, so
there is no UI tree (ui_tree() returns None and helpers fall back to OCR),
and input must be synthesized at the HID level with the window frontmost.
Ported from ShawnPana/phone-harness (MIT).
"""
import subprocess, sys, tempfile, time
from pathlib import Path

from .base import DeviceDriver

if sys.platform == "darwin":
    import Quartz
    from AppKit import NSRunningApplication, NSWorkspace

APP_NAME = "iPhone Mirroring"
BUNDLE_ID = "com.apple.ScreenContinuity"
APP_PATH = "/System/Applications/iPhone Mirroring.app"

TMP = Path(tempfile.gettempdir()) / "uniphone"
TMP.mkdir(exist_ok=True)


class IOSMirrorDriver(DeviceDriver):
    name = "ios-mirror"
    has_ui_tree = False

    def __init__(self):
        if sys.platform != "darwin":
            raise RuntimeError("the ios-mirror driver needs macOS (iPhone Mirroring)")
        if not Path(APP_PATH).exists():
            raise RuntimeError("iPhone Mirroring app not found - needs macOS Sequoia+")

    # --- window / app state ---
    def find_window(self):
        """{x, y, w, h, id} of the mirroring window in screen points, or None."""
        wins = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID) or []
        for w in wins:
            if w.get("kCGWindowOwnerName") == APP_NAME and w.get("kCGWindowLayer", 1) == 0:
                b = w["kCGWindowBounds"]
                if b["Width"] < 100:  # ignore panels/toolbars
                    continue
                return {"x": b["X"], "y": b["Y"], "w": b["Width"], "h": b["Height"],
                        "id": int(w["kCGWindowNumber"])}
        return None

    def running_app(self):
        apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(BUNDLE_ID)
        return apps[0] if apps else None

    def is_frontmost(self):
        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        return bool(front and front.bundleIdentifier() == BUNDLE_ID)

    def activate(self):
        """Bring the mirroring window frontmost. Does NOT launch the app -
        connecting the phone is the user's job, not the agent's."""
        app = self.running_app()
        if app is None:
            raise RuntimeError(
                f"{APP_NAME} isn't running - open it and connect your phone.")
        if not self.is_frontmost():
            app.activateWithOptions_(1 << 1)  # NSApplicationActivateIgnoringOtherApps
            time.sleep(0.5)

    def connection_state(self):
        if self.running_app() is None:
            return "not-running"
        if self.find_window() is None:
            return "no-window"
        return "ready"  # 'blocked' interstitials are detected via OCR in helpers

    # --- eyes ---
    def screenshot(self, path=None):
        """Capture the mirroring window. Returns (path, window_bounds).
        -l grabs just the window but needs it composited; fall back to a
        region capture after activate()."""
        path = str(path or TMP / "window.png")
        last = None
        for _ in range(3):
            win = self.find_window()
            if win is None:
                self.activate()
                time.sleep(0.5)
                continue
            ok, last = _run(["screencapture", "-x", "-o", "-l", str(win["id"]), path], path)
            if ok:
                return path, win
            self.activate()
            win = self.find_window() or win
            region = f"{int(win['x'])},{int(win['y'])},{int(win['w'])},{int(win['h'])}"
            ok, last = _run(["screencapture", "-x", "-R", region, path], path)
            if ok:
                return path, win
            time.sleep(0.3)
        raise RuntimeError(f"window capture failed: {last}")

    def ui_tree(self):
        return None  # video stream - OCR is the element tree

    def bounds(self):
        win = self.find_window()
        if win is None:
            self.activate()
            win = self.find_window()
        if win is None:
            raise RuntimeError(
                f"{APP_NAME} has no phone window - connect your phone.")
        return win

    # --- hands ---
    def tap(self, x, y):
        self.activate()
        _mouse(Quartz.kCGEventMouseMoved, x, y)
        time.sleep(0.1)
        _mouse(Quartz.kCGEventLeftMouseDown, x, y)
        time.sleep(0.06)
        _mouse(Quartz.kCGEventLeftMouseUp, x, y)

    def long_press(self, x, y, duration=0.8):
        self.activate()
        _mouse(Quartz.kCGEventMouseMoved, x, y)
        time.sleep(0.1)
        _mouse(Quartz.kCGEventLeftMouseDown, x, y)
        time.sleep(duration)
        _mouse(Quartz.kCGEventLeftMouseUp, x, y)

    def swipe(self, x1, y1, x2, y2, duration=0.35, steps=14):
        self.activate()
        _mouse(Quartz.kCGEventMouseMoved, x1, y1)
        time.sleep(0.1)
        _mouse(Quartz.kCGEventLeftMouseDown, x1, y1)
        for i in range(1, steps + 1):
            t = i / steps
            _mouse(Quartz.kCGEventLeftMouseDragged,
                   x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
            time.sleep(duration / steps)
        _mouse(Quartz.kCGEventLeftMouseUp, x2, y2)

    def scroll(self, dy):
        """Wheel scroll at window center (a slow touch-drag barely moves an
        iOS list; wheel events advance it deterministically)."""
        b = self.bounds()
        x, y = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        self.activate()
        _mouse(Quartz.kCGEventMouseMoved, x, y)
        time.sleep(0.1)
        steps = 10
        for _ in range(steps):
            ev = Quartz.CGEventCreateScrollWheelEvent(
                None, Quartz.kCGScrollEventUnitPixel, 1, int(-dy / steps))
            Quartz.CGEventSetLocation(ev, Quartz.CGPointMake(x, y))
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
            time.sleep(0.03)

    def press_key(self, key):
        key = key.lower()
        if key == "back":  # no shortcut - the iOS edge-swipe back gesture
            b = self.bounds()
            mid = b["y"] + b["h"] / 2
            self.swipe(b["x"] + 2, mid, b["x"] + b["w"] * 0.4, mid, duration=0.2)
            return
        combo = _KEYMAP.get(key)
        if combo is None:
            raise ValueError(f"unknown key {key!r}; have {sorted(_KEYMAP)} + 'back'")
        self._press_combo(combo)

    def type_text(self, text, delay=0.03):
        """US-layout keycodes - mirroring forwards raw HID keycodes and
        ignores unicode payloads, so non-ASCII raises."""
        self.activate()
        for i, line in enumerate(text.split("\n")):
            if i:
                self._press_combo("return")
            for ch in line:
                code, shifted = _keycode_for(ch)
                if code is None:
                    raise ValueError(f"cannot type {ch!r} via keycodes")
                for down in (True, False):
                    ev = Quartz.CGEventCreateKeyboardEvent(None, code, down)
                    if shifted:
                        Quartz.CGEventSetFlags(ev, Quartz.kCGEventFlagMaskShift)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
                    time.sleep(0.01)
                time.sleep(delay)

    # --- navigation ---
    def open_app(self, name):
        """Spotlight: Cmd+3, type the name, return."""
        self._press_combo("cmd+3")
        time.sleep(0.9)
        self.type_text(name)
        time.sleep(1.2)
        self._press_combo("return")
        time.sleep(1.5)
        return name

    def _press_combo(self, combo):
        self.activate()
        parts = combo.lower().split("+")
        key, mods = parts[-1], parts[:-1]
        if key not in _KEYCODES:
            raise ValueError(f"unknown key {key!r}")
        flags = 0
        for m in mods:
            flags |= _MODIFIERS[m]
        for down in (True, False):
            ev = Quartz.CGEventCreateKeyboardEvent(None, _KEYCODES[key], down)
            if flags:
                Quartz.CGEventSetFlags(ev, flags)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
            time.sleep(0.03)


def _run(args, path):
    r = subprocess.run(args, capture_output=True)
    ok = (r.returncode == 0 and Path(path).exists()
          and Path(path).stat().st_size > 1000)
    return ok, r.stderr.decode(errors="replace").strip()


def _mouse(etype, x, y):
    ev = Quartz.CGEventCreateMouseEvent(
        None, etype, Quartz.CGPointMake(x, y), Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


_KEYMAP = {
    "home": "cmd+1",
    "app_switcher": "cmd+2",
    "spotlight": "cmd+3",
    "enter": "return",
    "delete": "delete",
    "escape": "escape",
    "tab": "tab",
    "space": "space",
}

_KEYCODES = {
    "return": 36, "enter": 36, "tab": 48, "space": 49, "delete": 51,
    "backspace": 51, "escape": 53, "esc": 53,
    "left": 123, "right": 124, "down": 125, "up": 126,
    "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26,
    "8": 28, "9": 25, "0": 29,
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8,
    "v": 9, "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17,
    "o": 31, "u": 32, "i": 34, "p": 35, "l": 37, "j": 38, "k": 40, "n": 45,
    "m": 46,
}

_MODIFIERS = {
    "cmd": 0x100000,      # kCGEventFlagMaskCommand
    "shift": 0x020000,    # kCGEventFlagMaskShift
    "alt": 0x080000,      # kCGEventFlagMaskAlternate
    "option": 0x080000,
    "ctrl": 0x040000,     # kCGEventFlagMaskControl
}

_SHIFTED = {
    "A": "a", "B": "b", "C": "c", "D": "d", "E": "e", "F": "f", "G": "g",
    "H": "h", "I": "i", "J": "j", "K": "k", "L": "l", "M": "m", "N": "n",
    "O": "o", "P": "p", "Q": "q", "R": "r", "S": "s", "T": "t", "U": "u",
    "V": "v", "W": "w", "X": "x", "Y": "y", "Z": "z",
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6", "&": "7",
    "*": "8", "(": "9", ")": "0", "_": "-", "+": "=", ":": ";", '"': "'",
    "<": ",", ">": ".", "?": "/", "~": "`", "{": "[", "}": "]", "|": "\\",
}

_PUNCT_KEYCODES = {
    ".": 47, ",": 43, "/": 44, ";": 41, "'": 39, "[": 33, "]": 30,
    "\\": 42, "-": 27, "=": 24, "`": 50, " ": 49,
}


def _keycode_for(ch):
    """(keycode, needs_shift) for a character, or (None, False) if untypable."""
    shifted = ch in _SHIFTED
    base = _SHIFTED.get(ch, ch)
    code = _KEYCODES.get(base, _PUNCT_KEYCODES.get(base))
    return code, shifted
