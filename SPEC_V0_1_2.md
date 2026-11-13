# SPEC V0.1.2 — lllm (Tier 1: LLLM), changes over SPEC 0.1.1

SPEC_V0_1_2.md — the changes LLLM v0.1.2 makes to SPEC 0.1.0 as amended by SPEC_V0_1_1.md.

Function:
    Lets the Voice speak the signed claims James actually keeps: a
    subject (a repo) with several claims, each an aspect ("status",
    "design") whose content is in its asserted face's text. Where this
    file is silent, SPEC.md 0.1.0 and SPEC_V0_1_1.md apply unchanged.
    The 0.1.1 code is frozen and not edited: 0.1.2 is new modules
    (`know/v0_1_2.py`, `decide/v0_1_2.py`, `speak/v0_1_2.py`) and a new
    entry point, `lllm_v0_1_2.py`.

Tier:     Tier 1 — Consumer (The Voice)
Depends:  SPEC.md 0.1.0, SPEC_V0_1_1.md; P9 forge.db (read-only)
Version:  SPEC 0.1.2
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)

---

## 0. Why

Asked about the repo cubes, 0.1.1 said "ledger-layer is status." and
asked which of three claims was meant: it reads only subject /
predicate / object, never the face text, and treats two objects of one
subject as a disagreement. Found 2026-11-13 by asking the Voice about
the 72 signed repo claims.

## 1. The asserted text (adds to SPEC §1 and §3)

A claim's **asserted face** is `capsule.face` when it is FACT, COUNTER
or CONTEXT (the faces that carry polarity). Its **text** is that face's
value when it is a non-empty string **and** says more than the triple:
after lower-casing, collapsing spaces, dropping a leading "the ", "a "
or "an " and trailing ". ! ?", it is neither "{subject} {predicate}
{object}" nor "{subject} {predicate} not {object}". Otherwise the claim
has no text and behaves exactly as in 0.1.1. OPINION, FICTION and
UNKNOWN faces are never read.

## 2. Matching (amends SPEC §6)

`t` counts distinct shared tokens between the input terms and the
claim's subject, predicate, object **and text**, still capped at 5.
Function words in the text never count: the, a, an, is, are, was,
were, be, been, of, and, or, to, in, on, at, by, for, with, as, it,
its, this, that, these, those, what, which, who, how, do, does, did,
not, no. (Without this, a text starting "The …" outranks its siblings.)
A candidate still needs s = 1 or o = 1.

## 3. Aspects are not disagreement (amends SPEC §7 and SPEC_V0_1_1 §2)

Two candidates within δ with the same subject:

- If **both have text** and their objects differ, they are two
  **aspects** of the subject, not a disagreement. The Voice answers
  with every candidate within δ of top1 that has the same subject, has
  text and has a distinct object, up to 3, in rank order (plan
  `answer`, template `answer_aspects`, each cited).
- Same object, opposite polarity, both with text: a disagreement;
  clarify as before.
- Otherwise 0.1.1's rule applies unchanged (so "door is open" against
  "door is shut" still clarifies).

## 4. Templates (adds to SPEC §9.1)

For a claim with text, in place of the 0.1 answer templates:

- `answer_text`: `{subject} ({object}): {text} [{claim_id}]`
- `answer_yes_text`: `Yes. {subject} ({object}): {text} [{claim_id}]`
- `answer_no_text`: `No. {subject} ({object}): {text} [{claim_id}]`

chosen by 0.1.1's yes / no rule. The text is the signed statement, so
it is spoken as written; `No.` is used when the claim's polarity is
negate and the question names its object. `answer_aspects` renders
`answer_text` once per aspect, one per line.

`text` is a locked slot (SPEC §10): its value must appear verbatim, or
the reply falls back to `answer_text`.

## 5. Acceptance

- Every query in FIXTURE.md gives the same plan, template and reply
  through 0.1.2 as through 0.1.1.
- Repo cubes: the status question answers with the status FACT text;
  "is the ledger-layer frozen?" finds the claim whose text says frozen;
  "what is the ledger-layer?" answers with up to three aspects, each
  cited; no OPINION, FICTION or UNKNOWN text is ever spoken; an
  opposite-polarity pair on one aspect clarifies.
- New modules import only the standard library and the 0.1 packages.

---

## Document control

- **SPEC 0.1.2** — 2026-11-13, by the VS Code AI on James's delegation
  ("i sign, yo decide"; "make sure [the LLLM] is properly wired in";
  "all of it"). Not signed off; SPEC.md stays 0.1.0 as signed.
