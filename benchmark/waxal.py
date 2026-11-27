"""Test ACE's language tools on real African speech text from WAXAL.

    python -m benchmark.waxal                 fetch (or reuse) the text and write benchmark/results/waxal.*
    python -m benchmark.waxal --limit 200     fewer sentences per set, for a quick look

WAXAL (Google Research and African partners, 2026) publishes human transcriptions of natural speech and the
scripts read for synthetic voices. ACE uses the text, never the audio, to answer three questions on sentences no
ACE author wrote:

  * language: does ACE recognise its own languages in real speech, and does it stay quiet on languages it does
    not speak instead of answering a Gikuyu speaker in Swahili?
  * false alarms: how often does ordinary speech set off the safety rail?
  * services: how often does ordinary speech get routed to a decision service it was not asking for?

The text is fetched at run time from the Hugging Face dataset viewer into benchmark/.waxal_cache, which git
ignores. Nothing from WAXAL is committed: the results hold counts, never sentences. Most WAXAL sets are
CC BY-SA 4.0 and the University of Ghana sets are CC BY 4.0; see snapshots/register.yaml.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ace_engine import services  # noqa: E402
from ace_engine.countries import COUNTRIES, readable  # noqa: E402
from ace_engine.langid import detect_language, unread_language  # noqa: E402
from ace_engine.safety import EscalationPolicy  # noqa: E402
from ace_engine.text import tokens  # noqa: E402

DATASET = "google/WaxalNLP"
REVISION_NOTE = "dataset card revision 5f4d8ca, updated 1 September 2026"
ROWS_API = "https://datasets-server.huggingface.co/rows"
CACHE = Path(__file__).parent / ".waxal_cache"
OUT = Path(__file__).parent / "results"
NO_CLAIM = "none"
UNREAD = "not read"  # ACE says it does not read the language yet and names the languages it reads there

# WAXAL set -> (language, the ACE language it should be read as or None when ACE does not speak it, and the country
# whose callers ACE would read it for, or None when ACE covers no country where it is spoken). ACE guesses a
# language only among the caller's country languages, so the check does the same.
SETS: dict[str, tuple[str, str | None, str | None]] = {
    "amh_asr": ("Amharic", "am", "ET"),
    "orm_asr": ("Afaan Oromo", "om", "ET"),
    "swa_tts": ("Swahili", "sw", "KE"),
    "tir_asr": ("Tigrinya", "ti", "ET"),
    "sid_asr": ("Sidama", None, "ET"),
    "wal_asr": ("Wolaytta", None, "ET"),
    "kik_tts": ("Gikuyu", None, "KE"),
    "luo_tts": ("Dholuo", None, "KE"),
    "lug_asr": ("Luganda", "lg", "UG"),
    "ach_asr": ("Acholi", None, "UG"),
    "nyn_asr": ("Runyankole", None, "UG"),
    "sog_asr": ("Lusoga", None, "UG"),
    "mas_asr": ("Masaaba", None, "UG"),
    "lin_asr": ("Lingala", "ln", "CD"),
    "sna_asr": ("Shona", "sn", "ZW"),
    "mlg_asr": ("Malagasy", None, None),
    "ful_asr": ("Fula (ACE writes Pular)", "fuf", "GN"),
    "hau_tts": ("Hausa", "ha", "NG"),
    "yor_tts": ("Yoruba", "yo", "NG"),
    "ibo_tts": ("Igbo", "ig", "NG"),
    "pcm_tts": ("Nigerian Pidgin", "pcm", "NG"),
    "aka_asr": ("Akan", "ak", "GH"),
    "twi_tts": ("Twi", "ak", "GH"),
    "fat_tts": ("Fante (Akan)", "ak", "GH"),
    "ewe_asr": ("Ewe", "ee", "GH"),
    "dag_asr": ("Dagbani", None, "GH"),
    "dga_asr": ("Dagaare", None, "GH"),
    "kpo_asr": ("Ikposo", None, "TG"),
    "bau_tts": ("Baoule", None, "CI"),
}


def fetch(config: str, limit: int, split: str = "test") -> list[str]:
    """Up to limit sentences of one WAXAL set, cached on disk. Audio columns are ignored."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{config}-{split}.json"
    if path.exists():
        rows = json.loads(path.read_text(encoding="utf-8"))
        if len(rows) >= limit or not rows or rows[-1] == "":
            return [r for r in rows if r][:limit]
    texts: list[str] = []
    offset = 0
    while len(texts) < limit:
        query = urllib.parse.urlencode({"dataset": DATASET, "config": config, "split": split,
                                        "offset": offset, "length": 100})
        data = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(f"{ROWS_API}?{query}", timeout=60) as response:
                    data = json.load(response)
                break
            except OSError:
                time.sleep(3 * (attempt + 1))
        if not data or not data.get("rows"):
            break
        for item in data["rows"]:
            row = item["row"]
            text = (row.get("transcription") or row.get("text") or "").strip()
            if text:
                texts.append(text)
        offset += 100
        if offset >= data.get("num_rows_total", 0):
            texts.append("")  # marks a set read to the end
            break
    path.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    return [t for t in texts if t][:limit]


