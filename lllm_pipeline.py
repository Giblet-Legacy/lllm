"""
lllm_pipeline.py — LLLM four-layer pipeline (v0.1.0)

Function:
    Understand → Know → Decide → Speak. Reads from P9 (read-only),
    parses intent, matches claims, decides a plan, renders a reply
    from templates with locked slots. Returns a result dict.

Tier:    Tier 1 — LLLM
Depends: P9 substrate (read-only)
Spec:    SPEC.md v0.1.0
Licence: MSL-1.0
"""

import os
import re
import json
import sqlite3
import datetime


# ---------------------------------------------------------------------------
# P9 reader
# ---------------------------------------------------------------------------
def _forge_home():
    return os.environ.get("FORGE_HOME", os.path.expanduser("~/.forge"))


def _db_path():
    return os.path.join(_forge_home(), "forge.db")


def _load_claims():
    """Reads all claims from P9 (read-only). Returns (active, excluded)."""
    db = _db_path()
    if not os.path.exists(db):
        return [], []

    # mode=ro: SQLite physically prevents writes
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT claim_id, signer, capsule, is_active, superseded_by, created_at FROM claims"
    ).fetchall()
    conn.close()

    active = []
    excluded = []

    for row in rows:
        cid, signer, capsule_json, is_active, superseded_by, created_at = row
        try:
            capsule = json.loads(capsule_json)
        except json.JSONDecodeError:
            excluded.append({"claim_id": cid, "reason": "capsule_invalid"})
            continue

        # Status mapping (SPEC §2)
        if is_active == 0:
            if superseded_by:
                excluded.append({"claim_id": cid, "reason": "status_excluded"})
            else:
                excluded.append({"claim_id": cid, "reason": "status_excluded"})
            continue

        # Field mapping (SPEC §1)
        subject = capsule.get("subject")
        obj = capsule.get("object")
        polarity = capsule.get("polarity")

        if subject is None or obj is None:
            excluded.append({"claim_id": cid, "reason": "capsule_invalid"})
            continue

        # Polarity rule (SPEC §4)
        if polarity is None:
            excluded.append({"claim_id": cid, "reason": "polarity_missing"})
            continue
        if polarity not in ("affirm", "negate"):
            excluded.append({"claim_id": cid, "reason": "polarity_invalid"})
            continue

        try:
            created_dt = datetime.datetime.fromisoformat(created_at)
        except (ValueError, TypeError):
            excluded.append({"claim_id": cid, "reason": "created_at_invalid"})
            continue

        active.append({
            "claim_id": cid,
            "subject": subject,
            "predicate": capsule.get("predicate", "is"),
            "object": obj,
            "polarity": polarity,
            "source": signer or "unknown",
            "created_at": created_dt,
        })

    return active, excluded


# ---------------------------------------------------------------------------
# Understand: tokenise + intent
# ---------------------------------------------------------------------------
_INTENT_PATTERNS = [
    ("trace_query", [
        r"how\s+(did|do)\s+you\s+(work|know|figure)\s+(that|this|it)\s+out",
        r"why\s+did\s+you\s+(say|answer|reply)",
        r"where\s+did\s+(that|this|it)\s+come\s+from",
        r"show\s+(me\s+)?your\s+(trace|reasoning)",
    ]),
    ("self_query", [
        r"^who\s+are\s+you",
        r"^what\s+are\s+you",
        r"^what\s+can\s+you\s+do",
        r"how\s+(do|does)\s+(you|lllm)\s+work",
        r"tell\s+me\s+about\s+(yourself|lllm)",
    ]),
    ("clarify", [
        r"what\s+do\s+you\s+mean",
        r"can\s+you\s+(clarify|explain)",
        r"i\s+don'?t\s+understand",
        r"which\s+one",
    ]),
    ("greeting", [
        r"^(hi|hello|hey|hiya|howdy|greetings)\b",
        r"^good\s+(morning|afternoon|evening)\b",
    ]),
    ("farewell", [
        r"^(bye|goodbye|see\s+you|good\s+night)\b",
        r"^(thanks|thank\s+you|cheers)\b",
    ]),
]


def _tokenise(text):
    return re.findall(r"[a-z0-9][a-z0-9.+'-]*", text.lower())


def _understand(text):
    lowered = text.lower().strip()
    terms = _tokenise(lowered)
    negation = "not" in terms or "n't" in lowered

    intent = None
    for name, patterns in _INTENT_PATTERNS:
        for pat in patterns:
            if re.search(pat, lowered):
                intent = name
                break
        if intent:
            break

    if intent is None:
        # SPEC §5.3: question if ends with ? or starts with WH-word
        if lowered.endswith("?"):
            intent = "question"
        elif re.match(r"^(who|what|where|when|why|how|which|is|are|was|were|do|does|did|can|could|will|would|should)\b", lowered):
            intent = "question"
        else:
            intent = "statement"

    return {
        "raw": text,
        "intent": intent,
        "terms": terms,
        "negation": negation,
    }


