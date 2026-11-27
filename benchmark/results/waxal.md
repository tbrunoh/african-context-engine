# ACE on WAXAL speech text

Real sentences from [WAXAL](https://huggingface.co/datasets/google/WaxalNLP) (dataset card revision 5f4d8ca, updated 1 September 2026): up to 600 per set from each test split, transcriptions of natural speech for ASR sets and voice scripts for TTS sets. Each set is read as a message from a country where the language is spoken, so ACE guesses only among that country's languages, as it does for a real caller. A sentence ACE judges to be in a language it does not speak is not read: ACE says so and names the languages it reads in that country (see docs/languages.md). Counts only; no WAXAL text is stored in this repository, and none was used to build ACE's language profiles.

## ACE languages: recognised in real speech

| Language | Read as from | Sentences | Recognised | Not read | Other guesses | False alarms | Routed to a service |
|:--|:--|--:|--:|--:|:--|--:|--:|
| Amharic | ET | 600 | 100.0% | 0.0% | none | 1 | 30 |
| Shona | ZW | 600 | 100.0% | 0.0% | none | 0 | 44 |
| Akan | GH | 600 | 99.5% | 0.0% | ee 2, en 1 | 0 | 28 |
| Swahili | KE | 199 | 99.5% | 0.5% | none | 1 | 19 |
| Afaan Oromo | ET | 600 | 99.0% | 0.0% | so 6 | 0 | 137 |
| Twi | GH | 104 | 98.1% | 0.0% | country default 1, en 1 | 0 | 14 |
| Igbo | NG | 200 | 97.5% | 0.0% | country default 3, yo 1, en 1 | 0 | 28 |
| Luganda | UG | 600 | 97.0% | 0.0% | sw 18 | 0 | 27 |
| Tigrinya | ET | 600 | 95.0% | 0.0% | am 30 | 0 | 32 |
| Hausa | NG | 197 | 94.4% | 0.0% | country default 10, pcm 1 | 0 | 16 |
| Yoruba | NG | 177 | 91.5% | 0.0% | country default 15 | 0 | 39 |
| Fante (Akan) | GH | 101 | 88.1% | 0.0% | ee 10, country default 2 | 0 | 6 |
| Fula (ACE writes Pular) | GN | 600 | 76.5% | 0.0% | fr 141 | 1 | 34 |
| Lingala | CD | 600 | 75.7% | 0.5% | sw 143 | 0 | 20 |
| Nigerian Pidgin | NG | 204 | 68.6% | 0.0% | en 52, country default 8, ig 4 | 1 | 20 |

## Languages ACE does not speak: told so, or answered in one of ACE's languages

| Language | Read as from | Sentences | Not read | Answered | Answered in | False alarms | Routed to a service |
|:--|:--|--:|--:|--:|:--|--:|--:|
| Sidama | ET | 600 | 0.0% | 100.0% | om 562, so 22, country default 16 | 0 | 3 |
| Wolaytta | ET | 600 | 0.0% | 100.0% | om 524, so 40, country default 36 | 0 | 9 |
| Runyankole | UG | 600 | 0.0% | 100.0% | lg 207, sw 187, rw 152, country default 53, en 1 | 0 | 1 |
| Lusoga | UG | 600 | 0.0% | 100.0% | lg 518, sw 67, country default 15 | 0 | 2 |
| Masaaba | UG | 600 | 24.8% | 75.2% | sw 231, lg 175, rw 24, country default 20, en 1 | 0 | 101 |
| Ikposo | TG | 600 | 32.7% | 67.3% | fr 211, ee 143, yo 27, country default 18, ak 5 | 0 | 54 |
| Dagaare | GH | 600 | 50.8% | 49.2% | en 208, ak 62, ee 14, country default 8, ha 3 | 0 | 2 |
| Acholi | UG | 528 | 83.3% | 16.7% | rw 34, sw 22, lg 18, country default 14 | 0 | 19 |
| Dagbani | GH | 600 | 85.0% | 15.0% | ha 57, ee 23, country default 5, ak 4, en 1 | 0 | 4 |
| Dholuo | KE | 209 | 87.1% | 12.9% | sw 11, country default 9, lg 3, en 2, so 2 | 0 | 3 |
| Gikuyu | KE | 214 | 94.9% | 5.1% | sw 8, country default 3 | 0 | 1 |
| Malagasy | any country | 600 | 100.0% | 0.0% | none | 0 | 0 |

Across 12 languages ACE does not speak, each counted once, ACE tells the writer it does not read the language in 46.6% of sentences on average, and answers 53.4% in one of its own languages, most often a close neighbour. In ACE's own languages, at most 0.5% of a language's sentences are not read.

Across 12,333 sentences in 27 sets, the safety rail fired 4 times (0.03%). Each firing is listed in waxal.json by queue for review.

Not measured: Ewe, Baoule. The dataset viewer could not serve their text on this run; load them with the datasets library instead.
