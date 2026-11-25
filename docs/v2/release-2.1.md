# Release 2.1: 34 countries, eight languages

Release 2.1 preview (2.1.0b1, 24 November 2026) takes ACE from 13 to 34 African countries and from three to eight languages. Every new country gets every service on day one, the safety rail and the number line work in every language, and wherever open data does not reach a country, ACE says so in the person's language instead of guessing. The release also fixes five data problems that a bigger map exposed.

This page is the design record: what was added, why, how it works, what was decided, and what is still a gap.

## What changed for a person

A mother in Nampula can text in Portuguese and get the antenatal schedule, the danger signs and Mozambique's 112. A farmer in Amhara can ask in Amharic or Afaan Oromo whether it will rain this week and what is eating the maize. A caller in Mogadishu who writes in Somali that she wants to end her life reaches the safety rail and the numbers Somalia publishes. A family in Assiut can ask in Arabic for food prices in the nearest market. Every one of those answers fits one USSD screen in its own alphabet and cites its source.

## The 21 new countries

The countries were chosen with one test: is there clean, current, open data that turns into a service, beyond an emergency number? The research behind the choice checked the WMO register of alerting authorities, WFP price datasets on HDX, OCHA administrative boundaries and the 2019 public facility list for every country on the continent.

| Group | Countries |
| --- | --- |
| Five with the strongest data | DR Congo, Malawi, Burundi, Cameroon, Benin |
| The next five | Zambia, Chad, Guinea, Burkina Faso, South Sudan |
| Requested by name | Ethiopia, Mozambique, Guinea-Bissau, Angola, Somalia, Sudan |
| North Africa | Algeria, Egypt, Libya, Morocco, Tunisia |

Mali and Niger have comparable data but were not requested, so they stay out of this release.

## Coverage in all 34 countries

Yes means ACE answered with current data at the last refresh. Gap means ACE names the gap and who to ask. `ace services` prints the live table.

| Country | Languages | Rain | Warnings | Facilities | Prices | Pregnancy | Crops |
|:--|:--|:-:|:-:|:-:|:-:|:-:|:-:|
| Kenya | English, Swahili | Yes | Yes | Yes | Yes | Yes | Yes |
| Tanzania | Swahili, English | Yes | Yes | Yes | Yes | Yes | Yes |
| Uganda | English, Swahili | Yes | Yes | Yes | Yes | Yes | Yes |
| Rwanda | English, French | Yes | Gap | Yes | Yes | Yes | Yes |
| South Africa | English | Yes | Gap | Yes | Gap | Yes | Yes |
| Botswana | English | Yes | Yes | Yes | Gap | Yes | Yes |
| Namibia | English | Yes | Gap | Yes | Gap | Yes | Yes |
| Zimbabwe | English | Yes | Yes | Yes | Gap | Yes | Yes |
| Nigeria | English | Yes | Yes | Yes | Yes | Yes | Yes |
| Ghana | English | Yes | Yes | Yes | Gap | Yes | Yes |
| Senegal | French | Yes | Yes | Yes | Yes | Yes | Yes |
| Côte d'Ivoire | French | Yes | Yes | Yes | Yes | Yes | Yes |
| Togo | French | Yes | Yes | Yes | Yes | Yes | Yes |
| DR Congo | French, Swahili | Yes | Yes | Yes | Yes | Yes | Yes |
| Malawi | English | Yes | Yes | Yes | Yes | Yes | Yes |
| Burundi | French, Swahili | Yes | Yes | Yes | Yes | Yes | Yes |
| Cameroon | French, English | Yes | Yes | Yes | Yes | Yes | Yes |
| Benin | French | Yes | Yes | Yes | Yes | Yes | Yes |
| Zambia | English | Yes | Yes | Yes | Gap | Yes | Yes |
| Chad | French, Arabic | Yes | Yes | Yes | Yes | Yes | Yes |
| Guinea | French | Yes | Yes | Yes | Yes | Yes | Yes |
| Burkina Faso | French | Yes | Yes | Yes | Yes | Yes | Yes |
| South Sudan | English, Arabic | Yes | Yes | Yes | Yes | Yes | Yes |
| Ethiopia | Amharic, Oromo, Somali, English | Yes | Yes | Yes | Yes | Yes | Yes |
| Mozambique | Portuguese | Yes | Yes | Yes | Gap | Yes | Yes |
| Guinea-Bissau | Portuguese, French | Yes | Yes | Yes | Yes | Yes | Yes |
| Angola | Portuguese | Yes | Gap | Yes | Gap | Yes | Yes |
| Somalia | Somali, Arabic, English | Yes | Yes | Yes | Gap | Yes | Yes |
| Sudan | Arabic, English | Yes | Yes | Yes | Yes | Yes | Yes |
| Algeria | Arabic, French | Yes | Yes | Gap | Yes | Yes | Yes |
| Egypt | Arabic, English | Yes | Yes | Gap | Yes | Yes | Yes |
| Libya | Arabic, English | Yes | Yes | Gap | Yes | Yes | Yes |
| Morocco | Arabic, French | Yes | Gap | Gap | Gap | Yes | Yes |
| Tunisia | Arabic, French | Yes | Yes | Gap | Gap | Yes | Yes |

