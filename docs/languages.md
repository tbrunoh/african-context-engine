# Languages

ACE answers in 32 languages. English, Swahili and French live in the code. The other 29 each live in one file, `src/ace_engine/locales/<code>.yaml`, so a new language is one file and no code change. Each language is offered in the countries where people speak it, after that country's existing languages.

| Code | Language | Native name | Script | Alphabet on a phone | Countries where it is offered | Reviewed |
| --- | --- | --- | --- | --- | --- | --- |
| en | English | English | Latin | GSM-7 | Kenya, Tanzania, Uganda, Rwanda, South Africa, Botswana, Namibia, Zimbabwe, Nigeria, Ghana, Malawi, Cameroon, Zambia, South Sudan, Ethiopia, Somalia, Sudan, Egypt, Libya | Yes |
| sw | Swahili | Kiswahili | Latin | GSM-7 | Kenya, Tanzania, Uganda, DR Congo, Burundi | Awaiting fluent review |
| fr | French | Français | Latin | GSM-7 | Rwanda, Senegal, Côte d'Ivoire, Togo, DR Congo, Burundi, Cameroon, Benin, Chad, Guinea, Burkina Faso, Guinea-Bissau, Algeria, Morocco, Tunisia | Awaiting fluent review |
| pt | Portuguese | Português | Latin | GSM-7 | Mozambique, Guinea-Bissau, Angola | No |
| ar | Arabic | العربية | Arabic | UCS-2 | Chad, South Sudan, Somalia, Sudan, Algeria, Egypt, Libya, Morocco, Tunisia | No |
| am | Amharic | አማርኛ | Ge'ez | UCS-2 | Ethiopia | No |
| om | Afaan Oromo | Afaan Oromoo | Latin | GSM-7 | Ethiopia | No |
| so | Somali | Soomaali | Latin | GSM-7 | Ethiopia, Somalia | No |
| af | Afrikaans | Afrikaans | Latin | GSM-7 | South Africa, Namibia | No |
| ak | Akan (Twi) | Twi | Latin | GSM-7 | Ghana | No |
| bem | Bemba | Icibemba | Latin | GSM-7 | Zambia | No, lower confidence draft |
| dyu | Dyula | Julakan | Latin | GSM-7 | Côte d'Ivoire, Burkina Faso | No, lower confidence draft |
| ee | Ewe | Eʋegbe | Latin | GSM-7 | Ghana, Togo | No |
| fuf | Pular | Pular | Latin | GSM-7 | Guinea | No, lower confidence draft |
| ha | Hausa | Hausa | Latin | GSM-7 | Nigeria | No |
| ig | Igbo | Igbo | Latin | GSM-7 | Nigeria | No |
| lg | Luganda | Luganda | Latin | GSM-7 | Uganda | No |
| ln | Lingala | Lingala | Latin | GSM-7 | DR Congo | No |
| mos | Mooré | Mooré | Latin | GSM-7 | Burkina Faso | No, lowest confidence draft |
| ny | Chichewa | Chichewa | Latin | GSM-7 | Malawi, Zambia | No |
| pcm | Nigerian Pidgin | Naija | Latin | GSM-7 | Nigeria | No |
| rn | Kirundi | Ikirundi | Latin | GSM-7 | Burundi | No |
| rw | Kinyarwanda | Ikinyarwanda | Latin | GSM-7 | Rwanda | No |
| sn | Shona | chiShona | Latin | GSM-7 | Zimbabwe | No |
| st | Sesotho | Sesotho | Latin | GSM-7 | South Africa | No |
| ti | Tigrinya | ትግርኛ | Ge'ez | UCS-2 | Ethiopia | No |
| tn | Setswana | Setswana | Latin | GSM-7 | South Africa, Botswana | No |
| ts | Xitsonga | Xitsonga | Latin | GSM-7 | South Africa, Mozambique | No |
| wo | Wolof | Wolof | Latin | GSM-7 | Senegal | No, lower confidence draft |
| xh | isiXhosa | isiXhosa | Latin | GSM-7 | South Africa | No |
| yo | Yoruba | Yorùbá | Latin | GSM-7 | Nigeria, Benin | No |
| zu | isiZulu | isiZulu | Latin | GSM-7 | South Africa | No |

