"""The number watcher, with a fake fetcher. No network."""
from __future__ import annotations

from pathlib import Path

from ace_engine.connectors.base import ConnectorError
from ace_engine.context.packs import load_packs
from ace_engine.watch import check, number_on_page, report_markdown

PACKS = Path(__file__).resolve().parents[1] / "context_packs"


def test_number_on_page_matches_whole_numbers_with_spacing():
    assert number_on_page("0800 199 195", "Call 0800-199-195 for help")
    assert number_on_page("112", "Emergency: 112 (ambulance)")
    assert not number_on_page("112", "Call 11200 now")
    assert not number_on_page("116", "Room 1160")


def test_watch_reports_found_missing_and_unchecked():
    packs = [p for p in load_packs(PACKS) if p.id in ("gh-emergency-contacts", "ke-emergency-contacts")]

    def fetch(url, timeout=45):
        if "migecah" in url:
            raise ConnectorError("unreachable")
        if url.endswith(".pdf"):
            return b"%PDF-1.7"
        return b"<html><body>Call 112, 999, 1199, 191, 192, 193, 1195 or 911</body></html>"

    results = check(packs, fetch=fetch)
    statuses = {r.status for r in results}
    assert {"found", "unchecked"} <= statuses
    assert all(r.status != "found" or r.number in "112 999 1199 191 192 193 1195 911".split() for r in results)
    report = report_markdown(results)
    assert report.startswith("# Number watcher:") and "To check by hand" in report
