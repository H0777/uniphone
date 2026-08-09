"""Abstract device driver: one interface, any phone.

A driver owns the transport (how screenshots and input reach the device).
Everything above it - the element tree, tap-by-text, scroll collection, the
agent loop - is platform-neutral and lives in helpers.py / agent_loop.py.

Coordinate contract: all public methods use the driver's coordinate space,
and screenshot() returns the bounds of that space alongside the PNG, so
helpers can map image pixels to coordinates (origin + px * scale).
"""
from abc import ABC, abstractmethod


class DeviceDriver(ABC):
    name = "abstract"
    has_ui_tree = False  # True when ui_tree() returns a real accessibility tree

    # --- state ---
    @abstractmethod
    def connection_state(self):
        """'ready' | 'no-device' | 'unauthorized' | 'offline' |
        'not-running' | 'no-window' | 'no-adb'."""

    # --- eyes ---
    @abstractmethod
    def screenshot(self, path=None):
        """Capture the screen to a PNG. Returns (path, bounds) with bounds =
        {'x', 'y', 'w', 'h'} in driver coordinates for the captured image."""

    def ui_tree(self):
        """Real accessibility tree as [{text, x, y, w, h, clickable}] in driver
        coordinates, or None when the platform has none (iOS mirroring) -
        helpers then fall back to OCR as the element tree."""
        return None

    # --- hands ---
    @abstractmethod
    def tap(self, x, y):
        ...

    @abstractmethod
    def long_press(self, x, y, duration=0.8):
        ...

    @abstractmethod
    def swipe(self, x1, y1, x2, y2, duration=0.35):
        """Touch-drag from (x1, y1) to (x2, y2) over `duration` seconds."""

    def scroll(self, dy):
        """Scroll gesture at screen center, dy in driver units. Positive dy
        reveals content below (finger moves up). Default: a swipe."""
        b = self.bounds()
        cx = b["x"] + b["w"] / 2
        cy = b["y"] + b["h"] / 2
        self.swipe(cx, cy + dy / 2, cx, cy - dy / 2, duration=0.3)

    @abstractmethod
    def type_text(self, text):
        ...

    @abstractmethod
    def press_key(self, key):
        """'home' | 'back' | 'enter' | 'delete' | 'app_switcher' | ..."""

    # --- navigation ---
    def home(self):
        self.press_key("home")

    def back(self):
        self.press_key("back")

    @abstractmethod
    def open_app(self, name):
        ...

    # --- convenience ---
    def bounds(self):
        _, b = self.screenshot()
        return b
