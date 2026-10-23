<div align="center">

# uniphone

**Connect any LLM to any phone.**

Android over plain ADB · iPhone over the macOS Mirroring window · fully
local with Ollama, no cloud at all.

A thin, editable harness: your agent gets eyes (screenshot + a real UI tree)
and hands (tap, type, swipe) on a real phone. No root, no companion app, no
jailbreak, no WebDriverAgent.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![tests](https://github.com/H0777/uniphone/actions/workflows/tests.yml/badge.svg)](https://github.com/H0777/uniphone/actions/workflows/tests.yml)
[![Android host](https://img.shields.io/badge/Android-any%20host%20OS-blue)](#platform-reality-check)
[![iOS host](https://img.shields.io/badge/iOS-macOS%20Sequoia%2B-lightgrey)](#platform-reality-check)

```text
$ uniphone agent "open Chrome and search for the weather"   # example session
[1] {"action": "open_app", "name": "com.android.chrome"}
[2] {"action": "tap", "x": 540, "y": 190}
[3] {"action": "type", "text": "weather today"}
[4] {"action": "key", "key": "enter"}
[5] {"action": "done", "result": "Forecast for today: 24°C, clear skies"}
```

**Install** · [Usage](#usage) · [MCP](#mcp-mode) · [Cloud](#cloud--network-android-no-cable) · [How it works](#how-it-works) · [Limits](#limits)

</div>

## Why uniphone

- **Agent-agnostic** — Claude Code, Codex, any MCP client, or a fully local
  Ollama vision model. The phone is exposed through three interchangeable
  surfaces (script / MCP / local agent loop); nothing is tied to one vendor.
- **Local-first** — the whole loop can run offline: model, screen
  understanding, and control on your machine.
- **Real UI tree on Android** — `uiautomator` gives every visible string with
  tap-ready coordinates, sharper than OCR. iOS falls back to Vision OCR over
  the mirroring video stream.
- **Swappable transports** — one abstract `DeviceDriver`; add a new phone
  transport by implementing ~8 methods.
- **Honest diagnostics** — `uniphone --doctor` walks the dependency ladder
  (Python → driver → device → capture → OCR → model) and tells you the first
  thing to fix.
- **Guardrails built in** — outward-facing actions (send / post / purchase /
  delete) require confirmation; consent rules ship in the agent-facing skill.

## Install

You need Python 3.10+ (`winget install Python.Python.3.12` on Windows).

```bash
git clone https://github.com/H0777/uniphone.git
cd uniphone
pip install -e ".[all]"
```

`[all]` = the local agent loop (Ollama client) + the MCP server + the OCR
engine in one command. On a Mac add iOS support: `pip install -e ".[all,ios]"`.
Minimalists: `pip install -e .` has zero hard dependencies — extras are
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

> [!TIP]
> The doctor walks the ladder — Python, driver, device, capture, OCR/UI
> tree, Ollama — and tells you the first thing to fix. Fix it, re-run, done.

Windows: after `pip install -e .` the `uniphone` command works from any
shell. Without installing, use the dev launcher `uniphone.cmd` from the repo.

### Cloud / network Android (no cable)

Any adb endpoint works — a rented cloud Android, or a second phone on Wi-Fi
(Android 11+ wireless debugging: pair once with `adb pair IP:PORT`, enter
the code on the phone):

```bash
uniphone connect 10.0.0.5:5555    # adb connect + verified state check
```

If several adb devices are attached, pick one: `set UNIPHONE_SERIAL=...`
(Windows) or `export UNIPHONE_SERIAL=...`. Slow cloud links:
`set UNIPHONE_ADB_TIMEOUT=60` (seconds).

> [!WARNING]
> A cloud provider sees everything on the screen. Don't sign in to accounts
> you wouldn't share.

## Usage

Three surfaces, same helpers underneath.

### Script mode

Any agent that can run shell commands:

```bash
uniphone <<'PY'
open_app("com.android.settings")
tap_text("Network")
print([e["text"] for e in ui_tree()][:10])
PY
```

cmd.exe has no heredocs: save the lines to a file and run
`uniphone < script.py`.

### MCP mode

Claude Desktop or any MCP client:

```json
{"mcpServers": {"uniphone": {"command": "uniphone-mcp"}}}
```

### Agent mode (fully local, no cloud)

Install [Ollama](https://ollama.com) and pull a vision model, then:

```bash
ollama pull qwen2.5vl:7b          # recommended: strong UI grounding
ollama pull llama3.2-vision:11b   # alternative
uniphone agent "open Chrome and search for the weather"
uniphone agent "task" --model llama3.2-vision:11b --max-steps 20 --yes
```

Risk guardrails: before send/post/purchase/delete-style actions the agent
asks for confirmation — `--yes` skips that (only for tasks you trust).

Agents that read skills should also run `uniphone skill` and save the output
as a skill file — it teaches them the workflow (see install.md, step 4).

### CLI Quick Reference

| Command | Description |
|---|---|
| `uniphone --doctor` | Run environment diagnostics (Python, drivers, devices, screencap, OCR, Ollama) |
| `uniphone connect <host:port>` | Connect a network/cloud Android (`adb connect` + verified state) |
| `uniphone devices` | Display detected driver and device connection status |
| `uniphone skill` | Output agent instructions and skill reference (`SKILL.md`) |
| `uniphone mcp` | Launch the stdio MCP server for Claude Desktop / MCP clients |
| `uniphone agent "task"` | Run local autonomous vision loop (`--model`, `--max-steps`, `--yes`) |
| `uniphone < script.py` | Execute automation script with helpers pre-imported (`tap`, `ui_tree`, etc.) |

## How it works

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

- `src/uniphone/drivers/` — the transports (add your own: one ABC)
- `src/uniphone/helpers.py` — the primitives pre-imported into scripts
- `src/uniphone/agent_loop.py` — the local Ollama agent (screenshot + tree
  → JSON action → verify → repeat); only the newest screenshot is sent each
  step, so long tasks don't blow the context window
- `src/uniphone/mcp_server.py` — the phone as MCP tools
- `SKILL.md` / `install.md` — the agent-facing surface and detailed setup
- `agent-workspace/agent_helpers.py` — helper code the agent edits;
  auto-loaded into every script (editable installs use the repo copy; plain
  `pip install` seeds a per-user copy at `~/.uniphone/agent-workspace/`)

## Platform reality check

| | Android | iOS |
|---|---|---|
| Eyes | real UI tree (uiautomator) + screencap | screencapture + OCR (video stream, no DOM) |
| Hands | `input tap/swipe/text/keyevent` | HID CGEvents into the Mirroring window |
| Host OS | any | macOS Sequoia+ only |
| Setup | USB debugging toggle | pairing + 2 privacy permissions |

## Limits

- Typing is ASCII by default: Arabic/emoji on Android need ADBKeyboard
  (install.md); iOS typing is US-keyboard Latin only.
- iOS: one phone, one session; unlocking the physical phone pauses mirroring;
  no multi-touch; DRM video renders black.
- Local vision models are weaker planners than frontier cloud models — keep
  tasks short, or use the MCP/CLI surface with a stronger agent.
- OCR sees text, not semantics — unlabeled icons need the vision model.
- This is the user's real phone. uniphone asks before outward-facing or
  irreversible actions, and never connects the phone for you — allowing the
  USB prompt, pairing Mirroring, unlocking the screen are physical,
  human-only steps.

## Roadmap

- [ ] Cloud-device rental lifecycle (`uniphone cloud ls/start/stop`) per
      provider — the transport itself already works today via
      [`uniphone connect`](#cloud--network-android-no-cable)
- [ ] Cloud iPhone — needs a provider with a documented control API (the
      driver slot is ready: implement `DeviceDriver` over HTTPS)
- [ ] Arabic README variant

## Contributing

Issues and PRs are welcome. For code changes:

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q    # must stay green
```

Keep the drivers thin — logic that works on any phone belongs in
`helpers.py`.

## Credits

Inspired by and partially ported from
[ShawnPana/phone-harness](https://github.com/ShawnPana/phone-harness) (MIT) —
same idea, generalized: the transport is swappable and the agent surface is
agent-agnostic.

## License

[MIT](LICENSE) — see [LICENSE](LICENSE).
