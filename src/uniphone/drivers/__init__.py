"""Driver factory + auto-detection."""
import os, subprocess, sys
from pathlib import Path

from .base import DeviceDriver

__all__ = ["DeviceDriver", "get_driver", "detect"]


def detect():
    """'android' if adb sees a device, else 'ios-mirror' on a Mac with the app."""
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True,
                             timeout=10).stdout.decode()
        if any(l.split()[-1] == "device"
               for l in out.splitlines()[1:] if l.strip()):
            return "android"
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    if sys.platform == "darwin" and Path(
            "/System/Applications/iPhone Mirroring.app").exists():
        return "ios-mirror"
    raise RuntimeError(
        "No device found. Connect an Android with USB debugging (adb devices), "
        "or pair iPhone Mirroring on macOS - or set "
        "UNIPHONE_DRIVER=android|ios-mirror.")


def get_driver(name=None):
    name = (name or os.environ.get("UNIPHONE_DRIVER") or detect()).lower()
    if name == "android":
        from .android import AndroidDriver
        return AndroidDriver(serial=os.environ.get("UNIPHONE_SERIAL"))
    if name in {"ios", "ios-mirror", "mirror"}:
        from .ios_mirror import IOSMirrorDriver
        return IOSMirrorDriver()
    raise ValueError(f"unknown driver {name!r}: use 'android' or 'ios-mirror'")
