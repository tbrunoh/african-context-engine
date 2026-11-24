"""Safety rail: decide when a conversation must go to a human expert.

The default trigger list is a STARTER LIST for development only. Every
deployment must replace it with terms reviewed by clinicians and domain
experts for each language it serves. Keyword matching is a floor, not a
ceiling: production deployments should add a classifier and route every
safety critical fact through the same escalation path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_TRIGGERS: dict[str, tuple[str, ...]] = {
    "health_urgent": (
        # English
        "bleeding", "convulsion", "seizure", "unconscious", "not breathing",
        "difficulty breathing", "chest pain", "severe headache", "baby not moving",
        # Swahili (requires native speaker and clinical review before use)
        "kutokwa na damu", "degedege", "kupoteza fahamu",
    ),
    "poisoning": ("swallowed pesticide", "drank pesticide", "poisoned", "sumu"),
}


@dataclass
class SafetyDecision:
    escalate: bool
    queue: str | None = None
    matched: list[str] = field(default_factory=list)


class EscalationPolicy:
    def __init__(self, triggers: dict[str, tuple[str, ...]] | None = None) -> None:
        self.triggers = triggers or DEFAULT_TRIGGERS
        self._patterns = {
            queue: [re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE) for t in terms]
            for queue, terms in self.triggers.items()
        }

    def check(self, text: str, safety_critical_context: bool = False) -> SafetyDecision:
        for queue, patterns in self._patterns.items():
            hits = [p.pattern for p in patterns if p.search(text)]
            if hits:
                return SafetyDecision(True, queue, [h.replace("\\b", "").replace("\\", "") for h in hits])
        if safety_critical_context:
            return SafetyDecision(False, "offer_human", [])
        return SafetyDecision(False)
