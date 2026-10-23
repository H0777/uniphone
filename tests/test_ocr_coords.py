from unittest.mock import patch
from uniphone.ocr import image_size, recognize


def test_image_size(fake_png):
    w, h = image_size(fake_png)
    assert w == 100
    assert h == 200


def test_coordinate_mapping(fake_png):
    bounds = {"x": 0, "y": 0, "w": 1080, "h": 2400}
    fake_raw = [("Hello", 0.95, (10, 20, 80, 30))]
    with (
        patch("uniphone.ocr._rapidocr", return_value=fake_raw),
        patch("uniphone.ocr._backend", "rapidocr"),
    ):
        results = recognize(fake_png, bounds)
    assert len(results) == 1
    r = results[0]
    assert r["text"] == "Hello"
    assert r["confidence"] == 0.95
    # center x = (10 + 80/2) * (1080/100) = 50 * 10.8 = 540
    assert abs(r["x"] - 540.0) < 1
