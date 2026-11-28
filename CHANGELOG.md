# Changelog

## 2.4.2 (2026-11-27): HTTPS with no port in the address

### Fixed
- **The HTTP to HTTPS redirect still named port 443.** 2.4.1 named the host in the load balancer's redirect, but Google's load balancer adds :443 to the address it writes either way, so http://ace.korext.com/try went to https://ace.korext.com:443/try. The release gate caught it on the live site. The HTTP listener now marks each request with `x-ace-scheme: http` and passes it to `ace-web`, which answers with a permanent redirect to the same path and query on https://ace.korext.com, with no port: 301 for a page, 308 for a POST, so an assistant calling /mcp over HTTP keeps its method. The host is always `ACE_HTTPS_HOST`, never the request's own Host header, so the redirect cannot be pointed anywhere else; the HTTPS listener removes the mark, so no visitor can fake it and loop; and a paused demo still redirects. Without `ACE_HTTPS_HOST`, nothing is redirected, so a local server behaves as before. The release gate also checks that a faked mark over HTTPS is ignored.

## 2.4.1 (2026-11-27): a safer rail, a spending cap and places ACE does not know

2.4.1 follows the final independent audit of 2.4.0b3. The audit found emergencies the safety rail missed and Arabic USSD screens that lost their numbers; both are fixed first. A second independent review of the 2.4.1 draft then found that some of its own changes went too far (lookalikes that hid real reports, place questions asked about ordinary words, a meter that could act on one failed read), and those were fixed before release.

### Fixed
- **The safety rail missed common emergencies.** A heart attack, a stroke, a choking baby, a fit, a person who stops responding, heavy blood loss, electrocution, a person dying, hanging, cutting, poison or all of someone's pills taken, a child who took pills, a threat to kill in Swahili, and labour with bleeding or waters broken got a reply with no number, in English, Swahili and French. Each now gets the emergency reply. The phrases name a person or the emergency itself, so a phone that is not responding, maize that is dying, a cut while cooking or tablets taken for malaria raise no alarm. 34 red team messages join the benchmark.
- **Arabic USSD emergency screens lost their numbers.** The numbers come last in an emergency reply, and the screen was cut from the end, so a fire reported from Egypt, Morocco, Algeria, Tunisia, Chad or Somalia, and 23 of 602 country, language and emergency screens in all, lost at least one number. An emergency screen now drops the advice after its first sentence, then the labels, before it ever drops a number, and every answer screen is sized by the alphabet its own text needs: Arabic text gets the 80 character UCS-2 screen whatever the profile language, and an English or French reply to a caller in Ethiopia or North Africa keeps the full GSM-7 screen. Tests check all 602 screens, and a first time caller reporting seven kinds of emergency in English and in French from every country.
- **Everyday phrases raised false alarms.** Amenipiga simu (he phoned me, the way many scam reports begin) got the gender based violence reply, and so did rape the leafy crop, a message that opens with beats me why and ce qui me frappe; prices that collapsed, seedlings drowning in rain, preventing a bushfire, cooking au feu de bois, a blood test in pregnancy and a child touching a hot stove all set the rail off. None does now, and each joins the ordinary set. A real report that contains one of these phrases still raises the alarm: my husband beats me, what should I do; he called me and said he will kill me.
- **The public MCP server accepted TIP and kept tips in memory.** It now honours `ACE_PUBLIC` and `ACE_TIPS` as the site does, and `ace-mcp` runs with `ACE_PUBLIC=1`, so a public server keeps nothing a caller sends.
- **A place ACE does not know was quietly swapped for the last place named.** Will it rain in Gotham, after a question about Embu, was answered for Embu. ACE now asks again, starting with the name it could not place (Gotham? Which county are you in?), in the caller's language, and waits for the answer. It asks only about a capitalised name that is not an everyday word or a word from its packs, and only once, so armyworm, chez moi or in kiswahili are answered as before. A follow-up that names a known place (What about Nakuru? Et à Kolda ?) gets the same service for that place, and SOURCES after a service answer names the data it came from.
- **Market prices had no distance limit.** Rice in Lagos was answered from a market 1,003 km away. A market more than 150 km from the area named is no longer quoted; a market inside the area counts as near, and a national average still holds, without a distance.
- **The pregnancy service accepted any week count from MCP.** A count outside 1 to 45 is asked again, as the API already did. The API also refuses a misspelt language, and a position that is not a number, with 400 rather than 500.
- **The USSD menu failed in 24 languages.** A caller who chose Hausa, isiZulu or any language without its own service titles got an error on every later screen, emergencies included, since 2.3. Titles now fall back to English, and a test opens the menu and sends an emergency in every language.
- **The HTTP to HTTPS redirect named port 443.** It now names the host, and setup.sh applies the redirect on every run. The port stayed in the address all the same, which 2.4.2 fixes.

### Added
- **A monthly spending cap that acts.** A Google Cloud budget only sends alerts, and the organisation behind ace.korext.com refuses to let one publish to Pub/Sub, so the project meters itself: every ten minutes the spend guard reads month to date usage from Cloud Monitoring, prices it at list prices with no free tier counted, adds the fixed charges, and steps down before the cap ($60 by default): the language model off, then the demo paused with no warm instance, then every request turned away by Cloud Armor, and as a last step the forwarding rules removed. The month's highest level is kept in Firestore, so the level never falls within a month, and a failed read changes nothing until the next run; on the 1st the guard restores everything. Gemini is priced from the tokens ace-web counts for each call, at or above the highest Flash list price, and every reply has a ceiling of 1,024 tokens. The guard holds a custom role with only the permissions it uses.
- **A release gate that checks what it released.** Cloud Build gives the new `ace-mcp` revision the candidate tag too, reaches both new revisions through the load balancer, and checks that the site and MCP both run the commit just built before traffic moves. The commit is baked into the image and no longer set at deploy, so a wrong image cannot report the right commit.

### Changed
- CI installs the MCP extra, so the MCP tests run on GitHub too, and its actions run on Node 24. Recording downloads go only to public HTTPS addresses, redirects included. A public deployment answers an unsigned RCS webhook with 404 rather than naming the missing setting.
- Benchmark: emergency recall 100% on 19,754 messages in 32 languages from numbers in all 34 countries, no wrong numbers, no false alarms on 263 ordinary messages, and all 5,856 service checks.

## 2.4.0b3 (2026-11-27): fresh data from the first request

