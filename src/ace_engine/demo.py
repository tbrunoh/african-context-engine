"""One person, several channels, one memory.

A farmer in Kenya calls in about armyworm, follows up by SMS in Swahili,
checks a suspicious M-PESA message on USSD, and finally asks ACE to delete
her data. Runs offline against the starter packs.
"""
from __future__ import annotations

from pathlib import Path

from .channels import SmsAdapter, UssdApp, VoiceAdapter
from .engine import Engine
from .models import Channel, Message


def run_demo(pack_roots: list[Path]) -> list[tuple[str, str]]:
    engine = Engine.from_packs(*pack_roots)
    phone = "0712000000"  # fictional demo number
    voice, sms, ussd = VoiceAdapter(), SmsAdapter(), UssdApp(engine)
    log: list[tuple[str, str]] = []

    m = voice.parse_inbound({"caller": phone, "transcript": "Armyworm is eating my maize, what do I do?",
                             "language": "en", "call_id": "demo-call"})
    log.append(("voice", " | ".join(voice.render(engine.handle(m)))))

    reply = engine.handle(Message(channel=Channel.SMS, sender=phone, text="LANG SW"))
    log.append(("sms", reply.text))
    reply = engine.handle(Message(channel=Channel.SMS, sender=phone, text="zaidi"))
    log.append(("sms", " ".join(sms.render(reply))))

    screen = ussd.respond(phone, "9*Safaricom: your line is double registered. Send your M-PESA PIN to 0711000000")
    log.append(("ussd", screen.replace("\n", " / ")))

    profile = engine.profiles.peek(phone)
    used = ", ".join(c.value for c in profile.channels) if profile else "none"
    log.append(("memory", f"One pseudonymous profile across: {used}"))

    reply = engine.handle(Message(channel=Channel.SMS, sender=phone, text="FUTA"))
    log.append(("sms", reply.text))
    log.append(("memory", f"Profile still held: {engine.profiles.peek(phone) is not None}"))
    return log
