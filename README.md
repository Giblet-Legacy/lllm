# LLLM — Low Level Language Model

**Tier 1 Consumer — The Voice**

A conversational language model you can see all the way through. LLLM
takes natural language input, parses intent, reads validated claims
from P9 (substrate-layer), decides a response plan, and replies. Every
reply can be traced back to the claims and rules that produced it. It
never invents facts, and when no claim covers a question it says so.

No neural nets. No black-box weights. Just counting, rules, and claims.

| | |
|---|---|
| **Tier** | Tier 1 — Consumer (The Voice) |
| **Consumed by** | The Cockpit, The Legacy, any conversational surface |
| **Licence** | MSL-1.0 |
| **Author** | James Gilbert (Giblets Forge) |
| **Status** | 0.1.1 frozen (2026-11-13): 20/20 on the laptop and the S24 (Termux). 0.1.2 (`lllm_v0_1_2.py`, SPEC_V0_1_2.md: face text, aspects) frozen; Legacy v7 uses it |

### Dependencies by version

| Version | Requires |
|---|---|
| v0.1 | P9 Substrate |
| v0.2 | + P14 (Leighton weight λ), P1, P2 (signature verification) |
| v0.3 | + P13 DataCube (Keystone Gate), P15 HAL, P4 Ledger |
| v0.5 | + P1 Envelope, P2 Sign (signed traces) |

A v0.1 consumer needs P9 and nothing else.

---

## What it does

- **General conversation** (v0.1): greets, answers, asks back, admits when it doesn't know
- **Grounded answers** (v0.1): answers only from active claims in P9
- **Citations** (v0.1): every answer names the `claim_id`s it used
- **Self-explanation** (v0.1, once bootstrapped): answers questions about its own architecture from claims whose subject is `agent://lllm`
- **Trace lookup** (v0.1): "how did you work that out?" answers from the current turn's trace
- **Natural phrasing** (v0.2): n-gram phrasing on top of templates
- **Learns under supervision** (v0.3): statements become proposals, are gated, buffered, and need human validation via HAL
- **Signed traces** (v0.5): every reply becomes a signed, hash-chained ledger event

## What it doesn't do

- It doesn't reason like a large neural model
- It doesn't generate long-form text with sustained coherence
- It doesn't invent facts. If no active claim covers a question, the `unknown` plan fires.
- It doesn't write to the substrate. Only humans, via HAL, commit claims.
- It doesn't verify signatures on loaded claims in v0.1 (arrives v0.2)

---

## Forge Stack integration

LLLM does not invent new physics. It orchestrates the frozen primitives.

| LLLM component | Primitive | Why |
|---|---|---|
| Claims | P9 substrate-layer | Single source of truth. LLLM reads only. |
| Self-model | P9, filtered by `subject = agent://lllm` | Self-knowledge is just claims about LLLM. |
| Contradiction check | P13 datacube-layer (Keystone Gate) | Runs at proposal time and tags conflicts for the human. |
| Human validation | P15 hal-layer | Approvals and refusals become signed seals, not silent database flips. |
| Trace records | P2 sign-layer + P4 ledger-layer | Every reply becomes a signed, hash-chained event. |
| Canonicalisation | P1 envelope-layer | For any signed artefact (trace, seal). |

> **Naming note:** `substrate-layer` (P9) is the primitive that holds
> claims. `scp-substrate` is a separate consumer — the 3D visual viewer.
> LLLM reads from P9, not from the viewer.

---

## Claims as LLLM sees them