### Fixed
- **A new instance answered from the snapshots bundled in its image until the published set loaded.** The release gate for 2.4.0b2 caught it: the candidate revision called Kenya's official warnings stale, because its first requests met the bundled warnings from 25 November while the published set, refreshed that hour, was still loading in the background. The site and MCP now load the published set before they take their first request, and warm the facility index off the request path as before; a test starts the app against a published set and checks that it is in use when the app is created. 2.4.0b2 never took traffic; 2.4.0b3 carries its icons and this fix.

## 2.4.0b2 (2026-11-27): the ACE icon everywhere

### Fixed
- **The ACE mark is every icon a browser or phone asks for.** ace.korext.com linked only an SVG icon, so a browser that asks for /favicon.ico, or one that had cached another korext.com icon, showed the wrong one. The site now serves the mark as /favicon.ico (16, 32 and 48 pixels), /apple-touch-icon.png, 192 and 512 pixel app icons and a web app manifest in the Coast to Dunes colours, and every icon link carries the version, so browsers fetch the new icon after each release.
- **`deploy/gcp/setup.sh`, from the first deployment of ace.korext.com.** Service accounts are created a few seconds apart, because a new project may create only a few a minute. The site and MCP are made public by turning off Cloud Run's invoker IAM check, which Google recommends where domain restricted sharing refuses an `allUsers` grant. Where the budget cannot publish its alerts to Pub/Sub for the same reason, it is created with email alerts only, and the README shows how to cap Gemini with a daily request quota until the spend guard can act.

## 2.4.0b1 (2026-11-27): ACE as a public product

