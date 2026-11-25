"""Speech and translation for ACE: what each language can do today, and the interfaces providers plug into.

ACE runs with no speech or translation provider at all. The keypad voice line, USSD, SMS and WhatsApp need
none. A provider adds three things, each optional:

  * hear: speech to text for spoken questions on the voice line (the SpeechToText interface)
  * speak: text to speech, so the voice line talks in the caller's language (the TextToSpeech interface).
    Two paths: the Africa's Talking Say action reads text with a Google Cloud Text-to-Speech voice, or ACE
    synthesises the audio with Gemini TTS and the call plays it with the Play action (see PlayedVoice)
  * translate: machine drafts and back translations that help fluent reviewers check locale files. Translation
    never runs while answering a person; every word ACE sends comes from a locale file or a sourced pack.

The safety rail never waits on any of this. It reads the transcript like any other text, and the keypad stays
open on every voice turn, so a caller is never stuck behind a recogniser.

support.yaml records, with sources and a date, what exists for each ACE language. `speakable()` is the rule the
voice line follows for Say: a language is read aloud only where a Cloud Text-to-Speech voice is known to exist,
or where the operator has checked their own provider and listed the language in ACE_VOICE_LANGUAGES. A
PlayedVoice adds the languages its Gemini model speaks, such as Amharic and Somali.
"""
from __future__ import annotations

import hashlib
import os
import re
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


def say_voice(language: str) -> dict[str, Any] | None:
    """The Cloud Text-to-Speech voice the Say action can read this language with, or None."""
    return (capability(language, "speak") or {}).get("say")


def play_voice(language: str) -> dict[str, Any] | None:
    """The Gemini TTS model that can speak this language for the Play action, or None."""
    return (capability(language, "speak") or {}).get("play")


def declared_voice_languages() -> frozenset[str]:
    """Languages the operator has checked on their own voice provider, from ACE_VOICE_LANGUAGES (comma separated)."""
    raw = os.environ.get(VOICE_LANGUAGES_ENV, "")
    return frozenset(code.strip().lower() for code in raw.split(",") if code.strip())


def speakable(language: str) -> bool:
    """True when the Say action may read this language: a known voice, or one the operator declared."""
    declared = declared_voice_languages()
    if declared:
        return language in declared
    return say_voice(language) is not None


def spoken_language(preferred: list[str], extra: frozenset[str] = frozenset()) -> str:
    """The first language in preferred order the voice line can speak (Say, or extra played languages)."""
    for code in preferred:
        if code in extra or speakable(code):
            return code
    return "en"


AUDIO_NAME = re.compile(r"^[0-9a-f]{32}\.wav$")


class PlayedVoice:
    """Speaks through synthesised audio files that the call plays with the Play action.

    Each prompt or fact is synthesised once, stored as <hash>.wav in cache_dir and served by the web server at
    <base_url>/voice/audio/<hash>.wav. Only fixed prompts and public pack text are ever synthesised, never a
    caller's words or number, so the files hold nothing personal.
    """

    def __init__(self, tts: TextToSpeech, cache_dir: str | os.PathLike[str], base_url: str,
                 languages: frozenset[str] | None = None) -> None:
        self.tts = tts
        self.cache_dir = Path(cache_dir)
        self.base_url = base_url.rstrip("/")
        self.languages = languages if languages is not None else frozenset(
            code for code in support()["languages"] if play_voice(code))

    def speaks(self, language: str) -> bool:
        return language in self.languages

    def url(self, text: str, language: str) -> str:
        name = hashlib.sha256(f"{language}\n{text}".encode()).hexdigest()[:32] + ".wav"
        path = self.cache_dir / name
        if not path.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".part")
            tmp.write_bytes(self.tts.synthesize(text, language))
            tmp.replace(path)
        return f"{self.base_url}/voice/audio/{name}"

    def audio(self, name: str) -> bytes | None:
        """The bytes of a cached file, or None. Rejects any name that is not a cache file name."""
        if not AUDIO_NAME.match(name):
            return None
        path = self.cache_dir / name
        return path.read_bytes() if path.is_file() else None


def table() -> list[dict[str, str]]:
    """One row per ACE language for docs and `ace voice languages`."""
    from ..text import SUPPORTED_LANGUAGES

    rows = []
    for code in SUPPORTED_LANGUAGES:
        hear, trans = capability(code, "hear"), capability(code, "translate")
        say, play = say_voice(code), play_voice(code)
        spoken = [f"Say {say['locale']} ({say['voices']})" if say else "", f"Play {play['model']}" if play else ""]
        waxal = (support()["languages"].get(code) or {}).get("waxal") or {}
        rows.append({
            "language": code,
            "hear": f"{hear['model']} {hear['locale']} ({hear['stage']})" if hear else "none found",
            "speak": "; ".join(x for x in spoken if x) or "none found",
            "translate": trans["model"] if trans else "none found",
            "waxal": (f"{waxal['asr_hours']} h transcribed" if "asr_hours" in waxal else
                      f"{waxal['tts_utterances']} voice script lines" if "tts_utterances" in waxal else "not in WAXAL"),
        })
    return rows
