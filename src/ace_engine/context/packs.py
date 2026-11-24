"""Load and validate context packs: the open, versioned files that carry context facts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import GeoPoint
from .schema import ContextFact, GeoScope, ReviewStatus, Tier

PACK_SPEC_VERSION = "0.1"
_REQUIRED_PACK = ("spec_version", "id", "title", "license", "maintainers", "facts")
_REQUIRED_FACT = ("id", "claim", "topic", "vertical", "source")


class PackError(ValueError):
    pass


@dataclass(frozen=True)
class ContextPack:
    id: str
    title: str
    license: str
    maintainers: tuple[str, ...]
    facts: tuple[ContextFact, ...]
    description: str = ""


def _load_raw(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml  # optional dependency
        except ImportError as exc:  # pragma: no cover
            raise PackError("Install PyYAML to load YAML packs: pip install 'ace-engine[yaml]'") from exc
        return yaml.safe_load(text)
    return json.loads(text)


def _scope(raw: dict[str, Any] | None) -> GeoScope:
    if not raw:
        return GeoScope()
    center = raw.get("center")
    return GeoScope(
        countries=tuple(c.upper() for c in raw.get("countries", [])),
        admin_areas=tuple(raw.get("admin_areas", [])),
        center=GeoPoint(center["lat"], center["lon"]) if center else None,
        radius_km=raw.get("radius_km"),
        altitude_min_m=raw.get("altitude_min_m"),
        altitude_max_m=raw.get("altitude_max_m"),
    )


def parse_pack(raw: dict[str, Any]) -> ContextPack:
    missing = [k for k in _REQUIRED_PACK if k not in raw]
    if missing:
        raise PackError(f"Pack is missing fields: {', '.join(missing)}")
    if str(raw["spec_version"]) != PACK_SPEC_VERSION:
        raise PackError(f"Unsupported spec_version {raw['spec_version']!r}; expected {PACK_SPEC_VERSION}")
    tier = Tier(raw.get("tier", "open"))
    if tier is Tier.OPEN and raw["license"] != "CC-BY-4.0":
        raise PackError("Open tier packs must use the CC-BY-4.0 license")
    facts: list[ContextFact] = []
    seen: set[str] = set()
    for i, f in enumerate(raw["facts"]):
        missing = [k for k in _REQUIRED_FACT if not f.get(k)]
        if missing:
            raise PackError(f"Fact #{i} is missing fields: {', '.join(missing)}")
        fid = f"{raw['id']}/{f['id']}"
        if fid in seen:
            raise PackError(f"Duplicate fact id in pack: {f['id']}")
        seen.add(fid)
        status = ReviewStatus(f.get("review_status", "draft"))
        if status is not ReviewStatus.DRAFT and not f.get("reviewed_by"):
            raise PackError(f"Fact {f['id']} is marked {status.value} but names no reviewer")
        months = tuple(int(m) for m in f.get("months", []))
        if any(m < 1 or m > 12 for m in months):
            raise PackError(f"Fact {f['id']} has a month outside 1 to 12")
        facts.append(ContextFact(
            id=fid,
            claim=f["claim"].strip(),
            topic=f["topic"],
            vertical=f["vertical"],
            scope=_scope(f.get("scope")),
            subjects=tuple(f.get("subjects", [])),
            months=months,
            languages=tuple(f.get("languages", [])),
            source=f["source"],
            reviewed_by=f.get("reviewed_by"),
            review_status=status,
            tier=tier,
            expires=f.get("expires"),
            safety_critical=bool(f.get("safety_critical", False)),
        ))
    return ContextPack(
        id=raw["id"], title=raw["title"], license=raw["license"],
        maintainers=tuple(raw["maintainers"]), facts=tuple(facts),
        description=raw.get("description", ""),
    )


def load_pack(path: str | Path) -> ContextPack:
    return parse_pack(_load_raw(Path(path)))
