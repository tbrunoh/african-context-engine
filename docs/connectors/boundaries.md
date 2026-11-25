# Connector: boundaries

**What it gives ACE.** The areas people name (county, state, region, district) for all 34 countries, so a person on a basic phone can say where they are. 719 areas in total.

**Access.** No key. geoBoundaries gbOpen first level areas are read from the geoBoundaries GitHub release (`media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/<ISO3>/ADM1/`). Uganda's 135 districts and Namibia's 14 regions come from OCHA COD-AB on HDX (`cod-ab-uga`, `cod-ab-nam`), because the geoBoundaries layers are four regions for Uganda and an outdated Natural Earth layer for Namibia. The 21 countries added in 2.1 all use OCHA COD-AB, at the level people name: second level areas for Malawi (districts), Libya (districts) and Tunisia (governorates), first level areas everywhere else.

**Licence.** Recorded per country in each places snapshot, from the source metadata: public domain (Kenya), CC BY 4.0 (Rwanda, Nigeria, Côte d'Ivoire), CC BY 3.0 IGO (South Africa, Zimbabwe, Senegal), CC BY-IGO (Uganda, Namibia), CC BY-SA 2.0 (Botswana, Ghana) and ODbL 1.0 (Tanzania and Togo, from OpenStreetMap, kept in `snapshots/odbl/`). Every COD-AB layer is CC BY-IGO. Cite geoBoundaries as Runfola et al. (2020).

**Processing.** Shapes are simplified to about 300 metres. Each area keeps its official name, a few common names (Abuja for the Federal Capital Territory, Accra for Greater Accra, Kigali for the City of Kigali) and its centre.

**Clean up added in 2.1.** Names published in capitals are written in title case. The alternative names each COD-AB layer carries become aliases, as do common city names (Matadi for Kongo-Central, Mogadishu for Banadir). Areas a layer labels contested or disputed are left out. Official spellings that differ from the layer, such as accents, are set in one map and the source spelling still matches.

**Known limits.** Each layer is the newest the national office has endorsed. Burundi's five provinces of 2025 and Burkina Faso's 17 regions are in. Algeria (48 wilayas), Angola (18 provinces) and Morocco still show their earlier divisions, and Morocco's layer leaves out the territory of Western Sahara.

**Refresh.** Yearly, or when a country changes its boundaries.

**Fallback.** None needed at run time: boundaries change rarely, and the last snapshot stays in use.
