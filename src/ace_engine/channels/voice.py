"""Voice adapter. Speech recognition and synthesis sit behind interfaces so any
open or hosted model (Omnilingual ASR, WAXAL tuned models, a cloud provider) plugs in."""
from __future__ import annotations

import re
from typing import Any, Protocol

from ..models import Channel, Message, Reply
from .base import ChannelAdapter


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