Nigerian Pidgin and Mooré keep their commands in English and French, the way most of their speakers use them. Umbundu, planned for Angola, is not in this release: the draft was not good enough to carry safety text, so it waits for a fluent speaker to write or check it.

## How a person picks a language

ACE guesses from the first message, and only among the languages of the caller's country, so a short English question from Kenya is never read as Portuguese. Arabic script means Arabic. Ge'ez script means Amharic or Tigrinya, chosen by marker words, and Amharic wins a tie. In Latin script, marker words choose the language. A tie between the country's default and another language goes to the default. A tie between two other languages, such as Sesotho and Setswana in South Africa, goes to the one the country lists first, because their speakers read each other's language and neither wrote in English. Nigerian Pidgin and Afrikaans share short words such as is and my with English, and Lingala shares its commonest words, na and ya, with Swahili, so their own marker words count double (`marker_weight: 2` in the file). With no marker word at all, ACE reads the message by its letters: it removes names, links and the country's place names, compares what is left with a character profile of each of the country's languages, and of the ACE languages written there from across a border, and takes the one that is clearly closest, or the country's first language when none is. A reply to a question ACE just asked, such as a county name, keeps the language of the question, unless the reply is a full sentence in another language, which then wins. Marker words always win when present, and they are read without the country's place names, so Homa Bay hospital is English even though homa is a Swahili word. English is read in every country: where the country's languages do not include English, a message with two or more English marker words and none from the country's languages gets an English reply, and an English message is never answered in a language from across the border. A person who has chosen a language keeps it until they change it.

Marker words must be common in their language and rare in every other language offered in the same country. A marker counts only as one whole word, so a marker such as b'a, which splits into b and a, does not count. Words that are common in English, French or Portuguese, or in another language of the same country, are not markers: `tests/test_v23_languages.py` fails if one is added. Sesotho and Setswana share some words on purpose, and the country order settles a tie between them.

A person can switch at any time with LANG and a code (LANG ZU), or with the language's own name (isiZulu, Hausa, ትግርኛ). LANG alone lists the caller's country languages. The word for language acts as a command only alone or with a language after it, because in many languages it also means tongue, and a bare name works only when it is longer than three letters, because BEM is Portuguese for well. On USSD the language menu offers up to four languages, the caller's country languages first, each in its own name, so it fits one screen in any alphabet. In South Africa that is English, isiZulu, isiXhosa and Afrikaans; Sesotho, Setswana and Xitsonga are one message away with LANG ST, LANG TN or LANG TS. In Nigeria, Nigerian Pidgin is LANG PCM; in Ethiopia, Tigrinya is LANG TI.

On real speech text from WAXAL, the results for every ACE language are in [the WAXAL report](../benchmark/results/waxal.md); see [speech.md](speech.md) for how to read it.

## Languages ACE does not speak

A message in a language ACE does not speak would otherwise be read as one of the caller's country languages: a Gikuyu message from Kenya reads as Swahili, and the reply comes in a language its writer may not read. So ACE compares each message with character profiles of its 32 languages and of 49 languages it does not speak but its callers do, among them Gikuyu, Dholuo, Kikamba, Dagbani, Dagaare, Runyankore, Malagasy, Sepedi, siSwati, Kikongo, Tshiluba, Kanuri, Fon and Ga. When a message is plainly closer to one of those than to any language ACE offers in the caller's country, ACE replies in the country's first language that it does not read this language yet, names the languages it does read there, and gives the lines the safety rail would give for an urgent health message:

> ACE does not read this language yet. Please write in one of these: English or Kiswahili. Call 999 or 112 (emergency), 1199 (Kenya Red Cross ambulance).

The reply does not guess which language the message was in, because a close relative is often the nearest profile: Acholi reads closest to Dholuo. Some rules keep it safe and fair:

- **The safety rail, commands and Scam Shield run first.** A message the safety rail recognises gets the emergency reply, LANG still switches language, and a scam check still runs. A message in a language ACE does not speak may hold danger words ACE cannot read, so the reply that says ACE does not read it always carries the country's urgent health numbers too.
- **A chosen language is always answered.** A person who set a language with LANG, an API caller that names the language, and a person answering a question ACE just asked are never turned away.
- **Names, places and links do not count.** Links, email addresses and numbers are removed, and so are capitalised words that do not start a sentence and the caller's country's place names, so a list of Kenyan towns is not read as Gikuyu. A message with two or more English, French or Portuguese marker words, which most callers mix in, is never turned away.
- **English counts as ACE's own everywhere.** English is read in every country, so an English message is never turned away, whatever the country offers.
- **ACE languages from across a border count as ACE's own.** People often write in an ACE language that their country's menus do not offer, such as Somali or Afaan Oromo in Kenya, Hausa or Fula in Cameroon, or isiZulu for isiNdebele speakers in Zimbabwe. `countries.ALSO_READ` lists them for each country; ACE never turns them away, and when a message in one has no marker word of the country's own languages, ACE answers in it.
- **Short messages are never judged.** A message needs 24 three letter sequences after that, often four or five words, before ACE judges its language, so a greeting or a single word is answered as before.
- **Latin letters for Arabic, Amharic and Tigrinya.** Many speakers write these languages in Latin letters, which no profile covers, so in countries where ACE offers them it never turns a message away.
- **Close neighbours are left out.** Languages whose speakers read an ACE language are not profiled, so ACE answers them: isiNdebele (isiZulu), Krio (Nigerian Pidgin), Bambara and Maninka (Dyula), and Chitumbuka, whose speakers in Malawi read Chichewa.
- **An operator can confirm with a fuller model.** Set `EngineConfig(language_identifier=...)` to `GoogleLanguageDetector()` (Cloud Translation detectLanguage) or `GlotLID(model_path)`, an open model of more than 2,000 languages. ACE asks it only about messages it would turn away, answers if it says the message is in an offered language, and keeps its own judgement if the identifier fails or takes longer than three seconds, credentials included. The Google detector sends the first 500 characters of the message to Google Cloud under the operator's project; an operator who turns it on says so in their privacy notice. GlotLID runs on the operator's own server.

The profiles are counts of three letter sequences, built by `benchmark/langid/build.py` from ACE's own locale and pack text, the FLORES-200 dev split and the Universal Declaration of Human Rights, with every download pinned and checked. `src/ace_engine/langid/profiles.json` holds counts only and is shared under CC BY-SA 4.0, because FLORES-200 is. The thresholds were set on the WAXAL validation split and FLORES-200 dev; the WAXAL test split was not used to build or tune anything.

On the WAXAL test split, ACE tells the writer it does not read the language in 46.5% of sentences on average across 12 languages it does not speak: Malagasy 100%, Gikuyu 94.9%, Dholuo 87.1%, Dagbani 85.0%, Acholi 83.1% and Dagaare 50.8%, but Ikposo 32.7%, Masaaba 24.7% and none of Lusoga, Runyankole, Sidama and Wolaytta. No open text was found to profile Lusoga, Sidama or Wolaytta, and Runyankole's profile comes from one short text, so ACE still answers them in another of its languages that many of their speakers read: Lusoga and Runyankole mostly in Luganda, Swahili or Kinyarwanda, Sidama and Wolaytta in Afaan Oromo or Somali. In ACE's own languages, at most 0.5% of a language's sentences are turned away in the countries that offer it, and on FLORES-200 devtest none, in every country that offers or reads it from across a border (`benchmark/results/langid-devtest.md`, from `benchmark/langid/devtest.py`). ACE leans this way on purpose: turning away a person who writes in a language ACE speaks costs more than answering a speaker of a neighbouring language in a language close to theirs.

## How Latin letters reach a phone

Many African languages write letters that GSM-7, the SMS alphabet every phone reads, does not hold: ɓ, ɗ, ƙ and ƴ in Hausa and Pular, ɛ and ɔ in Akan, Ewe and Dyula, ŋ, ɖ, ƒ, ɣ and ʋ in Ewe, ɲ in Dyula, and the dotted vowels of Yoruba and Igbo. Before a reply leaves, ACE folds each to its closest GSM-7 letter (ɓ to b, ŋ to ng, ẹ to e), the way most people already type these languages, so the reply keeps the full 160 characters per segment instead of dropping to 70. Mooré is written with plain u and i where the standard spelling has ʋ and ɩ, because ʋ is a vowel in Mooré but a consonant in Ewe. Amharic and Tigrinya travel as UCS-2.

## What a locale file holds

