"""Google providers for hearing, speaking and translating: Cloud Speech-to-Text V2, Cloud Text-to-Speech, Cloud
Translation, and Gemini TTS for languages Cloud Text-to-Speech has no voice for, such as Amharic and Somali.

Optional. Install with `pip install -e ".[google]"` from a checkout and give ACE a Google Cloud project with the APIs you
need enabled. Credentials come from Application Default Credentials (a service account attached to the host, or
GOOGLE_APPLICATION_CREDENTIALS pointing at a key file outside the repository). ACE never reads, stores or logs a
key itself, and no key belongs in this repository. Usage is billed to the operator's project.

Gemini TTS uses a Gemini API key from GEMINI_API_KEY, sent only in the request header.

Each class takes a `post` callable so tests and other transports can stand in for the network.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from . import capability, play_voice, say_voice

Post = Callable[[str, dict[str, Any]], dict[str, Any]]
SCOPE = "https://www.googleapis.com/auth/cloud-platform"
MAX_INLINE_BYTES = 10 * 1024 * 1024  # Speech-to-Text V2 inline audio limit for Recognize


def project_from_env() -> str:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project:
        raise RuntimeError("Set GOOGLE_CLOUD_PROJECT to the Google Cloud project ACE should bill")
    return project


def authorized_post(timeout: float = 60.0) -> Post:
    """A POST function signed with Application Default Credentials. Needs the google extra."""
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
    except ImportError as exc:  # pragma: no cover - depends on the optional extra
        raise RuntimeError('Install the Google extra: pip install -e ".[google]" from a checkout') from exc
    credentials, _ = google.auth.default(scopes=[SCOPE])
    session = AuthorizedSession(credentials)

    def post(url: str, body: dict[str, Any]) -> dict[str, Any]:
        response = session.post(url, json=body, timeout=timeout)
        if response.status_code >= 400:
            raise RuntimeError(f"Google Cloud returned {response.status_code} for {url.split('?')[0]}")
        return response.json()

    return post


def fetch_audio(url: str) -> bytes:
    """Download a call recording, such as the recordingUrl Africa's Talking sends."""
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(MAX_INLINE_BYTES + 1)
    if len(data) > MAX_INLINE_BYTES:
        raise ValueError("Recording is too long for one recognition request")
    return data


class GoogleSpeechToText:
    """Speech-to-Text V2 Recognize with the model support.yaml records for each language (Chirp 3 where it exists)."""

    def __init__(self, project: str | None = None, location: str | None = None, post: Post | None = None,
                 fetch: Callable[[str], bytes] = fetch_audio) -> None:
        self.project = project or project_from_env()
        self.location = location
        self._post = post
        self.fetch = fetch

    @property
    def post(self) -> Post:
        if self._post is None:
            self._post = authorized_post()
        return self._post

    def transcribe(self, audio_uri: str, language_hint: str | None = None) -> tuple[str, str | None]:
        hear = capability(language_hint or "", "hear")
        if hear is None:
            raise ValueError(f"No speech recognition model is recorded for {language_hint!r}; use the keypad line")
        # Chirp and Chirp 2 run in single regions; Chirp 3 and the older long and short models in multi-regions.
        location = self.location or ("us-central1" if hear["model"] in ("chirp", "chirp_2") else "us")
        host = "speech.googleapis.com" if location == "global" else f"{location}-speech.googleapis.com"
        url = f"https://{host}/v2/projects/{self.project}/locations/{location}/recognizers/_:recognize"
        body: dict[str, Any] = {"config": {"autoDecodingConfig": {}, "model": hear["model"],
                                           "languageCodes": [hear["locale"]]}}
        if audio_uri.startswith("gs://"):
            body["uri"] = audio_uri
        else:
            body["content"] = base64.b64encode(self.fetch(audio_uri)).decode("ascii")
        result = self.post(url, body)
        parts = [r["alternatives"][0].get("transcript", "") for r in result.get("results", []) if r.get("alternatives")]
        return " ".join(p.strip() for p in parts if p.strip()), language_hint


