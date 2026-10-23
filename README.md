<div align="center">

# 📱 uniphone

### Connect Any AI Agent to Any Phone

*Android over plain ADB · iPhone over macOS Mirroring · Fully local with Ollama, zero cloud required.*

A thin, editable harness giving your agent **eyes** (screencap + real UI tree) and **hands** (tap, swipe, type) on a physical or cloud phone.<br>
*No root · No companion app · No jailbreak · No WebDriverAgent.*

---

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=flat-square&logo=python&logoColor=white)](pyproject.toml)
[![Tests CI](https://img.shields.io/badge/Tests-56%20Passed-success.svg?style=flat-square&logo=pytest&logoColor=white)](tests/)
[![Platforms](https://img.shields.io/badge/Platforms-Android%20%7C%20iOS-orange.svg?style=flat-square)](https://github.com/H0777/uniphone)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://github.com/H0777/uniphone)

[**Features**](#-features) · [**Quickstart**](#-quickstart) · [**Usage Modes**](#-usage-modes) · [**CLI Reference**](#-cli-quick-reference) · [**Architecture**](#-architecture) · [**Roadmap**](#-roadmap)

---

```text
$ uniphone agent "open Chrome and search for the weather"

[1] 👁️  ui_tree()  -> Chrome icon @ (540, 190)
[2] 👆 tap(540, 190)
[3] ⌨️  type_text("weather today") + press("enter")
[4] ⏳ wait_stable() -> screen settled in 0.8s
[5] ✅ done: "Forecast: 24°C, Sunny"
```

</div>

---

## ⚡ Features

| Feature | Description |
|---|---|
| 🧠 **Agent Agnostic** | Seamlessly connects with **Claude Code**, **Codex**, **OpenAI**, **MCP clients**, or local **Ollama** vision models. |
| 👁️ **Native UI Tree + OCR** | Real accessibility tree via `uiautomator` on Android with tap-ready bounds. High-speed Vision OCR for iOS. |
| 🪟 **First-Class Windows Support** | Native `uniphone.cmd` launcher, automated UTF-8 stream handling for Arabic text, and standard CLI tools. |
| 🌐 **Cloud & Network Ready** | Connect wirelessly or to remote cloud Android instances via `uniphone connect <host:port>`. |
| 🔒 **Built-in Safety Guardrails** | Automatic confirmation before risky actions (*send, delete, pay, purchase*) with `--yes` override. |
| 🧰 **Extensible Agent Workspace** | Agents can inspect and edit their own helpers at `agent-workspace/agent_helpers.py`. |

---

## 📱 Platform Support Matrix

| Dimension | 🤖 Android | 🍏 iPhone |
|---|---|---|
| **Eyes (Vision)** | Native UI tree (`uiautomator`) + lossless `screencap` | `screencapture` + Vision OCR |
| **Hands (Input)** | Native `input tap`, `swipe`, `text`, `keyevent` | HID `CGEvents` into Mirroring window |
| **Typing Support** | ASCII default; Arabic & Emoji via `ADBKeyboard` | US-Keyboard Latin layout |
| **Host System** | Windows, macOS, Linux (Any OS) | macOS Sequoia+ (15.0+) |
| **Prerequisites** | USB Debugging enabled + `adb` on PATH | Native iPhone Mirroring paired once |

---

## 🚀 Quickstart

### 1. Installation

Ensure **Python 3.10+** is installed (`winget install Python.Python.3.12` on Windows).

```bash
# Clone the repository
git clone https://github.com/H0777/uniphone.git
cd uniphone

# Install full bundle (Local Agent Loop + MCP Server + OCR Engine)
pip install -e ".[all]"
```

> **macOS + iPhone users**: Install with iOS extras:
> ```bash
> pip install -e ".[all,ios]"
> ```
> *Minimalists*: `pip install -e .` has zero external dependencies; extras are opt-in (`agent`, `mcp`, `ocr`, `ios`, `dev`).

### 2. Verify Environment (`--doctor`)

Run the automated diagnostic check:

```bash
uniphone --doctor
```

> [!TIP]
> The doctor inspects each level of the stack: **Python → Driver → Device Connection → Screen Capture → OCR/UI Tree → Vision Model**, pointing directly to the first required fix.

---

## 🔌 Connection Modes

### Cable (USB)
- **Android**: Plug in phone with **USB Debugging** enabled, tap *Allow*.
- **iPhone**: Open macOS **iPhone Mirroring**, complete the one-time pairing.

### Wireless & Cloud Android (No Cable)
Connect to any Android device on your local Wi-Fi or in the cloud:

```bash
uniphone connect 192.168.1.50:5555
```

- **Targeting specific devices**: Set `UNIPHONE_SERIAL=<serial>`.
- **Slower network links**: Increase timeout with `UNIPHONE_ADB_TIMEOUT=60`.

> [!WARNING]
> Cloud providers can see the device screen. Avoid authenticating personal accounts on untrusted remote instances.

---

## 💻 Usage Modes

`uniphone` provides three clean surfaces powered by the same underlying helpers:

### 1. Local Autonomous Agent
Fully local vision-agent loop using **Ollama** (requires zero cloud API keys):

```bash
# Pull recommended vision model
ollama pull qwen2.5vl:7b

# Run autonomous task
uniphone agent "open Settings and turn on Dark Mode"

# Advanced parameters
uniphone agent "task" --model qwen2.5vl:7b --max-steps 25 --yes
```

### 2. MCP Server (Claude Desktop & MCP Clients)
Add `uniphone` directly into your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "uniphone": {
      "command": "uniphone-mcp"
    }
  }
}
```

### 3. Script Automation
Execute Python scripts with all driver helpers pre-imported:

```bash
# Linux / macOS
uniphone <<'PY'
open_app("com.android.settings")
tap_text("Network")
print([e["text"] for e in ui_tree()][:5])
PY

# Windows (via piping)
uniphone < script.py
```

---

## 🛠️ CLI Quick Reference

| Command | Usage & Purpose |
|---|---|
| `uniphone --doctor` | Diagnose Python, drivers, device state, screen capture, OCR, and models |
| `uniphone devices` | Inspect currently active driver and connected device status |
| `uniphone connect <host:port>` | Connect network/wireless Android device with verified state check |
| `uniphone agent "<task>"` | Launch local vision agent (`--model`, `--max-steps`, `--yes`, `--driver`) |
| `uniphone mcp` | Start stdio MCP server for Claude Desktop / Cursor / Windsurf |
| `uniphone skill` | Print agent skill workflow guide ([SKILL.md](SKILL.md)) |
| `uniphone < script.py` | Run standalone automation script with helpers pre-loaded |

---

## 🏗️ Architecture

```
+-------------------------------------------------------------------------+
|                              AGENT LAYER                                |
|    Claude Code / Codex / Cursor / MCP Client / Local Ollama Loop       |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                           UNIPHONE HELPERS                              |
|   tap(), tap_text(), swipe(), scroll_collect(), ui_tree(), wait_stable  |
|             (Pre-imported & shared across all surfaces)                 |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                         ABSTRACT DEVICE DRIVER                          |
|             screenshot / tap / swipe / type / ui_tree / keys            |
+-----------------------------------+-------------------------------------+
                 │                                     │
                 ▼                                     ▼
+-----------------------------------+ +-----------------------------------+
|          ANDROID DRIVER           | |          IOS MIRROR DRIVER        |
|  - adb exec-out screencap (PNG)   | |  - screencapture macOS window     |
|  - uiautomator XML dump           | |  - RapidOCR / Vision OCR engine   |
|  - input tap / swipe / text       | |  - CoreGraphics HID CGEvents      |
|  - ADBKeyboard (Unicode/Arabic)   | |  - Window bounds caching          |
+-----------------------------------+ +-----------------------------------+
```

---

## 🛡️ Guardrails & Safety

- **Physical confirmation**: Actions involving irreversible consequences (`send`, `post`, `buy`, `delete`) prompt for interactive confirmation.
- **Context window protection**: Past screenshot payloads are automatically pruned from the agent conversation history to avoid token bloat.
- **Physical security**: Pairing, granting USB debugging, and device unlocking remain human-only physical actions.

---

## 🗺️ Roadmap

- [x] Strict binary PNG verification for Android screencap.
- [x] Multi-platform CI with GitHub Actions matrix (Ubuntu & Windows).
- [x] First-class Windows terminal & launch support (`uniphone.cmd`).
- [x] Network/Cloud Android connect via `uniphone connect`.
- [ ] Cloud-device rental lifecycle (`uniphone cloud ls/start/stop`).
- [ ] Cloud iPhone support via remote HTTP driver adapter.
- [ ] Multilingual docs (Arabic README variant).

---

## 🤝 Contributing

Contributions and pull requests are welcome!

```bash
# Setup dev environment
pip install -e ".[dev]"

# Run full test suite (56 tests)
pytest tests/ -v
```

> Drivers should remain thin: platform-agnostic business logic belongs in `helpers.py`.

---

## 📄 License & Credits

- **License**: [MIT](LICENSE) © 2026 uniphone contributors.
- **Credits**: Inspired by and partially ported from [ShawnPana/phone-harness](https://github.com/ShawnPana/phone-harness) (MIT).
