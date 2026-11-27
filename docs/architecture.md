# Architecture

ACE is one pipeline behind many entry points. Channels and models will keep changing. The checked, local knowledge in the packs is what compounds.

## Request flow

```
inbound payload (USSD, SMS, RCS, voice, WhatsApp, API, MCP)
   |
   v
channel adapter        parse_inbound -> Message
   |
   v
Engine.handle
   1 identity          ProfileStore.record_inbound: salted HMAC key, language, location, channels
   2 language          message language, else the person's chosen language, else marker words among the
                       country's languages, else the closest character profile
   3 safety rail       EscalationPolicy.check -> verified numbers + HandoffSink, then stop
   4 commands          HELP, LANG, TIP, SCAM, SOURCES, MORE, STOP, FORGET
   5 unread language   a message plainly in a language ACE does not speak gets told so, with the
                       languages ACE reads in the caller's country (langid)
   6 Scam Shield       auto checks forwarded money messages with strong warning signs
   7 V2 services       ServiceHub: detect the decision, resolve the place, answer from snapshots
   8 retrieval         ContextStore.query: hard filters, then ranking, then topic coherence
   9 compose           ExtractiveComposer or GroundedGenerator, inside the channel budget
  10 safety numbers    safety critical facts always carry the numbers to call
   |
   v
Reply (text, kind, language, citations, escalation)  -> channel adapter render -> provider
```

Every stage is a small class with its own tests. The order is the design: nothing can delay or override an emergency, and nothing reaches a person unless it is grounded in a checked fact, a dated snapshot or is a fixed system message.

## V2 services, connectors and snapshots

```
connectors (ace refresh, scheduled)  ->  snapshots/<dataset>/<COUNTRY>.json  ->  services  ->  Reply
   the only network access               dated, checksummed, licence registered     read only
```

Services sit after Scam Shield and before retrieval. `detect()` recognises the decision from words in all 32 languages; the gazetteer resolves the place from a name, a position or the place named last time; the service answers from snapshots and packs inside the channel budget, or refuses and says who to ask. A service waiting for a place or details is remembered on the profile, so the next message completes it. Menus call `Engine.run_service`, which still runs the safety rail first and gives it the screen's context, so bleeding typed on the pregnancy screen is treated as a pregnancy emergency. The [services guide](services.md) has the decision rules and coverage, and [docs/connectors](connectors/README.md) has every source.

## Modules