class GoogleTextToSpeech:
    """Text-to-Speech synthesis in the voice support.yaml records for each language."""

    URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

    def __init__(self, post: Post | None = None, encoding: str = "MP3") -> None:
        self._post = post
        self.encoding = encoding

    @property
    def post(self) -> Post:
        if self._post is None:
            self._post = authorized_post()
        return self._post

    def synthesize(self, text: str, language: str) -> bytes:
        speak = say_voice(language)
        if speak is None:
            raise ValueError(f"No Cloud Text-to-Speech voice is recorded for {language!r}; try GeminiTextToSpeech")
        body = {"input": {"text": text}, "voice": {"languageCode": speak["locale"]},
                "audioConfig": {"audioEncoding": self.encoding}}
        return base64.b64decode(self.post(self.URL, body)["audioContent"])


def keyed_post(env: str = "GEMINI_API_KEY") -> Post:
    """A POST function that sends the Gemini API key from the environment in the x-goog-api-key header."""
    key = os.environ.get(env, "")
    if not key:
        raise RuntimeError(f"Set {env} to a Gemini API key; ACE never stores it")

    def post(url: str, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Gemini API returned {exc.code}") from None

    return post


class GeminiTextToSpeech:
    """Gemini TTS through the Gemini API. The model reads the language from the text; unary calls return WAV.

    support.yaml lists which ACE languages the model speaks (speak.play). Amharic and Somali are the reason this
    exists: Cloud Text-to-Speech has no voice for them, Gemini 3.8 Flash TTS lists both.
    """

    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, model: str = "gemini-3.8-flash-tts", voice: str = "Kore", post: Post | None = None) -> None:
        self.model = model
        self.voice = voice
        self._post = post

    @property
    def post(self) -> Post:
        if self._post is None:
            self._post = keyed_post()
        return self._post

    def synthesize(self, text: str, language: str) -> bytes:
        play = play_voice(language)
        if play is None:
            raise ValueError(f"No Gemini TTS voice is recorded for {language!r}")
        body = {"contents": [{"role": "user", "parts": [{"text": text}]}],
                "generationConfig": {"responseModalities": ["AUDIO"],
                                     "speechConfig": {"voiceConfig": {"voice": self.voice}}}}
        result = self.post(self.URL.format(model=play.get("model", self.model)), body)
        try:
            data = result["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("Gemini TTS returned no audio") from None
        return base64.b64decode(data)


class GoogleTranslator:
    """Cloud Translation Advanced (v3) translateText, for drafts and back translations only."""

    def __init__(self, project: str | None = None, post: Post | None = None, batch: int = 100) -> None:
        self.project = project or project_from_env()
        self._post = post
        self.batch = batch

    @property
    def post(self) -> Post:
        if self._post is None:
            self._post = authorized_post()
        return self._post

    @property
    def url(self) -> str:
        return f"https://translation.googleapis.com/v3/projects/{self.project}/locations/global:translateText"

    def translate(self, texts: list[str], target: str, source: str = "en") -> list[str]:
        out: list[str] = []
        for i in range(0, len(texts), self.batch):
            chunk = texts[i:i + self.batch]
            body = {"contents": chunk, "sourceLanguageCode": source, "targetLanguageCode": target,
                    "mimeType": "text/plain"}
            found = [t["translatedText"] for t in self.post(self.url, body).get("translations", [])]
            if len(found) != len(chunk):
                raise RuntimeError("Translation returned a different number of texts than were sent")
            out.extend(found)
        return out


class GoogleLanguageDetector:
    """Cloud Translation Advanced (v3) detectLanguage, as a LanguageIdentifier (see ace_engine.langid).

    Unlike the translator, this runs while a person waits: ACE calls it only to confirm a message its own check
    would turn away and sends at most the first 500 characters. ACE gives up after three seconds, credentials
    included (see langid.confirmed_by), and keeps its own judgement. The message text goes to Google Cloud under
    the operator's own project and terms, so an operator who turns it on says so in their privacy notice. Each call
    is billed like translation."""

    MAX_CHARS = 500

    def __init__(self, project: str | None = None, post: Post | None = None, timeout: float = 3.0) -> None:
        self.project = project or project_from_env()
        self._post = post
        self.timeout = timeout

    @property
    def post(self) -> Post:
        if self._post is None:
            self._post = authorized_post(timeout=self.timeout)
        return self._post

    @property
    def url(self) -> str:
        return f"https://translation.googleapis.com/v3/projects/{self.project}/locations/global:detectLanguage"

    def identify(self, text: str) -> list[tuple[str, float]]:
        found = self.post(self.url, {"content": text[:self.MAX_CHARS], "mimeType": "text/plain"}).get("languages", [])
        return [(str(f.get("languageCode", "")), float(f.get("confidence", 0.0))) for f in found]

