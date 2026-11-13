"""
test_lllm_v0_1_2.py — LLLM v0.1.2 (face text, aspects) test suite

Function:
    Executable expression of SPEC_V0_1_2.md. Written before the 0.1.2
    modules and run red first. The FIXTURE.md contract must hold
    unchanged; repo cubes are written with the fixture's own P9 writer.

Functions in this file (pytest-collected):
    1. test_fixture_unchanged
    2. test_status_question_speaks_fact_text
    3. test_text_words_rank
    4. test_aspects_answer
    5. test_other_faces_never_spoken
    6. test_opposite_polarity_aspect_clarifies
    7. test_text_slot_locked
    8. test_new_modules_stdlib_only

Helpers:
    9.  cubes — fixture: a P9 db with three ledger-layer cubes
    10. _short

Tier:     Tier 1 — Consumer (The Voice)
Spec:     SPEC_V0_1_2.md 0.1.2
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import ast
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fixture_p9  # noqa: E402
import lllm  # noqa: E402
import lllm_v0_1_2 as v2  # noqa: E402

STATUS = "ledger_v2 is frozen at 2.0.0; 18/18 tests pass (v1 5, v2 13)."
DESIGN = "LF-only, strict line form, refuses foreign signers."
PURPOSE = "The hash-chained, append-only ledger."


# 10. _short
def _short(claim_id):
    return claim_id[:12]


# 9. cubes
@pytest.fixture
def cubes(tmp_path):
    db = str(tmp_path / "forge.db")
    p9 = fixture_p9._p9()
    p9.init_db(db)
    w = lambda cap: fixture_p9._write(p9, db, cap)  # noqa: E731
    ids = {
        "status": w({"subject": "ledger-layer", "object": "status", "face": "FACT", "polarity": "affirm",
                     "FACT": STATUS, "OPINION": "secret opinion", "FICTION": "secret fiction",
                     "UNKNOWN": "secret question?"}),
        "design": w({"subject": "ledger-layer", "object": "hardening", "face": "FACT", "polarity": "affirm",
                     "FACT": DESIGN}),
        "purpose": w({"subject": "ledger-layer", "object": "P4 Ledger", "face": "FACT", "polarity": "affirm",
                      "FACT": PURPOSE}),
        "plain": w({"subject": "sky", "object": "blue", "face": "FACT", "polarity": "affirm",
                    "FACT": "The sky is blue."}),
    }
    return db, ids


# 1. test_fixture_unchanged
def test_fixture_unchanged(tmp_path):
    db = str(tmp_path / "forge.db")
    fixture_p9.build_fixture(db)
    fixture_p9.seed_self_model(db)
    queries = ["what is the sky?", "is the sky blue?", "is the sky green?", "what is the grass?",
               "is the moon cheese?", "is the sun hot?", "what is the door?", "is the tide late?",
               "is the cat a dog?", "what does the earth orbit?", "who are you?", "how did you work that out?",
               "the moon is cheese", "hello", "thanks", "what is the fire?", "what do you mean?",
               "does the earth orbit the star?", "is the grass green?", "is the fire cold?", "what is a volcano?",
               "what is blue?", "the river is wide", "cheers"]
    old, new = lllm.Session(db), v2.Session(db)
    for q in queries:
        r1, t1 = old.turn(q)
        r2, t2 = new.turn(q)
        assert (r2, t2["plan"], t2["template"]) == (r1, t1["plan"], t1["template"]), q


# 2. test_status_question_speaks_fact_text
def test_status_question_speaks_fact_text(cubes):
    db, ids = cubes
    reply, trace = v2.Session(db).turn("what is the status of the ledger-layer?")
    assert reply == f"ledger-layer (status): {STATUS} [{_short(ids['status'])}]"
    assert trace["plan"] == "answer" and trace["template"] == "answer_text"
    plain, _ = v2.Session(db).turn("is the sky blue?")
    assert plain == f"Yes. sky is blue. [{_short(ids['plain'])}]"  # no extra text: 0.1.1 wording


# 3. test_text_words_rank
def test_text_words_rank(cubes):
    db, ids = cubes
    reply, trace = v2.Session(db).turn("is the ledger-layer frozen?")
    assert trace["cited"] == [ids["status"]] and STATUS in reply


# 4. test_aspects_answer
def test_aspects_answer(cubes):
    db, ids = cubes
    reply, trace = v2.Session(db).turn("what is the ledger-layer?")
    assert trace["plan"] == "answer" and trace["template"] == "answer_aspects"
    lines = reply.split("\n")
    assert len(lines) == 3 and set(trace["cited"]) == {ids["status"], ids["design"], ids["purpose"]}
    assert f"ledger-layer (hardening): {DESIGN} [{_short(ids['design'])}]" in lines
    assert all(line.startswith("ledger-layer (") for line in lines)


# 5. test_other_faces_never_spoken
def test_other_faces_never_spoken(cubes):
    db, _ = cubes
    s = v2.Session(db)
    for q in ("what is the status of the ledger-layer?", "what is the ledger-layer?", "is the ledger-layer secret?"):
        reply, _ = s.turn(q)
        assert "secret" not in reply


# 6. test_opposite_polarity_aspect_clarifies
def test_opposite_polarity_aspect_clarifies(cubes):
    db, ids = cubes
    neg = fixture_p9._write(fixture_p9._p9(), db, {"subject": "ledger-layer", "object": "status", "face": "FACT",
                                                    "polarity": "negate", "FACT": "ledger_v2 is not frozen yet."})
    reply, trace = v2.Session(db).turn("what is the status of the ledger-layer?")
    assert trace["plan"] == "clarify" and set(trace["cited"]) == {ids["status"], neg}


# 7. test_text_slot_locked
def test_text_slot_locked():
    slots = {"subject": "s", "object": "o", "text": "the signed words", "claim_id": "abc"}
    assert v2.speak.render("answer_text", slots) == ("s (o): the signed words [abc]", "answer_text")
    out, used = v2.speak.render("answer_yes_text", slots, {"answer_yes_text": "Yes. {subject} said something [{claim_id}]"})
    assert used == "answer_text" and "the signed words" in out


# 8. test_new_modules_stdlib_only
def test_new_modules_stdlib_only():
    allowed = set(sys.stdlib_module_names) | {"know", "decide", "speak", "traces", "understand", "lllm"}
    for rel in ("lllm_v0_1_2.py", "know/v0_1_2.py", "decide/v0_1_2.py", "speak/v0_1_2.py"):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for name in names:
                assert name.split(".")[0] in allowed, (rel, name)
