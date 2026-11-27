from __future__ import annotations

import pytest

from ace_engine.models import Channel, Message, ReplyKind
from ace_engine.safety import EscalationPolicy


@pytest.mark.parametrize("text, queue", [
    ("I am pregnant and bleeding", "maternal"),
    ("Nina mimba na ninatokwa na damu", "maternal"),
    ("my wife is 7 months pregnant and has fits", "maternal"),
    ("just delivered and heavy bleeding", "maternal"),
    ("my child drank pesticide", "poisoning"),
    ("mtoto amekunywa sumu", "poisoning"),
    ("he swallowed rat poison", "poisoning"),
    ("my husband beats me every night", "gbv"),
    ("nimebakwa", "gbv"),
    ("my daughter was defiled by a neighbour", "child_protection"),
    ("I want to kill myself", "self_harm"),
    ("nataka kujiua", "self_harm"),
    ("my father is not breathing", "health_urgent"),
    ("amezimia na hapumui", "health_urgent"),
    ("bitten by a snake on the farm", "health_urgent"),
])
def test_emergencies_are_caught(text, queue):
    decision = EscalationPolicy().check(text)
    assert decision.escalate and decision.queue == queue, (text, decision)


@pytest.mark.parametrize("text", [
    "which pesticide works on armyworm",
    "how do I store maize",
    "my maize is drying in the sun",
    "pregnancy danger signs",          # a question about signs, not an emergency
    "my child is learning to farm",
    "dawa ya wadudu ni ipi bora",
    "",
])
def test_ordinary_questions_do_not_escalate(text):
    assert not EscalationPolicy().check(text).escalate, text


def test_emergency_reply_uses_verified_numbers(engine):
    reply = engine.ask("I am pregnant and bleeding", sender="+254700000000", channel=Channel.SMS)
    assert reply.kind is ReplyKind.EMERGENCY and reply.escalated
    assert "999" in reply.text and "1199" in reply.text
    assert all(c.fact_id.startswith("ke-emergency-contacts/") for c in reply.citations)


def test_gbv_reply_gives_the_helpline(engine):
    reply = engine.ask("my husband beats me", sender="+254700000000", channel=Channel.SMS)
    assert "1195" in reply.text and "999" in reply.text


def test_child_reply_gives_childline(engine):
    assert "116" in engine.ask("my daughter was defiled", sender="+254700000000", channel=Channel.SMS).text


def test_self_harm_reply_is_supportive_and_gives_numbers(engine):
    reply = engine.ask("I want to end my life", sender="+254700000000", channel=Channel.SMS)
    assert reply.text.startswith("I am really sorry")
    assert "1190" in reply.text and "999" in reply.text


def test_swahili_emergency_reply(engine):
    reply = engine.ask("mtoto amekunywa sumu", sender="+254700000000", channel=Channel.SMS)
    assert reply.language == "sw" and reply.text.startswith("Hii inaonekana kuwa sumu")


def test_handoff_is_raised_without_the_phone_number(engine):
    engine.ask("I am pregnant and bleeding", sender="+254711222333", channel=Channel.SMS)
    event = engine.handoffs.events[-1]
    assert event["queue"] == "maternal"
    assert "254711222333" not in str(event)


def test_safety_runs_before_commands(engine):
    reply = engine.ask("HELP my baby is not breathing", sender="+254700000000", channel=Channel.SMS)
    assert reply.kind is ReplyKind.EMERGENCY


def test_emergency_fits_a_ussd_screen(engine):
    reply = engine.handle(Message(channel=Channel.USSD, sender="+254700000000", text="mtoto amekunywa sumu"))
    assert len(reply.text) <= 178
