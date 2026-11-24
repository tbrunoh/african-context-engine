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

## Engine enforcement

The loader rejects open tier packs that do not declare `CC-BY-4.0`, and the store never returns verified tier facts unless the deployment sets `include_verified=True`, which licensed operators enable.
