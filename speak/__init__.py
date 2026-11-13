"""
speak — LLLM layer 4: surface generation with locked slots

Function:
    Renders a plan's template by plain `str.replace` of each `{slot}`,
    then checks that every slot value appears verbatim in the result.
    If one does not, the rendering is discarded and the plan's bare
    fallback template is used (SPEC §9, §10). In v0.1 there is no
    n-gram phrasing, so the check always passes; it exists so v0.2's
    phrasing can never alter claim text.

Public API:
    1. render(template_name, slots, templates=None) -> (text, template_used)

Internal helpers:
    2. _fill    — replace each {slot}
    3. _intact  — every slot value present verbatim

Tier:     Tier 1 — Consumer (LLLM), layer 4
Depends:  standard library only
Spec:     SPEC.md 0.1.0 §9, §10
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

TEMPLATES = {
    "answer_yes": "Yes. {subject} {predicate} {object}. [{claim_id}]",
    "answer_no": "No. {subject} {predicate} not {object}. [{claim_id}]",
    "answer_state": "{subject} {predicate} {object}. [{claim_id}]",
    "answer_state_negate": "{subject} {predicate} not {object}. [{claim_id}]",
    "answer_source": "From the substrate: {subject} {predicate} {object}. [{claim_id}]",
    "explain_self": "{subject} {predicate} {object}. [{claim_id}]",
    "clarify": ("I have more than one active claim that matches. One says {subject} {predicate} {object1} "
                "[{claim_id1}], another says {subject} {predicate} {object2} [{claim_id2}]. Which one do you mean?"),
    "unknown_loaded": "I don't have an active claim for that.",
    "unknown_empty": "I can't answer that from the substrate.",
    "acknowledge": "Noted. That would be a proposal — it needs a human seal before I can use it.",
    "social_greeting": "Hello. What can I look up for you?",
    "social_farewell": "Goodbye.",
    "trace": ("My last reply used plan {plan}, template {template_name}, and cited {claim_ids}. "
              "The input parsed as intent {intent} with terms {terms}."),
}

FALLBACK = {"answer_yes": "answer_state", "answer_no": "answer_state_negate", "answer_source": "answer_state",
            "answer_state": "answer_state", "answer_state_negate": "answer_state_negate"}


# ---------------------------------------------------------------------------
# 2. _fill
# ---------------------------------------------------------------------------
def _fill(template, slots):
    out = template
    for name, value in slots.items():
        out = out.replace("{" + name + "}", str(value))
    return out


# ---------------------------------------------------------------------------
# 3. _intact
#    SPEC §10 step 3. The locked slots are the ones the *contract*
#    template (TEMPLATES) names; each value must appear verbatim, and no
#    unfilled `{slot}` may remain.
# ---------------------------------------------------------------------------
def _intact(template_name, text, slots):
    contract = TEMPLATES[template_name]
    locked = [k for k in slots if "{" + k + "}" in contract]
    return all(str(slots[k]) in text for k in locked) and "{" not in text


# ---------------------------------------------------------------------------
# 1. render
#    `templates` overrides the wording by name (a phrasing layer, or a
#    test's corrupting template); the contract stays TEMPLATES. KeyError
#    for an unknown name.
# ---------------------------------------------------------------------------
def render(template_name, slots, templates=None):
    if template_name not in TEMPLATES:
        raise KeyError(template_name)
    template = (templates or {}).get(template_name, TEMPLATES[template_name])
    text = _fill(template, slots)
    if _intact(template_name, text, slots):
        return text, template_name
    fallback = FALLBACK.get(template_name, template_name)
    return _fill(TEMPLATES[fallback], slots), fallback
