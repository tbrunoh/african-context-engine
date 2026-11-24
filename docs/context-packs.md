# Context packs

A context pack is a YAML file of facts that ACE can stand behind. Packs are versioned in git, reviewed in pull requests and licensed CC BY 4.0, so any service, government or AI assistant can reuse them.

You do not need to write code to contribute a pack. You need to know a topic and a place, and to cite where each fact comes from.

## A fact, annotated

```yaml
- id: drying-moisture                 # lowercase letters, digits and dashes; unique in the pack
  claim: >-                           # the full fact, in plain words a person can act on
    Dry maize to about 13 percent moisture before storing it. KALRO advises that maize for food and
    animal feed should be at 13 to 13.5 percent moisture.
  short: "Dry maize to about 13% moisture before storage. KALRO advises 13 to 13.5% for food and feed."
                                      # at most 160 characters; used on USSD, SMS and voice
  topic: storage                      # groups facts for menus and follow ups
  vertical: agriculture               # agriculture, health, finance, safety, legal, education, climate
  kind: action                        # action (what to do), sign (how to recognise), or info
  subjects: [maize]                   # crops, conditions or services the fact is about
  keywords: [dry, moisture, kausha, unyevu, sumukuvu]   # the words people actually type, any language
  months: [7, 8, 9]                   # optional: only serve in these months
  scope:                              # optional: where it applies (country defaults to the pack's)
    admin_areas: [Nakuru, Uasin Gishu]
    altitude_min_m: 1500
  translations:
    sw:
      claim: Kausha mahindi hadi unyevu wa takriban asilimia 13 ...
      short: Kausha mahindi hadi unyevu wa asilimia 13 kabla ya kuhifadhi ...
      reviewed: false                 # set true only after a fluent speaker has checked it
  contacts:                           # optional: lines people can call, with the safety queues they serve
    - {label: Emergency, number: "999", queues: [emergency, health_urgent]}
  source: KALRO, Maize post harvest   # who published it
  source_url: https://www.kalro.org/maize/maize-post-harvest
  checked_on: 2026-11-23              # when a maintainer last compared the claim with the source
  review_status: sourced
  expires: 2027-11-23                 # optional: withheld after this date until re-checked
  safety_critical: false              # true if a wrong answer could cause harm; answers then carry numbers
  refer_queue: maternal               # optional, for packs in several countries: add the caller's own
                                      # national numbers for this safety queue instead of listing contacts
```

## Review status

| Status | Meaning | Required | Served by default |
|:--|:--|:--|:-:|
| `draft` | Submitted, not yet checked | source | no |
| `sourced` | A maintainer checked the claim against the cited public source | source_url, checked_on | yes |
| `expert_reviewed` | A named domain expert reviewed it for this place | plus reviewed_by | yes |
| `outcome_verified` | Measured outcomes from real deployments confirm it | plus reviewed_by | yes |

Never mark a fact `expert_reviewed` or `outcome_verified` unless you are the named reviewer or have their written agreement on the pull request.

## Rules the validator enforces

Run `ace packs validate` before you open a pull request. CI runs it too.

- Required pack fields: `spec_version` (1.0), `id`, `title`, `license`, `maintainers`, `facts`.
- Open packs use `CC-BY-4.0`. Only cite sources you are allowed to summarise.
- `sourced` and better need `source_url` and `checked_on`; expert levels also need `reviewed_by`.
- `short` forms are at most 160 characters in every language.
- Contact numbers are digits, optionally with a leading plus.
- Dates are ISO (`2026-11-23`); months are 1 to 12.

Warnings (not failures): translations not yet reviewed, facts last checked more than a year ago, expired facts, safety critical facts without contacts, and menu labels longer than 24 characters. See them all with `ace packs validate --strict`.

## Writing good facts

- **One fact, one action.** If a person can only remember one sentence, it should be this one.
- **Say it the way an extension officer would say it**, not the way a paper abstract would.
- **Stay inside the source.** Do not add advice the source does not give. If two sources disagree, open an issue.
- **No product brands, prices or doses** unless a licensed reviewer for that place adds them.
- **Keywords are where local knowledge lives.** Add the Swahili, Sheng and local names people actually use.
- **Health and safety facts are `safety_critical`** and should list the numbers to call, or name a `refer_queue` when the pack serves several countries.
- **Never borrow a number.** An emergency pack lists only numbers a public source publishes for that country. If two official sources disagree, leave the number out and open an issue.

## Packs for several countries

Guidance that holds across borders, such as WHO danger signs or FAO pest guidance, lives in `context_packs/africa/`. List the countries the pack serves in a pack level `countries: [KE, TZ, UG]` field instead of `country`. A fact can narrow that list with its own `scope.countries`. Safety critical facts in these packs carry no numbers of their own: they name a `refer_queue`, and ACE adds the caller's national numbers for that queue from their country's emergency pack. Give every fact a rendering in each language of every country it serves; the test suite checks this.

## Starting a new pack

1. Copy `context_packs/_template.yaml` into a folder for the country, for example `context_packs/ug/`.
2. Fill in the pack fields, including menu `labels` in each language and an `order`.
3. Add facts with sources. Start them as `draft` if you have not checked them against the source yourself.
4. Run `ace packs validate context_packs/ug` and `ace chat --country UG`. Without `--country`, ACE picks the country from the phone number.
5. Open a pull request using the context pack template.

The JSON schema for editors and other tools is in [spec/context-pack.schema.json](../spec/context-pack.schema.json).
