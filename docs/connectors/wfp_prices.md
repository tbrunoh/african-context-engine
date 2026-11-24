# Connector: wfp_prices

**What it gives ACE.** For every market WFP monitors, the last six monthly prices of each food, retail first. 1,092 markets across 12 countries. It feeds `market_prices`.

**Access.** No key. The HDX CKAN API (`data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-<country>`) gives the current CSV for each country.

**Licence.** CC BY-IGO. Credit: food prices from the World Food Programme, via HDX.

**Processing.** Non food items are left out. Where a market reports a food as both retail and wholesale, the retail series is kept.

**Refresh.** Weekly. WFP updates most countries monthly.

**Gaps.** Botswana has no WFP price dataset. South Africa's latest prices are from June 2022 and Ghana's from July 2023, so `market_prices` refuses to quote them. Prices older than four months are never quoted as current.

**Fallback.** Traders and the agriculture office, named in the refusal. The V2 design adds FEWS NET prices and outlooks.
