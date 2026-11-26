# ACE tokenizer audit

What 59 African language varieties cost against English on nine released tokenizers, measured on FLORES-200 and on the health, farming and service text that ACE sends to people on basic phones. One script produces every figure below, from the raw counts to the derived summaries, and the same script scores an unreleased tokenizer offline.

By Tom Bruno, part of [ACE, the African Context Engine](https://tbrunoh.github.io/ace/). Code Apache-2.0.

## What it finds

- **Eight of 59 varieties meet 1.5 times English on a released tokenizer today**: Portuguese, four Arabic varieties, French, Afrikaans and Swahili. Of the 53 varieties other than French, Portuguese and the four Arabic varieties, only Afrikaans and Swahili meet it, and Swahili sits on the line: its devtest interval reaches 1.5005.
- **Script predicts which tokenizer wins.** o200k uses the fewest tokens for all 34 varieties written almost entirely in basic Latin letters. Of the 20 other varieties outside Arabic script, Gemma 4's tokenizer gives the lowest ratio for 13, including all four in Ge'ez and Tifinagh, and it needs a third of o200k's tokens for Amharic.
- **Newer is not always fairer.** Llama 4 needs fewer tokens than Llama 3 for all 59 varieties and cuts Amharic by 68.6%. Qwen3.5, which Alibaba says covers 201 languages and dialects, costs more than Qwen3 for 17 varieties and nearly doubles the cost of both varieties written in Tifinagh. DeepSeek-V4 produces the same token ids as DeepSeek-V3 for every sentence measured.
- **A ratio can reward spending more on English.** Mistral Tekken's French ratio is 3 to 4% lower than o200k's, yet the two use almost the same French tokens, because Tekken spends 3.5% to 3.7% more on the same English.
- **Somali and Oromo miss 1.5 on all nine tokenizers.** Their best figures are 1.70 and 1.88, on o200k.
- **Spelling Hausa correctly costs more.** Native speaker corrections to FLORES double the hooked letters ɓ, ɗ, ƙ and ƴ in the Hausa dev sentences, from 855 to 1,714, and every tokenizer then needs 2.1% to 4.4% more tokens.
- **On SMS, the alphabet can cost more than the tokenizer.** One letter outside the GSM alphabet sends a whole message as UCS-2, so ACE's Arabic, French and Portuguese facts take 1.8 to 2.2 times the SMS segments of English, more than their o200k token ratios.

## Run it

Python 3.10 or later. From this folder:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python audit.py fetch                 # FLORES-200, the corrections and every tokenizer file, each checked against its SHA-256
python audit.py run                   # FLORES-200 dev, ACE's text and SMS: results/
python audit.py run --split devtest   # results_devtest/
python audit.py run --nfc             # dev normalised to Unicode NFC: results_nfc/
python audit.py corrections           # native speaker corrections: results/flores_corrections.csv
python audit.py equivalence           # tokenizers that count exactly like one measured here: results/equivalence.csv
python audit.py summary               # every derived figure in this README: results/summary.json
```

After `fetch`, everything runs offline, including tiktoken, whose files are kept in `cache/tiktoken`. A full run takes a few minutes on a laptop. With the pinned requirements, a fresh run from a clean checkout reproduces the committed results byte for byte.

### Score a tokenizer before you release it

```bash
python audit.py check --tokenizer path/to/tokenizer.json --ceiling 1.5 \
    --baseline o200k --tolerance 0.01 --compare path/to/previous_tokenizer.json --out report.json
```

Nothing leaves the machine. `check` reports the English token count against the baseline's English count and the tolerance, then each variety's same text ratio with a 95% interval. A variety passes only when its whole interval sits below the ceiling; the tokenizer passes only when English is within budget and every variety passes, and the exit code is non-zero otherwise, so it can gate a build. `--compare` adds each variety's change against a previous tokenizer and lists the varieties that cost more. It reads devtest by default, so a tokenizer tuned on the dev sentences is scored on other sentences. `--tokenizer` and `--compare` also accept a name from `tokenizers.json`. For example, `python audit.py check --tokenizer "Gemma 4" --languages swh_Latn,amh_Ethi` prints:

```text
English budget: 27,114 tokens against 26,873 on o200k (+0.90%, tolerance 1.0%): PASS
Swahili                   1.64  [1.62, 1.66]  FAIL
Amharic                   1.94  [1.91, 1.96]  FAIL
0 of 2 varieties pass the 1.5 ceiling with their whole interval below it
Overall: FAIL (a tokenizer passes only if English is within budget and every variety passes)
```

### Rebuild ACE's parallel text

`data/ace_parallel.jsonl` is generated from ACE's own sources. From the repository root, with ACE installed:

```bash
python benchmark/tokenizer-audit/export_ace_text.py --ace . --out benchmark/tokenizer-audit/data/ace_parallel.jsonl
```

## What is in this folder

| Path | What it is |
| --- | --- |
| `ACE-tokenizer-audit.pdf` | The report: findings, charts, method and instructions, in twelve pages |
| `audit.py` | Six commands: `fetch`, `run`, `corrections`, `equivalence`, `summary` and `check` |
| `export_ace_text.py` | Rebuilds the parallel text from ACE's reply templates and context packs |
| `tokenizers.json` | The nine tokenizers: source pinned to a commit, SHA-256, vocabulary size and, for open-weight models, embedding rows from the pinned configuration |
| `data/ace_parallel.jsonl` | 84 reply templates, from full sentences to single words such as or and per, and 23 health and farming facts, each in English, Swahili, French, Portuguese, Arabic, Amharic, Afaan Oromo and Somali, with source and licence on every row |
| `results/` | FLORES-200 dev (997 sentences), the corrections and equivalence checks, and `summary.json` |
| `results_devtest/` | FLORES-200 devtest (1,012 sentences) |
| `results_nfc/` | FLORES-200 dev normalised to NFC |

Each results folder holds `flores_african.csv` (every variety and tokenizer, with intervals), `best_tokenizer.csv` (each variety's best tokenizer by ratio and by absolute tokens, with a paired test against the runner up), `ace_text.csv`, `sms_channel.csv` and `results.json`.

The 59 varieties are every FLORES-200 variety spoken in Africa except English, Spanish and romanised Arabic, with each script counted separately: Latin, Ge'ez, Arabic and Tifinagh.

## The measure

The same text ratio is a tokenizer's total tokens for a variety divided by its total for the aligned English sentences, the tokenization premium of Petrov et al. (2023). Each tokenizer is divided by its own English count, so the absolute English counts are reported beside every ratio. Intervals are 95% percentile bootstrap intervals over sentences, with 1,000 resamples (seed 7). Each variety's best and second best tokenizers are compared on the same resampled sentences (seeds 11 for ratios and 13 for absolute tokens), and a win counts as clear only when the whole interval for the difference sits on one side of zero. Special tokens are not counted. Text is counted as distributed unless `--nfc` is set. Placeholders in ACE's templates, such as `{numbers}`, are removed before counting.

## Results

All figures are FLORES-200 dev unless a line says devtest. `results/summary.json` holds every derived figure.

1. **Eight varieties meet 1.5.** Portuguese (1.23, Llama 4, level with o200k), Standard Arabic (1.25), Egyptian Arabic (1.29), French (1.30), Tunisian Arabic (1.31) and Moroccan Arabic (1.37), all on Mistral Tekken, then Afrikaans (1.43) and Swahili (1.48) on o200k. Another 36 sit between 1.5 and 2.0, 12 between 2.0 and 3.0, and three above 3.0, led by Tamasheq in Tifinagh at 5.18. On devtest the same eight meet 1.5 by point estimate, but only seven by interval: Swahili's upper bound is 1.5005.
2. **Who wins.** By ratio, o200k is best for 38 varieties, Gemma 4 for 13, Mistral Tekken for 5, Qwen3.5 for 2 (Kikuyu and Kanuri in Ajami) and Llama 4 for 1 (Portuguese). A paired bootstrap confirms 57 of the 59 winners on dev and 58 on devtest; Portuguese is a tie between Llama 4 and o200k on both splits, and Kabuverdianu a tie between o200k and Llama 4 on dev.
3. **Script.** For all 34 varieties whose letters are at least 95% basic Latin, o200k uses the fewest absolute tokens. Of the 20 other varieties outside Arabic script, Gemma 4 gives the lowest ratio for 13, including all four in Ge'ez and Tifinagh: Amharic 1.97 against 5.88 on o200k, Tigrinya 2.47 against 5.97, Central Atlas Tamazight 4.41 against 10.10. o200k wins Akan, Bambara, Dinka, Igbo, Twi and Yoruba, and Qwen3.5 wins Kikuyu. Across all 59, the more letters outside basic Latin, the fewer tokens Gemma 4 needs relative to o200k (rank correlation −0.69).
4. **Coverage, not size.** Qwen3, with 151,669 entries, needs 5.00 times English for Tamazight in Tifinagh; Qwen3.5, with 248,070, needs 9.88, and o200k, with 200,019, needs 10.10. What a vocabulary covers is associated with the result more than how large it is.
5. **Generations.** Llama 4 needs fewer tokens than Llama 3 for every variety, a median 8.9% fewer and 68.6% fewer for Amharic (a ratio of 7.71 falling to 2.43). Qwen3.5 needs a median 4.4% fewer tokens than Qwen3 and gains most in Arabic script (Kanuri in Ajami 3.12 to 2.37, Standard Arabic 1.63 to 1.31), but it costs more for 17 varieties, among them Tamazight in Tifinagh (5.00 to 9.88), Tamasheq in Tifinagh (5.31 to 9.99), Tigrinya (4.17 to 4.71) and Amharic (4.11 to 4.45). DeepSeek-V4 produces the same token ids as DeepSeek-V3 for all 120,540 FLORES-200 sentences measured, dev and devtest together.
6. **English.** On the 997 dev English sentences: Mistral Tekken 26,478, Qwen3 26,255, Qwen3.5 26,168, Gemma 4 25,881, cl100k 25,801, Llama 3 25,792, Llama 4 25,712, DeepSeek-V4 25,695, o200k 25,536. On the 1,012 devtest sentences: Mistral Tekken 27,827, Qwen3 27,621, Qwen3.5 27,530, cl100k 27,182, Llama 3 27,171, Gemma 4 27,114, Llama 4 27,048, DeepSeek-V4 27,041, o200k 26,873. A budget of o200k plus 1% on devtest (27,141) admits DeepSeek-V4, Llama 4 and Gemma 4 and rejects Llama 3 by 30 tokens; on dev, Gemma 4 would fail at +1.35%. At this margin the tolerance and the split decide membership.
7. **French and Dyula.** Mistral Tekken's French ratio is 3 to 4% lower than o200k's on both splits (1.30 against 1.35 on dev), yet their French token counts are within 0.4% of each other: o200k uses fewer on dev (34,375 against 34,492) and Tekken fewer on devtest (36,748 against 36,808). Gemma 4 and o200k show the same pattern in Dyula.
8. **Somali and Oromo.** Best figures 1.70 and 1.88 on o200k; Gemma 4 comes second (1.89 and 2.13) and Llama 4 third (1.91 and 2.16). Whether more Somali and Oromo training text would close the gap is not tested here.
9. **ACE's own text.** On ACE's facts, o200k gives Swahili 1.48 and Amharic 5.78, beside FLORES's 1.48 and 5.88. The reply templates cost less: 1.42 and 5.40, a gap within the intervals for Swahili. The cheapest and costliest languages are the same on all three texts.
10. **SMS.** ACE's Arabic, French and Portuguese facts take 1.80, 2.24 and 2.22 times the SMS segments of English. Folding accents brings French and Portuguese to 1.20 and 1.15, at a cost: in ACE's French farming facts, maïs (maize) becomes mais (but). Amharic goes the other way: 0.70 times the characters of English (0.68 on FLORES) and 1.51 times the segments, far below its token ratio.

## Robustness

- **Two splits.** Across 531 variety and tokenizer pairs, dev and devtest differ by a median of 0.012 and at most 0.13, and no variety changes its best tokenizer by ratio. By absolute tokens, French (Tekken or o200k) and Kanuri in Ajami (Gemma 4 or Qwen3.5) are too close to call on devtest.
- **Normalisation.** FLORES ships some Yoruba and Fon text in decomposed form. Under NFC, Yoruba falls from 2.18 to 2.13 on o200k and Fon from 2.87 to 2.81, or from 3.54 to 3.39 on Mistral Tekken. English does not move, and no variety changes its best tokenizer.
- **Native speaker corrections.** Abdulmumin et al. (2024) corrected the FLORES sentences for Hausa, Northern Sotho, Xitsonga and isiZulu: devtest for all four and dev for three. On the Hausa dev sentences, where 632 of 997 were corrected and the hooked letters double, ratios rise by 2.1% (Llama 4) to 4.4% (Qwen3.5), and every corrected interval sits above the original figure. Elsewhere the changes are at most 0.011, and no variety changes its best tokenizer. FLORES+, the version now maintained by the Open Language Data Initiative, carries community corrections; the corrections here are pinned to one public commit so the result can be reproduced.
- **Equivalent tokenizers.** `audit.py equivalence` confirms that DeepSeek-V3 and NVIDIA Nemotron 3 Nano give the same token ids as DeepSeek-V4 and Mistral Tekken on every sentence of both splits, and that Gemma 3 differs from Gemma 4 on 3 of 120,540 sentences, which leaves every ratio the same to two decimals.

## Read with care

- ACE's translations were drafted for ACE 2.1 and await review by fluent speakers and, for the safety phrases, by clinicians. Treat them as a cost benchmark, not reference translations. With 23 facts, intervals are wider than on FLORES.
- FLORES-200 sentences come from English Wikinews, Wikijunior and Wikivoyage articles translated into each language, so they measure one register. Both splits have been public since 2022, so neither is unseen by every tokenizer; scoring private text is the stronger test.
- The bootstrap resamples sentences and ignores that several sentences come from one article, so the intervals are a little narrow. Each winner is chosen and tested on the same data, with no correction across 59 tests.
- The SMS figures use the default GSM alphabet; national language shift tables, which some networks support, would change them for Portuguese and other languages.
- Every figure counts tokens. None measures answer quality, which a separate evaluation must test.
- The Llama 3 and Llama 4 files come from public mirrors, because Meta's repositories require a sign in. Every download is pinned to a commit, and the checksums in `tokenizers.json` let anyone confirm a file.

## Related work

- Petrov, La Malfa, Torr and Bibi (2023), *Language Model Tokenizers Introduce Unfairness Between Languages*, NeurIPS: the tokenization premium measured here.
- Ahia et al. (2023), *Do All Languages Cost the Same? Tokenization in the Era of Commercial Language Models*, EMNLP: what the premium costs users of commercial APIs.
- Lundin et al. (2026), *The Token Tax: Systematic Bias in Multilingual Tokenization*, AfricaNLP: higher token fertility is associated with lower accuracy on AfriMMLU.
- Somide (2026), *The African Language Tax*, arXiv:2606.24460: premiums on eleven tokenizers on FLORES devtest, with cost and latency.
- NLLB Team (2022), *No Language Left Behind*: FLORES-200. Abdulmumin et al. (2024), *Correcting FLORES Evaluation Dataset for Four African Languages*, WMT: the corrections used here.

What this audit adds: a test of the English denominator; paired tests of each winner and a pass rule on intervals; an offline check, with a comparison against a previous release, that a lab can run before release; the previous and current tokenizer of three families (Llama, Qwen and DeepSeek); the cost of correct orthography; and the SMS channel, measured on text a deployed service sends.

## Licences

- Code: Apache-2.0, as for the rest of ACE. The GSM alphabet tables follow ACE's `encoding.py`.
- ACE's reply templates are Apache-2.0, and its wording of the facts is CC BY 4.0, each fact naming the publisher whose guidance it restates.
- FLORES-200 (CC BY-SA 4.0, Meta and the NLLB team), the corrections and the tokenizer files, each under its publisher's terms, are downloaded by `fetch` and not included here.

## Cite

Use the Cite this repository button on GitHub, or:

> Bruno, T. (2026). *ACE, the African Context Engine* (version 2.2.0b3) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.24565738. Tokenizer audit in `benchmark/tokenizer-audit`.

The DOI points to the archived 2.2.0b3 release, and 10.5281/zenodo.24565737 always resolves to the latest version; the code and results are at [v2.2.0b3/benchmark/tokenizer-audit](https://github.com/tbrunoh/african-context-engine/tree/v2.2.0b3/benchmark/tokenizer-audit).

## Acknowledgements

Thanks to Dr. Shikoh Gitau and the Ndimi team at Qhala for the discussions that prompted this work, and for rerunning its first version.
