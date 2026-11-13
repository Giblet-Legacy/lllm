"""
decide/v0_1_2.py — LLLM v0.1.2 Decide: aspects are not disagreement

Function:
    0.1.1's dialogue manager (decide/__init__.py, frozen) with one
    change to answering (SPEC_V0_1_2 §3–4): two claims of one subject
    that both carry text and differ in object are aspects, answered
    together; claims with text are spoken with the text templates.
    Claims without text take exactly 0.1.1's path.

Public API:
    1. decide(parse, loaded, last_trace) -> plan

Internal helpers:
    2. _answer       — the question plan
    3. _text_answer  — single claim with text
    4. _clarify      — 0.1.1's clarify plan

Tier:     Tier 1 — Consumer (The Voice)
Depends:  decide (0.1.1, frozen), know/v0_1_2; standard library
Spec:     SPEC_V0_1_2.md §3–4
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import decide as _d
from know import v0_1_2 as kn

MAX_ASPECTS = 3


# ---------------------------------------------------------------------------
# 4. _clarify
# ---------------------------------------------------------------------------
def _clarify(top1, top2, margin, ranked, excluded):
    a, b = top1["claim"], top2["claim"]
    slots = {"subject": a["subject"], "predicate": a["predicate"], "object1": _d._obj(a),
             "object2": _d._obj(b), "claim_id1": _d._short(a["claim_id"]), "claim_id2": _d._short(b["claim_id"])}
    return _d._plan("clarify", f"top two within δ ({top1['score']} vs {top2['score']}, margin {margin:g}) "
                    "and disagree", "clarify", slots, [a["claim_id"], b["claim_id"]], ranked, excluded)


# ---------------------------------------------------------------------------
# 3. _text_answer
#    SPEC_V0_1_2 §4: the yes / no rule of 0.1.1, text templates.
# ---------------------------------------------------------------------------
def _text_answer(parse, top1, cited, reason, ranked, excluded):
    claim = top1["claim"]
    yes_no = bool(parse["terms"]) and parse["terms"][0] in _d.YES_NO_STARTS
    names_object = yes_no and top1["o"] == 1 and not parse["negation"]
    if names_object:
        template = "answer_no_text" if claim["polarity"] == "negate" else "answer_yes_text"
    else:
        template = "answer_text"
    slots = {"subject": claim["subject"], "object": claim["object"], "text": claim["text"],
             "claim_id": ", ".join(_d._short(c["claim_id"]) for c in cited)}
    return _d._plan("answer", reason, template, slots, [c["claim_id"] for c in cited], ranked, excluded)


# ---------------------------------------------------------------------------
# 2. _answer
# ---------------------------------------------------------------------------
def _answer(parse, loaded):
    ranked, excluded = kn.candidates(parse, loaded)
    if not ranked:
        why = "no active claim matches the subject or object" if loaded["rows"] else "no claims loaded"
        return _d._plan("unknown", why, "unknown_loaded" if loaded["rows"] else "unknown_empty", excluded=excluded)
    top1 = ranked[0]
    a = top1["claim"]
    margin = _d._delta() * top1["score"]
    near = [r for r in ranked[1:] if top1["score"] - r["score"] <= margin
            and r["claim"]["subject"].lower() == a["subject"].lower()]
    pair = None
    if near:
        top2 = near[0] if near[0] is ranked[1] else None
        b = top2["claim"] if top2 else None
        if b is not None and a["text"] and b["text"]:
            if a["object"].lower() != b["object"].lower():
                aspects, seen = [top1], {a["object"].lower()}
                for r in near:
                    c = r["claim"]
                    if c["text"] and c["object"].lower() not in seen and len(aspects) < MAX_ASPECTS:
                        aspects.append(r)
                        seen.add(c["object"].lower())
                slots = [{"subject": r["claim"]["subject"], "object": r["claim"]["object"], "text": r["claim"]["text"],
                          "claim_id": _d._short(r["claim"]["claim_id"])} for r in aspects]
                return _d._plan("answer", f"{len(aspects)} aspects of {a['subject']} within δ (margin {margin:g})",
                                "answer_aspects", slots, [r["claim"]["claim_id"] for r in aspects], ranked, excluded)
            if a["polarity"] != b["polarity"]:
                return _clarify(top1, top2, margin, ranked, excluded)
            pair = top2
        elif b is not None:
            if a["object"].lower() != b["object"].lower() or a["polarity"] != b["polarity"]:
                return _clarify(top1, top2, margin, ranked, excluded)
            pair = top2
    cited = [a] + ([pair["claim"]] if pair else [])
    reason = (f"top candidate score {top1['score']}" + ("; agrees with the next (within δ), citing both" if pair else
              "; next is outside δ" if len(ranked) > 1 else "; only candidate"))
    if a["text"]:
        return _text_answer(parse, top1, cited, reason, ranked, excluded)
    yes_no = bool(parse["terms"]) and parse["terms"][0] in _d.YES_NO_STARTS
    names_object = yes_no and top1["o"] == 1 and not parse["negation"]
    if a["polarity"] == "negate":
        template = "answer_no" if names_object else "answer_state_negate"
    else:
        template = "answer_yes" if names_object else "answer_state"
    slots = {"subject": a["subject"], "predicate": a["predicate"], "object": a["object"],
             "claim_id": ", ".join(_d._short(c["claim_id"]) for c in cited)}
    return _d._plan("answer", reason, template, slots, [c["claim_id"] for c in cited], ranked, excluded)


# ---------------------------------------------------------------------------
# 1. decide
#    0.1.1's dispatch, with this _answer for questions.
# ---------------------------------------------------------------------------
def decide(parse, loaded, last_trace):
    if parse["intent"] in ("trace_query", "clarify", "self_query", "statement", "greeting", "farewell"):
        return _d.decide(parse, loaded, last_trace)
    return _answer(parse, loaded)
