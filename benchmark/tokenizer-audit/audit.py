"""ACE tokenizer audit: how many tokens African languages cost against English, on any tokenizer.

Six commands:

    python audit.py fetch                  download FLORES-200 and the tokenizers, verifying every checksum
    python audit.py run                    measure every tokenizer on FLORES-200 dev and on ACE's text
    python audit.py corrections            how native speaker corrections to FLORES move each ratio
    python audit.py equivalence            confirm the tokenizers that count exactly like one measured here
    python audit.py summary                derive every headline figure into results/summary.json
    python audit.py check --tokenizer F    score one local tokenizer offline against a ceiling and an
                                           English budget, with nothing sent anywhere

The measure is the same-text ratio: a tokenizer's total tokens for a language divided by its total for the
aligned English text. Each tokenizer is compared with its own English count, and the absolute English
counts are reported beside it so that no tokenizer can pass by spending more on English.

Author: Tom Bruno (https://tbrunoh.github.io/ace/). Code licensed Apache-2.0.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import tarfile
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(CACHE / "tiktoken"))  # keep tiktoken's files with the rest, for offline use
RESULTS = ROOT / "results"
REGISTRY = json.loads((ROOT / "tokenizers.json").read_text(encoding="utf-8"))

FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
FLORES_SHA256 = "b8b0b76783024b85797e5cc75064eb83fc5288b41e9654dabc7be6ae944011f6"

# Native speaker corrections to FLORES for Hausa, Northern Sotho, Xitsonga and isiZulu (Abdulmumin et al., WMT 2024),
# pinned to one commit of https://github.com/dsfsi/flores-fix-4-africa. The repository corrects dev for three of the
# four languages and devtest for all four.
# Tokenizers that the audit shows to be equivalent to one it measures, pinned for `audit.py equivalence`.
EQUIVALENTS = [
    {"name": "DeepSeek-V3", "same_as": "DeepSeek-V4", "file": "deepseek-ai_DeepSeek-V3.json",
     "url": "https://huggingface.co/deepseek-ai/DeepSeek-V3/resolve/e815299b0bcbac849fa540c768ef21845365c9eb/tokenizer.json",
     "sha256": "621ac2e32d0dba658404412318818aaa8ce8cda492e59830109d8da6b517fb41"},
    {"name": "Gemma 3", "same_as": "Gemma 4", "file": "unsloth_gemma-3-1b-it.json",
     "url": "https://huggingface.co/unsloth/gemma-3-1b-it/resolve/5b11413a10db4e486ef16a20101fd028f8f2499c/tokenizer.json",
     "sha256": "4667f2089529e8e7657cfb6d1c19910ae71ff5f28aa7ab2ff2763330affad795"},
    {"name": "Nemotron 3 Nano", "same_as": "Mistral Tekken", "file": "nvidia_NVIDIA-Nemotron-3-Nano-30B-A3B-BF16.json",
     "url": "https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/resolve/"
            "bf77c3174f68ad409e1c2aa60daeb46e32d1c606/tokenizer.json",
     "sha256": "c6021eb6847e682f89aa52d5eb6e8c7d902a23acfc8137e25211cf84828f1592"},
]

CORRECTIONS_URL = "https://raw.githubusercontent.com/dsfsi/flores-fix-4-africa/431b57cab27acc97627842ea0299fd344acb2c82"
CORRECTIONS = {
    ("dev", "hau_Latn"): "8c7feb127de674ade06df6f45108ed47197d21b1f12533967b7263682f05f7e6",
    ("dev", "nso_Latn"): "d369a769d6154b0cc6c8368cd8a9fb7b21984fea880dbf7d54f0c0ddd14067a9",
    ("dev", "zul_Latn"): "ccc00c1521bf9c2f95edb5afee4f896c958c15b36acdae7ec6ee181f6b1a30f1",
    ("devtest", "hau_Latn"): "c2aa048677ebb9cd015eb51403592932ef42192b0c6e97e5c0793bec13b4d1be",
    ("devtest", "nso_Latn"): "4bb651ca477070c6298d4571626459e2a3704cb844405a80cde9d6074e596396",
    ("devtest", "tso_Latn"): "121e3e4aa4b3ee9045d225c9461289b5670f70c10f3bf71a01812bed9b758b54",
    ("devtest", "zul_Latn"): "8aaed311070178b78a026d56fcfe9d05eee988916a08e1094fcc928ba71fbae6",
}

# FLORES-200 languages spoken in Africa, with the code ACE uses where ACE has a locale.
AFRICAN = {
    "afr_Latn": "Afrikaans", "aka_Latn": "Akan", "amh_Ethi": "Amharic", "arb_Arab": "Arabic (Standard)",
    "ary_Arab": "Moroccan Arabic", "arz_Arab": "Egyptian Arabic", "aeb_Arab": "Tunisian Arabic",
    "bam_Latn": "Bambara", "bem_Latn": "Bemba", "cjk_Latn": "Chokwe", "dik_Latn": "Dinka", "dyu_Latn": "Dyula",
    "ewe_Latn": "Ewe", "fon_Latn": "Fon", "fra_Latn": "French", "fuv_Latn": "Fulfulde (Nigerian)",
    "gaz_Latn": "Oromo", "hau_Latn": "Hausa", "ibo_Latn": "Igbo", "kab_Latn": "Kabyle", "kam_Latn": "Kamba",
    "kbp_Latn": "Kabiye", "kea_Latn": "Kabuverdianu", "kik_Latn": "Kikuyu", "kin_Latn": "Kinyarwanda",
    "kmb_Latn": "Kimbundu", "knc_Latn": "Kanuri (Latin)", "knc_Arab": "Kanuri (Ajami)", "kon_Latn": "Kikongo",
    "lin_Latn": "Lingala", "lua_Latn": "Luba-Kasai", "lug_Latn": "Luganda", "luo_Latn": "Luo", "mos_Latn": "Mossi",
    "nso_Latn": "Northern Sotho", "nus_Latn": "Nuer", "nya_Latn": "Chichewa", "plt_Latn": "Malagasy",
    "por_Latn": "Portuguese", "run_Latn": "Kirundi", "sag_Latn": "Sango", "sna_Latn": "Shona", "som_Latn": "Somali",
    "sot_Latn": "Southern Sotho", "ssw_Latn": "Swati", "swh_Latn": "Swahili", "taq_Latn": "Tamasheq (Latin)",
    "taq_Tfng": "Tamasheq (Tifinagh)", "tir_Ethi": "Tigrinya", "tsn_Latn": "Setswana", "tso_Latn": "Tsonga",
    "tum_Latn": "Tumbuka", "twi_Latn": "Twi", "tzm_Tfng": "Central Atlas Tamazight", "umb_Latn": "Umbundu",
    "wol_Latn": "Wolof", "xho_Latn": "Xhosa", "yor_Latn": "Yoruba", "zul_Latn": "Zulu",
}
ACE_LANGS = {"sw": "Swahili", "fr": "French", "pt": "Portuguese", "ar": "Arabic", "am": "Amharic",
             "om": "Oromo", "so": "Somali"}

# GSM 03.38 basic and extension sets, as in ACE's encoding.py (Apache-2.0).
GSM7 = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
           "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
GSM7_EXT = set("^{}\\[~]|€")
TYPOGRAPHY = {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", " ": " ",
              "«": '"', "»": '"', "ç": "c", "œ": "oe", "Œ": "OE"}


# ---------------------------------------------------------------- downloads and checksums

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, dest: Path, expected: str | None) -> None:
    if dest.exists() and (expected is None or sha256(dest) == expected):
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url}")
    urllib.request.urlretrieve(url, dest)
    got = sha256(dest)
    if expected and got != expected:
        dest.unlink()
        sys.exit(f"checksum mismatch for {dest.name}: expected {expected}, got {got}")


def cmd_fetch(_: argparse.Namespace) -> None:
    tar = CACHE / "flores200_dataset.tar.gz"
    download(FLORES_URL, tar, FLORES_SHA256)
    with tarfile.open(tar) as t:
        members = [m for m in t.getmembers() if m.name.endswith((".dev", ".devtest"))]
        root = CACHE.resolve()
        for m in members:  # refuse any path that would land outside cache/
            if not (root / m.name).resolve().is_relative_to(root) or not m.isfile():
                sys.exit(f"unsafe archive member: {m.name}")
        try:
            t.extractall(CACHE, members=members, filter="data")
        except TypeError:  # Python before 3.12 has no extraction filters; members were checked above
            t.extractall(CACHE, members=members)
    for (split, code), digest in CORRECTIONS.items():
        download(f"{CORRECTIONS_URL}/data/corrected/{split}/{code}.{split}",
                 CACHE / "corrections" / split / f"{code}.{split}", digest)
    for spec in EQUIVALENTS:
        download(spec["url"], CACHE / "tokenizers" / spec["file"], spec["sha256"])
    for spec in REGISTRY:
        if spec["kind"] == "hf":
            download(spec["url"], CACHE / "tokenizers" / spec["file"], spec["sha256"])
        else:
            import tiktoken
            tiktoken.get_encoding(spec["encoding"])  # tiktoken caches and verifies its own files
    print("all downloads verified")


# ---------------------------------------------------------------- tokenizers

def load_tokenizer(spec: dict):
    if spec["kind"] == "tiktoken":
        import tiktoken
        enc = tiktoken.get_encoding(spec["encoding"])
        return lambda s: len(enc.encode(s, disallowed_special=()))
    from tokenizers import Tokenizer
    path = Path(spec["path"]) if spec.get("path") else CACHE / "tokenizers" / spec["file"]
    tok = Tokenizer.from_file(str(path))
    return lambda s: len(tok.encode(s, add_special_tokens=False).ids)


# ---------------------------------------------------------------- data

SPLIT = "dev"
NFC = False
SIZES = {"dev": 997, "devtest": 1012}


def norm(text: str) -> str:
    return unicodedata.normalize("NFC", text) if NFC else text


def flores(code: str) -> list[str]:
    """FLORES-200 sentences for one language, from the dev split or the devtest split."""
    path = CACHE / "flores200_dataset" / SPLIT / f"{code}.{SPLIT}"
    if not path.exists():
        sys.exit(f"{path} is missing: run python audit.py fetch first")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == SIZES[SPLIT], f"{code}: expected {SIZES[SPLIT]} sentences, found {len(lines)}"
    return [norm(line) for line in lines]


def ace_rows() -> list[dict]:
    with open(ROOT / "data" / "ace_parallel.jsonl", encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    for r in rows:
        r["text"] = {k: norm(v) for k, v in r["text"].items()}
    return rows


# ---------------------------------------------------------------- measures

def counts(count, texts: list[str]) -> np.ndarray:
    return np.array([count(t) for t in texts], dtype=np.int64)


def ratio_ci(lang: np.ndarray, eng: np.ndarray, reps: int = 1000, seed: int = 7) -> tuple[float, float, float]:
    """Ratio of totals, with a 95% percentile bootstrap interval over aligned items."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(eng), size=(reps, len(eng)))
    boots = lang[idx].sum(axis=1) / eng[idx].sum(axis=1)
    return float(lang.sum() / eng.sum()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def paired_diff_ci(a: np.ndarray, b: np.ndarray, eng_a: np.ndarray, eng_b: np.ndarray, reps: int = 1000,
                   seed: int = 11) -> tuple[float, float]:
    """95% interval for ratio(a) minus ratio(b), resampling the same sentences for both tokenizers."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(reps, len(a)))
    d = a[idx].sum(1) / eng_a[idx].sum(1) - b[idx].sum(1) / eng_b[idx].sum(1)
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def paired_abs_ci(a: np.ndarray, b: np.ndarray, reps: int = 1000, seed: int = 13) -> tuple[float, float]:
    """95% interval for the relative difference in absolute tokens, a over b minus one."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(reps, len(a)))
    d = a[idx].sum(1) / b[idx].sum(1) - 1
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def gsm_fold(text: str) -> str:
    out = []
    for c in text:
        c = TYPOGRAPHY.get(c, c)
        if len(c) == 1 and c not in GSM7 and c not in GSM7_EXT and c.isalpha():
            base = unicodedata.normalize("NFKD", c)[0]
            c = base if base in GSM7 else c
        out.append(c)
    return "".join(out)


def sms_segments(text: str) -> int:
    if all(c in GSM7 or c in GSM7_EXT for c in text):
        n = sum(2 if c in GSM7_EXT else 1 for c in text)
        return 1 if n <= 160 else math.ceil(n / 153)
    n = len(text.encode("utf-16-le")) // 2
    return 1 if n <= 70 else math.ceil(n / 67)


def write_csv(name: str, rows: list[dict]) -> None:
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- run

def cmd_run(args: argparse.Namespace) -> None:
    toks = {s["name"]: load_tokenizer(s) for s in REGISTRY}
    eng_text = flores("eng_Latn")
    out: dict = {"flores": {}, "english": {}, "ace": {}}

    # 1. FLORES-200 dev, every African language, every tokenizer
    flores_rows = []
    best_rows = []
    eng_counts = {}
    for tname, count in toks.items():
        eng_counts[tname] = counts(count, eng_text)
        out["english"][tname] = int(eng_counts[tname].sum())
    for code, lname in AFRICAN.items():
        text = flores(code)
        words = sum(len(s.split()) for s in text)
        per = {}
        for tname, count in toks.items():
            c = counts(count, text)
            per[tname] = c
            r, lo, hi = ratio_ci(c, eng_counts[tname], args.reps)
            per_word = (c.sum() / words) / (eng_counts[tname].sum() / sum(len(s.split()) for s in eng_text))
            flores_rows.append({"flores_code": code, "language": lname, "tokenizer": tname,
                                "same_text_ratio": round(r, 4), "ci_low": round(lo, 4), "ci_high": round(hi, 4),
                                "tokens_per_word_ratio": round(float(per_word), 4), "tokens": int(c.sum()),
                                "english_tokens": int(eng_counts[tname].sum())})
            out["flores"].setdefault(code, {})[tname] = round(r, 4)
        print(f"{lname:24}" + " ".join(f"{out['flores'][code][t]:6.2f}" for t in toks))
        ranked = sorted(toks, key=lambda t: out["flores"][code][t])
        b1, b2 = ranked[0], ranked[1]
        lo, hi = paired_diff_ci(per[b1], per[b2], eng_counts[b1], eng_counts[b2], args.reps)
        by_abs = sorted(toks, key=lambda t: per[t].sum())
        a1, a2 = by_abs[0], by_abs[1]
        alo, ahi = paired_abs_ci(per[a1], per[a2], args.reps)
        _, _rlo, rhi = ratio_ci(per[b1], eng_counts[b1], args.reps)
        best_rows.append({"flores_code": code, "language": lname,
                          "best_by_ratio": b1, "ratio": out["flores"][code][b1], "ratio_ci_high": round(rhi, 4),
                          "runner_up_by_ratio": b2, "runner_up_ratio": out["flores"][code][b2],
                          "ratio_gap_ci_low": round(lo, 4), "ratio_gap_ci_high": round(hi, 4),
                          "ratio_win_is_clear": hi < 0,
                          "best_by_absolute_tokens": a1, "runner_up_by_absolute_tokens": a2,
                          "absolute_gap_ci_low": round(alo, 4), "absolute_gap_ci_high": round(ahi, 4),
                          "absolute_win_is_clear": ahi < 0,
                          "meets_1_5_point": out["flores"][code][b1] <= 1.5, "meets_1_5_interval": rhi <= 1.5})
    write_csv("flores_african.csv", flores_rows)
    write_csv("best_tokenizer.csv", best_rows)

    # 2. ACE's own text: service messages and health and farming facts
    rows = ace_rows()
    ace_out = []
    for kind in ("service_message", "fact"):
        sub = [r for r in rows if r["kind"] == kind]
        for tname, count in toks.items():
            eng = counts(count, [r["text"]["en"] for r in sub])
            for lang, lname in ACE_LANGS.items():
                c = counts(count, [r["text"][lang] for r in sub])
                ratio, lo, hi = ratio_ci(c, eng, args.reps)
                ace_out.append({"corpus": kind, "items": len(sub), "language": lname, "tokenizer": tname,
                                "same_text_ratio": round(ratio, 4), "ci_low": round(lo, 4), "ci_high": round(hi, 4)})
                out["ace"].setdefault(kind, {}).setdefault(lang, {})[tname] = round(ratio, 4)
    write_csv("ace_text.csv", ace_out)

    # 3. The SMS channel: characters, UTF-8 bytes and segments against English
    sms_out = []
    for kind in ("service_message", "fact"):
        sub = [r for r in rows if r["kind"] == kind]
        en = [r["text"]["en"] for r in sub]
        for lang, lname in ACE_LANGS.items():
            tx = [r["text"][lang] for r in sub]
            sms_out.append({
                "corpus": kind, "language": lname,
                "characters_ratio": round(sum(map(len, tx)) / sum(map(len, en)), 3),
                "utf8_bytes_ratio": round(sum(len(t.encode()) for t in tx) / sum(len(t.encode()) for t in en), 3),
                "sms_segments_ratio": round(sum(map(sms_segments, tx)) / sum(map(sms_segments, en)), 3),
                "sms_segments_ratio_after_folding": round(sum(sms_segments(gsm_fold(t)) for t in tx)
                                                          / sum(sms_segments(gsm_fold(t)) for t in en), 3),
                "share_fitting_gsm7": round(sum(all(c in GSM7 or c in GSM7_EXT for c in t) for t in tx) / len(tx), 3),
            })
    write_csv("sms_channel.csv", sms_out)

    (RESULTS / "results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {RESULTS}")


# ---------------------------------------------------------------- private check

def cmd_corrections(args: argparse.Namespace) -> None:
    """How much native speaker corrections to FLORES move each ratio, on both splits."""
    global SPLIT
    toks = {s["name"]: load_tokenizer(s) for s in REGISTRY}
    rows = []
    for split in ("dev", "devtest"):
        SPLIT = split
        eng = {t: counts(c, flores("eng_Latn")) for t, c in toks.items()}
        for (sp, code), _ in CORRECTIONS.items():
            if sp != split:
                continue
            original = flores(code)
            path = CACHE / "corrections" / split / f"{code}.{split}"
            corrected = [norm(line) for line in path.read_text(encoding="utf-8").splitlines()]
            assert len(corrected) == len(original), code
            changed = sum(a != b for a, b in zip(original, corrected, strict=True))
            for t, c in toks.items():
                before = counts(c, original).sum() / eng[t].sum()
                after_counts = counts(c, corrected)
                after, lo, hi = ratio_ci(after_counts, eng[t], args.reps)
                rows.append({"split": split, "flores_code": code, "language": AFRICAN[code],
                             "sentences": len(original), "sentences_corrected": changed, "tokenizer": t,
                             "ratio_original": round(float(before), 4), "ratio_corrected": round(after, 4),
                             "corrected_ci_low": round(lo, 4), "corrected_ci_high": round(hi, 4),
                             "change": round(after - float(before), 4)})
            best_before = min(toks, key=lambda t: next(r["ratio_original"] for r in rows
                                                       if r["split"] == split and r["flores_code"] == code
                                                       and r["tokenizer"] == t))
            best_after = min(toks, key=lambda t: next(r["ratio_corrected"] for r in rows
                                                      if r["split"] == split and r["flores_code"] == code
                                                      and r["tokenizer"] == t))
            biggest = max((r for r in rows if r["split"] == split and r["flores_code"] == code),
                          key=lambda r: abs(r["change"]))
            print(f"{split:8} {AFRICAN[code]:16} {changed:4} of {len(original)} sentences corrected; best tokenizer "
                  f"{best_before} -> {best_after}; largest change {biggest['change']:+.3f} ({biggest['tokenizer']})")
    write_csv("flores_corrections.csv", rows)


def cmd_equivalence(_: argparse.Namespace) -> None:
    """Compare each equivalent tokenizer with the one it matches, sentence by sentence, on both splits."""
    global SPLIT
    from tokenizers import Tokenizer
    rows = []
    for spec in EQUIVALENTS:
        a = Tokenizer.from_file(str(CACHE / "tokenizers" / spec["file"]))
        twin = next(s for s in REGISTRY if s["name"] == spec["same_as"])
        b = Tokenizer.from_file(str(CACHE / "tokenizers" / twin["file"]))
        for split in ("dev", "devtest"):
            SPLIT = split
            sentences = same_ids = same_count = 0
            files_same_count = 0
            codes = ["eng_Latn", *AFRICAN]
            for code in codes:
                file_same = True
                for line in flores(code):
                    ia, ib = a.encode(line, add_special_tokens=False).ids, b.encode(line, add_special_tokens=False).ids
                    sentences += 1
                    same_ids += ia == ib
                    same_count += len(ia) == len(ib)
                    file_same &= len(ia) == len(ib)
                files_same_count += file_same
            rows.append({"tokenizer": spec["name"], "compared_with": spec["same_as"], "split": split,
                         "sentences": sentences, "identical_token_ids": same_ids, "identical_counts": same_count,
                         "files": len(codes), "files_with_identical_counts": files_same_count})
            print(f"{spec['name']:16} vs {spec['same_as']:15} {split:8} {same_ids:,} of {sentences:,} sentences with "
                  f"identical ids, {same_count:,} with identical counts")
    write_csv("equivalence.csv", rows)


def letter_share(code: str) -> float:
    """Share of letters outside basic Latin (code points above 127) in the dev sentences."""
    letters = [ch for ch in "".join(flores(code)) if ch.isalpha()]
    return sum(ord(ch) > 127 for ch in letters) / len(letters)


def spearman(x: list[float], y: list[float]) -> float:
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def cmd_summary(_: argparse.Namespace) -> None:
    """Derive every headline figure from the results files and the FLORES text, into results/summary.json."""
    global SPLIT
    out: dict = {}

    def load(folder: str, name: str) -> list[dict]:
        with open(ROOT / folder / name, encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    tok_names = [s["name"] for s in REGISTRY]
    for folder in ("results", "results_devtest", "results_nfc"):
        best = load(folder, "best_tokenizer.csv")
        vals = [float(r["ratio"]) for r in best]
        out[folder] = {
            "varieties": len(best),
            "meets_1_5_point": [r["language"] for r in best if r["meets_1_5_point"] == "True"],
            "meets_1_5_interval": [r["language"] for r in best if r["meets_1_5_interval"] == "True"],
            "bands": {"at_most_1_5": sum(v <= 1.5 for v in vals), "1_5_to_2": sum(1.5 < v <= 2 for v in vals),
                      "2_to_3": sum(2 < v <= 3 for v in vals), "above_3": sum(v > 3 for v in vals)},
            "wins_by_ratio": dict(Counter(r["best_by_ratio"] for r in best).most_common()),
            "wins_by_absolute_tokens": dict(Counter(r["best_by_absolute_tokens"] for r in best).most_common()),
            "ratio_ties": [[r["language"], r["best_by_ratio"], r["runner_up_by_ratio"]] for r in best
                           if r["ratio_win_is_clear"] != "True"],
            "absolute_ties": [[r["language"], r["best_by_absolute_tokens"], r["runner_up_by_absolute_tokens"]]
                              for r in best if r["absolute_win_is_clear"] != "True"],
        }
    dev = {(r["flores_code"], r["tokenizer"]): r for r in load("results", "flores_african.csv")}
    dt = {(r["flores_code"], r["tokenizer"]): r for r in load("results_devtest", "flores_african.csv")}
    nfc = {(r["flores_code"], r["tokenizer"]): r for r in load("results_nfc", "flores_african.csv")}
    ratio = {k: float(v["same_text_ratio"]) for k, v in dev.items()}
    toks = {k: int(v["tokens"]) for k, v in dev.items()}
    diffs = [abs(ratio[k] - float(dt[k]["same_text_ratio"])) for k in dev]
    best_dev = {r["flores_code"]: r for r in load("results", "best_tokenizer.csv")}
    best_dt = {r["flores_code"]: r for r in load("results_devtest", "best_tokenizer.csv")}
    out["dev_vs_devtest"] = {
        "pairs": len(diffs), "median_abs_change": round(float(np.median(diffs)), 4), "max_abs_change": round(max(diffs), 4),
        "best_by_ratio_changes": [AFRICAN[c] for c in AFRICAN if best_dev[c]["best_by_ratio"] != best_dt[c]["best_by_ratio"]],
        "best_by_absolute_changes": [AFRICAN[c] for c in AFRICAN
                                     if best_dev[c]["best_by_absolute_tokens"] != best_dt[c]["best_by_absolute_tokens"]]}
    out["nfc"] = {"moves_of_0_005_or_more": sorted(
        ([AFRICAN[c], t, round(ratio[(c, t)], 4), round(float(nfc[(c, t)]["same_text_ratio"]), 4)]
         for (c, t) in dev if abs(ratio[(c, t)] - float(nfc[(c, t)]["same_text_ratio"])) >= 0.005),
        key=lambda x: x[3] - x[2]),
        "english_unchanged": all(dev[("eng_Latn", t)]["tokens"] == nfc[("eng_Latn", t)]["tokens"] for t in tok_names)
        if ("eng_Latn", tok_names[0]) in dev else None}

    # script
    SPLIT = "dev"
    share = {c: letter_share(c) for c in AFRICAN}
    best_abs = {c: best_dev[c]["best_by_absolute_tokens"] for c in AFRICAN}
    basic = [c for c in AFRICAN if share[c] < 0.05]
    arabic_script = [c for c in AFRICAN if c.endswith("_Arab")]
    other = [c for c in AFRICAN if share[c] >= 0.05 and c not in arabic_script]
    gem = {c: toks[(c, "Gemma 4")] / toks[(c, "o200k")] for c in AFRICAN}
    out["script"] = {
        "basic_latin_varieties": len(basic),
        "basic_latin_o200k_fewest_absolute_tokens": sum(best_abs[c] == "o200k" for c in basic),
        "non_basic_varieties_outside_arabic_script": len(other),
        "of_those_gemma4_best_by_ratio": [AFRICAN[c] for c in other if best_dev[c]["best_by_ratio"] == "Gemma 4"],
        "of_those_other_winners": {AFRICAN[c]: best_dev[c]["best_by_ratio"] for c in other
                                   if best_dev[c]["best_by_ratio"] != "Gemma 4"},
        "spearman_share_vs_gemma4_over_o200k_tokens": round(spearman([share[c] for c in AFRICAN],
                                                                     [gem[c] for c in AFRICAN]), 4),
        "n": len(AFRICAN),
        "amharic_gemma4_over_o200k_tokens": round(gem["amh_Ethi"], 4),
        "letter_share_outside_basic_latin": {AFRICAN[c]: round(share[c], 4) for c in AFRICAN}}
    arabic = ("arb_Arab", "ary_Arab", "arz_Arab", "aeb_Arab")
    without = [c for c in AFRICAN if c not in arabic and c not in ("fra_Latn", "por_Latn")]
    out["meets_1_5_outside_french_portuguese_and_arabic_varieties"] = {
        "varieties": len(without), "meet": [AFRICAN[c] for c in without if float(best_dev[c]["ratio"]) <= 1.5]}

    # generations, in tokens for the same sentences
    def change(old: str, new: str) -> dict:
        pct = {c: (toks[(c, new)] - toks[(c, old)]) / toks[(c, old)] * 100 for c in AFRICAN}
        worse = sorted((c for c in AFRICAN if pct[c] > 0), key=lambda c: -pct[c])
        best = min(AFRICAN, key=lambda c: pct[c])
        return {"median_token_change_pct": round(float(np.median(list(pct.values()))), 2),
                "largest_cut": [AFRICAN[best], round(pct[best], 2)], "varieties_costlier": len(worse),
                "costlier": [[AFRICAN[c], round(pct[c], 2)] for c in worse]}
    out["generations"] = {"Llama 3 to Llama 4": change("Llama 3", "Llama 4"), "Qwen3 to Qwen3.5": change("Qwen3", "Qwen3.5")}

    # English budget on devtest
    eng_dt = {t: int(dt[("eng_Latn", t)]["tokens"]) for t in tok_names} if ("eng_Latn", "o200k") in dt else \
        json.loads((ROOT / "results_devtest" / "results.json").read_text())["english"]
    budget = int(eng_dt["o200k"] * 1.01)
    out["english_budget_devtest"] = {"o200k": eng_dt["o200k"], "budget_at_1_pct": budget,
                                     "pass": sorted(t for t, n in eng_dt.items() if n <= budget),
                                     "fail": {t: n - budget for t, n in eng_dt.items() if n > budget}}

    # corrections
    corr = load("results", "flores_corrections.csv")
    hau = [r for r in corr if r["split"] == "dev" and r["flores_code"] == "hau_Latn"]
    original = "".join(flores("hau_Latn"))
    corrected = (CACHE / "corrections" / "dev" / "hau_Latn.dev").read_text(encoding="utf-8")
    out["corrections"] = {
        "hausa_dev_change_pct": {r["tokenizer"]: round(float(r["change"]) / float(r["ratio_original"]) * 100, 2)
                                 for r in hau},
        "hausa_dev_every_corrected_interval_above_original": all(
            float(r["corrected_ci_low"]) > float(r["ratio_original"]) for r in hau),
        "hausa_dev_hooked_letters": {"original": sum(original.count(ch) for ch in "ɓɗƙƴ"),
                                     "corrected": sum(corrected.count(ch) for ch in "ɓɗƙƴ")},
        "largest_change_elsewhere": round(max(abs(float(r["change"])) for r in corr
                                              if not (r["split"] == "dev" and r["flores_code"] == "hau_Latn")), 4),
        "best_tokenizer_changes": sum(
            min((r for r in corr if (r["split"], r["flores_code"]) == key), key=lambda r: float(r["ratio_original"]))
            ["tokenizer"]
            != min((r for r in corr if (r["split"], r["flores_code"]) == key), key=lambda r: float(r["ratio_corrected"]))
            ["tokenizer"]
            for key in {(r["split"], r["flores_code"]) for r in corr})}
    # FLORES character ratios for ACE's languages
    eng_chars = len("".join(flores("eng_Latn")))
    out["flores_character_ratio"] = {AFRICAN[c]: round(len("".join(flores(c))) / eng_chars, 3)
                                     for c in ("amh_Ethi", "arb_Arab", "fra_Latn", "por_Latn", "swh_Latn", "som_Latn",
                                               "gaz_Latn")}
    path = RESULTS / "summary.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    s = out["script"]
    print(f"{len(out['results']['meets_1_5_point'])} varieties meet 1.5 on dev; outside French, Portuguese and Arabic, "
          f"{len(out['meets_1_5_outside_french_portuguese_and_arabic_varieties']['meet'])} of "
          f"{out['meets_1_5_outside_french_portuguese_and_arabic_varieties']['varieties']}")
    print(f"basic Latin varieties: {s['basic_latin_varieties']}, o200k fewest tokens in "
          f"{s['basic_latin_o200k_fewest_absolute_tokens']}; Gemma 4 best in {len(s['of_those_gemma4_best_by_ratio'])} "
          f"of {s['non_basic_varieties_outside_arabic_script']} others outside Arabic script; "
          f"rank correlation {s['spearman_share_vs_gemma4_over_o200k_tokens']:.2f}")
    for k, v in out["generations"].items():
        print(f"{k}: median {v['median_token_change_pct']:+.1f}% tokens, {v['varieties_costlier']} varieties costlier, "
              f"largest cut {v['largest_cut'][0]} {v['largest_cut'][1]:+.1f}%")
    print(f"wrote {path.relative_to(ROOT)}")


def cmd_check(args: argparse.Namespace) -> None:
    """Score a local tokenizer offline: same-text ratio per language against a ceiling, and English budget."""
    named = next((s for s in REGISTRY if s["name"] == args.tokenizer), None)
    cand = load_tokenizer(named if named else {"kind": "hf", "path": args.tokenizer})
    base = next(s for s in REGISTRY if s["name"] == args.baseline)
    base_count = load_tokenizer(base)
    eng_text = flores("eng_Latn")
    eng = counts(cand, eng_text)
    budget = counts(base_count, eng_text).sum()
    langs = args.languages.split(",") if args.languages else list(AFRICAN)
    english_ok = eng.sum() <= budget * (1 + args.tolerance)
    print(f"English budget: {eng.sum():,} tokens against {budget:,} on {args.baseline} "
          f"({eng.sum() / budget - 1:+.2%}, tolerance {args.tolerance:.1%}): {'PASS' if english_ok else 'FAIL'}")
    report, passed = [], 0
    for code in langs:
        r, lo, hi = ratio_ci(counts(cand, flores(code)), eng, args.reps)
        ok = hi <= args.ceiling
        passed += ok
        report.append({"flores_code": code, "language": AFRICAN.get(code, code), "same_text_ratio": round(r, 3),
                       "ci_low": round(lo, 3), "ci_high": round(hi, 3), "ceiling": args.ceiling,
                       "result": "PASS" if ok else "FAIL"})
        print(f"{AFRICAN.get(code, code):24} {r:5.2f}  [{lo:.2f}, {hi:.2f}]  {'PASS' if ok else 'FAIL'}")
    print(f"{passed} of {len(langs)} varieties pass the {args.ceiling} ceiling with their whole interval below it")
    verdict = english_ok and passed == len(langs)
    print(f"Overall: {'PASS' if verdict else 'FAIL'} (a tokenizer passes only if English is within budget "
          f"and every variety passes)")
    regressions = []
    if args.compare:
        named_prev = next((s for s in REGISTRY if s["name"] == args.compare), None)
        prev = load_tokenizer(named_prev if named_prev else {"kind": "hf", "path": args.compare})
        prev_eng = counts(prev, eng_text)
        print(f"Against {args.compare}, variety by variety:")
        for row in report:
            p_ratio = counts(prev, flores(row["flores_code"])).sum() / prev_eng.sum()
            row["previous_ratio"] = round(float(p_ratio), 3)
            row["change_pct"] = round((row["same_text_ratio"] / p_ratio - 1) * 100, 1)
            if row["change_pct"] > 0:
                regressions.append(row["language"])
            print(f"{row['language']:24} {p_ratio:5.2f} -> {row['same_text_ratio']:5.2f}  {row['change_pct']:+.1f}%")
        print(f"{len(regressions)} of {len(report)} varieties cost more than on {args.compare}")
    if args.out:
        Path(args.out).write_text(json.dumps({"split": SPLIT, "nfc": NFC, "english_tokens": int(eng.sum()),
                                              "english_budget": int(budget), "english_pass": bool(english_ok),
                                              "overall_pass": bool(verdict), "regressions": regressions,
                                              "languages": report}, indent=1))
    sys.exit(0 if verdict else 1)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch").set_defaults(func=cmd_fetch)
    run = sub.add_parser("run")
    run.add_argument("--reps", type=int, default=1000, help="bootstrap resamples")
    run.add_argument("--split", choices=["dev", "devtest"], default="dev", help="FLORES-200 split")
    run.add_argument("--nfc", action="store_true", help="normalise all text to Unicode NFC before counting")
    run.set_defaults(func=cmd_run)
    cor = sub.add_parser("corrections")
    cor.add_argument("--reps", type=int, default=1000, help="bootstrap resamples")
    cor.set_defaults(func=cmd_corrections)
    sub.add_parser("equivalence").set_defaults(func=cmd_equivalence)
    sub.add_parser("summary").set_defaults(func=cmd_summary)
    chk = sub.add_parser("check")
    chk.add_argument("--tokenizer", required=True,
                     help="path to a Hugging Face tokenizer.json, or the name of a tokenizer in tokenizers.json")
    chk.add_argument("--ceiling", type=float, default=1.5)
    chk.add_argument("--baseline", default="o200k", help="tokenizer whose English count sets the budget")
    chk.add_argument("--tolerance", type=float, default=0.01, help="allowed English increase over the baseline")
    chk.add_argument("--languages", help="comma separated FLORES codes; default every African language")
    chk.add_argument("--reps", type=int, default=1000)
    chk.add_argument("--split", choices=["dev", "devtest"], default="devtest",
                     help="FLORES-200 split; devtest by default, so a tokenizer tuned on dev is scored on other sentences")
    chk.add_argument("--nfc", action="store_true", help="normalise all text to Unicode NFC before counting")
    chk.add_argument("--compare", help="a previous tokenizer (path or name) to compare with, variety by variety")
    chk.add_argument("--out", help="write the report as JSON")
    chk.set_defaults(func=cmd_check)
    args = p.parse_args()
    global SPLIT, RESULTS, NFC
    SPLIT = getattr(args, "split", "dev")
    NFC = getattr(args, "nfc", False)
    suffix = ("" if SPLIT == "dev" else f"_{SPLIT}") + ("_nfc" if NFC else "")
    RESULTS = ROOT / f"results{suffix}"
    args.func(args)


if __name__ == "__main__":
    main()