| Service | Countries with an answer | Why the gaps exist |
| --- | --- | --- |
| Rain this week | 34 of 34 | None |
| Official warnings | 29 of 34 | Rwanda, Namibia, Angola (INAMET) and Morocco (DGM) list no CAP feed in the WMO register. South Africa's feed was down at the last refresh |
| Nearest health facility | 29 of 34 | The 2019 list covers sub-Saharan Africa only, so Algeria, Egypt, Libya, Morocco and Tunisia have no open list yet. Guinea-Bissau has only 8 facilities in it |
| Market prices | 23 of 34 | WFP publishes nothing for Botswana, Morocco and Tunisia. The latest prices are too old to quote for South Africa (2022), Namibia, Zimbabwe, Ghana (2023), Mozambique, Angola (2020) and Somalia (2021). Zambia's recent prices cover too few staple foods |
| Pregnancy companion | 34 of 34 | None |
| Crop problem check | 34 of 34 | None |

## Emergency numbers: checked, and honest where none exist

Every new country has an emergency pack with the numbers the UK Foreign, Commonwealth and Development Office publishes on its getting help page for that country, checked on 24 November 2026. Each fact expires after a year, and the number watcher rechecks each source weekly.

Three countries need care, and ACE designs around each one:

- **Guinea and South Sudan have no national emergency number.** ACE says so and sends the person to the nearest health facility. It never borrows a number from another country.
- **DR Congo's numbers serve Kinshasa.** The pack says so in its claim.
- **Malawi's lines are unreliable and Sudan's services are disrupted,** as the FCDO warns. The packs carry the warning.

## Eight languages

Release 2.0 spoke English, Swahili and French. Release 2.1 adds the five languages that the new countries need most.

| Language | Native name | Script | Countries where it is offered first or second |
| --- | --- | --- | --- |
| Portuguese | Português | Latin | Mozambique, Angola, Guinea-Bissau |
| Arabic | العربية | Arabic, right to left | Sudan, Egypt, Libya, Algeria, Morocco, Tunisia, Chad, South Sudan, Somalia |
| Amharic | አማርኛ | Ge'ez | Ethiopia |
| Afaan Oromo | Afaan Oromoo | Latin | Ethiopia |
| Somali | Soomaali | Latin | Somalia, Ethiopia |

### How a language is added

English, Swahili and French stay in the code. Every other language lives in one file, `src/ace_engine/locales/<code>.yaml`, with four parts:

