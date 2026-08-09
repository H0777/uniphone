# uniphone install

Use once. For phone work, read SKILL.md.

## 1. Pick your phone path

### Android (any host OS - easiest, start here)

1. Install platform-tools so `adb` is on PATH:
   https://developer.android.com/tools/releases/platform-tools
2. On the phone: Settings > About > tap Build number 7x > Developer options >
   enable USB debugging. Plug in, then tap Allow on the RSA prompt.
3. Optional live view of the screen: scrcpy
   (https://github.com/Genymobile/scrcpy) - not required, the harness talks
   to adb directly.
4. Optional Arabic/emoji typing: ADBKeyboard
   (https://github.com/senzhk/ADBKeyBoard) - `input text` is ASCII-only.

### iPhone (needs macOS Sequoia+)

1. Pair iPhone Mirroring once by hand - the pairing prompts need the
   physical phone.
2. `pip install pyobjc-framework-Quartz pyobjc-framework-Vision pyobjc-framework-AppKit`
3. Grant the terminal Accessibility + Screen Recording in System Settings >
   Privacy & Security. Accessibility is immediate; Screen Recording takes
   effect after the terminal restarts.

## 2. The harness

```bash
git clone <your-repo-url> ~/.uniphone && cd ~/.uniphone
pip install -e .            # core (no hard deps)
pip install -e ".[ocr]"     # RapidOCR - element tree for iOS on any host
pip install -e ".[agent]"   # ollama python client (the local agent loop)
pip install -e ".[mcp]"     # MCP server
./uniphone --doctor
```

`--doctor` walks the ladder: python -> driver detected -> device state ->
capture -> OCR/UI tree -> ollama model. Fix the first FAIL; later checks
depend on earlier ones.

## 3. The local model (Ollama)

Install Ollama (https://ollama.com), then pull a vision model:

```bash
ollama pull qwen2.5vl:7b          # recommended: strong UI grounding
ollama pull llama3.2-vision:11b   # alternative
```

## 4. Register as an agent skill

So any skill-capable agent reaches for uniphone on its own:

```bash
mkdir -p ~/.claude/skills/uniphone
uniphone skill > ~/.claude/skills/uniphone/SKILL.md
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/uniphone"
uniphone skill > "${CODEX_HOME:-$HOME/.codex}/skills/uniphone/SKILL.md"
```

## 5. MCP (Claude Desktop and other MCP clients)

```json
{"mcpServers": {"uniphone": {"command": "uniphone-mcp"}}}
```

## If it fails

- Android 'unauthorized': the RSA prompt is on the phone - tap Allow.
- Android blank tree: `uiautomator dump` was busy - retry after wait_stable().
- iOS capture black: Screen Recording was granted but the terminal hasn't
  restarted since.
- iOS taps do nothing: Accessibility missing, or the mirroring window isn't
  frontmost.
