# NOTES — lllm (Tier 1: LLLM)

NOTES.md — open questions, decisions, and philosophical stance for LLLM.

## Why LLLM exists

The Forge Stack has primitives for everything except *voice*. P9 can
store claims. P13 can classify them. P10/P14 can score them. P15 can
gate them. But none of them can hold a conversation.

LLLM is the answer to "what does it sound like?" It is a conversational
surface over the substrate — not a general-purpose assistant, not a
chatbot. A voice that reads from claims and only speaks what is
validated.

## The core insight

Most conversational systems conflate two things that should never be
combined:

1. **Content** — what is being said.
2. **Phrasing** — how it is being said.

They mix them into a single neural pipeline, and then a bug in phrasing
can silently corrupt content. LLLM keeps them separate by design:
content comes from claims (validated, cited, locked), phrasing comes
from templates and (in v0.2) n-grams. The n-gram model cannot alter
content. Locked slots enforce it.

## Locked slots, not trust

The lock isn't "we hope the n-gram model is well-behaved." The lock is
a mechanical assertion: before a reply is emitted, the slot text is
verified byte-for-byte against the intended content. If a phrasing
candidate altered a slot, the candidate is discarded and the bare
template is used.

This is the difference between *hoping* and *enforcing*.

## Trust the substrate, verify at v0.2

v0.1 reads P9 without verifying signatures. This is a real limitation
and it is stated in the README. The reason is discipline: "v0.1 requires
P9 and nothing else" is a clean boundary, and adding P1/P2 to v0.1
would blur it.

v0.2-B adds signature verification via P2's `verify_capsule`. Once that
arrives, no claim enters the pipeline without a valid signature. The
Known Limitations entry is removed in the same commit.

## Polarity is required, not defaulted

A claim with no `capsule.polarity` is excluded from answers, and the
trace records `polarity_missing`. The alternative — assuming `affirm`
by default — silently invents information. "The sky is green" and "the
sky is not green" are different claims; a substrate that stores one
without polarity is ambiguous. LLLM refuses to guess.

## Contradiction is tagged, not rejected

v0.3 adds the proposal path. When a user states something new, the
Keystone Gate (P13) checks it against stored FACT / COUNTER / CONTEXT.
If it contradicts a fact, the proposal is tagged `contradicts: <id>` —
**but it still goes to the human**.

The reason is important: a user may be *correcting* a wrong stored fact.
If the gate hard-rejected the proposal, the correction would never reach
the human who could approve it. Tagging keeps both the correction and
the existing fact visible, and the human decides.

## trace_query is not self_query

"Who are you?" is a `self_query` — it asks about LLLM's self-model in
P9. "How did you work that out?" is a `trace_query` — it asks about
*this turn's* trace.

These are different intents. Folding them together means either
self-queries start depending on the last turn (wrong), or trace queries
have no answer (also wrong). They are separate, and precedence puts
`trace_query` first so it wins over anything it might look like.

## Conversation state is in-session at v0.4

v0.4 conversation state (topic, recent turns, open questions) does not
persist across restarts. This is deliberate: persistence belongs to
v0.5, when the state itself becomes a signed trace in P4. Persisting
unsiged state in v0.4 would create a shadow substrate that no one can
verify.

## Open questions

- **Q1.** Match score formula. The SPEC must define it precisely. Open
  question: does `subject` matching weight higher than term matching?
  Proposed: yes — subject match × 3, term match × 1, object match × 2.
  To be tuned when the fixture is built.
- **Q2.** Clarify δ. Default 0.10 is a guess. May need tuning after the
  first real conversations. It is configurable via an environment
  variable for tuning without code changes.
- **Q3.** N-gram corpus. The old LLLM engine was trained on James's own
  writing. Is that the right corpus for a conversational voice, or does
  LLLM need a broader conversational corpus for phrasing? Deferred to
  v0.2-C.
- **Q4.** Multi-turn ambiguity. If a user says "tell me more" without a
  topic, LLLM must ask "which topic?" rather than guess. This arrives
  with v0.4 state.

