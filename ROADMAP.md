# LLLM — Roadmap

From spec to v0.5. The contract is written before the code, and nothing
starts until the step before it is frozen.

---

## Rules of the road

1. **SPEC before code.** Each version's behaviour is written into the
   SPEC before it's built.
2. **Freeze gates.** A version is frozen when every acceptance
   criterion passes in `test_lllm.py`. No work on the next version
   until then.
3. **Dependencies arrive on schedule.** A version may only import the
   primitives listed for it in the README's dependency table.
4. **Stdlib only, Termux baseline.** Every gate is checked on the
   phone, not just on a desktop.
5. **Each milestone ships alone.** If a version has two milestones,
   each one is releasable without the other.

---

## Phase 0 — SPEC (no code)

**Goal:** a written contract that v0.1 can be built and tested against.

**SPEC must contain:**
- [ ] **P9 mapping table**, field by field: LLLM field → P9 source → default
- [ ] **Status mapping:** `is_active` + `superseded_by` → `active` /
      `superseded` / `inactive`
- [ ] **Polarity rule:** a claim with no `capsule.polarity` is excluded
      from answers, and the trace records it as `polarity_missing`
- [ ] **Capsule shape:** which keys LLLM expects inside `capsule`
      (`subject`, `object`, optional `predicate`, `polarity`)
- [ ] **Intent rules:** the patterns that fire each intent, plus their
      precedence when several match
- [ ] **Intent precedence:** `trace_query > self_query > question >
      statement > clarify > greeting > farewell`
- [ ] **Matching:** how the match score is computed (terms, subject,
      object), with its range and a worked example
- [ ] **Ranking:** v0.1 ranks by match score, then breaks ties on
      `created_at`
- [ ] **Clarify rule:** δ = 0.10, the definition of "disagree" (object
      or polarity differs), and the agree case (answer citing both)
- [ ] **Response plans:** trigger conditions for all seven plans
      (`answer`, `explain_self`, `trace`, `clarify`, `unknown`,
      `acknowledge`, `social`)
- [ ] **Template set:** one or more templates per plan, with named slots
- [ ] **Locked-slot contract:** which slots are locked, how they're
      marked in templates, and that they must render verbatim
- [ ] **Trace format:** fields and console layout for v0.1
- [ ] **P9 access:** opened read-only, so LLLM physically cannot write
- [ ] **v0.1 acceptance criteria** (copied from below and expanded into
      test cases)

**Gate:** you sign off the SPEC. It's then frozen for v0.1, and changes
need a version bump.

---

## Phase 1 — Scaffold

**Goal:** a skeleton that runs end to end and returns `unknown` for
everything.

- [ ] Directory layout as in the README
- [ ] `lllm.py` REPL: read input, run the pipeline, print the reply
      and trace
- [ ] Stub for each layer with its input and output types defined
- [ ] **Fixture P9:** a small SQLite file using the real P9 schema,
      seeded with test claims:
  - active claims
  - a superseded pair
  - an inactive claim
  - a claim with no polarity
  - two competing claims (one pair that disagrees, one that agrees)
  - zero `agent://lllm` claims, so the bootstrap case gets tested
- [ ] `test_lllm.py` harness running against the fixture
- [ ] **Fixture manifest:** documented list of test queries and their
      expected outcomes (candidates, statuses, exclusions). The fixture
      is a contract, not just data.

**Gate:** the REPL runs in Termux, returns `unknown` for every
question, the tests run and fail as expected, and the fixture manifest
matches reality.

---

## v0.1 — The Voice speaks (P9 only)

Build in pipeline order. Each layer has its own mini-gate.

### 1. Understand
- [ ] Tokeniser
- [ ] Intent rules for `greeting`, `question`, `statement`,
      `self_query`, `trace_query`, `clarify`, `farewell`
- [ ] Term, entity and negation extraction
- **Mini-gate:** a table of sample inputs maps to the expected parses
  (including intent precedence when multiple match)

### 2. Know
- [ ] P9 reader, read-only, applying the mapping and status tables
- [ ] Filters to `active` and drops claims with polarity missing
- [ ] Match scoring, with ranking by score then `created_at`
- [ ] ISO 8601 `created_at` parsed via `datetime.fromisoformat`
- **Mini-gate:** fixture queries return the expected ranked candidates

### 3. Decide
- [ ] All seven plans
- [ ] Clarify rule with δ
- [ ] Trace plan returns the previous turn's trace
- **Mini-gate:** each plan fires on its fixture case and on nothing else

### 4. Speak
- [ ] Templates with locked slots
- [ ] Verbatim slot rendering, checked by assertion
- **Mini-gate:** every template renders with its slots intact

### Trace
- [ ] Console trace on every reply

### v0.1 acceptance criteria
- [ ] Empty P9: every question returns `unknown`
- [ ] A question matched by one active claim gets `answer`, citing its
      `claim_id`
- [ ] Superseded and inactive claims are never used
- [ ] A claim with polarity missing is never used, and the trace says
      why (`polarity_missing`)
- [ ] Two competing claims within δ that disagree get `clarify`
- [ ] Two competing claims within δ that agree get `answer`, citing
      both
- [ ] A self-query with no `agent://lllm` claims gets `unknown`
- [ ] A self-query once `agent://lllm` claims are seeded gets
      `explain_self`, with citations
- [ ] A `trace_query` right after an `answer` returns the trace of that
      answer
