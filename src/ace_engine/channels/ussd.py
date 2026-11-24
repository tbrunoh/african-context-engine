"""USSD: a full menu app for any phone, built for Africa's Talking style gateways.

The gateway POSTs sessionId, serviceCode, phoneNumber and text on every
screen, where text holds every input of the session joined by "*". Replies
start with CON to keep the session open or END to close it. A screen holds
about 182 characters, and some networks give the application only a few
seconds to answer, so every screen here is composed locally and quickly.

The app is stateless: it rebuilds the session state by replaying the input
path, so it scales horizontally without a session store.

Menu (V2):
    1..6  decision services: rain this week, official warnings, nearest health facility,
          market prices, pregnancy check, crop problem
    7     topics: browse a context pack one fact at a time
    8     ask a question in your own words
    9     check a suspicious message (Scam Shield)
    10    language
Without snapshots (a V1 deployment) the services are left out and the packs are listed directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..models import Channel, Message, Reply, ReplyKind
from ..router import Budget
from .base import ChannelAdapter, truncate_words

if TYPE_CHECKING:
    from ..engine import Engine

USSD_MAX_CHARS = 182

UI = {
    "en": {"ask": "Ask a question", "scam": "Check a message", "lang": "Language",
           "more": "98 More", "next": "1 Next", "back": "0 Back", "menu": "0 Menu",
           "ask_prompt": "Type your question:", "scam_prompt": "Type or paste the message:",
           "invalid": "Invalid choice.", "end_pack": "That is all for this topic.",
           "lang_prompt": "1 English\n2 Kiswahili\n3 Francais", "topics": "Topics",
           "place_prompt": "Type your {area}:", "food_prompt": "Type the food and your {area}, e.g. maize {example}:",
           "weeks_prompt": "How many weeks pregnant are you?", "crop_prompt": "Type the crop and what you see:"},
    "sw": {"ask": "Uliza swali", "scam": "Kagua ujumbe", "lang": "Lugha/Language",
           "more": "98 Zaidi", "next": "1 Endelea", "back": "0 Rudi", "menu": "0 Menyu",
           "ask_prompt": "Andika swali lako:", "scam_prompt": "Andika au bandika ujumbe:",
           "invalid": "Chaguo si sahihi.", "end_pack": "Hayo ndiyo yote kwa mada hii.",
           "lang_prompt": "1 English\n2 Kiswahili\n3 Francais", "topics": "Mada",
           "place_prompt": "Andika {area} yako:", "food_prompt": "Andika chakula na {area} yako, mf. mahindi {example}:",
           "weeks_prompt": "Una ujauzito wa wiki ngapi?", "crop_prompt": "Andika zao na unachokiona:"},
    "fr": {"ask": "Poser une question", "scam": "Verifier un message", "lang": "Langue/Language",
           "more": "98 Suite", "next": "1 Suivant", "back": "0 Retour", "menu": "0 Menu",
           "ask_prompt": "Tapez votre question :", "scam_prompt": "Tapez ou collez le message :",
           "invalid": "Choix invalide.", "end_pack": "C'est tout pour ce sujet.",
           "lang_prompt": "1 English\n2 Kiswahili\n3 Francais", "topics": "Sujets",
           "place_prompt": "Tapez votre {area} :", "food_prompt": "Tapez l'aliment et votre {area}, ex. maïs {example} :",
           "weeks_prompt": "Enceinte de combien de semaines ?", "crop_prompt": "Tapez la culture et ce que vous voyez :"},
}
SERVICE_ORDER = ("rain_this_week", "official_warnings", "nearest_facility", "market_prices", "pregnancy_companion",
                 "pest_check")
PROMPT_KEY = {"rain_this_week": "place_prompt", "official_warnings": "place_prompt", "nearest_facility": "place_prompt",
              "market_prices": "food_prompt", "pregnancy_companion": "weeks_prompt", "pest_check": "crop_prompt"}
_LANG_CHOICES = {"1": "en", "2": "sw", "3": "fr"}


class UssdAdapter(ChannelAdapter):
    """Parse a gateway callback into a Message carrying the latest input."""

    channel = Channel.USSD

    def __init__(self, max_chars: int = USSD_MAX_CHARS) -> None:
        self.max_chars = max_chars

    def parse_inbound(self, payload: dict[str, Any]) -> Message:
        inputs = split_inputs(str(payload.get("text", "")))
        return Message(
            channel=self.channel,
            sender=str(payload["phoneNumber"]),
            text=inputs[-1] if inputs else "",
            session_id=str(payload.get("sessionId", "")) or None,
            raw={"inputs": inputs, "serviceCode": payload.get("serviceCode")},
        )

    def render(self, reply: Reply) -> list[str]:
        prefix = "END " if reply.end_session else "CON "
        return [prefix + truncate_words(reply.text, self.max_chars - len(prefix))]


def split_inputs(text: str) -> list[str]:
    return [p for p in text.split("*")] if text else []


@dataclass
class _State:
    screen: str = "main"      # main, topics, pack, svc, ask, scam, lang, answer
    service: str = ""
    page: int = 0
    pack_index: int = 0
    fact_index: int = 0
    error: bool = False
    answer: str = ""
    end: bool = False


class UssdApp:
    """The menu state machine. One call per gateway request; returns the CON or END string."""

    def __init__(self, engine: Engine, title: str = "ACE", max_chars: int = USSD_MAX_CHARS) -> None:
        self.engine = engine
        self.title = title
        self.max_chars = max_chars

    # -- public ---------------------------------------------------------------

    def respond(self, phone: str, text: str, session_id: str | None = None) -> str:
        inputs = split_inputs(text)
        state = _State()
        for i, token in enumerate(inputs):
            self._step(state, token.strip(), phone, session_id, last=(i == len(inputs) - 1))
        return self._render(state, phone)

    def handle_payload(self, payload: dict[str, Any]) -> str:
        return self.respond(str(payload["phoneNumber"]), str(payload.get("text", "")),
                            str(payload.get("sessionId", "")) or None)

    # -- helpers --------------------------------------------------------------

    def _lang(self, phone: str) -> str:
        lang = self.engine.language_for(phone)
        return lang if lang in UI else "en"

    def _packs(self, phone: str):
        return self.engine.packs_for(self.engine.country_for(phone))

    def _items(self, lang: str, phone: str) -> list[tuple[str, str]]:
        tail = [("ask", UI[lang]["ask"]), ("scam", UI[lang]["scam"]), ("lang", UI[lang]["lang"])]
        if self.engine.services is None:  # V1: packs straight on the main menu
            return [("pack:" + p.id, p.label(lang)) for p in self._packs(phone)] + tail
        from ..services import SERVICES

        services = [("svc:" + sid, SERVICES[sid].title[lang]) for sid in SERVICE_ORDER]
        return services + [("topics", UI[lang]["topics"])] + tail

    def _topic_items(self, lang: str, phone: str) -> list[tuple[str, str]]:
        return [("pack:" + p.id, p.label(lang)) for p in self._packs(phone)]

    def _pages(self, lang: str, phone: str, topics: bool = False) -> list[list[tuple[int, str, str]]]:
        """Split the numbered menu into screens that fit, leaving room for the More line."""
        items = self._topic_items(lang, phone) if topics else self._items(lang, phone)
        numbered = [(n, key, label) for n, (key, label) in enumerate(items, start=1)]
        head = max(len(self.title), len(UI[lang]["invalid"]), len(UI[lang]["topics"]))  # room for any title line
        budget = self.max_chars - 4 - head - 1 - len(UI[lang]["more"]) - 1 - (len(UI[lang]["back"]) + 1 if topics else 0)
        pages: list[list[tuple[int, str, str]]] = [[]]
        used = 0
        for item in numbered:
            line = len(f"{item[0]} {item[2]}") + 1
            if pages[-1] and used + line > budget:
                pages.append([])
                used = 0
            pages[-1].append(item)
            used += line
        return pages

    def _answer_budget(self, lang: str) -> Budget:
        return Budget(max_chars=self.max_chars - 4 - len(UI[lang]["menu"]) - 1, short=True, max_facts=1)

    def _ask(self, phone: str, text: str, session_id: str | None) -> Reply:
        message = Message(channel=Channel.USSD, sender=phone, text=text, session_id=session_id)
        return self.engine.handle(message, self._answer_budget(self._lang(phone)))

    def _step(self, s: _State, token: str, phone: str, session_id: str | None, last: bool) -> None:
        s.error = False
        lang = self._lang(phone)
        if s.screen in ("pack", "answer") and token == "00":
            s.screen, s.page = "main", 0
            return
        if s.screen in ("main", "topics"):
            topics = s.screen == "topics"
            if topics and token == "0":
                s.screen, s.page = "main", 0
                return
            pages = self._pages(lang, phone, topics)
            if token == "98" and s.page + 1 < len(pages):
                s.page += 1
                return
            choice = next((key for n, key, _ in (i for p in pages for i in p) if str(n) == token), None)
            if choice is None:
                s.error = True
            elif choice.startswith("pack:"):
                s.screen, s.pack_index, s.fact_index = "pack", [p.id for p in self._packs(phone)].index(
                    choice[5:]), 0
            elif choice.startswith("svc:"):
                s.screen, s.service = "svc", choice[4:]
            elif choice == "topics":
                s.screen, s.page = "topics", 0
            else:
                s.screen = choice
        elif s.screen == "pack":
            if token == "1":
                s.fact_index += 1
            elif token == "0":
                s.screen, s.page = "main", 0
            else:
                s.error = True
        elif s.screen in ("ask", "scam", "svc", "answer"):
            if s.screen == "answer" and token == "0":
                s.screen, s.page = "main", 0
                return
            if last:
                text = f"SCAM {token}" if s.screen == "scam" else token
                if s.screen == "svc":
                    message = Message(channel=Channel.USSD, sender=phone, text=token, session_id=session_id)
                    reply = self.engine.run_service(s.service, message, self._answer_budget(lang))
                else:
                    reply = self._ask(phone, text, session_id)
                s.answer = reply.text
                s.end = reply.kind is ReplyKind.EMERGENCY or reply.end_session
            s.screen = "answer"
        elif s.screen == "lang":
            if token in _LANG_CHOICES:
                profile = self.engine.profiles.get_or_create(phone)
                profile.language = _LANG_CHOICES[token]
                s.screen, s.page = "main", 0
            else:
                s.error = True

    def _render(self, s: _State, phone: str) -> str:
        lang = self._lang(phone)
        ui = UI[lang]
        prefix = ""
        if s.error:
            prefix = ui["invalid"] + "\n"
        if s.screen in ("main", "topics"):
            topics = s.screen == "topics"
            pages = self._pages(lang, phone, topics)
            page = pages[min(s.page, len(pages) - 1)]
            title = ui["topics"] if topics else self.title
            lines = [ui["invalid"] if s.error else title] + [f"{n} {label}" for n, _, label in page]
            if s.page + 1 < len(pages):
                lines.append(ui["more"])
            if topics:
                lines.append(ui["back"])
            return self._con("\n".join(lines))
        if s.screen == "svc":
            from ..services.base import EXAMPLE_PLACE, area_word

            country = self.engine.country_for(phone)
            prompt = ui[PROMPT_KEY[s.service]].format(area=area_word(country, lang),
                                                      example=EXAMPLE_PLACE.get(country or "", "Kano"))
            return self._con(prefix + prompt)
        if s.screen == "pack":
            pack = self._packs(phone)[s.pack_index]
            footer_full = f"\n{ui['next']}  {ui['back']}"
            budget = Budget(self.max_chars - 4 - len(prefix) - len(footer_full), short=True, max_facts=1)
            text, has_more = self.engine.browse(pack.id, s.fact_index, lang, budget,
                                                self.engine.country_for(phone))
            if not text:
                return self._con(f"{prefix}{ui['end_pack']}\n{ui['back']}")
            footer = footer_full if has_more else f"\n{ui['back']}"
            return self._con(prefix + text + footer)
        if s.screen == "ask":
            return self._con(prefix + ui["ask_prompt"])
        if s.screen == "scam":
            return self._con(prefix + ui["scam_prompt"])
        if s.screen == "lang":
            return self._con(prefix + ui["lang_prompt"])
        if s.screen == "answer":
            if s.end:
                return self._end(s.answer)
            return self._con(f"{s.answer}\n{ui['menu']}")
        return self._con(self.title)

    def _con(self, body: str) -> str:
        return "CON " + _fit(body, self.max_chars - 4)

    def _end(self, body: str) -> str:
        return "END " + _fit(body, self.max_chars - 4)


def _fit(body: str, limit: int) -> str:
    """Trim a multi line screen to the limit, keeping the menu lines at the end intact."""
    if len(body) <= limit:
        return body
    lines = body.split("\n")
    tail = [ln for ln in lines[1:] if ln[:2].strip().isdigit()]
    head = "\n".join(ln for ln in lines if ln not in tail)
    room = limit - sum(len(t) + 1 for t in tail)
    return "\n".join([truncate_words(head, max(10, room)), *tail])[:limit]
