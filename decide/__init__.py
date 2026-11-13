"""
decide — LLLM layer 3: the dialogue manager

Function:
    Chooses exactly one response plan per turn (SPEC §8): answer,
    explain_self, trace, clarify, unknown, acknowledge or social. Applies
    the clarify rule with δ (SPEC §7), picks the template (SPEC §9.1)
    and fills the locked slots. Returns the plan; `speak` renders it.

Public API:
    1. decide(parse, loaded, last_trace) -> dict
       {plan, reason, template, slots, cited, candidates, excluded}

Internal helpers:
    2. _delta     — δ from LLLM_CLARIFY_DELTA (default 0.10)
    3. _short     — 12-character cited id (SPEC §9.1)
    4. _obj       — object text, "not " prefixed for negate
    5. _plan      — assemble the result dict
    6. _answer    — answer / clarify for a question
    7. _self      — explain_self or unknown
    8. _trace     — the trace plan from the previous turn

Tier:     Tier 1 — Consumer (LLLM), layer 3
Depends:  standard library; know (local)
Spec:     SPEC.md 0.1.0 §7, §8, §9 + SPEC_V0_1_1.md §2, §3
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import os

import know

YES_NO_STARTS = {"is", "are", "was", "were", "do", "does", "did", "can", "could", "will", "would", "should"}


# ---------------------------------------------------------------------------
# 2. _delta
# ---------------------------------------------------------------------------
def _delta():
    try:
        return float(os.environ.get("LLLM_CLARIFY_DELTA", "0.10"))
    except ValueError:
        return 0.10


# ---------------------------------------------------------------------------
# 3. _short
# ---------------------------------------------------------------------------
def _short(claim_id):
    return claim_id[:12]


# ---------------------------------------------------------------------------
# 4. _obj
# ---------------------------------------------------------------------------
def _obj(claim):
    return ("not " if claim["polarity"] == "negate" else "") + claim["object"]


# ---------------------------------------------------------------------------
# 5. _plan
# ---------------------------------------------------------------------------
def _plan(plan, reason, template, slots=None, cited=(), candidates=(), excluded=()):
    return {"plan": plan, "reason": reason, "template": template, "slots": slots or {},
            "cited": list(cited), "candidates": list(candidates), "excluded": list(excluded)}


# ---------------------------------------------------------------------------
# 6. _answer
#    SPEC §7 (clarify rule) and §9.1 (template choice).
# ---------------------------------------------------------------------------
def _answer(parse, loaded):
    ranked, excluded = know.candidates(parse, loaded)
    unknown_template = "unknown_loaded" if loaded["rows"] else "unknown_empty"
    if not ranked:
        why = "no active claim matches the subject or object" if loaded["rows"] else "no claims loaded"
        return _plan("unknown", why, unknown_template, excluded=excluded)
    top1 = ranked[0]
    pair = None
    if len(ranked) > 1:
        top2 = ranked[1]
        margin = _delta() * top1["score"]
        a, b = top1["claim"], top2["claim"]
        same_subject = a["subject"].lower() == b["subject"].lower()  # SPEC_V0_1_1 §2
        if top1["score"] - top2["score"] <= margin and same_subject:
            if a["object"].lower() != b["object"].lower() or a["polarity"] != b["polarity"]:
                slots = {"subject": a["subject"], "predicate": a["predicate"], "object1": _obj(a),
                         "object2": _obj(b), "claim_id1": _short(a["claim_id"]), "claim_id2": _short(b["claim_id"])}
                return _plan("clarify", f"top two within δ ({top1['score']} vs {top2['score']}, margin {margin:g}) "
                             "and disagree", "clarify", slots, [a["claim_id"], b["claim_id"]], ranked, excluded)
            pair = top2
    claim = top1["claim"]
    cited = [claim] + ([pair["claim"]] if pair else [])
    yes_no = bool(parse["terms"]) and parse["terms"][0] in YES_NO_STARTS  # SPEC_V0_1_1 §3
    names_object = yes_no and top1["o"] == 1 and not parse["negation"]
    if claim["polarity"] == "negate":
        template = "answer_no" if names_object else "answer_state_negate"
    else:
        template = "answer_yes" if names_object else "answer_state"
    slots = {"subject": claim["subject"], "predicate": claim["predicate"], "object": claim["object"],
             "claim_id": ", ".join(_short(c["claim_id"]) for c in cited)}
    reason = (f"top candidate score {top1['score']}" + (f"; agrees with the next (within δ), citing both" if pair else
              f"; next is outside δ" if len(ranked) > 1 else "; only candidate"))
    return _plan("answer", reason, template, slots, [c["claim_id"] for c in cited], ranked, excluded)


# ---------------------------------------------------------------------------
# 7. _self
#    SPEC §8: the top three self-model claims, one template each.
# ---------------------------------------------------------------------------
def _self(parse, loaded):
    ranked = know.self_candidates(parse, loaded)
    if not ranked:
        return _plan("unknown", "no agent://lllm claims: self-model not bootstrapped",
                     "unknown_loaded" if loaded["rows"] else "unknown_empty")
    top = [r["claim"] for r in ranked[:3]]
    slots = [{"subject": c["subject"], "predicate": c["predicate"], "object": _obj(c), "claim_id": _short(c["claim_id"])}
             for c in top]
    return _plan("explain_self", f"{len(ranked)} self-model claim(s); citing {len(top)}", "explain_self",
                 slots, [c["claim_id"] for c in top], ranked)


# ---------------------------------------------------------------------------
# 8. _trace
#    SPEC §8: the previous turn's trace, or unknown before any reply.
# ---------------------------------------------------------------------------
def _trace(last_trace, loaded):
    if last_trace is None:
        return _plan("unknown", "no previous reply to explain", "unknown_loaded" if loaded["rows"] else "unknown_empty")
    slots = {"plan": last_trace["plan"], "template_name": last_trace["template"],
             "claim_ids": ", ".join(_short(c) for c in last_trace["cited"]) or "nothing",
             "intent": last_trace["intent"], "terms": ", ".join(last_trace["terms"]) or "none"}
    return _plan("trace", "explaining the previous reply", "trace", slots)


# ---------------------------------------------------------------------------
# 1. decide
# ---------------------------------------------------------------------------
def decide(parse, loaded, last_trace):
    intent = parse["intent"]
    if intent in ("trace_query", "clarify"):
        return _trace(last_trace, loaded)
    if intent == "self_query":
        return _self(parse, loaded)
    if intent == "statement":
        return _plan("acknowledge", "statement: a proposal needs a human seal (v0.3)", "acknowledge")
    if intent == "greeting":
        return _plan("social", "greeting", "social_greeting")
    if intent == "farewell":
        return _plan("social", "thanks or farewell", "social_farewell")
    return _answer(parse, loaded)
