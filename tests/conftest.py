import struct
import zlib
import pytest


@pytest.fixture
def fake_png(tmp_path):
    """Create a minimal valid PNG file for OCR tests."""
    path = tmp_path / "test.png"
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 100, 200, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xffffffff)
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + ihdr_crc
    path.write_bytes(sig + ihdr)
    return str(path)