def evaluate(limit: int) -> dict:
    policy = EscalationPolicy()
    report: dict = {"dataset": DATASET, "source": REVISION_NOTE, "limit": limit, "sets": {}}
    for config, (name, expected, country) in SETS.items():
        texts = fetch(config, limit)
        if not texts:
            report["sets"][config] = {"language": name, "error": "no text fetched"}
            continue
        guesses: dict[str, int] = {}
        offered = COUNTRIES[country].languages if country else None
        also = (readable(country) or ())[len(offered or ()):]
        places = _place_words(country)
        for text in texts:
            if unread_language(text, offered, places, also):
                code = UNREAD
            else:
                code = detect_language(text, default=NO_CLAIM, allowed=offered, also=also, ignore=places)
            guesses[code] = guesses.get(code, 0) + 1
        alarms = [policy.check(t) for t in texts]
        routed = [services.detect(t) for t in texts]
        n = len(texts)
        entry = {
            "language": name,
            "ace_language": expected,
            "country": country,
            "sentences": n,
            "guesses": dict(sorted(guesses.items(), key=lambda kv: -kv[1])),
            "false_alarms": sum(a.escalate for a in alarms),
            "false_alarm_queues": _count(a.queue for a in alarms if a.escalate),
            "service_routes": sum(r is not None for r in routed),
            "service_route_ids": _count(r for r in routed if r),
        }
        entry["not_read"] = guesses.get(UNREAD, 0) / n
        if expected:
            entry["recognised"] = guesses.get(expected, 0) / n
        else:
            # A sentence with no language evidence at all is answered in the country's first language, so it is
            # claimed too: every sentence ACE does not turn away gets an answer in one of its languages.
            entry["claimed_as_ace_language"] = (n - guesses.get(UNREAD, 0)) / n
        report["sets"][config] = entry
    return report


def _place_words(country: str | None) -> frozenset[str]:
    """The caller's country place names, folded, as the engine removes them before judging a language."""
    if not country:
        return frozenset()
    from ace_engine.places import Gazetteer
    from ace_engine.snapshots import SnapshotStore, default_root

    words: set[str] = set()
    for rec in Gazetteer(SnapshotStore(default_root())).areas(country):
        for name in [rec.get("name", ""), *rec.get("aliases", [])]:
            words.update(t for t in tokens(name) if len(t) > 3)
    return frozenset(words)


def _count(items) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        out[item] = out.get(item, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def markdown(report: dict) -> str:
    rows = [v for v in report["sets"].values() if "error" not in v]
    own = sorted((r for r in rows if r["ace_language"]), key=lambda r: -r["recognised"])
    other = sorted((r for r in rows if not r["ace_language"]), key=lambda r: -r["claimed_as_ace_language"])
    lines = [
        "# ACE on WAXAL speech text",
        "",
        f"Real sentences from [WAXAL](https://huggingface.co/datasets/google/WaxalNLP) ({report['source']}): "
        f"up to {report['limit']} per set from each test split, transcriptions of natural speech for ASR sets "
        "and voice scripts for TTS sets. Each set is read as a message from a country where the language is spoken, "
        "so ACE guesses only among that country's languages, as it does for a real caller. A sentence ACE judges "
        "to be in a language it does not speak is not read: ACE says so and names the languages it reads in that "
        "country (see docs/languages.md). Counts only; no WAXAL text is stored in this repository, and none was "
        "used to build ACE's language profiles.",
        "",
        "## ACE languages: recognised in real speech",
        "",
        "| Language | Read as from | Sentences | Recognised | Not read | Other guesses | False alarms | "
        "Routed to a service |",
        "|:--|:--|--:|--:|--:|:--|--:|--:|",
    ]
    for r in own:
        others = ", ".join(f"{'country default' if k == NO_CLAIM else k} {v}" for k, v in r["guesses"].items()
                           if k not in (r["ace_language"], UNREAD))
        where = r.get("country") or "any country"
        lines.append(f"| {r['language']} | {where} | {r['sentences']} | {r['recognised']:.1%} | {r['not_read']:.1%} | "
                     f"{others or 'none'} | {r['false_alarms']} | {r['service_routes']} |")
    lines += [
        "",
        "## Languages ACE does not speak: told so, or answered in one of ACE's languages",
        "",
        "| Language | Read as from | Sentences | Not read | Answered | Answered in | False alarms | Routed to a service |",
        "|:--|:--|--:|--:|--:|:--|--:|--:|",
    ]
    for r in other:
        claimed = ", ".join(f"{'country default' if k == NO_CLAIM else k} {v}" for k, v in r["guesses"].items()
                            if k != UNREAD) or "none"
        where = r.get("country") or "any country"
        lines.append(f"| {r['language']} | {where} | {r['sentences']} | {r['not_read']:.1%} | "
                     f"{r['claimed_as_ace_language']:.1%} | {claimed} | {r['false_alarms']} | {r['service_routes']} |")
    if other:
        claimed_avg = sum(r["claimed_as_ace_language"] for r in other) / len(other)
        unread_avg = sum(r["not_read"] for r in other) / len(other)
        own_unread = max((r["not_read"] for r in own), default=0.0)
        lines += ["", f"Across {len(other)} languages ACE does not speak, each counted once, ACE tells the writer it "
                  f"does not read the language in {unread_avg:.1%} of sentences on average, and answers "
                  f"{claimed_avg:.1%} in one of its own languages, most often a close neighbour. In ACE's own "
                  f"languages, at most {own_unread:.1%} of a language's sentences are not read."]
    total = sum(r["sentences"] for r in rows)
    alarms = sum(r["false_alarms"] for r in rows)
    lines += ["", f"Across {total:,} sentences in {len(rows)} sets, the safety rail fired {alarms} times "
              f"({alarms / total:.2%}). Each firing is listed in waxal.json by queue for review.", ""]
    skipped = [v["language"] for v in report["sets"].values() if "error" in v]
    if skipped:
        lines += [f"Not measured: {', '.join(skipped)}. The dataset viewer could not serve their text on this run; "
                  "load them with the datasets library instead.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=600)
    args = parser.parse_args()
    report = evaluate(args.limit)
    OUT.mkdir(exist_ok=True)
    (OUT / "waxal.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "waxal.md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
