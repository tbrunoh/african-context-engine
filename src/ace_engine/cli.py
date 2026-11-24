"""ace-demo: one farmer, five channels, one memory.

Runs offline with the extractive provider and the example pack, so anyone can
see the multichannel flow without credentials or model keys.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .channels import SmsAdapter, UssdAdapter, VoiceAdapter, WhatsAppAdapter
from .context import ContextStore, load_pack
from .engine import Engine, EngineConfig, Intent, KeywordClassifier
from .models import Channel, GeoPoint, Message

DEFAULT_PACK = Path(__file__).resolve().parents[2] / "context_packs" / "examples" / "kenya-maize-demo.yaml"


def run_demo(pack_path: Path = DEFAULT_PACK) -> list[tuple[str, str]]:
    store = ContextStore()
    store.extend(list(load_pack(pack_path).facts))
    engine = Engine(
        store,
        classifier=KeywordClassifier({"armyworm": Intent("agriculture", "pest", "maize"),
                                      "viwavijeshi": Intent("agriculture", "pest", "maize")}),
        config=EngineConfig(country="KE"),
    )
    phone = "0712000000"  # fictional demo number
    when = datetime(2026, 4, 14, 7, 30, tzinfo=timezone.utc)
    farm = GeoPoint(-0.42, 36.95, altitude_m=1950)  # an illustrative highland location

    voice, wa, ussd, sms = VoiceAdapter(), WhatsAppAdapter(), UssdAdapter(), SmsAdapter()
    log: list[tuple[str, str]] = []

    m1 = voice.parse_inbound({"caller": phone, "transcript": "I think armyworm is eating my maize",
                              "language": "en", "call_id": "demo-call"})
    m1.location, m1.received_at = farm, when
    log.append(("voice", " | ".join(voice.render(engine.handle(m1)))))

    m2 = Message(channel=Channel.WHATSAPP, sender="+254712000000", text="Here is a photo of the leaves",
                 received_at=when)
    log.append(("whatsapp", wa.render(engine.handle(m2))[0]))

    m3 = ussd.parse_inbound({"sessionId": "demo", "serviceCode": "*000#", "phoneNumber": phone, "text": "1*2"})
    m3.received_at = when
    log.append(("ussd", ussd.render(engine.handle(m3))[0]))

    profile = engine.profiles.get_or_create(phone)
    log.append(("memory", "Channels used so far: " + ", ".join(c.value for c in profile.channels_used())))
    m4 = sms.parse_inbound({"from": phone, "text": "My child is bleeding after drinking something"})
    log.append(("sms", " ".join(sms.render(engine.handle(m4)))))
    return log


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ACE multichannel demo")
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    args = parser.parse_args()
    for channel, text in run_demo(args.pack):
        print(f"[{channel:>8}] {text}\n")


if __name__ == "__main__":  # pragma: no cover
    main()
