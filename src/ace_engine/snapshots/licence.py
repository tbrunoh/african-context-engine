"""The licence register: every source a connector may use, with the credit and terms it requires."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class LicenceEntry:
    id: str
    name: str
    publisher: str
    url: str
    licence: str
    attribution: str
    share_alike: bool = False
    terms: str = ""


def load_register(path: str | Path) -> dict[str, LicenceEntry]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    out = {}
    for item in data.get("sources", []):
        out[item["id"]] = LicenceEntry(
            id=item["id"], name=item["name"], publisher=item["publisher"], url=item["url"],
            licence=item["licence"], attribution=item["attribution"], share_alike=bool(item.get("share_alike")),
            terms=item.get("terms", ""))
    return out
