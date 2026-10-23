from unittest.mock import MagicMock, patch
import pytest
from uniphone.drivers.android import AndroidDriver


def test_type_text_non_ascii_with_adbkeyboard():
    driver = AndroidDriver()
    driver._adbkb = True
    with patch.object(driver, "_shell") as mock_shell:
        driver.type_text("مرحبا")
        mock_shell.assert_called_once()
        cmd = mock_shell.call_args[0][0]
        assert "am broadcast -a ADB_INPUT_B64" in cmd
        assert "com.android.adbkeyboard/.AdbIME" in cmd
        # Verify base64 encoding of 'مرحبا'
        import base64
        assert base64.b64encode("مرحبا".encode("utf-8")).decode() in cmd


def test_type_text_non_ascii_without_adbkeyboard():
    driver = AndroidDriver()
    driver._adbkb = False
    with pytest.raises(ValueError, match="cannot type non-ASCII"):
        driver.type_text("مرحبا")


def test_type_text_ascii_always_works():
    driver = AndroidDriver()
    with patch.object(driver, "_shell") as mock_shell:
        driver.type_text("hello")
        mock_shell.assert_called_once_with("input text hello")


def test_has_adbkeyboard_detection():
    driver = AndroidDriver()
    with patch.object(driver, "_shell", return_value="com.android.adbkeyboard/.AdbIME\ncom.google.android.inputmethod.latin/LatinIME"):
        assert driver._has_adbkeyboard() is True
        # verify caching
        assert driver._has_adbkeyboard() is True