LLLM reads this view of each claim. The P9 reader in `know/` maps each
field from P9's schema (`claim_id, signer, capsule, is_active,
superseded_by, created_at`). The full mapping table is in the SPEC,
which is authoritative.

| LLLM field | P9 source | Default if absent |
|---|---|---|
| `claim_id` | `claim_id` | required |
| `subject` | `capsule.subject` | required |
| `predicate` | `capsule.predicate` if present | `is` |
| `object` | `capsule.object` | required |
| `polarity` | `capsule.polarity` if present | **required; claim excluded if absent** |
| `source` | `signer` | `unknown` |
| `created_at` | `created_at` | required |
| `status` | `is_active` + `superseded_by` | required |

**λ (Leighton weight)** is not in the v0.1 view. λ is never stored. P14
computes it from the claim's observation stream:
`λ(t) = 1.00 + (λ₀ − 1.00) × e^(−kt)`. Neutral is 1.00. Higher means
more trusted and lower means less trusted, and decay pulls back toward
1.00. LLLM adds λ ranking at v0.2, through P14.

**Status mapping (P9 → LLLM):**

| `is_active` | `superseded_by` | LLLM status |
|---|---|---|
| 1 | — | `active` |
| 0 | set | `superseded` |
| 0 | null | `inactive` (withdrawn without a replacement) |

Only `active` claims are spoken as fact. "Validated" in this document
always means `status = active`.

---

## Architecture

Four layers in a pipeline. Each is small, inspectable and replaceable.

input ──► [1 UNDERSTAND] ──► [2 KNOW] ──► [3 DECIDE] ──► [4 SPEAK] ──► reply
▲                            │
P9 substrate (claims)              trace log
▲
[P15 HAL buffer] ◄── proposed claims
▲
P13 Keystone Gate (contradiction tagging)

```

### 1. Understand: input to meaning
- Tokeniser
- Rule-based intent detection: `greeting`, `question`, `statement`,
  `self_query`, `trace_query`, `clarify`, `farewell`
- Key-term and entity extraction, including negation detection
- **Output:** a structured parse (intent, terms, entities, negation,
  raw text)
- **Intent precedence:** trace_query > self_query > clarify >
  question > statement > greeting > farewell

### 2. Know: the claim layer
- Reads claims from P9
- Matches the parse against claims by subject, predicate, object and
  terms
- Filters to `status = active`
- Excludes claims with no `polarity`; trace records `polarity_missing`
- Self-model = active claims with `subject = agent://lllm`
- **Output:** candidate claims ranked by:
  - **v0.1:** match score, then tie-break on `created_at` (most recent
    wins)
  - **v0.2+:** match score × λ (from P14), then tie-break on `created_at`

### 3. Decide: the dialogue manager
Chooses one response plan:

| Plan | Fires when |
|---|---|
| `answer` | One claim clearly covers the question |
| `explain_self` | A self-query matches self-model claims |
| `trace` | A trace_query asks how the last reply was worked out |
| `clarify` | Several claims compete (see rule below) or the parse is ambiguous |
| `unknown` | No active claim covers it |
| `acknowledge` | The user stated something (proposal path from v0.3) |
| `social` | Greetings, thanks, farewells |

**Clarify rule:** if the top two candidates' ranking scores (match
score in v0.1, match × λ from v0.2) are within margin **δ** of each
other (default `0.10`, configurable) **and** they disagree on object or
polarity, `clarify` fires instead of `answer`. If they agree, LLLM
answers and cites both.

### 4. Speak: surface generation
- **Templates** (v0.1) give each plan its structure
- **Locked slots:** claim-bearing tokens (subject, predicate, object,
  polarity/negation, cited `claim_id`) are fixed slots. Nothing
  downstream may alter them.
- **N-gram phrasing** (v0.2), harvested from the old LLLM engine, fills
  only the connective text *between* locked slots
- Candidate phrasings are scored by n-gram likelihood, and the most
  natural wins
- **Slot check:** before a reply is emitted, the locked slots are
  verified as unchanged. If they've changed, LLLM falls back to the
  bare template.

---

## Proposal path & validation buffer (v0.3+)

LLLM does not mutate the substrate. Ever.

When a user states something new:

1. LLLM turns it into a proposal (`acknowledge` plan)
2. **P13 Keystone Gate** checks it against stored FACT / COUNTER /
   CONTEXT claims
   - No conflict: tag `clean`
   - Conflict: tag `contradicts: <claim_id>`. **Not rejected.** A user
     correcting a wrong stored fact must still reach a human.
