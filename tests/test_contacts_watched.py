"""Every number an emergency fact says out loud must be in its contacts, so the weekly watcher rechecks it."""
from __future__ import annotations

import re
from pathlib import Path

from ace_engine.context import load_packs

ROOT = Path(__file__).resolve().parents[1]
# Runs of two or more digits, allowing spaced groups such as 0800 3222 911. Percentages, decimals and years are skipped.
NUMBER = re.compile(r"(?<![\d.,%])(\d{2,}(?: \d{3,})*)(?!\s?%|[\d.,]\d)")
YEAR = re.compile(r"(19|20)\d\d")


def numbers_in(text: str) -> set[str]:
    return {m.replace(" ", "") for m in NUMBER.findall(text or "") if not YEAR.fullmatch(m)}


def test_pattern_finds_spaced_and_short_numbers():
    assert numbers_in("NetOne users can call 114, and the landline is 0800 3222 911.") == {"114", "08003222911"}
    assert numbers_in("Call 17 or 18.") == {"17", "18"}
    assert numbers_in("98% of calls, version 2.1, in 2026") == set()


def test_every_number_in_an_emergency_fact_is_watched():
    missing = []
    for pack in load_packs(ROOT / "context_packs"):
        for fact in pack.facts:
            if fact.topic != "emergency_contacts":
                continue
            watched = {c.number.replace(" ", "") for c in fact.contacts}
            texts = [fact.claim, fact.short or ""]
            for rendering in fact.translations.values():
                texts += [rendering.claim, rendering.short or ""]
            for text in texts:
                missing += [(fact.id, n) for n in numbers_in(text) - watched]
    assert not missing, f"numbers said to callers but not watched: {sorted(set(missing))}"
