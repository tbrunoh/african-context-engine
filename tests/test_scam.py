from __future__ import annotations

import pytest

from ace_engine.models import Channel, ReplyKind
from ace_engine.scam import Verdict, analyse


@pytest.mark.parametrize("text, sender, signal", [
    ("Please share your M-PESA PIN to confirm your account", None, "asks_for_pin"),
    ("Tuma PIN yako ili kuthibitisha akaunti", None, "asks_for_pin"),
    ("Your line has been registered twice", None, "double_registration"),
    ("Laini yako imesajiliwa mara mbili", None, "double_registration"),
    ("I sent you 2000 by mistake, please send it back", None, "refund_request"),
    ("Nimekutumia pesa kimakosa tafadhali nirudishie", None, "refund_request"),
    ("QK7H2 Confirmed. Ksh2,500.00 received from JOHN 0712345678", "0712345678",
     "confirmation_from_personal_number"),
    ("Safaricom customer care: call us on 0711222333", None, "unofficial_operator_number"),
    ("Dial *334*1*0712345678# to claim", None, "dial_code_instruction"),
    ("Congratulations, you have won 50,000 in the promotion", None, "prize_or_offer"),
    ("Hongera umeshinda zawadi ya pesa", None, "prize_or_offer"),
    ("Verify at http://safaricom-bonus.xyz now", None, "link"),
    ("Your account will be blocked within 24 hours", None, "pressure"),
])
def test_signals(text, sender, signal):
    report = analyse(text, sender)
    assert signal in [s.id for s in report.signals], (text, report)


def test_official_number_is_not_flagged():
    report = analyse("Safaricom will call you from 0722000000 about your request")
    assert "unofficial_operator_number" not in [s.id for s in report.signals]


def test_confirmation_from_mpesa_sender_is_not_flagged():
    report = analyse("QK7H2 Confirmed. Ksh2,500.00 received from JOHN 0712345678", sender="MPESA")
    assert report.verdict is Verdict.NO_KNOWN_SIGNS


def test_verdict_thresholds():
    assert analyse("Share your PIN with us").verdict is Verdict.LIKELY_SCAM
    assert analyse("Your account will be blocked soon, act immediately").verdict is Verdict.SUSPICIOUS
    assert analyse("See you at the market tomorrow").verdict is Verdict.NO_KNOWN_SIGNS


def test_no_known_signs_never_says_safe(engine):
    reply = engine.scam_reply(analyse("See you at the market tomorrow"), "en",
                              engine.config.budgets[Channel.SMS])
    assert "does not prove it is safe" in reply.text


def test_scam_command_and_auto_detection(engine):
    by_command = engine.ask("SCAM your account will be blocked, act immediately", channel=Channel.SMS)
    assert by_command.kind is ReplyKind.SCAM and by_command.text.startswith("BE CAREFUL")
    forwarded = engine.ask("Your SIM is registered twice. Send your M-PESA PIN to confirm", channel=Channel.SMS)
    assert forwarded.kind is ReplyKind.SCAM and forwarded.text.startswith("LIKELY SCAM")
    assert "333" in forwarded.text


def test_scam_reply_cites_operator_guidance(engine):
    reply = engine.ask("SCAM please share your PIN", channel=Channel.WHATSAPP)
    cited = {c.fact_id for c in reply.citations}
    assert "ke-mobile-money-safety/never-share-pin" in cited
    assert "ke-mobile-money-safety/report-333" in cited
    assert all(c.source_url.startswith("https://safaricom.co.ke") for c in reply.citations
               if c.fact_id.endswith(("never-share-pin", "report-333")))


def test_scam_reply_in_swahili(engine):
    reply = engine.ask("UTAPELI tuma PIN yako sasa hivi", channel=Channel.SMS, language="sw")
    assert reply.text.startswith("HUU NI UTAPELI MTARAJIWA")


def test_scam_reply_fits_ussd(engine):
    budget = engine.config.budgets[Channel.USSD]
    reply = engine.scam_reply(analyse("Registered twice, send PIN, dial *123#, won a prize, http://x.xyz"), "sw",
                              budget)
    assert len(reply.text) <= budget.max_chars and "333" in reply.text
