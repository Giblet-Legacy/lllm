"""
lllm.py — LLLM v0.1 entry point: the session and the REPL

Function:
    The Voice of The Legacy. Each turn runs the four layers in order —
    understand → know → decide → speak — and produces a reply and a
    trace. Claims are re-read from P9 on every turn (read-only), so a
    claim committed through the Cockpit is visible on the next question.
    `python lllm.py` starts the REPL; `--once TEXT` answers one input
    (for scripts and Termux checks). Every reply prints its trace.

Public API:
    1. Session(db_path)          — .turn(text) -> (reply, trace)
    2. format_trace(trace) -> str (from traces)
    3. default_db_path(env=None) -> str
    4. main(argv=None) -> int

Tier:     Tier 1 — Consumer (LLLM, The Voice)
Depends:  standard library; P9's forge.db, read-only (SPEC §12)
Spec:     SPEC.md 0.1.0
Version:  0.1.0-dev
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import decide  # noqa: E402
import know  # noqa: E402
import speak  # noqa: E402
import traces  # noqa: E402
import understand  # noqa: E402

format_trace = traces.format_trace


# ---------------------------------------------------------------------------
# 3. default_db_path
#    SPEC §12: --db, else $FORGE_HOME/forge.db, else ~/.forge/forge.db.
# ---------------------------------------------------------------------------
def default_db_path(env=None):
    env = os.environ if env is None else env
    home = env.get("FORGE_HOME") or os.path.join(os.path.expanduser("~"), ".forge")
    return os.path.join(home, "forge.db")


# ---------------------------------------------------------------------------
# 1. Session
# ---------------------------------------------------------------------------
class Session:
    """One conversation: the database path and the previous turn's trace."""

    # 1a. __init__
    def __init__(self, db_path):
        self.db_path = db_path
        self.last_trace = None

    # 1b. turn — understand, know, decide, speak; then the trace.
    def turn(self, text):
        parsed = understand.parse(text)
        loaded = know.load(self.db_path)
        plan = decide.decide(parsed, loaded, self.last_trace)
        if isinstance(plan["slots"], list):
            parts = [speak.render(plan["template"], s) for s in plan["slots"]]
            reply, used = " ".join(p[0] for p in parts), parts[0][1]
        else:
            reply, used = speak.render(plan["template"], plan["slots"])
        trace = traces.build(parsed, plan, used, reply)
        self.last_trace = trace
        return reply, trace


# ---------------------------------------------------------------------------
# 4. main
# ---------------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(prog="lllm", description="LLLM v0.1 — the Voice of The Legacy (read-only).")
    p.add_argument("--db", help="P9 database (default: $FORGE_HOME/forge.db, else ~/.forge/forge.db)")
    p.add_argument("--once", metavar="TEXT", help="answer one input, print reply and trace, exit")
    p.add_argument("--no-trace", action="store_true", help="REPL only: hide the trace")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    session = Session(args.db or default_db_path())
    if args.once is not None:
        reply, trace = session.turn(args.once)
        print(reply)
        print(format_trace(trace))
        return 0
    print(f"LLLM v0.1 — reading {session.db_path} (read-only). Ctrl-D to leave.")
    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not text.strip():
            continue
        reply, trace = session.turn(text)
        print(reply)
        if not args.no_trace:
            print(format_trace(trace))
        if trace["intent"] == "farewell" and trace["reply"] == "Goodbye.":
            return 0


if __name__ == "__main__":
    sys.exit(main())
