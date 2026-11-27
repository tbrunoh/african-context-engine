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

The design is published in [docs/v2](docs/v2/README.md). Every service covers every country by default and names the gap wherever open data does not exist.

### 2.4 preview (2.4.0b1 to 2.4.1, 27 November 2026): ACE as a public product

- [x] The site at ace.korext.com: a phone for USSD, SMS, voice, WhatsApp and RCS, coverage, developers, status and about pages
- [x] 2.4.0b2: the ACE mark as the favicon, the phone icons and a web app manifest
- [x] 2.4.0b3: a new instance loads the published snapshot set before its first request
- [x] 2.4.1: the emergencies a final audit found missing, every number on an Arabic USSD screen, no false alarm on a phone call or a crop, a place ACE does not know asked about, a monthly spending cap that acts, and a release gate that checks the commit on the site and MCP
- [x] Private web sessions, a production factory that refuses unsafe settings, and no phone number trusted from an unauthenticated caller
- [x] Firestore sessions with a 24 hour expiry, escalation counts with no text, and checked snapshot sets swapped in without a restart
- [x] MCP over Streamable HTTP, a facility index, the model off for USSD and voice, citations with licence and date
- [x] Fire, drowning, stabbing and road accidents in the safety rail, in all 32 languages, with red team messages
- [x] The relevance test: no fact on another topic
- [x] deploy/gcp: the same stack in any Google Cloud project, a monthly spending cap and a weekly model check
- [ ] Fluent speaker and clinician review, language by language, lifting the preview label
- [ ] Real phone numbers, country by country, after each privacy review

### 2.3 preview (2.3.0b1, 26 November 2026): 24 languages, and honesty about the rest

2.3.0b2 (27 November 2026) removes the last defaults that assumed a caller is in Kenya: in the MCP tools, local format numbers, the playground, the command line and `Engine.ask`.

- [x] Hausa, Yoruba, Igbo and Nigerian Pidgin in Nigeria; isiZulu, isiXhosa, Afrikaans, Sesotho, Setswana and Xitsonga in South Africa; Setswana in Botswana; Afrikaans in Namibia; Shona in Zimbabwe; Akan and Ewe in Ghana; Ewe in Togo; Wolof in Senegal; Dyula in Côte d'Ivoire and Burkina Faso; Mooré in Burkina Faso; Pular in Guinea; Yoruba in Benin; Chichewa in Malawi and Zambia; Bemba in Zambia; Xitsonga in Mozambique; Kinyarwanda in Rwanda; Kirundi in Burundi; Luganda in Uganda; Lingala in DR Congo; Tigrinya in Ethiopia
- [x] Every template, safety phrase, command and Africa pack fact in each, and 13 red team and 7 ordinary benchmark messages each
- [x] Language detection within the caller's country, ties between close languages resolved by the country's order, and double weight for Nigerian Pidgin and Afrikaans markers against English and for Lingala against Swahili
- [x] African Latin letters folded into GSM-7, so replies keep 160 characters a segment
- [x] A message with no marker word read by its letters, among the country's languages
- [x] ACE says when it does not read a language, from character profiles of 49 languages its callers speak, names the languages it reads and gives the emergency numbers; an optional Cloud Translation or GlotLID check confirms
- [x] Every benchmark red team message escalates in all 32 languages, no false alarm on the benchmark's ordinary messages, no wrong numbers
- [x] Nine independent reviews of the draft, with their fixes: Dyula comfort lines, false alarm words, marker collisions, command words, Ewe letters, messages the new check had turned away, emergencies the safety rail missed, and numbers given to callers outside ACE's countries
- [x] The WAXAL check reads each language as from a country where it is spoken; 4 safety rail firings in 12,333 real texts; 46.6% of sentences in languages ACE does not speak now told so
- [x] Voices for 12 of the 24 through Gemini 3.8 Flash TTS, Afrikaans also through a Cloud voice, and speech to text for 16 more languages, 23 of the 32
- [ ] Fluent speaker review of all 24, with Mooré, Bemba, Dyula, Pular and Wolof first
- [ ] Umbundu for Angola, written or checked by a fluent speaker
- [ ] A fluent listener for each of the 12 new voices before a public voice line
- [ ] Profiles for Lusoga, Sidama and Wolaytta, and a fuller one for Runyankole, once open text exists
- [ ] A paged USSD language menu, so countries with more than four languages list them all

