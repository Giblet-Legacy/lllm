"""
lllm_v0_1_2.py — LLLM v0.1.2, the Voice that speaks a claim's signed text

Function:
    The entry point from 0.1.2 (SPEC_V0_1_2.md). The same pipeline as
    lllm.py (understand → know → decide → speak → trace), with the
    0.1.2 Know (asserted face text), Decide (aspects are not
    disagreement) and Speak (text templates). Aspects are one per line.
    `python lllm_v0_1_2.py` starts the REPL; `--once TEXT` answers one
    input. lllm.py and the 0.1 packages are frozen and not edited.

Public API:
    1. Session(db_path)          — .turn(text) -> (reply, trace)
    2. format_trace(trace) -> str (0.1's)
    3. default_db_path(env=None) -> str (0.1's)
    4. main(argv=None) -> int

Tier:     Tier 1 — Consumer (The Voice)
Depends:  understand, traces (0.1); know/v0_1_2, decide/v0_1_2, speak/v0_1_2
Spec:     SPEC_V0_1_2.md (over SPEC_V0_1_1.md and SPEC.md 0.1.0)
Version:  0.1.2
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import lllm as _v011  # noqa: E402
import traces  # noqa: E402
import understand  # noqa: E402
from decide import v0_1_2 as decide  # noqa: E402
from know import v0_1_2 as know  # noqa: E402
from speak import v0_1_2 as speak  # noqa: E402

format_trace = _v011.format_trace
default_db_path = _v011.default_db_path


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
            joiner = "\n" if plan["template"] == "answer_aspects" else " "
            reply, used = joiner.join(p[0] for p in parts), parts[0][1]
        else:
            reply, used = speak.render(plan["template"], plan["slots"])
        trace = traces.build(parsed, plan, used, reply)
        self.last_trace = trace
        return reply, trace


# ---------------------------------------------------------------------------
# 4. main
# ---------------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(prog="lllm_v0_1_2", description="LLLM v0.1.2 — the Voice of The Legacy (read-only).")
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
    print(f"LLLM v0.1.2 — reading {session.db_path} (read-only). Ctrl-D to leave.")
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
