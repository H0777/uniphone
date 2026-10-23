from unittest.mock import MagicMock, patch


def test_connection_ready_android():
    """Android driver returning 'ready' means connection_state() is 'ready'."""
    mock_drv = MagicMock()
    mock_drv.connection_state.return_value = "ready"
    mock_drv.has_ui_tree = True
    with patch("uniphone.helpers._DRIVER", mock_drv):
        from uniphone.helpers import connection_state
        assert connection_state() == "ready"


def test_connection_no_device():
    mock_drv = MagicMock()
    mock_drv.connection_state.return_value = "no-device"
    with patch("uniphone.helpers._DRIVER", mock_drv):
        from uniphone.helpers import connection_state
        assert connection_state() == "no-device"


def test_connection_ios_blocked():
    """iOS driver returning ready, but screenshot has blocked text -> blocked."""
    mock_drv = MagicMock()
    mock_drv.connection_state.return_value = "ready"
    mock_drv.has_ui_tree = False
    mock_drv.screenshot.return_value = ("fake.png", {"x": 0, "y": 0, "w": 100, "h": 200})
    fake_ocr = [{"text": "iPhone in Use", "confidence": 0.9}]
    with (
        patch("uniphone.helpers._DRIVER", mock_drv),
        patch("uniphone.ocr.recognize", return_value=fake_ocr),
    ):
        from uniphone.helpers import connection_state
        assert connection_state() == "blocked"
