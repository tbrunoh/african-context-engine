"""Check ACE's language identification on FLORES-200 devtest, which nothing in ACE was built or tuned on.

For every ACE language and every country that offers it or reads it from across a border, each devtest sentence is
read as a message from that country. The check counts sentences ACE would turn away as a language it does not speak,
and, in countries whose languages do not include English, sentences of a country language read as English.

    python benchmark/langid/build.py fetch   # downloads FLORES-200 once, checked against its SHA-256
    python benchmark/langid/devtest.py

Writes benchmark/results/langid-devtest.md and .json. Counts only; no FLORES-200 text is stored.
"""

from __future__ import annotations

import json
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import build  # noqa: E402

from ace_engine import langid  # noqa: E402
from ace_engine.countries import COUNTRIES, readable  # noqa: E402

RESULTS = ROOT / "benchmark" / "results"


def sentences(tf: tarfile.TarFile, files: list[str]) -> list[str]:
    out: list[str] = []
    for name in files:
        member = tf.extractfile(f"./flores200_dataset/devtest/{name}.devtest")
        if member is not None:
            out += member.read().decode("utf-8").splitlines()
    return out


def evaluate() -> dict:
    tar = build.CACHE / "flores200_dataset.tar.gz"
    if not tar.exists():
        sys.exit("FLORES-200 is not downloaded yet: run python benchmark/langid/build.py first.")
    checked = turned_away = read_as_english = english_checked = 0
    away_by: dict[str, int] = {}
    english_by: dict[str, int] = {}
    with tarfile.open(tar) as tf:
        for code, (files, _) in sorted(build.ACE.items()):
            texts = sentences(tf, files)
            for cc, country in sorted(COUNTRIES.items()):
                langs = readable(cc)
                if code not in langs:
                    continue
                also = langs[len(country.languages):]
                away = sum(langid.unread_language(t, country.languages, also=also) is not None for t in texts)
                checked += len(texts)
                turned_away += away
                if away:
                    away_by[f"{code} {cc}"] = away
                if code != "en" and code in country.languages and "en" not in country.languages:
                    english = sum(langid.detect_language(t, country.languages[0], country.languages, also) == "en"
                                  for t in texts)
                    english_checked += len(texts)
                    read_as_english += english
                    if english:
                        english_by[f"{code} {cc}"] = english
    return {"split": "FLORES-200 devtest", "flores_sha256": build.FLORES_SHA256, "checked": checked,
            "turned_away": turned_away, "turned_away_by": away_by, "english_checked": english_checked,
            "read_as_english": read_as_english, "read_as_english_by": english_by}


def write(report: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "langid-devtest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# ACE language identification on FLORES-200 devtest", "",
        "Each devtest sentence of each ACE language is read as a message from every country that offers the language "
        "or reads it from across a border. Nothing in ACE was built or tuned on this split. Counts only.", "",
        f"- Sentence checks: {report['checked']:,}",
        f"- Turned away as a language ACE does not speak: {report['turned_away']:,}"
        + (f" ({', '.join(f'{k} {v}' for k, v in report['turned_away_by'].items())})" if report["turned_away_by"]
           else ""),
        f"- Country language sentences read as English, where English is not offered: {report['read_as_english']:,} "
        f"of {report['english_checked']:,}"
        + (f" ({', '.join(f'{k} {v}' for k, v in report['read_as_english_by'].items())})"
           if report["read_as_english_by"] else ""),
        "",
    ]
    (RESULTS / "langid-devtest.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    result = evaluate()
    write(result)
    print((RESULTS / "langid-devtest.md").read_text(encoding="utf-8"))
