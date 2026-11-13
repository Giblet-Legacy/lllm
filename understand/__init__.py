"""
understand — LLLM layer 1: input to meaning

Function:
    Turns raw input into a structured parse: intent, terms, entities,
    negation and the raw text (SPEC §5, §6 "Terms"). Rule-based and
    deterministic: regex patterns per intent, chosen by the locked
    precedence (SPEC 0.1.1) trace_query > self_query > clarify >
    question > statement > greeting > farewell.

Public API:
    1. tokenise(text) -> list[str]
    2. parse(text) -> dict

Internal helpers:
    3. _matches(intent, text) -> bool
    4. _is_question(text, terms) -> bool

Tier:     Tier 1 — Consumer (LLLM), layer 1
Depends:  standard library only
Spec:     SPEC.md 0.1.1 §5, §6
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import re

PRECEDENCE = ("trace_query", "self_query", "clarify", "question", "statement", "greeting", "farewell")  # SPEC 0.1.1

PATTERNS = {
    "trace_query": [r"how (did|do) you (work|know|figure) (that|this|it) out", r"why did you (say|answer|reply)",
                    r"where did (that|this|it) come from", r"what (was|were) your (reasoning|trace)",
                    r"show (me )?your (trace|reasoning)"],
    "self_query": [r"who are you", r"what are you", r"what can you do", r"how (do|does) (you|lllm) work",
                   r"tell me about (yourself|lllm)"],
    "clarify": [r"^what do you mean", r"^can you (clarify|explain)", r"^i don'?t understand", r"^which one\b\W*$"],
    "greeting": [r"^(hi|hello|hey|hiya|good (morning|afternoon|evening))\b", r"^(greetings|howdy)\b"],
    "farewell": [r"^(bye|goodbye|see you|good ?night|cheers)\b", r"^(thanks|thank you|cheers)\b"],
}
QUESTION_STARTS = {"who", "what", "where", "when", "why", "how", "which", "is", "are", "was", "were",
                   "do", "does", "did", "can", "could", "will", "would", "should"}
NEGATIONS = {"not", "no", "never"}
STOPWORDS = {"a", "an", "the", "is", "are", "was", "were", "do", "does", "did", "of", "to", "in", "on", "it"}

_TOKEN = re.compile(r"[a-z0-9][a-z0-9'’:/.\-]*")


# ---------------------------------------------------------------------------
# 1. tokenise
#    Lower-cased word tokens; trailing punctuation stripped (SPEC §6).
# ---------------------------------------------------------------------------
def tokenise(text):
    out = []
    for tok in _TOKEN.findall((text or "").lower()):
        tok = tok.rstrip(".:/-'’")
        if tok:
            out.append(tok)
    return out


# ---------------------------------------------------------------------------
# 3. _matches
# ---------------------------------------------------------------------------
def _matches(intent, text):
    return any(re.search(p, text) for p in PATTERNS[intent])


# ---------------------------------------------------------------------------
# 4. _is_question
#    SPEC §5.3: ends in "?", or starts with a WH-word or auxiliary.
# ---------------------------------------------------------------------------
def _is_question(text, terms):
    return text.rstrip().endswith("?") or (bool(terms) and terms[0] in QUESTION_STARTS)


# ---------------------------------------------------------------------------
# 2. parse
#    The highest-precedence intent that fires; default `question`.
#    `statement` fires only if no clarify / greeting / farewell pattern
#    matches (SPEC §5.4 implementation rule).
# ---------------------------------------------------------------------------
def parse(text):
    raw = text or ""
    low = raw.strip().lower()
    terms = tokenise(low)
    social_or_clarify = any(_matches(i, low) for i in ("clarify", "greeting", "farewell"))
    fired = {
        "trace_query": _matches("trace_query", low),
        "self_query": _matches("self_query", low),
        "question": _is_question(low, terms),
        "statement": bool(terms) and not _is_question(low, terms) and not social_or_clarify,
        "clarify": _matches("clarify", low),
        "greeting": _matches("greeting", low),
        "farewell": _matches("farewell", low),
    }
    intent = next((i for i in PRECEDENCE if fired[i]), "question")
    return {
        "raw": raw,
        "intent": intent,
        "terms": terms,
        "entities": [t for t in terms if t not in STOPWORDS and t not in NEGATIONS],
        "negation": any(t in NEGATIONS or t.endswith("n't") or t.endswith("n’t") for t in terms),
    }
