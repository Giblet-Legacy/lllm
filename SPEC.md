# SPEC — lllm (Tier 1: LLLM), v0.1.0

SPEC.md — specification for LLLM v0.1.0.

Function:
    The contract for v0.1. Defines every mapping, rule, plan, template,
    and acceptance criterion required to build and freeze v0.1.0.

Tier:     Tier 1 — Consumer (The Voice)
Depends:  P9 substrate-layer (read-only)
Version:  SPEC 0.1.0
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)

---

## 1. P9 mapping table

Each row shows: LLLM field → P9 source → default if absent. If the
default is `required`, a claim missing that field is excluded from
the pipeline and the trace records the exclusion reason.

| LLLM field | P9 source | Default if absent |
|---|---|---|
| `claim_id` | `claims.claim_id` | required |
| `subject` | `json_extract(capsule, '$.subject')` | required |
| `predicate` | `json_extract(capsule, '$.predicate')` | `is` |
| `object` | `json_extract(capsule, '$.object')` | required |
| `polarity` | `json_extract(capsule, '$.polarity')` | required; excluded if absent |
| `source` | `claims.signer` | `unknown` |
| `created_at` | `claims.created_at` (ISO 8601) | required |
| `status` | `claims.is_active` + `claims.superseded_by` | required |

If the `capsule` column is not valid JSON, the claim is excluded, and
the trace records `capsule_invalid`.

`created_at` must be parsed with `datetime.fromisoformat`. Never with
`float()`.

## 2. Status mapping

| `is_active` | `superseded_by` | LLLM status |
|---|---|---|
| 1 | NULL or empty | `active` |
| 0 | set | `superseded` |
| 0 | NULL or empty | `inactive` |

Only `status = active` claims enter the pipeline. `superseded` and
`inactive` claims are excluded, and the trace records `status_excluded`.

## 3. Capsule shape

LLLM expects the following keys inside `claims.capsule` (as a JSON
object):

- `subject` — string, required
- `object` — string, required
- `predicate` — string, optional, defaults to `is`
- `polarity` — string, must be `"affirm"` or `"negate"`; required
  for the claim to be used

Any other keys in `capsule` (e.g. `FACT`, `UNKNOWN` from P13) are
ignored by LLLM v0.1. Future versions may read them.

## 4. Polarity rule

A claim with no `capsule.polarity`, or with a polarity other than
`"affirm"` or `"negate"`, is excluded from answers. The trace records
`polarity_missing` or `polarity_invalid`.

Rationale: assuming `affirm` silently invents information. "The sky
is green" and "the sky is not green" are different claims; a substrate
that stores one without stating which is ambiguous. LLLM refuses to
guess.

---

## 5. Intent rules

Each intent has a set of regex patterns. The intent that fires is the
highest-precedence intent whose pattern matches. Precedence:

1. `trace_query`
2. `self_query`
3. `question`
4. `statement`
5. `clarify`
6. `greeting`
7. `farewell`

If no pattern matches, the default intent is `question`.

### 5.1 `trace_query`
Patterns (case-insensitive):
- `how (did|do) you (work|know|figure) (that|this|it) out`
- `why did you (say|answer|reply)`
- `where did (that|this|it) come from`
- `what (was|were) your (reasoning|trace)`
- `show (me )?your (trace|reasoning)`

### 5.2 `self_query`
Patterns:
- `who are you`
- `what are you`
- `what can you do`
- `how (do|does) (you|lllm) work`
- `tell me about (yourself|lllm)`

### 5.3 `question`
A sentence ending in `?`, or starting with a WH-word:
`who`, `what`, `where`, `when`, `why`, `how`, `which`, or one of
`is`, `are`, `was`, `were`, `do`, `does`, `did`, `can`, `could`,
`will`, `would`, `should`.

### 5.4 `statement`
A sentence that is not a question, not social, and does not contain
`not` alone as a filler (e.g. "not bad" is a statement).

Implementation rule: `statement` fires only if no `clarify`,
`greeting` or `farewell` pattern matches. Otherwise "hello" (not a
question) would be a statement, since `statement` has higher
precedence.

### 5.5 `clarify`
Patterns:
- `what do you mean`
- `can you (clarify|explain)`
- `i don'?t understand`
- `which one`

### 5.6 `greeting`
Patterns:
- `^(hi|hello|hey|hiya|good (morning|afternoon|evening))\b`
- `^(greetings|howdy)\b`

### 5.7 `farewell`
Patterns:
- `^(bye|goodbye|see you|good ?night|cheers)\b`
- `^(thanks|thank you|cheers)\b`

(`cheers` appears twice above but in no `greeting` pattern, so
`cheers` alone fires `farewell` (social). Corrected before sign-off:
the draft said it fired `greeting`.)

## 6. Matching and ranking

For a `question` parse, LLLM matches against each active claim:

