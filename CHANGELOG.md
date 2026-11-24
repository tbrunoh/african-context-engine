# Changelog

## Unreleased

### Added
- The V2 design in `docs/v2/`: a product spec with twelve decision services built on public data, a data and model catalog, and a build plan for Google Antigravity.
- Six V2 diagrams as SVG in the house style: V2 in one picture, the twelve services, three journeys, the five pillars, the architecture and the roadmap.
- `AGENTS.md`, the rules every AI coding agent follows in this repository.
- `llms.txt`, a plain summary of ACE and its key documents for AI agents and search tools.
- `ACKNOWLEDGMENTS.md`, which credits every organisation whose published work ACE uses today, with links, and lists the sources planned for V2 with the licence and credit each requires.
- A project page at [tbrunoh.github.io/ace](https://tbrunoh.github.io/ace/), linked from the README and `llms.txt`.

### Changed
- `NOTICE`, `DATA_LICENSE.md` and `CONTRIBUTING.md` now explain that third party sources keep their own rights, that a credit is not an endorsement, and that each new source must be credited in the same pull request.
- `ROADMAP.md` now follows the four V2 phases.

## 1.1.0 (2026-11-23)

ACE now serves 13 countries from one deployment: Kenya, Tanzania, Uganda, Rwanda, South Africa, Botswana, Namibia, Zimbabwe, Nigeria, Ghana, Senegal, Côte d'Ivoire and Togo.

### Added
- Country detection from each caller's dialling code. Emergency numbers, menus, packs and the default language follow the caller, and no number from another country is ever given. `EngineConfig(country=...)` still pins one country.
- Twelve new emergency and helpline packs, 54 numbers in all across the 13 countries, each checked against a government, regulator, police, UN or Child Helpline International source on 2026-11-23 and set to expire after a year.
- French across the engine: commands (AIDE, LANGUE FR, ARNAQUE, ASTUCE, SOURCES, SUITE, OUBLIER), safety phrases and replies, Scam Shield signals and verdicts, the USSD menu and voice prompts. Language detection now chooses among English, Swahili and French.
- Continental packs in `context_packs/africa/` for WHO pregnancy danger signs and FAO and ICIPE fall armyworm guidance, in English, Swahili and French. Push-pull is offered only in Kenya, Uganda, Tanzania and Rwanda.
- `refer_queue` on facts and a pack level `countries` list, so guidance shared across countries carries the caller's own national numbers.
- `ace ask --country NG` and `--phone`; the MCP tools `ask_ace`, `check_message` and `emergency_contacts` take a country.
- 51 new tests, including every country's medical, violence and child protection numbers.

### Changed
- Scam Shield cites Safaricom guidance only to callers in Kenya. Elsewhere it tells people to report through their provider's official channel and gives no number it cannot cite.
- `GET /v1/emergency` requires a country unless the deployment pins one, so numbers from different countries are never mixed.
- Contact numbers keep their readable spacing, and two digit national codes such as Senegal's 15, 17 and 18 are valid.
- CI cancels superseded runs on the same branch.

### Known gaps
- Togo has no national ambulance number in the sources checked, so medical emergencies there get the instruction to call the local emergency number or go to the nearest health facility.
- Botswana Police publish two different GBV toll free numbers (0800 600 144 and 0800 600 999). ACE routes GBV to the police on 999 until the conflict is resolved.
- Swahili and French renderings await review by fluent speakers.

## 1.0.0 (2026-11-23)

The first release people can use and build on.

### Added
- Safety rail with phrase rules in English and Swahili for self harm, maternal danger, poisoning, child protection, gender based violence and urgent health cases; replies with verified numbers and raises a human handoff.
- Scam Shield for mobile money messages, with nine signals grounded in Safaricom's published guidance.
- Retrieval with hard filters (review status, expiry, tier, place, season) and BM25 ranking over claims, translations and keywords; action intent boosting and topic coherence.
- USSD menu app, SMS with GSM-7 handling and Africa's Talking sending, voice IVR, WhatsApp Cloud API with signature checks.
- WSGI server for every webhook, a JSON API and a browser playground.
- Grounded generation for any OpenAI compatible model, with a citation and phone number check and extractive fallback.
- MCP tools: `ask_ace`, `search_context`, `check_message`, `emergency_contacts`, `list_packs`.
- Commands in English and Swahili: HELP, LANG, TIP, SCAM, SOURCES, MORE, STOP, FORGET.
- Pseudonymous profiles, deletion on request, community tip queue.
- Pack specification 1.0 and six sourced Kenya packs with Swahili translations.
- `ace` command line: ask, chat (including a terminal USSD simulator), scam, serve, packs, tips, demo.
- Competitive landscape, architecture, channels, safety and privacy docs; 20 good first issues.

### Changed
- Pack specification moved from 0.1 to 1.0 and added the `sourced` review status.
- The placeholder demo pack was replaced by sourced packs.

### Removed
- The M-PESA payment request builder, to keep payment credentials out of the default install. It returns later as an optional plugin.
