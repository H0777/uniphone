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

## Install

You need Python 3.10+ (`winget install Python.Python.3.12` on Windows).

```bash
git clone <repo> uniphone && cd uniphone
pip install -e ".[all]"
```

`[all]` = the local agent loop (Ollama client) + the MCP server + the OCR
engine in one command. On a Mac add iOS support: `pip install -e ".[all,ios]"`.
Minimalists: `pip install -e .` has zero hard dependencies - extras are
opt-in (`agent`, `mcp`, `ocr`, `ios`, `dev`).

Then the one platform prerequisite:

| Path | What you need |
|---|---|
| **Android** (any host OS) | [platform-tools](https://developer.android.com/tools/releases/platform-tools) so `adb` is on PATH. On the phone: enable USB debugging, plug in, tap Allow. |
| **iPhone** (macOS Sequoia+ only) | Pair iPhone Mirroring once by hand; grant the terminal Accessibility + Screen Recording. |

Verify everything:

```bash
uniphone --doctor
```

The doctor walks the ladder - Python, driver, device, capture, OCR/UI tree,
Ollama - and tells you the first thing to fix. Fix it, re-run, done.

Windows: after `pip install -e .` the `uniphone` command works from any
shell. Without installing, use the dev launcher `uniphone.cmd` from the repo.

## Use

Three surfaces, same helpers underneath.

**Script mode** - any agent that can run shell commands:

```bash
uniphone <<'PY'
open_app("com.android.settings")
tap_text("Network")
print([e["text"] for e in ui_tree()][:10])
PY
```

cmd.exe has no heredocs: save the lines to a file and run
`uniphone < script.py`.

**MCP mode** - Claude Desktop or any MCP client:

```json
{"mcpServers": {"uniphone": {"command": "uniphone-mcp"}}}
```

**Agent mode** - fully local, no cloud. Install
[Ollama](https://ollama.com) and pull a vision model, then:

```bash
ollama pull qwen2.5vl:7b          # recommended: strong UI grounding
ollama pull llama3.2-vision:11b   # alternative
uniphone agent "open Chrome and search for the weather"
uniphone agent "task" --model llama3.2-vision:11b --max-steps 20 --yes
```

Risk guardrails: before send/post/purchase/delete-style actions the agent
asks for confirmation - `--yes` skips that (only for tasks you trust).

Agents that read skills should also run `uniphone skill` and save the output
as a skill file - it teaches them the workflow (see install.md, step 4).

### CLI Quick Reference

| Command | Description |
|---|---|
| `uniphone --doctor` | Run environment diagnostics (Python, drivers, devices, screencap, OCR, Ollama) |
| `uniphone devices` | Display detected driver and device connection status |
| `uniphone skill` | Output agent instructions and skill reference (`SKILL.md`) |
| `uniphone mcp` | Launch the stdio MCP server for Claude Desktop / MCP clients |
| `uniphone agent "task"` | Run local autonomous vision loop (`--model`, `--max-steps`, `--yes`) |
| `uniphone < script.py` | Execute automation script with helpers pre-imported (`tap`, `ui_tree`, etc.) |

## Platform reality check

| | Android | iOS |
|---|---|---|
| Eyes | real UI tree (uiautomator) + screencap | screencapture + OCR (video stream, no DOM) |
| Hands | `input tap/swipe/text/keyevent` | HID CGEvents into the Mirroring window |
| Host OS | any | macOS Sequoia+ only |
| Setup | USB debugging toggle | pairing + 2 privacy permissions |

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
- `SKILL.md` / `install.md` - the agent-facing surface and detailed setup
- `agent-workspace/agent_helpers.py` - helper code the agent edits;
  auto-loaded into every script (editable installs use the repo copy; plain
  `pip install` seeds a per-user copy at `~/.uniphone/agent-workspace/`)

## Troubleshooting

- Run `uniphone --doctor` and fix the first FAIL - later checks depend on
  earlier ones.
- `uniphone devices` shows the detected driver and connection state.
- Detailed bootstrap and per-platform failure notes: `install.md`.
- The agent's own user manual (what it sees): `uniphone skill`.

## Limits

- Typing is ASCII by default: Arabic/emoji on Android need ADBKeyboard
  (install.md); iOS typing is US-keyboard Latin only.
- iOS: one phone, one session; unlocking the physical phone pauses mirroring;
  no multi-touch; DRM video renders black.
- Local vision models are weaker planners than frontier cloud models - keep
  tasks short, or use the MCP/CLI surface with a stronger agent.
- OCR sees text, not semantics - unlabeled icons need the vision model.

## License

MIT - see [LICENSE](LICENSE).
