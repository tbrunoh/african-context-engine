"""Build the character profiles ACE uses to tell a language it speaks from one it does not.

    python benchmark/langid/build.py fetch    download FLORES-200 and the UDHR texts, verifying every checksum
    python benchmark/langid/build.py build    write src/ace_engine/langid/profiles.json

A profile is the frequency of each three letter sequence in a language, read from folded text the way ACE reads a
message. ACE's 32 languages are built from ACE's own locale and pack text, the FLORES-200 dev split and the
Universal Declaration of Human Rights. The languages ACE does not speak but that its callers do (Gikuyu, Dholuo,
Dagbani, Malagasy and others) come from the same two outside sources. No sentence is stored: profiles.json holds
counts only. Because FLORES-200 is CC BY-SA 4.0, profiles.json is shared under CC BY-SA 4.0 too.

The WAXAL speech text that ACE is measured on is never read here, so the WAXAL check stays a held-out test.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ace_engine import i18n  # noqa: E402
from ace_engine.langid import grams  # noqa: E402

CACHE = Path(__file__).parent / ".cache"
OUT = ROOT / "src" / "ace_engine" / "langid" / "profiles.json"
SOURCES = Path(__file__).parent / "sources.json"

FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
FLORES_SHA256 = "b8b0b76783024b85797e5cc75064eb83fc5288b41e9654dabc7be6ae944011f6"  # as in the tokenizer audit
UDHR_COMMIT = "e6a1b6f8cb048fba115d6b81bab47875a4eca0d8"  # github.com/eric-muller/udhr, 19 November 2026
UDHR_URL = "https://raw.githubusercontent.com/eric-muller/udhr/{commit}/data/udhr/udhr_{key}.xml"
TOP = 2000  # three letter sequences kept per language

# ACE language: (FLORES-200 dev files, UDHR keys). Pular takes in the other Fula varieties, so a Fula message is read
# as Pular, the Fula ACE writes, and not as a language ACE does not speak.
ACE = {
    "en": (["eng_Latn"], ["eng"]), "fr": (["fra_Latn"], ["fra"]), "pt": (["por_Latn"], ["por_PT"]),
    "sw": (["swh_Latn"], ["swh"]), "ar": (["arb_Arab"], ["arb"]), "am": (["amh_Ethi"], ["amh"]),
    "om": (["gaz_Latn"], ["gax"]), "so": (["som_Latn"], ["som"]), "ha": (["hau_Latn"], ["hau_NG"]),
    "yo": (["yor_Latn"], ["yor"]), "ig": (["ibo_Latn"], ["ibo"]), "pcm": ([], ["pcm"]),
    "zu": (["zul_Latn"], ["zul"]), "xh": (["xho_Latn"], ["xho"]), "af": (["afr_Latn"], ["afr"]),
    "st": (["sot_Latn"], ["sot"]), "tn": (["tsn_Latn"], ["tsn"]), "ts": (["tso_Latn"], ["tso_MZ"]),
    "sn": (["sna_Latn"], ["sna"]), "ny": (["nya_Latn"], ["nya_chechewa", "nya_chinyanja"]),
    "bem": (["bem_Latn"], ["bem"]), "rw": (["kin_Latn"], ["kin"]), "rn": (["run_Latn"], ["run"]),
    "lg": (["lug_Latn"], ["lug"]), "ln": (["lin_Latn"], ["lin"]),
    "ak": (["aka_Latn", "twi_Latn"], ["aka_asante", "aka_akuapem", "aka_fante"]), "ee": (["ewe_Latn"], ["ewe"]),
    "wo": (["wol_Latn"], ["wol"]), "dyu": (["dyu_Latn"], ["dyu"]), "mos": (["mos_Latn"], ["mos"]),
    "fuf": (["fuv_Latn"], ["fuf", "fuv"]), "ti": (["tir_Ethi"], ["tir"]),
}
# Languages ACE does not speak, spoken in or next to the countries it covers, each with its own name.
# Languages so close to one ACE speaks that their speakers read it are left out, so ACE answers them rather than
# turning them away: isiNdebele (isiZulu), Krio (Nigerian Pidgin), Bambara and Maninka (Dyula), and Chitumbuka,
# whose speakers in Malawi read Chichewa.
OTHER = {
    "kik": ("Gĩkũyũ", ["kik_Latn"], []), "luo": ("Dholuo", ["luo_Latn"], []), "kam": ("Kikamba", ["kam_Latn"], []),
    "dik": ("Thuɔŋjäŋ", ["dik_Latn"], []), "nus": ("Thok Naath", ["nus_Latn"], []),
    "fon": ("Fɔngbè", ["fon_Latn"], ["fon"]),
    "kmb": ("Kimbundu", ["kmb_Latn"], ["kmb"]), "kon": ("Kikongo", ["kon_Latn"], ["kng"]),
    "lua": ("Tshiluba", ["lua_Latn"], ["lua"]), "sag": ("Sängö", ["sag_Latn"], ["sag"]),
    "knc": ("Kanuri", ["knc_Latn"], ["knc"]), "kbp": ("Kabɩyɛ", ["kbp_Latn"], ["kbp"]),
    "taq": ("Tamasheq", ["taq_Latn"], []),
    "nso": ("Sepedi", ["nso_Latn"], ["nso"]), "ssw": ("siSwati", ["ssw_Latn"], ["ssw"]),
    "umb": ("Umbundu", ["umb_Latn"], ["umb"]), "cjk": ("Chokwe", ["cjk_Latn"], []),
    "kab": ("Taqbaylit", ["kab_Latn"], []), "plt": ("Malagasy", ["plt_Latn"], ["plt"]),
    "dag": ("Dagbanli", [], ["dag"]), "dga": ("Dagaare", [], ["dga"]), "nyn": ("Runyankore", [], ["nyn"]),
    "bci": ("Baoulé", [], ["bci"]), "gaa": ("Gã", [], ["gaa"]), "loz": ("Silozi", [], ["loz"]),
    "toi": ("Chitonga", [], ["toi"]), "ven": ("Tshivenḓa", [], ["ven"]), "nzi": ("Nzema", [], ["nzi"]),
    "gjn": ("Gonja", [], ["gjn"]), "tiv": ("Tiv", [], ["tiv"]), "srr": ("Seereer", [], ["srr"]),
    "snk": ("Sooninkanxanne", [], ["snk"]), "men": ("Mɛnde", [], ["men"]), "tem": ("Themne", [], ["tem"]),
    "sus": ("Sosoxui", [], ["sus"]), "dyo": ("Joola", [], ["dyo"]),
    "bin": ("Ẹ̀dó", [], ["bin"]), "ibb": ("Ibibio", [], ["ibb"]), "ada": ("Dangme", [], ["ada"]),
    "kqn": ("Kikaonde", [], ["kqn"]), "yao": ("Chiyao", [], ["yao"]), "vmw": ("Emakhuwa", [], ["vmw"]),
    "nym": ("Kinyamwezi", [], ["nym"]), "suk": ("Kisukuma", [], ["suk"]), "kde": ("Chimakonde", [], ["kde"]),
    "lot": ("Otuho", [], ["lot"]), "nba": ("Nyemba", [], ["nba"]), "lun": ("Chilunda", [], ["lun"]),
    "lue": ("Luvale", [], ["lue"]),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "ACE langid build"})
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310  fixed, pinned sources
        dest.write_bytes(r.read())


def udhr_keys() -> list[str]:
    return sorted({k for _, ks in ACE.values() for k in ks} | {k for _, _, ks in OTHER.values() for k in ks})


def fetch() -> None:
    tar = CACHE / "flores200_dataset.tar.gz"
    if not tar.exists() or sha256(tar) != FLORES_SHA256:
        download(FLORES_URL, tar)
    if sha256(tar) != FLORES_SHA256:
        raise SystemExit("FLORES-200 checksum does not match")
    pinned = json.loads(SOURCES.read_text(encoding="utf-8"))["udhr"] if SOURCES.exists() else {}
    record = {}
    for key in udhr_keys():
        dest = CACHE / "udhr" / f"udhr_{key}.xml"
        if not dest.exists():
            download(UDHR_URL.format(commit=UDHR_COMMIT, key=key), dest)
        got = sha256(dest)
        if key in pinned and pinned[key] != got:
            raise SystemExit(f"UDHR {key} checksum does not match")
        record[key] = got
    SOURCES.write_text(json.dumps({"flores200": {"url": FLORES_URL, "sha256": FLORES_SHA256},
                                   "udhr_commit": UDHR_COMMIT, "udhr": record}, indent=1) + "\n", encoding="utf-8")
    print(f"FLORES-200 and {len(record)} UDHR texts verified")


def flores(names: list[str]) -> list[str]:
    out = []
    with tarfile.open(CACHE / "flores200_dataset.tar.gz") as tf:
        for name in names:
            out.append(tf.extractfile(f"./flores200_dataset/dev/{name}.dev").read().decode("utf-8"))
    return out


def udhr(keys: list[str]) -> list[str]:
    out = []
    for key in keys:
        root = ET.parse(CACHE / "udhr" / f"udhr_{key}.xml").getroot()
        out.append("\n".join(t.strip() for t in root.itertext() if t.strip()))
    return out


def strings(x):
    if isinstance(x, (str, int, float)):
        yield str(x)
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, (list, tuple, set, frozenset)):
        for v in x:
            yield from strings(v)


def ace_text() -> dict[str, list[str]]:
    import yaml

    texts: dict[str, list[str]] = {code: [] for code in ACE}
    for code, loc in i18n.locales().items():
        texts[code] += list(strings(loc.templates)) + list(strings(loc.phrases))
    for path in sorted((ROOT / "context_packs").rglob("*.yaml")):
        for fact in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("facts", []):
            texts["en"] += [fact.get("claim") or "", fact.get("short") or ""]
            for code, t in (fact.get("translations") or {}).items():
                if code in texts:
                    texts[code] += list(strings(t))
    return texts


def ace_text_digest() -> str:
    """SHA-256 of ACE's own text that goes into the profiles, so a test can tell when a locale edit needs a rebuild."""
    return hashlib.sha256(json.dumps(ace_text(), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def profile(texts: list[str]) -> dict:
    counts = Counter(g for t in texts for g in grams(t))
    top = counts.most_common(TOP)
    return {"total": sum(counts.values()), "grams": dict(top)}


def build() -> None:
    own = ace_text()
    langs: dict[str, dict] = {}
    for code, (fl, ud) in ACE.items():
        langs[code] = {"ace": True, **profile(own[code] + flores(fl) + udhr(ud))}
    for code, (name, fl, ud) in OTHER.items():
        langs[code] = {"ace": False, "name": name, **profile(flores(fl) + udhr(ud))}
    data = {"licence": "CC BY-SA 4.0", "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": "Counts of three letter sequences from FLORES-200 (NLLB Team, Meta AI, CC BY-SA 4.0), "
            "translations of the Universal Declaration of Human Rights (OHCHR, via the UDHR in XML project) and ACE's "
            "own locale and pack text",
            "built_from": f"ACE locale and pack text, FLORES-200 dev, UDHR in XML ({UDHR_COMMIT[:7]})",
            "ace_text_sha256": ace_text_digest(), "top": TOP, "languages": langs}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(langs)} languages, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    {"fetch": fetch, "build": build}[sys.argv[1] if len(sys.argv) > 1 else "build"]()
