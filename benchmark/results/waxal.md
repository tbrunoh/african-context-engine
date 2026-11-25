# ACE on WAXAL speech text

Real sentences from [WAXAL](https://huggingface.co/datasets/google/WaxalNLP) (dataset card revision 5f4d8ca, updated 1 September 2026): up to 600 per set from each test split, transcriptions of natural speech for ASR sets and voice scripts for TTS sets. Counts only; no WAXAL text is stored in this repository.

## ACE languages: recognised in real speech

| Language | Sentences | Recognised | Other guesses | False alarms | Routed to a service |
|:--|--:|--:|:--|--:|--:|
| Amharic | 600 | 100.0% | none | 1 | 28 |
| Swahili | 199 | 97.0% | none 6 | 1 | 18 |
| Afaan Oromo | 600 | 93.2% | none 32, sw 5, so 4 | 0 | 136 |

## Languages ACE does not speak: how often ACE claims them as its own

| Language | Sentences | Claimed | Claimed as | False alarms | Routed to a service |
|:--|--:|--:|:--|--:|--:|
| Tigrinya | 600 | 100.0% | am 600 | 0 | 10 |
| Lingala | 600 | 97.2% | sw 583 | 0 | 3 |
| Kikuyu | 214 | 89.7% | sw 192 | 0 | 1 |
| Igbo | 200 | 77.5% | sw 155 | 0 | 1 |
| Nigerian Pidgin | 204 | 70.1% | en 111, sw 32 | 0 | 17 |
| Yoruba | 177 | 69.5% | sw 113, om 8, fr 2 | 0 | 0 |
| Fante | 101 | 60.4% | sw 55, om 5, fr 1 | 0 | 0 |
| Akan | 600 | 60.2% | sw 341, om 17, fr 2, en 1 | 0 | 0 |
| Dagbani | 600 | 58.8% | sw 343, om 4, fr 4, so 1, pt 1 | 0 | 0 |
| Masaaba | 600 | 58.3% | sw 323, pt 25, en 2 | 0 | 0 |
| Dagaare | 600 | 58.2% | en 246, so 37, sw 34, om 21, fr 10, pt 1 | 0 | 0 |
| Hausa | 197 | 55.8% | sw 100, om 10 | 0 | 0 |
| Twi | 104 | 52.9% | sw 42, fr 7, om 6 | 0 | 0 |
| Ikposo | 600 | 44.8% | sw 231, fr 34, pt 2, om 1, so 1 | 0 | 0 |
| Fula | 600 | 32.7% | fr 89, sw 86, om 19, en 1, pt 1 | 1 | 2 |
| Runyankole | 600 | 32.3% | sw 194 | 0 | 0 |
| Dholuo | 209 | 28.2% | sw 46, fr 7, so 5, en 1 | 0 | 2 |
| Acholi | 528 | 26.5% | sw 110, fr 20, so 6, en 2, om 2 | 0 | 19 |
| Lusoga | 600 | 26.0% | sw 120, pt 35, om 1 | 0 | 0 |
| Wolaytta | 600 | 14.8% | sw 49, so 31, fr 6, om 3 | 0 | 0 |
| Luganda | 600 | 14.2% | sw 83, en 2 | 0 | 0 |
| Malagasy | 600 | 11.8% | sw 69, fr 1, pt 1 | 0 | 0 |
| Sidama | 600 | 8.7% | so 18, om 14, sw 12, fr 7, pt 1 | 0 | 0 |
| Shona | 600 | 4.5% | so 15, om 4, fr 4, sw 4 | 0 | 0 |

Average claimed rate: 45.8% across 23 languages, each language counted once. Tigrinya is listed but not averaged, because it shares Ge'ez script with Amharic.

Across 12,333 sentences in 27 sets, the safety rail fired 3 times (0.02%). Each firing is listed in waxal.json by queue for review.

Not measured: Ewe, Baoule. The dataset viewer could not serve their text on this run; load them with the datasets library instead.
