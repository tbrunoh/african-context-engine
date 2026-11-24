from __future__ import annotations

from pathlib import Path

import pytest

from ace_engine.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "context_packs"


@pytest.fixture(scope="session")
def packs_dir() -> Path:
    return PACKS


@pytest.fixture()
def engine() -> Engine:
    """A fresh engine per test, so profiles and tips never leak between tests."""
    return Engine.from_packs(PACKS)


def minimal_pack(**overrides):
    """A valid one fact pack that tests mutate to check each validation rule."""
    fact = {
        "id": "f1", "claim": "Water maize in the morning.", "topic": "irrigation", "vertical": "agriculture",
        "source": "Test source", "source_url": "https://example.org/source", "checked_on": "2026-11-01",
        "review_status": "sourced",
    }
    fact.update(overrides.pop("fact", {}))
    pack = {"spec_version": "1.0", "id": "test-pack", "title": "Test pack", "license": "CC-BY-4.0",
            "maintainers": ["Tester"], "country": "KE", "facts": [fact]}
    pack.update(overrides)
    return pack
