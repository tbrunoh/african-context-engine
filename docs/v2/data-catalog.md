# Public data and model catalog

Every V2 service is built on the sources below. Each row says what ACE takes from the source, where it applies, how to get access and under what licence. Rows marked waitlist or allowlist need an application, filed in the first week of phase 1. Sources checked on 24 November 2026. The credit ACE will show for each source is in [ACKNOWLEDGMENTS.md](../../ACKNOWLEDGMENTS.md).

## Six licence rules every connector follows

- Record the licence, the attribution line and the refresh schedule in `docs/connectors/<name>.md` before the first fetch, add the source to ACKNOWLEDGMENTS.md, and show the source and its date in every answer.
- CC BY 4.0 data, such as iSDAsoil, the Flood Forecasting API and the University of Ghana sets in WAXAL, can be used and redistributed with attribution. The other WAXAL sets are CC BY-SA 4.0, so anything derived from them carries the same licence.
- ODbL data, such as healthsites.io and OpenStreetMap, stays in its own store, because any database derived from it and shared must also be shared under ODbL.
- Terms of use apply on top of any licence for MedGemma (HAI-DEF terms), HDX HAPI and the FEWS NET Data Warehouse. Read them before a service ships.
- The Community Health Toolkit is AGPL 3.0, so ACE integrates with it over an API and does not copy its code.
- No service depends only on a waitlisted or allowlisted source. Each has an open fallback named in this catalog.

## Weather and climate: ensemble forecasts, station truth and rainfall history

