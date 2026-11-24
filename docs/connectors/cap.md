# Connector: cap

**What it gives ACE.** Official warnings in force from each country's alerting authority, in the authority's own words. It feeds `official_warnings`.

**Access.** No key. The feeds are the ones the WMO Register of Alerting Authorities lists (read on 24 November 2026): Kenya, Tanzania, Uganda, South Africa, Botswana, Zimbabwe, Nigeria, Ghana, Senegal, Côte d'Ivoire and Togo. Rwanda and Namibia list no CAP feed. Where the register lists a mirror as well (Kenya), the register's own URL is tried first and the mirror is used only when it is newer.

**Processing.** RSS and Atom feeds are both read. ACE keeps only alerts with status Actual, scope Public and an expiry in the future, drops any alert a later message cancels or replaces, and keeps headline, instruction, severity, urgency, certainty, onset, expiry, area descriptions and simplified polygons.

**Licence.** Public warnings are published for redistribution to the public. ACE passes them on unchanged, credits the authority, and never rewrites the authority's text.

**Refresh.** Hourly for a deployment. A snapshot is valid for six hours. ACE says there is no warning only when it read the feed in that window; when only an out of date mirror answered, it says it cannot tell.

**Fallback.** The authority itself, named in every refusal: listen to the national met service on radio and TV.
