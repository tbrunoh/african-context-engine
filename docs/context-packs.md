# Context pack specification, version 0.1

A context pack is a versioned YAML or JSON file of context facts. The machine readable schema is [spec/context-pack.schema.json](../spec/context-pack.schema.json).

## Pack fields

| Field | Required | Notes |
|---|---|---|
| `spec_version` | yes | `"0.1"` |
| `id` | yes | Lowercase slug, unique across packs, for example `ke-maize-nyeri` |
| `title` | yes | Human readable name |
| `license` | yes | `CC-BY-4.0` for open tier packs |
| `tier` | no | `open` (default) or `verified` |
| `maintainers` | yes | People or organizations responsible for the pack |
| `description` | no | Scope and intended use |
| `facts` | yes | List of facts |

## Fact fields

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique within the pack. The engine prefixes it with the pack id |
| `claim` | yes | One practical statement, written for the person who will act on it |
| `topic` | yes | For example `pest`, `soil`, `market`, `planting`, `maternal`, `land` |
| `vertical` | yes | `agriculture`, `health`, `legal` or `finance` |
| `source` | yes | Where the claim comes from |
| `subjects` | no | Crops, livestock or conditions |
| `scope` | no | `countries` (ISO alpha-2), `admin_areas`, `center` with `radius_km`, `altitude_min_m`, `altitude_max_m` |
| `months` | no | 1 to 12. Empty means all year |
| `languages` | no | BCP 47 tags with a localized rendering |
| `review_status` | no | `draft` (default), `expert_reviewed`, `outcome_verified` |
| `reviewed_by` | if reviewed | Named reviewer |
| `expires` | no | ISO date after which the fact needs re-review |
| `safety_critical` | no | `true` makes every answer using it offer a human expert |

## Validation rules enforced by the loader

- Required fields present; fact ids unique within the pack.
- Reviewed facts name a reviewer.
- Months fall between 1 and 12.
- Open tier packs declare `CC-BY-4.0`.

## Writing good facts

- Scope as tightly as the evidence allows. A fact true at 2,100m may be wrong at 800m.
- One claim per fact. Split compound advice.
- Prefer actions a person can take today over background explanation.
