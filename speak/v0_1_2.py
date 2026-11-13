"""
speak/v0_1_2.py — LLLM v0.1.2 Speak: templates for claims with text

Function:
    0.1's templates (speak/__init__.py, frozen) plus the text templates
    of SPEC_V0_1_2 §4. `text` is a locked slot; a reply that loses a
    locked value falls back to `answer_text`.

Public API:
    1. render(template_name, slots, templates=None) -> (text, template_used)
    TEMPLATES, FALLBACK

Tier:     Tier 1 — Consumer (The Voice)
Depends:  speak (0.1, frozen); standard library
Spec:     SPEC_V0_1_2.md §4
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import speak as _s

TEMPLATES = dict(_s.TEMPLATES, **{
    "answer_text": "{subject} ({object}): {text} [{claim_id}]",
    "answer_yes_text": "Yes. {subject} ({object}): {text} [{claim_id}]",
    "answer_no_text": "No. {subject} ({object}): {text} [{claim_id}]",
    "answer_aspects": "{subject} ({object}): {text} [{claim_id}]",
})
FALLBACK = dict(_s.FALLBACK, answer_text="answer_text", answer_yes_text="answer_text",
                answer_no_text="answer_text", answer_aspects="answer_text")


# ---------------------------------------------------------------------------
# 1. render
#    0.1's rule (SPEC §10) against this contract.
# ---------------------------------------------------------------------------
def render(template_name, slots, templates=None):
    if template_name not in TEMPLATES:
        raise KeyError(template_name)
    template = (templates or {}).get(template_name, TEMPLATES[template_name])
    text = _s._fill(template, slots)
    contract = TEMPLATES[template_name]
    locked = [k for k in slots if "{" + k + "}" in contract]
    if all(str(slots[k]) in text for k in locked) and "{" not in text:
        return text, template_name
    fallback = FALLBACK.get(template_name, template_name)
    return _s._fill(TEMPLATES[fallback], slots), fallback
