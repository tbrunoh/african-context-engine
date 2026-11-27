# Acknowledgments

ACE stands on work published by governments, UN agencies, research institutes, companies and journalists. This file names every organisation whose published work ACE uses today, says what ACE takes from each one, lists the sources the V2 design plans to use with the credit each requires, and sets the rules for crediting new sources.

## How ACE credits a source

- **The packs are the record.** Every fact in a context pack carries `source`, `source_url` and `checked_on`, and a person can see the source of any answer with the SOURCES command (VYANZO in Swahili). This file summarises those records.
- **Facts, not copies.** ACE restates facts in its own words and links to the original. It does not copy documents, logos or long passages.
- **Each source keeps its own rights.** The CC BY 4.0 licence on ACE's open packs covers ACE's own wording and compilation. Every original source keeps its copyright and terms of use.
- **A credit is not an endorsement.** Naming an organisation here records that ACE uses its published work. It does not mean that the organisation endorses, reviews or partners with ACE. All names and marks belong to their owners.
- **Corrections come first.** If you represent an organisation listed here and want a credit corrected, a link changed or a fact removed, open an issue at [github.com/tbrunoh/african-context-engine/issues](https://github.com/tbrunoh/african-context-engine/issues). The change will be made before the next release.

## Sources used in release 1.1.0

### Health guidance

| Organisation | What ACE uses | Pack |
| --- | --- | --- |
| World Health Organization | Danger signs in pregnancy and after birth, from [Counselling for maternal and newborn health care](https://www.ncbi.nlm.nih.gov/books/NBK304178/) and the [World Health Day 2025 key messages](https://www.who.int/campaigns/world-health-day/2025/key-messages) | `africa/maternal-danger-signs` |

### Agriculture and weather

| Organisation | What ACE uses | Pack |
| --- | --- | --- |
| Food and Agriculture Organization of the United Nations (FAO) | [Fall armyworm management guidance for smallholders](https://openknowledge.fao.org/server/api/core/bitstreams/f1e28a46-3822-4c03-bc31-4294e7e83ea1/content) and [Fall Armyworm Guidance Notes 2 and 4](https://ges.research.ncsu.edu/wp-content/uploads/2018/10/FAW-How-to-Manage-FAW-Guidance-note-4-Allan-Hruska.pdf) | `africa/maize-fall-armyworm` |
| International Centre of Insect Physiology and Ecology (ICIPE) | [Fall armyworm identification, management and control](https://technologytransfer.icipe.org/wp-content/uploads/2021/04/Fall-Armyworm-Brochure-Identification-Management-and-Control-1.pdf) and [push-pull guidance](https://technologytransfer.icipe.org/wp-content/uploads/2021/04/FAW-Comic.pdf) | `africa/maize-fall-armyworm` |
| CIFOR-ICRAF | Fall armyworm guide | `africa/maize-fall-armyworm` |
| Oklahoma State University Extension and Texas A&M AgriLife Extension | [Fall armyworm pest alert](https://extension.okstate.edu/e-pest-alerts/2024/fall-armyworms-aug-28-2024.html) | `africa/maize-fall-armyworm` |
| Pacific Pests, Pathogens and Weeds | Fall armyworm fact sheet | `africa/maize-fall-armyworm` |
| Kenya Agricultural and Livestock Research Organization (KALRO) | [Maize post harvest guidance](https://www.kalro.org/maize/maize-post-harvest) | `ke/maize-post-harvest` |
| USAID AflaSTOP, and Nganga, Mutungi and Imathiu (2016), Journal of Stored Products Research | [Evidence on hermetic storage](https://pdf.usaid.gov/pdf_docs/PA00MV4J.pdf) | `ke/maize-post-harvest` |
| Kenya Meteorological Department | [March to May 2025 and 2026 seasonal forecasts](https://meteo.go.ke/documents/2537/March-April-May_MAM_2026_Seasonal_Weather_Forecast.pdf) | `ke/rainfall-seasons` |

### Emergency and helpline numbers

Every number was checked against the sources below on 23 November 2026, and Namibia's again on 24 November 2026 after its earlier source stopped showing them. Each country's pack is `context_packs/<country code>/emergency-contacts.yaml`.

| Country | Sources |
| --- | --- |
| Kenya | [State Department for Gender and Affirmative Action](https://migecah.go.ke/index.php/gbv-prevention-and-response); [NASCOP](https://nascop.or.ke/wp-content/uploads/2025/08/NASCOP_FAQ_GBV_PRINT-COPY-1-2-compressed.pdf); UN Women Kenya; UNHCR Kenya; [The Standard](https://www.standardmedia.co.ke/business/amp/national/article/2001432592/emergency-numbers-you-should-have-over-the-holiday) |
| Tanzania | [UK Foreign, Commonwealth and Development Office (FCDO)](https://www.gov.uk/foreign-travel-advice/tanzania/getting-help); Government of Canada; [Child Helpline International](https://childhelplineinternational.org/helplines/) |
| Uganda | [UK FCDO](https://www.gov.uk/foreign-travel-advice/uganda/getting-help); Australian Government Smartraveller; Uganda Police Force, Child and Family Protection Department, reported by [Nile Post](https://nilepost.co.ug/news/109883/police-ask-gender-based-violence-victims-to-always-speak-out); UN Women Uganda; [UNICEF Uganda](https://www.unicef.org/uganda/stories/sauti-116-bolsters-government-response-violence-and-abuse-homes-and-communities-uganda) |
| Rwanda | [Government of Rwanda](https://www.gov.rw/emergency) |
| South Africa | [UK FCDO](https://www.gov.uk/foreign-travel-advice/south-africa/getting-help); Western Cape Government; Government of Canada; [Department of Justice and Constitutional Development](https://www.justice.gov.za/vg/GBV.html); Child Helpline International |
| Botswana | [Botswana Police Service](https://www.police.gov.bw/images/Magazines/Issue_12025.pdf); Child Helpline International |
| Namibia | [UK FCDO](https://www.gov.uk/foreign-travel-advice/namibia/getting-help); [LifeLine/ChildLine Namibia](https://www.lifelinechildline.org.na/); Namibian Police Force |
| Zimbabwe | [UK FCDO](https://www.gov.uk/foreign-travel-advice/zimbabwe/getting-help); Government of Canada; Government of Zimbabwe; Child Helpline International |
| Nigeria | [UK FCDO](https://www.gov.uk/foreign-travel-advice/nigeria/getting-help); Nigerian Communications Commission; Government of Canada; Child Helpline International |
| Ghana | [Government of Canada](https://travel.gc.ca/assistance/embassies-consulates/ghana); Australian Government Smartraveller; UK FCDO; [Ministry of Gender, Children and Social Protection](https://www.mogcsp.gov.gh/market-sensitization/); UNFPA Ghana |
| Senegal | [UK FCDO](https://www.gov.uk/foreign-travel-advice/senegal/getting-help); Government of Canada; [Ministère de la Santé et de l'Action sociale](https://sante.gouv.sn/documentations-generales); Child Helpline International |
| Côte d'Ivoire | [UK FCDO](https://www.gov.uk/foreign-travel-advice/cote-d-ivoire/getting-help); Government of Canada; Australian Government Smartraveller; [Ministère de la Femme, de la Famille et de l'Enfant](https://famille.gouv.ci/vbg_app/public/storage/vbg/V1_Kit_Media_Engagement_National_VBG.pdf); Child Helpline International |
| Togo | [UK FCDO](https://www.gov.uk/foreign-travel-advice/togo/getting-help); Government of Canada; Child Helpline International |

### Mobile money safety

| Organisation | What ACE uses | Where |
| --- | --- | --- |
| Safaricom | Fraud awareness guidance: [tips for staying safe](https://safaricom.co.ke/fraud-awareness/tips-tricks), [types of fraud](https://safaricom.co.ke/fraud-awareness), [fake or old M-PESA messages](https://safaricom.co.ke/fraud-awareness/m-pesa-fraud/fake-old-m-pesa-message), [Secure M-PESA](https://safaricom.co.ke/main-mpesa/m-pesa-for-you/m-pesa-tips/secure-m-pesa), [device security](https://safaricom.co.ke/personal/value-added-services/other-services/securing-your-mobile-phone-device) and [fake branded links](https://safaricom.co.ke/fraud-awareness/impersonation/fake-safaricom-branded-online-links-websites) | `ke/mobile-money-safety` and the Scam Shield signals in `src/ace_engine/scam.py`, shown only to callers in Kenya |

### News reporting used to confirm facts

ACE prefers primary sources. Where a fact was confirmed through reporting, the outlet is credited: [The Standard](https://www.standardmedia.co.ke/business/amp/national/article/2001432592/emergency-numbers-you-should-have-over-the-holiday), [The Star](https://the-star.co.ke/news/2023-08-03-dry-and-store-maize-well-to-avoid-aflatoxin-farmers-told), [Daily Nation, Seeds of Gold](https://nation.africa/kenya/business/seeds-of-gold/keep-in-control-maize-losses-this-rainy-season-474984), [Nile Post](https://nilepost.co.ug/news/109883/police-ask-gender-based-violence-victims-to-always-speak-out) and [K24 Digital](https://k24.digital/lifestyle/money/safaricom-lists-fake-fuliza-limit-messages-among-top-scams-targeting-m-pesa-users).

## Sources added in release 2.0 preview

Every dataset below is fetched by a connector into a dated snapshot, and its licence is recorded in [`snapshots/register.yaml`](snapshots/register.yaml). Each connector has a page in [`docs/connectors/`](docs/connectors/README.md).

### Data behind the decision services

| Organisation | What ACE uses | Licence and credit |
| --- | --- | --- |
| ECMWF | IFS ensemble forecasts, open data, for rain this week | CC BY 4.0 |
| Open-Meteo | The [Ensemble API](https://open-meteo.com/en/docs/ensemble-api) that serves the ECMWF data. Weather data by Open-Meteo.com | CC BY 4.0; free API for non-commercial use |
| World Meteorological Organization | The [Register of Alerting Authorities](https://alertingauthority.wmo.int/), which names each country's official CAP feed | Index of official sources |
| Kenya Meteorological Department; Tanzania Meteorological Authority; Uganda Department of Meteorological Services; South African Weather Service; Botswana Meteorological Services; Zimbabwe Meteorological Services Department; Nigerian Meteorological Agency; Ghana Meteorological Agency; ANACIM, Senegal; Direction de la Météorologie Nationale (SODEXAM), Côte d'Ivoire; Agence Nationale de la Météorologie du Togo | Official CAP warnings, passed on in the authority's own words | Public warnings; each credited to its authority |
| World Food Programme | The [WFP Price Database](https://data.humdata.org/organization/wfp), food prices by market for 12 countries | CC BY-IGO |
| KEMRI-Wellcome Trust Research Programme | Maina J, Ouma PO, Macharia PM et al. (2019), [A spatial database of health facilities managed by the public health sector in sub Saharan Africa](https://doi.org/10.1038/s41597-019-0142-2), Scientific Data 6: 134 | CC BY 4.0 |
| UN OCHA and the Humanitarian Data Exchange | Hosting of the price and facility datasets, and [COD-AB boundaries](https://data.humdata.org/dataset/cod-ab-uga) for Uganda (Uganda Bureau of Statistics) and Namibia (Namibia Statistics Agency) | CC BY-IGO |
| geoBoundaries, William & Mary geoLab | [First level boundaries](https://www.geoboundaries.org/) for 11 countries (Runfola et al. 2020), with the national and open sources named in each snapshot, including OpenStreetMap contributors for Tanzania, Togo, Botswana and Ghana | Licence recorded per country; ODbL data in its own store |

### Guidance in the new packs

| Organisation | What ACE uses | Pack |
| --- | --- | --- |
| World Health Organization | [New guidelines on antenatal care for a positive pregnancy experience](https://www.who.int/news/item/07-11-2016-new-guidelines-on-antenatal-care-for-a-positive-pregnancy-experience) (2016) | `africa/antenatal-care` |
| CIMMYT | [Maize lethal necrosis symptoms and best practices](https://mln.cimmyt.org/wp-content/uploads/sites/39/2016/06/MLN-FLYER-final-complete.pdf) | `africa/crop-pests-diseases` |
| CABI Plantwise, with the Tanzania Ministry of Agriculture, Food Security and Cooperatives | [Control of cassava mosaic disease by uprooting](https://farmknowledge.info/sites/default/files/resource/20157800492.pdf) (2014) and [Life cycle of the tomato leaf miner](https://factsheetadmin.plantwise.org/Uploads/PDFs/20187800458.pdf) (Ghana, 2018) | `africa/crop-pests-diseases` |
| Bioversity International | [Single diseased stem removal for Xanthomonas wilt of banana](https://core.ac.uk/download/211048384.pdf) | `africa/crop-pests-diseases` |
| International Institute of Tropical Agriculture (IITA) | [Single diseased stem removal to control banana Xanthomonas wilt](https://www.iita.org/news-item/novel-and-effective-technique-to-control-banana-xanthomonas-wilt-is-suitable-for-rwandan-agroecology/) (2020) | `africa/crop-pests-diseases` |
| World Vegetable Center, with TAHA and icipe | [Tuta absoluta flyer](https://worldveg.tind.io/record/66511/files/Tuta-revised-flyer.pdf) (2016) | `africa/crop-pests-diseases` |

## Sources added in release 2.1 preview

Release 2.1 adds 21 countries and five languages. Every dataset below is fetched by a connector into a dated snapshot and recorded in [`snapshots/register.yaml`](snapshots/register.yaml).

### Emergency and helpline numbers for the 21 new countries

Every number was checked on 24 November 2026 against the getting help page the UK Foreign, Commonwealth and Development Office publishes for the country, under the Open Government Licence. Each fact expires after a year, and the number watcher rechecks each page weekly.

| Country | Source |
| --- | --- |
| DR Congo | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/democratic-republic-of-the-congo/getting-help) |
| Malawi | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/malawi/getting-help) |
| Burundi | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/burundi/getting-help) |
| Cameroon | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/cameroon/getting-help) |
| Benin | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/benin/getting-help) |
| Zambia | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/zambia/getting-help) |
| Chad | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/chad/getting-help) |
| Guinea | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/guinea/getting-help) |
| Burkina Faso | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/burkina-faso/getting-help) |
| South Sudan | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/south-sudan/getting-help) |
| Ethiopia | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/ethiopia/getting-help) |
| Mozambique | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/mozambique/getting-help) |
| Guinea-Bissau | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/guinea-bissau/getting-help) |
| Angola | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/angola/getting-help) |
| Somalia | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/somalia/getting-help) |
| Sudan | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/sudan/getting-help) |
| Algeria | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/algeria/getting-help) |
| Egypt | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/egypt/getting-help) |
| Libya | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/libya/getting-help) |
| Morocco | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/morocco/getting-help) |
| Tunisia | [UK FCDO, getting help](https://www.gov.uk/foreign-travel-advice/tunisia/getting-help) |

### Data behind the services in the new countries

| Organisation | What ACE uses | Licence and credit |
| --- | --- | --- |
| National meteorological services of 19 new countries: METTELSAT, Météo RD Congo; Department of Climate Change and Meteorological Services; Institut Géographique du Burundi (IGEBU); Direction de la Météorologie Nationale du Cameroun; Météo-Bénin; Zambia Meteorological Department; Agence Nationale de la Météorologie du Tchad; Agence Nationale de la Météorologie de Guinée; Agence Nationale de la Météorologie du Burkina Faso; South Sudan Meteorological Service; Ethiopian Meteorological Institute; Instituto Nacional de Meteorologia de Moçambique; Instituto Nacional de Meteorologia da Guiné-Bissau; Somalia National Meteorological Agency; Sudan Meteorological Authority; Office National de la Météorologie; Egyptian Meteorological Authority; Libyan National Meteorological Centre; Institut National de la Météorologie | Official CAP warnings listed in the WMO Register of Alerting Authorities, passed on in the authority's own words | Public warnings; each credited to its authority |
| World Food Programme | Price datasets for 19 more countries, 31 in all | CC BY-IGO |
| KEMRI-Wellcome Trust Research Programme | The 2019 public facility list for 16 more sub-Saharan countries | CC BY 4.0 |
| UN OCHA and the national offices that endorse each layer | COD-AB boundaries on HDX for the 21 new countries, each linked in its places snapshot, with the national source named in each places snapshot: Référentiel Géographique Commun (DR Congo), National Statistics Office (Malawi), Bureau de Centralisation de Géomatique (Burundi), Institut National de Cartographie (Cameroon), SALB (Benin, Guinea-Bissau), DMMU (Zambia), INSEED (Chad), WFP (Guinea), Institut Géographique du Burkina, South Sudan IMWG and National Bureau of Statistics, Central Statistics Agency and regional bureaus (Ethiopia), INE (Mozambique), INE and GADM (Angola), OCHA Somalia, Sudan IMWG, UNHCR from GAUL (Algeria), CAPMAS (Egypt), UNITAR-UNOSAT and the Libyan Bureau of Statistics (Libya), Haut Commissariat au Plan (Morocco) and Institut National de la Statistique (Tunisia) | CC BY-IGO |
| International Plant Protection Convention | Egypt's [first report of fall armyworm](https://ippc.int/en/countries/egypt/pestreports/2019/06/report-of-first-detection-of-spodoptera-frugiperda-fall-armyworm-faw-in-egypt) (2019), the basis for offering the fall armyworm pack there | Official pest report |

### Sources held until their licence is cleared

| Organisation | What ACE would use | Status |
| --- | --- | --- |
| Malawi Ministry of Health | The [Malawi Health Facility Registry](https://zipatala.health.gov.mw/): facilities, positions and contact numbers | No licence stated. The connector is built and held until the ministry confirms reuse in writing |
| Zambia Ministry of Health | The [Zambia Health Facility Registry](https://zhfr.moh.gov.zm/): facilities, positions and phone numbers | No licence stated. The connector is built and held until the ministry confirms reuse in writing |

## Sources added in release 2.2 preview

| Organisation | What ACE uses | Licence | Where |
| --- | --- | --- | --- |
| Google Research, with Makerere University, the University of Ghana, Digital Umuganda, Media Trust, Loud and Clear and AIMS Senegal | The [WAXAL speech corpus](https://huggingface.co/datasets/google/WaxalNLP) ([paper](https://arxiv.org/abs/2602.02734)): transcriptions and voice scripts in 29 sets, read at run time to measure ACE's language guess, safety rail and service router. No WAXAL text or audio is stored in ACE | CC BY 4.0 for the University of Ghana sets; CC BY-SA 4.0 for the others. Partners keep ownership | `benchmark/waxal.py`, [docs/speech.md](docs/speech.md) |
| Google Cloud | Published language lists for [Speech-to-Text](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3), [Text-to-Speech](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd) and [Cloud Translation](https://docs.cloud.google.com/translate/docs/languages), checked on 25 November 2026 | Public documentation | `src/ace_engine/speech/support.yaml` |
| Google AI for Developers | Published language lists for [Gemini TTS](https://ai.google.dev/gemini-api/docs/speech-generation) and [Gemini 3.5 Transcribe](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-transcribe), checked on 25 November 2026 | Public documentation | `src/ace_engine/speech/support.yaml` |
| Africa's Talking | The [Say action](https://developers.africastalking.com/docs/voice/actions/say) reads text with Google Cloud Text-to-Speech voices, which sets which languages the keypad line can speak without synthesis | Public documentation | `src/ace_engine/channels/voice.py` |

### Used by the tokenizer audit in 2.2.0b3

| Organisation | What ACE uses | Licence | Where |
| --- | --- | --- | --- |
| Meta AI and the NLLB team | The [FLORES-200](https://github.com/facebookresearch/flores/blob/main/flores200/README.md) dev and devtest sentences, downloaded at run time to measure tokenizers. No FLORES text is stored in ACE | CC BY-SA 4.0 | `benchmark/tokenizer-audit` |
| Abdulmumin et al. (2024), from Data Science for Social Impact at the University of Pretoria and co-authors | [Native speaker corrections](https://github.com/dsfsi/flores-fix-4-africa) to FLORES for Hausa, Northern Sotho, Xitsonga and isiZulu (Abdulmumin et al., 2024), downloaded at run time from one pinned commit | As published by the authors | `benchmark/tokenizer-audit` |
| OpenAI, Meta, Alibaba Qwen, Google, DeepSeek, Mistral AI and NVIDIA | The published tokenizers of o200k and cl100k (through tiktoken, which checks its own files), Llama 3 and Llama 4 (through the unsloth mirrors on Hugging Face, because Meta's repositories require a sign in), Qwen3 and Qwen3.5, Gemma 3 and Gemma 4, DeepSeek-V3 and DeepSeek-V4, Mistral Tekken and Nemotron 3 Nano, downloaded at run time from pinned commits and checked against their SHA-256 | Each publisher's licence | `benchmark/tokenizer-audit/tokenizers.json` |

### Used by the language profiles in 2.3

| Organisation | What ACE uses | Licence | Where |
| --- | --- | --- | --- |
| Meta AI and the NLLB team | The [FLORES-200](https://github.com/facebookresearch/flores/blob/main/flores200/README.md) dev sentences of ACE's languages and of 19 languages ACE does not speak, downloaded once from the pinned archive the tokenizer audit uses, and counted into three letter sequences. No FLORES sentence is stored; the counts are shared under the same licence | CC BY-SA 4.0 | `benchmark/langid/build.py`, `src/ace_engine/langid/profiles.json` |
| The Office of the United Nations High Commissioner for Human Rights, and the UDHR in XML project of Eric Muller and the Unicode Consortium | Translations of the [Universal Declaration of Human Rights](https://www.ohchr.org/en/human-rights/universal-declaration/universal-declaration-human-rights/about-universal-declaration-human-rights-translation-project), 77 files, from [github.com/eric-muller/udhr](https://github.com/eric-muller/udhr) at one pinned commit, each file checked against its SHA-256 in `benchmark/langid/sources.json` and counted into three letter sequences. No text is stored | Published by OHCHR through its [translation project](https://www.ohchr.org/en/human-rights/universal-declaration/universal-declaration-human-rights/about-universal-declaration-human-rights-translation-project); the UDHR in XML repository states no licence | `benchmark/langid/build.py`, `src/ace_engine/langid/profiles.json` |
| Google | The [Speech-to-Text V2 language list](https://docs.cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages), the [Cloud Text-to-Speech voice list](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types), the [Gemini speech generation page](https://ai.google.dev/gemini-api/docs/speech-generation) and [Cloud Translation language detection](https://docs.cloud.google.com/translate/docs/detect-language), checked on 26 November 2026 | Public documentation | `src/ace_engine/speech/support.yaml`, `src/ace_engine/speech/google.py` |
| Kargaran, Imani, Yvon and Schütze, LMU Munich | [GlotLID](https://github.com/cisnlp/GlotLID), an optional language identifier an operator can run; ACE neither ships nor downloads it | Apache 2.0 | `src/ace_engine/langid/__init__.py` |

## Software, services and standards

| Project or service | How ACE uses it | Licence or terms |
| --- | --- | --- |
| [PyYAML](https://github.com/yaml/pyyaml) | Loads context packs; the only required dependency | MIT |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Optional `mcp` extra for the MCP server | MIT |
| [pytest](https://github.com/pytest-dev/pytest) and [Ruff](https://docs.astral.sh/ruff/) | Tests and linting, development only | MIT |
| [Model Context Protocol](https://modelcontextprotocol.io/) | The protocol ACE's MCP server speaks | Open specification under the Linux Foundation's Agentic AI Foundation |
| Africa's Talking | SMS sending over its HTTP API, when a deployment configures it | Provider terms |
| WhatsApp Cloud API (Meta) | WhatsApp channel, when a deployment configures it | Provider terms |
| Any OpenAI compatible model server | Optional wording of answers, behind ACE's citation check | Provider or model terms |
| [Google Cloud Speech-to-Text, Text-to-Speech and Cloud Translation](https://cloud.google.com/speech-to-text) | Optional `google` extra: spoken questions and replies on the voice line, and back translation reports for locale reviewers | Google Cloud terms of the operator's own account |
| [Gemini API](https://ai.google.dev/gemini-api/docs/speech-generation) | Optional Gemini 3.8 Flash TTS voices for Amharic and Somali on the voice line, with a key from `GEMINI_API_KEY` | Gemini API terms of the operator's own account |
| [google-auth](https://github.com/googleapis/google-auth-library-python) | Application Default Credentials for the optional `google` extra | Apache 2.0 |

## Planned for later V2 releases: sources and the credit each requires

None of these sources is in the code yet. The [V2 design](docs/v2/README.md) plans to use them. Before a connector fetches anything, it must record the licence and the credit line in `docs/connectors/<name>.md`, and every answer built on it must show the source and its date. The [V2 data and model catalog](docs/v2/data-catalog.md) gives the details of each.

| Source | Owner | Licence or terms | Credit ACE will show |
| --- | --- | --- | --- |
| [Flood Forecasting API](https://developers.google.com/flood-forecasting) and flood datasets | Google | CC BY 4.0 | Google Flood Forecasting, CC BY 4.0 |
| [WAXAL speech dataset](https://research.google/blog/waxal-a-large-scale-open-resource-for-african-language-speech-technology/), for training voice models | Google Research with African academic and community partners | CC BY 4.0 for the University of Ghana sets; CC BY-SA 4.0 for the others | WAXAL with the citation given in its paper; a model trained on a CC BY-SA set carries that licence |
| [iSDAsoil](https://registry.opendata.aws/isdasoil/) | Innovative Solutions for Decision Agriculture (iSDA) | CC BY 4.0 | iSDAsoil, with Miller and others (2021), PLoS Biology 19(11): e3001441 |
| [WeatherNext 2 and 3](https://developers.google.com/weathernext/guides/models-wn2) | Google DeepMind and Google Research | Terms accepted with the data request | As those terms require |
| [Agricultural Understanding API](https://developers.google.com/agricultural-understanding/api) | Google | Google Cloud terms; allowlist | As those terms require |
| [AlphaEarth Foundations embeddings](https://arxiv.org/abs/2507.22291) | Google DeepMind | Open licence stated by the authors | As the dataset page requires |
| [NeuralGCM](https://blog.google/technology/research/indian-farmers-monsoon-prediction/) | Google Research | Open source | As the repository licence requires |
| [TomorrowNow Global Access Platform](https://kartoza.github.io/tomorrownow_gap_documentation/developer/api/guide/measurements/overview), with TAHMO and Arable station data | TomorrowNow, TAHMO, Arable | Account terms | Each underlying data provider by name |
| [CHIRPS](https://www.chc.ucsb.edu/data/chirps) | Climate Hazards Center, UC Santa Barbara | Public domain | CHIRPS, with the 2015 Scientific Data paper, doi:10.1038/sdata.2015.66 |
| [Digital Earth Africa](https://www.digitalearthafrica.org) | Digital Earth Africa | Free use | Digital Earth Africa and the underlying product |
| [WMO Register of Alerting Authorities](https://alertingauthority.wmo.int), national CAP feeds and the [IFRC Alert Hub](https://preparecenter.org/?p=26279) | WMO, national alerting authorities, IFRC | Public | The issuing authority, named on every warning |
| [FAO FAMEWS](https://www.fao.org/fall-armyworm/monitoring-tools/en) | FAO | Free; FAO states the data is freely available | FAO FAMEWS |
| [PlantVillage Nuru](https://pmc.ncbi.nlm.nih.gov/articles/PMC7775399) and [kilimoAI datasets](https://icml.cc/virtual/2026/78313) | PlantVillage (Penn State) with FAO, IITA and CIMMYT; the kilimoAI team | Confirm before use | As their terms require |
| [CABI PlantwisePlus Knowledge Bank](https://blog.plantwise.org/2022/11/29/plantwiseplus-knowledge-bank-joins-the-cabi-digital-library/) | CABI | Free to read; reuse terms to be confirmed with CABI | Linked, not copied, unless CABI grants reuse |
| [WFP food prices on HDX HAPI](https://data.humdata.org/hapi) | World Food Programme, via OCHA's Humanitarian Data Exchange | HDX HAPI terms of use | WFP, via HDX |
| [FEWS NET Data Warehouse](https://help.fews.net/fde/fews-net-api) | FEWS NET | FEWS NET data use and attribution policy | As that policy requires |
| [WHO SMART Guidelines, antenatal care kit](https://www.who.int/publications/i/item/9789240020306) | World Health Organization | WHO publication terms | WHO, with the title of the kit |
| [Kenya Master Health Facility List](https://mfl-api-docs.readthedocs.io/) | Ministry of Health, Kenya | Ministry API terms | Kenya Ministry of Health, Master Facility List |
| [healthsites.io](https://www.digitalpublicgoods.net/r/global-healthsites-mapping-project) and OpenStreetMap | Global Healthsites Mapping Project and OpenStreetMap contributors | ODbL 1.0, kept in its own store | © OpenStreetMap contributors, healthsites.io, ODbL |
| [Public health facilities in sub-Saharan Africa](https://pmc.ncbi.nlm.nih.gov/articles/PMC6658526) | KEMRI-Wellcome Trust Research Programme | Dataset terms on figshare | The 2019 Scientific Data paper, doi:10.1038/s41597-019-0142-2 |
| [Community Health Toolkit](https://medic.org/wp-content/uploads/2025/04/Medic_2024_Annual_Report-Final.pdf) | Medic and contributors | AGPL 3.0; ACE integrates over its API and copies no code | Community Health Toolkit |
| [MedGemma](https://developers.google.com/health-ai-developer-foundations/medgemma) | Google | Health AI Developer Foundations terms of use | As those terms require |
| [Sunbird AI models](https://huggingface.co/sunbird) | Sunbird AI | Licence of each model | Sunbird AI and the model name |
| [N-ATLaS](https://techcabal.com/2025/09/25/nigerian-government-awarri-launch-n-atlas/) | Awarri with the Government of Nigeria | Licence of the model | As that licence requires |
| [Intron Sahara](https://techcabal.com/2026/03/05/intron-expands-sahara-to-57-languages/) | Intron | Provider terms | As those terms require |
| [Gemma 3n](https://developers.googleblog.com/introducing-gemma-3n-developer-guide/) | Google | Gemma terms of use | As those terms require |
| [GSMA Open Gateway SIM Swap](https://www.gsma.com/solutions-and-impact/gsma-open-gateway/gsma-open-gateway-api-descriptions/) and [Scam Signal](https://www.gsma.com/newsroom/?p=25403) | GSMA and participating operators | Operator or aggregator contracts | As those contracts require |

## Research and programmes that shaped the V2 design

The V2 design learned from the published work of the University of Chicago's Human-Centered Weather Forecasts Initiative, AIM for Scale, the Gates Foundation, Google Research Africa, Google DeepMind, TomorrowNow and KALRO, Medic, Jacaranda Health, Digital Green and Viamo. Each is cited where its work is used in [docs/v2](docs/v2/README.md). None of them has endorsed ACE.

## Adding a source

1. Give every new fact a `source`, a `source_url` and a `checked_on` date.
2. If the source comes from an organisation not listed here, add it to this file in the same pull request.
3. For a V2 connector, add `docs/connectors/<name>.md` with access, licence, refresh and fallback, and add or update its row in the table above.
4. Never add content whose terms forbid reuse. Link to it instead.
