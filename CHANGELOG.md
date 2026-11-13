# CHANGELOG — lllm (Tier 1: LLLM)

CHANGELOG.md — build history for LLLM, latest entry at top.

## [Unreleased]

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
