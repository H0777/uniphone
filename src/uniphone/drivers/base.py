"""Abstract device driver: one interface, any phone.

A driver owns the transport (how screenshots and input reach the device).
Everything above it - the element tree, tap-by-text, scroll collection, the
agent loop - is platform-neutral and lives in helpers.py / agent_loop.py.

Coordinate contract: all public methods use the driver's coordinate space,
and screenshot() returns the bounds of that space alongside the PNG, so
helpers can map image pixels to coordinates (origin + px * scale).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DeviceDriver(ABC):
    name: str = "abstract"
    has_ui_tree: bool = False  # True when ui_tree() returns a real accessibility tree

    # --- state ---
    @abstractmethod
    def connection_state(self) -> str:
        """'ready' | 'no-device' | 'unauthorized' | 'offline' |
        'not-running' | 'no-window' | 'no-adb'."""

    # --- eyes ---
    @abstractmethod
    def screenshot(self, path: str | None = None) -> tuple[str, dict[str, float]]:
        """Capture the screen to a PNG. Returns (path, bounds) with bounds =
        {'x', 'y', 'w', 'h'} in driver coordinates for the captured image."""

    def ui_tree(self) -> list[dict[str, Any]] | None:
        """Real accessibility tree as [{text, x, y, w, h, clickable}] in driver
        coordinates, or None when the platform has none (iOS mirroring) -
        helpers then fall back to OCR as the element tree."""
        return None

    # --- hands ---
    @abstractmethod
    def tap(self, x: float, y: float) -> None:
        ...

    @abstractmethod
    def long_press(self, x: float, y: float, duration: float = 0.8) -> None:
        ...

    @abstractmethod
    def swipe(self, x1: float, y1: float, x2: float, y2: float, duration: float = 0.35) -> None:
        """Touch-drag from (x1, y1) to (x2, y2) over `duration` seconds."""

    def scroll(self, dy: float) -> None:
        """Scroll gesture at screen center, dy in driver units. Positive dy
        reveals content below (finger moves up). Default: a swipe."""
        b = self.bounds()
        cx = b["x"] + b["w"] / 2
        cy = b["y"] + b["h"] / 2
        self.swipe(cx, cy + dy / 2, cx, cy - dy / 2, duration=0.3)

    @abstractmethod
    def type_text(self, text: str) -> None:
        ...

    @abstractmethod
    def press_key(self, key: str) -> None:
        """'home' | 'back' | 'enter' | 'delete' | 'app_switcher' | ..."""

    # --- navigation ---
    def home(self) -> None:
        self.press_key("home")

    def back(self) -> None:
        self.press_key("back")

    @abstractmethod
    def open_app(self, name: str) -> str:
        ...

    # --- convenience ---
    def bounds(self) -> dict[str, float]:
        _, b = self.screenshot()
        return b

