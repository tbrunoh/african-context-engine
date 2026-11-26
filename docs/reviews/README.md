# Back translation reports

These reports give fluent speakers a head start on reviewing ACE's five newest languages. Each one lines up every string in a locale file with a machine back translation into English, lowest word overlap first, with the safety strings marked.

| Language | Report | Strings | On the safety rail |
| --- | --- | --: | --: |
| Afaan Oromo | [om-backcheck.md](om-backcheck.md) | 112 | 10 |
| Amharic | [am-backcheck.md](am-backcheck.md) | 112 | 10 |
| Arabic | [ar-backcheck.md](ar-backcheck.md) | 112 | 10 |
| Portuguese | [pt-backcheck.md](pt-backcheck.md) | 112 | 10 |
| Somali | [so-backcheck.md](so-backcheck.md) | 112 | 10 |

Generated on 25 November 2026 with `ace locales backcheck` (ACE 2.2.0b2) and Google Cloud Translation Advanced (v3).

## How to read them

A back translation is a pointer, never a verdict. Machine translation into English often misreads short words, abbreviations and local names, so a low overlap does not mean the string is wrong, and a high overlap does not mean it is right. Only a fluent speaker may set `reviewed: true` in a locale file, and the safety phrases also need a clinician. Review in the order set out in [languages.md](../languages.md#review): the safety phrases and the maternal danger signs first, then the service templates, then the pack translations.

The day and month abbreviations score near zero in most languages because the machine reads three letters as a word. Check them by eye.

## Where to look first

These rows came back with a meaning that differs from ACE's English in a way that would matter to the person reading it. Each needs a fluent speaker to say whether the locale text is right and the machine is wrong, or the other way round.

| Language | Key | ACE English | What came back | Why it matters |
| --- | --- | --- | --- | --- |
| Afaan Oromo | `safety.OPENERS.poisoning` | take the container with you | grab his ax | The text may only say hold the container, not bring it to the clinic |
| Afaan Oromo | `commands.TEXTS.stopped` | You will not get any further messages from ACE unless you write again. | If you do not type again you will receive another message from ACE. | The opposite meaning; the Oromo appears to keep the negative, so confirm it |
| Afaan Oromo | `services.pests.REFER` | before you spray | before seeding | The verb may mean sow rather than spray pesticide |
| Somali | `scam.REPORT_LINE` | Forward it to 333 | Call 333 | 333 takes a forwarded text, not a call |
| Somali | `commands.TEXTS.help_short` | Ask ACE a question | ACE asks a question | Word order may make ACE the one asking |
| Somali | `commands.TEXTS.stopped` | unless you write again | until you sign up again | A person need only write again, not sign up |
| Amharic | `services.pregnancy.LATE` | you are past the last planned check at 40 weeks | You have had your final scheduled check-up at week {w}, week 40 | The point is that the 40 week check has passed and she should be seen today |
| Amharic | `services.pests.NAMES.fall_armyworm` | fall armyworm | American immigrant | Confirm the local name farmers use; the example in `commands.TEXTS.tip_usage` came back as American cockroaches |
| Amharic | `services.prices.NO_FOOD` | ACE has no recent WFP price | ACE is not eligible for the latest WFP price | Wording may read as a refusal rather than a gap in the data |
| Somali, Arabic, Afaan Oromo | `services.pregnancy.FIRST`, `NEXT`, `DUE_NOW` | antenatal check | pregnancy test | The word may also mean a pregnancy test; the messages are about antenatal visits |
| Arabic | `services.warnings.NATIONAL` | the whole country | all countries | The phrase can read as every country rather than this one |

Portuguese came back close to ACE's English throughout, and every safety message in every language came back with its meaning intact apart from the Oromo poisoning line above.

## Running them again

The reports are generated, so run them again after any change to a locale file:

```bash
pip install "ace-engine[google]"
export GOOGLE_CLOUD_PROJECT=your-project        # with the Cloud Translation API enabled
gcloud auth application-default login
ace locales backcheck om --out docs/reviews/om-backcheck.md
```

See [speech.md](../speech.md#running-it) for the project setup, including a note on Google Cloud Shell.
