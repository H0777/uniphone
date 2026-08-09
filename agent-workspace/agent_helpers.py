"""Agent-editable helpers - auto-loaded into every uniphone script.

Add task-specific primitives here; anything defined becomes available
alongside the core helpers.
"""


def tap_icon(label, index=0):
    """Tap a Home-Screen app icon by its label.

    iOS mirroring: tapping the label text itself is a no-op - the tappable
    icon is ~35 points above the label.
    """
    from uniphone.helpers import find_text, tap
    hits = find_text(label)
    if not hits:
        raise RuntimeError(f"no Home-Screen label matching {label!r}")
    h = hits[index]
    tap(h["x"], h["y"] - 35)
    return h
