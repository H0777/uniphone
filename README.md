# uniphone

Connect **any LLM** to **any phone** with a thin, editable harness.
Android over plain ADB (no root, no companion app, any host OS). iPhone over
the macOS Mirroring window (no jailbreak, no Xcode, no WebDriverAgent).
Driven by Claude Code, Codex, any MCP client - or a fully local Ollama
vision model, no cloud at all.

```
  agent: "open Notes and create a note"
  |
  ui_tree() -> "Notes" @ (400, 468)        (real accessibility tree on Android,
  |                                          OCR boxes on iOS)
  tap(400, 468) -> wait_stable() -> ui_tree() confirms
  done
```

Inspired by and partially ported from
[ShawnPana/phone-harness](https://github.com/ShawnPana/phone-harness) (MIT) -
same idea, generalized: the transport is swappable and the agent surface is
agent-agnostic.

## Architecture

```
+---------------------------------------------------+
|  any agent: Claude Code / Codex / MCP client /    |
|  local Ollama loop (uniphone agent "...")         |
+---------------------------------------------------+
|  helpers.py - ui_tree(), tap_text(), swipe(),     |
|  scroll_collect(), wait_stable()  (platform-free) |
+---------------------------------------------------+
|  DeviceDriver (abstract):                         |
|  screenshot / tap / swipe / type / ui_tree / keys |
+------------------+--------------------------------+
|  AndroidDriver   |  IOSMirrorDriver               |
|  adb screencap + |  screencapture + Vision OCR +  |
|  uiautomator +   |  HID CGEvents (macOS Sequoia+) |
|  input tap/swipe |                                |
+------------------+--------------------------------+
```

- `src/uniphone/drivers/` - the transports (add your own: one ABC)
- `src/uniphone/helpers.py` - the primitives pre-imported into scripts
- `src/uniphone/agent_loop.py` - the local Ollama agent (screenshot + tree
  -> JSON action -> verify -> repeat)
- `src/uniphone/mcp_server.py` - the phone as MCP tools
- `SKILL.md` / `install.md` - the agent-facing surface and bootstrap
- `agent-workspace/agent_helpers.py` - helper code the agent edits;
  auto-loaded into every script

## Quickstart (Android + Ollama, fully local)

```bash
git clone <repo> ~/.uniphone && cd ~/.uniphone
pip install -e ".[agent]"
ollama pull qwen2.5vl:7b
# phone: enable USB debugging, plug in, tap Allow
./uniphone --doctor
./uniphone agent "open Chrome and search for the weather"
```

## Script mode (any agent that can run shell commands)

```bash
uniphone <<'PY'
open_app("com.android.settings")
tap_text("Network")
print([e["text"] for e in ui_tree()][:10])
PY
```

## MCP mode

```json
{"mcpServers": {"uniphone": {"command": "uniphone-mcp"}}}
```

## Platform reality check

| | Android | iOS |
|---|---|---|
| Eyes | real UI tree (uiautomator) + screencap | screencapture + OCR (video stream, no DOM) |
| Hands | `input tap/swipe/text/keyevent` | HID CGEvents into the Mirroring window |
| Host OS | any | macOS Sequoia+ only |
| Setup | USB debugging toggle | pairing + 2 privacy permissions |

## Limits

- Typing is ASCII-only on both drivers today (ADBKeyboard fixes Android).
- iOS: one phone, one session; unlocking the physical phone pauses mirroring;
  no multi-touch; DRM video renders black.
- Local vision models are weaker planners than frontier cloud models - keep
  tasks short, or use the MCP/CLI surface with a stronger agent.
- OCR sees text, not semantics - unlabeled icons need the vision model.
