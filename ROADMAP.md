# Roadmap

## V1: a working commons for Kenya

- [x] Engine with safety rail, commands, Scam Shield, filtered BM25 retrieval and channel budgets
- [x] USSD menu app, SMS, voice IVR and WhatsApp, all behind one web server
- [x] Pack specification 1.0 with review status, sourcing, expiry, contacts and translations
- [x] Six sourced Kenya packs in English and Swahili
- [x] Grounded generation with any OpenAI compatible model, with extractive fallback
- [x] MCP server with five tools
- [x] Pseudonymous identity, deletion on request, community tip queue
- [x] Browser playground and terminal USSD simulator

## 1.1: 13 countries

- [x] Country picked from each caller's dialling code, with no number ever borrowed from another country
- [x] Verified emergency and helpline packs for Kenya, Tanzania, Uganda, Rwanda, South Africa, Botswana, Namibia, Zimbabwe, Nigeria, Ghana, Senegal, Côte d'Ivoire and Togo
- [x] French across commands, the safety rail, Scam Shield, USSD and voice
- [x] Continental WHO maternal and fall armyworm packs in English, Swahili and French

## V2: decision services on public data

The design is published in [docs/v2](docs/v2/README.md). Every service covers all 13 countries by default and names the gap wherever open data does not exist.

### 2.0 preview (current release, 24 November 2026)

- [x] Connector framework, dated and checksummed snapshots, a licence register and credits in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md)
- [x] Weekly number watcher
- [x] Public benchmark per country and language, tracked in CI
- [x] Places for all 13 countries
- [x] Rain this week, official warnings, nearest health facility, market prices, pregnancy companion and crop problem check, as a preview
- [x] Grounding API routes and MCP tools for every service

### Phase 1, foundations: December 2026 to February 2027

- [ ] Signed packs
- [ ] Fluent speaker review of every Swahili and French rendering and every safety phrase
- [ ] Clinical review of the maternal and antenatal packs and agronomist review of the crop packs, raising them to expert reviewed
- [ ] Forecast skill benchmark for rain this week against the season average, in every country
- [ ] Persistent profile, tip and handoff stores
- [ ] Applications filed for the Flood Forecasting API, WeatherNext data, the Agricultural Understanding API and a TomorrowNow GAP account
- [ ] Recheck the source links the number watcher flagged at release

Gate: every served number checked against its source within 30 days.

### Phase 2, weather and voice: March to May 2027

- [ ] Rain this week out of preview in every country where it beats the season average
- [ ] Flood warnings, with opt in alerts for flood and official warnings
- [ ] Nearest health facility with services and phone numbers from open national registries
- [ ] Voice pilot with keyword spotting for danger words, starting in Swahili and French
- [ ] Pilot with one programme on a live shortcode, with a human helpdesk behind the safety rail

Gate: 99% recall on voice emergencies.

### Phase 3, farm and health: June to August 2027

- [ ] Planting window and soil and fertiliser advice
- [ ] Pest and disease check for more crops, reviewed by agronomists in each country
- [ ] Food outlook from FEWS NET, and prices for the countries WFP does not cover
- [ ] Pregnancy and newborn companion out of preview, built on WHO SMART Guidelines, with opt in reminders
- [ ] Scam Shield 2 with SIM swap checks and scam wave warnings, plus mobile money packs for MTN MoMo, Airtel Money, Orange Money and Wave
- [ ] Grounding API, with a first partner in test

Gate: every service beats its decision benchmark.

### Phase 4, reach: September to November 2027

- [ ] Health worker assist inside Community Health Toolkit apps
- [ ] Hausa, Yoruba and English voice
- [ ] Opt in alerts across covered countries
- [ ] One health and one farming partner live

Gate: V2 targets met, then the V2.0 release.

## Later

- [ ] Kikuyu, Dholuo and Luhya; Sheng keywords across packs
- [ ] Livestock and land rights packs
- [ ] Mobile money payments as an optional plugin (moved out of the core in V1 to keep credentials out of the default install)
- [ ] More countries, added as contributors who can source and review the packs come forward
- [ ] Governance moves to a neutral foundation, with a published review council for safety critical packs