# ---------------------------------------------------------------------------
# Know: matching and ranking
# ---------------------------------------------------------------------------
def _match_score(claim, terms):
    terms_set = set(terms)
    s = 1 if claim["subject"].lower() in terms_set else 0
    o = 1 if claim["object"].lower() in terms_set else 0
    claim_terms = set(_tokenise(
        f"{claim['subject']} {claim['predicate']} {claim['object']}"
    ))
    t = min(5, len(claim_terms & terms_set))
    return (3 * s) + (2 * o) + t


def _know(parse, active_claims):
    candidates = []

    # Self-model queries: include all active agent://lllm claims as
    # candidates with a synthetic score. The user isn't matching a
    # specific claim; they're asking about the self.
    if parse["intent"] == "self_query":
        for claim in active_claims:
            if claim["subject"] == "agent://lllm":
                candidates.append({**claim, "score": 1.0})
        candidates.sort(key=lambda c: c["created_at"], reverse=True)
        return candidates

    for claim in active_claims:
        if claim["subject"] == "agent://lllm":
            # Don't surface self-model claims for ordinary questions.
            continue
        score = _match_score(claim, parse["terms"])
        if score > 0:
            candidates.append({**claim, "score": score})

    # Rank: score desc, then created_at desc.
    candidates.sort(key=lambda c: (c["score"], c["created_at"]), reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Decide: plan selection
# ---------------------------------------------------------------------------
CLARIFY_DELTA = float(os.environ.get("LLLM_CLARIFY_DELTA", "0.10"))


def _decide(parse, candidates, prev_trace):
    intent = parse["intent"]

    if intent == "trace_query":
        if prev_trace is None:
            return "unknown", "no previous reply to trace"
        return "trace", "previous reply exists"

    if intent in ("greeting", "farewell"):
        return "social", f"intent={intent}"

    if intent == "statement":
        return "acknowledge", "user stated something"

    if intent == "clarify":
        return "unknown", "user asked to clarify; no dialogue state in v0.1"

    if intent == "self_query":
        if not candidates:
            return "unknown", "no active self-model claims"
        return "explain_self", "self-model claims found"

    if intent == "question":
        if not candidates:
            return "unknown", "no active claim matched"

        if len(candidates) >= 2:
            top1, top2 = candidates[0], candidates[1]
            gap = top1["score"] - top2["score"]
            threshold = CLARIFY_DELTA * top1["score"]
            # Clarify only makes sense if both claims are about the same
            # subject. Otherwise the reply would compare unrelated claims.
            if gap <= threshold and top1["subject"] == top2["subject"]:
                if (top1["object"] != top2["object"]
                        or top1["polarity"] != top2["polarity"]):
                    return "clarify", (
                        f"top scores within δ: {top1['score']} vs {top2['score']}, disagree on object/polarity"
                    )
                else:
                    return "answer", "top scores within δ but agree; cite both"

        return "answer", "single best match"

    return "unknown", "unrecognised intent"


# ---------------------------------------------------------------------------
# Speak: templates with locked slots
# ---------------------------------------------------------------------------
def _slot_fill(template, slots):
    rendered = template
    for k, v in slots.items():
        rendered = rendered.replace("{" + k + "}", str(v))
    # Locked-slot check
    for k, v in slots.items():
        if str(v) not in rendered:
            return None
    return rendered


def _render_claim(claim):
    if claim["polarity"] == "negate":
        return f"{claim['subject']} {claim['predicate']} not {claim['object']}"
    return f"{claim['subject']} {claim['predicate']} {claim['object']}"


def _speak(plan, parse, candidates, prev_trace):
    if plan == "answer":
        cited = []
        if len(candidates) >= 2 and candidates[0]["score"] == candidates[1]["score"]:
            cited = [candidates[0], candidates[1]]
        else:
            cited = [candidates[0]]

        ids = [c["claim_id"] for c in cited]
        if len(cited) == 1:
            c = cited[0]
            slots = {
                "subject": c["subject"],
                "predicate": c["predicate"],
                "object": c["object"],
                "claim_id": c["claim_id"],
            }
            tmpl = ("Yes. {subject} {predicate} {object}. [{claim_id}]"
                    if c["polarity"] == "affirm"
                    else "No. {subject} {predicate} not {object}. [{claim_id}]")
        else:
            a, b = cited
            slots = {
                "subject": a["subject"],
                "predicate": a["predicate"],
                "object": a["object"],
                "claim_id_a": a["claim_id"],
                "claim_id_b": b["claim_id"],
            }
            tmpl = "{subject} {predicate} {object}. [{claim_id_a}] Also: [{claim_id_b}]."
        rendered = _slot_fill(tmpl, slots)
        return rendered or "I have claims but could not render them.", slots, tmpl, ids

    if plan == "explain_self":
        c = candidates[0]
        slots = {
            "subject": c["subject"],
            "predicate": c["predicate"],
            "object": c["object"],
            "claim_id": c["claim_id"],
        }
        tmpl = "{subject} {predicate} {object}. [{claim_id}]"
        rendered = _slot_fill(tmpl, slots)
        return rendered or "I could not describe myself from the substrate.", slots, tmpl, [c["claim_id"]]

    if plan == "clarify":
        a, b = candidates[0], candidates[1]
        slots = {
            "subject": a["subject"],
            "predicate": a["predicate"],
            "object1": a["object"],
            "object2": b["object"],
            "claim_id1": a["claim_id"],
            "claim_id2": b["claim_id"],
        }
        tmpl = ("I have more than one active claim matching. One says "
                "{subject} {predicate} {object1} [{claim_id1}], another says "
                "{subject} {predicate} {object2} [{claim_id2}]. Which do you mean?")
        rendered = _slot_fill(tmpl, slots)
        return rendered or "Multiple claims match; which did you mean?", slots, tmpl, [a["claim_id"], b["claim_id"]]

    if plan == "unknown":
        tmpl = "I don't have an active claim for that."
        return tmpl, {}, tmpl, []

    if plan == "acknowledge":
        tmpl = "Noted. That would be a proposal — it needs a human seal before I can use it."
        return tmpl, {}, tmpl, []

    if plan == "social":
        if parse["intent"] == "greeting":
            tmpl = "Hello. What can I look up for you?"
        else:
            tmpl = "Goodbye."
        return tmpl, {}, tmpl, []

    if plan == "trace":
        t = prev_trace or {}
        slots = {
            "plan": t.get("plan", "unknown"),
            "template_name": t.get("template_name", "none"),
            "intent": t.get("intent", "unknown"),
            "terms": ", ".join(t.get("terms", [])) or "none",
            "claim_ids": ", ".join(t.get("claim_ids_used", [])) or "none",
        }
        tmpl = ("My last reply used plan {plan}, template {template_name}, "
                "and cited {claim_ids}. The input parsed as intent {intent} "
                "with terms {terms}.")
        rendered = _slot_fill(tmpl, slots)
        return rendered or "I have a trace but could not render it.", slots, tmpl, []

    return "I don't know how to answer that.", {}, "fallback", []


# ---------------------------------------------------------------------------
# run() — orchestrator: ties the four layers together
# ---------------------------------------------------------------------------
_PREV_TRACE = None  # module-level state for trace_query (v0.4 makes this proper)


def reset():
    """Clears per-session state. Call at REPL startup or in tests."""
    global _PREV_TRACE
    _PREV_TRACE = None


def run(text):
    global _PREV_TRACE

    parse = _understand(text)
    active, excluded = _load_claims()
    candidates = _know(parse, active)
    plan, reason = _decide(parse, candidates, _PREV_TRACE)
    reply, slots, template, claim_ids_used = _speak(plan, parse, candidates, _PREV_TRACE)

    trace = {
        "intent": parse["intent"],
        "terms": parse["terms"],
        "negation": parse["negation"],
        "plan": plan,
        "reason": reason,
        "candidates": [
            {
                "claim_id": c["claim_id"],
                "score": c["score"],
                "subject": c["subject"],
                "object": c["object"],
                "polarity": c["polarity"],
            }
            for c in candidates
        ],
        "excluded": excluded,
        "template_name": "template_" + plan,
        "template": template,
        "slots": slots,
        "claim_ids_used": claim_ids_used,
    }

    _PREV_TRACE = trace

    return {
        "reply": reply,
        "plan": plan,
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# __main__ — REPL
# ---------------------------------------------------------------------------
def _print_trace(trace):
    print("--- trace ---")
    print(f"intent:   {trace['intent']}")
    print(f"terms:    {trace['terms']}")
    print(f"negation: {trace['negation']}")
    print(f"plan:     {trace['plan']}")
    print(f"reason:   {trace['reason']}")
    print("candidates:")
    if trace["candidates"]:
        for c in trace["candidates"]:
            print(f"  - {c['claim_id']} score={c['score']} {c['subject']}/{c['object']} polarity={c['polarity']}")
    else:
        print("  (none)")
    print("excluded:")
    if trace["excluded"]:
        for e in trace["excluded"]:
            print(f"  - {e['claim_id']} reason={e['reason']}")
    else:
        print("  (none)")
    print(f"template: {trace['template_name']}")
    print(f"slots:    {trace['slots']}")
    print("")


if __name__ == "__main__":
    import sys
    print("LLLM v0.1.0 — Type 'quit' to exit.")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in ("quit", "exit", "bye"):
            print("Goodbye.")
            break
        if not text:
            continue
        result = run(text)
        print(f"\n{result['reply']}\n")
        _print_trace(result["trace"])
