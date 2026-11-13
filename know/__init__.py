"""
know — LLLM layer 2: the claim layer (P9 reader, matching, ranking)

Function:
    Reads claims from P9 read-only (SQLite mode=ro, so LLLM physically
    cannot write), maps each row to LLLM's view (SPEC §1–§4), excludes
    what may not be spoken with a reason for the trace, and scores and
    ranks candidates for a parse (SPEC §6). Self-model candidates are
    active claims whose subject is `agent://lllm` (SPEC §8).

Public API:
    1. load(db_path) -> dict          {claims, excluded, rows}
    2. score(terms, claim) -> tuple   (score, s, o, t)
    3. candidates(parse, loaded) -> (ranked, excluded_relevant)
    4. self_candidates(parse, loaded) -> list

Internal helpers:
    5. _connect_ro  — read-only connection; None if the file is missing
    6. _status      — is_active + superseded_by → active/superseded/inactive
    7. _view        — one row → (claim, None) or (None, reason)
    8. _contains    — needle tokens as a contiguous run of terms
    9. _rank_key    — score desc, then created_at desc

Tier:     Tier 1 — Consumer (LLLM), layer 2
Depends:  standard library; P9's forge.db (read-only, by schema)
Spec:     SPEC.md 0.1.0 §1–§4, §6, §12
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import json
import os
import pathlib
import sqlite3
from datetime import datetime

from understand import tokenise

SELF_SUBJECT = "agent://lllm"
POLARITIES = ("affirm", "negate")


# ---------------------------------------------------------------------------
# 5. _connect_ro
#    SPEC §12. A missing file is "zero claims": never created, never raised.
# ---------------------------------------------------------------------------
def _connect_ro(db_path):
    if not db_path or not os.path.isfile(db_path):
        return None
    return sqlite3.connect(pathlib.Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)


# ---------------------------------------------------------------------------
# 6. _status
#    SPEC §2.
# ---------------------------------------------------------------------------
def _status(is_active, superseded_by):
    if is_active == 1:
        return "active"
    return "superseded" if superseded_by else "inactive"


# ---------------------------------------------------------------------------
# 7. _view
#    SPEC §1, §3, §4: required fields, status, then polarity.
# ---------------------------------------------------------------------------
def _view(row):
    claim_id, signer, capsule_text, is_active, superseded_by, created_at = row
    try:
        capsule = json.loads(capsule_text)
    except (TypeError, ValueError):
        capsule = None
    if not isinstance(capsule, dict):
        return None, "capsule_invalid"
    subject, obj = capsule.get("subject"), capsule.get("object")
    predicate = capsule.get("predicate") or "is"
    try:
        created = datetime.fromisoformat(created_at)  # never float() (SPEC §1)
    except (TypeError, ValueError):
        created = None
    if not (isinstance(subject, str) and subject.strip() and isinstance(obj, str) and obj.strip()
            and isinstance(predicate, str) and created is not None):
        return None, "field_missing"
    claim = {"claim_id": claim_id, "subject": subject.strip(), "predicate": predicate.strip(),
             "object": obj.strip(), "polarity": capsule.get("polarity"), "source": signer or "unknown",
             "created_at": created, "status": _status(is_active, superseded_by)}
    if claim["status"] != "active":
        return claim, "status_excluded"
    if "polarity" not in capsule or capsule["polarity"] is None:
        return claim, "polarity_missing"
    if capsule["polarity"] not in POLARITIES:
        return claim, "polarity_invalid"
    return claim, None


# ---------------------------------------------------------------------------
# 1. load
#    Every row, mapped. `excluded` keeps the partial view (when there is
#    one) so the trace can name relevant exclusions.
# ---------------------------------------------------------------------------
def load(db_path):
    conn = _connect_ro(db_path)
    if conn is None:
        return {"claims": [], "excluded": [], "rows": 0}
    try:
        rows = conn.execute(
            "SELECT claim_id, signer, capsule, is_active, superseded_by, created_at FROM claims "
            "ORDER BY created_at, rowid").fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    claims, excluded = [], []
    for row in rows:
        claim, reason = _view(row)
        if reason is None:
            claims.append(claim)
        else:
            excluded.append({"claim_id": row[0], "reason": reason, "claim": claim})
    return {"claims": claims, "excluded": excluded, "rows": len(rows)}


# ---------------------------------------------------------------------------
# 8. _contains
# ---------------------------------------------------------------------------
def _contains(terms, needle):
    n = len(needle)
    return n > 0 and any(terms[i:i + n] == needle for i in range(len(terms) - n + 1))


# ---------------------------------------------------------------------------
# 2. score
#    SPEC §6: 3*s + 2*o + t, t = distinct shared tokens, capped at 5.
# ---------------------------------------------------------------------------
def score(terms, claim):
    s = int(_contains(terms, tokenise(claim["subject"])))
    o = int(_contains(terms, tokenise(claim["object"])))
    claim_tokens = set(tokenise(claim["subject"]) + tokenise(claim.get("predicate") or "is")
                       + tokenise(claim["object"]))
    t = min(5, len(claim_tokens & set(terms)))
    return 3 * s + 2 * o + t, s, o, t


# ---------------------------------------------------------------------------
# 9. _rank_key
# ---------------------------------------------------------------------------
def _rank_key(entry):
    return (-entry["score"], -entry["claim"]["created_at"].timestamp())


# ---------------------------------------------------------------------------
# 3. candidates
#    SPEC §6: a candidate matches the subject or the object. Excluded
#    claims that would have matched are returned for the trace.
# ---------------------------------------------------------------------------
def candidates(parse, loaded):
    terms = parse["terms"]
    ranked = []
    for claim in loaded["claims"]:
        sc, s, o, t = score(terms, claim)
        if s or o:
            ranked.append({"claim": claim, "score": sc, "s": s, "o": o, "t": t})
    ranked.sort(key=_rank_key)
    relevant = []
    for ex in loaded["excluded"]:
        claim = ex["claim"]
        if claim is not None and any(score(terms, claim)[1:3]):
            relevant.append({"claim_id": ex["claim_id"], "reason": ex["reason"]})
    return ranked, relevant


# ---------------------------------------------------------------------------
# 4. self_candidates
#    SPEC §8: active, polarised agent://lllm claims, by term match then
#    recency.
# ---------------------------------------------------------------------------
def self_candidates(parse, loaded):
    out = []
    for claim in loaded["claims"]:
        if claim["subject"] == SELF_SUBJECT:
            sc, s, o, t = score(parse["terms"], claim)
            out.append({"claim": claim, "score": t, "s": s, "o": o, "t": t})
    out.sort(key=_rank_key)
    return out
