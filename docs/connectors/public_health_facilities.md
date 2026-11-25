# Connector: public_health_facilities

**What it gives ACE.** Name, type, ownership, first level area and position of 84,060 public health facilities across the 29 sub-Saharan countries ACE covers. North Africa (Algeria, Egypt, Libya, Morocco and Tunisia) is outside the list, so `nearest_facility` names that gap there. It feeds `nearest_facility`.

**Source.** Maina J, Ouma PO, Macharia PM, Alegana VA, Mitto B, Fall IS, Noor AM, Snow RW, Okiro EA (2019). A spatial database of health facilities managed by the public health sector in sub Saharan Africa. Scientific Data 6: 134. https://doi.org/10.1038/s41597-019-0142-2. Assembled by the KEMRI-Wellcome Trust Research Programme from national master facility lists.

**Access.** No key. The spreadsheet on HDX (`health-facilities-in-sub-saharan-africa`), read with the standard library.

**Licence.** CC BY 4.0.

**Limits, stated in every answer.** Public facilities only. The list dates from 2019. It has no phone numbers, opening hours or services, so ACE never claims them; every answer ends with the country's verified medical emergency number, and never guesses one where no pack publishes it.

**Clean up.** The source saves accented letters in the wrong encoding (Santé reads Sant├⌐ in 3,359 names, nearly all in Côte d'Ivoire, Senegal and Togo) and title cases apostrophes (St. Mary'S). The connector repairs both and changes nothing else.

**Position check, added in 2.1.** 2,611 records sit in the wrong place, 2,217 of them at latitude 0, longitude 0. Any facility more than 25 km outside every area of its country, or more than 25 km from the first level area its own record names, is left out, so ACE never sends someone the wrong way. Areas split by a reform count as one when the record uses the old name. The names of dropped facilities are kept in each snapshot under `meta.dropped_positions` for review. Guinea-Bissau keeps only 8 facilities in the list.

**Refresh.** Quarterly, to pick up a new release.

**Fallback.** A cleared national registry replaces the list in its country: the connector for Malawi and Zambia is built and held until each ministry confirms reuse, see [national_facility_registry.md](national_facility_registry.md). The V2 design adds the Kenya Master Health Facility List and healthsites.io in its own ODbL store, to add private facilities and services.
