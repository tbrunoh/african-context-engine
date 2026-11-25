# Connector: national_facility_registry

**Status: built and held.** The connector is complete and tested, but it writes no snapshot until each ministry of health confirms in writing that ACE may reuse its registry. The licence register marks the source `cleared: false`, and `ace refresh` reports it as held. Until then, `nearest_facility` serves the 2019 list in Malawi and Zambia.

**What it would give ACE.** The ministry's own list of facilities, public and private, with positions and, where the registry holds a plausible one, a phone number. The facility finder prefers a cleared registry to the 2019 list, shows the phone number beside each facility, and says the list is from the ministry's registry.

**Sources.**
- Malawi Health Facility Registry, Ministry of Health: https://zipatala.health.gov.mw/. The API gives facilities, geolocations and contact people as three lists joined on the facility id.
- Zambia Health Facility Registry, Ministry of Health: https://zhfr.moh.gov.zm/. One CSV export with every field.

**Licence.** Neither registry states a licence. Publishing data openly is not the same as permitting reuse, so ACE waits for written confirmation.

**Processing.** Facilities without a position, archived or not operational are left out, as are template rows. Phone numbers are kept only when they have 9 to 13 digits and are not placeholders such as 1234567890 or a single repeated digit. The same position check as the 2019 list runs on every record.

**To clear it.** Record the ministry's written confirmation in `snapshots/register.yaml` (the licence and the attribution it asks for) and set `cleared: true`. The next `ace refresh` writes `snapshots/facilities_registry/MW.json` and `ZM.json`, and the facility finder starts using them at once.

**Refresh.** Monthly once cleared.

**Fallback.** The 2019 list of public facilities, see [public_health_facilities.md](public_health_facilities.md).
