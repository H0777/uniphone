"""Regression tests for AndroidDriver.screenshot PNG handling.

The old code ran `data.replace(b"\\r\\n", b"\\n")` whenever it saw \\r\\n in
the first 64 bytes - but a valid PNG signature itself contains \\r\\n at
bytes 4-5, so every good capture was mangled.
"""
import struct
import zlib

import pytest
from uniphone.drivers.android import AndroidDriver, _PNG_SIG


def _make_png(width=1080, height=2400):
    """A real (decompressible) PNG at phone resolution whose stream contains
    \\r\\n byte pairs (added after IEND, where a real capture may also have
    them inside compressed chunks)."""
    raw = b"".join(b"\x00" + bytes([200, 100, 50]) * width for _ in range(height))
    idat = zlib.compress(raw)

    def chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(
            ">I", zlib.crc32(c) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", idat)
            + chunk(b"IEND", b""))


def _driver_with_adb(png_bytes):
    driver = AndroidDriver()
    driver._cmd = lambda *args, binary=False, timeout=30: png_bytes if binary else ""
    driver._shell = lambda command, **kw: ""
    driver._size = (1080, 2400)
    return driver


def test_valid_png_signature_passes_through_untouched(tmp_path):
    """A well-formed capture must be written byte-for-byte - including any
    \\r\\n pairs in the compressed IDAT data."""
    png = _make_png() + b"\x0d\x0a\x0d\x0a" * 20  # pad IDAT with \r\n pairs
    driver = _driver_with_adb(png)
    path, bounds = driver.screenshot(str(tmp_path / "s.png"))
    assert path == str(tmp_path / "s.png")
    assert bounds == {"x": 0, "y": 0, "w": 1080, "h": 2400}
    written = open(path, "rb").read()
    assert written == png  # no rewriting at all
    assert written.startswith(_PNG_SIG)


def test_mangled_signature_raises_loudly(tmp_path):
    """A stream whose signature was mangled by a line-ending-translating
    shell cannot be repaired (the signature itself contains \\r\\n), so the
    driver must fail loudly instead of writing a corrupt file."""
    good = _make_png()
    mangled = good.replace(b"\r\n", b"\n")
    driver = _driver_with_adb(mangled)
    with pytest.raises(RuntimeError, match="did not return a valid PNG"):
        driver.screenshot(str(tmp_path / "s.png"))
    assert not (tmp_path / "s.png").exists()


def test_unrepairable_signature_raises(tmp_path):
    """Corruption beyond line-ending translation must fail loudly, not write
    a broken file."""
    bad = b"\x89PNGxx xx" + b"\x00" * 32
    driver = _driver_with_adb(bad)
    with pytest.raises(RuntimeError):
        driver.screenshot(str(tmp_path / "s.png"))


def test_non_png_output_raises(tmp_path):
    driver = _driver_with_adb(b"error: device offline\n")
    with pytest.raises(RuntimeError, match="did not return a valid PNG"):
        driver.screenshot(str(tmp_path / "s.png"))
