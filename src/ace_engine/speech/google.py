"""Google Cloud providers for hearing, speaking and translating: Speech-to-Text V2, Text-to-Speech and Translation.

Optional. Install with `pip install "ace-engine[google]"` and give ACE a Google Cloud project with the APIs you
need enabled. Credentials come from Application Default Credentials (a service account attached to the host, or
GOOGLE_APPLICATION_CREDENTIALS pointing at a key file outside the repository). ACE never reads, stores or logs a
key itself, and no key belongs in this repository. Usage is billed to the operator's project.

Each class takes a `post` callable so tests and other transports can stand in for the network.
"""
from __future__ import annotations

import base64
import os
import urllib.request
from collections.abc import Callable
from typing import Any

from . import capability

Post = Callable[[str, dict[str, Any]], dict[str, Any]]
SCOPE = "https://www.googleapis.com/auth/cloud-platform"
MAX_INLINE_BYTES = 10 * 1024 * 1024  # Speech-to-Text V2 inline audio limit for Recognize


def project_from_env() -> str:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project:
        raise RuntimeError("Set GOOGLE_CLOUD_PROJECT to the Google Cloud project ACE should bill")
    return project


def authorized_post() -> Post:
    """A POST function signed with Application Default Credentials. Needs the google extra."""
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
    except ImportError as exc:  # pragma: no cover - depends on the optional extra
        raise RuntimeError('Install the Google extra: pip install "ace-engine[google]"') from exc
    credentials, _ = google.auth.default(scopes=[SCOPE])
    session = AuthorizedSession(credentials)

    def post(url: str, body: dict[str, Any]) -> dict[str, Any]:
        response = session.post(url, json=body, timeout=60)
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
        location = self.location or ("asia-southeast1" if hear["model"] == "chirp" else "us")
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
        speak = capability(language, "speak")
        if speak is None:
            raise ValueError(f"No voice is recorded for {language!r}")
        body = {"input": {"text": text}, "voice": {"languageCode": speak["locale"]},
                "audioConfig": {"audioEncoding": self.encoding}}
        return base64.b64decode(self.post(self.URL, body)["audioContent"])


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