| Source | What ACE uses it for | Coverage | Access and licence | Feeds |
| --- | --- | --- | --- | --- |
| [Google MetNet](https://blog.google/feed/google-ai-weather-forecasting-africa/) | Short term rain forecasts within 5 km, every 15 minutes, 12 hours ahead, shown in Google Search | Across Africa, in Search | No public data access found; ACE points people to Search and asks Google Research Africa about partner access | Rain this week, as a reference |
| [WeatherNext 2](https://developers.google.com/weathernext/guides/models-wn2) and WeatherNext 3 | Global 15 day forecast, 64 member ensemble, about 25 km, new run every 6 hours; the spread of members gives the chance of rain in plain words | Global | BigQuery, Earth Engine and Cloud Storage after a data request; Google recommends WeatherNext 3 for new projects | Rain this week, planting window |
| [TomorrowNow Global Access Platform](https://kartoza.github.io/tomorrownow_gap_documentation/developer/api/guide/measurements/overview) | One REST API over TAHMO and Arable station observations (300+ stations each in East Africa), Google GenCast and Salient seasonal forecasts | East Africa first | Open source platform; API account with authorisation | Rain this week, forecast checks |
| [TAHMO](https://content.meteoblue.com/en/about-us/references/business-partners/tahmo/) | Station observations to measure whether a forecast is right | Sub-Saharan Africa | Free for national met services and researchers | Benchmark |
| [NeuralGCM](https://blog.google/technology/research/indian-farmers-monsoon-prediction/) | Open source hybrid model that, with ECMWF's AIFS, best predicted India's monsoon onset; part of the forecasts sent to 38 million farmers in 2025 | Global | Open source | Planting window |
| [CHIRPS](https://www.chc.ucsb.edu/data/chirps) | Rainfall history since 1981 for season averages, onset dates and baselines; version 3 is now available | Quasi global, 50°S to 50°N | Public domain; cite the 2015 Scientific Data paper | Planting window, benchmark |
| [Digital Earth Africa](https://www.digitalearthafrica.org) | Analysis ready satellite data for Africa, including iSDAsoil layers | Africa | Free sandbox and data cube API | Soil, crop maps |

## Water, floods and official warnings

| Source | What ACE uses it for | Coverage | Access and licence | Feeds |
| --- | --- | --- | --- | --- |
| [Google Flood Forecasting API](https://developers.google.com/flood-forecasting) | Riverine flood forecasts up to 7 days ahead, the same forecasts shown in Flood Hub | Flood Hub covers 150+ countries; the API page lists its countries | Free, CC BY 4.0; waitlist, then an API key | Flood warning |
| [Google flood datasets](https://developers.google.com/flood-forecasting) | Historical flood events (1999 to 2020) and the GRRR river flow reanalysis (1980 to 2023) to set and test thresholds | Global | Public datasets | Flood warning, benchmark |
| [WMO Register of Alerting Authorities](https://alertingauthority.wmo.int) | The official alerting authorities for each country and the addresses of their CAP feeds | Global | Public | Official warnings |
| [IFRC Alert Hub](https://preparecenter.org/?p=26279) | One free source of CAP alerts, limited to official alerting authorities | Global | Free | Official warnings, flood warning |

## Land, soil and crops

| Source | What ACE uses it for | Coverage | Access and licence | Feeds |
| --- | --- | --- | --- | --- |
| [iSDAsoil](https://registry.opendata.aws/isdasoil/) | Over 20 soil properties at 30 m, at 0 to 20 and 20 to 50 cm, each with its prediction error | All of Africa | CC BY 4.0; AWS open data, Earth Engine and Digital Earth Africa | Soil and fertiliser |
| [Agricultural Understanding API](https://developers.google.com/agricultural-understanding/api) | Field boundaries, trees, farm ponds and wells as vectors, with history from 2011 | Kenya, Uganda, Ghana, Rwanda, Zambia, Nigeria | REST on Google Cloud; allowlist | Field level soil and crop advice |
| [AlphaEarth Foundations](https://arxiv.org/abs/2507.22291) | Annual 10 m embeddings for 2017 to 2024 that make crop maps possible from few labels | Global | Open licence | Crop maps for planting and pest services |

## Pests and plant health

| Source | What ACE uses it for | Coverage | Access and licence | Feeds |
| --- | --- | --- | --- | --- |
| [FAO FAMEWS](https://www.fao.org/fall-armyworm/monitoring-tools/en) | Fall armyworm scouting and trap reports, mapped at country and sub country level | Africa and beyond | Free app and platform; FAO states the data is freely available | Pest check, scouting reminders |
| [PlantVillage Nuru](https://pmc.ncbi.nlm.nih.gov/articles/PMC7775399) | Offline phone model for cassava pests and diseases, built as a public good and field tested in East Africa | East Africa | Public good; confirm reuse terms | Design reference for the photo check |
| [kilimoAI](https://icml.cc/virtual/2026/78313) | Over 500,000 curated maize and bean leaf images, published as open datasets, with an offline first deployment | Tanzania | Open datasets | Photo check model |
| [CABI PlantwisePlus Knowledge Bank](https://blog.plantwise.org/2022/11/29/plantwiseplus-knowledge-bank-joins-the-cabi-digital-library/) | Over 15,000 factsheets, decision guides and videos | Plantwise countries | Free to read; reuse terms to be confirmed with CABI | References in pest answers |

## Food security and markets

| Source | What ACE uses it for | Coverage | Access and licence | Feeds |
| --- | --- | --- | --- | --- |
| [WFP food prices on HDX HAPI](https://data.humdata.org/hapi) | Monthly market prices by commodity and market, updated weekly | Countries WFP monitors | No account needed, only an app identifier; HDX HAPI terms of use | Market prices |
| [FEWS NET Data Warehouse API](https://help.fews.net/fde/fews-net-api) | Market prices, IPC food security phases and outlooks | Countries FEWS NET covers | REST API; some data needs partner permission | Food outlook for officials |

## Health

| Source | What ACE uses it for | Coverage | Access and licence | Feeds |
| --- | --- | --- | --- | --- |
| [WHO SMART Guidelines, antenatal care kit](https://www.who.int/publications/i/item/9789240020306) | Decision support tables for antenatal care, imported as signed facts | Global guidance, adapted per country | Public | Pregnancy companion, health worker assist |
| [Kenya Master Health Facility List](https://mfl-api-docs.readthedocs.io/) | Every registered facility with its code, owner, services and coordinates, plus community health units | Kenya | Ministry of Health API | Facility finder |
| [healthsites.io](https://www.digitalpublicgoods.net/r/global-healthsites-mapping-project) | OpenStreetMap based facility data with an API | Global | ODbL | Facility finder outside Kenya |
| [KEMRI-Wellcome public facility database](https://pmc.ncbi.nlm.nih.gov/articles/PMC6658526) | 98,745 public health facilities across sub-Saharan Africa | Sub-Saharan Africa | Free on figshare | Facility finder baseline |
| [Community Health Toolkit](https://medic.org/wp-content/uploads/2025/04/Medic_2024_Annual_Report-Final.pdf) | Apps used by more than 170,000 health workers in 21 countries, including Kenya's national eCHIS | 21 countries | AGPL 3.0; ACE integrates over its API | Health worker assist |
| [MedGemma](https://developers.google.com/health-ai-developer-foundations/medgemma) | Open medical text and image models, plus MedASR for medical speech; optional, for extraction and wording only, never diagnosis | Global | HAI-DEF terms of use; must be validated for each use | Pregnancy companion, optional |

## Language and speech

| Source | What ACE uses it for | Coverage | Access and licence | Feeds |
| --- | --- | --- | --- | --- |
| [WAXAL](https://research.google/blog/waxal-a-large-scale-open-resource-for-african-language-speech-technology/) | Speech recognition and voice data. The dataset card (revision 5f4d8ca, 1 September 2026) lists 2,242 hours of transcribed speech in 19 languages, including Amharic and Afaan Oromo, and 15 voice sets, including Swahili, Hausa and Yoruba. The March 2026 announcement counted 27 languages. ACE measures its language tools on it today; see [speech.md](../speech.md) | More than 26 countries | CC BY 4.0 for University of Ghana sets, CC BY-SA 4.0 for the rest, on Hugging Face | Voice line, language benchmark |
| [Sunbird AI](https://huggingface.co/sunbird) | Sunflower 14B and 32B models for about 40 Ugandan languages; Whisper based speech models for 51 African languages | Uganda and East Africa | Open models on Hugging Face; check each model's licence | Voice, translation |
| [N-ATLaS](https://techcabal.com/2025/09/25/nigerian-government-awarri-launch-n-atlas/) | Open model for Yoruba, Hausa, Igbo and Nigerian accented English, in speech and text | Nigeria | Open on Hugging Face; check licence | Hausa and Yoruba voice |
| [Intron Sahara](https://techcabal.com/2026/03/05/intron-expands-sahara-to-57-languages/) | Speech recognition in 57 languages, including Swahili and English code switching | Africa | Check terms | Voice fallback |
| [Gemma 3n](https://developers.googleblog.com/introducing-gemma-3n-developer-guide/) | Small on device model, about 2 GB of memory, to word answers behind the citation check | Global | Gemma terms | Optional wording |

## Money, telecom and messaging rails

| Source | What ACE uses it for | Coverage | Access and licence | Feeds |
| --- | --- | --- | --- | --- |
| [GSMA Open Gateway SIM Swap](https://www.gsma.com/solutions-and-impact/gsma-open-gateway/gsma-open-gateway-api-descriptions/) | Whether a number changed SIM recently | Live in South Africa with MTN, Telkom and Cell C; other markets through aggregators such as NetAPI | Operator or aggregator contract | Scam Shield 2 |
| [Scam Signal](https://www.gsma.com/newsroom/?p=25403) | Network signal that helps banks stop push payment fraud | UK and South Africa | Bank and operator partnership | Scam Shield 2 |
| [Safaricom Daraja](https://www.safaricom.co.ke/personal/m-pesa/do-more-with-m-pesa/m-pesa-api) | M-PESA payment APIs with a test environment | Kenya | Developer portal | Partner payments only; ACE never holds money |
| [MTN MoMo developer portal](https://www.ericsson.com/en/cases/2023/mtn-mobile-money-open-apis) | Mobile money open APIs with sandbox access | 12 countries in 2023 | Developer portal | Partner payments only |

## Programmes ACE can serve as their shared last mile

| Programme | What it is | Where | How ACE fits |
| --- | --- | --- | --- |
| [Gates Foundation and Google farmer initiative](https://www.gatesfoundation.org/ideas/media-center/press-releases/2026/09/google-ai-farmers) | $100 million to scale AI climate and crop insights to 200 million smallholders, up from 50 million | Sub-Saharan Africa and South Asia | Shared channel, safety layer and local language for grantees |
| [Horizon1000](https://openai.com/index/horizon-1000/) | $50 million from the Gates Foundation and OpenAI to bring AI to 1,000 primary care clinics by 2028 | Rwanda first | Grounding API for intake, triage and referral tools |
| [TomorrowNow and KALRO](https://www.gatesfoundation.org/?p=14956) | Hyper local weather alerts to more than 5 million Kenyan farmers | Kenya | GAP data in, shared alert channel out |
| [AIM for Scale](https://www.eurekalert.org/news-releases/1109162) | AI weather forecasts and advisory, with a shared ambition to reach 100 million farmers by 2030 | Africa, Asia, Latin America | Decision oriented benchmarking for the planting window |
| [Kenya eCHIS](https://medic.org/stories/over-100000-community-health-workers-now-using-open-source-apps-to-deliver-healthcare/) | National community health information system built on the Community Health Toolkit | Kenya | Health worker assist |

## Agent standards and build tools

- [Model Context Protocol](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation), now under the Linux Foundation's Agentic AI Foundation, is how partners and agents call ACE.
- [Google Antigravity 2.0](https://thenextweb.com/news/google-antigravity-2-desktop-cli-sdk-io-2026), announced at Google I/O in May 2026 with a desktop app, a CLI and an SDK, is the build environment in the [build plan](build-plan.md).
