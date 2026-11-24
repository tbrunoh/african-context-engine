"""Load and validate context packs: the open, versioned files that carry context facts.

A pack is a YAML or JSON file. The format is specified in
spec/context-pack.schema.json and explained in docs/context-packs.md.
Validation is strict on anything that affects safety or trust (sources,
review status, expiry, contacts) and gentle on everything else (warnings).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from ..models import GeoPoint
from .schema import Contact, ContextFact, GeoScope, Rendering, ReviewStatus, Tier

PACK_SPEC_VERSION = "1.0"
SUPPORTED_SPEC_VERSIONS = ("1.0",)
SHORT_MAX = 160
STALE_AFTER_DAYS = 365

_REQUIRED_PACK = ("spec_version", "id", "title", "license", "maintainers", "facts")
_REQUIRED_FACT = ("id", "claim", "topic", "vertical", "source")
_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_LANG = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
_NUMBER = re.compile(r"^\+?[0-9]{3,15}$")
KINDS = ("action", "sign", "info")
VERTICALS = ("agriculture", "health", "finance", "safety", "legal", "education", "climate")


class PackError(ValueError):
    """Raised when a pack fails validation. The message lists every error found."""


@dataclass(frozen=True)
class ContextPack:
    id: str
    title: str
    license: str
    maintainers: tuple[str, ...]
    facts: tuple[ContextFact, ...]
    description: str = ""
    country: str | None = None
    version: str = "0.0.0"
    path: str | None = None
    labels: dict[str, str] = field(default_factory=dict)  # short menu label per language
    order: int = 100                                      # menu position, lowest first

    def label(self, language: str | None) -> str:
        return self.labels.get(language or "", "") or self.labels.get("en", "") or self.title


@dataclass
class PackReport:
    path: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    pack: ContextPack | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_raw(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        import yaml

        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise PackError(f"{path}: a pack must be a mapping at the top level")
    return data


def _iso(value: Any) -> str | None:
    """YAML turns unquoted dates into date objects; normalise to ISO strings."""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _valid_date(value: str | None) -> bool:
    if value is None:
        return True
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _scope(raw: dict[str, Any] | None, default_country: str | None) -> GeoScope:
    raw = raw or {}
    center = raw.get("center")
    countries = raw.get("countries") or ([default_country] if default_country else [])
    return GeoScope(
        countries=tuple(str(c).upper() for c in countries),
        admin_areas=tuple(raw.get("admin_areas", [])),
        center=GeoPoint(float(center["lat"]), float(center["lon"])) if center else None,
        radius_km=raw.get("radius_km"),
        altitude_min_m=raw.get("altitude_min_m"),
        altitude_max_m=raw.get("altitude_max_m"),
    )


def validate_pack(raw: dict[str, Any], path: str = "<memory>", today: date | None = None) -> PackReport:
    """Check a raw pack and build it. Never raises; read the report."""
    today = today or date.today()
    report = PackReport(path=path)
    err, warn = report.errors.append, report.warnings.append

    missing = [k for k in _REQUIRED_PACK if k not in raw]
    if missing:
        err(f"pack is missing fields: {', '.join(missing)}")
        return report
    if str(raw["spec_version"]) not in SUPPORTED_SPEC_VERSIONS:
        err(f"unsupported spec_version {raw['spec_version']!r}; supported: {', '.join(SUPPORTED_SPEC_VERSIONS)}")
        return report
    pack_id = str(raw["id"])
    if not _ID.match(pack_id):
        err(f"pack id {pack_id!r} must be lowercase letters, digits and dashes")
    tier = Tier(raw.get("tier", "open"))
    if tier is Tier.OPEN and raw["license"] != "CC-BY-4.0":
        err("open tier packs must use the CC-BY-4.0 license")
    for lang, label in (raw.get("labels") or {}).items():
        if len(str(label)) > 24:
            warn(f"menu label for {lang} is longer than 24 characters and may not fit a USSD screen")
    if not raw["maintainers"]:
        err("a pack needs at least one maintainer")
    country = raw.get("country")
    pack_lang = raw.get("language", "en")
    if not isinstance(raw["facts"], list) or not raw["facts"]:
        err("facts must be a non empty list")
        return report

    facts: list[ContextFact] = []
    seen: set[str] = set()
    for i, f in enumerate(raw["facts"]):
        where = f"fact {f.get('id', f'#{i}')}"
        missing = [k for k in _REQUIRED_FACT if not f.get(k)]
        if missing:
            err(f"{where} is missing fields: {', '.join(missing)}")
            continue
        if not _ID.match(str(f["id"])):
            err(f"{where}: id must be lowercase letters, digits and dashes")
        if f["id"] in seen:
            err(f"{where}: duplicate id")
        seen.add(f["id"])
        if f["vertical"] not in VERTICALS:
            err(f"{where}: vertical must be one of {', '.join(VERTICALS)}")

        if f.get("kind", "info") not in KINDS:
            err(f"{where}: kind must be one of {', '.join(KINDS)}")
        try:
            status = ReviewStatus(f.get("review_status", "draft"))
        except ValueError:
            err(f"{where}: unknown review_status {f.get('review_status')!r}")
            continue
        checked_on, expires = _iso(f.get("checked_on")), _iso(f.get("expires"))
        if not _valid_date(checked_on):
            err(f"{where}: checked_on must be an ISO date")
            checked_on = None
        if not _valid_date(expires):
            err(f"{where}: expires must be an ISO date")
            expires = None
        if status.rank >= ReviewStatus.SOURCED.rank:
            if not f.get("source_url"):
                err(f"{where}: {status.value} facts need a source_url")
            if not checked_on:
                err(f"{where}: {status.value} facts need a checked_on date")
        if status.rank >= ReviewStatus.EXPERT_REVIEWED.rank and not f.get("reviewed_by"):
            err(f"{where}: {status.value} facts must name a reviewer in reviewed_by")
        if checked_on and (today - date.fromisoformat(checked_on)).days > STALE_AFTER_DAYS:
            warn(f"{where}: last checked {checked_on}, more than a year ago")
        if expires and date.fromisoformat(expires) < today:
            warn(f"{where}: expired on {expires} and will not be served")

        short = f.get("short")
        if short and len(short) > SHORT_MAX:
            err(f"{where}: short is {len(short)} characters; the limit is {SHORT_MAX}")
        months = tuple(int(m) for m in f.get("months", []))
        if any(m < 1 or m > 12 for m in months):
            err(f"{where}: months must be between 1 and 12")

        translations: dict[str, Rendering] = {}
        for lang, t in (f.get("translations") or {}).items():
            if not _LANG.match(lang):
                err(f"{where}: translation language {lang!r} is not a BCP 47 tag")
                continue
            if not t.get("claim"):
                err(f"{where}: translation {lang} needs a claim")
                continue
            if t.get("short") and len(t["short"]) > SHORT_MAX:
                err(f"{where}: {lang} short is {len(t['short'])} characters; the limit is {SHORT_MAX}")
            reviewed = bool(t.get("reviewed", False))
            if not reviewed:
                warn(f"{where}: {lang} translation awaits review by a fluent speaker")
            translations[lang] = Rendering(t["claim"].strip(), (t.get("short") or None), reviewed)

        contacts: list[Contact] = []
        for c in f.get("contacts") or []:
            number = str(c.get("number", "")).replace(" ", "")
            if not _NUMBER.match(number):
                err(f"{where}: contact number {c.get('number')!r} must be digits, optionally with a leading +")
                continue
            contacts.append(Contact(label=c.get("label", number), number=number,
                                    queues=tuple(c.get("queues", [])), free=c.get("free"),
                                    hours=c.get("hours")))
        if f.get("safety_critical") and not (contacts or f.get("refer_to")):
            warn(f"{where}: safety critical facts should list contacts people can reach")

        facts.append(ContextFact(
            id=f"{pack_id}/{f['id']}",
            claim=" ".join(str(f["claim"]).split()),
            topic=str(f["topic"]),
            vertical=str(f["vertical"]),
            kind=str(f.get("kind", "info")),
            scope=_scope(f.get("scope"), country),
            subjects=tuple(str(s).lower() for s in f.get("subjects", [])),
            keywords=tuple(str(k).lower() for k in f.get("keywords", [])),
            months=months,
            short=" ".join(short.split()) if short else None,
            translations=translations,
            language=f.get("language", pack_lang),
            contacts=tuple(contacts),
            source=str(f["source"]),
            source_url=f.get("source_url"),
            checked_on=checked_on,
            reviewed_by=f.get("reviewed_by"),
            review_status=status,
            tier=tier,
            expires=expires,
            safety_critical=bool(f.get("safety_critical", False)),
            pack_id=pack_id,
        ))

    if not report.errors:
        report.pack = ContextPack(
            id=pack_id, title=str(raw["title"]), license=str(raw["license"]),
            maintainers=tuple(raw["maintainers"]), facts=tuple(facts),
            description=str(raw.get("description", "")).strip(), country=country,
            version=str(raw.get("version", "0.0.0")), path=path,
            labels={str(k): str(v) for k, v in (raw.get("labels") or {}).items()},
            order=int(raw.get("order", 100)),
        )
    return report


def parse_pack(raw: dict[str, Any], path: str = "<memory>") -> ContextPack:
    report = validate_pack(raw, path)
    if not report.ok:
        raise PackError(f"{path}: " + "; ".join(report.errors))
    assert report.pack is not None
    return report.pack


def load_pack(path: str | Path) -> ContextPack:
    p = Path(path)
    return parse_pack(_load_raw(p), str(p))


def check_file(path: str | Path) -> PackReport:
    p = Path(path)
    try:
        return validate_pack(_load_raw(p), str(p))
    except (PackError, ValueError, OSError) as exc:
        return PackReport(path=str(p), errors=[str(exc)])


def pack_files(root: str | Path) -> list[Path]:
    """Every pack file under a directory, skipping templates."""
    root = Path(root)
    if root.is_file():
        return [root]
    found = [p for ext in ("*.yaml", "*.yml", "*.json") for p in root.rglob(ext)]
    return sorted(p for p in found if not p.name.startswith("_"))


def load_packs(*roots: str | Path) -> list[ContextPack]:
    """Load every pack under the given files or directories. Raises on the first invalid pack."""
    packs: list[ContextPack] = []
    ids: set[str] = set()
    for root in roots:
        for path in pack_files(root):
            pack = load_pack(path)
            if pack.id in ids:
                raise PackError(f"{path}: pack id {pack.id!r} is already loaded")
            ids.add(pack.id)
            packs.append(pack)
    return packs
