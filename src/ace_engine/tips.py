"""The community knowledge loop: anyone can text a tip, nothing is served until reviewed.

Tips land in a queue keyed by the pseudonymous profile key, never the phone
number. Reviewers export the queue, check each tip with a domain expert, and
turn the good ones into pack facts through a normal pull request. That keeps
the review history in git, where everyone can see it.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Tip:
    person: str          # pseudonymous profile key
    text: str
    channel: str
    language: str
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "pending_review"


class TipQueue:
    """Append only queue. With a path, tips persist as JSON lines; without one they stay in memory."""

    def __init__(self, path: str | Path | None = None, max_chars: int = 500) -> None:
        self.path = Path(path) if path else None
        self.max_chars = max_chars
        self._memory: list[Tip] = []

    def submit(self, tip: Tip) -> Tip:
        tip.text = " ".join(tip.text.split())[: self.max_chars]
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(asdict(tip), ensure_ascii=False) + "\n")
        else:
            self._memory.append(tip)
        return tip

    def pending(self) -> list[Tip]:
        if not self.path:
            return list(self._memory)
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as fh:
            return [Tip(**json.loads(line)) for line in fh if line.strip()]

    def forget(self, person: str) -> int:
        """Remove every tip from one person. Returns how many were removed."""
        tips = self.pending()
        keep = [t for t in tips if t.person != person]
        removed = len(tips) - len(keep)
        if removed:
            if self.path:
                with self.path.open("w", encoding="utf-8") as fh:
                    for t in keep:
                        fh.write(json.dumps(asdict(t), ensure_ascii=False) + "\n")
            else:
                self._memory = keep
        return removed
