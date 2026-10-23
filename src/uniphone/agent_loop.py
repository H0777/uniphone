"""Local agent loop: an Ollama vision model drives the phone.

The model sees a screenshot + the element tree each step and replies with one
JSON action. Works with any vision model Ollama can run (qwen2.5vl,
llama3.2-vision, ...). Usage:
    uniphone agent "open Notes and create a note called shopping"
"""
from __future__ import annotations

import json, logging, re
from typing import Any

_log = logging.getLogger("uniphone.agent")

SYSTEM_PROMPT = """You control a {platform} phone through a harness. Each step you receive:
1) a screenshot of the phone, 2) the visible elements as text @ (x, y) center
coordinates in the tap coordinate space.

Reply with EXACTLY ONE JSON object - no prose, no markdown fences:
{{"action": "tap_text", "text": "Sign in"}}          - preferred when the target has visible text
{{"action": "tap", "x": 540, "y": 1200}}             - for icons without labels
{{"action": "type", "text": "hello world"}}          - types into the focused field (tap it first)
{{"action": "swipe", "direction": "up|down|left|right"}}
{{"action": "scroll", "direction": "up|down"}}       - up reveals content below
{{"action": "open_app", "name": "Notes"}}
{{"action": "key", "key": "home|back|enter|delete"}}
{{"action": "wait", "seconds": 2}}
{{"action": "done", "result": "what you accomplished or found"}}

Rules:
- One action per reply. You get a fresh screenshot and element list after each.
- Verify the result of your previous action before continuing.
- If two attempts change nothing, try a different approach.
- Never send, post, purchase, delete, or change settings unless the task
  explicitly asks for it.
- When the task is complete, reply with done.
"""

_RISKY_WORDS = re.compile(
    r"\b(send|post|purchase|buy|delete|pay|publish|share|confirm)\b", re.I)


def run_agent(task: str, model: str = "qwen2.5vl:7b", max_steps: int = 30,
              assume_yes: bool = False, verbose: bool = True) -> dict[str, Any]:
    try:
        import ollama
    except ImportError:
        raise SystemExit(f"pip install ollama   # and: ollama pull {model}")
    from . import helpers

    helpers.ensure_device()
    info = helpers.screen_info()
    history = [{"role": "system",
                "content": SYSTEM_PROMPT.format(platform=info["driver"])}]

    for step in range(1, max_steps + 1):
        tree = helpers.ui_tree()
        shot, b = helpers.screenshot()
        elements = "\n".join(
            f"- {e['text']!r} @ ({e['x']:.0f}, {e['y']:.0f})"
            + (" [clickable]" if e.get("clickable") else "")
            for e in tree[:100]) or "(no visible text)"
        obs = (f"Step {step}/{max_steps}. Tap space: origin "
               f"({b['x']:.0f},{b['y']:.0f}), size {b['w']:.0f}x{b['h']:.0f}.\n"
               f"Elements:\n{elements}")
        # keep the screenshot only on the newest user message - resending
        # every past image each step blows the context window
        _drop_old_images(history)
        content = f"Task: {task}\n\n{obs}" if step == 1 else obs
        history.append({"role": "user", "content": content, "images": [shot]})

        resp = ollama.chat(model=model, messages=history)
        msg = resp["message"]["content"] if isinstance(resp, dict) \
            else resp.message.content
        history.append({"role": "assistant", "content": msg})

        act = _parse_action(msg)
        if act is None:
            history.append({"role": "user", "content":
                            "Invalid reply. Respond with ONE JSON action object."})
            continue
        _log.info("[%d] %s", step, json.dumps(act, ensure_ascii=False))
        if verbose:
            print(f"[{step}] {json.dumps(act, ensure_ascii=False)}")
        if act.get("action") == "done":
            return {"ok": True, "steps": step, "result": act.get("result", "")}
        if _RISKY_WORDS.search(json.dumps(act)) and not assume_yes:
            try:
                answer = input(f"Step {step}: allow risky action {act}? [y/N] "
                               ).strip().lower()
            except EOFError:  # piped/scheduled run - nobody can confirm
                answer = ""
            if answer != "y":
                return {"ok": False, "steps": step,
                        "result": "stopped before a risky action"}
        try:
            _dispatch(helpers, act)
        except Exception as e:
            history.append({"role": "user", "content": f"Action failed: {e}"})
            continue
        helpers.wait_stable()
    return {"ok": False, "steps": max_steps, "result": "max steps reached"}


def _drop_old_images(history: list[dict[str, Any]]) -> None:
    """Strip screenshot payloads from every message but the newest user one."""
    for m in history:
        m.pop("images", None)


def _parse_action(msg: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", msg, re.S)
    if not m:
        return None
    try:
        act = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return act if isinstance(act, dict) and "action" in act else None


def _dispatch(helpers: Any, act: dict[str, Any]) -> None:
    a = act.get("action")
    if a == "tap":
        helpers.tap(float(act["x"]), float(act["y"]))
    elif a == "tap_text":
        helpers.tap_text(act["text"])
    elif a == "type":
        helpers.type_text(act["text"])
    elif a == "swipe":
        helpers.swipe(act["direction"])
    elif a == "scroll":
        helpers.scroll_screen(act.get("direction", "up"))
    elif a == "open_app":
        helpers.open_app(act["name"])
    elif a == "key":
        helpers.press(act["key"])
    elif a == "wait":
        helpers.wait(float(act.get("seconds", 1)))
    else:
        raise ValueError(f"unknown action {a!r}")
