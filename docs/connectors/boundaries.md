# Connector: boundaries

**What it gives ACE.** The areas people name (county, state, region, district) for all 13 countries, so a person on a basic phone can say where they are. 346 areas in total.

**Access.** No key. geoBoundaries gbOpen first level areas are read from the geoBoundaries GitHub release (`media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/<ISO3>/ADM1/`). Uganda's 135 districts and Namibia's 14 regions come from OCHA COD-AB on HDX (`cod-ab-uga`, `cod-ab-nam`), because the geoBoundaries layers are four regions for Uganda and an outdated Natural Earth layer for Namibia.

**Licence.** Recorded per country in each places snapshot, from the source metadata: public domain (Kenya), CC BY 4.0 (Rwanda, Nigeria, Côte d'Ivoire), CC BY 3.0 IGO (South Africa, Zimbabwe, Senegal), CC BY-IGO (Uganda, Namibia), CC BY-SA 2.0 (Botswana, Ghana) and ODbL 1.0 (Tanzania and Togo, from OpenStreetMap, kept in `snapshots/odbl/`). Cite geoBoundaries as Runfola et al. (2020).

**Processing.** Shapes are simplified to about 300 metres. Each area keeps its official name, a few common names (Abuja for the Federal Capital Territory, Accra for Greater Accra, Kigali for the City of Kigali) and its centre.

**Refresh.** Yearly, or when a country changes its boundaries.

**Fallback.** None needed at run time: boundaries change rarely, and the last snapshot stays in use.
