# ACE: the African Context Engine

[![CI](https://github.com/tbrunoh/african-context-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/tbrunoh/african-context-engine/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-0E7490)](LICENSE)
[![Python 3.10 to 3.13](https://img.shields.io/badge/python-3.10%20to%203.13-1E40AF)](pyproject.toml)
[![Packs: CC BY 4.0](https://img.shields.io/badge/packs-CC%20BY%204.0-B45309)](DATA_LICENSE.md)
[![MCP server](https://img.shields.io/badge/MCP-server-2DD4BF)](docs/architecture.md#mcp)

**Checked, local, citable knowledge for Africa, on any phone.**

ACE answers the questions that matter to people who will never install an app: a farmer whose maize is being eaten, a pregnant woman who is bleeding, a mother who just got an M-PESA message that feels wrong. It answers on USSD, SMS, voice, WhatsApp and the web, in English and Swahili, and every answer points to the published source it came from. It runs with no language model and no API key. When you do plug in a model, ACE checks that the model stayed with the facts and falls back when it did not.

```
$ ace ask "viwavi wanakula mahindi yangu nifanye nini" --channel sms
Ponda mayai na viwavi wachanga kwa mkono. Inafaa sana kwa mashamba madogo. Dalili: madoa kama madirisha
kwenye majani, kilele kilicholiwa, kinyesi kibichi kama unga wa mbao.

Sources:
  [sourced] FAO, Fall armyworm management guidance for smallholders
      https://openknowledge.fao.org/server/api/core/bitstreams/f1e28a46-3822-4c03-bc31-4294e7e83ea1/content
  [sourced] ICIPE, Fall armyworm identification, management and control; CIFOR-ICRAF, Fall Armyworm guide
      https://technologytransfer.icipe.org/wp-content/uploads/2021/04/Fall-Armyworm-Brochure-Identification-Management-and-Control-1.pdf
```

## Why ACE exists

- About 1 billion Africans live inside mobile broadband coverage but do not use mobile internet (GSMA, Mobile Economy Africa 2026). USSD, SMS and voice still reach them.
- AI advisory services are proving demand: Digital Green's FarmerChat reaches more than 1.7 million farmers, Jacaranda Health's PROMPTS has reached 2.5 million mothers, and MTN Rwanda launched a voice AI anyone can call. Each one rebuilds its own knowledge base, channel stack and safety layer, and the knowledge stays locked inside.
- African language models are arriving (InkubaLM, Sunflower), but a model does not know which hotline handles gender based violence in Kenya or what moisture level keeps maize free of aflatoxin. Models need grounding.

ACE is the shared layer underneath: open knowledge packs anyone can load, a channel toolkit for the phones people actually use, and a safety rail that runs before anything else. The full competitive map is in [docs/landscape.md](docs/landscape.md).

## What V1 does

| Capability | What it means for a person | Where |
|:--|:--|:--|
| **Grounded answers** | Short, practical answers in English or Swahili, each traced to a published source | `engine.py`, `context/` |
| **Safety rail** | Emergency language in English and Swahili gets verified numbers at once (999, 112, 1195, 116, 1199, 1190) and a human handoff, before retrieval or any model | `safety.py` |
| **Scam Shield** | Forward a suspicious M-PESA message and get an explained verdict built on Safaricom's own guidance. It never calls a message safe | `scam.py` |
| **USSD app** | A full menu on any phone: browse topics, ask in your own words, check a message, switch language. Every screen fits 182 characters | `channels/ussd.py` |
| **SMS** | GSM-7 aware replies within three segments, keyword commands, Africa's Talking sending | `channels/sms.py` |
| **Voice IVR** | Keypad menu over the same knowledge, plus a hook for any speech recognition model | `channels/voice.py` |
| **WhatsApp** | Cloud API webhook with signature checks, sources listed under every answer | `channels/whatsapp.py` |
| **MCP server** | Any AI assistant can ask ACE for cited African context, scam checks and emergency numbers | `mcp_server.py` |
| **Privacy by design** | Phone numbers stored only as salted hashes; FORGET or FUTA deletes everything | `identity.py` |
| **Community loop** | Text TIP or DOKEZO with your advice; it waits for expert review and is never served until checked | `tips.py` |
| **Playground** | A phone simulator in the browser for USSD and SMS, with the sources behind every reply | `ace serve` |

### Starter knowledge for Kenya

37 facts across six packs, each checked against a public source and translated into Swahili. Swahili renderings are marked for review by fluent speakers.

| Pack | Facts | Sources |
|:--|:-:|:--|
| Fall armyworm in maize | 8 | FAO guidance notes, ICIPE, CIFOR-ICRAF |
| Maize drying, storage and aflatoxin | 7 | KALRO, USAID AflaSTOP, CGIAR research |
| Danger signs in pregnancy and after birth | 5 | WHO |
| Mobile money safety | 10 | Safaricom fraud awareness pages |
| Emergency and helpline numbers | 5 | State Department for Gender, NASCOP |
| Rainfall seasons | 2 | Kenya Meteorological Department |

## Quickstart

```bash
git clone https://github.com/tbrunoh/african-context-engine.git
cd african-context-engine
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                                   # 220+ tests, a few seconds
ace demo                                 # one person, four channels, one memory
ace chat --channel ussd                  # a USSD session in your terminal
ace scam "Your SIM is registered twice. Send your M-PESA PIN to confirm"
ace serve                                # open http://127.0.0.1:8000 for the phone playground
```

Connect a real shortcode in [docs/channels.md](docs/channels.md). Add a language model in [docs/architecture.md](docs/architecture.md#language-models).

## How it works

```
 USSD   SMS   Voice   WhatsApp   Web/API   MCP        thin adapters, one Message type
   \      \     |        |         /       /
    +---------------- Engine ----------------+
    | identity    one pseudonymous profile across channels
    | safety      emergency phrases -> verified numbers + human handoff
    | commands    HELP  LANG SW  TIP  SCAM  SOURCES  MORE  FORGET
    | scam        Scam Shield on forwarded money messages
    | retrieve    filters (review, expiry, place, season) then BM25 ranking
    | compose     extractive by default, or a model with a grounding check
    +----------------------------------------+
                      |
            Context packs (YAML, CC BY 4.0, versioned in git)
```

Design choices that matter:

- **Nothing reaches a person unless it is grounded in a checked fact or is a fixed system message.** Draft and expired facts are withheld by default.
- **Safety first, always.** The rail runs before commands, retrieval and generation. HELP followed by an emergency is still an emergency.
- **Honest about gaps.** When no checked fact matches, ACE says so and lists what it can help with.
- **Fits the channel.** Each channel has a character budget, and answers are composed to fit rather than cut mid sentence.
- **No vendor lock in.** Standard library plus PyYAML. Any OpenAI compatible model server works, including models you host yourself.

## Contributing

ACE grows through two kinds of contributors, and both matter equally.

- **People who know a place**: extension officers, clinicians, midwives, agronomists, translators. Add facts to a pack, review a Swahili translation, or start a pack for your county or country. No coding needed. Start with [docs/context-packs.md](docs/context-packs.md).
- **Developers**: new channels, languages, retrieval, evaluation. See [docs/good-first-issues.md](docs/good-first-issues.md) for scoped starter tasks.

Everything else is in [CONTRIBUTING.md](CONTRIBUTING.md). The plan is in [ROADMAP.md](ROADMAP.md).

## Safety and responsibility

ACE is not a doctor, agronomist, lawyer or bank. It shares published guidance and tells people when and where to get human help. The safety phrases and every Swahili rendering need review by clinicians and fluent speakers before a public launch, and each deployment is responsible for its own data protection obligations. Read [docs/safety-and-privacy.md](docs/safety-and-privacy.md) before you deploy. Report vulnerabilities through [SECURITY.md](SECURITY.md).

## License

Code: [Apache License 2.0](LICENSE). Open context packs: CC BY 4.0, see [DATA_LICENSE.md](DATA_LICENSE.md).

---

<sub>Created by <a href="https://github.com/tbrunoh">Tom Bruno</a>, Product and Ecosystem Leader, AI Ecosystems, and maintained with the <a href="AUTHORS">ACE contributors</a>.</sub>
