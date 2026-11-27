# ACE agent rules

These rules apply to every AI coding agent working in this repository, including Google Antigravity, Claude Code and any tool that reads AGENTS.md. Human contributors follow the same rules through [CONTRIBUTING.md](CONTRIBUTING.md).

## What ACE is

ACE is an open source safety and decision layer for people on any phone in Africa (USSD, SMS/RCS, voice, WhatsApp and MCP). It covers 34 countries in 32 languages: English, Swahili and French in the code, and 29 more in `src/ace_engine/locales/` (see [docs/languages.md](docs/languages.md)). Six decision services run on dated public data; see [docs/services.md](docs/services.md). The [V2 design](docs/v2/README.md), the [2.1 design](docs/v2/release-2.1.md) and the [build plan](docs/v2/build-plan.md) set out the rest. Every service covers all 34 countries by default and names the gap wherever data does not exist: never build for one country first.

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
10. **Keep languages in step.** Every user facing string exists in every supported language: English, Swahili and French in the code, every other language in its file in `src/ace_engine/locales/`. `i18n.missing()` must stay empty and every placeholder must survive translation. See [docs/languages.md](docs/languages.md).
11. **Fit the phone.** 182 characters per USSD screen, three SMS segments, short spoken turns. Arabic and Amharic travel as UCS-2: about 80 characters per USSD screen and 67 per SMS segment. Latin script is folded into GSM-7 before it leaves. RCS replies use the SMS budget, so falling back to SMS never cuts them.
12. **Reach by default, richer by choice.** Every answer, service and safety feature works on USSD, SMS and voice, which reach any phone without data. WhatsApp, RCS and apps built on the API are optional layers for people with a smartphone and data. RCS always falls back to SMS and stays off until an operator lists its countries in `ACE_RCS_COUNTRIES`.
13. **Pass the checks before proposing a change.** Run `ruff check src tests benchmark`, `ace packs validate`, `pytest -q` and `python -m benchmark.run --quick`. All must pass.
14. **Commits name only their human authors.** Add no co-author or session lines for an AI tool. An AI tool that helped with a change is not listed as a contributor.

## Where things live

| Path | What it holds |
| --- | --- |
| `src/ace_engine/engine.py` | The pipeline: country, safety rail, commands, the unread language check, Scam Shield, retrieval, composition |
| `src/ace_engine/safety.py`, `scam.py` | The safety rail and Scam Shield |
| `src/ace_engine/countries.py` | The 34 countries, their dialling codes and languages |
| `src/ace_engine/i18n.py`, `locales/`, `encoding.py` | Added languages, one file each; GSM-7 and UCS-2 budgets |
| `src/ace_engine/langid/` | Character profiles (CC BY-SA 4.0, built by `benchmark/langid/build.py`) for reading a message by its letters and telling a language ACE does not speak |
| `src/ace_engine/context/` | Pack loading, schema checks and retrieval |
| `src/ace_engine/channels/` | USSD, SMS, RCS, voice and WhatsApp adapters; RCS with SMS fallback |
| `src/ace_engine/server.py`, `mcp_server.py` | The web server, JSON API and MCP server |
| `src/ace_engine/connectors/` | V2 connectors, the only code that touches the network |
| `src/ace_engine/snapshots/` | The snapshot store and the licence register loader |
| `src/ace_engine/services/` | V2 decision services, one module each, and the hub that routes to them |
| `src/ace_engine/places.py`, `watch.py` | Places by name or position; the number watcher |
| `src/ace_engine/speech/` | Speech and translation interfaces, the support table per language, optional Google Cloud providers and the back translation report |
| `context_packs/` | Sourced YAML packs, CC BY 4.0 |
| `snapshots/` | Dated snapshots and `register.yaml`; ODbL data in `snapshots/odbl/` |
| `benchmark/` | Red team and false alarm sets, the runner, the CI baseline and the WAXAL language check |
| `docs/v2/`, `docs/services.md`, `docs/connectors/` | The V2 design, the services guide and one page per connector |

Speech providers sit in the channel layer, like an SMS gateway: they turn audio into text before the safety rail and text into audio after the reply. Machine translation runs only in review tools, never while answering a person. See [docs/speech.md](docs/speech.md).

## Writing style for docs and user facing text

Plain words a reader understands at first glance. Headlines state the point. No em dashes, no contractions, and no double quotes in prose. Never start a sentence with And.

## Visual identity: Coast to Dunes

Every graphic, page and badge uses the Coast to Dunes palette on a clean white ground.

| Name | Hex | Use |
| --- | --- | --- |
| Lamu Tide | `#006B69` | The mark, links, buttons and the main accent |
| Congo Canopy | `#364E3C` | Secondary accent and depth |
| Mara Gold | `#BE823C` | Warm accent for shapes, rules and large display only; use `#8F5E24` when gold must be small text |
| Sahara Sand | `#E8C69F` | Soft surfaces; `#FAF4EC` for warm panels |
| Rift Basalt | `#253239` | Text and contrast; `#56636A` for secondary text |

Lead with Lamu Tide on white. Use gold as an accent, not a second primary. Headings use a serif (Newsreader, then ui-serif and Georgia); text uses Inter or the system sans. Keep text at WCAG AA contrast or better. Emergency states may keep a clear danger red, because a safety signal must never read as decoration.

Diagrams follow the same rules:

- Draw at 1000 units wide. GitHub shows a README image at about 840 pixels, so body text is at least 14 units and small capital labels at least 11 units.
- Set every word as outlines in Inter or Newsreader. GitHub cannot load web fonts inside an image, so live text falls back to whatever the reader has installed.
- Use solid Lamu Tide for the one panel that matters, white cards with a warm hairline for everything else, and a pale tide wash to highlight. No gradients.
- Keep monospace for code only. Labels, numbers and tags use Inter.
- Give every image an alt text, and a title inside the SVG, that says what it shows.

