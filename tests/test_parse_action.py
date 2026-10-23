from uniphone.agent_loop import _parse_action


def test_valid_tap():
    assert _parse_action('{"action": "tap", "x": 100, "y": 200}') == {
        "action": "tap",
        "x": 100,
        "y": 200,
    }


def test_with_prose():
    msg = 'I will tap the button {"action": "tap_text", "text": "OK"} now'
    result = _parse_action(msg)
    assert result["action"] == "tap_text"
    assert result["text"] == "OK"


def test_markdown_fences():
    msg = '```json\n{"action": "done", "result": "finished"}\n```'
    result = _parse_action(msg)
    assert result["action"] == "done"


def test_no_json():
    assert _parse_action("just some text") is None


def test_no_action_key():
    assert _parse_action('{"x": 1, "y": 2}') is None


def test_malformed_json():
    assert _parse_action('{"action": "tap"') is None


def test_nested_braces():
    assert _parse_action("{{bad}}") is None
