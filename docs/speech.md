# Speech and translation

ACE 2.2 adds an optional speech and translation layer, measures ACE's language tools on real African speech text from WAXAL, and makes the voice line speak only languages a voice exists for. The second build, 2.2.0b2, adds Gemini TTS, which gives the voice line Amharic and Somali. Release 2.3 gives the voice line 12 of its 24 new languages and speech recognition for 16 more. Nothing here is needed to run ACE: the keypad voice line, USSD, SMS and WhatsApp work with no provider at all.

## What the layer does

| Job | Interface | Ready provider | When it runs |
| --- | --- | --- | --- |
| Hear a spoken question | `SpeechToText` | Google Cloud Speech-to-Text V2: Chirp 3 where it exists, then Chirp 2, Chirp or the long model | On the voice line, before the safety rail reads the transcript |
| Speak a reply | `TextToSpeech` | Google Cloud Text-to-Speech, read by the Africa's Talking Say action; Gemini 3.8 Flash TTS, played with the Play action | On the voice line, for languages with a voice |
| Translate | `Translator` | Google Cloud Translation Advanced (v3) | Only in `ace locales backcheck`, a review tool. Never while answering a person |
| Identify a language | `LanguageIdentifier` | Cloud Translation detectLanguage, or GlotLID on your own server | Optional, only to confirm a message ACE would turn away as a language it does not speak; it never translates or answers |

Three rules hold the design together:

1. **The safety rail never waits on a provider.** A transcript is text like any other and meets the rail first. The keypad stays open on every voice turn, so a caller is never stuck behind a recogniser.
2. **Every word ACE sends still comes from a locale file or a sourced pack.** Machine translation helps people review those files; it is never served. This keeps rule 2 of [AGENTS.md](../AGENTS.md), no answer without a citation.
3. **Speak only what a voice can say.** A voice reading a script it was not built for produces noise. The voice line speaks a language only where `src/ace_engine/speech/support.yaml` records a voice, or where the operator lists the language in `ACE_VOICE_LANGUAGES` after checking their own provider. Otherwise it moves to the next language of the caller's country that has a voice, then English.

### Two ways to speak

The Africa's Talking Say action reads text aloud with [Google Cloud Text-to-Speech voices](https://developers.africastalking.com/docs/voice/actions/say), so it can only speak the languages those voices cover: English, Swahili, French, Portuguese, Arabic and, from 2.3, Afrikaans. For the rest, ACE synthesises the audio itself with [Gemini 3.8 Flash TTS](https://ai.google.dev/gemini-api/docs/speech-generation), stores each file once, and the call plays it with the Play action. That gives the voice line Amharic and Somali, and from 2.3 Hausa, Igbo, Sesotho, Chichewa, Bemba, Kinyarwanda, Luganda, Lingala, Akan, Dyula and Tigrinya. The voice line uses Say wherever Say can speak the language, because it is quicker and costs nothing extra, and uses Play only where Say cannot. If synthesis fails during a call, the line answers anyway with Say in a language it can read.

Only fixed prompts and public pack text are ever synthesised, never a caller's words or number, so the audio files hold nothing personal and the server can serve them without a key.

## What exists for each ACE language

For the eight languages of 2.2, checked on 25 November 2026 against the published language lists of Google Cloud and the Gemini API, and the WAXAL dataset card. `ace voice languages` prints the same table from `support.yaml`. Preview means Google has not made the model generally available.

