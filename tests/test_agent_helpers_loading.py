from pathlib import Path
from unittest.mock import patch


def test_broken_agent_helpers_does_not_crash(tmp_path):
    """A syntax error in agent_helpers.py must log a warning, not crash."""
    helpers_file = tmp_path / "agent_helpers.py"
    helpers_file.write_text("def broken(:\n  pass\n")  # SyntaxError
    with patch("uniphone.helpers.AGENT_WORKSPACE", tmp_path):
        from uniphone.helpers import _load_agent_helpers
        _load_agent_helpers()


def test_raising_agent_helpers_does_not_crash(tmp_path):
    """A runtime error in agent_helpers.py must log a warning, not crash."""
    helpers_file = tmp_path / "agent_helpers.py"
    helpers_file.write_text("raise RuntimeError('boom')\n")
    with patch("uniphone.helpers.AGENT_WORKSPACE", tmp_path):
        from uniphone.helpers import _load_agent_helpers
        _load_agent_helpers()