## Decisions at sign-off (2026-11-13)

- SPEC v0.1.0 signed off by James after pre-sign-off corrections, each
  marked in the SPEC. The two that change answers: a candidate must
  match the subject or object (term-only matches such as "is" made
  every claim a candidate), and `Yes.`/`No.` is used only when the
  question names the claim's object.
- `traces/` instead of `trace/` (SPEC §12a): avoids shadowing the
  standard-library `trace` module.
- The `clarify` intent answers from the last turn's trace (SPEC §8).

## Open questions raised at sign-off

- **Q5. Which faces may be spoken as fact?** v0.1 ignores the P13 face
  keys (SPEC §3), so an active UNKNOWN (a dream), OPINION or FICTION
  claim with a polarity would be answered like a FACT. Proposed: the
  Cockpit records `polarity` only for FACT, COUNTER and CONTEXT claims,
  so the others are excluded as `polarity_missing` until a later SPEC
  reads faces. Owner: James.
  **Resolved 2026-11-13 — James: "lllm should be stored in a different db and be
  opinions"; the face rule decided by the VS Code AI on James's delegation ("i sign, yo decide").** Polarity only for FACT /
  COUNTER / CONTEXT; LLLM output goes to `lllm.db` as OPINION.
- **Q6. Two LLLMs, one name.** `JamesTheGiblet/lllm` (the n-gram
  engine: `lllm gen`, `lllm info`, used by the Cockpit's dream/think/
  reason and the Weaver) and this repo (the Voice) both want the
  `lllm` command. Which owns it? Owner: James.
  **Resolved 2026-11-13 — James: "lllm commands go via the legacy".** The Voice is
  used through The Legacy's Voice panel; the old engine keeps `lllm`.
- **Q7. Who signs v0.5 traces?** The stack's ledger has one signer,
  the operator key. Signing traces needs that key (a passphrase per
  session) or a separate consumer ledger anchored to the root (P5
  NOTES Q1). Owner: James.
  **Resolved 2026-11-13 — James: "i sign".** v0.5 traces are signed with the
  operator key.
- **Q8. Who writes polarity?** No Forge Stack code writes
  `capsule.polarity` yet, so on a real `forge.db` every claim is
  `polarity_missing`. Proposed: a Cockpit v1.3 layer. Owner: James.
  **Resolved 2026-11-13, decided by the VS Code AI on James's delegation ("i sign, yo decide"):** the Cockpit's current layer (v1.2, not yet frozen)
  writes it: `remember` and `inbox commit` record `polarity` for FACT,
  COUNTER and CONTEXT ("is not" → negate, `--polarity` overrides).

- **Q9. The clarify intent is mostly unreachable.** With the locked
  precedence (question above clarify), "what do you mean?", "can you
  clarify?" and "which one?" all parse as questions; only "i don't
  understand" reaches `clarify`. Proposed: move `clarify` above
  `question` in a SPEC v0.1.1 (a locked commitment, so James's call).
  Pinned in FIXTURE.md. Owner: James.
  **Resolved 2026-11-13, decided by the VS Code AI on James's delegation ("i sign, yo decide"):** SPEC 0.1.1 moves `clarify` above `question`
  and anchors its patterns.

## What LLLM refuses to be

- A general-purpose chatbot. It answers from claims or says `unknown`.
- A generative model. It phrases templates; it does not generate prose.
- A silent learner. Every proposal needs a human seal.
- A black box. Every reply has a trace.

## Known issues carried forward from earlier LLLM work

The old LLLM project had several known issues that informed this
rebuild:
- Casing glitches in generated paths — not applicable here (templates,
  not generation).
- Dedupe credits wrong origin — not applicable (no corpus in v0.1).
- ~1/3 of vocabulary was identifiers — not applicable (locked slots
  keep identifiers verbatim).

The new LLLM is a rebuild, not a patch. It learns from the old issues
without inheriting the old code.
