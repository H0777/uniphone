"""MCP server: expose the phone as tools for any MCP client.

Run: uniphone-mcp   (stdio transport)
Claude Desktop config:
  {"mcpServers": {"uniphone": {"command": "uniphone-mcp"}}}
"""

_INSTRUCTIONS = (
    "Control the user's real phone (Android via adb, or iPhone via macOS "
    "Mirroring). Ask the user before outward-facing or irreversible actions: "
    "sending messages, posting, purchasing, deleting, changing settings.")


def main():
    try:
        from mcp.server.fastmcp import FastMCP, Image
    except ImportError:
        raise SystemExit("pip install mcp")
    from . import helpers

    mcp = FastMCP("uniphone", instructions=_INSTRUCTIONS)

    @mcp.tool()
    def phone_state() -> str:
        """Connection state: ready / no-device / unauthorized / blocked / ..."""
        return helpers.connection_state()

    @mcp.tool()
    def phone_screenshot() -> Image:
        """Capture the phone screen as an image."""
        path, _ = helpers.screenshot()
        return Image(path=path)

    @mcp.tool()
    def phone_elements() -> list:
        """Visible elements: [{text, x, y, w, h, clickable?}] in tap
        coordinates. Real UI tree on Android, OCR boxes on iOS."""
        return helpers.ui_tree()

    @mcp.tool()
    def phone_tap(x: float, y: float) -> str:
        """Tap at (x, y) in phone_elements coordinates."""
        helpers.tap(x, y)
        return "ok"

    @mcp.tool()
    def phone_tap_text(text: str) -> str:
        """Tap the center of a visible text label."""
        hit = helpers.tap_text(text)
        return f"tapped {hit['text']!r} @ ({hit['x']}, {hit['y']})"

    @mcp.tool()
    def phone_type(text: str) -> str:
        """Type into the focused field (tap the field first). ASCII only."""
        helpers.type_text(text)
        return "ok"

    @mcp.tool()
    def phone_swipe(direction: str) -> str:
        """Swipe 'up' | 'down' | 'left' | 'right' (finger motion)."""
        helpers.swipe(direction)
        return "ok"

    @mcp.tool()
    def phone_key(key: str) -> str:
        """Press 'home' | 'back' | 'enter' | 'delete' | 'app_switcher'."""
        helpers.press(key)
        return "ok"

    @mcp.tool()
    def phone_open_app(name: str) -> str:
        """Open an app by name (Android: package id or fuzzy match)."""
        return f"opened {helpers.open_app(name)}"

    mcp.run()


if __name__ == "__main__":
    main()
