# Speech and translation

ACE 2.2 adds an optional speech and translation layer, measures ACE's language tools on real African speech text from WAXAL, and makes the voice line speak only languages a voice exists for. The second build, 2.2.0b2, adds Gemini TTS, which gives the voice line Amharic and Somali. Nothing here is needed to run ACE: the keypad voice line, USSD, SMS and WhatsApp work with no provider at all.

## What the layer does

| Job | Interface | Ready provider | When it runs |
| --- | --- | --- | --- |
| Hear a spoken question | `SpeechToText` | Google Cloud Speech-to-Text V2, Chirp 3 where it exists | On the voice line, before the safety rail reads the transcript |
| Speak a reply | `TextToSpeech` | Google Cloud Text-to-Speech, read by the Africa's Talking Say action; Gemini 3.8 Flash TTS, played with the Play action | On the voice line, for languages with a voice |
| Translate | `Translator` | Google Cloud Translation Advanced (v3) | Only in `ace locales backcheck`, a review tool. Never while answering a person |

Three rules hold the design together:

1. **The safety rail never waits on a provider.** A transcript is text like any other and meets the rail first. The keypad stays open on every voice turn, so a caller is never stuck behind a recogniser.
2. **Every word ACE sends still comes from a locale file or a sourced pack.** Machine translation helps people review those files; it is never served. This keeps rule 2 of [AGENTS.md](../AGENTS.md), no answer without a citation.
3. **Speak only what a voice can say.** A voice reading a script it was not built for produces noise. The voice line speaks a language only where `src/ace_engine/speech/support.yaml` records a voice, or where the operator lists the language in `ACE_VOICE_LANGUAGES` after checking their own provider. Otherwise it moves to the next language of the caller's country that has a voice, then English.

### Two ways to speak

The Africa's Talking Say action reads text aloud with [Google Cloud Text-to-Speech voices](https://developers.africastalking.com/docs/voice/actions/say), so it can only speak the languages those voices cover: English, Swahili, French, Portuguese and Arabic. For the rest, ACE synthesises the audio itself with [Gemini 3.8 Flash TTS](https://ai.google.dev/gemini-api/docs/speech-generation), stores each file once, and the call plays it with the Play action. That gives the voice line Amharic and Somali. The voice line uses Say wherever Say can speak the language, because it is quicker and costs nothing extra, and uses Play only where Say cannot. If synthesis fails during a call, the line answers anyway with Say in a language it can read.

Only fixed prompts and public pack text are ever synthesised, never a caller's words or number, so the audio files hold nothing personal and the server can serve them without a key.

## What exists for each ACE language

Checked on 25 November 2026 against the published language lists of Google Cloud and the Gemini API, and the WAXAL dataset card. `ace voice languages` prints the same table from `support.yaml`. Preview means Google has not made the model generally available.

| Language | Speech to text | Say: Cloud Text-to-Speech | Play: Gemini 3.8 Flash TTS | Translation | WAXAL |
| --- | --- | --- | --- | --- | --- |
| English | Chirp 3, en-US, GA | Chirp 3 HD, Neural2, WaveNet, Standard | Yes | NMT and Translation LLM | Not included |
| Swahili | Chirp 3, sw-KE, Preview; Gemini 3.5 Transcribe | Chirp 3 HD, sw-KE | Yes; not in Flash-Lite | NMT and Translation LLM | 1,778 voice script lines; no transcribed speech |
| French | Chirp 3, fr-FR, GA; no African French locale | Chirp 3 HD, Neural2, WaveNet, Standard, fr-FR | Yes | NMT and Translation LLM | Not included |
| Portuguese | Chirp 3, pt-PT, GA; no Mozambican or Angolan locale | WaveNet and Standard, pt-PT | Yes | NMT and Translation LLM | Not included |
| Arabic | Chirp 3 for Algeria, Egypt, Morocco and Tunisia, Preview; none for Libya, Sudan or Chad | Chirp 3 HD, WaveNet, Standard, Modern Standard Arabic | Standard and Egyptian Arabic | NMT and Translation LLM | Not included |
| Amharic | Chirp 3, am-ET, Preview; Gemini 3.5 Transcribe | None | Yes | NMT; Translation LLM experimental | 219.9 hours transcribed |
| Afaan Oromo | None found | None | Not listed | NMT | 222.7 hours transcribed |
| Somali | First generation Chirp, so-SO | None | Yes; not in Flash-Lite | NMT; Translation LLM experimental | Not included |

