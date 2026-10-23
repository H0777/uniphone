"""Tests for the network/cloud Android connect flow (adb_connect) and the
remote-link timeout override."""
from unittest.mock import patch

import pytest

from uniphone.drivers.android import AndroidDriver, adb_connect


def _fake_run(*outputs):
    """subprocess.run stub returning canned stdout strings in order."""
    outs = list(outputs)

    def fake(cmd, capture_output=True, timeout=None):
        out = outs.pop(0) if outs else ""
        return type("R", (), {"stdout": out.encode(), "stderr": b"",
                              "returncode": 0})()

    return fake


def test_connect_success_reports_verified_state():
    fake = _fake_run(
        "connected to 10.0.0.5:5555\n",
        "List of devices attached\n10.0.0.5:5555\tdevice\n\n")
    with patch("uniphone.drivers.android.subprocess.run", side_effect=fake):
        assert adb_connect("10.0.0.5:5555") == "device"


def test_connect_already_connected_ok():
    fake = _fake_run(
        "already connected to 10.0.0.5:5555\n",
        "List of devices attached\n10.0.0.5:5555\tdevice\n")
    with patch("uniphone.drivers.android.subprocess.run", side_effect=fake):
        assert adb_connect("10.0.0.5:5555") == "device"


def test_connect_unauthorized_state_surfaces():
    fake = _fake_run(
        "connected to 10.0.0.5:5555\n",
        "List of devices attached\n10.0.0.5:5555\tunauthorized\n")
    with patch("uniphone.drivers.android.subprocess.run", side_effect=fake):
        assert adb_connect("10.0.0.5:5555") == "unauthorized"


def test_connect_failure_raises_with_reason():
    fake = _fake_run("failed to connect to '10.0.0.5:5555': cannot connect")
    with patch("uniphone.drivers.android.subprocess.run", side_effect=fake):
        with pytest.raises(RuntimeError, match="failed"):
            adb_connect("10.0.0.5:5555")


def test_connect_success_but_not_listed_raises():
    fake = _fake_run("connected to 10.0.0.5:5555\n",
                     "List of devices attached\n")
    with patch("uniphone.drivers.android.subprocess.run", side_effect=fake):
        with pytest.raises(RuntimeError, match="not listed"):
            adb_connect("10.0.0.5:5555")


def test_connect_appends_default_port():
    calls = []

    def fake(cmd, capture_output=True, timeout=None):
        calls.append(cmd)
        if len(calls) == 1:
            return type("R", (), {"stdout": b"connected to 10.0.0.5:5555\n",
                                  "stderr": b"", "returncode": 0})()
        return type("R", (), {"stdout": b"List of devices attached\n",
                              "stderr": b"", "returncode": 0})()

    with patch("uniphone.drivers.android.subprocess.run", side_effect=fake):
        with pytest.raises(RuntimeError, match="not listed"):
            adb_connect("10.0.0.5")
    assert calls[0][2] == "10.0.0.5:5555"  # default port appended


def test_connect_without_adb_clean_error():
    with patch("uniphone.drivers.android.subprocess.run",
               side_effect=FileNotFoundError()):
        with pytest.raises(RuntimeError, match="adb not found"):
            adb_connect("10.0.0.5:5555")


def test_connect_timeout_raises_clean():
    import subprocess

    def fake(cmd, capture_output=True, timeout=None):
        raise subprocess.TimeoutExpired(cmd, timeout)

    with patch("uniphone.drivers.android.subprocess.run", side_effect=fake):
        with pytest.raises(RuntimeError, match="timed out"):
            adb_connect("10.0.0.5:5555", timeout=5)


# --- remote-link timeout override ---

def test_adb_timeout_env_override():
    with patch.dict("os.environ", {"UNIPHONE_ADB_TIMEOUT": "45"}):
        assert AndroidDriver().timeout == 45.0


def test_adb_timeout_default():
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("UNIPHONE_ADB_TIMEOUT", None)
        assert AndroidDriver().timeout == 30.0


def test_adb_timeout_garbage_falls_back():
    with patch.dict("os.environ", {"UNIPHONE_ADB_TIMEOUT": "banana"}):
        assert AndroidDriver().timeout == 30.0
