# CHANGELOG — lllm (Tier 1: LLLM)

CHANGELOG.md — build history for LLLM, latest entry at top.

## [v0.1.0] — The Voice Speaks

### Good
- `lllm_pipeline.py` implemented to SPEC v0.1.0.
- 17/17 pytest tests pass.
- Four-layer pipeline: Understand → Know → Decide → Speak.
- P9 read-only via `mode=ro`. Verified by file-hash test.
- Seven response plans: `answer`, `explain_self`, `trace`, `clarify`,
  `unknown`, `acknowledge`, `social`.
- Locked-slot rendering with mechanical verification.
- Explicit exclusions: superseded, inactive, missing polarity (each
  with a trace reason).
- Self-model filtered by `agent://lllm` and bypasses scoring for
  self_query intent.
- REPL prints full trace on every reply.
- Clarify requires same subject. Without this, "is the earth flat?"
  compared unrelated claims (sky/sun) and produced nonsense. Fixed
  before freeze.

### Bad
- No trust ranking. Recency is the tie-breaker. λ arrives in v0.2.
- No signature verification on loaded claims. v0.1 trusts P9.
  P1/P2 verification arrives in v0.2.
- No n-gram phrasing. Replies are templated.
- No proposals stored. Every statement returns the same
  `acknowledge` template.
- `_PREV_TRACE` is module-level state. Fine for the REPL; v0.4 will
  formalise conversation state.
- Match score formula is a first guess (subject×3, object×2, term×1).
  Recorded in NOTES.md Q1; will tune against real conversations.

### Ugly
- First test run: 3 failures. Root causes:
  - Clarify test used "is the apple red?" — the user specified the
    object, so no clarify. Test case rewritten to "is the apple ripe?".
  - Self-model claims scored 0 (no terms matched), so
    `explain_self` never fired. Fixed by treating self_query as a
    bypass-intent: include all agent://lllm claims regardless of
    score.
  - `_PREV_TRACE` leaked between tests. Added `reset()`.
- Second discovery (during REPL proof): clarify fired on unrelated
  subjects ("is the earth flat?" compared sky and sun). Fixed by
  requiring `top1.subject == top2.subject`. New test added.
- `_print_trace` referenced `trace['reply']` which doesn't exist
  (reply is top-level). Removed the line. Tests didn't catch it
  because tests don't print traces.

## [Unreleased]

### Good

- (none)

### Bad

- (none)

### Ugly

- (none)

## [v0.1.2] — 2026-11-13 — FROZEN

### Good

- `SPEC_V0_1_2.md`, `test_lllm_v0_1_2.py` (8 tests, run red first) and new
  modules `know/v0_1_2.py`, `decide/v0_1_2.py`, `speak/v0_1_2.py`,
  `lllm_v0_1_2.py`: the Voice speaks a claim's asserted face text
  ("ledger-layer (status): ledger_v2 is frozen at 2.0.0 ..."), counts that
  text when ranking, and answers a subject's aspects together instead
  of asking which one. OPINION, FICTION and UNKNOWN are never read.
- Every FIXTURE.md query gives the same plan, template and reply as
  0.1.1. 28/28 pass. The 0.1.1 code and SPEC.md are untouched. Decided
  by the VS Code AI on James's delegation ("i sign, yo decide"; "all of
  it"). Frozen at 0.1.2 (James: "freeze commmit and push", 2026-11-13); laptop run, S24 run
  still to be confirmed.

### Bad

- Found 2026-11-13: asked about the 72 drafted repo claims, 0.1.1 said
  "ledger-layer is status." and asked which of three claims was meant.

### Ugly

- Function words in face text are ignored when ranking (a fixed list in
  SPEC_V0_1_2 §2); without it a text starting "The ..." outranked its
  siblings.

## [v0.1.1] — 2026-11-13 — FROZEN

