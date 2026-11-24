"""Channel adapters stay thin: parse the provider payload in, render a Reply out."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import Channel, Message, Reply
from ..text import truncate_words

__all__ = ["ChannelAdapter", "truncate_words"]


class ChannelAdapter(ABC):
    channel: Channel

    @abstractmethod
    def parse_inbound(self, payload: dict[str, Any]) -> Message:
        """Turn a provider webhook or callback payload into a normalized Message."""

    @abstractmethod
    def render(self, reply: Reply) -> list[str]:
        """Turn a Reply into what the channel can carry: one or more payloads, in order."""
