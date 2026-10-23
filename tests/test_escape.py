from uniphone.drivers.android import _escape


def test_escape_plain_text():
    assert _escape("hello") == "hello"


def test_escape_spaces():
    assert _escape("hello world") == "hello%sworld"


def test_escape_shell_chars():
    assert _escape("a&b") == "a\\&b"
    assert _escape("a'b") == "a\\'b"


def test_escape_empty():
    assert _escape("") == ""


def test_escape_all_special():
    for ch in '&<>|();$`\\"\'':
        assert _escape(ch) == "\\" + ch
