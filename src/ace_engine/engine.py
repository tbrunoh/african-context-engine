"""The engine: one pipeline behind every entry point.

    identity -> country -> safety rail -> commands -> Scam Shield -> V2 services -> retrieval -> compose -> reply

Every stage is small, replaceable and tested on its own. The order is the
design: nothing can delay or override an emergency, and nothing reaches a
person unless it is grounded in a checked fact or is a fixed system message.

One engine serves every covered country at once. The caller's dialling code
picks the country, so packs, emergency numbers and the default language are
always the ones for that caller.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

from . import encoding, i18n
from .commands import LANGUAGE_COMMANDS, Command, language_menu, parse_command, say
from .context.packs import ContextPack, load_packs
from .context.schema import Contact, ContextFact, ReviewStatus
from .context.store import ContextQuery, ContextStore, ScoredFact
from .countries import COUNTRIES, country_for_msisdn, default_language, readable
from .identity import WEB_PREFIX, Profile, ProfileStore, normalize_msisdn, web_country
from .langid import LanguageIdentifier, carries_language, confirmed_by, detect_language, unread_language
from .models import Channel, Citation, Message, Reply, ReplyKind
from .router import Budget, ExtractiveComposer, GroundedGenerator
from .safety import (
    OR_WORD,
    EscalationPolicy,
    HandoffSink,
    InMemoryHandoffs,
    alarm_language,
    call_line,
    contacts_for,
    emergency_text,
    format_numbers,
)
from .scam import GENERIC_REPORT_LINE, HEADLINES, NEUTRAL_ADVICE, REPORT_LINE, SIGNS_LABEL, ScamReport, Verdict, analyse
from .services import PLACE_SERVICES, ServiceHub, add_known_words, bare_name, detect, needs_named_place
from .snapshots import SnapshotStore, default_root
from .text import SUPPORTED_LANGUAGES, terms, tokens, truncate_words, wants_action
from .tips import Tip, TipQueue

CHANNEL_BUDGETS: dict[Channel, Budget] = {
    Channel.USSD: Budget(max_chars=150, short=True, max_facts=1),
    Channel.SMS: Budget(max_chars=450, short=True, max_facts=3),     # three GSM-7 segments
    Channel.RCS: Budget(max_chars=450, short=True, max_facts=3),     # fits SMS, so a fallback never cuts it
    Channel.VOICE: Budget(max_chars=320, short=True, max_facts=2),
    Channel.RADIO: Budget(max_chars=320, short=True, max_facts=2),
    Channel.WHATSAPP: Budget(max_chars=1200, short=False, max_facts=3),
    Channel.APP: Budget(max_chars=1500, short=False, max_facts=4),
    Channel.API: Budget(max_chars=1500, short=False, max_facts=4),
    Channel.AGENT: Budget(max_chars=1500, short=False, max_facts=4),
}


SAFETY_CONTEXT = {"pregnancy_companion": "pregnant"}
# Channels that never call a language model: USSD sessions time out in seconds and a call cannot pause for one.
EXTRACTIVE_ONLY = frozenset({Channel.USSD, Channel.VOICE})


@dataclass
class EngineConfig:
    country: str | None = None      # None: detect from each caller's number; set it to pin one country
    default_language: str = "en"    # used when the country is unknown
    min_review: ReviewStatus = ReviewStatus.SOURCED
    # TIP stores what a person types for expert review. A deployment with no reviewer, such as a public demo, switches
    # it off: TIP is then read as an ordinary message, and help and clarify replies do not offer it.
    tips: bool = True
    include_verified: bool = False  # True only when this deployment holds a verified tier license
    budgets: dict[Channel, Budget] = field(default_factory=lambda: dict(CHANNEL_BUDGETS))
    # Optional: a fuller language identifier that confirms a message is in a language ACE does not speak before ACE
    # says so (see ace_engine.langid). Without one, ACE's own character profiles decide.
    language_identifier: LanguageIdentifier | None = None


class Engine:
    def __init__(self, store: ContextStore, packs: list[ContextPack] | None = None,
                 profiles: ProfileStore | None = None,
                 composer: ExtractiveComposer | GroundedGenerator | None = None,
                 safety: EscalationPolicy | None = None, handoffs: HandoffSink | None = None,
                 tips: TipQueue | None = None, config: EngineConfig | None = None,
                 services: ServiceHub | None = None) -> None:
        self.store = store
        self.packs = sorted(packs or [], key=lambda p: (p.order, p.id))
        _PACK_LICENCE.update({f.id: p.license for p in self.packs for f in p.facts})
        pinned = COUNTRIES.get(((config.country if config else None) or "").upper())
        # Local numbers take the pinned country's code; with none pinned, a caller's country comes only from their number
        self.profiles = profiles if profiles is not None else ProfileStore(default_country_code=pinned.dial if pinned else None)
        self.composer = composer or ExtractiveComposer()
        self.safety = safety or EscalationPolicy()
        self.handoffs = handoffs if handoffs is not None else InMemoryHandoffs()
        self.tips = tips if tips is not None else TipQueue()
        self.config = config or EngineConfig()
        self.services = None
        if services is not None:
            self.use_services(services)

    def use_services(self, hub: ServiceHub) -> None:
        """Wire a service hub to this engine's packs and emergency numbers, then put it in use.

        Every way a hub reaches the engine goes through here, including a snapshot set swapped in while serving, so a
        service never answers without the pack facts and numbers it cites."""
        hub.ctx.store = self.store
        hub.ctx.numbers = self.numbers_for
        self.services = hub

    @classmethod
    def from_packs(cls, *paths: str | Path, snapshots: str | Path | SnapshotStore | None = "auto",
                   **kwargs) -> Engine:
        """Build an engine from packs. V2 services read snapshots from the given folder, or from the
        repository or installed copy when snapshots is "auto"; pass None to run with packs only (V1)."""
        packs = load_packs(*paths)
        store = ContextStore()
        for pack in packs:
            store.extend(pack.facts)
            # What people ask about is never a place ACE should ask after: armyworm, viwavijeshi, malaria
            add_known_words(w for f in pack.facts for w in (*f.keywords, *f.subjects, f.topic))
        if "services" not in kwargs and snapshots is not None:
            if isinstance(snapshots, SnapshotStore):
                snap_store = snapshots
            else:
                root = default_root() if snapshots == "auto" else Path(snapshots)
                snap_store = SnapshotStore(root) if root else None
            if snap_store is not None:
                kwargs["services"] = ServiceHub(snap_store)
        return cls(store, packs=packs, **kwargs)

    def numbers_for(self, queue: str, country: str | None) -> list[Contact]:
        """Verified numbers for a queue in one country, from the V1 emergency packs."""
        return contacts_for(queue, self._contact_facts(country), country) if country else []

    # ------------------------------------------------------------------ country and language

    def country_for(self, phone: str) -> str | None:
        """The pinned country, or the covered country of a caller's number."""
        if self.config.country:
            return self.config.country.upper()
        if phone.startswith(WEB_PREFIX):
            return web_country(phone)
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
        allowed = COUNTRIES[country].languages if country in COUNTRIES else None
        also = (readable(country) or ())[len(allowed or ()):]
        if not text:
            return fallback
        lang = detect_language(text, fallback, allowed, also, self._place_words(country))
        # An answer to ACE's own question, such as a county name, carries no language: keep the question's.
        if (profile and profile.pending_service and profile.pending_language
                and not carries_language(text, self._place_words(country))):
            return profile.pending_language
        return lang

    def packs_for(self, country: str | None) -> list[ContextPack]:
        """Packs that hold at least one fact for the country; with no known country, packs with a fact that applies
        everywhere, so a caller from outside ACE's countries never browses another country's lines."""
        return [p for p in self.packs
                if any(not f.scope.countries or (country and country in f.scope.countries) for f in p.facts)]

    # ------------------------------------------------------------------ pipeline

    def handle(self, message: Message, budget: Budget | None = None) -> Reply:
        budget = budget or self.config.budgets.get(message.channel, CHANNEL_BUDGETS[Channel.API])
        text = " ".join(message.text.split())
        lang = self.language_for(message.sender, text, message.language)
        budget = self._fit_alphabet(budget, message.channel, lang)
        profile = self.profiles.record_inbound(message)
        country = self.country_for(message.sender)

        reply = (self._safety(text, lang, profile, message, country)
                 or self._command(text, lang, profile, message, budget, country)
                 or self._scam_auto(text, lang, message, budget, country)
                 or self._unread(text, lang, profile, message, budget, country)
                 or self._service(text, lang, profile, message, budget, country)
                 or self._answer(text, lang, profile, message, budget, country))
        # Fold first: folding ŋ to ng or ɲ to ny lengthens the text, and the budget is for what is sent.
        reply.text = self._for_network(reply.text, message.channel, lang)
        if reply.kind is not ReplyKind.EMERGENCY and len(reply.text) > budget.max_chars:
            reply.text = truncate_words(reply.text, budget.max_chars)  # last line of defence
        self.profiles.record_reply(profile, message.channel, reply.text)
        self.profiles.save(profile)
        return reply

    @staticmethod
    def _fit_alphabet(budget: Budget, channel: Channel, lang: str) -> Budget:
        """Shrink SMS, RCS and USSD budgets for languages whose script needs UCS-2 (Arabic, Amharic)."""
        if budget.fitted:  # the USSD app sizes its budget from the screen limit, which already counts the alphabet
            return budget
        scaled = encoding.scale(budget.max_chars, channel.value, lang)
        return budget if scaled == budget.max_chars else replace(budget, max_chars=scaled)

    @staticmethod
    def _for_network(text: str, channel: Channel, lang: str) -> str:
        """Keep Latin script SMS and USSD replies in the GSM alphabet, so they keep their full length."""
        return encoding.gsm_fold(text) if channel in (Channel.SMS, Channel.USSD) else text

    def ask(self, text: str, sender: str | None = None, channel: Channel = Channel.API,
            language: str | None = None) -> Reply:
        """Convenience for scripts, notebooks and tests. Pass the caller's number, or pin a country in the
        config; with neither, ACE answers as for a caller outside its 34 countries."""
        if sender is None:
            pinned = COUNTRIES.get((self.config.country or "").upper())
            sender = f"+{pinned.dial}700000000" if pinned else "+888700000000"
        return self.handle(Message(channel=channel, sender=sender, text=text, language=language))

    # ------------------------------------------------------------------ stages

    def _safety(self, text: str, lang: str, profile: Profile, message: Message,
                country: str | None) -> Reply | None:
        decision = self.safety.check(text)
        if not decision.escalate or decision.queue is None:
            return None
        if not (message.language or profile.language):  # a chosen language is kept, in an emergency too
            lang = alarm_language(text, lang, readable(country))
        facts = self._contact_facts(country)
        contacts = contacts_for(decision.queue, facts, country)
        numbers = {c.number for c in contacts}
        cited = [f for f in facts if f.topic == "emergency_contacts"
                 and any(c.number in numbers for c in f.contacts)]
        _raise(self.handoffs, decision.queue, profile.key, text, message.channel.value, country)
        return Reply(
            text=emergency_text(decision.queue, contacts, lang), kind=ReplyKind.EMERGENCY, language=lang,
            escalated=True, escalation_queue=decision.queue, citations=_cite(cited),
        )

    def _command(self, text: str, lang: str, profile: Profile, message: Message,
                 budget: Budget, country: str | None) -> Reply | None:
        cmd = parse_command(text)
        if (cmd is not None and cmd.name in LANGUAGE_COMMANDS and profile.pending_service and self.services is not None
                and self.services.resolve_place(text, country) is not None):
            cmd = None  # Somali answering ACE's region question in Ethiopia is a place, not a language switch
        if cmd is not None and cmd.name == "tip" and not self.config.tips:
            cmd = None
        if cmd is None:
            # A greeting or an empty message gets the help text; a bare place name, such as Oyo, answering ACE's own
            # question goes on to that question, even when the name is also a common word.
            if not terms(text) and not (profile.pending_service and self.services is not None
                                        and self.services.resolve_place(text, country) is not None):
                return self._help(lang, budget)
            return None
        return self.run_command(cmd, lang, profile, message, budget, country)

    def _unread(self, text: str, lang: str, profile: Profile, message: Message, budget: Budget,
                country: str | None) -> Reply | None:
        """A message in a language ACE does not speak gets told so, in the caller's country language, with the
        languages ACE reads there and the country's emergency numbers, instead of an answer in a language its
        writer may not read.

        A person who chose a language, a message that says its language, and the answer to a question ACE just
        asked are always read."""
        if profile.language or message.language or profile.pending_service:
            return None
        offered = COUNTRIES[country].languages if country in COUNTRIES else None
        places = self._place_words(country)
        also = (readable(country) or ())[len(offered or ()):]
        if unread_language(text, offered, places, also) is None:
            return None
        if not confirmed_by(self.config.language_identifier, text, readable(country)):
            return None
        reply_lang = offered[0] if offered else self.config.default_language
        codes = list(offered or (reply_lang,))
        if len(codes) == 1 and "en" not in codes:
            codes.append("en")  # ACE reads English in every country, so a list of one is never all it offers
        names = [i18n.native_name(code) for code in codes]
        listing = _listing(names, reply_lang)
        # The lines the safety rail would give for an urgent health message, so a person in danger who writes in any
        # language still has a number to call; the country's emergency lines come first.
        urgent = contacts_for("health_urgent", self._contact_facts(country), country)[:3]
        numbers = format_numbers(urgent, reply_lang)
        base = self.config.budgets.get(message.channel, CHANNEL_BUDGETS[Channel.API]).max_chars
        coded = _listing([c.upper() for c in codes], reply_lang)
        # Names first; on a small screen the codes, which LANG understands; on the smallest, the codes alone, so the
        # languages ACE reads and the numbers to call always both reach the person.
        for unread in (say("unread", reply_lang, languages=listing), say("unread", reply_lang, languages=coded),
                       f"{coded}."):
            script_lang = reply_lang if encoding.is_gsm7(encoding.gsm_fold(f"{unread} {numbers}")) else "ar"
            room = encoding.scale(base, message.channel.value, script_lang) - len(numbers) - 1
            if len(unread) <= room:
                break
        return self._system(f"{truncate_words(unread, room)} {numbers}", reply_lang)

    def _place_words(self, country: str | None) -> frozenset[str]:
        """Folded words of the caller's country's place names, so a list of towns is not read as a language."""
        if not country or self.services is None:
            return frozenset()
        cache = self.__dict__.setdefault("_place_word_cache", {})
        if country not in cache:
            words: set[str] = set()
            for rec in self.services.places.areas(country):
                for name in [rec.get("name", ""), *rec.get("aliases", [])]:
                    words.update(t for t in tokens(name) if len(t) > 3)  # not de, du, le or of
            cache[country] = frozenset(words)
        return cache[country]

    def _help(self, lang: str, budget: Budget) -> Reply:
        full = budget.max_chars >= 250 and self.config.tips  # the full help offers TIP; the short one does not
        return self._system(say("help" if full else "help_short", lang), lang)

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
            menu = COUNTRIES[country].languages if country in COUNTRIES else None
            text = say("language", lang, menu)
            # On a small screen the list itself is the message: every code in it works with LANG.
            return self._system(text if len(text) <= budget.max_chars else language_menu(menu), lang)
        if cmd.name == "tip":
            if not cmd.arg:
                return self._system(say("tip_usage", lang), lang)
            self.tips.submit(Tip(profile.key, cmd.arg, message.channel.value, lang))
            return self._system(say("tip_thanks", lang), lang)
        if cmd.name == "scam":
            if not cmd.arg:
                return self._system(say("scam_usage", lang), lang)
            return self.scam_reply(analyse(cmd.arg, message.raw.get("forwarded_from")), lang, budget, country)
        if cmd.name in ("sources", "more") and not profile.last_fact_ids and profile.last_sources:
            # After a service answer there are no more facts to give: both name the data it came from
            body = "; ".join(src if not budget.short else src.split(" (http")[0] for src in profile.last_sources)
            return Reply(truncate_words(body, budget.max_chars), ReplyKind.SYSTEM, lang)
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

    def _service(self, text: str, lang: str, profile: Profile, message: Message, budget: Budget,
                 country: str | None) -> Reply | None:
        """V2 decision services: rain, warnings, facilities, prices, pregnancy checks and crop problems."""
        if self.services is None:
            return None
        sid = detect(text)
        pending = profile.pending_service
        asked = text
        if sid is None and pending:
            sid, asked = pending, f"{profile.pending_text} {text}".strip()
            if sid in PLACE_SERVICES and self.services.resolve_place(text, country, message.location) is None:
                name = None if profile.pending_asked else bare_name(text)
                if name:  # a short answer to ACE's own question that names no place ACE knows: say so, ask again once
                    profile.pending_asked = True
                    refusal = needs_named_place(sid, country, name)
                    return Reply(truncate_words(refusal.text.get(lang) or refusal.text["en"], budget.max_chars),
                                 ReplyKind.CLARIFY, lang, actions=[{"type": "service", "service": sid,
                                                                    "preview": True, "outcome": "needs_place",
                                                                    "data": refusal.data}])
                profile.pending_service, profile.pending_text, profile.pending_asked = None, "", False
                return None  # not a place: treat it as a new question
        if (sid is None and profile.last_service in PLACE_SERVICES
                and (self.services.follow_up_place(text, country) is not None
                     or self.services.follow_up_unknown(text))):
            sid = profile.last_service  # What about Nakuru? Et à Kolda ? A follow-up that names another place
        if sid is None:
            return None
        return self._service_reply(sid, asked, lang, profile, message, budget, country, pending=pending)

    def run_service(self, service_id: str, message: Message, budget: Budget | None = None,
                    params: dict | None = None) -> Reply:
        """Run one named V2 service, for menus and the API. The safety rail still runs first."""
        if self.services is None:
            raise RuntimeError("this engine has no snapshots, so V2 services are off")
        budget = budget or self.config.budgets.get(message.channel, CHANNEL_BUDGETS[Channel.API])
        text = " ".join(message.text.split())
        lang = self.language_for(message.sender, text, message.language)
        budget = self._fit_alphabet(budget, message.channel, lang)
        profile = self.profiles.record_inbound(message)
        country = self.country_for(message.sender)
        # A menu screen sets the context a message would otherwise carry: "bleeding" typed on the
        # pregnancy screen is a pregnancy emergency, so the safety rail sees it that way.
        context = SAFETY_CONTEXT.get(service_id, "")
        reply = (self._safety(f"{context} {text}".strip(), lang, profile, message, country)
                 or self._service_reply(service_id, text, lang, profile, message, budget, country,
                                        pending=service_id, params=params))
        reply.text = self._for_network(reply.text, message.channel, lang)
        if reply.kind is not ReplyKind.EMERGENCY and len(reply.text) > budget.max_chars:
            reply.text = truncate_words(reply.text, budget.max_chars)  # folding can lengthen a reply
        self.profiles.record_reply(profile, message.channel, reply.text)
        self.profiles.save(profile)
        return reply

    def _service_reply(self, sid: str, asked: str, lang: str, profile: Profile, message: Message, budget: Budget,
                       country: str | None, pending: str | None = None, params: dict | None = None) -> Reply:
        run = self.services.run(sid, asked, country, lang, budget.max_chars, location=message.location,
                                remembered=profile.last_place, params=params)
        result = run.result
        if run.place is not None:
            profile.last_place = (run.place.country, run.place.code)
        if not run.ok and result.reason in ("needs_place", "needs_crop", "needs_weeks") and pending != sid:
            profile.pending_service, profile.pending_text, profile.pending_language = sid, asked, lang
            profile.pending_asked = False
        else:
            profile.pending_service, profile.pending_text, profile.pending_asked = None, "", False
        if run.ok:
            profile.last_service = sid
            profile.last_fact_ids, profile.last_query = [], None
            profile.last_sources = [c.source + (f" ({c.source_url})" if c.source_url else "") for c in result.citations]
        action = {"type": "service", "service": sid, "preview": result.preview, "outcome":
                  "answer" if run.ok else result.reason, "data": result.data}
        if run.ok:
            action["data_date"] = result.data_date
            action["confidence"] = result.confidence
        kind = ReplyKind.ANSWER if run.ok else ReplyKind.CLARIFY
        return Reply(run.text(lang), kind, lang, list(result.citations), actions=[action])

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
        scored = [s for s in self.store.query(query) if s.fact.id not in exclude
                  # with no known country, a fact for one country, and its numbers, is for someone else
                  and (country is not None or not s.fact.scope.countries)]
        if scored and not exclude and not self.store.on_topic(scored[0].fact.id, text):
            scored = []  # the best fact shares only a word with the question: say so rather than answer off topic
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
        if isinstance(self.composer, GroundedGenerator) and message.channel not in EXTRACTIVE_ONLY:
            composed = self.composer.compose(results, lang, room, question=text)
        elif isinstance(self.composer, GroundedGenerator):  # USSD and voice cannot wait on a model
            composed = self.composer.fallback.compose(results, lang, room)
        else:
            composed = self.composer.compose(results, lang, room)
        if human_line:  # do not repeat numbers the answer already gives
            remaining = [c for c in contacts if c.number not in composed.text]
            human_line = format_numbers(remaining, lang) if remaining else ""
        body = f"{composed.text} {human_line}".strip()

        if not exclude:
            profile.last_query = text
        profile.last_fact_ids = list(exclude | {f.id for f in composed.used})
        profile.last_sources, profile.last_service = [], None
        if composed.used:
            profile.last_topic = (composed.used[0].vertical, composed.used[0].topic)
        return Reply(body, ReplyKind.ANSWER, composed.language, _cite(composed.used))

    # ------------------------------------------------------------------ helpers

    def contacts_for_facts(self, facts: list[ContextFact], country: str | None) -> list[Contact]:
        """Numbers to show with safety critical facts: the fact's own lines when they belong to the
        caller's country, plus the caller's national lines for the fact's refer_queue."""
        out: list[Contact] = []
        for f in facts:
            if not f.scope.countries or (country and f.scope.countries == (country,)):
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
                   and (not f.scope.countries or (country and country in f.scope.countries))]
        matches.sort(key=lambda f: f.id)
        return matches[0] if matches else None

    def browse(self, pack_id: str, index: int, lang: str, budget: Budget,
               country: str | None = None) -> tuple[str, bool]:
        """One fact of a pack, for menu browsing. Returns (text, has_more)."""
        pack = next((p for p in self.packs if p.id == pack_id), None)
        if pack is None:
            return "", False
        facts = [f for f in pack.facts if (country or not f.scope.countries) and self.store.allowed(f, ContextQuery(
            country=country, min_review=self.config.min_review,
            include_verified=self.config.include_verified))]
        if index >= len(facts):
            return "", False
        fact = facts[index]
        text = fact.render(lang, short=budget.short)[0]
        if fact.safety_critical:
            missing = [c.number for c in self.contacts_for_facts([fact], country) if c.number not in text]
            if missing:
                call = call_line(", ".join(dict.fromkeys(missing)), lang)
                text = f"{truncate_words(text, budget.max_chars - len(call) - 1)} {call}"
        return truncate_words(text, budget.max_chars), index + 1 < len(facts)

    def _contact_facts(self, country: str | None = None) -> list[ContextFact]:
        """Facts that publish phone lines for the country. Emergency contact facts come first. With no known country,
        only lines that serve everywhere count, so a caller from outside ACE's countries is never given another
        country's number; with none, the reply tells them to call their local emergency number."""
        facts = [f for f in self.store if f.contacts
                 and (not f.scope.countries or (country is not None and country in f.scope.countries))]
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
        text = say("clarify", lang, topics=topics)
        if not self.config.tips:  # every clarify text ends with a sentence offering TIP, after the topics
            cut = text.rfind(topics) + len(topics)
            text = text[:cut] + (text[cut] if cut < len(text) and text[cut] in ".։።۔" else ".")
        return Reply(text, ReplyKind.CLARIFY, lang)

    @staticmethod
    def _system(text: str, lang: str, end: bool = False) -> Reply:
        return Reply(text, ReplyKind.SYSTEM, lang, end_session=end)

    @staticmethod
    def covered_countries() -> list[str]:
        return list(COUNTRIES)


def _listing(items: list[str], lang: str) -> str:
    """A, B or C, with the word for or in the reply's language."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} {OR_WORD.get(lang, 'or')} {items[-1]}"


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


# The licence of the pack each fact came from, so every citation names the terms its text is shared under.
_PACK_LICENCE: dict[str, str] = {}


def _date_text(value: object) -> str | None:
    """A fact's checked date as text, or None when it has none (never the word None)."""
    if value is None or value == "":
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _cite(facts: list[ContextFact]) -> list[Citation]:
    seen: dict[str, Citation] = {}
    for f in facts:
        checked = _date_text(f.checked_on)
        seen.setdefault(f.id, Citation(f.id, f.source, f.review_status.value, f.source_url,
                                       licence=_PACK_LICENCE.get(f.id), date=checked or None))
    return list(seen.values())


def _raise(sink: HandoffSink, queue: str, key: str, text: str, channel: str, country: str | None) -> None:
    """Raise a handoff, passing the country to sinks that take it (sinks written before 2.4 do not)."""
    params = inspect.signature(sink.raise_handoff).parameters
    if "country" in params or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        sink.raise_handoff(queue, key, text, channel, country=country)
    else:
        sink.raise_handoff(queue, key, text, channel)