| Language | Speech to text | Say: Cloud Text-to-Speech | Play: Gemini 3.8 Flash TTS | Translation | WAXAL |
| --- | --- | --- | --- | --- | --- |
| English | Chirp 3, en-US, GA | Chirp 3 HD, Neural2, WaveNet, Standard | Yes | NMT and Translation LLM | Not included |
| Swahili | Chirp 3, sw-KE, Preview; Gemini 3.5 Transcribe | Chirp 3 HD, sw-KE | Yes; not in Flash-Lite | NMT and Translation LLM | 1,778 voice script lines; no transcribed speech |
| French | Chirp 3, fr-FR, GA; no African French locale | Chirp 3 HD, Neural2, WaveNet, Standard, fr-FR | Yes | NMT and Translation LLM | Not included |
| Portuguese | Chirp 3, pt-PT, GA; no Mozambican or Angolan locale | WaveNet and Standard, pt-PT | Yes | NMT and Translation LLM | Not included |
| Arabic | Chirp 3 for Algeria, Egypt, Morocco and Tunisia, Preview; none for Libya, Sudan or Chad | Chirp 3 HD, WaveNet, Standard, Modern Standard Arabic | Standard and Egyptian Arabic | NMT and Translation LLM | Not included |
| Amharic | Chirp 3, am-ET, Preview; Gemini 3.5 Transcribe | None | Yes | NMT; Translation LLM experimental | 219.9 hours transcribed |
| Afaan Oromo | Chirp 2, om-ET (found in 2.3) | None | Not listed | NMT | 222.7 hours transcribed |
| Somali | Chirp 2 (found in 2.3) and first generation Chirp, so-SO | None | Yes; not in Flash-Lite | NMT; Translation LLM experimental | Not included |

### The 24 languages added in 2.3

Checked on 26 November 2026 against the Speech-to-Text V2 language list, the Cloud Text-to-Speech voice list, the Africa's Talking Say page, the Gemini speech generation page and the Cloud Translation language list; the WAXAL column follows the dataset card quoted below. A language with no voice is not spoken: its callers hear the next language of their country with a voice, and get the full reply on SMS and USSD in their own language. No new voice has been heard by a fluent listener yet, so an operator should have one listen before opening a voice line to the public.

| Language | Speech to text | Voice | Translation | WAXAL |
| --- | --- | --- | --- | --- |
| Afrikaans | Chirp 3, af-ZA, Preview | Say, af-ZA-Standard-A; Gemini TTS | NMT and Translation LLM | Not included |
| Akan (Twi) | None | Gemini TTS | NMT, as Twi (Akan) | Akan transcribed speech; Twi and Fante voice scripts |
| Bemba | None | Gemini TTS; not in Flash-Lite | NMT | Not included |
| Chichewa | Chirp 2, ny-MW | Gemini TTS, as Nyanja | NMT, as Chichewa (Nyanja) | Not included |
| Dyula | None | Gemini TTS; not in Flash-Lite | Not listed | Not included |
| Ewe | None | None | NMT | Transcribed speech |
| Hausa | Chirp 3, ha-NG, Preview | Gemini TTS | NMT; Translation LLM experimental | Voice scripts |
| Igbo | Chirp 2, ig-NG | Gemini TTS; not in Flash-Lite | NMT; Translation LLM experimental | Voice scripts |
| isiXhosa | Chirp 3, xh-ZA, Preview | None | NMT | Not included |
| isiZulu | Chirp 3, zu-ZA, Preview | None | NMT and Translation LLM | Not included |
| Kinyarwanda | Long model, rw-RW | Gemini TTS | NMT | Not included |
| Kirundi | None | None | NMT, as Rundi | Not included |
| Lingala | Chirp 2, ln-CD | Gemini TTS | NMT and Translation LLM | Transcribed speech |
| Luganda | Chirp 2, lg-UG | Gemini TTS, as Ganda | NMT, as Ganda (Luganda) | Transcribed speech and voice scripts |
| Mooré | None | None | Not listed | Not included |
| Nigerian Pidgin | None | None | Not listed | Voice scripts |
| Pular | None; Chirp 2 lists ff-SN, which is Pulaar of Senegal | None; Gemini TTS lists Nigerian Fulfulde | NMT for Fulfulde, not Pular | Pular voice scripts in the repository; Fula transcribed speech and voice scripts |
| Sesotho | Long model, st-ZA | Gemini TTS, as Southern Sotho; not in Flash-Lite | NMT | Not included |
| Setswana | Long model, tn-Latn-ZA | None | NMT | Not included |
| Shona | Chirp 2, sn-ZW | None | NMT | Transcribed speech |
| Tigrinya | None | Gemini TTS; not in Flash-Lite | NMT | Transcribed speech |
| Wolof | Chirp 3, wo-SN, Preview | None | Not listed | Voice scripts in the repository |
| Xitsonga | Long model, ts-ZA | None | NMT | Not included |
| Yoruba | Chirp 3, yo-NG, Preview | None | NMT | Voice scripts |

