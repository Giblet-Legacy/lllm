# Forge Stack Context — LLLM

CLAUDE.md — Context briefing for AI assistants working in this repository.

## What this repo is
Tier 1 Consumer. LLLM is the conversational voice of The Legacy. It
takes natural language input, parses intent, reads active claims from
P9 (substrate-layer), decides a response plan, and replies. Every
reply is traceable. It never invents facts.

## The Immutable Rule
Never rewrite a primitive. Add a layer. LLLM consumes P9 (and later
P13, P14, P15, P4, P1, P2). It does not rewrite them.

## Dependencies by version
- v0.1: P9 only.
- v0.2: + P14 (λ ranking) and P1/P2 (signature verification).
- v0.3: + P13, P15, P4.
- v0.5: signed traces (P1, P2, P4).

A v0.1 build imports nothing outside the standard library and P9.

## Architectural commitments (locked)
- Polarity is required. A claim with no `capsule.polarity` is excluded
  from answers, and the trace records `polarity_missing`.
- v0.1 trusts P9 (no signature verification). Verification arrives at
  v0.2. Recorded as a Known Limitation.
- `trace_query` is a first-class intent, distinct from `self_query`.
  "How did you work that out?" answers from the current turn's trace.
- Intent precedence: trace_query > self_query > question > statement >
  clarify > greeting > farewell.
- v0.4 conversation state is in-session only. Persistence arrives at
  v0.5 with signed traces.

## Design principles
1. Truth from claims, fluency from counts. Locked slots enforce it.
2. Nothing unvalidated is spoken as fact.
3. Everything is inspectable. Untraceable reply = bug.
4. Stdlib-first, Termux baseline.
5. "I don't know" is a first-class reply.

## Dual-Device Workflow
S24/Termux and laptop/VS Code. State confirmed, never assumed. LF-only.
British English (-ise, artefact). Good/Bad/Ugly CHANGELOG, latest at top.
Header discipline on every file and function.
