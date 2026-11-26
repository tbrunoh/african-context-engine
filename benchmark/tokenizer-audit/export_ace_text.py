"""Rebuild data/ace_parallel.jsonl from an ACE checkout.

    python export_ace_text.py --ace /path/to/african-context-engine --out data/ace_parallel.jsonl

Service messages are ACE's reply templates in src/ace_engine, one row per template that is a full translation in all
eight languages. Facts are the claims in context_packs/africa that carry a rendering in all eight languages.
Placeholders such as {numbers} are removed, because their values are filled in at reply time.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path

import yaml

LANGS = ("en", "sw", "fr", "pt", "ar", "am", "om", "so")
MODULES = ("commands", "safety", "scam", "services.base", "services.facility", "services.pests", "services.pregnancy",
           "services.prices", "services.rain", "services.warnings")
SERVICE_SOURCE = "ACE service templates, src/ace_engine (Apache-2.0)"
PLACEHOLDER = re.compile(r"\{[^{}]*\}")


def is_lang_map(value: object) -> bool:
    return isinstance(value, dict) and set(LANGS) <= set(value) and all(isinstance(value[k], str) for k in LANGS)


def full_translation(text: dict[str, str]) -> bool:
    """A real translation: at least four distinct renderings, and English that contains letters.

    This drops templates that are the same in most languages, such as a unit (km) or a language's own name.
    """
    return len(set(text.values())) >= 4 and any(ch.isalpha() for ch in text["en"])


def service_rows() -> list[dict]:
    rows = []
    for mod_name in MODULES:
        mod = importlib.import_module(f"ace_engine.{mod_name}")
        for attr in sorted(vars(mod)):
            if not attr.isupper():
                continue
            value = getattr(mod, attr)
            found = []
            if is_lang_map(value):
                found.append((f"{mod_name}.{attr}", value))
            elif isinstance(value, dict):
                found += [(f"{mod_name}.{attr}.{getattr(k, 'name', k)}", v) for k, v in value.items() if is_lang_map(v)]
            for row_id, text in found:
                text = {k: " ".join(PLACEHOLDER.sub("", text[k]).split()) for k in LANGS}
                if row_id == "commands.LANGUAGE_NAMES" or not full_translation(text):
                    continue
                rows.append({"id": row_id, "kind": "service_message", "source": SERVICE_SOURCE,
                             "license": "Apache-2.0", "reviewed": False, "text": text})
    return rows


def fact_rows(ace: Path) -> list[dict]:
    rows = []
    for pack_file in sorted((ace / "context_packs" / "africa").glob("*.yaml")):
        pack = yaml.safe_load(pack_file.read_text(encoding="utf-8"))
        for fact in pack.get("facts", []):
            tr = fact.get("translations", {})
            if not all(k in tr and tr[k].get("claim") for k in LANGS[1:]):
                continue
            text = {"en": fact["claim"], **{k: tr[k]["claim"] for k in LANGS[1:]}}
            rows.append({"id": f"{pack['id']}/{fact['id']}", "kind": "fact", "source": fact["source"],
                         "source_url": fact["source_url"], "license": pack["license"], "reviewed": False,
                         "text": {k: " ".join(text[k].split()) for k in LANGS}})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ace", required=True, type=Path, help="path to an ACE checkout")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    sys.path.insert(0, str(args.ace / "src"))
    rows = sorted(service_rows(), key=lambda r: r["id"]) + fact_rows(args.ace)
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds = {k: sum(r["kind"] == k for r in rows) for k in ("service_message", "fact")}
    print(f"{len(rows)} rows: {kinds['service_message']} service messages, {kinds['fact']} facts")


if __name__ == "__main__":
    main()
