"""
test_lllm.py — LLLM v0.1.0 test suite (SPEC §13 acceptance criteria)

Function:
    Executable form of SPEC.md 0.1.0. Written before the code and run
    red first. Every SPEC §13 acceptance criterion is a test here, plus
    the ROADMAP mini-gates (parse table, ranking, plans, templates) and
    a check that FIXTURE.md's manifest matches what LLLM really does.

Functions in this file (pytest-collected), mapped to SPEC §13:
    1.  test_empty_p9_unknown                 — empty / missing P9 → unknown, no file created
    2.  test_single_claim_answer_cites        — answer cites its claim_id
    3.  test_superseded_and_inactive_unused   — never used, traced
    4.  test_polarity_missing_unused          — never used, trace says polarity_missing
    5.  test_disagreeing_pair_clarifies       — clarify within δ
    6.  test_agreeing_pair_cites_both         — answer citing both
    7.  test_self_query_without_self_model    — unknown
    8.  test_self_query_with_self_model       — explain_self with citations
    9.  test_trace_query_after_answer         — returns that answer's trace
    10. test_trace_query_first                — unknown
    11. test_statement_acknowledged_p9_unchanged — fixed reply, file hash unchanged
    12. test_social                           — greetings, thanks, farewells
    13. test_full_trace_printed               — parse, candidates, plan, reason, template, slots
    14. test_runtime_imports_stdlib_only      — no imports outside stdlib (P9 is the db file)
    15. test_manifest_matches_reality         — every FIXTURE.md row
    16. test_parse_table                      — mini-gate: understand
    17. test_ranking_and_worked_example       — mini-gate: know (SPEC §6 example)
    18. test_locked_slot_fallback             — mini-gate: speak
    19. test_clarify_delta_env                — δ is configurable
    20. test_repl_once                        — `python lllm.py --once` prints reply and trace

Fixtures and helpers:
    21. fixture_db — the FIXTURE.md database, built once per session
    22. session    — a fresh LLLM session on the fixture
    23. _short     — 12-character cited id
    24. _manifest  — FIXTURE.md table rows

Tier:     Tier 1 — Consumer (LLLM)
Spec:     SPEC.md 0.1.0 + SPEC_V0_1_1.md
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import ast
import hashlib
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fixture_p9  # noqa: E402
import lllm  # noqa: E402
from understand import parse  # noqa: E402
from know import score  # noqa: E402
from speak import render  # noqa: E402

RUNTIME = ["lllm.py", "understand", "know", "decide", "speak", "traces"]


# 23. _short
def _short(claim_id):
    return claim_id[:12]


# 24. _manifest
def _manifest():
    with open(os.path.join(ROOT, "FIXTURE.md"), encoding="utf-8") as f:
        text = f.read()
    table = text.split("<!-- manifest:start -->")[1].split("<!-- manifest:end -->")[0]
    rows = []
    for line in table.strip().splitlines()[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(dict(zip(["query", "intent", "plan", "template", "cites", "excluded"], cells)))
    return rows


# 21. fixture_db
@pytest.fixture(scope="session")
def fixture_db(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("p9") / "forge.db")
    ids = fixture_p9.build_fixture(path)
    return path, ids


# 22. session
@pytest.fixture
def session(fixture_db):
    return lllm.Session(fixture_db[0])


# 1. test_empty_p9_unknown
def test_empty_p9_unknown(tmp_path):
    missing = tmp_path / "absent.db"
    s = lllm.Session(str(missing))
    reply, trace = s.turn("is the sky blue?")
    assert trace["plan"] == "unknown" and reply == "I can't answer that from the substrate."
    assert not missing.exists()
    empty = tmp_path / "empty.db"
    fixture_p9._p9().init_db(str(empty))
    reply, trace = lllm.Session(str(empty)).turn("what is the sea?")
    assert trace["plan"] == "unknown"


# 2. test_single_claim_answer_cites
def test_single_claim_answer_cites(session, fixture_db):
    _, ids = fixture_db
    reply, trace = session.turn("is the sky blue?")
    assert reply == f"Yes. sky is blue. [{_short(ids['sky'])}]"
    assert trace["plan"] == "answer" and trace["slots"]["claim_id"] == _short(ids["sky"])
    assert [c["claim_id"] for c in trace["candidates"]][0] == ids["sky"]


# 3. test_superseded_and_inactive_unused
def test_superseded_and_inactive_unused(session, fixture_db):
    _, ids = fixture_db
    reply, trace = session.turn("is the grass green?")
    assert ids["grass_old"] not in [c["claim_id"] for c in trace["candidates"]]
    assert {"claim_id": ids["grass_old"], "reason": "status_excluded"} in trace["excluded"]
    assert reply == f"grass is brown. [{_short(ids['grass_new'])}]"
    reply, trace = session.turn("is the moon cheese?")
    assert trace["plan"] == "unknown"
    assert {"claim_id": ids["moon"], "reason": "status_excluded"} in trace["excluded"]


# 4. test_polarity_missing_unused
def test_polarity_missing_unused(session, fixture_db):
    _, ids = fixture_db
    reply, trace = session.turn("is the sun hot?")
    assert trace["plan"] == "unknown" and trace["candidates"] == []
    assert {"claim_id": ids["sun"], "reason": "polarity_missing"} in trace["excluded"]
    _, trace = session.turn("is the fire cold?")
    assert {"claim_id": ids["fire"], "reason": "polarity_invalid"} in trace["excluded"]


# 5. test_disagreeing_pair_clarifies
def test_disagreeing_pair_clarifies(session, fixture_db):
    _, ids = fixture_db
    reply, trace = session.turn("what is the door?")
    assert trace["plan"] == "clarify"
    assert reply == (f"I have more than one active claim that matches. One says door is shut "
                     f"[{_short(ids['door_shut'])}], another says door is open [{_short(ids['door_open'])}]. "
                     f"Which one do you mean?")


# 6. test_agreeing_pair_cites_both
def test_agreeing_pair_cites_both(session, fixture_db):
    _, ids = fixture_db
    reply, trace = session.turn("is the tide late?")
    assert trace["plan"] == "answer"
    assert reply == f"Yes. tide is late. [{_short(ids['tide_b'])}, {_short(ids['tide_a'])}]"


# 7. test_self_query_without_self_model
def test_self_query_without_self_model(session):
    reply, trace = session.turn("who are you?")
    assert trace["intent"] == "self_query" and trace["plan"] == "unknown"


# 8. test_self_query_with_self_model
def test_self_query_with_self_model(fixture_db, tmp_path):
    db = str(tmp_path / "forge.db")
    shutil.copy(fixture_db[0], db)
    self_ids = fixture_p9.seed_self_model(db)
    reply, trace = lllm.Session(db).turn("what are you?")
    assert trace["plan"] == "explain_self"
    assert reply == (f"agent://lllm answers from active claims. [{_short(self_ids[1])}] "
                     f"agent://lllm is the voice of the legacy. [{_short(self_ids[0])}]")


# 9. test_trace_query_after_answer
def test_trace_query_after_answer(session, fixture_db):
    _, ids = fixture_db
    session.turn("is the sky blue?")
    reply, trace = session.turn("how did you work that out?")
    assert trace["intent"] == "trace_query" and trace["plan"] == "trace"
    assert reply == (f"My last reply used plan answer, template answer_yes, and cited {_short(ids['sky'])}. "
                     f"The input parsed as intent question with terms is, the, sky, blue.")


# 10. test_trace_query_first
def test_trace_query_first(session):
    reply, trace = session.turn("show me your reasoning")
    assert trace["intent"] == "trace_query" and trace["plan"] == "unknown"


# 11. test_statement_acknowledged_p9_unchanged
def test_statement_acknowledged_p9_unchanged(session, fixture_db):
    before = hashlib.sha256(open(fixture_db[0], "rb").read()).hexdigest()
    reply, trace = session.turn("the river is wide")
    assert trace["plan"] == "acknowledge"
    assert reply == "Noted. That would be a proposal — it needs a human seal before I can use it."
    assert hashlib.sha256(open(fixture_db[0], "rb").read()).hexdigest() == before


# 12. test_social
def test_social(session):
    for text, reply in [("hello", "Hello. What can I look up for you?"), ("Good morning", "Hello. What can I look up for you?"),
                        ("thanks", "Goodbye."), ("thank you", "Goodbye."), ("bye", "Goodbye."), ("cheers", "Goodbye.")]:
        r, trace = session.turn(text)
        assert (r, trace["plan"]) == (reply, "social"), text


# 13. test_full_trace_printed
def test_full_trace_printed(session):
    _, trace = session.turn("is the grass green?")
    text = lllm.format_trace(trace)
    for line in ("--- trace ---", "input: is the grass green?", "intent: question", "terms: [is, the, grass, green]",
                 "negation: False", "plan: answer", "reason:", "candidates:", "excluded:", "template: answer_state",
                 "slots:", "  subject: grass", "  object: brown", "reply: grass is brown."):
        assert line in text, line
    _, trace = session.turn("hello")
    assert "candidates:\n  (none)" in lllm.format_trace(trace)


# 14. test_runtime_imports_stdlib_only
def test_runtime_imports_stdlib_only():
    local = {"understand", "know", "decide", "speak", "traces", "lllm"}
    files = []
    for entry in RUNTIME:
        path = os.path.join(ROOT, entry)
        files += [path] if path.endswith(".py") else [os.path.join(path, n) for n in os.listdir(path) if n.endswith(".py")]
    for path in files:
        for node in ast.walk(ast.parse(open(path, encoding="utf-8").read())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [(node.module or "").split(".")[0]]
            for name in names:
                assert name in sys.stdlib_module_names or name in local, f"{path}: imports {name}"


# 15. test_manifest_matches_reality
def test_manifest_matches_reality(fixture_db):
    _, ids = fixture_db
    by_id = {v: k for k, v in ids.items()}
    for row in _manifest():
        reply, trace = lllm.Session(fixture_db[0]).turn(row["query"])
        cited = [by_id[c] for c in trace["cited"]]
        excluded = [f"{by_id[e['claim_id']]}:{e['reason']}" for e in trace["excluded"]]
        assert trace["intent"] == row["intent"], row
        assert trace["plan"] == row["plan"], row
        assert trace["template"] == row["template"], row
        assert cited == ([] if row["cites"] == "-" else row["cites"].split(",")), row
        assert excluded == ([] if row["excluded"] == "-" else row["excluded"].split(",")), row


# 16. test_parse_table
def test_parse_table():
    table = [
        ("how did you work that out?", "trace_query"), ("why did you say that", "trace_query"),
        ("who are you", "self_query"), ("tell me about yourself", "self_query"),
        ("how does lllm work?", "self_query"),
        ("is the sky blue?", "question"), ("Where is the sea", "question"), ("the sea is blue?", "question"),
        ("the sky is blue", "statement"), ("not bad", "statement"),
        ("i don't understand", "clarify"), ("what do you mean?", "clarify"), ("can you clarify?", "clarify"),
        ("which one?", "clarify"), ("which one is bigger?", "question"), ("what do you mean by sky?", "clarify"),
        ("hello there", "greeting"), ("hey", "greeting"), ("good evening", "greeting"),
        ("bye", "farewell"), ("goodnight", "farewell"), ("cheers", "farewell"), ("thank you", "farewell"),
        ("", "question"),
    ]
    for text, intent in table:
        assert parse(text)["intent"] == intent, (text, parse(text)["intent"])
    p = parse("Is the sky NOT blue?")
    assert p["terms"] == ["is", "the", "sky", "not", "blue"] and p["negation"] is True
    assert parse("isn't it")["negation"] is True and parse("is it")["negation"] is False
    assert parse("what is agent://lllm?")["terms"][-1] == "agent://lllm"


# 17. test_ranking_and_worked_example
def test_ranking_and_worked_example():
    terms = parse("is the sky blue")["terms"]
    a = {"subject": "sky", "predicate": "is", "object": "blue"}
    b = {"subject": "sea", "predicate": "is", "object": "blue"}
    assert score(terms, a) == (8, 1, 1, 3)
    assert score(terms, b) == (4, 0, 1, 2)
    assert score(parse("is the moon cheese")["terms"], a)[1:3] == (0, 0)  # term-only: not a candidate
    assert score(parse("is the big sky blue")["terms"], {"subject": "big sky", "predicate": "is", "object": "blue"})[1] == 1
    assert score(parse("is the sky big")["terms"], {"subject": "big sky", "predicate": "is", "object": "x"})[1] == 0


# 18. test_locked_slot_fallback
def test_locked_slot_fallback():
    slots = {"subject": "sky", "predicate": "is", "object": "blue", "claim_id": "abc123abc123"}
    assert render("answer_yes", slots) == ("Yes. sky is blue. [abc123abc123]", "answer_yes")
    bad = {"answer_yes": "Yes. {subject} is lovely. [{claim_id}]"}
    assert render("answer_yes", slots, templates=bad) == ("sky is blue. [abc123abc123]", "answer_state")
    with pytest.raises(KeyError):
        render("no_such_template", slots)


# 19. test_clarify_delta_env
def test_clarify_delta_env(fixture_db, tmp_path, monkeypatch):
    db = str(tmp_path / "forge.db")
    shutil.copy(fixture_db[0], db)
    fixture_p9._write(fixture_p9._p9(), db, {"subject": "door", "predicate": "is", "object": "red",
                                              "polarity": "affirm", "note": "extra term red"})
    q = "is the door red?"  # red claim scores 8, open/shut 5: gap 3 > 0.8, answers
    assert lllm.Session(db).turn(q)[1]["plan"] == "answer"
    monkeypatch.setenv("LLLM_CLARIFY_DELTA", "0.5")  # δ = 4 ≥ 3, and they disagree: clarify
    assert lllm.Session(db).turn(q)[1]["plan"] == "clarify"


# 20. test_repl_once
def test_repl_once(fixture_db):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "lllm.py"), "--db", fixture_db[0], "--once", "is the sky blue?"],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("Yes. sky is blue. [") and "--- trace ---" in r.stdout
