# Speech and translation

ACE 2.2 adds an optional speech and translation layer, measures ACE's language tools on real African speech text from WAXAL, and makes the voice line speak only languages a voice exists for. Nothing here is needed to run ACE: the keypad voice line, USSD, SMS and WhatsApp work with no provider at all.

## What the layer does

| Job | Interface | Ready provider | When it runs |
| --- | --- | --- | --- |
| Hear a spoken question | `SpeechToText` | Google Cloud Speech-to-Text V2, Chirp 3 where it exists | On the voice line, before the safety rail reads the transcript |
| Speak a reply | `TextToSpeech` | Google Cloud Text-to-Speech | On the voice line, for languages with a voice |
| Translate | `Translator` | Google Cloud Translation Advanced (v3) | Only in `ace locales backcheck`, a review tool. Never while answering a person |

Three rules hold the design together:

1. **The safety rail never waits on a provider.** A transcript is text like any other and meets the rail first. The keypad stays open on every voice turn, so a caller is never stuck behind a recogniser.
2. **Every word ACE sends still comes from a locale file or a sourced pack.** Machine translation helps people review those files; it is never served. This keeps rule 2 of [AGENTS.md](../AGENTS.md), no answer without a citation.
3. **Speak only what a voice can say.** A voice reading a script it was not built for produces noise. The voice line speaks a language only where `src/ace_engine/speech/support.yaml` records a voice, or where the operator lists the language in `ACE_VOICE_LANGUAGES` after checking their own provider. Otherwise it moves to the next language of the caller's country that has a voice, then English.

## What exists for each ACE language

Checked on 25 November 2026 against Google Cloud's published language lists and the WAXAL dataset card. `ace voice languages` prints the same table from `support.yaml`. Preview means Google has not made the model generally available.

| Language | Speech to text | Text to speech | Translation | WAXAL |
| --- | --- | --- | --- | --- |
| English | Chirp 3, en-US, GA | Chirp 3 HD, Neural2, WaveNet, Standard | NMT and Translation LLM | Not included |
| Swahili | Chirp 3, sw-KE, Preview | Chirp 3 HD, sw-KE | NMT and Translation LLM | 1,778 voice script lines; no transcribed speech |
| French | Chirp 3, fr-FR, GA; no African French locale | Chirp 3 HD, Neural2, WaveNet, Standard, fr-FR | NMT and Translation LLM | Not included |
| Portuguese | Chirp 3, pt-PT, GA; no Mozambican or Angolan locale | WaveNet and Standard, pt-PT | NMT and Translation LLM | Not included |
| Arabic | Chirp 3 for Algeria, Egypt, Morocco and Tunisia, Preview; none for Libya, Sudan or Chad | Chirp 3 HD, WaveNet, Standard, Modern Standard Arabic | NMT and Translation LLM | Not included |
| Amharic | Chirp 3, am-ET, Preview | None found | NMT; Translation LLM experimental | 219.9 hours transcribed |
| Afaan Oromo | None found | None found | NMT | 222.7 hours transcribed |
| Somali | First generation Chirp, so-SO | None found | NMT; Translation LLM experimental | Not included |

The gap is in speaking. No published Google Cloud voice speaks Amharic, Afaan Oromo or Somali, and WAXAL has no voice scripts in them, so for now the Ethiopian and Somali voice lines speak English or Arabic and the full replies stay on SMS and USSD in the caller's language. Closing that gap needs a voice trained on recordings in those languages, or recorded human prompts.

## WAXAL