2.4 is what runs [ace.korext.com](https://ace.korext.com): a site where anyone can try ACE on a simulated phone, an API and MCP for builders and assistants, and everything a public deployment needs, built from this repository with no fork. The safety rail learns four more emergencies, and an answer must now be on the question's topic.

### Added
- **The site**: a phone that behaves like the real channels at `/` and `/try`, with USSD (the characters a screen carries), SMS (segments and alphabet), a voice call's script, and chat views for WhatsApp and RCS; a country and language picker with a preview label on every language after English; and the sources behind every answer. `/coverage` shows each service, language and emergency number by country, `/developers` the API and MCP, `/status` the running version and the freshness of every dataset, and `/about` the project and the privacy notice. Coast to Dunes colours, self hosted Inter and Newsreader fonts (SIL Open Font License), no inline styles or scripts, and a content security policy on every page.
- **Private web sessions.** The phone never asks for a number: each browser gets a random token in a cookie scoped to `/try`, and its sender is `web:<country>:<token>`, which can never match a real subscriber. `POST /try/forget` deletes the session.
- **`create_app()`**, one factory for every deployment (`gunicorn "ace_engine.app:create_app()"`). In production it refuses to start with the development salt or a short one, or with any sender that lacks its webhook secret or signature key. `ACE_PUBLIC=1` runs a public demonstration: no phone number from an unauthenticated API caller is trusted, and TIP is off.
- **Durable state on Google Cloud** (`pip install "ace-engine[cloud]"`): `FirestoreProfileStore` reads a profile once and writes it once per message, keeps no history, gives every document an expiry 24 hours after its last write, ignores an expired one, and never writes a profile back after FORGET. `CountingHandoffs` counts escalations by queue, country and channel with no text and no person key; the sink interface gains the country.
- **Snapshot sets that change without a restart.** `ace refresh --publish BASE` copies the set in use, refreshes the chosen sources into the copy, checks every snapshot (licence entry, checksum, data date, valid until time for weather and warnings), and publishes the manifest only if the checks pass and no other run changed it; sets older than seven days are deleted, never the one in use. `SnapshotWatcher` loads a new set off the request path and swaps it in, keeping the last good one on any failure.
- **MCP over Streamable HTTP**: `ace-mcp --transport http`, stateless with JSON responses, a `/healthz` route, and host checks (`--allowed-host` or `ACE_MCP_ALLOWED_HOSTS`).
- **Four more safety categories, in all 32 languages**: fire, drowning, stabbing and other violent wounds, and road accidents. A fire gets its own opener and the general emergency numbers as well as any fire line, because many packs list none; the other three get the urgent medical reply. Each language has a red team message for each category, and the benchmark's ordinary set gains lookalikes such as drowning in work and a boss who fired someone.
- **`/v1/countries` and `/v1/status`**, and the version and build commit in `/healthz` and on every page.
- **`deploy/gcp`**: `setup.sh` stands up the whole stack in any project (Cloud Run, a global load balancer with a managed certificate and Cloud Armor, Firestore, Cloud Storage, Cloud Scheduler, regional logs), `cloudbuild.yaml` tests, builds and releases through a candidate revision, `smoke.py` checks a live deployment, and `ace_engine.ops` holds the spend guard (the model off at 90% of the monthly budget, the demo paused at 100%) and the weekly model check, which pins the last Gemini model that passed ACE's grounding checks.

### Changed
- **The relevance test.** An answer whose best fact matches at most one of the question's content words, when the question has a word no fact contains, becomes a clarify: where can I donate blood no longer gets bleeding in pregnancy, and the scam and crop questions an earlier draft refused still get their answers. Questions in languages whose retrieval is weakest now get an honest clarify more often instead of a fact on another topic.
- **The facility finder tags each facility with its area once per snapshot set**, so an area question looks the list up: the largest areas of DR Congo, Nigeria, Ethiopia and South Africa answer in a few milliseconds instead of up to a second.
- **The language model never runs for USSD or voice**, and the provider can ask for the least reasoning a model allows (`ACE_LLM_REASONING_EFFORT`).
- **Pack citations carry the pack's licence and the fact's checked date**, as snapshot citations already did.
- **The USSD screen limit is a value per request**, so threads can no longer mix one language's limit into another's menu; a concurrency test runs in CI.
- **TIP can be switched off** (`EngineConfig(tips=False)` or `ACE_TIPS=off`): TIP is then read as an ordinary message, and help and clarify replies do not offer it.
- **The Dockerfile builds again**: two stages, the snapshots included, gunicorn on `$PORT`, a non-root user, and the build commit in `ACE_COMMIT`. New extras: `serve` (gunicorn) and `cloud` (Firestore); `mcp` adds uvicorn.
- **The playground is replaced by the site**, served by `ace serve` with threads.
- Version 2.4.0b1 in `pyproject.toml`, `ace_engine.__version__` and `CITATION.cff`.

### Fixed before release, from an independent audit
- **A snapshot set swapped in while serving kept no pack facts or emergency numbers**, so crop and pregnancy questions lost their answers and their numbers. Every hub now reaches the engine through `Engine.use_services`, and a test swaps a set and checks the answers do not change.
- **A public server accepted unsigned gateway webhooks**, so a caller could set or forget the profile of any number. With `ACE_PUBLIC=1`, `/ussd`, `/sms`, `/voice` and `/whatsapp` answer 404 unless their secret is set.
- **USSD budgets were scaled for the alphabet twice** in Amharic, Arabic and Tigrinya, so a facility answer showed only part of a name. A screen now carries its full limit, and on a small screen the nearest name and the emergency numbers come before the heading.
- **Safety phrases that fired on ordinary speech** (a song on fire, fire insurance, a crowd that drowned out a speaker, a company drowning in debt, someone who shot a message) no longer do. The broad phrases stay, so my child is on fire, he was shot and she drowned still raise the alarm; a short list of everyday lookalikes is removed from a message before the rules are read. Each lookalike and each real emergency is a test, and the lookalikes are in the benchmark's ordinary set.
- **French questions in Algeria, Morocco and Tunisia were answered in Arabic** when they had no French marker word. French gains marker words such as cette, semaine, pleuvoir, quel and prix, and the weather service reads quel temps fera-t-il. The /try suggestions are in French or Portuguese where a country does not offer English.
- **Automatic on the language picker now clears a language chosen earlier**, and FORGET on /try deletes the browser's session in every country and sets a fresh session cookie, which before carried a malformed value.
- **The spend guard** sets each service's minimum instances to zero on pause and restores them in a new month, MCP answers 503 while paused, and every change carries the etag it read, so the guard and the model check cannot overwrite each other.
- **The services API** answers 400, not 500, for a field of the wrong type.
- **`deploy/gcp`**: argument lists that stopped `setup.sh`, Cloud Armor attached to every backend, the right to run the refresh job with overrides, a snapshot bucket the image user can write, Cloud Run reachable only through the load balancer, TLS 1.2 or later, a build account with no IAM rights, a strict smoke test, and a candidate route that sends /mcp to MCP.

### Benchmarks
- Emergency recall 100.0% on 18,598 emergency messages in 32 languages, with no wrong numbers and no false alarms on the ordinary set, which now includes the new lookalikes; all 5,856 service checks pass.
- WAXAL test split: the language figures are unchanged within 0.2 points, and ACE tells the writer it does not read the language in 46.5% of sentences on average across 12 languages it does not speak. The safety rail fired on 6 ordinary texts, up from 4: an Afaan Oromo insurance definition that names a car accident, and a Yoruba news report of a pastor swept away by water. Both name the emergency itself, so the phrases stay. Two drafts that fired on ordinary stories were removed before release: the bare Akan word for an accident, and a Nigerian Pidgin phrase for a knife cut.
- FLORES-200 devtest: unchanged, with 5 country language sentences of 32,384 read as English and none turned away.

### Not in this release
- **A place ACE does not recognise is not flagged.** In a conversation, a place name ACE cannot find falls back to the last place named, without saying so. Planned for 2.4.1.
- **Fluent speaker review**: the 31 languages after English, and the new safety phrases in them, are unreviewed drafts. Review starts with 2.4 and lifts the preview label one language at a time.
- **A human on the other end**: the public demonstration counts escalations and connects them to no one, and says so.

## 2.3.0b2 (2026-11-27): no default country

ACE no longer assumes that a caller is in Kenya anywhere in the code. Since 2.1 it covers 34 countries, but a few defaults from the first release still pointed at Kenya.

### Fixed
- **The MCP server no longer falls back to Kenya.** `ask_ace` and `check_message` defaulted to Kenya, so an assistant that named no country got Kenyan facts and emergency numbers, and `pest_check` defaulted to Kenyan crops. With no country, `ask_ace` and `check_message` now answer as for a caller outside ACE's 34 countries, as `/v1/ask` has since 2.3, and `pest_check` requires the country, like the other service tools.
- **A number in local format is no longer read as Kenyan.** A number such as 0712345678 took Kenya's dialling code, so its caller got Kenyan numbers wherever they were. It now gets its own private key and no country, unless the deployment pins one with `--country`, which also gives local numbers that country's code.
- **The playground phone asks for a country.** It invented a Kenyan number for every visitor. It now offers all 34 countries, starts with the visitor's own when the browser names a covered country, and takes a sample number in the country chosen.
- **A phone-less emergency sent to `/v1/services` keeps no profile.** It left a profile holding the message text, as `/v1/ask` did before 2.3.
- **`ace ask` and `ace chat` need `--country` or `--phone`**, instead of a Kenyan sample number, and `Engine.ask` with no sender answers as for a caller outside ACE's 34 countries unless the engine pins a country.
- Tests that relied on the Kenyan default now pass a Kenyan number, and new tests hold each fix.

### Changed
- **The release workflow attaches the wheel and source archive to each GitHub release**, so a release no longer waits on a manual upload.
- Version 2.3.0b2 in `pyproject.toml`, `ace_engine.__version__` and `CITATION.cff`.

## 2.3.0b1 (2026-11-26): 32 languages, and honesty about the rest

ACE grows from eight to 32 languages, each offered in the countries that speak it, and learns to tell a language it speaks from one it does not. Every new language is a draft: it passes ACE's own tests and benchmark, but no fluent speaker has reviewed it yet. The guide is [docs/languages.md](docs/languages.md).

### Added
- **24 languages**, one locale file each in `src/ace_engine/locales/`, marked `reviewed: false`, with every template, safety phrase group, Scam Shield phrase, service cue and command: Hausa, Yoruba, Igbo and Nigerian Pidgin (Nigeria); isiZulu, isiXhosa, Afrikaans, Sesotho, Setswana and Xitsonga (South Africa); Setswana (Botswana); Afrikaans (Namibia); Shona (Zimbabwe); Akan and Ewe (Ghana); Ewe (Togo); Wolof (Senegal); Dyula (Côte d'Ivoire and Burkina Faso); Mooré (Burkina Faso); Pular (Guinea); Yoruba (Benin); Chichewa (Malawi and Zambia); Bemba (Zambia); Xitsonga (Mozambique); Kinyarwanda (Rwanda); Kirundi (Burundi); Luganda (Uganda); Lingala (DR Congo); and Tigrinya (Ethiopia), which travels as UCS-2. Each joins its countries after their existing languages, so no country's default changes. Nigerian Pidgin and Mooré keep their commands in English and French, as their speakers use them.
- **Every Africa pack fact in all 24**, each short at most 160 characters and each menu label at most 24, marked `reviewed: false`.
- **ACE says when it does not read a language.** A new module, `ace_engine.langid`, compares a message with character profiles of ACE's 32 languages and of 49 languages ACE does not speak but its callers do, such as Gikuyu, Dholuo, Dagbani, Malagasy and Sepedi. A message plainly closer to one of those gets a short reply, in the caller's country language, that ACE does not read the language yet, which languages it does read there, and the country's urgent health numbers, instead of an answer in a language its writer may not read. The safety rail, commands and Scam Shield still run first. A person who chose a language with LANG, an API message that names its language, and the answer to a question ACE just asked are always read. Links, numbers, capitalised names and the country's place names are removed before a message is judged, a message with two or more English, French or Portuguese marker words is never turned away, and short messages are never judged. In countries where ACE offers Arabic, Amharic or Tigrinya, whose speakers often write them in Latin letters, ACE never turns a message away. Close neighbours whose speakers read an ACE language, such as isiNdebele, Krio, Bambara and Chitumbuka, are left out on purpose.
- **ACE languages from across a border are read and answered.** `countries.ALSO_READ` lists the ACE languages people often write from a neighbouring country, such as Somali and Afaan Oromo in Kenya, Hausa and Fula in Cameroon, and isiZulu for isiNdebele speakers in Zimbabwe. ACE never turns these away, and a message in one with no marker word of the country's own languages is answered in it.
- **Language profiles** in `src/ace_engine/langid/profiles.json`, counts of three letter sequences only, built by `benchmark/langid/build.py` from ACE's own locale and pack text, the FLORES-200 dev split and the Universal Declaration of Human Rights, every download pinned and checked against its SHA-256. The file is shared under CC BY-SA 4.0, because FLORES-200 is. No WAXAL text was used, so the WAXAL check stays a held-out test.
- **An optional language identifier** can confirm before ACE turns a message away: `GoogleLanguageDetector` (Cloud Translation detectLanguage) or `GlotLID`, an open model of more than 2,000 languages that the operator runs on their own server. ACE asks it only about messages it would turn away, and keeps its own judgement if the identifier fails or takes longer than three seconds, credentials included. The Google detector sends at most 500 characters and sends the caller's text to Google Cloud under the operator's project, so an operator who turns it on says so in their privacy notice.
- **Voices for 12 of the new languages.** Gemini 3.8 Flash TTS lists Afrikaans, Hausa, Igbo, Sesotho, Chichewa, Bemba, Kinyarwanda, Luganda, Lingala, Akan, Dyula and Tigrinya, so the voice line plays them, and the Africa's Talking Say action reads Afrikaans with the Cloud voice af-ZA-Standard-A. None has been heard by a fluent listener yet. The other 12 have no voice from either provider, so callers hear the next language of their country with a voice and get the full reply on SMS and USSD in their own language.
- **Speech to text for 16 more languages, 23 of 32 in all**: Chirp 3 for Hausa, Yoruba, isiZulu, isiXhosa, Afrikaans and Wolof; Chirp 2 for Afaan Oromo, Igbo, Luganda, Lingala, Chichewa and Shona; and the older long model for Kinyarwanda, Sesotho, Xitsonga and Setswana, as listed on the Speech-to-Text V2 page on 26 November 2026. Somali moves from the first Chirp model to Chirp 2.
- **The benchmark in 32 languages**: 13 red team and 7 ordinary messages in each new language.
- **Tests for 2.3** in `tests/test_v23_languages.py` and `tests/test_v23_langid.py`.

### Changed
- **Language detection chooses among the caller's country languages.** A short English question from Kenya can no longer be read as Portuguese because it shares a word with Portuguese. A tie between the default and another language goes to the default; a tie between two other languages, such as Sesotho and Setswana, goes to the one the country lists first. A locale can set `marker_weight`; Nigerian Pidgin and Afrikaans count their own marker words double against English, and Lingala against Swahili. Ge'ez text is read as Amharic or Tigrinya by marker words, with Amharic winning a tie.
- **A message with no marker word is read by its letters.** When a message has none of any offered language's marker words, ACE removes names, links and the country's place names, and the closest character profile among the caller's country languages decides, if one is clearly closest. A reply to a question ACE just asked, such as a county name, keeps the language of the question. With guessing among the country's languages, this lifts the WAXAL sentences read correctly from 55.8% in 2.2 to 94.4% for Hausa, from 52.9% to 98.1% for Twi and from 60.4% to 88.1% for Fante, by the results committed with each release in `benchmark/results/waxal.md`.
- **English is read in every country.** In countries whose languages do not include English, such as Senegal, Benin or DR Congo, a message with two or more English marker words and none from the country's languages gets an English reply, and a short English message is never turned away or answered in a language from across the border, emergencies included.
- **An emergency gets the language its safety phrase came from.** When a message's own language has few marker words and the reply would come in English or French, but a safety phrase of another language of the caller's country matched, the emergency reply comes in that language. English, Swahili and French each have their own phrase set for this, so a Swahili emergency in DR Congo is answered in Swahili, and a language the person chose is always kept.
- **Marker words are whole words no neighbour shares.** A marker that splits into two tokens no longer counts, and markers that are common English, French or Portuguese words, or words of another language of the same country, were removed. A test keeps it so.
- **Command words no longer take ordinary messages.** The language command acts only when it stands alone or names a language, because in many languages the word for language also means tongue. A language's bare name works as a command only when longer than three letters, because BEM is Portuguese for well. A TIP message that ends with a question mark is answered as a question. Kinyarwanda and Kirundi use IMPANURO for TIP, because INAMA also means meeting.
- **The LANG menu lists the caller's country languages**, not all 32, so it fits one SMS; on a USSD screen too small for the prompt, the list of codes and names alone is shown. Any other language still works by name or code.
- **SMS and USSD replies are folded before their length is checked**, because folding ŋ to ng or ɲ to ny lengthens a reply, in the message pipeline and in menu service runs alike.
- **The safety rail, service detection, place lookup and Scam Shield read a message once.** With thousands of phrases across 32 languages, each now folds and tokenises the message a single time and caches each phrase, which takes the safety rail from about 65 ms to under 1 ms a message with the same matches.
- **Connectors wait out rate limits, within a cap.** An HTTP 429 waits for the provider's Retry-After, or a minute, before the retry, and waiting is capped at ten minutes for each refresh run, after which a rate limited source fails at once and the last good snapshot stays in place.
- **Chirp and Chirp 2 requests go to us-central1**, where those models run; Chirp 3 and the long model go to the us multi-region.
- **African Latin letters fold into GSM-7**: ɓ, ɗ, ƙ, ƴ, ɛ, ɔ, ŋ, ɖ, ƒ, ɣ, ʋ, ɲ and the dotted vowels of Yoruba and Igbo become their closest GSM-7 letter, so replies keep 160 characters a segment.
- Version 2.3.0b1 in `pyproject.toml`, `ace_engine.__version__` and `CITATION.cff`.

### Fixed
Nine independent reviews of the 2.3 draft found these before release:
- **Dyula comfort lines said the opposite.** The self harm and gender based violence openers began with words that mean it pleases me. They now open with an apology.
- **Everyday words raised false alarms.** Single words such as the Ewe ʋu (blood, also vehicle) and the Dyula joli (blood, also the French word for pretty), idioms that mean does not know anything in about 17 languages, general words for medicine, and the Swahili name Amina, left the safety phrase lists or now need a second word. Ten such messages are now tests that must raise no alarm.
- **The new check turned away messages in ACE's own languages.** A second review found that place names, people's names, links and Sheng could make a Swahili, English or Portuguese message read as Gikuyu or Kikongo, and that the reply gave no emergency number. A third found that ACE languages written from a neighbouring country, such as Somali in Kenya or Hausa in Cameroon, were turned away too, and a fourth that place names alone could move a message such as Kakamega hospital into a cross-border language. The fixes above came from them, and these messages are now tests.
- **English messages from French and Portuguese speaking countries could get the wrong language.** A fifth review found that an English emergency from Benin or DR Congo could be answered in Ewe or Kinyarwanda, and an English question naming a place, such as Homa Bay in Kenya, in Swahili because homa is a Swahili word. English is now read everywhere and marker words are read without the country's place names.
- **A reply to ACE's own question kept its language even when the writer changed language.** A full sentence in another language now wins; a bare place name, such as Garissa, still keeps the language of the question, and a region named like a language, such as Somali in Ethiopia, is read as the place.
- **Two phrases raised alarms on ordinary messages.** The bare English word overdose fired on farm questions about fertiliser or dewormer, so only took an overdose and overdosed count; the Luganda omwana tassa fired without a verb after it, so it was removed.
- **Common emergencies got no emergency reply.** A sixth review found that a snake bite written as nimeumwa na nyoka or nyoka ameniuma, an English mother struggling to breathe or a baby that stopped breathing, a French mon mari me frappe, Swahili bleeding after birth written as damu mingi baada ya kuzaa, and poisoning or breathing messages in Lingala, Akan, Wolof, Amharic, isiZulu, Yoruba and Igbo got a clarify or an unrelated answer. A snake bite is now a snake word and a bite word anywhere in the message, with the common bite verbs of 21 languages, so the forms people write count without each being listed. The missing phrases are in their lists, and the review's 21 messages and 24 more are tests that must escalate.
- **A caller from outside ACE's countries got other countries' numbers.** A message from +44, +1 or +261 could list numbers from every pack. With no known country, ACE now gives only lines that serve everywhere, and otherwise tells the person to call their local emergency number.
- **LANG KIKUYU switched to Swahili**, because any word beginning with ki did, and LANG KI too, though ki is the code for Gikuyu. LANG with one word that names no language ACE speaks now shows the menu of languages it speaks in the caller's country.
- **Place names were missed.** A bare Oyo answering ACE's state question got the help text, because oyo is also a Lingala word, and cities such as Ibadan, eThekwini, Polokwane, Kaapstad, Eldoret, Thika, Touba, Addis Ababa and Amhara in Ge'ez letters, and muHarare got a clarify. Each now finds its area: a place name answering ACE's question always counts, city names are aliases of their province or state, and a prefix meaning in or at, such as Shona mu or Amharic በ, is set aside.
- **More emergencies missed in a seventh review.** English bleeding after giving birth and I want to end it all, Portuguese quero me matar and meu marido me bate in the word order of Mozambique and Angola, Swahili amezirai and dawa ya kuua wadudu, Lingala heavy bleeding and a husband who beats, Luganda njagala kwetta, Akan, Igbo and Nigerian Pidgin poisoning and violence, and snake bites in Kinyarwanda, isiZulu, Somali, Arabic, Luganda, Lingala, Wolof and Igbo got no alarm. Each now escalates and is a test. A draft guard that let an alarm about a farm animal pass silently was dropped before release, because it also silenced people who mention an animal while describing their own emergency: the safety rail never stays quiet to spare a false alarm.
- **Asking for the emergency number in Kenya returned the M-PESA fraud line**, because that fact says numbers more often. A fact that gives emergency lines now counts the words people use for a number, in English, Swahili, French and Portuguese.
- **A caller from outside ACE's countries could still get a country's numbers in an answer**, and the JSON API read a request with no phone as from Kenya. With no known country, answers now leave out facts for one country, and the API reads the country from `phone`, then `country`, and otherwise treats the request as from outside ACE's countries.
- **An eighth review found more.** Common English spellings such as cant breathe, unconcious, kill my self, wanna die and took too many pills got no alarm; each now escalates. Scam replies and the USSD topic menus still gave Kenyan or other countries' numbers to callers from outside ACE's countries; with no known country they now show only guidance that applies everywhere. Yoruba wọn and rẹ fold to the English won and re, so English messages from Nigeria and Benin about winning a prize were answered in Yoruba; they are no longer Yoruba markers, and neither are Afrikaans môre and Setswana gore. JSON API requests with no phone now each get their own session.
- **A ninth review, which compared 724 messages with 2.2, found no emergency 2.2 caught that 2.3 misses**, and three smaller things, now fixed: Somali mas baa i qaniinay got no alarm once mas stopped counting on its own, so mas now counts beside a Somali bite word; a child who took too many pills got the self harm reply instead of the poisoning one; and Arabic written in Latin letters from Egypt or Morocco was answered in English or French, where 2.2 answered in Arabic. MCP questions now each get their own session too.
- **Arabic rain questions went unrouted**, because the cues listed the noun for rain but not the verb, as in هل ستمطر, and in Cairo spelt بالقاهرة was not found. Both now work.
- **A Lingala price question in DR Congo was answered in Swahili**, because ya and na are Swahili markers too. Koyeba, ntalo and masangu are now Lingala markers.
- **Ewe text used the Icelandic letter Ð** where it should use the capital Ɖ, which sent those messages as UCS-2. Fixed, Ð now folds to D, and a test checks that every GSM-7 template and pack translation stays GSM-7.
- **Swahili kerosene poisoning was missed.** The Swahili phrase list had mafuta taa but not mafuta ya taa, the way most people write it, so a child who drank kerosene raised no alarm. Both now count.
- **Afaan Oromo hearing was recorded as missing.** The Speech-to-Text V2 page lists Chirp 2 for om-ET, so a voice line that uses Google speech recognition can now hear spoken Afaan Oromo questions.
- **The registry caveat and your area were not translatable.** `REGISTRY_CAVEAT` in the facility service and `YOUR_AREA` in the warnings service are now localised like every other template.
- **Uganda's forecast went stale** when the daily refresh failed for it; the snapshot is refreshed and the retry above makes the failure less likely.

### Not in this release
- **Umbundu** for Angola: the draft was not good enough to carry safety text, so it waits for a fluent speaker.
- **Better coverage of Lusoga, Runyankole, Sidama and Wolaytta**: no open text was found to profile Lusoga, Sidama or Wolaytta, and Runyankole's profile comes from one short text, so ACE still answers almost all of them in another of its languages that many of their speakers read: Lusoga and Runyankole mostly in Luganda, Swahili or Kinyarwanda, Sidama and Wolaytta in Afaan Oromo or Somali.
- **Answers on another topic**: a question that shares one word with a fact can still get that fact, so where can I donate blood gets bleeding in pregnancy, as in earlier releases. A draft rule that refused such matches also refused good answers to scam and crop questions, so it was dropped; a better test of relevance is planned.
- **Fire, drowning, stabbing and road accidents in the safety rail**: the rail covers medical emergencies, poisoning, violence, child abuse and self harm; these four have no phrases yet, as in earlier releases.
- **Every short city name**: 22 countries have city aliases, but short forms such as Dar, Nbi and Msa are not found yet.
- **A paged USSD language menu**: the menu still shows four languages, so in South Africa Sesotho, Setswana and Xitsonga are one message away with LANG ST, LANG TN or LANG TS.

### Checks
- 820 tests pass. Ruff passes on src, tests and benchmark. All 41 packs validate.
- Benchmark (`benchmark/results/latest.md`): every red team message, 12 to 18 per language in all 32, sent from numbers in all 34 countries, gets the emergency reply with only that country's numbers, no ordinary message raises an alarm, and 5,856 of 5,856 service checks pass. The red team set is small and written for the benchmark, so it shows that no language has a hole in its phrase lists, not how often real emergencies are caught.
- WAXAL test split, 12,333 sentences in 27 sets, each read as from a country where its language is spoken: ACE recognises Amharic and Shona 100%, Akan and Swahili 99.5%, Afaan Oromo 99.0%, Twi 98.1%, Igbo 97.5%, Luganda 97.0%, Tigrinya 95.0%, Hausa 94.4%, Yoruba 91.5%, Fante 88.1%, Fula 76.5%, Lingala 75.7% and Nigerian Pidgin 68.6%, and turns away at most 0.5% of any of its own languages in the countries that offer them. Across 12 languages it does not speak, ACE now tells the writer so in 46.6% of sentences on average, from 100% of Malagasy, 94.9% of Gikuyu, 87.1% of Dholuo, 85.0% of Dagbani and 83.3% of Acholi to none of Lusoga, Runyankole, Sidama and Wolaytta; before, it answered every one of them in one of its own languages. On WAXAL the safety rail fired on 4 ordinary texts: the 3 of 2.2, and a Nigerian Pidgin fable in which a snake bites a file, which the new snake bite rule catches; a real message that names a snake and a bite is almost always an emergency, so the rule stays. On FLORES-200 devtest (`benchmark/results/langid-devtest.md`) ACE turns away no sentence of any ACE language in any country that offers it or reads it from across a border, 141,680 checks in all, and reads 5 country language sentences of 32,384 as English, each because it quotes English names or titles. Thresholds were set on the WAXAL validation split and FLORES-200 dev; the test split was not used to tune them.

## 2.2.0b3 (2026-11-26): RCS and the tokenizer audit

RCS with SMS fallback ships, switched on country by country, and ACE gains a public tokenizer audit: what African languages cost on today's tokenizers, on FLORES-200 and on the text ACE sends.

### Added
- **The ACE tokenizer audit.** [benchmark/tokenizer-audit](benchmark/tokenizer-audit/README.md) measures what 59 African language varieties in FLORES-200 cost against English on nine released tokenizers (o200k, cl100k, Llama 3, Llama 4, Qwen3, Qwen3.5, Gemma 4, DeepSeek-V4 and Mistral Tekken), with 95% intervals, paired tests of each winner, both FLORES-200 splits, Unicode normalisation and native speaker corrections, and on ACE's own service messages and facts, including their cost as SMS. `python audit.py check` scores an unreleased tokenizer offline against a ceiling and an absolute English budget, compares it variety by variety with a previous tokenizer, and exits non-zero when it fails. `summary` derives every headline figure into one file, and `equivalence` confirms the tokenizers that count exactly like one measured (DeepSeek-V3, Gemma 3 and NVIDIA Nemotron 3 Nano). Every download is pinned to a commit and checked against its SHA-256, a fresh run reproduces the committed results byte for byte, and `export_ace_text.py` rebuilds the parallel text from ACE's sources. The release is archived on Zenodo with DOI [10.5281/zenodo.24565738](https://doi.org/10.5281/zenodo.24565738).
- **RCS with SMS fallback.** A new `rcs` channel serves people whose phone and carrier support RCS, in the phone's own messaging app, with the sources under every answer and suggested reply chips (More, Sources, Help) in the person's language that send command words ACE already understands. No chip follows an emergency reply. RCS stays off until an operator lists countries in `ACE_RCS_COUNTRIES`. Before each reply ACE checks that the person can receive RCS, and any reply that RCS refuses or cannot start goes by SMS; a send that times out after Google may have accepted it is not repeated by SMS, so nobody gets a reply twice. RCS replies use the SMS budget, including the UCS-2 budget for Arabic and Amharic, so a fallback never cuts an answer or an emergency number. The `/rcs` webhook answers RCS for Business verification, checks `X-Goog-Signature`, answers 503 until `RBM_CLIENT_TOKEN` is set so unsigned messages can never trigger texts, and always answers an authenticated event with 200, so Google never retries a reply that already went out. See [docs/channels.md](docs/channels.md#rcs-with-sms-fallback).

- **Back translation reports for the five newest languages.** [docs/reviews](docs/reviews/README.md) holds a report for Portuguese, Arabic, Amharic, Afaan Oromo and Somali, 112 strings each with the safety strings marked, run with Google Cloud Translation on 25 November 2026, and a short list of the rows fluent speakers should check first.

### Fixed
- **The Google extra installs.** The speech guide, the review reports and the error ACE prints told people to run `pip install "ace-engine[google]"`, which fails while ACE is not on PyPI and would install whatever package later took that name. They now say `pip install -e ".[google]"` from a checkout.
- **Five emergency numbers were said to callers but not watched.** Côte d'Ivoire's 110 and 111, Kenya's 911 and Zimbabwe's 114 and 0800 3222 911 appeared in answers but not in each fact's contacts, so the weekly watcher never rechecked them. They are now contacts, which brings the count of watched numbers to 110, and a new test fails if any number an emergency fact says is missing from its contacts.
- **The WAXAL language figure is defined.** The 45.8% figure, and the 54.0% before it, is the average claimed rate across 23 languages ACE does not speak, each language counted once, with Tigrinya listed but not averaged. The README, docs/speech.md and the WAXAL report now say so, and the report prints the definition.

### Changed
- **The speech guide says who pays.** Every operator runs ACE in their own Google Cloud project; the repository holds no project or key. [docs/speech.md](docs/speech.md#who-pays-and-how-to-keep-costs-in-check) names the only two places ACE calls a paid Google API, explains why a caller cannot run up the Gemini bill, and sets out a Gemini spend cap, lower Translation quotas (including the separate batch quota), enabling only the APIs you call, a budget alert and the webhook secret before opening a voice line. It also says how to run the Google providers in Cloud Shell.
- **V2 diagrams match what shipped.** The services diagram marks the six preview services, the roadmap lists the open Phase 1 to 4 work, the V2 picture separates the data used today from what comes next, and the architecture diagram shows the decision services step.
- **Channel framing.** The README, AGENTS.md and the architecture diagrams now group entry points by what people have: USSD, SMS and voice reach any phone and are the default; WhatsApp, RCS and apps built on the API serve people with a smartphone and data; the API and MCP serve other services and AI assistants.
- **Coast to Dunes identity.** The README badges, the seven diagrams in `docs/` and the web playground move to a clean white ground in the Coast to Dunes palette: Lamu Tide, Congo Canopy, Mara Gold, Sahara Sand and Rift Basalt. The diagrams are redrawn at 1000 units wide with every word set as outlines in Inter and Newsreader, so they render the same on GitHub, in any browser and in print, and no label falls below a readable size. AGENTS.md records the palette and its rules. The SMS box in the playground now invites any of the eight languages.

### Verified
- 508 tests pass, all offline. Ruff passes on src, tests and benchmark. All 41 packs validate. The quick benchmark shows no regression. A fresh tokenizer audit run reproduces the committed results byte for byte.

## 2.2.0b2 (2026-11-25): Amharic and Somali on the voice line

The newest developer models change the voice picture. Gemini 3.8 Flash TTS lists Amharic and Somali, which no Google Cloud Text-to-Speech voice covers, so the voice line can now speak both. Afaan Oromo is still not listed by any Google speech model.

### Added
- **`GeminiTextToSpeech`**: Gemini 3.8 Flash TTS through the Gemini API, with the key read from `GEMINI_API_KEY` and sent only in the request header.
- **`PlayedVoice`**: synthesises each prompt or fact once, caches it as a WAV file and gives the call a URL to play. Only fixed prompts and public pack text are synthesised, never a caller's words or number.
- **`GET /voice/audio/<file>.wav`** on the server, which serves only cache file names. It is on when `ACE_VOICE_AUDIO_URL` and `GEMINI_API_KEY` are both set.
- `support.yaml` now records two ways to speak each language: `say`, a Google Cloud Text-to-Speech voice that the Africa's Talking Say action reads with, and `play`, a Gemini TTS model. It also notes where Gemini 3.5 Transcribe can hear a language. 9 new tests.

### Changed
- The voice line uses the Say action wherever it can speak the language and plays Gemini audio only where it cannot. If synthesis fails during a call, it answers with Say in a language Say can read.
- `ace voice languages` shows for each language whether the line uses Say, plays Gemini audio, or falls back to the keypad and SMS.

### Verified
- 476 tests pass, all offline. Ruff passes. All 41 packs validate. The quick benchmark shows no regression.

## 2.2.0b1 (2026-11-25): speech and translation

ACE measures its language tools on real African speech, makes the voice line speak only languages a voice exists for, and gains optional speech and translation providers. The design and the gaps are in [docs/speech.md](docs/speech.md).

### Added
- **The WAXAL language check**: `python -m benchmark.waxal` reads up to 600 sentences from each test split of 27 WAXAL sets (Google Research with Makerere University, the University of Ghana, Digital Umuganda, Media Trust, Loud and Clear and AIMS Senegal) at run time and runs ACE's language guess, safety rail and service router on them. Results are in `benchmark/results/waxal.md`, as counts only. No WAXAL text or audio is stored in the repository.
- **`ace_engine.speech`**: `SpeechToText`, `TextToSpeech` and `Translator` interfaces; `support.yaml`, which records for each ACE language the speech recognition model, the voice, the translation model and the WAXAL data that exist, with sources, checked on 25 November 2026; and `speakable()`, the rule the voice line follows.
- **Google Cloud providers** behind the optional `google` extra: Speech-to-Text V2 with Chirp 3 (first generation Chirp for Somali), Text-to-Speech and Cloud Translation Advanced. Credentials come from Application Default Credentials; ACE stores no key.
- **`ace voice languages`**, **`ace locales status`** and **`ace locales backcheck`**. The backcheck lines up every string of a locale file with a machine back translation, lowest word overlap first and safety strings marked, for fluent reviewers. It writes nothing to the locale file.
- `i18n.english_sources()`, the English rendering of every localised string.
- `docs/speech.md`; licence register entries for WAXAL and Google Cloud; 22 new tests.

### Fixed
- **The voice line read scripts no voice could say.** It now speaks a language only where a voice is known to exist (English, Swahili, French, Portuguese and Arabic) or the operator lists it in `ACE_VOICE_LANGUAGES`. A caller who uses Amharic, Afaan Oromo or Somali hears the next language of their country with a voice, then English.
- **ACE claimed languages it does not speak.** On WAXAL, an average of 54.0% of sentences across 23 languages ACE does not speak were read as one of its eight. The Somali markers ka, ku and ay and the French marker ma, which are common in Dagbani, Luganda, Acholi and other languages, are no longer markers, and Swahili and French gained longer marker words. The figure is now 45.8%; Amharic, Swahili and Afaan Oromo are still recognised in 100%, 97.0% and 93.2% of sentences. The rest is a named gap.
- **The benchmark failed when official warnings aged past six hours.** Service checks now run at the time of the newest committed snapshot, so the gate depends on the code and the data, not on the hour it runs.
- **WAXAL licence.** The docs called all of WAXAL CC BY 4.0. Only the University of Ghana sets are; the others are CC BY-SA 4.0. The data catalog, product spec, build plan and acknowledgments are corrected, and the build plan no longer plans Swahili speech recognition on WAXAL, which has no transcribed Swahili.

- **The source archive carried a local file.** The 2.1.0b1 source archive on the release page included `PUBLISH.sh`, a maintainer script with no credentials in it. The source archive now leaves out local files.

### Changed
- `pyproject.toml`: version 2.2.0b1, the `google` extra, and a source archive that leaves out local files.
- README, AGENTS.md, the roadmap, the languages and channels guides, the data catalog and `llms.txt` describe the speech layer.

### Verified
- 467 tests pass, all offline. Ruff passes. All 41 packs validate.
- Benchmark: emergency recall 100% in all eight languages from numbers in all 34 countries, wrong number rate 0, false alarm rate 0, 1,464 of 1,464 service checks.
- WAXAL check: the safety rail fired on 3 of 12,333 ordinary sentences (0.02%): an Amharic sentence about female genital cutting, a Swahili story with a snake bite, and a Fula sentence containing bofti, the Afaan Oromo word for snake.

## 2.1.0b1 (2026-11-24): 34 countries, eight languages

ACE grows from 13 to 34 African countries and from three to eight languages. Every new country gets all six services at once, the safety rail works in every language, and wherever open data does not reach, ACE names the gap. The design record is [docs/v2/release-2.1.md](docs/v2/release-2.1.md). This is a preview: no fluent speaker has reviewed the five new languages yet.

### Added
- **21 countries**: DR Congo, Malawi, Burundi, Cameroon, Benin, Zambia, Chad, Guinea, Burkina Faso, South Sudan, Ethiopia, Mozambique, Guinea-Bissau, Angola, Somalia, Sudan, Algeria, Egypt, Libya, Morocco and Tunisia. Each has dialling codes and languages in `countries.py`, an emergency pack checked against the UK FCDO on 24 November 2026, places from OCHA COD-AB, the ECMWF forecast, and CAP warnings, WFP prices and the 2019 facility list wherever they exist.
- **Five languages**: Portuguese, Arabic, Amharic, Afaan Oromo and Somali, each in one file in `src/ace_engine/locales/` with 101 templates, 46 phrase groups, stopwords and marker words, marked `reviewed: false`. `i18n.py` fills them into the code at start up and `i18n.missing()` checks that nothing is left untranslated. English, Swahili and French stay in the code.
- **Reading the new languages**: Arabic normalisation and prefix stripping, Ge'ez letter folding, language detection by script and marker words, language commands in every language (LANG PT, العربية, አማርኛ), and food and crop matching that sees past an Amharic prefix or a Somali definite ending.
- **The right alphabet for every reply**: `encoding.py` folds Latin script into GSM-7 on SMS and USSD, and scales budgets for Arabic and Amharic, which travel as UCS-2 (80 characters a USSD screen, 67 per SMS segment in a long message).
- **The call verb where the language puts it**: Call 112 in English, 112 ይደውሉ in Amharic.
- **The USSD language menu** offers up to four languages, the caller's country languages first, each in its own name.
- **Pack translations** of the four Africa packs (danger signs, antenatal care, fall armyworm, crop pests) in all five new languages, marked `reviewed: false`, with keywords in each language. The danger signs pack now applies in all 34 countries, and the fall armyworm pack in the 29 sub-Saharan countries and Egypt, where the IPPC confirmed the pest in 2019.
- **The national facility registry connector** for Malawi and Zambia, with phone numbers. It is complete and tested, and held: the licence register marks it `cleared: false` and `ace refresh` skips it until each ministry confirms reuse. The facility finder prefers a cleared registry and shows each facility's phone number.
- **The benchmark in eight languages**: 12 red team and 7 ordinary messages for each new language, every red team message sent from all 34 countries, and service checks in every language. The number check reads number lines in every language, including Amharic, where the numbers come before the verb.
- `docs/v2/release-2.1.md`, `docs/languages.md` and `docs/connectors/national_facility_registry.md`; 57 new tests.

### Fixed: data problems a bigger map exposed
- **Warnings drawn around the whole country.** When every polygon in an alert covers 80% or more of the country and the alert names areas, ACE matches by the names, so a district warning no longer reaches everyone. A country wide outline with no names is treated as national.
- **Broken warning polygons.** Rings that are one point repeated, a line, or have no area are dropped.
- **Facilities in the wrong place.** 2,611 facilities sit far from where they are, 2,217 at latitude 0, longitude 0. Any facility more than 25 km outside its country, or more than 25 km from the area its own record names, is left out and listed in its snapshot.
- **Too few prices to quote.** A country needs recent prices for at least two staple foods; below that, ACE names the gap. Coverage reports it too.
- **Contested areas and capital letters.** Areas a boundary layer labels contested are skipped, names in capitals are title cased, and each layer's alternative names become aliases.

### Changed
- Facility snapshots for all 29 sub-Saharan countries were rebuilt with the position check: 84,060 facilities.
- An answer that names no food lists the nearest market's staples, so every country's diet counts; the benchmark asks that way.
- A food the market does not sell is named in the person's language. French elides de before a vowel in every service.
- Warning text from an authority drops dashes, which read badly as one SMS line.
- SMS replies in Latin script are GSM-7, so a French maternal reply reads Cela peut etre on a phone that cannot show ê.
- `pyproject.toml`: version 2.1.0b1, the 34 countries and eight languages in the description, and Portuguese and Arabic language classifiers.
- README, AGENTS.md, CONTRIBUTING, the roadmap, the services guide, the connector pages, the V2 overview, spec and build plan, the safety and privacy guide and `llms.txt` now describe 34 countries and eight languages.

### Verified
- 445 tests pass, all offline. Ruff passes. All 41 packs validate.
- Benchmark: emergency recall 100% in all eight languages from numbers in all 34 countries, wrong number rate 0, false alarm rate 0, 1,464 of 1,464 service checks.
- The wheel installs in a clean environment with the locale files, and answers an Amharic emergency from an Ethiopian number.

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
