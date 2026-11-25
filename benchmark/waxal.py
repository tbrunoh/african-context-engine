"""Test ACE's language tools on real African speech text from WAXAL.

    python -m benchmark.waxal                 fetch (or reuse) the text and write benchmark/results/waxal.*
    python -m benchmark.waxal --limit 200     fewer sentences per set, for a quick look

WAXAL (Google Research and African partners, 2026) publishes human transcriptions of natural speech and the
scripts read for synthetic voices. ACE uses the text, never the audio, to answer three questions on sentences no
ACE author wrote:

  * language: does ACE recognise its own languages (Amharic, Afaan Oromo, Swahili) in real speech, and does it
    stay quiet on languages it does not speak instead of answering a Luganda speaker in Swahili?
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
from ace_engine.safety import EscalationPolicy  # noqa: E402
from ace_engine.text import guess_language  # noqa: E402

DATASET = "google/WaxalNLP"
REVISION_NOTE = "dataset card revision 5f4d8ca, updated 1 September 2026"
ROWS_API = "https://datasets-server.huggingface.co/rows"
CACHE = Path(__file__).parent / ".waxal_cache"
OUT = Path(__file__).parent / "results"
NO_CLAIM = "none"

# WAXAL set -> (language, the ACE language it should be read as, or None when ACE does not speak it).
SETS: dict[str, tuple[str, str | None]] = {
    "amh_asr": ("Amharic", "am"),
    "orm_asr": ("Afaan Oromo", "om"),
    "swa_tts": ("Swahili", "sw"),
    "tir_asr": ("Tigrinya", None),
    "sid_asr": ("Sidama", None),
    "wal_asr": ("Wolaytta", None),
    "kik_tts": ("Kikuyu", None),
    "luo_tts": ("Dholuo", None),
    "lug_asr": ("Luganda", None),
    "ach_asr": ("Acholi", None),
    "nyn_asr": ("Runyankole", None),
    "sog_asr": ("Lusoga", None),
    "mas_asr": ("Masaaba", None),
    "lin_asr": ("Lingala", None),
    "sna_asr": ("Shona", None),
    "mlg_asr": ("Malagasy", None),
    "ful_asr": ("Fula", None),
    "hau_tts": ("Hausa", None),
    "yor_tts": ("Yoruba", None),
    "ibo_tts": ("Igbo", None),
    "pcm_tts": ("Nigerian Pidgin", None),
    "aka_asr": ("Akan", None),
    "twi_tts": ("Twi", None),
    "fat_tts": ("Fante", None),
    "ewe_asr": ("Ewe", None),
    "dag_asr": ("Dagbani", None),
    "dga_asr": ("Dagaare", None),
    "kpo_asr": ("Ikposo", None),
    "bau_tts": ("Baoule", None),
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
    for config, (name, expected) in SETS.items():
        texts = fetch(config, limit)
        if not texts:
            report["sets"][config] = {"language": name, "error": "no text fetched"}
            continue
        guesses: dict[str, int] = {}
        for text in texts:
            code = guess_language(text, default=NO_CLAIM)
            guesses[code] = guesses.get(code, 0) + 1
        alarms = [policy.check(t) for t in texts]
        routed = [services.detect(t) for t in texts]
        n = len(texts)
        entry = {
            "language": name,
            "ace_language": expected,
            "sentences": n,
            "guesses": dict(sorted(guesses.items(), key=lambda kv: -kv[1])),
            "false_alarms": sum(a.escalate for a in alarms),
            "false_alarm_queues": _count(a.queue for a in alarms if a.escalate),
            "service_routes": sum(r is not None for r in routed),
            "service_route_ids": _count(r for r in routed if r),
        }
        if expected:
            entry["recognised"] = guesses.get(expected, 0) / n
        else:
            entry["claimed_as_ace_language"] = (n - guesses.get(NO_CLAIM, 0)) / n
        report["sets"][config] = entry
    return report


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
        "and voice scripts for TTS sets. Counts only; no WAXAL text is stored in this repository.",
        "",
        "## ACE languages: recognised in real speech",
        "",
        "| Language | Sentences | Recognised | Other guesses | False alarms | Routed to a service |",
        "|:--|--:|--:|:--|--:|--:|",
    ]
    for r in own:
        others = ", ".join(f"{k} {v}" for k, v in r["guesses"].items() if k != r["ace_language"]) or "none"
        lines.append(f"| {r['language']} | {r['sentences']} | {r['recognised']:.1%} | {others} | "
                     f"{r['false_alarms']} | {r['service_routes']} |")
    lines += [
        "",
        "## Languages ACE does not speak: how often ACE claims them as its own",
        "",
        "| Language | Sentences | Claimed | Claimed as | False alarms | Routed to a service |",
        "|:--|--:|--:|:--|--:|--:|",
    ]
    for r in other:
        claimed = ", ".join(f"{k} {v}" for k, v in r["guesses"].items() if k != NO_CLAIM) or "none"
        lines.append(f"| {r['language']} | {r['sentences']} | {r['claimed_as_ace_language']:.1%} | {claimed} | "
                     f"{r['false_alarms']} | {r['service_routes']} |")
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