[WAXAL](https://huggingface.co/datasets/google/WaxalNLP) is an open speech corpus for African languages from Google Research and six African partners: Makerere University, the University of Ghana, Digital Umuganda, Media Trust, Loud and Clear and AIMS Senegal. The [Google Research announcement](https://research.google/blog/waxal-a-large-scale-open-resource-for-african-language-speech-technology/) and the [paper](https://arxiv.org/abs/2602.02734) describe it. Sources give different counts because the dataset has grown since February 2026, so ACE quotes the dataset card itself (revision 5f4d8ca, updated 1 September 2026):

- **Transcribed speech for 19 languages**: 438,230 utterances and 2,242 hours across the speaker disjoint splits. Acholi, Luganda, Masaaba, Runyankole and Lusoga from Makerere; Akan, Ewe, Dagbani, Dagaare and Ikposo from the University of Ghana; Fula, Lingala, Shona, Malagasy, Amharic, Afaan Oromo, Sidama, Tigrinya and Wolaytta from Digital Umuganda.
- **Voice scripts**: 15 loadable sets of single speaker studio recordings, among them Swahili, Hausa, Yoruba, Igbo, Nigerian Pidgin, Kikuyu, Dholuo, Luganda and Fula, with Bambara, Pular and Wolof from AIMS Senegal in the repository as well.
- **Licences differ by partner**: the University of Ghana sets are CC BY 4.0 and every other set is CC BY-SA 4.0, so a model or file derived from those must carry the same licence. Partners keep ownership of their recordings. The licence register records both.

### How ACE uses it today

`python -m benchmark.waxal` fetches up to 600 sentences from each test split through the Hugging Face dataset viewer, runs ACE's language guess, the safety rail and the service router on them, and writes counts to [benchmark/results/waxal.md](../benchmark/results/waxal.md). It never stores WAXAL text or audio in this repository. The first run measured 12,333 sentences in 27 sets:

- **ACE recognises its own languages in real speech**: Amharic 100%, Swahili 97.0%, Afaan Oromo 93.2%.
- **The safety rail fired 3 times in 12,333 ordinary sentences (0.02%)**: an Amharic sentence about female genital cutting, a Swahili story with a snake bite and a Fula sentence containing bofti, the Afaan Oromo word for snake. The first two are true matches for the topic; the third is a cross language collision kept on purpose, because a snake bite phrase must never be missed in Afaan Oromo.
- **ACE claims too many languages it does not speak**: 45.8% of sentences in 23 other languages were read as one of ACE's eight, mostly as Swahili. Lingala and Kikuyu read as Swahili almost every time, and Tigrinya always reads as Amharic because both use Ge'ez script. A caller whose language is misread gets their country's default language instead of the language they wrote in. Before this release the figure was 54.0%: the Somali markers ka, ku and ay, common in Dagbani, Luganda and many other languages, and the French marker ma, which is also Somali and Acholi, were removed, and French and Swahili gained longer, unambiguous marker words. Emergency recall stays 100% in every language.
- **Not measured**: Ewe and Baoule, which the dataset viewer could not serve.

The next step is a language guess trained on the WAXAL train splits and evaluated on the test splits, so that ACE says it does not know rather than guessing a neighbour language.

### How ACE can use it next

| Use | WAXAL sets | What it unlocks | Licence note |
| --- | --- | --- | --- |
| Tune speech recognition for Amharic and Afaan Oromo | amh_asr, orm_asr | Spoken questions in Ethiopia, where Afaan Oromo has no cloud model | Derived models CC BY-SA 4.0 |
| A Swahili voice | swa_tts | A second Swahili voice beside Chirp 3 HD | CC BY-SA 4.0 |
| Keyword spotting for danger words | All ASR sets | The 99% voice emergency recall gate in the [build plan](v2/build-plan.md) | Per set |
| Next languages | Hausa, Yoruba, Igbo, Lingala, Shona, Luganda, Akan and others | Voice and text for Nigeria, Ghana, DR Congo, Zimbabwe and Uganda | Per set |

## Running it

```bash
pip install "ace-engine[google]"
export GOOGLE_CLOUD_PROJECT=your-project        # the project that is billed
gcloud auth application-default login           # or a service account attached to the host
ace voice languages                             # what each language can do, with sources
ace locales backcheck am --out am-backcheck.md  # back translation report for Amharic reviewers
```

Enable the Cloud Translation, Speech-to-Text and Text-to-Speech APIs in that project. ACE reads credentials through Application Default Credentials and never stores, logs or prints a key. To accept spoken questions, pass `GoogleSpeechToText()` to `VoiceAdapter`. To tell the voice line which languages your own provider speaks, set `ACE_VOICE_LANGUAGES`, for example `en,sw,fr`.

### The back translation report

`ace locales backcheck` translates every string of a locale file back into English and lines it up with the English ACE wrote, lowest word overlap first, with safety strings marked. A low overlap points a reviewer to where meaning may have drifted. It is a pointer, never a verdict: only a fluent speaker may set `reviewed: true`, and safety phrases also need a clinician. The report writes nothing to the locale file.

## Gaps

- No voice in Amharic, Afaan Oromo or Somali from Google Cloud or WAXAL.
- No speech recognition model for Afaan Oromo in Google Cloud; WAXAL has the data to build one.
- No African locale of French or Portuguese for speech recognition.
- Arabic speech recognition has no locale for Libya, Sudan or Chad.
- The language guess still reads many neighbour languages as Swahili and Tigrinya as Amharic.
- The five new languages still await fluent review; the back translation report is ready for reviewers once a Google Cloud project is connected.