- **Subject match** — the claim's `subject` appears in the input terms
  (case-insensitive substring on the tokenised terms). Weight: ×3.
- **Object match** — the claim's `object` appears in the input terms.
  Weight: ×2.
- **Term match** — the number of shared tokens between the claim's
  `subject + object + predicate` and the input terms, capped at 5.
  Weight: ×1 each.

Match score = `3*s + 2*o + t`, where `s`, `o` ∈ {0, 1}, `t` ∈ [0, 5].

Only claims with **s = 1 or o = 1** are candidates. A claim that
shares only terms (for example the word "is") is not a candidate.
(Corrected before sign-off: with "score > 0", every claim shares "is"
with "is the moon cheese?", so a stored "sky is blue" would have been
answered as "Yes. sky is blue".)

**Terms** are the lower-cased word tokens of the input (letters,
digits, `'`, `:`, `/`, `.`, `-`; trailing punctuation stripped).
**Subject match** holds when the claim's subject, lower-cased and
tokenised the same way, appears as a contiguous run of input terms.
Object match likewise. `t` counts distinct shared tokens.

**Ranking v0.1:** sort by match score descending, then by `created_at`
descending (most recent wins).

Worked example: input `"is the sky blue"`.
- Claim A: `{subject: "sky", object: "blue", predicate: "is"}`
  → s=1 (sky in terms), o=1 (blue in terms), t=3 (sky, is, blue all
  in terms) → score = 3+2+3 = 8.
- Claim B: `{subject: "sea", object: "blue", predicate: "is"}`
  → s=0, o=1, t=2 → score = 0+2+2 = 4.

Claim A ranks above B.

## 7. Clarify rule

Let `top1` and `top2` be the two highest-scoring candidates.

**Clarify fires if all of these hold:**
1. `top1.score - top2.score ≤ δ`, where `δ = 0.10 × top1.score`
   (relative margin, default 0.10, configurable via env
   `LLLM_CLARIFY_DELTA`).
2. `top1` and `top2` disagree on **object** or **polarity**.

**Agree case:** if `top1` and `top2` score within δ and agree on both
object and polarity, LLLM answers and cites both: the `claim_id` slot
holds both ids, comma-separated (`[a1b2c3d4e5f6, 0f9e8d7c6b5a]`).

**No-clarify case:** if only one candidate exists, or the score gap
exceeds δ, LLLM answers with `top1` only.

---

## 8. Response plans

The dialogue manager fires exactly one plan per turn.

| Plan | Trigger |
|---|---|
| `trace` | Intent is `trace_query` and a previous reply exists |
| `explain_self` | Intent is `self_query` and active self-model claims exist |
| `answer` | Intent is `question` and at least one candidate exists and clarify rule does not fire |
| `clarify` | Intent is `question` and clarify rule fires |
| `unknown` | Intent is `question` or `self_query` and no candidate matches, or `trace_query` with no previous reply |
| `acknowledge` | Intent is `statement` |
| `social` | Intent is `greeting` or `farewell` |

**Intent `clarify`** ("what do you mean?") fires the `trace` plan when
a previous reply exists (it explains what the last reply rested on),
else `unknown`. (The draft listed the intent but gave it no plan.)

**`explain_self`:** self-model candidates are the active, polarised
claims with `subject = agent://lllm`, ranked by term match then
`created_at`; the reply renders the top three, one template each.

## 9. Templates

One or more templates per plan. `{slot}` marks a locked slot.

### 9.1 `answer`
- `Yes. {subject} {predicate} {object}. [{claim_id}]`
- `{subject} {predicate} {object}. [{claim_id}]`
- `From the substrate: {subject} {predicate} {object}. [{claim_id}]`

If `polarity == "negate"`, the template is rendered as:
- `No. {subject} {predicate} not {object}. [{claim_id}]`

**Template choice** (deterministic):
- `answer_yes` (`Yes. …`) or `answer_no` (`No. … not …`): the
  question names the claim's object (o = 1) and has no negation of its
  own. "Is the sky blue?" with "sky is blue" → `Yes.`
- `answer_state` (`{subject} {predicate} {object}.`, or `… not …`
  for negate): every other answer. "Is the sky green?" with only
  "sky is blue" → "sky is blue.", never "Yes." (corrected before
  sign-off).
- `From the substrate: …` is kept for `explain_self` fallbacks only.

**Cited ids** in replies are the first 12 hex characters of
`claim_id` (as a short git hash); the trace carries the full id.

### 9.2 `explain_self`
- `{subject} {predicate} {object}. [{claim_id}]`

(Rendered identically to `answer`; the plan label distinguishes it in
the trace.)

### 9.3 `clarify`
- `I have more than one active claim that matches. One says {subject} {predicate} {object1} [{claim_id1}], another says {subject} {predicate} {object2} [{claim_id2}]. Which one do you mean?`

