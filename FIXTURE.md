# FIXTURE — lllm (Tier 1: LLLM), v0.1.0

FIXTURE.md — the fixture P9 and its expected outcomes, as a contract.

Function:
    ROADMAP Phase 1 asks for a fixture manifest: "a documented list of
    test queries and their expected outcomes. The fixture is a
    contract, not just data." `fixture_p9.py` builds the database;
    this table says what LLLM must do with it. `test_lllm.py` reads the
    table below and checks every row against reality, so the manifest
    cannot drift from the code.

## Claims in the fixture

| Name | subject · predicate · object | polarity | State |
|---|---|---|---|
| sky | sky · is · blue | affirm | active |
| sea | sea · is · blue | affirm | active |
| grass_old | grass · is · green | affirm | superseded by grass_new |
| grass_new | grass · is · brown | affirm | active |
| moon | moon · is · cheese | affirm | inactive (withdrawn, no replacement) |
| sun | sun · is · hot | (missing) | active |
| fire | fire · is · cold | `maybe` (invalid) | active |
| door_open | door · is · open | affirm | active |
| door_shut | door · is · shut | affirm | active |
| tide_a, tide_b | tide · is · late | affirm | active (agree: differ only in `note`) |
| cat | cat · is · dog | negate | active |
| earth | earth · orbits · star | affirm | active |
| broken | (capsule is not JSON) | — | active |

No `agent://lllm` claims: the self-model is not bootstrapped.

## Expected outcomes

`cites` lists the fixture names cited, in order (`-` for none).
`excluded` lists the relevant exclusions the trace must report.

<!-- manifest:start -->
| query | intent | plan | template | cites | excluded |
|---|---|---|---|---|---|
| is the sky blue? | question | answer | answer_yes | sky | - |
| is the sky green? | question | answer | answer_state | sky | grass_old:status_excluded |
| is the cat a dog? | question | answer | answer_no | cat | - |
| does the earth orbit the star? | question | answer | answer_yes | earth | - |
| is the grass green? | question | answer | answer_state | grass_new | grass_old:status_excluded |
| is the moon cheese? | question | unknown | unknown_loaded | - | moon:status_excluded |
| is the sun hot? | question | unknown | unknown_loaded | - | sun:polarity_missing |
| is the fire cold? | question | unknown | unknown_loaded | - | fire:polarity_invalid |
| what is the door? | question | clarify | clarify | door_shut,door_open | - |
| is the tide late? | question | answer | answer_yes | tide_b,tide_a | - |
| what is a volcano? | question | unknown | unknown_loaded | - | - |
| what is blue? | question | answer | answer_state | sea | - |
| who are you? | self_query | unknown | unknown_loaded | - | - |
| the river is wide | statement | acknowledge | acknowledge | - | - |
| hello | greeting | social | social_greeting | - | - |
| thanks | farewell | social | social_farewell | - | - |
| cheers | farewell | social | social_farewell | - | - |
| what do you mean? | clarify | unknown | unknown_loaded | - | - |
<!-- manifest:end -->

Notes on the rows:
- "is the sky green?": the question does not name the claim's object,
  so the reply states what is known ("sky is blue.") and never says
  "Yes." (SPEC §9.1). The trace also reports grass_old: "green" is its
  object, so it would have matched, but it is superseded.
- "what is the door?": door_open and door_shut score equally and
  disagree on object, so `clarify` fires. Equal scores cite the more
  recent claim first.
- "is the tide late?": two claims agree, so `answer` cites both.
- "what is blue?": sky and sea score equally but have different
  subjects, so neither clarify nor cite-both applies (SPEC_V0_1_1 §2):
  the most recent answers alone, and a WH-question never gets "Yes."
  (SPEC_V0_1_1 §3).
- "what do you mean?": a `clarify` intent (SPEC_V0_1_1 §1). In a fresh
  session there is no previous reply to explain, so the plan is
  `unknown`. (Under SPEC 0.1.0 it parsed as a question; NOTES Q9.)
