"""Heuristic write-decision (salience) classifier for evaluation.

The production write decision is made by the LLM at write time per the
selective-write policy (write decisions/corrections/novel-facts/session
boundaries; decline mechanical/transient/acknowledgement excerpts). There is
no coded classifier in the live path, so the salience eval previously had
nothing to measure between its all-write baseline and the perfect oracle.

This module provides a deterministic, policy-grounded heuristic so the eval can
report a *measured* point. It is a coded proxy — NOT the LLM — and exists to
give salience quality a number that can be tracked and improved. Cues are drawn
from the documented policy, not reverse-engineered from specific fixtures.
"""

# Decline cues — mechanical, transient, or acknowledgement signals (checked first).
_DECLINE_CUES = (
    "running ", "passed in", "pytest", "failed in",
    "staged ", "committed", "pushed to", "git ",
    "let me ", "i will use", "i'll ", "i can help", "sure,", "yes,",
    "looks correct", "that looks correct",
    "do you want", "should i ", "would you like",
    "as we discussed", "as discussed", "earlier",
    "no errors", "no module named", "error message:", "looking at the error",
)

# Write cues — decisions, corrections, discoveries, durable facts, boundaries.
_WRITE_CUES = (
    "decid", "chose", "chosen", "we will use", "agreed",
    "corrected", "correction",
    "discover", "found that", "turns out", "realized", "realised",
    "confirm",
    "requires", "must ", "because",
    "session opened", "session checkpoint", "session complete", "checkpoint",
    "wants", "prefers", "rejected",
    "uses a ", "convention", "structure",
)


def classify_salience(excerpt: str) -> str:
    """Classify a session excerpt as 'write' or 'decline'.

    Decline cues are checked first (conservative default: decline), then write
    cues. An excerpt matching no cue defaults to 'decline'.
    """
    text = (excerpt or "").lower()
    for cue in _DECLINE_CUES:
        if cue in text:
            return "decline"
    for cue in _WRITE_CUES:
        if cue in text:
            return "write"
    return "decline"