### 9.4 `unknown`
- `I don't have an active claim for that.` (claims were loaded)
- `I can't answer that from the substrate.` (no claims loaded: empty
  or missing database)

### 9.5 `acknowledge`
- `Noted. That would be a proposal — it needs a human seal before I can use it.`

### 9.6 `social`
- Greeting: `Hello. What can I look up for you?`
- Farewell: `Goodbye.`

### 9.7 `trace`
- `My last reply used plan {plan}, template {template_name}, and cited {claim_ids}. The input parsed as intent {intent} with terms {terms}.`

## 10. Locked-slot contract

A slot is locked if it appears in braces `{name}` in a template.
Locked slots are:

- `subject`, `predicate`, `object`, `object1`, `object2` — claim text
- `claim_id`, `claim_id1`, `claim_id2` — cited IDs
- `plan`, `template_name`, `intent`, `terms`, `claim_ids` — trace fields

**Enforcement:**

1. Before rendering, the dialogue manager produces a `slots` dict.
2. The template is rendered by simple `str.replace("{name}", value)`
   for each slot.
3. Before emission, the rendered reply is checked: every slot's value
   appears verbatim in the rendered string. If any slot is missing,
   the reply is discarded and a fallback bare template is used.
4. In v0.1 there is no n-gram phrasing, so the check always passes.
   It exists so that v0.2 can rely on it.

## 11. Trace format (v0.1, console)

Printed to stdout after each reply. Plain text, key: value lines.

    --- trace ---
    input: <raw input>
    intent: <intent>
    terms: [<term1>, <term2>, ...]
    negation: <bool>
    plan: <plan>
    reason: <one-line reason>
    candidates:
      - claim_id=<id> score=<float> status=active subject=<s> object=<o> polarity=<p>
      - ...
    excluded:
      - claim_id=<id> reason=<polarity_missing|polarity_invalid|status_excluded|capsule_invalid|field_missing>
      - ...
    template: <template_name>
    slots:
      subject: <value>
      predicate: <value>
      object: <value>
      claim_id: <value>
    reply: <rendered reply>

Sections with no entries print `(none)`.

`excluded` lists the excluded claims that would otherwise have been
candidates for this input (subject or object match), so the trace says
why a relevant claim was not used without listing the whole substrate.
`field_missing` covers a missing `subject`, `object` or `created_at`.
(`signature_invalid` arrives with v0.2-B.)

## 12. P9 access

LLLM opens `forge.db` with SQLite URI `mode=ro`:

    sqlite3.connect(pathlib.Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)

(`Path.as_uri()` rather than an f-string, so a path containing a
space, `#` or `?`, or a Windows drive, still opens read-only; the same
form SCP Substrate and P9 v3 use.) The database path is `--db`, else
`$FORGE_HOME/forge.db`, else `~/.forge/forge.db` (the stack
convention).

If the file does not exist, the REPL starts with zero claims and every
question returns `unknown`. No exception is raised; no file is created.

LLLM cannot write to P9. This is enforced at the SQLite layer, not by
convention.

## 12a. Package names

The per-reply trace code lives in `traces/`, not `trace/`: a
top-level `trace` package would shadow Python's standard-library
`trace` module for anything run from the repository root.

## 13. v0.1 acceptance criteria

Every criterion is a test case in `test_lllm.py`. Freeze requires all
to pass.

- [x] Empty P9: every question returns `unknown`
- [x] A question matched by one active claim gets `answer`, citing its
      `claim_id`
- [x] Superseded and inactive claims are never used
- [x] A claim with polarity missing is never used, and the trace says
      why (`polarity_missing`)
- [x] Two competing claims within δ that disagree get `clarify`
- [x] Two competing claims within δ that agree get `answer`, citing
      both
- [x] A self-query with no `agent://lllm` claims gets `unknown`
- [x] A self-query once `agent://lllm` claims are seeded gets
      `explain_self`, with citations
- [x] A `trace_query` right after an `answer` returns the trace of that
      answer
- [x] A `trace_query` before any reply returns `unknown`
- [x] A statement gets the fixed `acknowledge` reply, and P9 is
      unchanged (verified by file hash)
- [x] Greetings, thanks and farewells get `social`
- [x] Every reply prints a full trace: parse, candidates, plan and
      reason, template, slots
- [x] No imports outside the standard library and P9
- [ ] All tests pass in Termux

---

## Document control

- SPEC v0.1.0 signed off by James, 2026-11-13 ("fix documentation and
  sign off and build v1"), after the pre-sign-off corrections marked
  above (§5.4, §5.7, §6, §7, §8, §9.1, §9.4, §11, §12, §12a). Frozen
  from here.
- Changes require a new SPEC version. SPEC v0.2.0 describes v0.2.
- Implementation of `lllm.py` v0.1.0 must match this spec.
