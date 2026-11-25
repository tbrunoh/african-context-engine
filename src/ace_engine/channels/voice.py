"""Voice: a keypad IVR for any phone, plus a hook for speech recognition.

VoiceApp answers Africa's Talking style voice callbacks (form fields
isActive, sessionId, callerNumber, dtmfDigits) with XML actions: Say to speak
and GetDigits to collect a key press. Callers browse the same context packs
as USSD, hearing the short form of each fact.

VoiceAdapter handles the other path: a transcript from any speech to text
engine, open or hosted, that plugs in behind the SpeechToText interface in
ace_engine.speech (Google Cloud Speech-to-Text is one ready option).

The line speaks a language only where a text to speech voice is known to
exist for it (see ace_engine/speech/support.yaml) or where the operator has
checked their provider and listed it in ACE_VOICE_LANGUAGES. No voice was
found for Amharic, Afaan Oromo or Somali on 25 November 2026, so callers who
use those languages hear the next language of their country that has one,
then English, rather than a voice reading a script it cannot pronounce.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from xml.sax.saxutils import escape

from .. import i18n, speech
from ..countries import COUNTRIES
from ..models import Channel, Message, Reply
from ..router import Budget
from .base import ChannelAdapter

if TYPE_CHECKING:
    from ..engine import Engine


SpeechToText = speech.SpeechToText  # kept here so existing imports keep working


class VoiceAdapter(ChannelAdapter):
    channel = Channel.VOICE

    def __init__(self, stt: SpeechToText | None = None, max_sentences_per_turn: int = 3) -> None:
        self.stt = stt
        self.max_sentences = max_sentences_per_turn

    def parse_inbound(self, payload: dict[str, Any]) -> Message:
        text, language = payload.get("transcript", ""), payload.get("language")
        if not text and payload.get("audio_uri"):
            if self.stt is None:
                raise ValueError("Audio received but no speech to text engine is configured")
            text, language = self.stt.transcribe(payload["audio_uri"], language)
        return Message(channel=self.channel, sender=str(payload["caller"]), text=text,
                       language=language, session_id=payload.get("call_id"), raw=payload)

    def render(self, reply: Reply) -> list[str]:
        """Split into short spoken turns so the caller can interrupt between them."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", reply.text) if s.strip()]
        turns = [" ".join(sentences[i:i + self.max_sentences])
                 for i in range(0, len(sentences), self.max_sentences)]
        return turns or [""]


PROMPTS = {
    "en": {"welcome": "Welcome to ACE.", "press": "For {label}, press {n}.", "repeat": "To hear the menu again, press 0.",
           "bye": "We did not get your choice. Goodbye.", "invalid": "That is not a valid choice."},
    "sw": {"welcome": "Karibu ACE.", "press": "Kwa {label}, bonyeza {n}.", "repeat": "Kusikia menyu tena, bonyeza 0.",
           "bye": "Hatukupata chaguo lako. Kwaheri.", "invalid": "Chaguo hilo si sahihi."},
    "fr": {"welcome": "Bienvenue sur ACE.", "press": "Pour {label}, tapez {n}.",
           "repeat": "Pour réécouter le menu, tapez 0.", "bye": "Nous n'avons pas reçu votre choix. Au revoir.",
           "invalid": "Ce choix n'est pas valide."},
}
i18n.localize("channels.voice", globals(), ("PROMPTS",))


class VoiceApp:
    """Keypad IVR over the context packs. Returns the XML body for each callback."""

    def __init__(self, engine: Engine, facts_per_topic: int = 3, timeout_s: int = 20) -> None:
        self.engine = engine
        self.facts_per_topic = facts_per_topic
        self.timeout_s = timeout_s

    def respond(self, payload: dict[str, Any]) -> str:
        if str(payload.get("isActive", "1")) == "0":
            return ""  # end of call notification; nothing to say
        caller = str(payload.get("callerNumber", ""))
        country = self.engine.country_for(caller) if caller else None
        lang = self.spoken_language(caller, country)
        digits = str(payload.get("dtmfDigits") or "").strip()
        packs = self.engine.packs_for(country)[:9]
        if not digits or digits == "0":
            return self._menu(lang, packs)
        if not digits.isdigit() or not 1 <= int(digits) <= len(packs):
            return self._menu(lang, packs, PROMPTS[lang]["invalid"])
        pack = packs[int(digits) - 1]
        budget = Budget(max_chars=400, short=True, max_facts=1)
        spoken = []
        for i in range(self.facts_per_topic):
            text, more = self.engine.browse(pack.id, i, lang, budget, country)
            if text:
                spoken.append(text)
            if not more:
                break
        return self._xml([("Say", " ".join(spoken))], gather=PROMPTS[lang]["repeat"], lang=lang)

    def spoken_language(self, caller: str, country: str | None) -> str:
        """The caller's language if the line can speak it, else the next spoken language of their country."""
        first = self.engine.language_for(caller) if caller else self.engine.config.default_language
        local = list(COUNTRIES[country].languages) if country in COUNTRIES else []
        preferred = [c for c in dict.fromkeys([first, *local, "en"]) if c in PROMPTS]
        return speech.spoken_language(preferred)

    def _menu(self, lang: str, packs: list, prefix: str = "") -> str:
        p = PROMPTS[lang]
        options = " ".join(p["press"].format(label=pk.label(lang), n=i) for i, pk in enumerate(packs, start=1))
        return self._xml([], gather=" ".join(x for x in (prefix, p["welcome"], options) if x), lang=lang)

    def _xml(self, actions: list[tuple[str, str]], gather: str, lang: str) -> str:
        body = "".join(f"<{tag}>{escape(text)}</{tag}>" for tag, text in actions if text)
        get = (f'<GetDigits timeout="{self.timeout_s}" numDigits="1">'
               f"<Say>{escape(gather)}</Say></GetDigits>")
        bye = f"<Say>{escape(PROMPTS[lang]['bye'])}</Say>"
        return f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}{get}{bye}</Response>'