3. The proposal enters the HAL buffer as `pending`, carrying its tag
4. A human uses **P15 HAL** to approve or reject. Each decision
   produces a signed seal appended to **P4**
   - Approving a `contradicts` proposal also marks the old claim
     `superseded`, in the same seal
5. Only on approval is the claim written to P9 as `active`

LLLM never answers from pending claims. It may say *"you told me X —
awaiting validation"*, but X is never spoken as fact until a seal
exists.

---

## Traceability

Every reply produces a trace record:

- Input parse
- Claims considered and claims used (`claim_id`)
- Response plan and why it fired (including the clarify margin when
  relevant)
- Template and locked slots
- N-gram candidates and scores (v0.2+)

| Version | Trace |
|---|---|
| v0.1 | Printed to console |
| v0.5 | P2-signed capsule appended to P4 |

From v0.5, a reply that can't be cryptographically traced is a bug,
not a caveat.

---

## Bootstrapping

An empty P9 means LLLM has nothing to ground answers in, so every
question returns `unknown`.

1. Use **explorer-d334-forge** (The Cockpit CLI) to build a set of
   active claims in P9
2. Once P9 has claims, LLLM can answer questions that reference them
3. For self-explanation, add claims with `subject = agent://lllm`
   describing its architecture

LLLM has no self-knowledge until its self-model is bootstrapped. That
is honest, not broken.

---

## Design principles

1. **Truth from claims, fluency from counts.** Locked slots enforce it.
2. **Nothing unvalidated is spoken as fact.**
3. **Everything is inspectable.** Untraceable reply = bug.
4. **Low level by choice.** Stdlib-first, Termux baseline.
5. **Honest about limits.** "I don't know" is a first-class reply.

---

## Requirements

- Python 3 (standard library only)
- Runs in Termux on Android as the baseline target
- Read access to P9 substrate-layer

---

## Project layout

```

lllm/
├── understand/     # tokeniser, intent rules, entity + negation extraction
├── know/           # P9 reader + field mapping, claim matching, ranking
├── decide/         # dialogue manager, clarify rule, P13 gate (v0.3)
├── speak/          # templates + locked slots (v0.1), n-gram (v0.2)
├── buffer/         # proposal buffer (v0.3)
├── traces/         # per-reply trace records (not trace/: SPEC §12a)
├── lllm.py         # entry point / REPL
├── fixture_p9.py   # builds the fixture P9 (tests only)
├── FIXTURE.md      # the fixture manifest: queries and expected outcomes
└── test_lllm.py    # test suite

```

`corpus/` for the n-gram phrasing model is added at v0.2, when the old
engine is harvested.

---

## Roadmap

- **v0.1 (current):** REPL, intent rules, read-only active claims from
  P9, recency ranking, citations, templates with locked slots, clarify
  rule, honest `unknown`, trace_query, console trace
- **v0.2:** λ ranking via P14, signature verification via P1/P2, n-gram
  phrasing between locked slots, candidate scoring, slot check
- **v0.3:** proposal path, P13 contradiction tagging, HAL buffer, P15
  seals to P4, supersession
- **v0.4:** conversation state (topic tracking, follow-ups), in-session
  only
- **v0.5:** full trace records as signed P2 capsules appended to P4

See ROADMAP.md for the detailed build plan with acceptance gates.

---

## Known limitations (v0.1.0)

- No trust ranking: claims rank by match then recency. λ arrives at
  v0.2, via P14
- No signature verification: v0.1 trusts P9. P1/P2 verification arrives
  at v0.2
- No n-gram phrasing: replies are templated, so they read as more
  structured than natural
- No proposals stored: every user statement returns a fixed
  `acknowledge` template
- Trace is console-only until v0.5
- No conversation state: each turn is independent
- No self-model by default: `explain_self` returns `unknown` until
  `agent://lllm` claims are bootstrapped
- Templated replies are British English only

---

*I wanted it. So I forged it. Now forge yours.*
— James Gilbert (Giblets Forge)
