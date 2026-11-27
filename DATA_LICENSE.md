# Data licensing

ACE separates code from knowledge. The code is open. The knowledge comes in two tiers.

| | Open tier | Verified tier |
|---|---|---|
| What | Baseline context packs built from open government, research and community sources | Facts that passed expert review and outcome checks, refreshed by season and location |
| License | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Commercial license from an ACE Verified operator |
| Who can use it | Anyone, with attribution | Licensed partners: operators, banks, insurers, NGOs, AI assistants |
| Review status allowed | `draft`, `sourced`, `expert_reviewed`, `outcome_verified` | `expert_reviewed`, `outcome_verified` |
| Where it ships | In this repository under `context_packs/` | Never in this repository |

## Principles

- **Contributors are paid.** Experts and communities whose facts reach the verified tier share in its licensing revenue.
- **People own their data.** Session data is collected only with consent, can be deleted on request (`ProfileStore.forget`), and is used for outcome checks in aggregate. Deployments in Kenya must comply with the Data Protection Act, 2019, and equivalent laws elsewhere.
- **No personal data in packs.** Context facts describe places, seasons, crops, conditions and rules, never individuals.
- **Attribution travels with the fact.** Every fact carries its source and, once reviewed, its reviewer.

## Third party sources

The CC BY 4.0 licence on open packs covers ACE's own wording and compilation. The organisations whose published facts ACE restates keep their own rights and terms, and each one is credited in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md). From V2 on, data that ACE fetches from public sources keeps the licence its owner set: CC BY 4.0 sources are credited in every answer that uses them, ODbL data such as healthsites.io and OpenStreetMap stays in its own store, and sources under terms of use are used only as those terms allow. The [V2 data and model catalog](docs/v2/data-catalog.md) records the licence of each, every snapshot carries its own, and `snapshots/register.yaml` lists the terms of every source, among them CC BY 4.0, CC BY IGO, CC BY-SA 2.0, ODbL 1.0, public domain and the terms each warning authority sets.

## Language profiles

`src/ace_engine/langid/profiles.json` holds counts of three letter sequences, built by `benchmark/langid/build.py` from ACE's own text, the FLORES-200 dev split and translations of the Universal Declaration of Human Rights. It holds no sentence from any source. Because FLORES-200 is CC BY-SA 4.0, the file is shared under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), and anyone who changes and shares it shares it under the same licence. See [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

## Engine enforcement

The loader rejects open tier packs that do not declare `CC-BY-4.0`, and the store never returns verified tier facts unless the deployment sets `include_verified=True`, which licensed operators enable.
