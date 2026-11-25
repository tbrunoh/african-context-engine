# V2 decision services

Release 2.0 preview ships six decision services. Each answers one decision for one person, in one or two sentences, with a citation for every fact and the date of its data. When a service cannot answer safely it returns a refusal that says why and who to ask instead. The safety rail runs before every service, on every channel.

All six are a preview. They pass ACE's tests and benchmark, but none has yet passed the launch gate in the [build plan](v2/build-plan.md): expert panel review for farm and health answers, forecast skill against the season average for weather, and two fluent reviewers per language.

## How a question reaches a service

1. The safety rail, commands and Scam Shield run first, exactly as in V1.
2. The hub recognises the decision from words in English, Swahili or French: rain, warnings, a facility, prices, a pregnancy check or a crop problem. A question about the rainy seasons goes to the season packs instead.
3. The hub works out the place: an area named in the message, the position a channel shares, or the area the person named last time. When it needs a place and has none, it asks in the local word (county, state, region, district, kaunti, mkoa, wilaya) and remembers the question.
4. The service reads snapshots and packs, never the network, and answers inside the channel's character budget.

On USSD the services are items 1 to 6 of the main menu. Each asks one question (the area, the food, the weeks of pregnancy or the crop) and answers on the next screen.

## The services

| Service | Decision rule | Data | Refuses when |
|:--|:--|:--|:--|
| `rain_this_week` | Per day, the share of 51 ECMWF ensemble runs with at least 1 mm: likely from 6 in 10, possible from 3 in 10, otherwise mostly dry. Heavy rain (20 mm or more) is mentioned from 3 in 10 | ECMWF IFS ensemble, open data, via Open-Meteo, for the centre of each area | The forecast is more than 36 hours old |
| `official_warnings` | Any actual, public, unexpired CAP alert whose polygon contains the area's centre, whose area description names the area, or that covers the whole country. The authority's headline and instruction are passed on unchanged | CAP feeds listed in the WMO Register of Alerting Authorities | The feed was not read in the last six hours, or only an out of date mirror answered. ACE then says it cannot tell, and never says there is no warning |
| `nearest_facility` | With a position: the three nearest public facilities within 60 km, plus the nearest hospital. With an area: the public hospitals inside it | Maina et al. (2019), public health facilities in sub-Saharan Africa | No facility within 60 km. Every answer ends with the country's medical emergency number from the packs, or the instruction to call the local emergency number where no pack publishes one (Togo), and says the list dates from 2019 |
| `market_prices` | The nearest market with a price for the food in the last four months, with the change on the previous month. Without a food, the staples in the nearest market | WFP Price Database, via HDX | The latest price is more than four months old, or WFP publishes no prices for the country |
| `pregnancy_companion` | WHO's eight contact schedule: by 12 weeks, then 20, 26, 30, 34, 36, 38 and 40. Always adds the signs that mean go now and the country's numbers | WHO 2016 antenatal care recommendations; WHO danger signs pack | Never. Without the weeks, it asks for them and still gives the danger signs |
| `pest_check` | The crop (maize, cassava, banana, tomato) and the words the farmer uses pick the likely problem. The answer gives the signs to check, the first step and a referral to an extension officer before any spraying | Sourced pack facts from FAO, CIMMYT, CABI Plantwise, Bioversity International, IITA and the World Vegetable Center | The crop is not one of the four. It names no pesticide product or rate |

## Coverage and gaps

Every service covers all 13 countries by default. Where open data does not exist, the service says so in the person's language and names who to ask. `ace services` prints the live table with the reason for every gap. At release:

| Service | Gaps |
|:--|:--|
| Official warnings | Rwanda and Namibia list no CAP feed in the WMO register. A feed that is down at a refresh is reported as a gap until it answers again |
| Market prices | Botswana has no WFP price dataset. South Africa (June 2022), Ghana (July 2023), Namibia (June 2026) and Zimbabwe (May 2026) have no price recent enough to quote |
| Nearest health facility | Public facilities only, from a 2019 list, with no phone numbers, hours or services |
| Crop problem check | Four crops so far |

## Calling a service

From the web server:

```bash
curl -s localhost:8000/v1/services | jq '.services[] | {id, coverage: .coverage.NG}'
curl -s -X POST localhost:8000/v1/services/market_prices \
  -d '{"country": "SN", "place": "Dakar", "food": "rice", "language": "fr"}'
```

From any MCP client: `rain_this_week`, `official_warnings`, `nearest_facility`, `market_prices`, `pregnancy_companion`, `pest_check` and `service_coverage`. Every result carries `outcome` (answer, needs_place, gap, stale or no_match), `preview`, `citations` with source, licence and date, and the structured `data` behind the text.

From Python:

```python
from ace_engine import Engine
engine = Engine.from_packs("context_packs")          # snapshots load from ./snapshots
print(engine.services.call("rain_this_week", "TZ", "Mwanza", language="sw")["text"])
```

## Adding a service

Follow the definition of done in the [build plan](v2/build-plan.md#definition-of-done-for-any-new-service): one named decision, a citation for every fact, an open fallback and a refusal path, tests in English, Swahili and French, a benchmark check, and exposure on USSD, SMS, the API and MCP. Services live in `src/ace_engine/services/`, one module each, and register in `services/__init__.py`.
