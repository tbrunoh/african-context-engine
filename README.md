# ACE: the African Context Engine

**One open context engine behind every entry point people in Africa already use.**

ACE grounds AI answers in hyperlocal knowledge that global models do not learn: which pest control works at 2,100m in the Rift Valley, what tomatoes cost on Thursdays at Wakulima, how land law changes 30km across a border. It serves that knowledge through any channel: a voice call, USSD, SMS, WhatsApp, a smartphone app, a trusted local agent, interactive radio, or another company's AI assistant through MCP.

> Status: pre-alpha scaffold (v0.1.0). The interfaces are real and tested; the example context pack is placeholder content, not agronomic or medical advice.

## Why ACE exists

- About 1 billion Africans live inside mobile broadband coverage but do not use mobile internet (GSMA, Mobile Economy Africa 2026). Voice, USSD and SMS still reach them.
- Sub-Saharan Africa moved $1.4 trillion through mobile money in 2025 across 1.2 billion registered accounts (GSMA, State of the Industry Report on Mobile Money 2026). Guidance can end in a transaction.
- Open speech models now cover African languages at scale: Meta's Omnilingual ASR (1,600+ languages) and Google's WAXAL dataset (27 Sub-Saharan languages, CC BY 4.0).
- Channels and speech AI are becoming shared infrastructure. Verified local context is still scarce. ACE is that layer, and it is open so operators, governments and builders adopt it instead of rebuilding it.

## Eight entry points, one identity, one memory

| Entry point | Reaches | Adapter |
|---|---|---|
| Voice call | Any phone, any literacy level | `channels/voice.py` |
| USSD | Any phone, no data | `channels/ussd.py` |
| SMS | Any phone, asynchronous | `channels/sms.py` |
| WhatsApp | Smartphone users on the WhatsApp Business Platform | `channels/whatsapp.py` |
| Smartphone app | Camera diagnosis, offline use | planned SDK |
| Trusted agent | Agro-dealers, health workers, extension officers, mobile money agents | planned agent app |
| Interactive radio | One to many broadcast with call-in | planned IVR bridge |
| API and MCP | Partner products and AI assistants | `mcp_server.py` |

Every adapter normalizes into the same `Message` and renders the same `Reply`. Identity is keyed to the phone number, so a person can start on a call, send a photo on WhatsApp and confirm on USSD without repeating themselves.

## Architecture

```
 Entry Layer        voice | ussd | sms | whatsapp | app | agent | radio | api/mcp
        |                        (thin adapters, one Message type)
 Engine             identity -> safety -> intent -> context -> grounded generation -> reply -> memory
        |
 Intelligence       model agnostic router (open speech models, frontier models, on-device models)
 Context Engine     knowledge graph of context facts, scoped by place, altitude, season, subject
 Transaction Layer  M-Pesa, MTN MoMo, Airtel Money, Orange Money connectors
 Safety rail        urgent cases route to a human expert before any generation
```

See [docs/architecture.md](docs/architecture.md).

## Quickstart

```bash
git clone https://github.com/tbrunoh/african-context-engine.git
cd african-context-engine
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,mcp]"
pytest
ace-demo          # one farmer, five channels, one memory, fully offline
ace-mcp --pack context_packs/examples/kenya-maize-demo.yaml   # MCP server over stdio
```

## Open core

| Open source (Apache 2.0) | Commercial terms |
|---|---|
| Channel adapters, engine, router, safety rail | Verified context tier (expert reviewed, outcome checked) |
| Context pack specification and loader | ACE Cloud hosting with uptime commitments and in-country data residency |
| MCP server and API | Support, integration and ACE Verified certification |
| Mobile money connectors | Consented, aggregated outcome analytics |
| Baseline context packs (CC BY 4.0) | The ACE name and Verified mark |

Details: [DATA_LICENSE.md](DATA_LICENSE.md) and [GOVERNANCE.md](GOVERNANCE.md).

## Contributing

Code, adapters, languages and context packs are all welcome. Community facts enter as drafts, move to expert review, then to outcome verification. Contributing experts earn a share of verified tier licensing revenue. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

## Safety

ACE is not a doctor, agronomist or lawyer. Urgent health cases escalate to humans before any model runs. The default trigger list in `safety.py` is a development starter list and must be replaced with clinically reviewed, localized terms before deployment. Report vulnerabilities through [SECURITY.md](SECURITY.md).

## License

Code: [Apache License 2.0](LICENSE). Baseline context packs: CC BY 4.0. Verified tier: commercial license.
