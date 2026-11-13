"""
traces — LLLM per-reply trace records (v0.1: console)

Function:
    Builds the trace record for one turn (parse, candidates, exclusions,
    plan and reason, template, slots, reply) and formats it in the SPEC
    §11 console layout. Named `traces`, not `trace`, so it never shadows
    the standard-library `trace` module (SPEC §12a). From v0.5 the same
    record becomes a signed capsule in P4.

Public API:
    1. build(parse, plan, template_used, reply) -> dict
    2. format_trace(trace) -> str

Internal helpers:
    3. _slot_lines — slot dict (or list of dicts) as indented lines

Tier:     Tier 1 — Consumer (LLLM)
Depends:  standard library only
Spec:     SPEC.md 0.1.0 §11
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""


# ---------------------------------------------------------------------------
# 1. build
# ---------------------------------------------------------------------------
def build(parse, plan, template_used, reply):
    candidates = [{"claim_id": c["claim"]["claim_id"], "score": c["score"], "status": c["claim"]["status"],
                   "subject": c["claim"]["subject"], "object": c["claim"]["object"],
                   "polarity": c["claim"]["polarity"]} for c in plan["candidates"]]
    return {"input": parse["raw"], "intent": parse["intent"], "terms": parse["terms"],
            "negation": parse["negation"], "plan": plan["plan"], "reason": plan["reason"],
            "candidates": candidates, "excluded": plan["excluded"], "template": template_used,
            "slots": plan["slots"], "cited": plan["cited"], "reply": reply}


# ---------------------------------------------------------------------------
# 3. _slot_lines
# ---------------------------------------------------------------------------
def _slot_lines(slots):
    groups = slots if isinstance(slots, list) else [slots]
    lines = []
    for i, group in enumerate(groups):
        if len(groups) > 1:
            lines.append(f"  [{i + 1}]")
        lines += [f"  {k}: {v}" for k, v in group.items()]
    return lines or ["  (none)"]


# ---------------------------------------------------------------------------
# 2. format_trace
#    SPEC §11. Sections with no entries print (none).
# ---------------------------------------------------------------------------
def format_trace(trace):
    lines = ["--- trace ---", f"input: {trace['input']}", f"intent: {trace['intent']}",
             f"terms: [{', '.join(trace['terms'])}]", f"negation: {trace['negation']}",
             f"plan: {trace['plan']}", f"reason: {trace['reason']}", "candidates:"]
    lines += [f"  - claim_id={c['claim_id']} score={c['score']} status={c['status']} subject={c['subject']} "
              f"object={c['object']} polarity={c['polarity']}" for c in trace["candidates"]] or ["  (none)"]
    lines.append("excluded:")
    lines += [f"  - claim_id={e['claim_id']} reason={e['reason']}" for e in trace["excluded"]] or ["  (none)"]
    lines += [f"template: {trace['template']}", "slots:"] + _slot_lines(trace["slots"])
    lines.append(f"reply: {trace['reply']}")
    return "\n".join(lines)
