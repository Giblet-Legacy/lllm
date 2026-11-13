# SPEC V0.1.1 — lllm (Tier 1: LLLM), changes over SPEC 0.1.0

SPEC_V0_1_1.md — the changes LLLM v0.1.1 makes to the signed-off SPEC 0.1.0.

Function:
    SPEC.md (0.1.0) was signed off by James on 2026-11-13 and is frozen.
    This file states only what 0.1.1 changes. Where it is silent,
    SPEC.md 0.1.0 applies unchanged. The code (`understand/`,
    `decide/`) implements 0.1.0 plus these three changes.

Tier:     Tier 1 — Consumer (The Voice)
Depends:  SPEC.md 0.1.0
Version:  SPEC 0.1.1
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)

---

## 1. Intent precedence and clarify patterns (replaces SPEC §5 list and §5.5)

Precedence:

1. `trace_query`
2. `self_query`
3. `clarify`
4. `question`
5. `statement`
6. `greeting`
7. `farewell`

`clarify` patterns, anchored at the start of the input:

- `^what do you mean`
- `^can you (clarify|explain)`
- `^i don'?t understand`
- `^which one\b\W*$`

**Why:** under 0.1.0, "what do you mean?", "can you clarify?" and
"which one?" all parsed as questions, so the `clarify` intent was
unreachable for them (NOTES Q9). Anchoring keeps a real question that
contains the words ("which one is bigger?") a question.

## 2. Clarify and cite-both need the same subject (adds to SPEC §7)

Clarify fires only if, in addition to SPEC §7's conditions, `top1` and
`top2` have the **same subject** (case-insensitive). The agree case
(answer citing both) likewise needs the same subject. If the top two
are within δ but have different subjects, they do not compete: LLLM
answers with `top1` only.

**Why:** under 0.1.0, "what is blue?" with "sky is blue" and "sea is
blue" would have cited the sky claim under the sentence "sea is blue".

## 3. `Yes.`/`No.` only for yes/no questions (amends SPEC §9.1)

`answer_yes` / `answer_no` need, in addition to SPEC §9.1's
conditions, a **yes/no question**: its first term is `is`, `are`,
`was`, `were`, `do`, `does`, `did`, `can`, `could`, `will`, `would` or
`should`. Every other answer uses `answer_state` /
`answer_state_negate`.

**Why:** under 0.1.0, "what is blue?" was answered "Yes. sky is blue."

## 4. Tests

`test_lllm.py` (20 tests) covers 0.1.0 and these changes: the parse
table (§1), and the FIXTURE.md rows "what do you mean?" (§1) and "what
is blue?" (§2, §3).

---

## Document control

- **SPEC 0.1.1** — 2026-11-13, decided by the VS Code AI on James's
  delegation ("i sign, yo decide"). §2 and §3 were found by asking the
  Voice through The Legacy on a Cockpit-written database.
- First recorded by editing SPEC.md in place after sign-off (commit
  `0117ee8`). Corrected the same day, at James's request ("make sure
  you are not over writing and versioning like the claude.md
  requires"): SPEC.md restored to the signed-off 0.1.0 text, and the
  changes moved here.
