"""Tests for run.py resource lookup, driver detection, and the agent-loop
history trim."""
import sys
from unittest.mock import patch

import pytest

from uniphone.agent_loop import _drop_old_images
from uniphone.drivers import get_driver


# --- run.py: bundled SKILL.md lookup ---

def test_resource_text_from_repo_checkout():
    from uniphone.run import _resource_text
    text = _resource_text("SKILL.md")
    assert "uniphone" in text
    assert "Consent" in text  # a section only SKILL.md has


def test_resource_text_missing_raises():
    from uniphone.run import _resource_text
    with pytest.raises(SystemExit, match="no-such-doc.md"):
        _resource_text("no-such-doc.md")


# --- drivers/__init__.py: factory + detection ---

def test_get_driver_unknown_name():
    with pytest.raises(ValueError, match="unknown driver"):
        get_driver("nokia-3310")


def test_get_driver_android_with_serial():
    with patch.dict("os.environ", {"UNIPHONE_SERIAL": "emulator-5554"}):
        drv = get_driver("android")
    assert drv.name == "android"
    assert drv.serial == "emulator-5554"


def test_detect_nothing_available():
    import subprocess
    with patch.dict("os.environ", {"UNIPHONE_DRIVER": ""}), \
         patch("uniphone.drivers.subprocess.run",
               side_effect=FileNotFoundError("no adb")), \
         patch.object(sys, "platform", "win32"):
        with pytest.raises(RuntimeError, match="No device found"):
            from uniphone.drivers import detect
            detect()


# --- agent_loop: screenshot trimming ---

def test_drop_old_images_keeps_only_latest_ready():
    history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "step 1", "images": ["a.png"]},
        {"role": "assistant", "content": "{...}"},
        {"role": "user", "content": "step 2", "images": ["b.png"]},
    ]
    _drop_old_images(history)
    assert all("images" not in m for m in history)
    # caller then appends the new image-carrying message
    history.append({"role": "user", "content": "step 3", "images": ["c.png"]})
    assert [m.get("images") for m in history if "images" in m] == [["c.png"]]


def test_drop_old_images_empty_history():
    _drop_old_images([])  # must not raise


# --- helpers: agent workspace seeding ---

def test_seed_agent_workspace_from_bundled_template(tmp_path):
    from uniphone import helpers
    target = tmp_path / "agent_helpers.py"
    helpers._seed_agent_workspace(target)
    assert target.exists()
    assert "def tap_icon" in target.read_text(encoding="utf-8")


def test_resolve_workspace_prefers_repo_checkout(tmp_path, monkeypatch):
    from uniphone import helpers
    monkeypatch.delenv("UNIPHONE_AGENT_WORKSPACE", raising=False)
    repo_ws = tmp_path / "agent-workspace"
    repo_ws.mkdir()
    with patch.object(helpers, "REPO_ROOT", tmp_path):
        assert helpers._resolve_agent_workspace() == repo_ws


def test_resolve_workspace_env_var_wins(tmp_path, monkeypatch):
    from uniphone import helpers
    monkeypatch.setenv("UNIPHONE_AGENT_WORKSPACE", str(tmp_path / "env-ws"))
    assert helpers._resolve_agent_workspace() == tmp_path / "env-ws"


def test_resolve_workspace_user_default(tmp_path, monkeypatch):
    from uniphone import helpers
    monkeypatch.delenv("UNIPHONE_AGENT_WORKSPACE", raising=False)
    with patch.object(helpers, "REPO_ROOT", tmp_path / "nonexistent"), \
         patch.object(helpers.Path, "home", return_value=tmp_path / "home"):
        assert (helpers._resolve_agent_workspace()
                == tmp_path / "home" / ".uniphone" / "agent-workspace")
