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


def main():
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
        root = Path(__file__).resolve().parent.parent.parent
        print((root / "SKILL.md").read_text(encoding="utf-8"), end="")
        return
    if args and args[0] == "devices":
        from . import helpers
        print(f"driver: {helpers.driver().name}")
        print(f"state:  {helpers.connection_state()}")
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
    import os
    task, model, max_steps, yes = None, "qwen2.5vl:7b", 30, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--model":
            i += 1
            model = argv[i]
        elif a == "--driver":
            i += 1
            os.environ["UNIPHONE_DRIVER"] = argv[i]
        elif a == "--max-steps":
            i += 1
            max_steps = int(argv[i])
        elif a == "--yes":
            yes = True
        elif not a.startswith("--"):
            task = a
        i += 1
    if not task:
        sys.exit('usage: uniphone agent "task" [--model M] [--driver D] '
                 "[--max-steps N] [--yes]")
    from .agent_loop import run_agent
    result = run_agent(task, model=model, max_steps=max_steps, assume_yes=yes)
    print(result)
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
