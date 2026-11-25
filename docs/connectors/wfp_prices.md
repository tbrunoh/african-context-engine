# Connector: wfp_prices

**What it gives ACE.** For every market WFP monitors, the last six monthly prices of each food, retail first. 2,418 markets across 31 countries. It feeds `market_prices`.

**Access.** No key. The HDX CKAN API (`data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-<country>`) gives the current CSV for each country.

**Licence.** CC BY-IGO. Credit: food prices from the World Food Programme, via HDX.

**Processing.** Non food items are left out. Where a market reports a food as both retail and wholesale, the retail series is kept.

**Refresh.** Weekly. WFP updates most countries monthly.

**Gaps.** Botswana, Morocco and Tunisia have no WFP price dataset. The latest prices are too old to quote for South Africa (June 2022), Ghana (July 2023), Angola (December 2020), Somalia (November 2021), Namibia, Zimbabwe and Mozambique, so `market_prices` names the gap. Prices older than four months are never quoted as current. Algeria's dataset covers only the Sahrawi refugee camps near Tindouf, so ACE gives the distance to them.

**Too few foods to quote.** From 2.1 a country needs recent prices for at least two staple foods (maize, beans, rice, sorghum, millet, cassava, wheat, flour, yam, gari, plantain, teff and the like). Below that, as in Zambia at release, ACE says the prices cover too few foods instead of quoting one item as if it were the market.

**Fallback.** Traders and the agriculture office, named in the refusal. The V2 design adds FEWS NET prices and outlooks.
