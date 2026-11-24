"""The engine: one pipeline behind every entry point.

    identity -> country -> safety rail -> commands -> Scam Shield -> retrieval -> compose -> reply

Every stage is small, replaceable and tested on its own. The order is the
design: nothing can delay or override an emergency, and nothing reaches a
person unless it is grounded in a checked fact or is a fixed system message.

One engine serves every covered country at once. The caller's dialling code
picks the country, so packs, emergency numbers and the default language are
always the ones for that caller.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .commands import LANGUAGE_COMMANDS, Command, parse_command, say
from .context.packs import ContextPack, load_packs
from .context.schema import Contact, ContextFact, ReviewStatus
from .context.store import ContextQuery, ContextStore, ScoredFact
from .countries import COUNTRIES, country_for_msisdn, default_language
from .identity import Profile, ProfileStore, normalize_msisdn
from .models import Channel, Citation, Message, Reply, ReplyKind
from .router import Budget, ExtractiveComposer, GroundedGenerator
from .safety import (
    CALL_WORD,
    EscalationPolicy,
    HandoffSink,
    InMemoryHandoffs,
    contacts_for,
    emergency_text,
    format_numbers,
)
from .scam import GENERIC_REPORT_LINE, HEADLINES, NEUTRAL_ADVICE, REPORT_LINE, SIGNS_LABEL, ScamReport, Verdict, analyse
from .text import SUPPORTED_LANGUAGES, guess_language, terms, truncate_words, wants_action
from .tips import Tip, TipQueue

CHANNEL_BUDGETS: dict[Channel, Budget] = {
    Channel.USSD: Budget(max_chars=150, short=True, max_facts=1),
    Channel.SMS: Budget(max_chars=450, short=True, max_facts=3),     # three GSM-7 segments
    Channel.VOICE: Budget(max_chars=320, short=True, max_facts=2),
    Channel.RADIO: Budget(max_chars=320, short=True, max_facts=2),
    Channel.WHATSAPP: Budget(max_chars=1200, short=False, max_facts=3),
    Channel.APP: Budget(max_chars=1500, short=False, max_facts=4),
    Channel.API: Budget(max_chars=1500, short=False, max_facts=4),
    Channel.AGENT: Budget(max_chars=1500, short=False, max_facts=4),
}


@dataclass
class EngineConfig:
    country: str | None = None      # None: detect from each caller's number; set it to pin one country
    default_language: str = "en"    # used when the country is unknown
    min_review: ReviewStatus = ReviewStatus.SOURCED
    include_verified: bool = False  # True only when this deployment holds a verified tier license
    budgets: dict[Channel, Budget] = field(default_factory=lambda: dict(CHANNEL_BUDGETS))


class Engine:
    def __init__(self, store: ContextStore, packs: list[ContextPack] | None = None,
                 profiles: ProfileStore | None = None,
                 composer: ExtractiveComposer | GroundedGenerator | None = None,
                 safety: EscalationPolicy | None = None, handoffs: HandoffSink | None = None,
                 tips: TipQueue | None = None, config: EngineConfig | None = None) -> None:
        self.store = store
        self.packs = sorted(packs or [], key=lambda p: (p.order, p.id))
        self.profiles = profiles or ProfileStore()
        self.composer = composer or ExtractiveComposer()
        self.safety = safety or EscalationPolicy()
        self.handoffs = handoffs or InMemoryHandoffs()
        self.tips = tips or TipQueue()
        self.config = config or EngineConfig()

    @classmethod
    def from_packs(cls, *paths: str | Path, **kwargs) -> Engine:
        packs = load_packs(*paths)
        store = ContextStore()
        for pack in packs:
            store.extend(pack.facts)
        return cls(store, packs=packs, **kwargs)

    # ------------------------------------------------------------------ country and language

    def country_for(self, phone: str) -> str | None:
        """The pinned country, or the covered country of a caller's number."""
        if self.config.country:
            return self.config.country.upper()
        try:
            found = country_for_msisdn(normalize_msisdn(phone, self.profiles.default_country_code))
        except ValueError:
            return None
        return found.code if found else None

    def language_for(self, phone: str, text: str = "", explicit: str | None = None) -> str:
        profile = self.profiles.peek(phone)
        if explicit:
            return explicit
        if profile and profile.language:
            return profile.language
        country = self.country_for(phone)
        fallback = default_language(country, self.config.default_language)
        return guess_language(text, fallback) if text else fallback

    def packs_for(self, country: str | None) -> list[ContextPack]:
        """Packs that hold at least one fact for the country (all packs when the country is unknown)."""
        if not country:
            return list(self.packs)
        return [p for p in self.packs
                if any(not f.scope.countries or country in f.scope.countries for f in p.facts)]

    # ------------------------------------------------------------------ pipeline

    def handle(self, message: Message, budget: Budget | None = None) -> Reply:
        budget = budget or self.config.budgets.get(message.channel, CHANNEL_BUDGETS[Channel.API])
        text = " ".join(message.text.split())
        lang = self.language_for(message.sender, text, message.language)
        profile = self.profiles.record_inbound(message)
        country = self.country_for(message.sender)

        reply = (self._safety(text, lang, profile, message, country)
                 or self._command(text, lang, profile, message, budget, country)
                 or self._scam_auto(text, lang, message, budget, country)
                 or self._answer(text, lang, profile, message, budget, country))
        if reply.kind is not ReplyKind.EMERGENCY and len(reply.text) > budget.max_chars:
            reply.text = truncate_words(reply.text, budget.max_chars)  # last line of defence
        self.profiles.record_reply(profile, message.channel, reply.text)
        return reply

    def ask(self, text: str, sender: str = "+254700000000", channel: Channel = Channel.API,
            language: str | None = None) -> Reply:
        """Convenience for scripts, notebooks and tests."""
        return self.handle(Message(channel=channel, sender=sender, text=text, language=language))

    # ------------------------------------------------------------------ stages

    def _safety(self, text: str, lang: str, profile: Profile, message: Message,
                country: str | None) -> Reply | None:
        decision = self.safety.check(text)
        if not decision.escalate or decision.queue is None:
            return None
        facts = self._contact_facts(country)
        contacts = contacts_for(decision.queue, facts, country)
        numbers = {c.number for c in contacts}
        cited = [f for f in facts if f.topic == "emergency_contacts"
                 and any(c.number in numbers and decision.queue in c.queues for c in f.contacts)]
        self.handoffs.raise_handoff(decision.queue, profile.key, text, message.channel.value)
        return Reply(
            text=emergency_text(decision.queue, contacts, lang), kind=ReplyKind.EMERGENCY, language=lang,
            escalated=True, escalation_queue=decision.queue, citations=_cite(cited),
        )

    def _command(self, text: str, lang: str, profile: Profile, message: Message,
                 budget: Budget, country: str | None) -> Reply | None:
        cmd = parse_command(text)
        if cmd is None:
            if not terms(text):  # a greeting or an empty message
                return self._help(lang, budget)
            return None
        return self.run_command(cmd, lang, profile, message, budget, country)

    def _help(self, lang: str, budget: Budget) -> Reply:
        return self._system(say("help" if budget.max_chars >= 250 else "help_short", lang), lang)

    def run_command(self, cmd: Command, lang: str, profile: Profile, message: Message,
                    budget: Budget, country: str | None = None) -> Reply:
        if cmd.name == "help":
            return self._help(lang, budget)
        if cmd.name == "forget":
            self.tips.forget(profile.key)
            self.profiles.forget(message.sender)
            return self._system(say("forgotten", lang), lang, end=True)
        if cmd.name == "stop":
            profile.opted_out = True
            return self._system(say("stopped", lang), lang, end=True)
        if cmd.name in LANGUAGE_COMMANDS:
            profile.language = LANGUAGE_COMMANDS[cmd.name]
            return self._system(say(cmd.name, profile.language), profile.language)
        if cmd.name == "language":
            return self._system(say("language", lang), lang)
        if cmd.name == "tip":
            if not cmd.arg:
                return self._system(say("tip_usage", lang), lang)
            self.tips.submit(Tip(profile.key, cmd.arg, message.channel.value, lang))
            return self._system(say("tip_thanks", lang), lang)
        if cmd.name == "scam":
            if not cmd.arg:
                return self._system(say("scam_usage", lang), lang)
            return self.scam_reply(analyse(cmd.arg, message.raw.get("forwarded_from")), lang, budget, country)
        if cmd.name == "sources":
            facts = [f for f in (self.store.get(i) for i in profile.last_fact_ids) if f]
            if not facts:
                return self._system(say("no_sources", lang), lang)
            body = "; ".join(f"{f.source} ({f.source_url})" if f.source_url and not budget.short
                             else f.source for f in facts)
            return Reply(truncate_words(body, budget.max_chars), ReplyKind.SYSTEM, lang, _cite(facts))
        if cmd.name == "more":
            if not profile.last_query:
                return self._system(say("no_sources", lang), lang)
            return self._answer(profile.last_query, lang, profile, message, budget, country,
                                exclude=set(profile.last_fact_ids))
        return self._help(lang, budget)

    def _scam_auto(self, text: str, lang: str, message: Message, budget: Budget,
                   country: str | None) -> Reply | None:
        report = analyse(text, message.raw.get("forwarded_from"))
        if report.verdict is Verdict.LIKELY_SCAM:
            return self.scam_reply(report, lang, budget, country)
        return None

    def _answer(self, text: str, lang: str, profile: Profile, message: Message, budget: Budget,
                country: str | None, exclude: set[str] | None = None) -> Reply:
        exclude = exclude or set()
        topic = profile.last_topic if exclude else None
        query = ContextQuery(
            text=None if exclude else text, vertical=topic[0] if topic else None,
            topic=topic[1] if topic else None, prefer_kind="action" if wants_action(text) else None,
            location=message.location or profile.last_location, country=country,
            month=message.received_at.month if isinstance(message.received_at, datetime) else None,
            language=lang, min_review=self.config.min_review,
            include_verified=self.config.include_verified, limit=budget.max_facts + len(exclude) + 4,
        )
        scored = [s for s in self.store.query(query) if s.fact.id not in exclude]
        if not scored:
            if exclude:
                return self._system(say("no_more", lang), lang)
            return self._clarify(lang, country)
        results = coherent(scored)

        human_line = ""
        contacts: list[Contact] = []
        critical = [f for f in results[: budget.max_facts] if f.safety_critical]
        if critical:
            contacts = self.contacts_for_facts(critical, country)
            if contacts:
                human_line = format_numbers(contacts, lang)
        room = Budget(budget.max_chars - (len(human_line) + 1 if human_line else 0), budget.short,
                      budget.max_facts)
        if isinstance(self.composer, GroundedGenerator):
            composed = self.composer.compose(results, lang, room, question=text)
        else:
            composed = self.composer.compose(results, lang, room)
        if human_line:  # do not repeat numbers the answer already gives
            remaining = [c for c in contacts if c.number not in composed.text]
            human_line = format_numbers(remaining, lang) if remaining else ""
        body = f"{composed.text} {human_line}".strip()

        if not exclude:
            profile.last_query = text
        profile.last_fact_ids = list(exclude | {f.id for f in composed.used})
        if composed.used:
            profile.last_topic = (composed.used[0].vertical, composed.used[0].topic)
        return Reply(body, ReplyKind.ANSWER, composed.language, _cite(composed.used))

    # ------------------------------------------------------------------ helpers

    def contacts_for_facts(self, facts: list[ContextFact], country: str | None) -> list[Contact]:
        """Numbers to show with safety critical facts: the fact's own lines when they belong to the
        caller's country, plus the caller's national lines for the fact's refer_queue."""
        out: list[Contact] = []
        for f in facts:
            if not f.scope.countries or not country or f.scope.countries == (country,):
                out.extend(f.contacts)
            if f.refer_queue:
                out.extend(contacts_for(f.refer_queue, self._contact_facts(country), country))
        return self._canonical(out, country)

    def scam_reply(self, report: ScamReport, lang: str, budget: Budget, country: str | None = None) -> Reply:
        lang = lang if lang in SUPPORTED_LANGUAGES else "en"
        facts = [f for f in (self.fact_by_suffix(s, country) for s in report.fact_ids) if f]
        report_fact = self.fact_by_suffix("report-333", country)
        pieces = [HEADLINES[report.verdict][lang]]
        if report.signals:
            shown = report.signals if budget.max_chars >= 250 else report.signals[:1]
            pieces.append(f"{SIGNS_LABEL[lang]} {'; '.join(s.explain[lang] for s in shown)}.")
            pieces.append(REPORT_LINE[lang] if report_fact else GENERIC_REPORT_LINE[lang])
            for f in facts:
                if f.topic == "fraud" and not f.contacts:
                    pieces.append(f.render(lang, short=True)[0])
        else:
            pieces.append(NEUTRAL_ADVICE[lang])
        text = pieces[0]
        for piece in pieces[1:]:  # add what fits; skip a piece that does not, keep trying smaller ones
            if len(f"{text} {piece}") <= budget.max_chars:
                text = f"{text} {piece}"
        cited = facts + ([report_fact] if report_fact and report_fact not in facts and report.signals else [])
        return Reply(truncate_words(text, budget.max_chars), ReplyKind.SCAM, lang, _cite(cited),
                     actions=[{"type": "scam_verdict", "verdict": report.verdict.value, "score": report.score,
                               "signals": [s.id for s in report.signals]}])

    def fact_by_suffix(self, suffix: str, country: str | None = None) -> ContextFact | None:
        """A fact by its id within any pack that applies to the country. Operator specific guidance
        is never shown to a caller in another country."""
        country = (country or self.config.country or "").upper()
        matches = [f for f in self.store if f.id.endswith("/" + suffix)
                   and (not country or not f.scope.countries or country in f.scope.countries)]
        matches.sort(key=lambda f: f.id)
        return matches[0] if matches else None

    def browse(self, pack_id: str, index: int, lang: str, budget: Budget,
               country: str | None = None) -> tuple[str, bool]:
        """One fact of a pack, for menu browsing. Returns (text, has_more)."""
        pack = next((p for p in self.packs if p.id == pack_id), None)
        if pack is None:
            return "", False
        facts = [f for f in pack.facts if self.store.allowed(f, ContextQuery(
            country=country, min_review=self.config.min_review,
            include_verified=self.config.include_verified))]
        if index >= len(facts):
            return "", False
        fact = facts[index]
        text = fact.render(lang, short=budget.short)[0]
        if fact.safety_critical:
            missing = [c.number for c in self.contacts_for_facts([fact], country) if c.number not in text]
            if missing:
                call = f"{CALL_WORD.get(lang, CALL_WORD['en'])} {', '.join(dict.fromkeys(missing))}."
                text = f"{truncate_words(text, budget.max_chars - len(call) - 1)} {call}"
        return truncate_words(text, budget.max_chars), index + 1 < len(facts)

    def _contact_facts(self, country: str | None = None) -> list[ContextFact]:
        """Facts that publish phone lines for the country. Emergency contact facts come first."""
        facts = [f for f in self.store if f.contacts
                 and (not country or not f.scope.countries or country in f.scope.countries)]
        return sorted(facts, key=lambda f: (0 if f.topic == "emergency_contacts" else 1, f.id))

    def _canonical(self, contacts: list[Contact], country: str | None = None) -> list[Contact]:
        """Deduplicate by number, using the emergency pack's version of each line when it exists."""
        canonical: dict[str, Contact] = {}
        for f in self._contact_facts(country):
            if f.topic == "emergency_contacts":
                for c in f.contacts:
                    canonical.setdefault(c.number, c)
        out: dict[str, Contact] = {}
        for c in contacts:
            out.setdefault(c.number, canonical.get(c.number, c))
        return list(out.values())

    def topic_labels(self, lang: str, country: str | None = None, limit: int = 5) -> list[str]:
        return [p.label(lang) for p in self.packs_for(country)[:limit]]

    def _clarify(self, lang: str, country: str | None = None) -> Reply:
        topics = ", ".join(self.topic_labels(lang, country)) or "help"
        return Reply(say("clarify", lang, topics=topics), ReplyKind.CLARIFY, lang)

    @staticmethod
    def _system(text: str, lang: str, end: bool = False) -> Reply:
        return Reply(text, ReplyKind.SYSTEM, lang, end_session=end)

    @staticmethod
    def covered_countries() -> list[str]:
        return list(COUNTRIES)


def coherent(scored: list[ScoredFact], keep_ratio: float = 0.75) -> list[ContextFact]:
    """Keep the answer on one topic: facts from the top fact's topic, plus any other
    fact that is nearly as relevant as the top one."""
    top = scored[0]
    best = max(s.relevance for s in scored) or 1.0
    out = []
    for s in scored:
        same = (s.fact.vertical, s.fact.topic) == (top.fact.vertical, top.fact.topic)
        if same or s.relevance >= keep_ratio * best:
            out.append(s.fact)
    return out


def _cite(facts: list[ContextFact]) -> list[Citation]:
    seen: dict[str, Citation] = {}
    for f in facts:
        seen.setdefault(f.id, Citation(f.id, f.source, f.review_status.value, f.source_url))
    return list(seen.values())