Chirp and Chirp 2 run in single regions, so ACE sends those requests to us-central1; Chirp 3 and the long model run in the us multi-region.

Gemini 3.8 Flash TTS closes the speaking gap for Amharic, Somali and 12 of the new languages, Afrikaans among them, which the Say action can also read. Afaan Oromo can now be heard, through Chirp 2, but no Google model speaks it: neither Cloud Text-to-Speech nor Gemini TTS lists it. Oromo callers hear the next language of their country with a voice and get the full reply on SMS and USSD in Afaan Oromo. WAXAL's 222.7 transcribed hours of Afaan Oromo are the way to close it.

## WAXAL

[WAXAL](https://huggingface.co/datasets/google/WaxalNLP) is an open speech corpus for African languages from Google Research and seven African partners: Makerere University, the University of Ghana, Digital Umuganda, Addis Ababa University, Media Trust, Loud n Clear and AIMS Senegal. The [Google Research announcement](https://research.google/blog/waxal-a-large-scale-open-resource-for-african-language-speech-technology/) and the [paper](https://arxiv.org/abs/2602.02734) describe it. Sources give different counts because the dataset has grown since February 2026, so ACE quotes the dataset card itself (revision 5f4d8ca, updated 1 September 2026):

- **Transcribed speech for 19 languages**: 438,230 utterances and 2,242 hours across the speaker disjoint splits. Acholi, Luganda, Masaaba, Runyankole and Lusoga from Makerere; Akan, Ewe, Dagbani, Dagaare and Ikposo from the University of Ghana; Fula, Lingala, Shona, Malagasy, Amharic, Afaan Oromo, Sidama, Tigrinya and Wolaytta from Digital Umuganda.
- **Voice scripts**: 15 loadable sets of single speaker studio recordings, among them Swahili, Hausa, Yoruba, Igbo, Nigerian Pidgin, Kikuyu, Dholuo, Luganda and Fula, with Bambara, Pular and Wolof from AIMS Senegal in the repository as well.
- **Licences differ by partner**: the University of Ghana sets are CC BY 4.0 and every other set is CC BY-SA 4.0, so a model or file derived from those must carry the same licence. Partners keep ownership of their recordings. The licence register records both.

### How ACE uses it today

`python -m benchmark.waxal` fetches up to 600 sentences from each test split through the Hugging Face dataset viewer, runs ACE's language detection, its check for languages it does not speak, the safety rail and the service router on them, and writes counts to [benchmark/results/waxal.md](../benchmark/results/waxal.md). It never stores WAXAL text or audio in this repository, and no WAXAL text was used to build ACE's language profiles; their thresholds were set on the validation split. It reads each set as a message from a country where the language is spoken, so ACE guesses only among that country's languages, as it does for a real caller: Lingala is read as from DR Congo, where ACE offers French, Swahili and Lingala. The run of 26 November 2026 measured 12,333 sentences in 27 sets:

- **ACE recognises its languages in real speech, in 15 sets covering 13 of them**: Amharic and Shona 100%, Akan and Swahili 99.5%, Afaan Oromo 99.0%, Twi 98.1%, Igbo 97.5%, Luganda 97.0%, Tigrinya 95.0%, Hausa 94.4%, Yoruba 91.5%, Fante 88.1%, Fula 76.5%, Lingala 75.7% and Nigerian Pidgin 68.6%. Reading a message with no marker word by its letters is what lifted Hausa, Shona, Twi, Fante and Fula. Most Lingala misses read as Swahili, most Fula misses as French and most Nigerian Pidgin misses as English. ACE writes Pular, a Fula variety of Guinea, so WAXAL's Fula set measures a neighbour. Fante is an Akan variety, and ACE's Akan is written in Twi.
- **ACE now says when it does not read a language**: across 12 languages it does not speak, it tells the writer so in 46.5% of sentences on average, from Malagasy 100%, Gikuyu 94.9%, Dholuo 87.1%, Dagbani 85.0% and Acholi 83.1% to Dagaare 50.8%, Ikposo 32.7% and Masaaba 24.7%. Lusoga, Runyankole, Sidama and Wolaytta, which no open text profiles well, are still answered in Luganda, Kinyarwanda or Afaan Oromo. Before 2.3, ACE answered every sentence of these languages in one of its own. In ACE's own languages, at most 0.5% of a language's sentences are turned away. See [languages.md](languages.md#languages-ace-does-not-speak).
- **The safety rail fired 4 times in 12,333 ordinary texts (0.03%)**: an Amharic sentence about female genital cutting, a Swahili story with a snake bite, a Nigerian Pidgin fable in which a snake bites a file, and a Fula sentence containing bofti, the Afaan Oromo word for snake. The first three are true matches for the topic, the fable caught by the snake bite rule added in 2.3; the fourth is a cross language collision kept on purpose, because a snake bite phrase must never be missed in Afaan Oromo. A first run of the 2.3 languages fired 69 times, mostly because the Akan word adi (ate) folds to the same letters as the Ewe word aɖi (poison); those words and a few other common ones left the safety phrase lists before release.
- **Not measured**: Ewe and Baoule, which the dataset viewer could not serve.

### How ACE can use it next

| Use | WAXAL sets | What it enables | Licence note |
| --- | --- | --- | --- |
| Tune speech recognition for Amharic and Afaan Oromo | amh_asr, orm_asr | Better spoken questions in Ethiopia, where Afaan Oromo has only Chirp 2 | Derived models CC BY-SA 4.0 |
| An Afaan Oromo voice | orm_asr, with a voice recorded for the purpose | A voice for Afaan Oromo, which no Google model speaks | CC BY-SA 4.0 |
| A Swahili voice | swa_tts | A third Swahili voice beside Chirp 3 HD and Gemini TTS | CC BY-SA 4.0 |
| Keyword spotting for danger words | All ASR sets | The 99% voice emergency recall gate in the [build plan](v2/build-plan.md) | Per set |
| Voices and recognition for the 2.3 languages | Hausa, Yoruba, Igbo, Lingala, Shona, Luganda, Akan, Ewe and Fula | Voices where Google has none, such as Yoruba, Shona and Ewe, and recognition where none exists, such as Akan and Ewe | Per set |

## Running it

```bash
pip install -e ".[google]"                      # from a checkout of this repository
export GOOGLE_CLOUD_PROJECT=your-project        # the project that is billed
gcloud auth application-default login           # or a service account attached to the host
ace voice languages                             # what each language can do, with sources
ace locales backcheck am --out am-backcheck.md  # back translation report for Amharic reviewers
```

Enable the Cloud Translation API in that project, and Speech-to-Text or Text-to-Speech only if you wire them in. ACE reads credentials through Application Default Credentials and never stores, logs or prints a key. In Google Cloud Shell, run `gcloud auth application-default login` first: the credentials Cloud Shell provides by default are not accepted by the Google auth library ACE uses, and the call fails with a RefreshError about a missing email field. To accept spoken questions, pass `GoogleSpeechToText()` to `VoiceAdapter`. To tell the voice line which languages your own provider speaks, set `ACE_VOICE_LANGUAGES`, for example `en,sw,fr`.

To give the voice line the 13 languages Gemini TTS plays (Amharic, Somali, Hausa, Igbo, Sesotho, Chichewa, Bemba, Kinyarwanda, Luganda, Lingala, Akan, Dyula and Tigrinya), set two more variables on the server that receives the voice callback:

```bash
export GEMINI_API_KEY=...                              # a Gemini API key, kept outside the repository
export ACE_VOICE_AUDIO_URL=https://your-host           # the public address of this server
export ACE_VOICE_AUDIO_DIR=/var/lib/ace/voice-audio    # optional cache folder
```

The server then serves the synthesised files at `/voice/audio/<file>.wav`. The first call to use a new prompt waits for synthesis; every later call plays the stored file.

### Who pays, and how to keep costs in check

Every operator runs ACE in their own Google Cloud project and pays for their own use. The repository holds no project, key or credential, so cloning or running ACE never bills anyone else. Costs arise only where your own credentials call a Google API. As shipped, ACE does that in two places: `ace locales backcheck`, which calls Cloud Translation, and Gemini audio for 13 languages on the voice line, which runs only when `GEMINI_API_KEY` is set. Cloud Speech-to-Text, Text-to-Speech and the Cloud Translation language detector (`GoogleLanguageDetector`, see [languages.md](languages.md#languages-ace-does-not-speak)) run only if you wire them in. The detector is the one Google call that can run while a person waits and that sends a caller's words: it sees at most 500 characters of a message ACE would otherwise turn away, gives up after three seconds, and is billed like translation. Nothing else in ACE calls Google Cloud; your SMS, voice, WhatsApp and RCS providers bill messages and calls separately.

A caller cannot run up the Gemini bill. The voice line is a keypad menu, and ACE synthesises only its fixed prompts and public pack text, never a caller's words. Each file is synthesised once and replayed, so the cost is bounded by the prompts and packs, not by the number of calls. Keep `ACE_VOICE_AUDIO_DIR` on storage that survives a restart, or every new server will synthesise the files again.

Before you open a voice line to the public:

- Set a spend cap budget for the Gemini API in Cloud Billing or Google AI Studio. Once the month's estimated cost passes the cap, new Gemini calls stop until the next month, and the voice line still answers by reading the reply with the provider's own voice in a language it speaks. Enforcement takes a little time, so set the cap slightly below your limit.
- Lower the Cloud Translation characters per day quota, which is unlimited by default, and the separate batch translation quota beside it. One back translation report sends 3,600 to 5,600 characters, depending on the language, so 25,000 a day covers the five reports in docs/reviews and limits the worst case to a few dollars a month. If you turn on the language detector, raise the quota by about 500 characters for each message it is asked about. Text-to-Speech and Speech-to-Text offer only requests per minute quotas. Requests beyond a quota fail.
- Enable only the APIs you call. As shipped, ACE needs Cloud Translation for the report and the Gemini API for voice audio; leave Speech-to-Text and Text-to-Speech off until you use them.
- Add a budget with alerts on the billing account for everything else. An alert budget warns you; it does not stop spending.
- Restrict the Gemini API key to the Generative Language API, and keep it in the server's environment only.
- Set `ACE_WEBHOOK_SECRET`, so only your voice and SMS provider can call `/voice`, `/ussd` and `/sms`.
- Turn on GitHub secret scanning and push protection for your fork, so a key committed by mistake is blocked or flagged at once.

### The back translation report

`ace locales backcheck` translates every string of a locale file back into English and lines it up with the English ACE wrote, lowest word overlap first, with safety strings marked. A low overlap points a reviewer to where meaning may have drifted. It is a pointer, never a verdict: only a fluent speaker may set `reviewed: true`, and safety phrases also need a clinician. The report writes nothing to the locale file. The reports for Portuguese, Arabic, Amharic, Afaan Oromo and Somali, run on 25 November 2026, are in [docs/reviews](reviews/README.md) with the rows to check first; the 24 languages added in 2.3 have no report yet.

## Gaps

- No voice for Afaan Oromo from any Google model, and only Chirp 2 hears it; WAXAL has the data to build both.
- No voice for 12 of the 2.3 languages: Yoruba, isiZulu, isiXhosa, Setswana, Xitsonga, Shona, Kirundi, Ewe, Wolof, Mooré, Nigerian Pidgin and Pular. None of the 12 new voices has been heard by a fluent listener yet.
- No speech recognition for Akan, Bemba, Dyula, Ewe, Kirundi, Mooré, Nigerian Pidgin, Pular and Tigrinya.
- Somali has a voice through Gemini 3.8 Flash TTS but not through Cloud Text-to-Speech.
- No African locale of French or Portuguese for speech recognition.
- Arabic speech recognition has no locale for Libya, Sudan or Chad.
- ACE still answers Lusoga and Runyankole mostly in Luganda, Swahili or Kinyarwanda, and Sidama and Wolaytta in Afaan Oromo or Somali, because no open text profiles them well, and reads one Tigrinya sentence in 20 as Amharic.
- All 29 added languages still await fluent review; back translation reports for the five of 2.1 are in [docs/reviews](reviews/README.md), and the other 24 wait for a run with a Google Cloud project.