- **meta**: name, native name, script, alphabet (GSM-7 or UCS-2), direction, the words that confirm a language switch, and `reviewed: false` until a fluent speaker signs it off.
- **templates**: every user facing sentence, keyed by where it lives in the code, such as `safety.OPENERS.maternal` or `services.prices.THIN`. Each file has 101.
- **phrases**: the words the safety rail, Scam Shield, the service router and the parsers listen for, in 46 groups. They only add to the built in lists; nothing is removed.
- **words**: stopwords and the marker words that help ACE guess the language of a message.

At start up, `i18n.localize` fills every English, Swahili and French dictionary in the code with the matching template from each locale file. `i18n.missing()` checks every live dictionary against every locale file, and the test suite fails if any sentence is missing or if a translation drops a placeholder such as `{numbers}`. A reply with no number in it cannot ship. [docs/languages.md](../languages.md) is the guide for adding a ninth.

### Reading five more languages

- **Arabic** is normalised before matching: the forms of alef fold together, ta marbuta and alef maqsura fold to their base letters, tatweel goes, and Arabic Indic digits become 0 to 9. Common attached prefixes (و, ال, بال, لل, فال, كال, وال) are stripped, so والحامل matches حامل.
- **Amharic** folds the letters that sound the same (ሐ and ኀ to ሀ, ሠ to ሰ, ዐ to አ, ፀ to ጸ), so people who spell a word either way are understood.
- **Language detection** reads the script first: Arabic script is Arabic, Ge'ez script is Amharic. Portuguese, Afaan Oromo and Somali are recognised by marker words. A caller can always switch with LANG and a code, or with the language's own name.
- **Named things** such as a food or a crop are also matched without an Amharic preposition prefix (የበቆሎ is of maize) or a Somali definite ending (galleyda is the maize). Retrieval does not strip words, because a stripped form can collide with another word.

### The safety rail in every language

The red team benchmark now has 12 messages in each added language, covering maternal danger, poisoning, gender based violence, child protection, self harm and urgent illness, and 7 ordinary messages per language that must not raise an alarm. Every message is sent from a number in all 34 countries. Recall is 100% in all eight languages, the wrong number rate is 0 and the false alarm rate is 0.

The number line follows each language's word order: Call 112 in English, 112 ይደውሉ in Amharic, where the verb comes last.

### The alphabet a reply travels in

A text message carries 160 characters in the GSM-7 alphabet, but only 70 in UCS-2, which Arabic and Amharic need. A USSD screen carries 182 GSM-7 characters, or about 80 in UCS-2. ACE now plans for both.

- **Arabic and Amharic** replies get a budget scaled to UCS-2: 80 characters per USSD screen and 67 per SMS segment in a long message. They are composed to fit, never cut in the middle of a sentence.
- **Latin script** replies on SMS and USSD are folded into GSM-7 before they leave: typographic quotes and dashes become plain ones, and accents GSM-7 lacks are dropped (ê becomes e, ç becomes c), while letters GSM-7 has (é, è, à, ù) stay. One stray accent would otherwise switch a whole French or Portuguese message to UCS-2 and more than double its cost.
- The USSD language menu offers at most four languages, the caller's country languages first, each in its own name. Every other language is one message away.

### What the translations are, and are not

The five new languages were written by the maintainers with care, but no fluent speaker or clinician has reviewed them. Every locale file says `reviewed: false`, every new pack translation carries `reviewed: false`, and the validator prints a warning for each one. That is why 2.1 is a preview. Review by fluent speakers, starting with the safety phrases and the maternal danger signs, is the most valuable contribution anyone can make to this release.

## Five data problems, and the design that handles each

A map of 34 countries exposed problems that 13 had hidden. Each fix is in the code, covered by a test, and recorded in the snapshot it affects.

