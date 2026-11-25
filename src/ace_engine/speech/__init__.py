"""Speech and translation for ACE: what each language can do today, and the interfaces providers plug into.

ACE runs with no speech or translation provider at all. The keypad voice line, USSD, SMS and WhatsApp need
none. A provider adds three things, each optional:

  * hear: speech to text for spoken questions on the voice line (the SpeechToText interface)
  * speak: text to speech, so the voice line talks in the caller's language (the TextToSpeech interface)
  * translate: machine drafts and back translations that help fluent reviewers check locale files. Translation
    never runs while answering a person; every word ACE sends comes from a locale file or a sourced pack.

The safety rail never waits on any of this. It reads the transcript like any other text, and the keypad stays
open on every voice turn, so a caller is never stuck behind a recogniser.

support.yaml records, with sources and a date, what exists for each ACE language. `speakable()` is the rule the
voice line follows: a language is spoken only where a voice is known to exist, or where the operator has checked
their own provider and listed the language in ACE_VOICE_LANGUAGES.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

import yaml

SUPPORT_FILE = Path(__file__).parent / "support.yaml"
VOICE_LANGUAGES_ENV = "ACE_VOICE_LANGUAGES"


class SpeechToText(Protocol):
    def transcribe(self, audio_uri: str, language_hint: str | None = None) -> tuple[str, str | None]:
        """Return (transcript, detected_language)."""


class TextToSpeech(Protocol):
    def synthesize(self, text: str, language: str) -> bytes:
        """Return encoded audio for text spoken in language."""


class Translator(Protocol):
    def translate(self, texts: list[str], target: str, source: str = "en") -> list[str]:
        """Return one translation per input text, in order."""


@lru_cache(maxsize=1)
def support() -> dict[str, Any]:
    return yaml.safe_load(SUPPORT_FILE.read_text(encoding="utf-8"))


def capability(language: str, kind: str) -> dict[str, Any] | None:
    """The recorded hear, speak or translate entry for a language, or None where nothing is known to exist."""
    return (support()["languages"].get(language) or {}).get(kind)


def declared_voice_languages() -> frozenset[str]:
    """Languages the operator has checked on their own voice provider, from ACE_VOICE_LANGUAGES (comma separated)."""
    raw = os.environ.get(VOICE_LANGUAGES_ENV, "")
    return frozenset(code.strip().lower() for code in raw.split(",") if code.strip())


def speakable(language: str) -> bool:
    """True when the voice line may speak this language: a known voice, or one the operator declared."""
    declared = declared_voice_languages()
    if declared:
        return language in declared
    return capability(language, "speak") is not None


def spoken_language(preferred: list[str]) -> str:
    """The first language in preferred order that the voice line can speak, falling back to English."""
    for code in preferred:
        if speakable(code):
            return code
    return "en"


def table() -> list[dict[str, str]]:
    """One row per ACE language for docs and `ace voice languages`."""
    from ..text import SUPPORTED_LANGUAGES

    rows = []
    for code in SUPPORTED_LANGUAGES:
        hear, speak, trans = (capability(code, k) for k in ("hear", "speak", "translate"))
        waxal = (support()["languages"].get(code) or {}).get("waxal") or {}
        rows.append({
            "language": code,
            "hear": f"{hear['model']} {hear['locale']} ({hear['stage']})" if hear else "none found",
            "speak": f"{speak['locale']} ({speak['voices']})" if speak else "none found",
            "translate": trans["model"] if trans else "none found",
            "waxal": (f"{waxal['asr_hours']} h transcribed" if "asr_hours" in waxal else
                      f"{waxal['tts_utterances']} voice script lines" if "tts_utterances" in waxal else "not in WAXAL"),
        })
    return rows
