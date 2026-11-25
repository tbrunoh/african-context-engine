# Competitive landscape and where ACE fits

Last reviewed: 23 November 2026. Every figure below links to its source. Corrections are welcome through a pull request.

## The short version

AI for African users is arriving through three kinds of players. Each solves part of the problem and leaves the same gap: **trusted, local, citable knowledge that any service can reuse, on any channel, without a smartphone.** ACE is built for that gap. It is not another chatbot. It is the shared context layer and channel toolkit that chatbots, call centres, NGOs, governments and global AI assistants can all draw on.

## 1. Vertical advisory services

| Service | What it does | Reach and evidence | What it leaves open |
|:--|:--|:--|:--|
| Digital Green FarmerChat | Generative AI farm advisory by text, voice and photo | Nearly 3 million farmers across six countries in more than ten languages, as of July 2026 ([Digital Green](https://www.digitalgreen.org/insights/v2-launch-performance)) | Curated knowledge sits inside one programme; app and chat first |
| Jacaranda Health PROMPTS | AI enabled two way SMS for pregnant and postpartum mothers, with a nurse helpdesk for urgent cases | Reached more than 3.8 million mothers in Kenya by March 2026, and launched in Kano State, Nigeria ([eHealth Africa](https://ehealthafrica.org/press-release/jacaranda-health-ehealth-africa-target-25000-mothers-ai-powered-maternal-health-support-nigeria/)); enrolled mothers were 2.28 times more likely to report four or more antenatal visits ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10967085)) | Maternal health only; enrolment through public facilities |
| iShamba (Mediae) | SMS tips, market prices, weather and an agronomist call centre | Builds on the Shamba Shape Up TV audience ([Torchbox](https://torchbox.com/work/mediae)) | Subscription service; content is not open for reuse |
| Apollo Agriculture | Inputs, credit, insurance and advice; farmers apply by SMS or USSD | Serves over 100,000 farmers in Kenya and Zambia ([FAO AgriTech Observatory](https://agritechobservatory.review.fao.org/es/apollo-agriculture)) | Advice serves a lending business, not a public good |
| Viamo and MTN Miss Baza | Voice first generative AI on any phone, reached by dialling a short code | Miss Baza launched in Rwanda on 845 in October 2026 and has reached more than 500,000 users ([The New Times](https://www.newtimes.co.rw/article/40095/news/featured/no-smartphone-no-internet-mtns-miss-baza-brings-ai-powered-services-to-your-phone)); Viamo has deployments with MTN in Ghana, Liberia, Zambia and Rwanda ([Dealroom](https://dealroom.co/news/169088-mtn-rwanda-launches-miss-baza-a-voice-first-ai-anyone-can-call/)) | Proves voice demand; local content partners are wired in one by one |

**Pattern:** every programme rebuilds the same three things: a curated local knowledge base, a channel stack for USSD, SMS, voice and WhatsApp, and a safety layer. The knowledge stays locked inside each programme. Miss Baza already relies on local content partners for Rwandan context ([KT Press](https://www.ktpress.rw/?p=133189)), which is exactly the role an open context layer plays.

## 2. African language models

| Effort | What it is |
|:--|:--|
| Lelapa AI InkubaLM | A 0.4B parameter model for isiZulu, Yoruba, Swahili, isiXhosa and Hausa, released under CC BY-NC 4.0 ([Hugging Face](https://huggingface.co/lelapa/InkubaLM-0.4B)) |
| Sunbird AI Sunflower | 14B and 32B models built on Qwen 3 with comprehension of most Ugandan languages, released open ([arXiv](https://arxiv.org/html/2510.07203v1)) |

**Pattern:** models make African languages workable, but a model does not know which hotline handles gender based violence in a given country, or that a maize store needs grain at 13 percent moisture. Models need grounding. ACE supplies it and stays model agnostic, so any of these models can sit behind it.

## 3. Platforms and protocols

* **WhatsApp.** Since 15 January 2026 the WhatsApp Business API bars general purpose AI assistants; business service bots remain allowed ([TechCrunch](https://techcrunch.com/2025/10/18/whatssapp-changes-its-terms-to-bar-general-purpose-chatbots-from-its-platform/)). ACE answers only from defined context packs, which keeps each deployment a scoped service.
* **USSD.** On Kenyan networks a session lasts up to 180 seconds; Safaricom drops a session after 30 seconds without input, and Airtel gives the application 15 seconds to respond ([Africa's Talking](https://help.africastalking.com/en/articles/1284071-what-is-the-duration-of-a-ussd-session-for-kenyan-telcos)). ACE composes every screen locally and never waits on a remote model inside a USSD session.
* **MCP.** The Model Context Protocol now sits under the Agentic AI Foundation at the Linux Foundation ([Linux Foundation](https://linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)). ACE ships an MCP server so any assistant can ask for African context with citations.

## Where ACE is different

1. **A commons, not an app.** Knowledge lives in open, versioned context packs with sources, geography, season, expiry and review status. Any service can load the same packs.
2. **Reach by default, richer by choice.** USSD, SMS and voice are first class: every answer, service and safety feature works on them, with no smartphone or data plan. WhatsApp, RCS and apps built on the API are optional layers for people who have both, and RCS falls back to SMS. Answers are composed to each channel's limits.
3. **Works with no model and no API key.** The default answerer is extractive and deterministic: cheap, fast and auditable. A language model can be plugged in, and ACE falls back to extractive answers whenever the model is slow or strays from the facts.
4. **Safety before anything else.** Emergency language in eight languages routes straight to the caller's own national hotlines, verified for 34 countries, before retrieval or generation runs.
5. **Scam Shield.** People forward a suspicious mobile money message and get an explained verdict grounded in the operator's own published guidance.
6. **Privacy by design.** Phone numbers are pseudonymised, conversation history is optional, and one word deletes a person's data, in line with the principles of Kenya's Data Protection Act 2019 ([ODPC](https://www.odpc.go.ke/wp-content/uploads/2024/02/TheDataProtectionAct__No24of2019.pdf)).
7. **A community knowledge loop.** Anyone can text a tip. It lands in a review queue, never in answers, until a reviewer approves it into a pack.

## Who ACE is for

* **Programmes and NGOs** that want USSD, SMS, RCS, voice and WhatsApp advisory without building a stack.
* **County and national governments** that want to publish extension, health and safety guidance once and serve it everywhere.
* **AI assistants and model builders** that need grounded, cited African context through MCP.
* **Contributors** who know their place and field: extension officers, clinicians, agronomists, translators and developers.
