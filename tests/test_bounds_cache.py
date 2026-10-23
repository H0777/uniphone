import time
from unittest.mock import patch
from uniphone.drivers.ios_mirror import IOSMirrorDriver


def _create_driver():
    with (
        patch("sys.platform", "darwin"),
        patch("pathlib.Path.exists", return_value=True),
    ):
        return IOSMirrorDriver()


def test_bounds_cached_within_ttl():
    driver = _create_driver()
    win = {"x": 10, "y": 20, "w": 300, "h": 600, "id": 123}
    with patch.object(driver, "find_window", return_value=win) as mock_find:
        b1 = driver.bounds()
        b2 = driver.bounds()
        assert b1 == win
        assert b2 == win
        assert mock_find.call_count == 1


def test_bounds_refreshed_after_ttl():
    driver = _create_driver()
    win1 = {"x": 10, "y": 20, "w": 300, "h": 600, "id": 123}
    win2 = {"x": 15, "y": 25, "w": 300, "h": 600, "id": 123}
    with patch.object(driver, "find_window", side_effect=[win1, win2]) as mock_find:
        with patch("time.monotonic", side_effect=[100.0, 103.0]):
            b1 = driver.bounds()
            b2 = driver.bounds()
            assert b1 == win1
            assert b2 == win2
            assert mock_find.call_count == 2
