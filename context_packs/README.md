# Context packs

Open packs live here under CC BY 4.0, one folder per country, plus `africa/` for packs that apply in every covered country. Verified tier packs never ship in this repository.

| Pack | Facts | Topic |
|:--|:-:|:--|
| [africa/maize-fall-armyworm.yaml](africa/maize-fall-armyworm.yaml) | 8 | Fall armyworm in maize, for the 29 sub-Saharan countries and Egypt (push-pull for KE, UG, TZ, RW) |
| [africa/maternal-danger-signs.yaml](africa/maternal-danger-signs.yaml) | 5 | Danger signs in pregnancy and after birth, for all 34 countries (safety critical) |
| [ke/maize-post-harvest.yaml](ke/maize-post-harvest.yaml) | 7 | Drying, storage and aflatoxin |
| [ke/mobile-money-safety.yaml](ke/mobile-money-safety.yaml) | 10 | Spotting and reporting M-PESA fraud |
| [ke/rainfall-seasons.yaml](ke/rainfall-seasons.yaml) | 2 | Long and short rains |
| [ke/emergency-contacts.yaml](ke/emergency-contacts.yaml) | 5 | Kenya emergency and helpline numbers used by the safety rail |
| [tz/emergency-contacts.yaml](tz/emergency-contacts.yaml) | 2 | Tanzania emergency and helpline numbers used by the safety rail |
| [ug/emergency-contacts.yaml](ug/emergency-contacts.yaml) | 3 | Uganda emergency and helpline numbers used by the safety rail |
| [rw/emergency-contacts.yaml](rw/emergency-contacts.yaml) | 3 | Rwanda emergency and helpline numbers used by the safety rail |
| [za/emergency-contacts.yaml](za/emergency-contacts.yaml) | 3 | South Africa emergency and helpline numbers used by the safety rail |
| [bw/emergency-contacts.yaml](bw/emergency-contacts.yaml) | 2 | Botswana emergency and helpline numbers used by the safety rail |
| [na/emergency-contacts.yaml](na/emergency-contacts.yaml) | 3 | Namibia emergency and helpline numbers used by the safety rail |
| [zw/emergency-contacts.yaml](zw/emergency-contacts.yaml) | 2 | Zimbabwe emergency and helpline numbers used by the safety rail |
| [ng/emergency-contacts.yaml](ng/emergency-contacts.yaml) | 2 | Nigeria emergency and helpline numbers used by the safety rail |
| [gh/emergency-contacts.yaml](gh/emergency-contacts.yaml) | 2 | Ghana emergency and helpline numbers used by the safety rail |
| [sn/emergency-contacts.yaml](sn/emergency-contacts.yaml) | 3 | Senegal emergency and helpline numbers used by the safety rail |
| [ci/emergency-contacts.yaml](ci/emergency-contacts.yaml) | 3 | Côte d'Ivoire emergency and helpline numbers used by the safety rail |
| [tg/emergency-contacts.yaml](tg/emergency-contacts.yaml) | 2 | Togo emergency and helpline numbers used by the safety rail |

Every fact is `sourced`: a maintainer compared it with the cited public source on the `checked_on` date. None is expert reviewed yet, and every Swahili, French, Portuguese, Arabic, Amharic, Afaan Oromo and Somali rendering awaits review by a fluent speaker. Both are open invitations: see [docs/good-first-issues.md](../docs/good-first-issues.md).

To add a pack, copy [_template.yaml](_template.yaml), follow [docs/context-packs.md](../docs/context-packs.md), run `ace packs validate`, and open a pull request with the context pack template.

## Packs for several countries

A pack in `africa/` lists the countries it serves in a pack level `countries` field. A single fact can narrow that with its own `scope.countries`. A safety critical fact that applies in many countries does not carry phone numbers. It names a `refer_queue` instead, and ACE adds the caller's own national numbers for that queue from their country's emergency pack.
