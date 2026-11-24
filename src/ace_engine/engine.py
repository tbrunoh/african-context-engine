"""The engine: one pipeline behind every entry point.

identity -> safety -> intent -> context -> grounded generation -> reply -> memory
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from .context.store import ContextQuery, ContextStore
from .identity import Profile, ProfileStore
from .models import Citation, Message, Reply
from .router import Router, build_prompt
from .safety import EscalationPolicy

HANDOFF_TEXT = ("This sounds urgent. I am connecting you to a human expert now. "
                "If you can, go to the nearest health facility or call your local emergency number.")
CLARIFY_TEXT = ("I do not have verified local guidance for that yet. Tell me if it is about crops, "
                "animals, health, prices or land, or I can connect you to a human expert.")


@dataclass
class Intent:
    vertical: str | None = None
    topic: str | None = None
    subject: str | None = None


class IntentClassifier(Protocol):
    def classify(self, text: str, profile: Profile) -> Intent: ...


@dataclass
class KeywordClassifier:
    """A transparent baseline. Swap for a model based classifier in production."""

    rules: dict[str, Intent] = field(default_factory=dict)

    def classify(self, text: str, profile: Profile) -> Intent:
        lowered = text.lower()
        for keyword, intent in self.rules.items():
            if keyword in lowered:
                return intent
        # carry the last known intent across channels, so a photo on WhatsApp
        # continues the voice call it followed
        last = profile.last_intent
        return last if isinstance(last, Intent) else Intent()


@dataclass
class EngineConfig:
    country: str | None = None
    include_verified: bool = False  # set True only when this deployment holds a verified tier license
    max_facts: int = 3


class Engine:
    def __init__(self, store: ContextStore, profiles: ProfileStore | None = None,
                 router: Router | None = None, safety: EscalationPolicy | None = None,
                 classifier: IntentClassifier | None = None, config: EngineConfig | None = None) -> None:
        self.store = store
        self.profiles = profiles or ProfileStore()
        self.router = router or Router()
        self.safety = safety or EscalationPolicy()
        self.classifier = classifier or KeywordClassifier()
        self.config = config or EngineConfig()

    def handle(self, message: Message) -> Reply:
        profile = self.profiles.record_inbound(message)

        decision = self.safety.check(message.text)
        if decision.escalate:
            reply = Reply(text=HANDOFF_TEXT, escalated=True, escalation_queue=decision.queue)
            self.profiles.record_reply(profile, message.channel, reply.text)
            return reply

        intent = self.classifier.classify(message.text, profile)
        if not (intent.vertical or intent.topic or intent.subject):
            # Never retrieve on an unknown intent: unfiltered facts would be off topic.
            reply = Reply(text=CLARIFY_TEXT)
            self.profiles.record_reply(profile, message.channel, reply.text)
            return reply
        profile.last_intent = intent

        month = message.received_at.month if isinstance(message.received_at, datetime) else None
        query = ContextQuery(
            vertical=intent.vertical, topic=intent.topic, subject=intent.subject,
            location=message.location or profile.last_location, country=self.config.country,
            month=month, language=message.language or profile.preferred_language,
            include_verified=self.config.include_verified, limit=self.config.max_facts,
        )
        facts = [s.fact for s in self.store.query(query)]

        history = [f"{t.role} via {t.channel.value}: {t.text}" for t in profile.recent()[:-1]]
        grounded = build_prompt(message.text, facts, query.language, history)
        text = self.router.generate(grounded, query.language)

        offer_human = any(f.safety_critical for f in facts)
        if offer_human:
            text += " If anything gets worse, reply HELP to reach a human expert."

        reply = Reply(
            text=text,
            citations=[Citation(f.id, f.source, f.review_status.value) for f in facts],
        )
        self.profiles.record_reply(profile, message.channel, reply.text)
        return reply
