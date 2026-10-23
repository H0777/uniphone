import logging
import os
import sys
from pathlib import Path

USAGE = """Usage:
  uniphone <<'PY'
  print(screen_info())
  PY

Commands:
  uniphone agent "task" [--model qwen2.5vl:7b] [--driver android] [--max-steps 30] [--yes]
  uniphone devices            show detected driver + connection state
  uniphone mcp                run the MCP server (stdio)
  uniphone skill              print the agent skill text (SKILL.md)
  uniphone --doctor           diagnose setup

Env: UNIPHONE_DRIVER=android|ios-mirror   UNIPHONE_SERIAL=<adb serial>
"""


def _resource_text(name: str) -> str:
    """Bundled docs (SKILL.md): packaged copy first, repo checkout fallback."""
    try:
        import importlib.resources
        f = importlib.resources.files("uniphone").joinpath(name)
        if f.is_file():
            return f.read_text(encoding="utf-8")
    except (ImportError, FileNotFoundError, NotImplementedError):
        pass
    p = Path(__file__).resolve().parent.parent.parent / name
    if p.exists():
        return p.read_text(encoding="utf-8")
    raise SystemExit(f"{name} not found - reinstall uniphone or run it from the repo")


def main():
    if sys.platform == "win32":
        # Arabic OCR text in errors / agent output would crash a redirected
        # pipe under the default cp1252
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, OSError):
                pass
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("UNIPHONE_DEBUG") else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    args = sys.argv[1:]
    if args and args[0] in {"-h", "--help"}:
        print(USAGE)
        return
    if args and args[0] in {"--doctor", "doctor"}:
        from .admin import run_doctor
        sys.exit(run_doctor())
    if args and args[0] == "skill":
        print(_resource_text("SKILL.md"), end="")
        return
    if args and args[0] == "devices":
        from . import helpers
        try:
            print(f"driver: {helpers.driver().name}")
            print(f"state:  {helpers.connection_state()}")
        except RuntimeError as e:
            print(f"no usable device: {e}")
            sys.exit(1)
        return
    if args and args[0] == "mcp":
        from .mcp_server import main as mcp_main
        mcp_main()
        return
    if args and args[0] == "agent":
        _agent(args[1:])
        return
    if args or sys.stdin.isatty():
        sys.exit(USAGE)
    code = sys.stdin.read()
    if not code.strip():
        sys.exit(USAGE)
    from . import helpers
    g = {k: v for k, v in vars(helpers).items() if not k.startswith("_")}
    g["__name__"] = "__main__"
    # SECURITY: exec() runs arbitrary user-supplied code from stdin.
    # This is intentional — uniphone is a CLI tool the user runs locally,
    # and script mode is equivalent to `python -c`. No sandboxing is applied.
    exec(code, g)


def _agent(argv):
    import argparse
    p = argparse.ArgumentParser(
        prog="uniphone agent",
        description="Run a local Ollama vision model that drives the phone.",
    )
    p.add_argument("task", help='task for the agent, e.g. "open Notes"')
    p.add_argument("--model", default="qwen2.5vl:7b")
    p.add_argument("--driver", default=None,
                   help="android | ios-mirror (default: auto-detect)")
    p.add_argument("--max-steps", type=int, default=30)
    p.add_argument("--yes", action="store_true",
                   help="auto-approve risky actions (send/post/delete/...)")
    ns = p.parse_args(argv)
    if ns.driver:
        os.environ["UNIPHONE_DRIVER"] = ns.driver
    from .agent_loop import run_agent
    result = run_agent(ns.task, model=ns.model, max_steps=ns.max_steps,
                       assume_yes=ns.yes)
    print(result)
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
