# CHANGELOG — lllm (Tier 1: LLLM)

CHANGELOG.md — build history for LLLM, latest entry at top.

## [Unreleased] — SPEC 0.1.1 (2026-11-13)

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
- That conversation found the two §7/§9.1 answer bugs ("what is blue?"
  → "Yes. sky is blue."), which the 0.1.0 tests had not covered.

### Ugly
- (none)

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