```yaml
meta:          # code, name, native name, script, encoding (gsm7 or ucs2), direction, reviewed, confirm, names,
               # and marker_weight for a language that shares many words with another
templates:     # every user facing sentence, keyed by where it lives in the code
phrases:       # words ACE listens for, in groups, added to the built in lists
words:         # stopwords and marker words for language detection
```

- **Templates** are keyed by module and name, for example `safety.OPENERS.maternal`, `services.prices.THIN` or `commands.TEXTS.help`. Keep every placeholder in braces, such as `{numbers}` or `{place}`, exactly as the English has it. The tests fail if one is missing or renamed, because a safety reply without `{numbers}` would carry no number.
- **The call line** is the template `safety.CALL_WORD`. Put `{numbers}` where the language puts the numbers: Call {numbers} in English, {numbers} ይደውሉ in Amharic.
- **Phrases** are the words the safety rail listens for (pregnancy, danger signs, poisoning, violence, self harm, urgent illness), the words Scam Shield looks for, the cues that route a question to a service, and the foods, crops, weeks and months the services parse. Add the forms people actually write, including common misspellings and the words that attach to them. Phrases from every language are matched in every message, so a single word that alone raises an alarm must be rare outside its language.
- **Commands** are the first word of a message. A command word may not mean a different command in another language; the tests check this.
- **Words** hold stopwords, ignored in retrieval, and marker words that are common in the language and rare in the others offered in the same countries.

## Add a language

1. Copy the closest locale file to `src/ace_engine/locales/<code>.yaml`, with a BCP 47 code.
2. Set `meta`. Use `encoding: ucs2` for any script outside Latin, so ACE budgets 80 characters per USSD screen and 67 per SMS segment. Keep `reviewed: false`.
3. Translate every template and rewrite every phrase group in the words people use. Do not translate word for word.
4. Add the code to the country entries in `src/ace_engine/countries.py` where it should be offered, after the country's existing languages.
5. Add renderings to the Africa packs with `reviewed: false`, each short at most 160 characters and each menu label at most 24, and 13 red team and 7 ordinary messages to `benchmark/sets/`.
6. Add the language to `src/ace_engine/speech/support.yaml`, checked against the provider pages, or with `speak` null so it is not spoken.
7. Add the language to `benchmark/langid/build.py` with its FLORES-200 and UDHR sources, if they exist, and rebuild the profiles with `python benchmark/langid/build.py fetch` and `build`. If the language was among the languages ACE does not speak, move it out of that list.
8. Run `ruff check src tests benchmark`, `ace packs validate`, `pytest -q` and `python -m benchmark.run --quick`. `i18n.missing()` must return an empty list for the new code, and recall in the new language must be at least 99%.

## Review

No sentence in any language added in 2.1 or 2.3 has yet been reviewed by a fluent speaker, and the Swahili and French renderings still await review too. The 2.3 drafts were written with care, but confidence varies: Bemba, Dyula, Pular and Wolof are lower confidence drafts, and Mooré is the lowest. Review those first, safety phrases before anything else, because a wrong safety phrase can miss an emergency. An independent review before release found and fixed Dyula comfort lines that said the opposite of what they meant, everyday words that raised false alarms, and Ewe text in a look alike letter outside the SMS alphabet; it also flagged phrases whose meaning it could not confirm, such as Bemba ifisushi and Ewe dzidzi le edzi for fits, which a fluent reviewer should check first. The reply that says ACE does not read a language is new in 2.3 and also awaits review in every language. In every country where they are offered, English, French or Portuguese safety phrases still apply to messages that mix languages, as many messages do.

A reviewer checks the safety phrases and the maternal danger signs first, then the service templates, then the pack translations, and sets `reviewed: true` in the file once done. Open a pull request with your name and the language; no coding is needed.

`ace locales status` shows each language and whether it has been reviewed. `ace locales backcheck <code>` gives reviewers a head start: it translates every string back into English with Google Cloud Translation and lists the strings whose meaning most likely drifted first, safety strings marked. It needs a Google Cloud project (see [speech.md](speech.md)), writes nothing to the locale file, and never replaces a fluent reviewer. Cloud Translation covers 20 of the 24 languages added in 2.3; it does not cover Nigerian Pidgin, Wolof, Dyula or Mooré, and it covers Fulfulde rather than Pular. Reports for Portuguese, Arabic, Amharic, Afaan Oromo and Somali are in [docs/reviews](reviews/README.md), with the rows to check first.