Gemini 3.8 Flash TTS closes the speaking gap for Amharic and Somali. Afaan Oromo remains the gap: no Google model lists it for speech in or out, neither Cloud Text-to-Speech, Gemini TTS, Chirp 3 nor [Gemini 3.5 Transcribe](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-transcribe). Oromo callers hear the next language of their country with a voice and get the full reply on SMS and USSD in Afaan Oromo. WAXAL's 222.7 transcribed hours of Afaan Oromo are the way to close it.

## WAXAL

[WAXAL](https://huggingface.co/datasets/google/WaxalNLP) is an open speech corpus for African languages from Google Research and seven African partners: Makerere University, the University of Ghana, Digital Umuganda, Addis Ababa University, Media Trust, Loud n Clear and AIMS Senegal. The [Google Research announcement](https://research.google/blog/waxal-a-large-scale-open-resource-for-african-language-speech-technology/) and the [paper](https://arxiv.org/abs/2602.02734) describe it. Sources give different counts because the dataset has grown since February 2026, so ACE quotes the dataset card itself (revision 5f4d8ca, updated 1 September 2026):

- **Transcribed speech for 19 languages**: 438,230 utterances and 2,242 hours across the speaker disjoint splits. Acholi, Luganda, Masaaba, Runyankole and Lusoga from Makerere; Akan, Ewe, Dagbani, Dagaare and Ikposo from the University of Ghana; Fula, Lingala, Shona, Malagasy, Amharic, Afaan Oromo, Sidama, Tigrinya and Wolaytta from Digital Umuganda.
- **Voice scripts**: 15 loadable sets of single speaker studio recordings, among them Swahili, Hausa, Yoruba, Igbo, Nigerian Pidgin, Kikuyu, Dholuo, Luganda and Fula, with Bambara, Pular and Wolof from AIMS Senegal in the repository as well.
- **Licences differ by partner**: the University of Ghana sets are CC BY 4.0 and every other set is CC BY-SA 4.0, so a model or file derived from those must carry the same licence. Partners keep ownership of their recordings. The licence register records both.

### How ACE uses it today

`python -m benchmark.waxal` fetches up to 600 sentences from each test split through the Hugging Face dataset viewer, runs ACE's language guess, the safety rail and the service router on them, and writes counts to [benchmark/results/waxal.md](../benchmark/results/waxal.md). It never stores WAXAL text or audio in this repository. The first run measured 12,333 sentences in 27 sets:

- **ACE recognises its own languages in real speech**: Amharic 100%, Swahili 97.0%, Afaan Oromo 93.2%.
- **The safety rail fired 3 times in 12,333 ordinary sentences (0.02%)**: an Amharic sentence about female genital cutting, a Swahili story with a snake bite and a Fula sentence containing bofti, the Afaan Oromo word for snake. The first two are true matches for the topic; the third is a cross language collision kept on purpose, because a snake bite phrase must never be missed in Afaan Oromo.
- **ACE claims too many languages it does not speak**: on average across 23 other languages (Tigrinya, which shares Ge'ez script with Amharic, aside), 45.8% of sentences were read as one of ACE's eight, mostly as Swahili. Lingala and Kikuyu read as Swahili almost every time, and Tigrinya always reads as Amharic because both use Ge'ez script. A caller whose language is misread gets their country's default language instead of the language they wrote in. Before this release the figure was 54.0%: the Somali markers ka, ku and ay, common in Dagbani, Luganda and many other languages, and the French marker ma, which is also Somali and Acholi, were removed, and French and Swahili gained longer, unambiguous marker words. Emergency recall stays 100% in every language.
- **Not measured**: Ewe and Baoule, which the dataset viewer could not serve.

The next step is a language guess trained on the WAXAL train splits and evaluated on the test splits, so that ACE says it does not know rather than guessing a neighbour language.

### How ACE can use it next

| Use | WAXAL sets | What it enables | Licence note |
| --- | --- | --- | --- |
| Tune speech recognition for Amharic and Afaan Oromo | amh_asr, orm_asr | Spoken questions in Ethiopia, where Afaan Oromo has no cloud model | Derived models CC BY-SA 4.0 |
| An Afaan Oromo voice | orm_asr, with a voice recorded for the purpose | The one ACE language no Google model speaks | CC BY-SA 4.0 |
| A Swahili voice | swa_tts | A third Swahili voice beside Chirp 3 HD and Gemini TTS | CC BY-SA 4.0 |
| Keyword spotting for danger words | All ASR sets | The 99% voice emergency recall gate in the [build plan](v2/build-plan.md) | Per set |
| Next languages | Hausa, Yoruba, Igbo, Lingala, Shona, Luganda, Akan and others | Voice and text for Nigeria, Ghana, DR Congo, Zimbabwe and Uganda | Per set |

## Running it

```bash
pip install -e ".[google]"                      # from a checkout of this repository
export GOOGLE_CLOUD_PROJECT=your-project        # the project that is billed
gcloud auth application-default login           # or a service account attached to the host
ace voice languages                             # what each language can do, with sources
ace locales backcheck am --out am-backcheck.md  # back translation report for Amharic reviewers
```

Enable the Cloud Translation, Speech-to-Text and Text-to-Speech APIs in that project. ACE reads credentials through Application Default Credentials and never stores, logs or prints a key. In Google Cloud Shell, run `gcloud auth application-default login` first: the credentials Cloud Shell provides by default are not accepted by the Google auth library ACE uses, and the call fails with a RefreshError about a missing email field. To accept spoken questions, pass `GoogleSpeechToText()` to `VoiceAdapter`. To tell the voice line which languages your own provider speaks, set `ACE_VOICE_LANGUAGES`, for example `en,sw,fr`.

To give the voice line Amharic and Somali, set two more variables on the server that receives the voice callback:

```bash
export GEMINI_API_KEY=...                              # a Gemini API key, kept outside the repository
export ACE_VOICE_AUDIO_URL=https://your-host           # the public address of this server
export ACE_VOICE_AUDIO_DIR=/var/lib/ace/voice-audio    # optional cache folder
```

The server then serves the synthesised files at `/voice/audio/<file>.wav`. The first call to use a new prompt waits for synthesis; every later call plays the stored file.

### Who pays, and how to keep costs in check

Every operator runs ACE in their own Google Cloud project and pays for their own use. The repository holds no project, key or credential, so cloning or running ACE never bills anyone else. Costs arise only where your own credentials call a Google API. As shipped, ACE does that in two places: `ace locales backcheck`, which calls Cloud Translation, and Gemini audio for Amharic and Somali on the voice line, which runs only when `GEMINI_API_KEY` is set. Cloud Speech-to-Text and Text-to-Speech run only if you wire them into your own code. Nothing else in ACE calls Google Cloud; your SMS, voice, WhatsApp and RCS providers bill messages and calls separately.

A caller cannot run up the Gemini bill. The voice line is a keypad menu, and ACE synthesises only its fixed prompts and public pack text, never a caller's words. Each file is synthesised once and replayed, so the cost is bounded by the prompts and packs, not by the number of calls. Keep `ACE_VOICE_AUDIO_DIR` on storage that survives a restart, or every new server will synthesise the files again.

Before you open a voice line to the public:

- Set a spend cap budget for the Gemini API in Cloud Billing or Google AI Studio. Once the month's estimated cost passes the cap, new Gemini calls stop until the next month, and the voice line still answers by reading the reply with the provider's own voice in a language it speaks. Enforcement takes a little time, so set the cap slightly below your limit.
- Lower the Cloud Translation characters per day quota, which is unlimited by default. Text-to-Speech and Speech-to-Text offer only requests per minute quotas. Requests beyond a quota fail.
- Add a budget with alerts on the billing account for everything else. An alert budget warns you; it does not stop spending.
- Restrict the Gemini API key to the Generative Language API, and keep it in the server's environment only.
- Set `ACE_WEBHOOK_SECRET`, so only your voice and SMS provider can call `/voice`, `/ussd` and `/sms`.
- Turn on GitHub secret scanning and push protection for your fork, so a key committed by mistake is blocked or flagged at once.

### The back translation report

`ace locales backcheck` translates every string of a locale file back into English and lines it up with the English ACE wrote, lowest word overlap first, with safety strings marked. A low overlap points a reviewer to where meaning may have drifted. It is a pointer, never a verdict: only a fluent speaker may set `reviewed: true`, and safety phrases also need a clinician. The report writes nothing to the locale file. The reports for the five newest languages, run on 25 November 2026, are in [docs/reviews](reviews/README.md) with the rows to check first.

## Gaps

- No voice and no speech recognition for Afaan Oromo from any Google model; WAXAL has the data to build both.
- Somali has a voice through Gemini 3.8 Flash TTS but not through Cloud Text-to-Speech, and only first generation Chirp hears it.
- No African locale of French or Portuguese for speech recognition.
- Arabic speech recognition has no locale for Libya, Sudan or Chad.
- The language guess still reads many neighbour languages as Swahili and Tigrinya as Amharic.
- The five new languages still await fluent review; their back translation reports are in [docs/reviews](reviews/README.md).
