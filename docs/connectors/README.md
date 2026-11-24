# Connectors

Connectors are the only code in ACE that touches the network. Each fetches one public source for one country and writes a dated, checksummed snapshot to `snapshots/<dataset>/<COUNTRY>.json`. Services read the snapshots and never the network. Every source is listed with its licence in [`snapshots/register.yaml`](../../snapshots/register.yaml), and ODbL data lives in its own store, `snapshots/odbl/`.

| Connector | Dataset | Source | Licence | Refresh | Page |
|:--|:--|:--|:--|:--|:--|
| `boundaries` | places | geoBoundaries; OCHA COD-AB for Uganda and Namibia | Varies by country | Yearly | [boundaries.md](boundaries.md) |
| `open_meteo` | weather | ECMWF IFS ensemble, open data, via Open-Meteo | CC BY 4.0 | Twice a day | [open_meteo.md](open_meteo.md) |
| `cap` | warnings | National CAP feeds from the WMO register | Official public warnings | Hourly | [cap.md](cap.md) |
| `wfp_prices` | prices | WFP Price Database, via HDX | CC BY-IGO | Weekly | [wfp_prices.md](wfp_prices.md) |
| `public_health_facilities` | facilities | Maina et al. 2019, via HDX | CC BY 4.0 | Quarterly | [public_health_facilities.md](public_health_facilities.md) |

```bash
ace refresh                               # every connector, every country
ace refresh --source cap --country GH     # one source, one country
```

A failed fetch leaves the last good snapshot in place, and each service judges freshness itself. The repository's `refresh` workflow updates the demo snapshots daily. A deployment runs `ace refresh` on its own schedule.

To add a connector, implement the contract in `src/ace_engine/connectors/base.py`, register it in `connectors/__init__.py`, add its source to the licence register and to [ACKNOWLEDGMENTS.md](../../ACKNOWLEDGMENTS.md), write a page here with access, licence, refresh and fallback, and add offline parser tests.
