# Changelog

## 2.0.0b2 (2026-11-24): audit fixes

A full audit of the preview against live sources, every service in every country and language, and every link in the repository, the website and the profile.

### Fixed
- **No guessed emergency numbers.** The facility finder fell back to 112 when a country's packs had no general emergency queue, so Botswana, Senegal, Côte d'Ivoire and Togo were told to call a number their packs do not publish. It now gives the medical emergency number from the packs (997, 15 and 1515, 185), and in Togo, where no source publishes one, tells the person to call the local emergency number. The benchmark now fails any service answer that gives a number the country's packs do not publish, checked on the full answer as well as the USSD screen.
- **Namibia's sources.** The regulator page cited for 112, 10111, 106 and 116 no longer shows them. The numbers now cite the UK FCDO (10111 and 112 for police, ambulance and fire) and LifeLine/ChildLine Namibia (106 and 116), both checked on 24 November 2026. ACE now leads with 10111, the number the Namibian Police publish.
- **Facility names.** 3,359 names read Sant├⌐ for Santé, nearly all in Côte d'Ivoire, Senegal and Togo, and 17 read St. Mary'S. The connector repairs both.
- **Hospital order.** Hospitals in an area are listed by size, referral and teaching hospitals first, instead of alphabetically.
- **Place names.** Thiès, Kédougou, Sédhiou, Saint-Louis, Comoé, Denguélé, Gôh-Djiboua, Sassandra-Marahoué, Vallée du Bandama, District Autonome d'Abidjan, Tharaka-Nithi and Northern Cape now carry their official spelling, and Togo's regions read Kara or Plateaux rather than Kara Region. The source spelling still matches.
- **Swahili and French answers.** Market prices name the food and its details in the person's language (Mahindi, Maïs), French counts units correctly (les 90 kg), elides de before a vowel and names the country with its article. The crop check no longer repeats its own label, and French says du flétrissement. Warnings name the authority as a source in French and drop list dashes from authority text.

### Verified
- Every external link in the repository, the website and the profile loads; the only failures from the build machine were sites that refuse automated requests.
- The WHO, FAO, ICIPE, USAID, KMD and ODPC sources behind the packs and the spec still load and still say what ACE cites.
- 366 tests pass. Benchmark: emergency recall 100% in English, Swahili and French, wrong number rate 0, false alarm rate 0, 207 of 207 service checks.

## 2.0.0b1 (2026-11-24): V2 preview

The first V2 release. Six decision services turn dated public data into short, cited answers, and each covers all 13 countries wherever open data exists. Where it does not, ACE names the gap. The services are a preview until they pass the launch gates in the build plan: expert panel review, forecast skill and fluent speaker review.

### Added
- **Six decision services** in `src/ace_engine/services/`: rain this week (ECMWF ensemble), official warnings (national CAP feeds from the WMO register), nearest health facility (Maina et al. 2019), market prices (WFP), a pregnancy companion (WHO 2016 antenatal schedule and danger signs) and a crop problem check (maize, cassava, banana and tomato). The hub runs after the safety rail and Scam Shield and before pack retrieval, asks for the place in the local word when it needs one, and remembers the question.
- **Places for every country**: 346 areas from geoBoundaries and OCHA COD-AB, found by name or by position, with common names such as Abuja, Accra and Kigali.
- **Five connectors** and `ace refresh`, the only code that touches the network. Snapshots are dated and checksummed, every source is in the licence register `snapshots/register.yaml`, and ODbL data lives in `snapshots/odbl/`. A page per connector in `docs/connectors/`.
- **The number watcher**, `ace watch`, and a weekly workflow that opens an issue when a served number is not found on its source page.
- **A public benchmark**, `python -m benchmark.run`: emergency recall per language, wrong number rate, false alarm rate and service checks for every covered country. CI fails on any regression. The first run found that a snake bit my child and its French form were missed by the safety rail; both now escalate.
- **Grounding API and MCP tools**: `GET /v1/services`, `POST /v1/services/<id>`, and seven MCP tools, one per service plus `service_coverage`.
- `ace services`, a coverage table with the reason for every gap.
- Two packs for every country: antenatal care (WHO) and crop pests and diseases (CIMMYT, CABI Plantwise, Bioversity International, IITA, World Vegetable Center), in English, Swahili and French.
- `docs/services.md`, and 84 new tests, all offline.
- A daily `refresh` workflow that keeps the demo snapshots current.

### Changed
- The USSD main menu puts the six services first, then topics, questions, Scam Shield and language. Without snapshots a deployment keeps the V1 menu.
- `Engine.from_packs` loads snapshots from `./snapshots` or the installed copy; pass `snapshots=None` for a packs only engine.
- Citations carry a licence and a date. Profiles remember the last place named and a service waiting for an answer.
- The V2 spec, build plan and roadmap drop the Kenya first framing: every service covers all 13 countries by default.
- The wheel ships the snapshots, so an installed ACE answers without a refresh.

### Known gaps
- Official warnings: Rwanda and Namibia list no CAP feed. South Africa's feed was down and Kenya's was reachable only through an out of date mirror at the release refresh; ACE says it cannot tell until a feed answers.
- Market prices: Botswana has no WFP dataset, and South Africa, Ghana, Namibia and Zimbabwe have no price recent enough to quote.
- Facilities: public facilities only, from a 2019 list, with no phone numbers.
- The number watcher could not reach Botswana Police's magazine PDF or Senegal's health ministry page from the release machine; both load in a browser and still show their numbers. Namibia's numbers sat on a page that no longer shows them, and 2.0.0b2 moves them to sources that do.
- Swahili and French text in the new packs and services awaits review by fluent speakers.

## Design work (24 November 2026)

### Added
- The V2 design in `docs/v2/`: a product spec with twelve decision services built on public data, a data and model catalog, and a build plan for Google Antigravity.
- Six V2 diagrams as SVG in the house style: V2 in one picture, the twelve services, three journeys, the five pillars, the architecture and the roadmap.
- `AGENTS.md`, the rules every AI coding agent follows in this repository.
- `llms.txt`, a plain summary of ACE and its key documents for AI agents and search tools.
- `ACKNOWLEDGMENTS.md`, which credits every organisation whose published work ACE uses today, with links, and lists the sources planned for V2 with the licence and credit each requires.
- A project page at [tbrunoh.github.io/ace](https://tbrunoh.github.io/ace/), linked from the README and `llms.txt`, and two essays on why ACE exists, linked from `llms.txt`.

### Changed
- `NOTICE`, `DATA_LICENSE.md` and `CONTRIBUTING.md` now explain that third party sources keep their own rights, that a credit is not an endorsement, and that each new source must be credited in the same pull request.
- `ROADMAP.md` now follows the four V2 phases.
- The README, `docs/landscape.md` and the V2 product spec carry the latest public figures for FarmerChat, PROMPTS and Miss Baza, checked on 24 November 2026.
- The README gives GSMA's exact usage gap figure, `llms.txt` says the release covers 13 countries rather than serving them, and the V2 spec states its outcomes as aims.

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
