"""Back translation reports that help fluent speakers review a locale file.

`ace locales backcheck am` translates every Amharic string in the locale file back into English with a machine
translator and lines it up with the English ACE wrote. Rows whose back translation shares the fewest words with
the English come first, so a reviewer starts where meaning most likely drifted. Safety strings are marked.

A back translation is a pointer, not a verdict. It cannot pass a string: only a fluent speaker sets
`reviewed: true`, and safety phrases also need a clinician. The report writes nothing back to the locale file.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .. import i18n
from ..text import tokens
from . import Translator


@dataclass
class Row:
    path: str
    english: str
    text: str
    back: str
    overlap: float

    @property
    def safety(self) -> bool:
        return self.path.startswith("safety.")


def _flat(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set, frozenset)):
        return [str(v) for v in value]
    return []


def overlap(a: str, b: str) -> float:
    """Share of words two English texts have in common (Jaccard on folded tokens, placeholders dropped)."""
    ta = {t for t in tokens(a) if t not in {"numbers", "place", "n", "label"}}
    tb = {t for t in tokens(b) if t not in {"numbers", "place", "n", "label"}}
    return len(ta & tb) / len(ta | tb) if ta | tb else 1.0


def backcheck(code: str, translator: Translator) -> list[Row]:
    loc = i18n.locales().get(code)
    if loc is None:
        raise ValueError(f"No locale file for {code!r}")
    english = i18n.english_sources()
    pairs: list[tuple[str, str, str]] = []
    for path, value in loc.templates.items():
        en_items, items = _flat(english.get(path)), _flat(value)
        if len(en_items) == len(items):
            pairs.extend((path, e, t) for e, t in zip(en_items, items, strict=True))
        else:
            pairs.append((path, " / ".join(en_items), " / ".join(items)))
    backs = translator.translate([t for _, _, t in pairs], target="en", source=code) if pairs else []
    rows = [Row(p, e, t, b, overlap(e, b)) for (p, e, t), b in zip(pairs, backs, strict=True)]
    return sorted(rows, key=lambda r: (r.overlap, not r.safety, r.path))


def markdown(code: str, rows: list[Row]) -> str:
    name = i18n.locales()[code].name
    cell = lambda s: s.replace("|", "\\|").replace("\n", " ")  # noqa: E731
    lines = [f"# Back translation check: {name}", "",
             "Machine back translation into English, lowest word overlap first. A pointer for fluent reviewers, "
             "never a verdict: only a fluent speaker may set reviewed to true.", "",
             f"{len(rows)} strings; {sum(r.safety for r in rows)} on the safety rail.", "",
             "| Overlap | Safety | Key | ACE English | Locale text | Back translation |",
             "|--:|:--:|:--|:--|:--|:--|"]
    for r in rows:
        lines.append(f"| {r.overlap:.0%} | {'yes' if r.safety else ''} | `{r.path}` | {cell(r.english)} | "
                     f"{cell(r.text)} | {cell(r.back)} |")
    return "\n".join(lines) + "\n"
