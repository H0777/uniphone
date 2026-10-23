"""Android driver over plain ADB.

No root, no companion app, any host OS. Eyes: `screencap` plus a REAL UI
tree from `uiautomator dump` (better than OCR - every node with text, bounds
and clickable). Hands: `input tap/swipe/text/keyevent`.
"""
import logging, re, subprocess, tempfile, time
from pathlib import Path

from .base import DeviceDriver

_log = logging.getLogger("uniphone.android")

TMP = Path(tempfile.gettempdir()) / "uniphone"
TMP.mkdir(exist_ok=True)

_KEYCODES = {
    "home": "KEYCODE_HOME",
    "back": "KEYCODE_BACK",
    "enter": "KEYCODE_ENTER",
    "delete": "KEYCODE_DEL",
    "tab": "KEYCODE_TAB",
    "space": "KEYCODE_SPACE",
    "app_switcher": "KEYCODE_APP_SWITCH",
    "power": "KEYCODE_POWER",
    "volume_up": "KEYCODE_VOLUME_UP",
    "volume_down": "KEYCODE_VOLUME_DOWN",
}

_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


class AndroidDriver(DeviceDriver):
    name = "android"
    has_ui_tree = True

    def __init__(self, serial=None, adb="adb"):
        self.serial = serial
        self.adb = adb
        self._size = None
        self._adbkb = None

    def _has_adbkeyboard(self) -> bool:
        if self._adbkb is None:
            imes = self._shell("ime list -s")
            self._adbkb = "com.android.adbkeyboard/.AdbIME" in imes
        return self._adbkb

    # --- low level ---
    def _cmd(self, *args, binary=False, timeout=30):
        _log.debug("adb %s", " ".join(args))
        cmd = [self.adb]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += list(args)
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError(
                f"adb {' '.join(args)} failed: "
                f"{r.stderr.decode(errors='replace').strip()}")
        return r.stdout if binary else r.stdout.decode(errors="replace").strip()

    def _shell(self, command, **kw):
        return self._cmd("shell", command, **kw)

    # --- state ---
    def connection_state(self):
        try:
            out = subprocess.run([self.adb, "devices"],
                                 capture_output=True, timeout=10).stdout.decode()
        except FileNotFoundError:
            return "no-adb"
        rows = [l.split() for l in out.splitlines()[1:] if l.strip()]
        rows = [r for r in rows if len(r) == 2]
        if self.serial:
            rows = [r for r in rows if r[0] == self.serial]
        if not rows:
            return "no-device"
        state = rows[0][1]
        return "ready" if state == "device" else state  # unauthorized | offline

    # --- eyes ---
    def screen_size(self):
        if self._size is None:
            out = self._shell("wm size")
            m = re.search(r"(\d+)x(\d+)", out)
            if not m:
                raise RuntimeError(f"cannot parse screen size from {out!r}")
            self._size = (int(m.group(1)), int(m.group(2)))
        return self._size

    def bounds(self):
        w, h = self.screen_size()
        return {"x": 0, "y": 0, "w": w, "h": h}

    def screenshot(self, path=None):
        path = str(path or TMP / "screen.png")
        data = self._cmd("exec-out", "screencap -p", binary=True, timeout=15)
        if b"\r\n" in data[:64]:  # some shells translate line endings
            data = data.replace(b"\r\n", b"\n")
        if data[:4] != b"\x89PNG":
            raise RuntimeError("screencap did not return a PNG")
        Path(path).write_bytes(data)
        w, h = self.screen_size()
        return path, {"x": 0, "y": 0, "w": w, "h": h}

    def ui_tree(self):
        import xml.etree.ElementTree as ET
        last = None
        root = None
        for _ in range(2):  # dump can fail on a busy accessibility service
            try:
                self._shell("uiautomator dump /sdcard/uniphone_ui.xml", timeout=20)
                xml = self._cmd("exec-out", "cat /sdcard/uniphone_ui.xml", timeout=15)
                root = ET.fromstring(xml)
                break
            except Exception as e:
                last = e
                _log.warning("uiautomator dump failed, retrying: %s", e)
                time.sleep(0.6)
        if root is None:
            raise RuntimeError(f"uiautomator dump failed: {last}")
        out = []
        for node in root.iter("node"):
            text = node.get("text") or node.get("content-desc") or ""
            if not text.strip():
                continue
            m = _BOUNDS_RE.match(node.get("bounds", ""))
            if not m:
                continue
            x1, y1, x2, y2 = map(int, m.groups())
            out.append({
                "text": text,
                "x": (x1 + x2) / 2, "y": (y1 + y2) / 2,
                "w": x2 - x1, "h": y2 - y1,
                "clickable": node.get("clickable") == "true",
            })
        _log.debug("uiautomator dump: %d elements", len(out))
        return out

    # --- hands ---
    def tap(self, x, y):
        self._shell(f"input tap {int(x)} {int(y)}")

    def long_press(self, x, y, duration=0.8):
        self._shell(f"input swipe {int(x)} {int(y)} {int(x)} {int(y)} "
                    f"{int(duration * 1000)}")

    def swipe(self, x1, y1, x2, y2, duration=0.35):
        ms = max(50, int(duration * 1000))
        self._shell(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {ms}")

    def type_text(self, text: str) -> None:
        for i, line in enumerate(text.split("\n")):
            if i:
                self.press_key("enter")
            if not line:
                continue
            try:
                line.encode("ascii")
                self._shell("input text " + _escape(line))
            except UnicodeEncodeError:
                if not self._has_adbkeyboard():
                    raise ValueError(
                        f"cannot type non-ASCII {line!r} — install ADBKeyboard "
                        "(see install.md) for Arabic/emoji")
                import base64
                encoded = base64.b64encode(line.encode("utf-8")).decode()
                self._shell(f"am broadcast -a ADB_INPUT_B64 "
                            f"--es msg {encoded} "
                            f"-n com.android.adbkeyboard/.AdbIME")

    def press_key(self, key):
        code = _KEYCODES.get(key.lower())
        if code is None:
            raise ValueError(f"unknown key {key!r}; have {sorted(_KEYCODES)}")
        self._shell(f"input keyevent {code}")

    # --- navigation ---
    def open_app(self, name):
        """Open an app by package id or fuzzy package-name match."""
        out = self._shell("pm list packages")
        pkgs = [l.replace("package:", "").strip() for l in out.splitlines()]
        pkg = name if name in pkgs else None
        if pkg is None:
            hits = [p for p in pkgs if name.lower() in p.lower()]
            if not hits:
                raise RuntimeError(
                    f"no package matching {name!r}; pass a package id "
                    "like com.example.app")
            pkg = sorted(hits, key=len)[0]
        self._shell(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1")
        time.sleep(1.5)
        return pkg


def _escape(s):
    out = []
    for ch in s:
        if ch == " ":
            out.append("%s")
        elif ch in "&<>|();$`\\\"'":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)
