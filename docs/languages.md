# Languages

ACE answers in eight languages: English, Swahili, French, Portuguese, Arabic, Amharic, Afaan Oromo and Somali. English, Swahili and French live in the code. The other five each live in one file, `src/ace_engine/locales/<code>.yaml`, so a ninth language is one file and no code change.

| Code | Language | Native name | Script | Alphabet on a phone | Countries where it is offered | Reviewed |
| --- | --- | --- | --- | --- | --- | --- |
| en | English | English | Latin | GSM-7 | Every country | Yes |
| sw | Swahili | Kiswahili | Latin | GSM-7 | Kenya, Tanzania, Uganda, DR Congo, Burundi | Awaiting fluent review |
| fr | French | Français | Latin | GSM-7 | Rwanda, Senegal, Côte d'Ivoire, Togo, DR Congo, Burundi, Cameroon, Benin, Chad, Guinea, Burkina Faso, Guinea-Bissau, Algeria, Morocco, Tunisia | Awaiting fluent review |
| pt | Portuguese | Português | Latin | GSM-7 | Mozambique, Angola, Guinea-Bissau | No |
| ar | Arabic | العربية | Arabic | UCS-2 | Sudan, Egypt, Libya, Algeria, Morocco, Tunisia, Chad, South Sudan, Somalia | No |
| am | Amharic | አማርኛ | Ge'ez | UCS-2 | Ethiopia | No |
| om | Afaan Oromo | Afaan Oromoo | Latin | GSM-7 | Ethiopia | No |
| so | Somali | Soomaali | Latin | GSM-7 | Somalia, Ethiopia | No |

## How a person picks a language

ACE guesses from the first message: Arabic script means Arabic, Ge'ez script means Amharic, and marker words pick out Portuguese, Afaan Oromo, Somali, Swahili and French. Otherwise it uses the first language of the caller's country. A person can switch at any time with LANG and a code (LANG PT), or with the language's own name (Português, العربية, አማርኛ). On USSD the language menu offers up to four languages, the caller's country languages first, each in its own name.

## What a locale file holds

```yaml
meta:          # code, name, native name, script, encoding (gsm7 or ucs2), direction, reviewed, confirm, names
templates:     # every user facing sentence, keyed by where it lives in the code
phrases:       # words ACE listens for, in groups, added to the built in lists
words:         # stopwords and marker words for language detection
```

- **Templates** are keyed by module and name, for example `safety.OPENERS.maternal`, `services.prices.THIN` or `commands.TEXTS.help`. Keep every placeholder in braces, such as `{numbers}` or `{place}`, exactly as the English has it. The tests fail if one is missing or renamed, because a safety reply without `{numbers}` would carry no number.
- **The call line** is the template `safety.CALL_WORD`. Put `{numbers}` where the language puts the numbers: Call {numbers} in English, {numbers} ይደውሉ in Amharic.
- **Phrases** are the words the safety rail listens for (pregnancy, danger signs, poisoning, violence, self harm, urgent illness), the words Scam Shield looks for, the cues that route a question to a service, and the foods, crops, weeks and months the services parse. Add the forms people actually write, including common misspellings and the words that attach to them.
- **Words** hold stopwords, ignored in retrieval, and marker words that are common in the language and rare in the others.

## Add a language

1. Copy the closest locale file to `src/ace_engine/locales/<code>.yaml`, with a BCP 47 code.
2. Set `meta`. Use `encoding: ucs2` for any script outside Latin, so ACE budgets 80 characters per USSD screen and 67 per SMS segment. Keep `reviewed: false`.
3. Translate every template and rewrite every phrase group in the words people use. Do not translate word for word.
4. Add the code to the country entries in `src/ace_engine/countries.py` where it should be offered.
5. Add renderings to the Africa packs with `reviewed: false`, and 12 red team and 7 ordinary messages to `benchmark/sets/`.
6. Run `ruff check src tests benchmark`, `ace packs validate`, `pytest -q` and `python -m benchmark.run --quick`. `i18n.missing()` must return an empty list for the new code, and recall in the new language must be at least 99%.

## Review

No sentence in Portuguese, Arabic, Amharic, Afaan Oromo or Somali has yet been reviewed by a fluent speaker, and the Swahili and French renderings still await review too. A reviewer checks the safety phrases and the maternal danger signs first, then the service templates, then the pack translations, and sets `reviewed: true` in the file once done. Open a pull request with your name and the language; no coding is needed.
