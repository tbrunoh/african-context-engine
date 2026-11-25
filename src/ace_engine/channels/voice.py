"""Voice: a keypad IVR for any phone, plus a hook for speech recognition.

VoiceApp answers Africa's Talking style voice callbacks (form fields
isActive, sessionId, callerNumber, dtmfDigits) with XML actions: Say to speak
and GetDigits to collect a key press. Callers browse the same context packs
as USSD, hearing the short form of each fact.

VoiceAdapter handles the other path: a transcript from any speech to text
engine, open or hosted, that plugs in behind the SpeechToText interface.
Whether a given text to speech voice can speak Swahili or another language
depends on the provider; check before launching a non English line.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Protocol
from xml.sax.saxutils import escape

from .. import i18n
from ..models import Channel, Message, Reply
from ..router import Budget
from .base import ChannelAdapter

if TYPE_CHECKING:
    from ..engine import Engine


class SpeechToText(Protocol):
    def transcribe(self, audio_uri: str, language_hint: str | None = None) -> tuple[str, str | None]:
        """Return (transcript, detected_language)."""


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
        lang = self.engine.language_for(caller) if caller else self.engine.config.default_language
        lang = lang if lang in PROMPTS else "en"
        country = self.engine.country_for(caller) if caller else None
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
