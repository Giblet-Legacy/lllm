"""
test_lllm.py — LLLM test suite (v0.1.0)

Function:
    Executable expression of SPEC.md §13 (v0.1 acceptance criteria).
    Runs against the fixture P9 database.

Tier:    Tier 1 — LLLM
Spec:    SPEC.md v0.1.0
Licence: MSL-1.0
"""

import os
import sys
import json
import sqlite3
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Import the pipeline (will fail until built)
import lllm_pipeline

FIXTURE_DB = os.path.join(HERE, "fixture", "forge.db")


@pytest.fixture
def fixture_db(monkeypatch):
    """Points the pipeline at the fixture database."""
    monkeypatch.setenv("FORGE_HOME", os.path.join(HERE, "fixture"))
    return FIXTURE_DB


@pytest.fixture
def empty_db(tmp_path, monkeypatch):
    """Points the pipeline at an empty P9 database."""
    db = tmp_path / "forge.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE claims (
            claim_id TEXT PRIMARY KEY, signer TEXT NOT NULL,
            capsule TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1,
            superseded_by TEXT, created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    monkeypatch.setenv("FORGE_HOME", str(tmp_path))
    lllm_pipeline.reset()
    return str(db)


# ---------------------------------------------------------------------------
# 1. Empty P9
# ---------------------------------------------------------------------------
def test_empty_p9_returns_unknown(empty_db):
    result = lllm_pipeline.run("is the sky blue?")
    assert result["plan"] == "unknown"


# ---------------------------------------------------------------------------
# 2. Single active match → answer
# ---------------------------------------------------------------------------
def test_single_match_answers(fixture_db):
    result = lllm_pipeline.run("is the sky blue?")
    assert result["plan"] == "answer"
    assert "active-sky" in result["trace"]["claim_ids_used"]


# ---------------------------------------------------------------------------
# 3. Superseded and inactive excluded
# ---------------------------------------------------------------------------
def test_superseded_claim_excluded(fixture_db):
    result = lllm_pipeline.run("is the moon cheese?")
    used = result["trace"]["claim_ids_used"]
    assert "superseded-old" not in used
    assert "superseded-new" in used


def test_inactive_claim_excluded(fixture_db):
    result = lllm_pipeline.run("is the earth flat?")
    assert "inactive-claim" not in result["trace"]["claim_ids_used"]


# ---------------------------------------------------------------------------
# 4. No polarity → excluded, trace records why
# ---------------------------------------------------------------------------
def test_missing_polarity_excluded(fixture_db):
    result = lllm_pipeline.run("is water wet?")
    excluded = result["trace"]["excluded"]
    reasons = [e["reason"] for e in excluded]
    assert "polarity_missing" in reasons


# ---------------------------------------------------------------------------
# 5. Competing claims
# ---------------------------------------------------------------------------
def test_competing_disagree_clarifies(fixture_db):
    # "is the apple ripe?" matches both apple claims on subject only;
    # neither object (red/green) is in terms, so both score equally and
    # disagree on object. Clarify fires.
    result = lllm_pipeline.run("is the apple ripe?")
    assert result["plan"] == "clarify"


def test_clarify_requires_same_subject(fixture_db):
    # "is the earth flat?" -- earth has no matching active claim, but
    # sky/sun/etc all score 1. They are not about the same subject, so
    # clarify must NOT fire. Fall back to the highest scorer (which is
    # still a poor match, but the honest plan is answer).
    result = lllm_pipeline.run("is the earth flat?")
    assert result["plan"] != "clarify", "clarify fired on unrelated subjects"


def test_competing_agree_answers_both(fixture_db):
    result = lllm_pipeline.run("is the sun hot?")
    assert result["plan"] == "answer"
    used = result["trace"]["claim_ids_used"]
    assert "agree-hot-1" in used
    assert "agree-hot-2" in used


# ---------------------------------------------------------------------------
# 6. Self-model
# ---------------------------------------------------------------------------
def test_self_query_bootstrapped(fixture_db):
    result = lllm_pipeline.run("who are you?")
    assert result["plan"] == "explain_self"
    assert "self-identity" in result["trace"]["claim_ids_used"]


def test_self_query_not_bootstrapped(empty_db):
    result = lllm_pipeline.run("who are you?")
    assert result["plan"] == "unknown"


# ---------------------------------------------------------------------------
# 7. Trace query
# ---------------------------------------------------------------------------
def test_trace_query_before_any_reply_returns_unknown(empty_db):
    result = lllm_pipeline.run("how did you work that out?")
    assert result["plan"] == "unknown"


# ---------------------------------------------------------------------------
# 8. Statement → acknowledge
# ---------------------------------------------------------------------------
def test_statement_acknowledge(fixture_db):
    result = lllm_pipeline.run("the sky is purple")
    assert result["plan"] == "acknowledge"


# ---------------------------------------------------------------------------
# 9. Social
# ---------------------------------------------------------------------------
def test_greeting(fixture_db):
    result = lllm_pipeline.run("hello")
    assert result["plan"] == "social"


def test_farewell(fixture_db):
    result = lllm_pipeline.run("goodbye")
    assert result["plan"] == "social"


# ---------------------------------------------------------------------------
# 10. Every reply prints a trace
# ---------------------------------------------------------------------------
def test_trace_has_required_fields(fixture_db):
    result = lllm_pipeline.run("is the sky blue?")
    trace = result["trace"]
    for key in ("intent", "terms", "plan", "reason", "candidates", "excluded", "template", "slots", "claim_ids_used"):
        assert key in trace, f"trace missing key: {key}"


# ---------------------------------------------------------------------------
# 11. P9 is read-only
# ---------------------------------------------------------------------------
def test_p9_not_modified_by_statement(fixture_db):
    import hashlib
    with open(fixture_db, "rb") as f:
        before = hashlib.sha256(f.read()).hexdigest()
    lllm_pipeline.run("the sky is purple")
    with open(fixture_db, "rb") as f:
        after = hashlib.sha256(f.read()).hexdigest()
    assert before == after, "P9 was modified"


# ---------------------------------------------------------------------------
# 12. Stdlib only
# ---------------------------------------------------------------------------
def test_no_external_imports():
    """Pipeline must only import stdlib + sibling primitives (v0.1: none)."""
    forbidden = ["requests", "flask", "fastapi", "numpy", "cryptography"]
    with open(os.path.join(HERE, "lllm_pipeline.py")) as f:
        source = f.read()
    for mod in forbidden:
        assert f"import {mod}" not in source
        assert f"from {mod}" not in source
