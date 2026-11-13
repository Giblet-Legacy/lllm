"""
know/v0_1_2.py — LLLM v0.1.2 Know: claims with their asserted text

Function:
    0.1's Know (know/__init__.py, frozen) plus the asserted face's text
    (SPEC_V0_1_2 §1) on every claim view, and term matching that counts
    that text (§2). OPINION, FICTION and UNKNOWN faces are never read.

Public API:
    1. load(db_path) -> {"claims", "excluded", "rows"}   — views gain face, text
    2. score(terms, claim) -> (score, s, o, t)
    3. candidates(parse, loaded) -> (ranked, relevant_excluded)
    4. text_of(capsule, claim) -> (face, text | None)

Internal helpers:
    5. _plain — lower-case, collapse spaces, drop a leading article and
                trailing . ! ?

Tier:     Tier 1 — Consumer (The Voice)
Depends:  know (0.1, frozen); standard library
Spec:     SPEC_V0_1_2.md §1–2
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import json
import sqlite3

import know as _k

ASSERTED = ("FACT", "COUNTER", "CONTEXT")
# SPEC_V0_1_2 §2: function words in a claim's text never count as matches.
FUNCTION_WORDS = frozenset("the a an is are was were be been of and or to in on at by for with as it its "
                           "this that these those what which who how do does did not no".split())


# ---------------------------------------------------------------------------
# 5. _plain
# ---------------------------------------------------------------------------
def _plain(text):
    t = " ".join(text.lower().split()).rstrip(".!? ")
    for article in ("the ", "a ", "an "):
        if t.startswith(article):
            return t[len(article):]
    return t


# ---------------------------------------------------------------------------
# 4. text_of
#    SPEC_V0_1_2 §1: the asserted face's value when it says more than
#    the triple; else None.
# ---------------------------------------------------------------------------
def text_of(capsule, claim):
    face = capsule.get("face")
    value = capsule.get(face) if face in ASSERTED else None
    if not isinstance(value, str) or not value.strip():
        return face, None
    s, p, o = claim["subject"], claim["predicate"], claim["object"]
    if _plain(value) in (_plain(f"{s} {p} {o}"), _plain(f"{s} {p} not {o}")):
        return face, None
    return face, value.strip()


# ---------------------------------------------------------------------------
# 1. load
#    0.1's mapping (_view) per row, then face and text added.
# ---------------------------------------------------------------------------
def load(db_path):
    conn = _k._connect_ro(db_path)
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
        claim, reason = _k._view(row)
        if claim is not None:
            capsule = json.loads(row[2])
            claim["face"], claim["text"] = text_of(capsule, claim)
        if reason is None:
            claims.append(claim)
        else:
            excluded.append({"claim_id": row[0], "reason": reason, "claim": claim})
    return {"claims": claims, "excluded": excluded, "rows": len(rows)}


# ---------------------------------------------------------------------------
# 2. score
#    SPEC §6 with SPEC_V0_1_2 §2: the text's tokens count towards t.
# ---------------------------------------------------------------------------
def score(terms, claim):
    s = int(_k._contains(terms, _k.tokenise(claim["subject"])))
    o = int(_k._contains(terms, _k.tokenise(claim["object"])))
    claim_tokens = set(_k.tokenise(claim["subject"]) + _k.tokenise(claim.get("predicate") or "is")
                       + _k.tokenise(claim["object"])
                       + [w for w in _k.tokenise(claim.get("text") or "") if w not in FUNCTION_WORDS])
    t = min(5, len(claim_tokens & set(terms)))
    return 3 * s + 2 * o + t, s, o, t


# ---------------------------------------------------------------------------
# 3. candidates
#    0.1's rule (s or o), ranked with this score.
# ---------------------------------------------------------------------------
def candidates(parse, loaded):
    terms = parse["terms"]
    ranked = []
    for claim in loaded["claims"]:
        sc, s, o, t = score(terms, claim)
        if s or o:
            ranked.append({"claim": claim, "score": sc, "s": s, "o": o, "t": t})
    ranked.sort(key=_k._rank_key)
    relevant = []
    for ex in loaded["excluded"]:
        claim = ex["claim"]
        if claim is not None and any(score(terms, claim)[1:3]):
            relevant.append({"claim_id": ex["claim_id"], "reason": ex["reason"]})
    return ranked, relevant