| Module | Responsibility |
|:--|:--|
| `models.py` | `Message`, `Reply`, `ReplyKind`, `Citation`, `Channel`, `GeoPoint` |
| `countries.py` | The 34 covered countries, their dialling codes and languages |
| `i18n.py`, `locales/` | Languages added in files: templates, phrases and words per language, filled into the code at start up and checked for completeness |
| `encoding.py` | GSM-7 folding for Latin script and UCS-2 budgets for Arabic and Amharic |
| `text.py` | Folding (including Arabic normalisation and Ge'ez letter folding), tokenising, light stemming, stopwords, script and marker word language guess, phrase matching |
| `context/schema.py` | `ContextFact`, `GeoScope`, `Rendering`, `Contact`, `ReviewStatus` |
| `context/packs.py` | Loading and strict validation of pack files |
| `context/store.py` | Filters plus BM25 ranking over each fact's text, keywords and translations |
| `safety.py` | Phrase rules per queue in all 32 languages, contact lookup by country, emergency wording with the call verb where each language puts it |
| `scam.py` | Scam Shield signals, scoring and verdicts |
| `commands.py` | Keyword commands and fixed system texts |
| `langid/` | Character profiles of ACE's languages and of 49 it does not speak; reading a message with no marker word, and telling a language ACE does not speak |
| `router.py` | Channel budgets, extractive composer, grounded generator, OpenAI compatible provider |
| `identity.py` | Phone normalisation, pseudonymisation, profiles, deletion |
| `tips.py` | Community tip queue |
| `engine.py` | The pipeline |
| `channels/` | USSD app, SMS, RCS with SMS fallback, voice IVR, WhatsApp |
| `server.py` | WSGI server for every webhook, the JSON API and the site |
| `site.py`, `web/site/` | The public site: the /try phone, coverage, developers, status and about pages |
| `app.py` | `create_app()`: one factory that builds the engine, stores and senders from the environment and refuses unsafe production settings |
| `stores.py` | Firestore profiles with a 24 hour expiry, and escalation counts with no text |
| `snapshots/manifest.py` | Publishing checked snapshot sets, and swapping them in while the service runs |
| `ops/` | The monthly spending cap (a meter, the guard that acts on it, and the edge it can close) and the weekly model check, for a Google Cloud deployment |
| `mcp_server.py` | MCP tools for AI assistants |
| `cli.py` | The `ace` command |

## Retrieval

Retrieval has two stages, both transparent.

1. **Hard filters** decide what is allowed: review status (sourced or better by default), tier, expiry, country, county, altitude, distance, season, vertical and topic. A fact that fails a filter is never served, however relevant its words look.
2. **Ranking** orders what is left. BM25 relevance over the claim, short form, translations, keywords and subjects carries most of the weight. Keywords and subjects count extra, because they hold the words people actually type, including Swahili and Sheng. Local specificity, review depth, season match, language availability and fact kind add smaller boosts. When someone asks what to do, facts of kind `action` rank higher.

Two guards keep answers on point: results far weaker than the best match are dropped, and the final answer stays on the topic of the best fact unless another fact is nearly as relevant.

## Channel budgets

| Channel | Characters | Form | Facts |
|:--|--:|:--|--:|
| USSD | 150 | short | 1 |
| SMS | 450 (three GSM-7 segments) | short | 3 |
| RCS | 450, the SMS budget, so a fallback to SMS never cuts the reply | short | 3 |
| Voice, radio | 320 | short | 2 |
| WhatsApp | 1,200 | full | 3 |
| App, API, agent | 1,500 | full | 4 |

Budgets live in `EngineConfig.budgets` and can be changed per deployment. On USSD, SMS and RCS, Arabic and Amharic replies are budgeted for UCS-2, which carries fewer characters, so ACE scales their budget (80 characters a USSD screen, 67 per SMS segment in a long message) and composes the reply to fit. Latin script replies are folded into GSM-7 before they leave, so one stray accent does not switch a message to UCS-2.

## Language models

The default `ExtractiveComposer` renders checked facts verbatim. It cannot invent anything, costs nothing and answers inside a USSD timeout.

To make answers more conversational, wrap any model in `GroundedGenerator`:

```python
from ace_engine import Engine
from ace_engine.router import GroundedGenerator, OpenAICompatibleProvider

provider = OpenAICompatibleProvider(base_url="http://localhost:11434/v1", model="your-model")  # Ollama, vLLM, a hosted API
engine = Engine.from_packs("context_packs", composer=GroundedGenerator(provider, timeout_s=6))
```

The model sees only the retrieved facts, numbered, and must end every sentence with the number of the fact it used. ACE then checks the output: every sentence must cite a fact it was given, no new phone numbers may appear, and the length must fit. Any failure, timeout or error falls back to the extractive answer. For USSD, keep the extractive composer: some networks give the application only a few seconds per screen.

## MCP

`ace-mcp --packs context_packs` starts a stdio MCP server, which never assumes a country, with five core tools, `ask_ace`, `search_context`, `check_message`, `emergency_contacts` and `list_packs`, and, when snapshots are present, seven V2 tools: `rain_this_week`, `official_warnings`, `nearest_facility`, `market_prices`, `pregnancy_companion`, `pest_check` and `service_coverage`. The tools are plain functions built by `build_tools(engine)`, so they are tested without the MCP SDK. Install the SDK with `pip install "ace-engine[mcp]"`.

## Scaling and storage

The V1 stores are in memory and the USSD app is stateless (it replays the input path each request), so a single process serves a pilot and several processes can run behind a load balancer. For production, implement `ProfileStore` and `TipQueue` over a database; the method names are the interface. The context store can move to a search engine or vector index without changing callers.
