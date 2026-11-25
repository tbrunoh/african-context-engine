# Connector: cap

**What it gives ACE.** Official warnings in force from each country's alerting authority, in the authority's own words. It feeds `official_warnings`.

**Access.** No key. The feeds are the ones the WMO Register of Alerting Authorities lists (read on 24 November 2026), for 30 of the 34 countries: Kenya, Tanzania, Uganda, South Africa, Botswana, Zimbabwe, Nigeria, Ghana, Senegal, Côte d'Ivoire, Togo, DR Congo, Malawi, Burundi, Cameroon, Benin, Zambia, Chad, Guinea, Burkina Faso, South Sudan, Ethiopia, Mozambique, Guinea-Bissau, Somalia, Sudan, Algeria, Egypt, Libya and Tunisia. Rwanda, Namibia, Angola (INAMET) and Morocco (DGM) list no CAP feed. Where the register lists a mirror as well (Kenya), the register's own URL is tried first and the mirror is used only when it is newer.

**Processing.** RSS and Atom feeds are both read. ACE keeps only alerts with status Actual, scope Public and an expiry in the future, drops any alert a later message cancels or replaces, and keeps headline, instruction, severity, urgency, certainty, onset, expiry, area descriptions and simplified polygons. Where an alert carries text in several languages, ACE keeps English first, then French, Portuguese and Arabic.

**Matching an alert to a place.** Polygons decide first, with two exceptions added in 2.1. A polygon that is one point repeated, a line, or has no area is dropped. When every polygon covers 80% or more of the country's extent and the alert names areas, the names decide, because the outline is the country's and not the warning's; with no names, such an alert is national. An alert with no usable polygon is matched by the areas it names, and one that names only the country, or says nationwide, covers everyone.

**Licence.** Public warnings are published for redistribution to the public. ACE passes them on unchanged, credits the authority, and never rewrites the authority's text.

**Refresh.** Hourly for a deployment. A snapshot is valid for six hours. ACE says there is no warning only when it read the feed in that window; when only an out of date mirror answered, it says it cannot tell.

**Known gaps at release.** South Africa's feed returned an error at the last refresh, so ACE says it cannot check warnings there until it answers. Kenya's register URL is often unreachable and the mirror is used.

**Fallback.** The authority itself, named in every refusal: listen to the national met service on radio and TV.
