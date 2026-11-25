# ACE agent rules

These rules apply to every AI coding agent working in this repository, including Google Antigravity, Claude Code and any tool that reads AGENTS.md. Human contributors follow the same rules through [CONTRIBUTING.md](CONTRIBUTING.md).

## What ACE is

ACE is an open source safety and decision layer for people on any phone in Africa. It covers 13 countries in English, Swahili and French over USSD, SMS, voice, WhatsApp, the web and MCP. Release 2.0 preview adds six decision services on dated public data; see [docs/services.md](docs/services.md). The [V2 design](docs/v2/README.md) and [build plan](docs/v2/build-plan.md) set out the rest. Every service covers all 13 countries by default and names the gap wherever data does not exist: never build for one country first.

## Never break these rules

1. **Safety first.** The safety rail in `src/ace_engine/safety.py` runs before anything else. It never needs a model or the network. Nothing may run before it or weaken it.
2. **No answer without a citation.** Every answer cites a fact from a context pack or, from V2 on, a dated snapshot from a registered connector. Fixed system messages are the only exception.
3. **Only connectors touch the network (V2).** Services read snapshots only. Connectors fetch on a schedule and write dated snapshots.
4. **Chances, not certainties.** Forecasts are stated as chances in plain words, never as certainties.
5. **Refer, do not prescribe.** Never give doses, pesticide rates or diagnoses beyond a signed national pack. Refer the person to a helpline, an extension officer or a health worker instead.
6. **Credit every source.** Every fact carries `source`, `source_url` and `checked_on`. A new organisation is added to [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) in the same pull request. From V2 on, every connector also adds `docs/connectors/<name>.md` with access, licence, refresh and fallback.
7. **Respect licences.** Copy nothing whose terms forbid reuse; link to it. Keep ODbL data in its own store. Integrate with AGPL projects over their API, never by copying code.
8. **No secrets.** Keys come from the environment and are never committed, logged or printed.
9. **Never store phone numbers in clear.** Use the pseudonymous profile key.
10. **Keep languages in step.** Every user facing string exists in English, Swahili and French.
11. **Fit the phone.** 182 characters per USSD screen, three SMS segments, short spoken turns.
12. **Pass the checks before proposing a change.** Run `ruff check src tests benchmark`, `ace packs validate`, `pytest -q` and `python -m benchmark.run --quick`. All must pass.

## Where things live

| Path | What it holds |
| --- | --- |
| `src/ace_engine/engine.py` | The pipeline: country, safety rail, commands, Scam Shield, retrieval, composition |
| `src/ace_engine/safety.py`, `scam.py` | The safety rail and Scam Shield |
| `src/ace_engine/countries.py` | The 13 countries, their dialling codes and default languages |
| `src/ace_engine/context/` | Pack loading, schema checks and retrieval |
| `src/ace_engine/channels/` | USSD, SMS, voice and WhatsApp adapters |
| `src/ace_engine/server.py`, `mcp_server.py` | The web server, JSON API and MCP server |
| `src/ace_engine/connectors/` | V2 connectors, the only code that touches the network |
| `src/ace_engine/snapshots/` | The snapshot store and the licence register loader |
| `src/ace_engine/services/` | V2 decision services, one module each, and the hub that routes to them |
| `src/ace_engine/places.py`, `watch.py` | Places by name or position; the number watcher |
| `context_packs/` | Sourced YAML packs, CC BY 4.0 |
| `snapshots/` | Dated snapshots and `register.yaml`; ODbL data in `snapshots/odbl/` |
| `benchmark/` | Red team and false alarm sets, the runner and the CI baseline |
| `docs/v2/`, `docs/services.md`, `docs/connectors/` | The V2 design, the services guide and one page per connector |

`speech/` comes with the voice epic, in the shape the build plan sets out.

## Writing style for docs and user facing text

Plain words a reader understands at first glance. Headlines state the point. No em dashes, no contractions, and no double quotes in prose. Never start a sentence with And.