### Good
- James answered NOTES Q5–Q9 ("lllm should be stored in a different db
  and be opinions, lllm commands go via the legacy, i sign, yo
  decide"). Recorded in NOTES and CLAUDE.md.
- SPEC 0.1.1, decided on James's delegation: `clarify` above `question`
  with anchored patterns (Q9); clarify and cite-both need the same
  subject (§7); `Yes.`/`No.` only for yes/no questions (§9.1).
- First real conversation through The Legacy (`/api/voice`) on a
  Cockpit-written forge.db: FACT and CONTEXT claims answered with
  citations; FICTION and OPINION refused (`polarity_missing`). 20/20.

### Bad
- Frozen on the laptop run alone (2026-11-13); confirmed on the S24 by James, 2026-11-13.
- 0.1.1 was first written into the signed-off SPEC.md in place
  (`0117ee8`). Corrected: SPEC.md restored to the signed-off 0.1.0 text,
  the changes moved to SPEC_V0_1_1.md (James: "make sure you are not
  over writing and versioning like the claude.md requires").
- That conversation found the two §7/§9.1 answer bugs ("what is blue?"
  → "Yes. sky is blue."), which the 0.1.0 tests had not covered.

### Ugly
- SPEC.md §13's own "All tests pass in Termux" box stays unticked:
  SPEC.md is signed off and never edited. The pass is recorded here, in
  VERSION, README and ROADMAP.
- `lllm.py`'s header still reads `Version: 0.1.0-dev`. It is committed
  and frozen, so it is left as is (the stack's convention for stale
  headers); VERSION is authoritative.

## [v0.1.0 build] — 2026-11-13

### Good
- SPEC v0.1.0 signed off by James, after pre-sign-off corrections
  marked in the SPEC (§5.4, §5.7, §6, §7, §8, §9.1, §9.4, §11, §12,
  §12a). The two that change answers: a candidate must match the
  subject or object, and `Yes.`/`No.` only when the question names the
  claim's object.
- Phase 1: `fixture_p9.py` builds the fixture P9 with real P9 code
  (substrate_v3), covering every ROADMAP case; `FIXTURE.md` is the
  manifest, and a test checks every row against reality.
- v0.1 built in pipeline order: `understand/`, `know/`, `decide/`,
  `speak/`, `traces/`, `lllm.py` (REPL, `--once`). Read-only P9 via
  `Path.as_uri()` + `mode=ro`; ISO 8601 `created_at`; polarity
  required; locked slots with a verbatim check and bare-template
  fallback; console trace on every reply.
- `test_lllm.py`: 20 tests (every SPEC §13 criterion, the ROADMAP
  mini-gates, the manifest), written first and run red. 20/20 pass on
  the laptop from the repo and from its parent. Runtime imports are
  standard library only (checked by reading the source).

### Bad
- Not yet run in Termux, which SPEC §13 requires for freeze. VERSION
  stays 0.1.0-dev.
- On a real `forge.db` written by the Cockpit, every claim is
  `polarity_missing` (checked 2026-11-13): no Forge Stack code writes
  polarity yet (NOTES Q8).
- The locked intent precedence makes the `clarify` intent unreachable
  for question-shaped phrases ("what do you mean?" parses as a
  question). Pinned in FIXTURE.md; NOTES Q9.

### Ugly
- The fixture manifest caught a mistake in the manifest itself on the
  first run ("is the sky green?" also matches the superseded "grass is
  green"); the manifest was corrected, not the code.

## [Contract] — 2026-11-13

### Good
- Repository scaffolded: `Giblet-Legacy/lllm` created as Tier 1
  Consumer (The Voice).
- README, ROADMAP, NOTES, CLAUDE all landed. Contract first, code
  later.
- Dependency table by version: v0.1 requires P9 only. v0.2 adds
  P14, P1, P2. v0.3 adds P13, P15, P4.
- Architectural commitments locked:
  - Polarity required; missing polarity → excluded + traced.
  - v0.1 trusts P9 (no signature verification); arrives v0.2-B.
  - trace_query is a first-class intent, precedence-listed.
  - Contradiction is tagged, not rejected.
  - v0.4 state is in-session only.

### Bad
- No code yet. Phase 0 (SPEC) must be written and signed off before
  the scaffold can be completed.
- No fixture P9 yet. The Phase 1 fixture is a written contract; it
  does not exist.
- TODOs in the README closed: MSL-1.0 description finalised,
  explorer-d334-forge described inline.

### Ugly
- The README went through three revisions before landing. Each caught
  a real conflict:
  - λ was described as 0.0–1.0 when P14's neutral is 1.00.
  - Polarity defaulted to `affirm` in one version and was excluded
    in another. Resolved to exclude.
  - The proposal path originally hard-rejected contradictory
    proposals. A user correcting a wrong fact would have been
    silenced. Changed to tag-and-forward.
  These are exactly the conflicts the "contract before code"
  discipline exists to surface.
