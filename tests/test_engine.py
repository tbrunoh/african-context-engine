from datetime import datetime, timezone

from ace_engine import Channel, Engine, EngineConfig, GeoPoint, Intent, KeywordClassifier, Message
from ace_engine.cli import run_demo
from ace_engine.context import ContextFact, ContextStore, GeoScope
from ace_engine.payments import MpesaStkPush, PaymentRequest

WHEN = datetime(2026, 4, 14, 7, 30, tzinfo=timezone.utc)


def make_engine() -> Engine:
    s = ContextStore()
    s.add(ContextFact(id="f1", claim="Highland maize note.", topic="pest", vertical="agriculture",
                      subjects=("maize",), scope=GeoScope(altitude_min_m=1800), source="Test source"))
    s.add(ContextFact(id="f2", claim="Danger sign note.", topic="maternal", vertical="health",
                      source="Test source", safety_critical=True))
    return Engine(s, classifier=KeywordClassifier({
        "armyworm": Intent("agriculture", "pest", "maize"),
        "pregnant": Intent("health", "maternal", None),
    }), config=EngineConfig(country="KE"))


def test_grounded_answer_cites_facts():
    e = make_engine()
    r = e.handle(Message(Channel.VOICE, "0712000001", "armyworm on my maize",
                         location=GeoPoint(-0.4, 36.9, 1950), received_at=WHEN))
    assert "[f1]" in r.text and r.citations[0].fact_id == "f1"


def test_context_carries_across_channels():
    e = make_engine()
    e.handle(Message(Channel.VOICE, "0712000002", "armyworm problem", location=GeoPoint(-0.4, 36.9, 1950),
                     received_at=WHEN))
    r = e.handle(Message(Channel.WHATSAPP, "+254712000002", "here is a photo", received_at=WHEN))
    assert r.citations and r.citations[0].fact_id == "f1"  # same intent and location, different channel
    profile = e.profiles.get_or_create("+254712000002")
    assert profile.channels_used() == [Channel.VOICE, Channel.WHATSAPP]


def test_no_facts_means_no_invention():
    e = make_engine()
    r = e.handle(Message(Channel.SMS, "0712000003", "what about cassava prices", received_at=WHEN))
    assert r.citations == [] and "human expert" in r.text


def test_urgent_message_escalates_before_any_generation():
    e = make_engine()
    r = e.handle(Message(Channel.SMS, "0712000004", "I am pregnant and bleeding", received_at=WHEN))
    assert r.escalated and r.escalation_queue == "health_urgent" and r.citations == []


def test_safety_critical_fact_offers_human():
    e = make_engine()
    r = e.handle(Message(Channel.SMS, "0712000005", "I am pregnant, what should I watch for", received_at=WHEN))
    assert "HELP" in r.text


def test_forget_deletes_profile():
    e = make_engine()
    e.handle(Message(Channel.SMS, "0712000006", "hello", received_at=WHEN))
    assert e.profiles.forget("0712000006") is True


def test_mpesa_stk_request_shape():
    p = MpesaStkPush("174379", "passkey", "https://example.org/cb",
                     clock=lambda: datetime(2026, 4, 14, 10, 30, 0))
    body = p.build_request(PaymentRequest("+254712000000", 450, "ORDER12345", "Biocontrol"))
    assert body["Timestamp"] == "20260414103000" and body["PartyA"] == "254712000000"
    assert body["TransactionType"] == "CustomerPayBillOnline" and body["Amount"] == 450


def test_demo_runs_end_to_end():
    log = dict(run_demo())
    assert "faw-highland-placeholder" in log["voice"]
    assert log["sms"].startswith("This sounds urgent")
