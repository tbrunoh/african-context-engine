# Connector: open_meteo

**What it gives ACE.** For the centre of every area in every country, the 7 day ECMWF IFS ensemble rainfall: per day, the chance of at least 1 mm, the median amount and the chance of at least 20 mm. It feeds `rain_this_week`.

**Access.** No key. `https://ensemble-api.open-meteo.com/v1/ensemble` with `models=ecmwf_ifs025`, up to 40 locations per call, about 18 calls for the 719 area centres in all 34 countries.

**Licence and terms.** ECMWF open data is CC BY 4.0. Open-Meteo serves it under CC BY 4.0 and its free API is for non-commercial use, under 10,000 calls a day, with attribution: Weather data by Open-Meteo.com. A commercial deployment needs an Open-Meteo subscription or its own pipeline from ECMWF open data.

**Refresh.** Twice a day. A snapshot is valid for 36 hours; after that `rain_this_week` refuses and points to the national met service.

**Fallback.** The national met service forecast, named in the refusal. The V2 design adds WeatherNext and TomorrowNow GAP when access is granted, and a forecast skill benchmark against the season average before any weather service leaves preview.
