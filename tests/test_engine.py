from __future__ import annotations

import pytest

from ace_engine.commands import parse_command
from ace_engine.engine import CHANNEL_BUDGETS
from ace_engine.identity import ProfileStore, normalize_msisdn
from ace_engine.models import Channel, GeoPoint, Message, ReplyKind


def test_grounded_answer_has_citations(engine):
    reply = engine.ask("Armyworm is eating my maize, what do I do?", channel=Channel.SMS)
    assert reply.kind is ReplyKind.ANSWER
    assert reply.citations and all(c.source_url for c in reply.citations)
    assert any(c.fact_id.endswith(("squash-eggs-larvae", "push-pull")) for c in reply.citations)


def test_swahili_question_gets_swahili_answer(engine):
    reply = engine.ask("viwavi wanakula mahindi yangu nifanye nini", channel=Channel.SMS)
    assert reply.language == "sw"
    assert "mahindi" in reply.text.lower() or "viwavi" in reply.text.lower()


def test_unknown_topic_is_admitted_not_invented(engine):
    reply = engine.ask("which football team plays best in the league")
    assert reply.kind is ReplyKind.CLARIFY and not reply.citations
    assert "no checked guidance" in reply.text


def test_greeting_gets_help(engine):
    assert engine.ask("Hello").kind is ReplyKind.SYSTEM
    assert engine.ask("Habari").language == "sw"


@pytest.mark.parametrize("channel", list(CHANNEL_BUDGETS))
@pytest.mark.parametrize("question", [
    "Armyworm is eating my maize, what do I do?", "how do I store maize", "pregnancy danger signs",
    "dalili za hatari kwa mama mjamzito", "someone says they sent me money by mistake", "HELP",
])
def test_every_answer_fits_its_channel(engine, channel, question):
    reply = engine.handle(Message(channel=channel, sender="+254700000000", text=question))
    assert len(reply.text) <= CHANNEL_BUDGETS[channel].max_chars, (channel, len(reply.text), reply.text)


def test_safety_critical_answers_carry_numbers(engine):
    reply = engine.ask("what are pregnancy danger signs", channel=Channel.SMS)
    assert reply.kind is ReplyKind.ANSWER
    assert "999" in reply.text and "1199" in reply.text
    assert reply.text.count("999") == 1


def test_language_command_persists(engine):
    phone = "+254700000101"
    engine.ask("LANG SW", sender=phone, channel=Channel.SMS)
    reply = engine.ask("how do I store maize", sender=phone, channel=Channel.SMS)
    assert reply.language == "sw"


def test_tip_is_queued_with_pseudonym(engine):
    phone = "+254700000102"
    reply = engine.ask("TIP neem leaves help against armyworm in Embu", sender=phone, channel=Channel.SMS)
    assert reply.kind is ReplyKind.SYSTEM
    tip = engine.tips.pending()[-1]
    assert tip.text.startswith("neem leaves") and tip.person != phone and "700000102" not in tip.person


def test_forget_deletes_profile_and_tips(engine):
    phone = "+254700000103"
    engine.ask("TIP plant early", sender=phone, channel=Channel.SMS)
    assert engine.profiles.peek(phone) is not None
    reply = engine.ask("FORGET", sender=phone, channel=Channel.SMS)
    assert reply.end_session
    assert engine.profiles.peek(phone) is None
    assert engine.tips.pending() == []


def test_sources_and_more(engine):
    phone = "+254700000104"
    first = engine.ask("how do I store maize to avoid aflatoxin", sender=phone, channel=Channel.SMS)
    sources = engine.ask("SOURCES", sender=phone, channel=Channel.SMS)
    assert "KALRO" in sources.text or "USAID" in sources.text
    more = engine.ask("MORE", sender=phone, channel=Channel.SMS)
    assert more.kind is ReplyKind.ANSWER
    assert not {c.fact_id for c in more.citations} & {c.fact_id for c in first.citations}
    assert all(c.fact_id.startswith("ke-maize-post-harvest/") for c in more.citations)


def test_more_runs_out_politely(engine):
    phone = "+254700000105"
    engine.ask("when are the long rains", sender=phone, channel=Channel.SMS)
    for _ in range(3):
        last = engine.ask("more", sender=phone, channel=Channel.SMS)
    assert "That is all" in last.text


def test_phone_numbers_are_never_stored_in_clear():
    store = ProfileStore(salt="test-salt")
    store.record_inbound(Message(channel=Channel.SMS, sender="0712345678", text="hi"))
    stored = str(store._profiles)
    assert "712345678" not in stored
    assert store.peek("+254712345678") is store.peek("254712345678")


def test_history_can_be_disabled():
    store = ProfileStore(keep_history=False)
    profile = store.record_inbound(Message(channel=Channel.SMS, sender="0712345678", text="hi"))
    assert profile.history == []


def test_one_identity_across_channels(engine):
    engine.handle(Message(channel=Channel.VOICE, sender="0712000000", text="armyworm"))
    engine.handle(Message(channel=Channel.WHATSAPP, sender="+254712000000", text="more"))
    profile = engine.profiles.peek("254712000000")
    assert profile.channels == [Channel.VOICE, Channel.WHATSAPP]


def test_location_is_remembered(engine):
    engine.handle(Message(channel=Channel.WHATSAPP, sender="0712000001", text="hello",
                          location=GeoPoint(-0.42, 36.95)))
    assert engine.profiles.peek("0712000001").last_location == GeoPoint(-0.42, 36.95)


@pytest.mark.parametrize("number, expected", [
    ("0712345678", "+254712345678"), ("254712345678", "+254712345678"), ("+254 712 345 678", "+254712345678"),
    ("00254712345678", "+254712345678"),
])
def test_normalize_msisdn(number, expected):
    assert normalize_msisdn(number) == expected


def test_normalize_rejects_garbage():
    with pytest.raises(ValueError):
        normalize_msisdn("hello")


@pytest.mark.parametrize("text, name, arg", [
    ("HELP", "help", ""), ("msaada", "help", ""), ("FUTA", "forget", ""), ("lang sw", "swahili", ""),
    ("LUGHA EN", "english", ""), ("TIP plant early", "tip", "plant early"), ("dokezo panda mapema", "tip",
                                                                            "panda mapema"),
    ("SCAM send your pin", "scam", "send your pin"), ("vyanzo", "sources", ""), ("zaidi", "more", ""),
])
def test_commands(text, name, arg):
    cmd = parse_command(text)
    assert cmd is not None and cmd.name == name and cmd.arg == arg


@pytest.mark.parametrize("text", ["help me with armyworm", "check my maize for armyworm", "more rain this year?",
                                  "stop armyworm"])
def test_questions_that_start_with_a_command_word_stay_questions(text):
    assert parse_command(text) is None
