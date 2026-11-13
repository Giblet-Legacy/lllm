"""
fixture_p9.py — builds the Phase 1 fixture P9 for LLLM's tests

Function:
    Writes a small P9 substrate (real schema, real signed claims, via
    P9 substrate_v3) holding every case ROADMAP Phase 1 lists: active
    claims, a superseded pair, an inactive claim, claims with missing
    and invalid polarity, a disagreeing pair, an agreeing pair, a
    negated claim, a predicate claim, an invalid capsule row, and no
    `agent://lllm` claims. The expected outcome of each test query is
    the written contract in FIXTURE.md. Test support only: the LLLM
    runtime never imports this file.

Functions:
    1. build_fixture(db_path) -> dict   (name -> claim_id)
    2. seed_self_model(db_path) -> list (claim_ids of agent://lllm claims)

Helpers:
    3. _p9     — import P9 substrate_v3 from the sibling layer
    4. _write  — write one claim capsule through P9
    5. _sql    — raw SQL for the two states P9 has no API for

Tier:     Tier 1 — Consumer (LLLM), test fixture
Depends:  P9 substrate_v3 (sibling ../substrate-layer), cryptography (via P9)
Spec:     SPEC.md 0.1.0, ROADMAP Phase 1
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import os
import sqlite3
import sys
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_HERE = os.path.dirname(os.path.abspath(__file__))
_KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))  # fixed: same ids every build


# ---------------------------------------------------------------------------
# 3. _p9
# ---------------------------------------------------------------------------
def _p9():
    path = os.path.abspath(os.path.join(_HERE, "..", "substrate-layer"))
    if path not in sys.path:
        sys.path.insert(0, path)
    import substrate_v3
    return substrate_v3


# ---------------------------------------------------------------------------
# 4. _write
#    A short sleep keeps created_at strictly increasing, so recency
#    tie-breaks are deterministic.
# ---------------------------------------------------------------------------
def _write(p9, db, capsule):
    time.sleep(0.002)
    return p9.write_claim(db, capsule, _KEY)


# ---------------------------------------------------------------------------
# 5. _sql
# ---------------------------------------------------------------------------
def _sql(db, statement, args):
    conn = sqlite3.connect(db)
    with conn:
        conn.execute(statement, args)
    conn.close()


# ---------------------------------------------------------------------------
# 1. build_fixture
# ---------------------------------------------------------------------------
def build_fixture(db_path):
    p9 = _p9()
    p9.init_db(db_path)
    ids = {}
    ids["sky"] = _write(p9, db_path, {"subject": "sky", "object": "blue", "polarity": "affirm", "face": "FACT"})
    ids["sea"] = _write(p9, db_path, {"subject": "sea", "object": "blue", "polarity": "affirm", "face": "FACT"})
    ids["grass_old"] = _write(p9, db_path, {"subject": "grass", "object": "green", "polarity": "affirm"})
    time.sleep(0.002)
    ids["grass_new"] = p9.supersede_claim(db_path, ids["grass_old"],
                                          {"subject": "grass", "object": "brown", "polarity": "affirm"}, _KEY)
    ids["moon"] = _write(p9, db_path, {"subject": "moon", "object": "cheese", "polarity": "affirm"})
    _sql(db_path, "UPDATE claims SET is_active = 0, superseded_by = NULL WHERE claim_id = ?", (ids["moon"],))
    ids["sun"] = _write(p9, db_path, {"subject": "sun", "object": "hot"})
    ids["fire"] = _write(p9, db_path, {"subject": "fire", "object": "cold", "polarity": "maybe"})
    ids["door_open"] = _write(p9, db_path, {"subject": "door", "object": "open", "polarity": "affirm"})
    ids["door_shut"] = _write(p9, db_path, {"subject": "door", "object": "shut", "polarity": "affirm"})
    ids["tide_a"] = _write(p9, db_path, {"subject": "tide", "object": "late", "polarity": "affirm", "note": "a"})
    ids["tide_b"] = _write(p9, db_path, {"subject": "tide", "object": "late", "polarity": "affirm", "note": "b"})
    ids["cat"] = _write(p9, db_path, {"subject": "cat", "object": "dog", "polarity": "negate"})
    ids["earth"] = _write(p9, db_path, {"subject": "earth", "predicate": "orbits", "object": "star", "polarity": "affirm"})
    ids["broken"] = "f" * 64
    _sql(db_path, "INSERT INTO claims (claim_id, signer, capsule, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
         (ids["broken"], "did:key:z6Mkfixture", "{not json", "2026-11-13T00:00:00+00:00"))
    return ids


# ---------------------------------------------------------------------------
# 2. seed_self_model
#    Bootstrap claims about LLLM itself (README "Bootstrapping").
# ---------------------------------------------------------------------------
def seed_self_model(db_path):
    p9 = _p9()
    return [
        _write(p9, db_path, {"subject": "agent://lllm", "predicate": "is", "object": "the voice of the legacy",
                             "polarity": "affirm"}),
        _write(p9, db_path, {"subject": "agent://lllm", "predicate": "answers from", "object": "active claims",
                             "polarity": "affirm"}),
    ]