### 2.2 preview, third build (2.2.0b3, 26 November 2026): RCS and the tokenizer audit

- [x] RCS with SMS fallback: switched on per country, a reachability check before each reply, replies composed to the SMS budget, and signed webhooks
- [x] The ACE tokenizer audit: 59 African language varieties on nine released tokenizers, ACE's own text and SMS, and an offline check for unreleased tokenizers

### 2.2 preview (25 November 2026): speech and translation

- [x] Language check on 12,333 sentences of real speech text from WAXAL, with counts published and no text stored
- [x] Colliding marker words removed, cutting how often ACE claims a language it does not speak from an average of 54.0% to 45.8% across 23 languages
- [x] Speech to text, text to speech and translation interfaces, with Google Cloud providers behind an optional extra
- [x] The voice line speaks only languages with a known voice; operators declare more in `ACE_VOICE_LANGUAGES`
- [x] Back translation reports for fluent reviewers, `ace locales backcheck`
- [x] Amharic and Somali on the voice line through Gemini 3.8 Flash TTS, played from a cache (2.2.0b2)
- [ ] A language guess trained on the WAXAL train splits that says it does not know instead of guessing a neighbour language
- [ ] Back translation reports for all five new languages, once a Google Cloud project is connected

### 2.1 preview (24 November 2026): 34 countries, eight languages

- [x] 21 countries: DR Congo, Malawi, Burundi, Cameroon, Benin, Zambia, Chad, Guinea, Burkina Faso, South Sudan, Ethiopia, Mozambique, Guinea-Bissau, Angola, Somalia, Sudan, Algeria, Egypt, Libya, Morocco and Tunisia, each with an emergency pack and all six services
- [x] Portuguese, Arabic, Amharic, Afaan Oromo and Somali, one locale file each, across the safety rail, commands, Scam Shield, services, USSD and voice prompts
- [x] GSM-7 folding for Latin script and UCS-2 budgets for Arabic and Amharic
- [x] Five data problems designed around: country wide warning outlines, broken polygons, misplaced facilities, thin price lists and unlicensed registries
- [x] Malawi and Zambia facility registry connector, held until each ministry confirms reuse
- [x] Red team and false alarm sets in all eight languages

### 2.0 preview (24 November 2026)

- [x] Connector framework, dated and checksummed snapshots, a licence register and credits in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md)
- [x] Weekly number watcher
- [x] Public benchmark per country and language, tracked in CI
- [x] Places for the first 13 countries
- [x] Rain this week, official warnings, nearest health facility, market prices, pregnancy companion and crop problem check, as a preview
- [x] Grounding API routes and MCP tools for every service

### Phase 1, foundations: December 2026 to February 2027

- [ ] Signed packs
- [ ] Fluent speaker review of every rendering in the 31 languages other than English and every safety phrase
- [ ] Written confirmation from the Malawi and Zambia ministries of health to reuse their facility registries
- [ ] A facility list for Algeria, Egypt, Libya, Morocco and Tunisia from an open source with a clear licence
- [ ] Mali and Niger, with the same data as their neighbours
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
- [ ] Voice pilot with keyword spotting for danger words, starting in Swahili and French on Chirp 3
- [ ] Amharic and Afaan Oromo speech recognition tuned on WAXAL, and a voice for Afaan Oromo, which no Google model speaks
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

- [ ] Gikuyu, Dholuo and Luhya; Sheng keywords across packs
- [ ] Livestock and land rights packs
- [ ] Mobile money payments as an optional plugin (moved out of the core in V1 to keep credentials out of the default install)
- [ ] More countries, added as contributors who can source and review the packs come forward
- [ ] Governance moves to a neutral foundation, with a published review council for safety critical packs
