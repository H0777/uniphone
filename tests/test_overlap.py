from uniphone.helpers import _overlap, _text_set


def test_overlap_identical():
    a = frozenset(["hello", "world"])
    assert _overlap(a, a) == 1.0


def test_overlap_disjoint():
    a = frozenset(["a", "b"])
    b = frozenset(["c", "d"])
    assert _overlap(a, b) == 0.0


def test_overlap_partial():
    a = frozenset(["a", "b", "c"])
    b = frozenset(["b", "c", "d"])
    # intersection=2, union=4 -> 0.5
    assert _overlap(a, b) == 0.5


def test_overlap_empty():
    assert _overlap(frozenset(), frozenset()) == 0.0
    assert _overlap(frozenset(["a"]), frozenset()) == 0.0


def test_text_set_strips_whitespace():
    boxes = [{"text": "  hello  "}, {"text": ""}, {"text": " "}]
    result = _text_set(boxes)
    assert result == frozenset(["hello"])