| Problem | What went wrong | What ACE does now |
| --- | --- | --- |
| Warnings drawn around the whole country | Some authorities attach a polygon that covers most of the country even when the alert names two districts, so everyone heard a local warning | When every polygon covers 80% or more of the country's extent and the alert names areas, ACE matches by the names. A country wide outline with no names is treated as national |
| Broken warning polygons | Some feeds send a polygon that is one point repeated, or a line | Rings with fewer than four points, fewer than three distinct points, or no area are dropped before matching |
| Facilities in the wrong place | 2,611 facilities in the 2019 list sit far from where they are, 2,217 of them at latitude 0, longitude 0 | Any facility more than 25 km outside its country, or more than 25 km from the area its own record names, is left out. The names go in the snapshot for review |
| Too few prices to be useful | A country with a recent price for one food looked covered, so ACE quoted a single item as if it were the market | A country needs recent prices for at least two staple foods. Below that, ACE says the prices cover too few foods and names who to ask |
| Registries without a licence | Malawi and Zambia publish national facility registries with positions and phone numbers, but state no licence | The connector is complete and tested, and the licence register holds it with `cleared: false`. `ace refresh` skips it with a held status, and ACE serves the 2019 list meanwhile |

Two smaller problems are handled in the boundaries connector. Contested areas, such as the part of Ethiopia's layer labelled contested, are skipped. Place names published in capitals are written in title case, and the alternative names in each OCHA layer become aliases, so a person can name a place the way they know it.

## Data sources added

| Source | What it feeds | Licence |
| --- | --- | --- |
| OCHA COD-AB for the 21 new countries | Places: 719 areas in all 34 countries | CC BY-IGO |
| CAP feeds of 19 national meteorological services, from the WMO register | Official warnings | Per authority, linked in each snapshot |
| WFP price datasets on HDX for 19 new countries | Market prices | CC BY-IGO |
| Maina et al. 2019, for 16 new sub-Saharan countries | Nearest facility: 84,060 public facilities after the position check | CC BY 4.0 |
| ECMWF ensemble via Open-Meteo, for all new countries | Rain this week | CC BY 4.0 |
| UK FCDO getting help pages, one per new country | Emergency packs | Open Government Licence |
| Malawi and Zambia facility registries | Held until cleared | Not stated |

Algeria's prices come from the Sahrawi refugee camps near Tindouf, the only Algerian markets WFP tracks, so a person in Algiers hears a market more than 1,400 km away and its distance. Boundaries for Algeria, Angola and Morocco show earlier divisions, because the national offices have not yet endorsed the new ones in COD-AB, and Morocco's layer leaves out Western Sahara.

## Decisions

- **Version 2.1.0b1.** New countries, new languages and new connectors are features, so the minor version moves. It stays a preview because the new translations are unreviewed and the 2.0 gates are still open.
- **Every new country gets every service at once.** No country is added with emergency numbers only. Where data is missing, the gap is named.
- **North Africa joins with its gaps visible.** Rain, warnings, prices in three of five countries, the pregnancy companion and the crop check work; the missing facility list is stated.
- **Arabic, not national dialects.** Modern Standard Arabic reaches every Arabic speaking country ACE covers. Dialect phrases for the safety rail are welcome additions to the locale file.
- **Mali and Niger wait.** They were not requested; adding them is one emergency pack and one line in each connector.
- **National registries wait for a licence.** Phone numbers would make the facility finder far more useful, but ACE does not publish data whose terms are not stated.

## Gates before 2.1 leaves preview

1. A fluent speaker reviews each locale file and each pack translation, safety phrases and danger signs first, and sets `reviewed: true`.
2. Field messages in each new language join the red team set, and recall stays at or above 99%.
3. A clinician reviews the maternal danger signs in Portuguese, Arabic, Amharic, Afaan Oromo and Somali.
4. The ministries of health of Malawi and Zambia confirm reuse of their registries in writing, or the connector stays held.
5. The 2.0 gates in the [build plan](build-plan.md) still apply to every service.

## Checks at release

- 443 tests pass, all offline.
- Benchmark: emergency recall 100% in all eight languages, wrong number rate 0, false alarm rate 0, and 1,464 of 1,464 service checks across 34 countries and eight languages.
- `ace packs validate`: 41 packs pass, with a warning for each translation that awaits review.
