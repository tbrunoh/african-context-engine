# ACE V2

V2 turns the best public data and open models into decisions people can act on today, on any phone. It keeps everything release 1.1.0 proved and adds twelve decision services built on named public data, voice in African languages, knowledge that stays true, and a shared layer that any health, farming or assistant service can call.

Release 2.1 preview (2.1.0b1, 24 November 2026) ships the foundations and six of the twelve services (rain this week, official warnings, nearest health facility, market prices, the pregnancy companion and the crop problem check) in 34 countries and eight languages. Each covers every country wherever open data exists and names the gap where it does not. The [2.1 design](release-2.1.md) records the new countries, languages and data decisions. The [services guide](../services.md) has the decision rules and the coverage, and the [connector pages](../connectors/README.md) have the sources. Release 2.2 preview (2.2.0b2, 25 November 2026) starts the voice epic: speech and translation interfaces with Google Cloud providers, a voice line that speaks only languages with a known voice, Amharic and Somali on that line through Gemini 3.8 Flash TTS, and a language check on real speech text from WAXAL. See [speech.md](../speech.md). The rest of V2 follows the roadmap below.

<img src="hero.svg" alt="ACE V2 in one picture: public data and open models go in; ACE fetches them into dated snapshots, runs the safety rail first and applies a published decision rule; people get a short, cited answer on any phone" width="100%">

## Start here

Read the three documents in this order. Each one stands on its own.

| Document | What it covers |
| --- | --- |
| [Product spec](product-spec.md) | The big picture, who V2 serves, the twelve services, three journeys, pillars, architecture, roadmap, measures, risks and the decisions needed before phase 1 |
| [Data and model catalog](data-catalog.md) | Every public dataset, model and programme V2 builds on, with coverage, access and licence |
| [Release 2.1 design](release-2.1.md) | The 21 new countries, five new languages, the alphabet each reply travels in, the five data problems ACE designs around, decisions, gaps and gates |
| [Build plan](build-plan.md) | How the work runs in Google Antigravity: repository layout, the two contracts, epics with done criteria, first sprint prompts and the evaluation plan |

The agent rules for the build are in [AGENTS.md](../../AGENTS.md). Every organisation whose work ACE uses, today or in V2, is credited in [ACKNOWLEDGMENTS.md](../../ACKNOWLEDGMENTS.md).

<img src="services.svg" alt="Twelve V2 decision services, each built on named public data and marked with the phase in which it ships" width="100%">

<img src="roadmap.svg" alt="V2 roadmap: four quarterly phases from December 2026 to November 2027, each closed by a measurable gate" width="100%">
