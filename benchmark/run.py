"""Run the ACE benchmark.

    python -m benchmark.run --quick      CI gate: fails on any regression against benchmark/baseline.json
    python -m benchmark.run              full run, writes benchmark/results/latest.json and latest.md

Measures, per language and per country:
  * emergency recall: share of red team messages that get an emergency reply
  * wrong number rate: share of emergency replies that give a number from outside the caller's country
  * false alarm rate: share of ordinary messages that trigger the safety rail
  * service checks (V2): every covered service answers a sample question in every covered country,
    with a citation, inside the USSD screen, and gives no phone number the country's packs do not publish

Service checks run at the time of the newest committed snapshot, so a result depends on the code and the
data, never on the day the benchmark runs. Official warnings are valid for six hours; keeping them fresh is
the job of `ace refresh` on a schedule, not of this gate.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ace_engine import safety  # noqa: E402
from ace_engine.channels.ussd import USSD_MAX_CHARS  # noqa: E402
from ace_engine.countries import COUNTRIES  # noqa: E402
from ace_engine.engine import Engine  # noqa: E402
from ace_engine.models import Channel, Message, ReplyKind  # noqa: E402
from ace_engine.router import Budget  # noqa: E402
from ace_engine.services import facility  # noqa: E402
from ace_engine.services.base import EXAMPLE_PLACE  # noqa: E402
from ace_engine.snapshots import parse_time  # noqa: E402
from ace_engine.text import SUPPORTED_LANGUAGES  # noqa: E402

SETS = Path(__file__).parent / "sets"
TARGET_RECALL = 0.99
_NUM = re.compile(r"(?<![\d+])\d{3,12}(?!\d)")

SERVICE_SAMPLES = {
    "rain_this_week": "{place}",
    "official_warnings": "{place}",
    "nearest_facility": "{place}",
    "market_prices": "price {place}",  # no food named: the nearest market's staples, so every country's diet counts
    "pregnancy_companion": "24",
    "pest_check": "maize leaves with holes and sawdust",
}


def phone(country: str, n: int) -> str:
    return f"+{COUNTRIES[country].dial}7{n:08d}"


def snapshot_time(root: Path):
    """The newest retrieved_at across the committed snapshots: the moment the data describes."""
    times = []
    for path in root.rglob("*.json"):
        try:
            stamp = json.loads(path.read_text(encoding="utf-8")).get("retrieved_at")
        except (ValueError, AttributeError):
            continue
        if stamp:
            times.append(parse_time(stamp))
    return max(t for t in times if t is not None)


def emergency(engine: Engine) -> dict:
    data = yaml.safe_load((SETS / "emergency.yaml").read_text(encoding="utf-8"))
    out: dict = {"by_language": {}, "by_country": {}, "misses": [], "wrong_numbers": []}
    n = 0
    for lang, items in data.items():
        hit = total = 0
        for item in items:
            for country in COUNTRIES:
                n += 1
                reply = engine.handle(Message(channel=Channel.SMS, sender=phone(country, n), text=item["text"],
                                              language=lang))
                total += 1
                ok = reply.kind is ReplyKind.EMERGENCY
                hit += ok
                c = out["by_country"].setdefault(country, {"hit": 0, "total": 0, "wrong": 0})
                c["total"] += 1
                c["hit"] += ok
                if not ok:
                    out["misses"].append({"language": lang, "country": country, "text": item["text"]})
                    continue
                allowed = {ct.number.replace(" ", "") for f in engine._contact_facts(country) for ct in f.contacts}
                given = {m for m in _NUM.findall(reply.text.replace(" ", "")) if m not in ("24",)}
                stray = sorted(g for g in given if g not in allowed)
                if stray:
                    c["wrong"] += 1
                    out["wrong_numbers"].append({"country": country, "text": item["text"], "numbers": stray})
        out["by_language"][lang] = {"recall": round(hit / total, 4), "hit": hit, "total": total}
    total = sum(v["total"] for v in out["by_country"].values())
    out["recall"] = round(sum(v["hit"] for v in out["by_country"].values()) / total, 4)
    answered = sum(v["hit"] for v in out["by_country"].values()) or 1
    out["wrong_number_rate"] = round(sum(v["wrong"] for v in out["by_country"].values()) / answered, 4)
    return out


def ordinary(engine: Engine) -> dict:
    data = yaml.safe_load((SETS / "ordinary.yaml").read_text(encoding="utf-8"))
    alarms, total = [], 0
    for lang, items in data.items():
        for text in items:
            total += 1
            if engine.safety.check(text).escalate:
                alarms.append({"language": lang, "text": text})
    return {"false_alarm_rate": round(len(alarms) / total, 4), "false_alarms": alarms, "total": total}


# The words that introduce a number in any language: the safety rail's call word and the facility emergency line.
# Words before the numbers in most languages, after them in Amharic (911 ይደውሉ).
_TEMPLATES = [*safety.CALL_WORD.values(), *facility.EMERGENCY.values()]
_BEFORE = {t.split("{")[0].strip(" :：፦") for t in _TEMPLATES} - {""}
_AFTER = {t.split("}")[1].strip(" .።") for t in _TEMPLATES if "}" in t} - {""}
_SEP = r"\s*[,،፣]\s*"
_NUMS = r"((?:\d[\d ]*\d|\d)(?:" + _SEP + r"\d[\d ]*\d)*)"
_CALL = re.compile(r"(?:" + "|".join(sorted(map(re.escape, _BEFORE), key=len, reverse=True)) + r")\s*[:：፦]?\s*" + _NUMS)
_CALL_AFTER = re.compile(_NUMS + r"\s*(?:" + "|".join(sorted(map(re.escape, _AFTER), key=len, reverse=True)) + r")")


def stray_numbers(engine: Engine, country: str, text: str) -> list[str]:
    """Numbers a service tells the person to call that no pack publishes for their country."""
    allowed = {ct.number.replace(" ", "") for f in engine._contact_facts(country) for ct in f.contacts}
    found = [*_CALL.findall(text), *_CALL_AFTER.findall(text)]
    given = {n.replace(" ", "") for m in found for n in re.split(_SEP, m)}
    return sorted(n for n in given if n and n not in allowed)


def market_place(hub, country: str) -> str:
    """The area of a market with recent prices: ACE quotes prices only within 150 km of a market, so the check asks
    where WFP has one, as a person there would."""
    from ace_engine.services.prices import MAX_AGE_DAYS, age_days

    snap = hub.snapshots.get("prices", country)
    today = hub.clock().date()
    for m in snap.records if snap else ():
        if any(age_days(i["series"][-1][0], today) <= MAX_AGE_DAYS for i in m["items"]):
            found = hub.places.locate(m["lat"], m["lon"], country, max_km=150)
            if found:
                return found.name
    return EXAMPLE_PLACE[country]


def services(engine: Engine) -> dict:
    hub = engine.services
    if hub is None:
        return {"skipped": "no snapshots"}
    coverage = hub.coverage()
    budget = Budget(max_chars=USSD_MAX_CHARS - 4 - 7, short=True, max_facts=1)
    checks, failures = 0, []
    for sid, sample in SERVICE_SAMPLES.items():
        for n, country in enumerate(COUNTRIES):
            if not coverage[sid][country]["available"]:
                continue
            place = market_place(hub, country) if sid == "market_prices" else EXAMPLE_PLACE[country]
            text = sample.format(place=place)
            for lang in SUPPORTED_LANGUAGES:
                checks += 1
                reply = engine.run_service(sid, Message(channel=Channel.USSD, sender=phone(country, 900 + n),
                                                        text=text, language=lang), budget)
                problem = None
                if reply.kind is ReplyKind.ANSWER and not reply.citations:
                    problem = "answer without a citation"
                elif len(reply.text) > budget.max_chars:
                    problem = f"too long for USSD ({len(reply.text)} characters)"
                elif reply.kind is not ReplyKind.ANSWER:
                    problem = f"no answer: {reply.text[:80]}"
                else:  # the USSD screen may cut the number line, so check the full answer too
                    full = engine.run_service(sid, Message(channel=Channel.API, sender=phone(country, 900 + n),
                                                           text=text, language=lang), Budget(max_chars=1500, short=False))
                    if stray := stray_numbers(engine, country, reply.text + " " + full.text):
                        problem = f"number not published for {country}: {', '.join(stray)}"
                if problem:
                    failures.append({"service": sid, "country": country, "language": lang, "problem": problem})
    gaps = {sid: [c for c, v in by.items() if not v["available"]] for sid, by in coverage.items()}
    return {"checks": checks, "failures": failures, "pass_rate": round(1 - len(failures) / max(checks, 1), 4),
            "gaps": gaps}


def run() -> dict:
    engine = Engine.from_packs(ROOT / "context_packs", snapshots=ROOT / "snapshots")
    if engine.services is not None:
        pinned = snapshot_time(ROOT / "snapshots")
        engine.services.clock = lambda: pinned
    return {"emergency": emergency(engine), "ordinary": ordinary(engine), "services": services(engine)}


def report(results: dict) -> str:
    e, o, s = results["emergency"], results["ordinary"], results["services"]
    lines = ["# ACE benchmark", "",
             f"Emergency recall: {e['recall']:.1%} (target {TARGET_RECALL:.0%}). "
             f"Wrong number rate: {e['wrong_number_rate']:.1%}. False alarm rate: {o['false_alarm_rate']:.1%}.", "",
             "| Language | Recall | Messages |", "| --- | --- | --- |"]
    lines += [f"| {lang} | {v['recall']:.1%} | {v['total']} |" for lang, v in e["by_language"].items()]
    if e["misses"]:
        missed = sorted({(m["language"], m["text"]) for m in e["misses"]})
        lines += ["", "Missed messages:", ""] + [f"- [{lang}] {text}" for lang, text in missed]
    if "checks" in s:
        lines += ["", f"Service checks: {s['checks'] - len(s['failures'])} of {s['checks']} passed.", ""]
        lines += [f"- {f['service']} {f['country']} {f['language']}: {f['problem']}" for f in s["failures"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="CI gate against benchmark/baseline.json")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()
    results = run()
    print(report(results))
    baseline_path = Path(__file__).parent / "baseline.json"
    current = {"recall": results["emergency"]["recall"],
               "wrong_number_rate": results["emergency"]["wrong_number_rate"],
               "false_alarm_rate": results["ordinary"]["false_alarm_rate"],
               "service_pass_rate": results["services"].get("pass_rate", 1.0)}
    if args.update_baseline:
        baseline_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    if not args.quick:
        out = Path(__file__).parent / "results"
        out.mkdir(exist_ok=True)
        (out / "latest.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / "latest.md").write_text(report(results), encoding="utf-8")
        return 0
    base = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else current
    worse = [k for k in ("recall", "service_pass_rate") if current[k] < base[k]] + \
            [k for k in ("wrong_number_rate", "false_alarm_rate") if current[k] > base[k]]
    if worse:
        print("REGRESSION against benchmark/baseline.json: " + ", ".join(worse))
        return 1
    print("No regression against benchmark/baseline.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