- [ ] A statement gets the fixed `acknowledge` reply, and P9 is
      unchanged (verified by hash)
- [ ] Greetings, thanks and farewells get `social`
- [ ] Every reply prints a full trace: parse, candidates, plan and
      reason, template, slots
- [ ] No imports outside the standard library and P9
- [ ] All tests pass in Termux

**Freeze → tag `v0.1.0`.**

---

## v0.2 — Trust and verification (+ P14, P1, P2)

There are three milestones, and each one ships alone.

### v0.2-A: λ ranking (+ P14)
- [ ] SPEC: the P14 call contract (inputs, outputs, failure behaviour)
- [ ] Ranking becomes match × λ, still breaking ties on `created_at`
- [ ] If P14 is unavailable, fall back to v0.1 ranking, and the trace
      says so
- [ ] Neutral λ = 1.00 is handled correctly, ranking between trusted
      and distrusted claims
- **Gate:** the fixture claims with known λ values rank as expected,
  and the fallback is tested

### v0.2-B: Signature verification (+ P1, P2)
- [ ] SPEC: which P9 capsules are verified, and what happens on
      failure
- [ ] Each loaded claim's signature is checked with P2
      (`verify_capsule`) before the claim is used
- [ ] A claim that fails verification is excluded, and the trace
      records `signature_invalid`
- [ ] The v0.1 "trusts P9" limitation is removed from the Known
      Limitations
- **Gate:** a fixture claim with a tampered capsule is excluded and
  traced

### v0.2-C: n-gram phrasing
Split further if needed: (c1) wrap the old engine for slot-fill mode,
(c2) candidate scoring.
- [ ] Harvest the old LLLM engine into `speak/` and build `corpus/`
- [ ] N-grams fill only the connective text between locked slots
- [ ] Candidate scoring by likelihood
- [ ] **Slot check:** if any slot is altered, fall back to the bare
      template, and the trace logs it
- [ ] Trace adds the candidates and their scores
- **Gate:** a deliberately corrupting phrasing (e.g. one that drops
  "not") is caught and falls back every time

**Freeze → tag `v0.2.0`.**

---

## v0.3 — Supervised learning (+ P13, P15, P4)

- [ ] SPEC: the proposal format, gate tags and HAL seal contract
- [ ] A statement becomes a proposal
- [ ] P13 Keystone Gate tags each proposal `clean` or
      `contradicts: <claim_id>`, and never rejects
- [ ] Proposals go into the HAL buffer as `pending`
- [ ] P15 approve or reject produces a signed seal in P4
- [ ] An approved `contradicts` proposal supersedes the old claim in
      the same seal
- [ ] LLLM can say "you told me X — awaiting validation", but never
      states pending claims as fact
- **Gate:**
  - [ ] a correction to a wrong fact reaches the human and, once
        approved, replaces the old claim
  - [ ] LLLM itself never writes to P9

**Freeze → tag `v0.3.0`.**

---

## v0.4 — Conversation state

- [ ] SPEC: the state model (current topic, recent turns, open
      questions) and its lifetime
- [ ] Follow-ups resolve against the topic ("what about its size?")
- [ ] A clarify reply can be answered on the next turn
- [ ] State is visible in the trace
- [ ] State is in-session only; restart clears it. Persistence arrives
      at v0.5.
- **Gate:**
  - [ ] a scripted multi-turn conversation resolves every follow-up
        correctly
  - [ ] after a reset, no stale state leaks into new conversations

**Freeze → tag `v0.4.0`.**

---

## v0.5 — Signed traces (+ P1, P2, P4)

- [ ] SPEC: the trace capsule schema
- [ ] Each trace is canonicalised with P1, signed with P2, and appended
      to P4
- [ ] "How did you work that out?" is answered from the signed trace
      (trace_query reads from P4, not just in-memory)
- [ ] Verifier: any reply can be checked against its ledger entry
- [ ] Conversation state becomes persistent across restarts, backed by
      the ledger
- **Gate:**
  - [ ] every reply has a verifiable signed trace
  - [ ] a tampered trace fails verification

**Freeze → tag `v0.5.0`.**

---

## Risks to watch

| Risk | Mitigation |
|---|---|
| The P9 capsule shape varies between claims | The SPEC fixes the expected keys; claims missing them are excluded and traced |
| Intent rules grow into a tangle | Fixed precedence in the SPEC; each new rule arrives with its own test |
| Recency ranking in v0.1 is mistaken for trust | Stated in the README limitations; λ arrives in v0.2 |
| Signature verification is missing until v0.2 | Stated in the README limitations; arrives in v0.2-B |
| The old n-gram engine doesn't fit locked slots | v0.2-C is separate from A and B, so trust and verification ship regardless |
| The old engine wraps-but-corrupts (e.g. drops "not") | The slot check catches it and falls back every time; a deliberately corrupting case is a required test |
| Scope creep between versions | Freeze gates plus the dependency table |
| The fixture drifts from reality | The Phase 1 fixture manifest is a written contract, checked against reality on every run |
| A trace_query asked before any reply | `trace` plan returns "no previous reply yet"; tested at v0.1 |

---

## Now → next

1. Write the SPEC (Phase 0)
2. Sign it off
3. Scaffold plus the fixture P9
4. Build the pipeline in order: Understand → Know → Decide → Speak
5. Run the v0.1 acceptance criteria in Termux
6. Freeze v0.1.0
