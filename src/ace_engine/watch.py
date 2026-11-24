"""The number watcher: recheck every served phone number against the page it was sourced from.

A hotline that changes while ACE keeps serving the old one is a wrong answer in an emergency. Every week the
watcher fetches each emergency fact's source page and confirms that each of its numbers still appears there.
It reports four outcomes per number: found; missing (not on the page as fetched, so a person must review it,
remembering that some pages load their content with scripts); other_source (the fact names several sources
and the number is not on the linked one, so a person checks the others); and unchecked (the page could not be
fetched or is not readable text, such as a PDF). The scheduled workflow opens an issue when any number is
missing. It never edits a pack on its own.
"""
from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass

from .connectors.base import ConnectorError, http_get
from .context.packs import ContextPack

_TAGS = re.compile(r"<script.*?</script>|<style.*?</style>|<[^>]+>", re.S | re.I)
_DIGITS = re.compile(r"\d+")


@dataclass
class NumberCheck:
    country: str
    fact_id: str
    number: str
    source_url: str
    status: str          # found, missing, other_source, unchecked
    detail: str = ""


def page_text(raw: bytes) -> str:
    text = raw.decode("utf-8", "replace")
    return html.unescape(_TAGS.sub(" ", text))


def number_on_page(number: str, text: str) -> bool:
    """True when the number's digits appear on the page as a whole number, allowing spaces or dashes inside it."""
    digits = "".join(_DIGITS.findall(number))
    if not digits:
        return False
    flat = re.sub(r"(?<=\d)[ \- .](?=\d)", "", text)
    return re.search(rf"(?<!\d){re.escape(digits)}(?!\d)", flat) is not None


def check(packs: list[ContextPack], fetch=http_get) -> list[NumberCheck]:
    cache: dict[str, str | Exception] = {}
    results = []
    for pack in packs:
        for fact in pack.facts:
            if fact.topic != "emergency_contacts" or not fact.contacts or not fact.source_url:
                continue
            url = fact.source_url
            if url not in cache:
                try:
                    raw = fetch(url, timeout=45)
                    cache[url] = "" if raw[:5] == b"%PDF-" else page_text(raw)
                except ConnectorError as exc:
                    cache[url] = exc
            page = cache[url]
            country = ",".join(fact.scope.countries) or (pack.country or "")
            for contact in fact.contacts:
                if isinstance(page, Exception):
                    results.append(NumberCheck(country, fact.id, contact.number, url, "unchecked", str(page)[:200]))
                elif page == "":
                    results.append(NumberCheck(country, fact.id, contact.number, url, "unchecked",
                                               "source is a PDF; check by hand"))
                elif number_on_page(contact.number, page):
                    results.append(NumberCheck(country, fact.id, contact.number, url, "found"))
                elif ";" in fact.source:
                    results.append(NumberCheck(country, fact.id, contact.number, url, "other_source",
                                               "fact names several sources; check the others by hand"))
                else:
                    results.append(NumberCheck(country, fact.id, contact.number, url, "missing",
                                               "not on the page as fetched; check by hand"))
    return results


def report_markdown(results: list[NumberCheck]) -> str:
    missing = [r for r in results if r.status == "missing"]
    unchecked = [r for r in results if r.status in ("unchecked", "other_source")]
    found = [r for r in results if r.status == "found"]
    lines = [f"# Number watcher: {len(found)} found, {len(missing)} missing, {len(unchecked)} to check by hand", ""]
    if missing:
        lines += ["## Not found on their source page: review before the next release", "",
                  "Some pages load their content with scripts, so a number can be on the page and still be missed "
                  "here. Open the source and confirm each one.", "",
                  "| Country | Fact | Number | Source |", "| --- | --- | --- | --- |"]
        lines += [f"| {r.country} | `{r.fact_id}` | {r.number} | {r.source_url} |" for r in missing]
        lines.append("")
    if unchecked:
        lines += ["## To check by hand", "", "| Country | Fact | Number | Why |", "| --- | --- | --- | --- |"]
        lines += [f"| {r.country} | `{r.fact_id}` | {r.number} | {r.detail} |" for r in unchecked]
    return "\n".join(lines) + "\n"


def as_dicts(results: list[NumberCheck]) -> list[dict]:
    return [asdict(r) for r in results]
