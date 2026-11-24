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

## 1.1: 13 countries (this release)

- [x] Country picked from each caller's dialling code, with no number ever borrowed from another country
- [x] Verified emergency and helpline packs for Kenya, Tanzania, Uganda, Rwanda, South Africa, Botswana, Namibia, Zimbabwe, Nigeria, Ghana, Senegal, Côte d'Ivoire and Togo
- [x] French across commands, the safety rail, Scam Shield, USSD and voice
- [x] Continental WHO maternal and fall armyworm packs in English, Swahili and French

## Next: trusted in the field

- [ ] Fluent speaker review of every Swahili and French rendering and every safety phrase
- [ ] Clinical review of the maternal pack and agronomist review of the maize packs, raising them to expert reviewed
- [ ] Persistent profile, tip and handoff stores
- [ ] Evaluation set of real questions with target facts, tracked in CI
- [ ] Pilot with one programme on a live shortcode, with a human helpdesk behind the safety rail
- [ ] Speech input for Swahili and English on the voice line, evaluated on a public benchmark

## Then: wider

- [ ] Kikuyu, Dholuo and Luhya; Sheng keywords across packs
- [ ] Mobile money safety packs beyond Kenya: MTN MoMo, Airtel Money, Orange Money and Wave
- [ ] Newborn danger signs, livestock, and land rights packs
- [ ] An agent mode for extension officers and community health workers
- [ ] Mobile money payments as an optional plugin (moved out of the core in V1 to keep credentials out of the default install)

## Later: a neutral home

- [ ] More countries, added as contributors who can source and review the packs come forward
- [ ] Governance moves to a neutral foundation, with a published review council for safety critical packs
