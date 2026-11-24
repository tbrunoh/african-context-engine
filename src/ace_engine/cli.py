"""The ace command line.

    ace ask "Armyworm is eating my maize"          one grounded answer, with sources
    ace chat --channel ussd                         talk to ACE in the terminal as a phone would
    ace scam "Your SIM is registered twice..."      Scam Shield verdict
    ace serve --port 8000                           web server, channel webhooks and playground
    ace packs validate [paths]                      check packs before a pull request
    ace packs list                                  what is loaded
    ace demo                                        one person, several channels, one memory
    ace tips list --file tips.jsonl                 review community tips

Packs load from ./context_packs, or from the folders given with --packs.
Everything runs offline with no model and no API key.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .channels import SmsAdapter, UssdApp, VoiceAdapter, WhatsAppAdapter
from .context.packs import check_file, pack_files
from .countries import COUNTRIES, default_language
from .engine import Engine, EngineConfig
from .models import Channel, Message
from .scam import analyse
from .tips import TipQueue

DEFAULT_PACKS = [
    Path.cwd() / "context_packs",                                # a checkout or a deployment folder
    Path(__file__).resolve().parent / "context_packs",           # packs bundled in the wheel
    Path(__file__).resolve().parents[2] / "context_packs",       # an editable install
]


def _pack_roots(given: list[str] | None) -> list[Path]:
    if given:
        return [Path(p) for p in given]
    for root in DEFAULT_PACKS:
        if root.exists():
            return [root]
    sys.exit("No context packs found. Pass --packs PATH or run from the repository root.")


def _engine(args: argparse.Namespace) -> Engine:
    country = (args.country or "").upper() or None
    if country and country not in COUNTRIES:
        sys.exit(f"Unknown country {country}. Covered: {', '.join(COUNTRIES)}")
    if getattr(args, "phone", "unset") is None:  # a sample number in the chosen country
        args.phone = f"+{COUNTRIES[country or 'KE'].dial}700000001"
    config = EngineConfig(country=country)
    tips = TipQueue(getattr(args, "tips_file", None))
    return Engine.from_packs(*_pack_roots(args.packs), config=config, tips=tips)


def cmd_ask(args: argparse.Namespace) -> int:
    engine = _engine(args)
    reply = engine.handle(Message(channel=Channel(args.channel), sender=args.phone, text=" ".join(args.text),
                                  language=args.language))
    if args.json:
        print(json.dumps(reply.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(reply.text)
    if reply.citations:
        print("\nSources:")
        for c in reply.citations:
            print(f"  [{c.review_status}] {c.source}" + (f"\n      {c.source_url}" if c.source_url else ""))
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    engine = _engine(args)
    channel = Channel(args.channel)
    print(f"ACE {__version__} | channel: {channel.value} | {len(engine.packs)} packs, {len(engine.store)} facts")
    print("Type a message. Ctrl+D or 'exit' to quit.\n")
    if channel is Channel.USSD:
        return _ussd_loop(engine, args.phone)
    adapter = {Channel.SMS: SmsAdapter(), Channel.WHATSAPP: WhatsAppAdapter(),
               Channel.VOICE: VoiceAdapter()}.get(channel)
    while True:
        try:
            text = input("you > ").strip()
        except EOFError:
            print()
            return 0
        if text.lower() in ("exit", "quit"):
            return 0
        reply = engine.handle(Message(channel=channel, sender=args.phone, text=text))
        parts = adapter.render(reply) if adapter else [reply.text]
        for i, part in enumerate(parts, start=1):
            label = f"ace [{i}/{len(parts)}]" if len(parts) > 1 else "ace"
            print(f"{label} > {part}")
        print(f"      ({reply.kind.value}; {len(reply.citations)} source{'s' if len(reply.citations) != 1 else ''})\n")


def _ussd_loop(engine: Engine, phone: str) -> int:
    app = UssdApp(engine)
    path: list[str] = []
    while True:
        screen = app.respond(phone, "*".join(path))
        print("+" + "-" * 34 + "+")
        for line in screen[4:].split("\n"):
            while line:
                print(f"| {line[:32]:<32} |")
                line = line[32:]
        print("+" + "-" * 34 + "+")
        if screen.startswith("END"):
            print("(session ended; starting a new one)\n")
            path = []
            continue
        try:
            entry = input("reply > ").strip()
        except EOFError:
            print()
            return 0
        if entry.lower() in ("exit", "quit"):
            return 0
        path.append(entry)


def cmd_scam(args: argparse.Namespace) -> int:
    engine = _engine(args)
    report = analyse(" ".join(args.text), args.sender)
    reply = engine.scam_reply(report, args.language or default_language(engine.config.country),
                              engine.config.budgets[Channel.WHATSAPP], engine.config.country)
    print(reply.text)
    print(f"\nverdict: {report.verdict.value}  score: {report.score}  signals: "
          f"{', '.join(s.id for s in report.signals) or 'none'}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .server import serve

    serve(_engine(args), host=args.host, port=args.port)
    return 0


def cmd_packs(args: argparse.Namespace) -> int:
    roots = _pack_roots(args.packs or None) if args.action != "validate" or not args.paths else \
        [Path(p) for p in args.paths]
    if args.action == "validate":
        failed = 0
        for path in [p for r in roots for p in pack_files(r)]:
            report = check_file(path)
            facts = len(report.pack.facts) if report.pack else 0
            print(f"{'PASS' if report.ok else 'FAIL'}  {path}  ({facts} facts)")
            for e in report.errors:
                print(f"      error: {e}")
            if args.strict:
                for w in report.warnings:
                    print(f"      warning: {w}")
            elif report.warnings:
                print(f"      {len(report.warnings)} warning(s); run with --strict to list them")
            failed += not report.ok
        return 1 if failed else 0
    engine = Engine.from_packs(*roots)
    for p in engine.packs:
        by_status: dict[str, int] = {}
        for f in p.facts:
            by_status[f.review_status.value] = by_status.get(f.review_status.value, 0) + 1
        langs = sorted({lang for f in p.facts for lang in f.languages})
        print(f"{p.id:<28} v{p.version:<7} {len(p.facts):>3} facts  {','.join(langs):<6} "
              f"{', '.join(f'{k}:{v}' for k, v in sorted(by_status.items()))}")
    return 0


def cmd_tips(args: argparse.Namespace) -> int:
    queue = TipQueue(args.file)
    for tip in queue.pending():
        print(f"{tip.received_at}  {tip.language}  {tip.channel:<8} {tip.text}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    from .demo import run_demo

    for channel, text in run_demo(_pack_roots(args.packs)):
        print(f"[{channel:>9}] {text}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ace", description="ACE, the African Context Engine")
    parser.add_argument("--version", action="version", version=f"ace {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--packs", action="append", help="pack file or folder (repeatable)")
    common.add_argument("--country", default=None,
                        help="pin one country, for example NG or SN (default: detect from each phone number)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ask", parents=[common], help="ask one question")
    p.add_argument("text", nargs="+")
    p.add_argument("--channel", default="api", choices=[c.value for c in Channel])
    p.add_argument("--language", choices=["en", "sw", "fr"])
    p.add_argument("--phone", default=None, help="caller number; its dialling code picks the country")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("chat", parents=[common], help="interactive session")
    p.add_argument("--channel", default="sms", choices=["sms", "ussd", "whatsapp", "voice", "api"])
    p.add_argument("--phone", default=None, help="caller number; its dialling code picks the country")
    p.add_argument("--tips-file", dest="tips_file")
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser("scam", parents=[common], help="check a suspicious message")
    p.add_argument("text", nargs="+")
    p.add_argument("--sender", help="number or name the message came from")
    p.add_argument("--language", choices=["en", "sw", "fr"])
    p.set_defaults(func=cmd_scam)

    p = sub.add_parser("serve", parents=[common], help="run the web server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--tips-file", dest="tips_file")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("packs", parents=[common], help="validate or list packs")
    p.add_argument("action", choices=["validate", "list"])
    p.add_argument("paths", nargs="*")
    p.add_argument("--strict", action="store_true", help="also list warnings")
    p.set_defaults(func=cmd_packs)

    p = sub.add_parser("tips", help="review community tips")
    p.add_argument("action", choices=["list"])
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_tips)

    p = sub.add_parser("demo", parents=[common], help="multichannel walkthrough")
    p.set_defaults(func=cmd_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


def demo_main() -> None:  # the ace-demo script
    sys.exit(main(["demo"]))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
