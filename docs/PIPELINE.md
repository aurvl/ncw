# NCW pipeline: data path and equations

This document explains the calculation path from biophysical data to national indicators. It defines the variables, units and successive transformations. Dates describe the available observations; annual flows are calculated from these sources and are not measurements taken simultaneously.

## 1. Notation and units

| Symbol | Definition | Unit |
|---|---|---|
| $i$ | Entity in the account (country or territory) | - |
| $b$ | Tropical, subtropical, temperate or boreal biome | Category |
| $e$ | Mangrove, seagrass or saltmarsh | Coastal ecosystem |
| $d$ | Shared draw of the global social cost of carbon | $d=1,\ldots,20\,000$ |
| $j$ | Geographic row in the published marine account | - |
| $A$ | Area | ha or km$^2$, depending on context |
| $A_{i,\mathrm{mang}}^{\mathrm{Hilmi\,2026}}$ | Mangrove area reported by Hilmi et al. (2026), used only as the last fallback | ha |
| $A_{i,e}$ | Area of coastal ecosystem $e$ assigned to entity $i$ | km$^2$ |
| $w_p$ | Actual area of pixel $p$, used as its weight in the spatial mean | ha |
| $r_b$ | Mean gross addition to living forest biomass in biome $b$ | tC ha$^{-1}$ yr$^{-1}$ |
| $R_{e,d}$ | Marine rate for ecosystem $e$ in draw $d$ | tC km$^{-2}$ yr$^{-1}$ |
| $S_{i,d}^{\mathrm{coast}}$ | Annual carbon flux from mangroves, seagrasses and saltmarshes | tC yr$^{-1}$ |
| $S_i^{BCP}$ | Annual carbon flux from the oceanic biological carbon pump | tC yr$^{-1}$ |
| $S_{i,d}^{\mathrm{blue}}$ | Total annual blue flux after conversion to CO$_2$, including BCP | tCO$_2$ yr$^{-1}$ |
| $GSCC_d$ | Draw $d$ of the global social cost of carbon | USD 2015 tCO$_2^{-1}$ |
| $P_p^X$ | Percentile of order $p$ of simulated quantity $X$ | Same unit as $X$ |
| $U_i$ | Estimated annual gross forest addition | tCO$_2$ yr$^{-1}$ |
| $A_{ib}$, $A_i^{total}$ | Forest area used in GCW for biome $b$, and the total across the four biomes | ha |
| $\bar u_i^{GCW}$ | Entity-level mean annual forest-addition rate, $U_i/A_i^{total}$ | tCO$_2$ ha$^{-1}$ yr$^{-1}$ |
| $GDP_i^*$, $Pop_i^*$ | Latest reported GDP or population value among 2024, 2023 and 2022 | USD 2015/yr; persons |
| $T_i$, $D_{i,t}^{FRA}$ | Available FRA periods and reported mean annual loss rate for period $t$ | Period; thousand ha/yr |
| $t_i^{sel}$ | Most recent reported FRA period selected for entity $i$ | Period |
| $D_i$ | FRA mean annual deforestation rate for $t_i^{sel}$ | ha/yr |
| $\Delta t$, $A_i^{loss}$ | Duration considered and area deforested during that duration, $A_i^{loss}=D_i\Delta t$ | yr; ha |
| $\widehat L_i$ | Annual forest-addition capacity associated with the area deforested during one year | tCO$_2$ yr$^{-1}$ |
| $\widehat V_{i,d}$ | Monetary value of that capacity at GSCC draw $d$ | USD 2015 yr$^{-1}$ |
| $E_i$ | Territorial fossil and industrial emissions | tCO$_2$/yr |
| $GCW_{i,d}, BCW_{i,d}, N_{i,d}$ | Monetary values of the GCW, BCW and NCW accounts | USD 2015 yr$^{-1}$ |

The conversions are $1\ \mathrm{km}^2=100\ \mathrm{ha}$ and $1\ \mathrm{tC}=44/12\ \mathrm{tCO_2}$. Multiplying an area by an annual rate per unit area gives an annual flow. Multiplying that flow by the GSCC draw, denoted $GSCC_d$, gives a monetary value. The symbol $P_p^X$ denotes a percentile; it is not a GSCC draw.

The variables in the account do not all come from the same year. The table summarizes their periods and selection rules:

| Data | Source and period | Rule used |
|---|---|---|
| Forest area | FRA 2025 | Area reported for 2025 |
| Mangrove area | GMW 2025, FRA 2025, Hilmi et al. (2026) | Priority: GMW 2025, then FRA 2025, then Hilmi et al. (2026) |
| Gibbs/GFW forest rate | 2001-2023 | Rate calculated over this period |
| Territorial emissions used for comparison | 2024 | 2024 value |
| GDP and population | 2024, 2023 or 2022 | First reported value in that order, separately for each variable and entity |
| Annual forest-area loss | FRA, periods 2010-2015, 2015-2020 and 2020-2025 | For each entity, use the reported rate from the latest available period: 2020-2025, then 2015-2020, then 2010-2015 |
| Marine rates and GSCC draws | BCW version used as the reference | Values taken from that version |

The account therefore combines data observed or calculated over different periods; each variable retains the period specified by its source.

## 2. Annual rates by biome (Gibbs/GFW)

The calculation starts with two spatial datasets covering 2001-2023: gross forest carbon removals and a mask distinguishing cover types. They are downloaded and processed together. Mangrove pixels are excluded from the terrestrial forest-rate calculation so that the terrestrial rate is not assigned to mangroves, whose flux is handled separately in the marine account.

For each valid pixel $p$, $x_p$ is a modelled estimate of cumulative gross removals between 2001 and 2023, in MgCO$_2$/ha. Earth-observation data do not directly measure this carbon flux; they provide the model with forest-activity data for each pixel of approximately 30 m. In the gain-loss approach of Gibbs et al. (2025), activity is combined with a removal factor (schematically: forest activity × removal factor). These factors include IPCC defaults and localized factors derived, among other sources, from inventories and field observations. The removal raster contains the modelled result of this operation for each cell. The estimated removals concern aboveground and belowground forest biomass. Thus, the numerical value $x_p$ is produced by the model; it is not calculated from a direct satellite measurement of carbon. Since one Mg equals one tonne, the annual carbon rate is:

$$
r_p=x_p\frac{12}{44}\frac{1}{23}
\qquad [\mathrm{tC\ ha^{-1}\ yr^{-1}}].
$$

Each pixel is assigned to one of the four FAO GEZ bioclimatic domains. The mask defines indicator $m_p$: $m_p=1$ if the pixel is classified as mangrove (code 6 in this mask), and $m_p=0$ otherwise. The sums below therefore include only non-mangrove pixels.

The weight $w_p$ is the actual pixel area in hectares. The geographic grid has a step of approximately $0.00025^\circ$, which near the equator is about 28 m north-south by 28 m east-west, or about 0.077 ha. Pixel area is not fixed at $30\times30$ m: east-west width and area decrease with latitude. For the pixel's northern and southern latitude boundaries $\varphi_N$ and $\varphi_S$, spherical area is:

$$
w_p=\frac{R_\oplus^2\,\Delta\lambda\,[\sin(\varphi_N)-\sin(\varphi_S)]}{10\,000}\quad[\mathrm{ha}],
$$

where $R_\oplus=6\,371\,008.8$ m and $\Delta\lambda$ is pixel width in longitude, in radians. The mean rate for a biome is calculated as the mean of pixel rates weighted by their areas $w_p$. Missing pixels are omitted, and negative values present in the source remain in the calculation:

$$
\bar r_b=\frac{\sum_{p\in b,\,m_p=0}w_pr_p}{\sum_{p\in b,\,m_p=0}w_p},
\qquad
\sigma_{b,\mathrm{spatial}}=\sqrt{\frac{\sum_{p\in b,\,m_p=0}w_p(r_p-\bar r_b)^2}{\sum_{p\in b,\,m_p=0}w_p}}.
$$

$\sigma_{b,\mathrm{spatial}}$ is the area-weighted spatial standard deviation of pixel rates within biome $b$. It describes how much modelled rates $r_p$ vary from one pixel to another. It is not the standard error of the mean $\bar r_b$, annual variation in removals, or the full uncertainty of the Gibbs/GFW model. The scenarios $\bar r_b\pm\sigma_{b,\mathrm{spatial}}$ used below are therefore sensitivities to spatial dispersion, not confidence intervals.

The source datasets and mask are combined pixel by pixel, converted to annual rates, classified by biome and aggregated by area. The complete processing path starts from 272 Gibbs/GFW removal tiles and their 272 matching WRI forest-type tiles (about 37 GB for the removal data). Area-weighted sums are calculated for each biome and tile, then tile summaries are combined into a four-row CSV, one row per biome, with the mean rate, $\sigma_{b,\mathrm{spatial}}$, area and quality-control fields. The resulting `data/outputs/gibbs_gfw/gfw_gibbs_biome_rates_non_mangrove.csv` is then used in the national calculation; the tile-by-biome audit table is stored beside it. For a cache-based run, this validated rate table is reused without downloading or aggregating the raw tiles again.

| Biome $b$ | Mean annual rate $\bar r_b$ (tC ha$^{-1}$ yr$^{-1}$) | $\sigma_{b,\mathrm{spatial}}$ (tC ha$^{-1}$ yr$^{-1}$) |
|---|---:|---:|
| Tropical | 0.9343985914 | 0.9269693002 |
| Subtropical | 1.3707381135 | 1.3227353783 |
| Temperate | 1.4300688032 | 0.8013244813 |
| Boreal | 0.6186330269 | 0.2612148756 |

$\sigma_{b,\mathrm{spatial}}$ describes spatial dispersion among pixels; it is not the standard error of a global estimate.

## 3. From FRA area to the forest GCW account

For each entity $i$, $F_i^{\mathrm{declared}}$ is the FRA area reported as Forest, in hectares. For shorter equations, write $F_i=F_i^{\mathrm{declared}}$. $M_i^{FRA}$ is the FRA area reported as mangroves. Depending on national classification, mangroves can be classified as Forest or Other wooded land (OWL); their total area is therefore not necessarily included in $F_i$.

Not all reports provide a numerical breakdown of mangrove area between Forest, OWL and other classes. In some cases, the detailed class is unknown even though total mangrove area is available. The audit covers 116 entities with a positive FRA value; a Forest allocation is applied in 26 cases. Brazil reports an area under Forest, Mozambique allocates its mangrove area between Forest (80%) and OWL (20%), and Saint Lucia classifies it as OWL. In total, 4,180,910 ha are documented in the Forest category; the Forest/OWL breakdown has not been verified for 11,613,440 ha.

Let $O_i^F$, $O_i^{OWL}$ and $O_i^R$ be areas documented as Forest, OWL and Remaining land, respectively, and let $O_i^?$ be the share without an established breakdown. The working decomposition is:

$$
M_i^{FRA}=O_i^F+O_i^{OWL}+O_i^R+O_i^?.
$$

The biome shares $s_{ib}$ sum to 1. They first come from the FRA climate breakdown (FRA 2025). When that breakdown cannot be used, the shares are estimated by intersecting GEZ domains (FAO GEZ 2010) with JRC forest cover (JRC Global Forest Cover 2020); if no usable forest-cover data are observed, terrestrial GEZ area (FAO GEZ 2010) is used instead. The reported area $F_i$ is first distributed across biomes. The mangrove area documented as already included in Forest, $O_i^F$, is then subtracted once from the tropical share (mangroves are treated as tropical for this FRA allocation):

$$
A_{ib}=F_i s_{ib}-{\bf1}_{b=\mathrm{tropical}}O_i^F,
\qquad \sum_b A_{ib}=F_i-O_i^F.
$$

The total forest area allocated after this correction is $A_i^{\mathrm{total}}=\sum_b A_{ib}=F_i-O_i^F$. It is the result of this correction, not an additional area to subtract in the formula.

GMW maps the location of mangroves, but does not by itself reveal the FRA class reported in a national report. For the $11\,613\,440$ ha without an established Forest/OWL breakdown, the main account therefore subtracts nothing. To measure the maximum possible effect, a separate upper-bound scenario assumes that all of the unknown area $O_i^?$ is actually included in Forest; it is then subtracted from the tropical share in addition to the area documented as $O_i^F$. Under this assumption alone, the additional reduction in forest additions is $38.69$ MtCO$_2$/yr, or $0.262\%$ of the account's global forest additions. If this assumption is combined with the removal already applied to the $4\,180\,910$ ha documented as Forest, the total reduction relative to a scenario with no overlap removed is about $53.02$ MtCO$_2$/yr, or $0.359\%$ of the uncorrected forest flow. This full assumption is a sensitivity representing a limiting case, not an observed reallocation.

For each entity, physical forest additions are calculated by multiplying hectares by the annual rates for each biome, then converting carbon to CO$_2$:

$$
U_i^C=\sum_b A_{ib}\bar r_b\quad[\mathrm{tC/yr}],
\qquad U_i=\frac{44}{12}U_i^C\quad[\mathrm{tCO_2/yr}].
$$

The GCW value in draw $d$ is:

$$
GCW_{i,d}=U_i\,GSCC_d\quad[\mathrm{USD\ 2015/yr}].
$$

Areas and the four rates remain fixed from one draw to another; the variation in value comes mainly from the shared GSCC draw $d$. The variants $r_b^-=\max(0,\bar r_b-\sigma_{b,\mathrm{spatial}})$ and $r_b^+=\bar r_b+\sigma_{b,\mathrm{spatial}}$ show the effect of shifting each rate by one spatial standard deviation. These are deterministic scenarios, not confidence bounds.

**Example for Brazil.** The reported Forest area is $F_{BRA}=486\,086\,640$ ha. The tropical and subtropical shares are 0.979 and 0.021; $O_{BRA}^F=1\,394\,680$ ha. After subtracting mangroves classified as Forest, $A_{trop}=474\,484\,140.56$ ha and $A_{subtrop}=10\,207\,819.44$ ha. The biome rates first give the carbon flow added to living biomass:

$$
U_{BRA}^{C}\simeq474\,484\,140.56\times0.9343985914+
10\,207\,819.44\times1.3707381135
=457\,349\,559.74\ \mathrm{tC/yr}.
$$

This flow is then converted to tonnes of CO$_2$:

$$
U_{BRA}=\frac{44}{12}U_{BRA}^{C}
=1\,676\,948\,385.69\ \mathrm{tCO_2/yr}.
$$

Finally, monetary value is calculated separately for each social-cost-of-carbon draw:

$$
GCW_{BRA,d}=U_{BRA}\,GSCC_d
$$

$$
GCW_{BRA}=938\,374\,837\,901.72
\pm450\,418\,996\,844.68\ \mathrm{USD\ 2015/yr}
\simeq(938.375\pm450.419)\ \text{billion USD 2015/yr}.
$$

## 4. Updating the BCW account: marine ecosystem areas

The mangrove area reported by Hilmi et al. (2026) is updated before BCW is calculated. In the equations below, $A_{i,\mathrm{mang}}^{\mathrm{sel}}$ denotes the area retained for entity $i$ after this update; “sel” means “selected.” The selection procedure, its sources and the treatment of missing values are described in the subsection “Selecting the mangrove area.”

The BCW account of Hilmi et al. (2026) combines coastal fluxes from mangroves, seagrasses and saltmarshes with the oceanic flux from the biological carbon pump (BCP). For entity $i$ and shared draw $d$, the coastal carbon flux is:

$$
S_{i,d}^{\mathrm{coast}}=
\frac{A_{i,\mathrm{mang}}^{\mathrm{sel}}}{100}R_{\mathrm{mang},d}
+A_{i,\mathrm{seag}}^{\mathrm{Hilmi\,2026}}R_{\mathrm{seag},d}
+A_{i,\mathrm{salt}}^{\mathrm{Hilmi\,2026}}R_{\mathrm{salt},d}
\quad[\mathrm{tC/yr}].
$$

The rates $R_{e,d}$ are in tC/km$^2$/yr. Seagrass and saltmarsh areas reported by Hilmi et al. (2026) are in km$^2$. The selected mangrove area is in hectares; dividing it by 100 in the equation converts it to km$^2$. The biological carbon-pump flux $S_i^{BCP}$ is the value reported by Hilmi et al. (2026), in tC/yr. The total valued blue flux is therefore:

$$
S_{i,d}^{\mathrm{blue}}=\frac{44}{12}\left(S_{i,d}^{\mathrm{coast}}+S_i^{BCP}\right)
\quad[\mathrm{tCO_2/yr}],
\qquad
BCW_{i,d}=S_{i,d}^{\mathrm{blue}}\,GSCC_d
\quad[\mathrm{USD\ 2015/yr}].
$$

Here, $S_{i,d}^{\mathrm{blue}}$ includes fluxes from the three coastal ecosystems and the BCP reported by Hilmi et al. (2026); $GSCC_d$ is the global social cost of carbon in draw $d$, in USD 2015/tCO$_2$.

### Mangrove area assigned by spatial intersection

The 2025 GMW mangrove area is obtained by intersecting the 2025 mangrove layer with the 2024 EEZ polygons associated with the entities studied. All mangrove polygons present in the 2025 layer are used. Let $E_u$ be the dissolved EEZ geometry for entity $u$, and $G_k$ be GMW polygon $k$. After reprojection to Mollweide (ESRI:54009), the raw area in hectares is:

$$
A_u^{GMW,raw}=\frac{1}{10\,000}\operatorname{Area}_{54009}\!\left(E_u\cap\bigcup_{k\in\mathcal K_{2025}}G_k\right)\quad[\mathrm{ha}].
$$

GMW applies a global correction factor of $0.9775$ to its area estimates. We apply it to the area of each intersection:

$$
A_u^{GMW,corr}=0.9775\,A_u^{GMW,raw}.
$$

For each entity $i$, $\mathcal U_i$ is the set of EEZ geometries of type “Union EEZ and country” associated with it. The raw and corrected areas assigned to the entity are:

$$
A_i^{GMW,raw}=\sum_{u\in\mathcal U_i}A_u^{GMW,raw},\qquad
A_i^{GMW,corr}=\sum_{u\in\mathcal U_i}A_u^{GMW,corr}=0.9775\,A_i^{GMW,raw}.
$$

The EEZ intersection determines which entity receives each area; GMW country code cntry_iso3 is used to describe the polygon's provenance.

### Selecting the mangrove area

For each entity $i$, the selected mangrove area follows this hierarchy: first, a positive area from the corrected GMW 2025 intersection; next, the value actually reported in FRA 2025, including zero; and then the area reported by Hilmi et al. (2026), if available. A blank FRA cell means “no value reported,” not zero. A value of zero is retained only when FRA explicitly reports zero. In the FRA 2025 extraction used here, 110 values are reported zeros, 116 are positive and 10 cells are blank; the FRA platform and reports distinguish numerical values from missing entries ([FRA platform](https://fra-data.fao.org/), [data download](https://fra-data.fao.org/api/export/bulk-download/)).

If neither GMW 2025 nor FRA 2025 provides an area for an entity, the area reported by Hilmi et al. (2026) is used. If Hilmi et al. (2026) also report no area, then $A_{i,\mathrm{mang}}^{\mathrm{sel}}=\mathrm{NaN}$: the area is unknown, not zero. Thus, a missing value in Hilmi et al. (2026) remains missing when the two more recent sources provide no area. Any retained area can be used to calculate the mangrove component; when Hilmi et al. (2026) do not publish a BCW account for that entity, the account is calculated from the selected area and the reported marine components. If no area is available, a published Hilmi BCW account is retained without recalculation.

The reference area reported by Hilmi et al. (2026) is denoted $A_{i,\mathrm{mang}}^{\mathrm{Hilmi\,2026}}$. It is used only as the last fallback. For example, the hierarchy selects $A_{BRA,\mathrm{mang}}^{\mathrm{sel}}=1\,083\,926.377$ ha directly from the corrected GMW 2025 layer for Brazil; the area reported by Hilmi et al. (2026) is $A_{BRA,\mathrm{mang}}^{\mathrm{Hilmi\,2026}}=1\,137\,555.043$ ha.

For any entity with a selected mangrove area, that area replaces the area reported by Hilmi when one is available. Seagrass and saltmarsh areas, their rates, the reported BCP flux and the shared draw $GSCC_d$ complete the BCW calculation. A missing marine component does not contribute numerically to the sum, which is arithmetically equivalent to zero; its NaN value remains in the source row. When multiple BCW rows are aggregated for one entity, reported values are added and coverage columns show how many source rows supplied each component. If no source row reports a component, its aggregated value remains NaN. An indicator distinguishes calculations for which all components are available.

The counts and amounts below describe tables saved on 28 October 2026, before the calculation of a BCW account was added for entities with a mangrove area but no published Hilmi account. They therefore do not represent results from the rule now described and will need to be updated in the final regeneration.

Hilmi et al. (2026) report a mangrove area for 119 of the 266 entities; no area is reported for the other 147. After applying the selection rule above, an area is available for 236 entities and remains NaN for 30. The sources of the 236 selected areas are:

| Selected source | Entities | Selected area |
|---|---:|---:|
| GMW 2025, corrected intersection | 126 | 14,815,223.7 ha |
| FRA 2025, value actually reported | 109 | 2,660 ha (3 positive values, 106 reported zeros) |
| Area reported by Hilmi et al. (2026), last fallback | 1 | 62.4 ha |
| No source available | 30 | NaN |

Among the 119 entities for which Hilmi et al. (2026) already reported an area, 118 now receive a different area; one retains the area reported by Hilmi et al. (2026) as the last fallback. For 117 entities, an area is now available although Hilmi et al. (2026) reported none. On a comparable basis, the sum of areas decreases from 11,187,925 ha to 11,104,147 ha, a change of -83,778 ha (-0.75%). The 3,713,799 ha for the 117 newly covered entities expand coverage; their inclusion explains why the total available area is not a like-for-like comparison.
Hilmi et al. (2026) publish a BCW account for 180 entities. Of these, 178 now have a selected area and their BCW flux is recalculated: 118 with an area that replaces one reported by Hilmi et al. (2026), 59 with a newly available area and one retaining the area reported by Hilmi et al. (2026). The two BCW accounts for which the area remains NaN retain their published values without recalculation. The remaining 58 entities have a selected area but are not among the BCW accounts published by Hilmi et al. (2026); they are therefore not included in this BCW update.

The global BCW total covers the same 180 accounts before and after the update. Statistics across the 20,000 shared draws are:

| Global BCW statistic | Area reported by Hilmi et al. (2026) | After update | Change |
|---|---:|---:|---:|
| Mean (billion USD 2015/yr) | 2,315.580 | 2,329.303 | +13.722 (+0.593%) |
| P05 (billion USD 2015/yr) | 904.682 | 909.096 | +4.414 |
| Median (billion USD 2015/yr) | 2,101.732 | 2,113.411 | +11.679 |
| P95 (billion USD 2015/yr) | 4,266.823 | 4,297.953 | +31.131 |

Changes are calculated from unrounded values; any small differences from subtracting the displayed values are due to rounding.

Mean BCW therefore increases by 13.722 billion USD 2015/yr, but the increase is not uniform: Indonesia has the largest mean increase (+11.981 billion USD 2015/yr), while Mexico has the largest mean decrease (-0.749 billion USD 2015/yr). The global result rises despite a slight decrease in total area among the 119 directly comparable entities because 117 entities that previously had no area now receive one and fluxes are redistributed among entities.

## 5. From GCW and BCW to NCW

For each entity and shared draw $d$, the natural-capital account is the sum of the two available values:

$$
NCW_{i,d}=GCW_{i,d}+BCW_{i,d}.
$$

If one component is missing, the reported sum represents the available component and the missing value remains identifiable; if both are missing, the total is missing. BCW source rows corresponding to the same country are added draw by draw. The global total adds available GCW and BCW values for countries and territories, then adds the BCW “Joint Regimes” row, which is not assigned to a national entity:

$$
NCW_{world,d}=\sum_{i\in\mathcal I_{GCW}}GCW_{i,d}
+\sum_{i\in\mathcal I_{BCW}}BCW_{i,d}+BCW_{JR,d}.
$$

The sets $\mathcal I_{GCW}$ and $\mathcal I_{BCW}$ contain the countries and territories for which the corresponding account is available; $BCW_{JR,d}$ is the value of the “Joint Regimes” row in draw $d$. All 296 raw rows in the BCW file are mapped and then combined into 266 entities in the final account: several territorial rows can contribute to the same country or territory. This aggregation aligns the BCW data with the country or territory level used by FRA and GCW. For example, the BCW row “Trinidade” (BR-ES) is assigned to Brazil (BRA), because the crosswalk identifies it as a sub-territory included in FRA Brazil. Ecosystem and BCW-account data for this row are missing: it remains in the source file and crosswalk, while Brazil's final account combines all rows assigned to it. The coverage count shows that a published account is reported for one of the two rows; it does not turn the blank row into zero. Treating Trinidade as a separate account entity would also require independent GCW and FRA data; the BCW row alone does not provide those accounts.

The NCW table uses the union of GCW entities, BCW entities and entities with mangrove areas, not their intersection; a row is retained even when one of the two accounts is missing. In that case, the total reflects the available account and the column for the missing component remains NaN.

For any simulated quantity $X$ (GCW, BCW or NCW), its percentile of order $p$ is calculated from its $D$ draws. $Q_q$ denotes the empirical quantile of order $q$; percentile $p$ is expressed on a scale from 0 to 100:

$$
P_p^X=Q_{p/100}\!\left(\{X_d\}_{d=1}^{D}\right),\qquad p\in[0,100].
$$

To calculate a global percentile of any order $p$, first add the account values across entities for each shared draw, then take the quantile of order $p/100$ across those resulting totals:

$$
P_p^{NCW,\,world}=Q_{p/100}\!\left(\{NCW_{world,d}\}_{d=1}^{D}\right).
$$

If each entity's percentile is calculated first and those percentiles are then added, the result is a different quantity:

$$
\sum_i P_{p,i}^{NCW}=\sum_i Q_{p/100}\!\left(\{N_{i,d}\}_{d=1}^{D}\right),
\qquad P_p^{NCW,\,world}\ne\sum_i P_{p,i}^{NCW}\quad\text{in general}.
$$

Here, $P_{p,i}^{NCW}$ is the percentile of order $p$ for the NCW of country or territory $i$, whereas $NCW_{world,d}$ is the global total defined above. The two operations generally differ because in the first case the quantile is taken after summing, while in the second it is taken before summing. With $D=20\,000$, the 5th and 95th percentiles delimit the central 90% interval; the same method applies to GCW, BCW and NCW. For example, at $p=5$ (P05), the global NCW percentile is 4,163.868 billion USD 2015/yr. The sum of the 5th percentiles calculated separately for the entities is 4,128.259 billion USD 2015/yr (242 entities with an available NCW), or 35.609 billion less. This difference also includes the “Joint Regimes” account, which is present in the global total but absent from the 242 entities; it therefore does not measure only the difference between a percentile of a sum and the sum of percentiles. The same index $d$ preserves the shared GSCC and marine-rate draws.

## 6. Comparison with the FAOSTAT net forest flux

This analysis addresses a scope question: how do the gross additions estimated by GCW compare with the net forest flux in FAOSTAT? It places two different quantities side by side. GCW estimates gross additions modelled by Gibbs/GFW; the selected FAOSTAT series estimates the net forest flux under the FAO Tier 1 method, accounting for removals and losses included in its account. In practice, the comparison calculates the 2015-2024 FAOSTAT mean for each entity, then presents the largest net sinks and sources alongside the corresponding GCW flow. It shows the difference between gross additions and a net balance and avoids presenting GCW as the net balance of the entire forest sector.

This comparison is descriptive: it does not validate either account against the other and does not measure what share of GCW is “offset” by deforestation. The scopes, methods, periods and carbon components differ; the results are therefore not two directly reconcilable measurements. In the FAOSTAT series, removals are negative and emissions are positive. To express net removals as a positive flow, the sign is reversed for available years from 2015 to 2024:

$$
U^{FAO}_{i,t}=-1\,000\,Value_{i,t}\quad[\mathrm{tCO_2/yr}],
\qquad \bar U^{FAO}_i=\frac{1}{n_i}\sum_{t\ available}U^{FAO}_{i,t}.
$$

The mean $\bar U^{FAO}_i$ is a comparative indicator of net flux under the FAOSTAT scope. It does not replace $U_i$: the two quantities cover different processes, periods and scopes.

## 7. Deforestation and lost annual addition capacity

FRA defines deforestation as the conversion of forest to another land use. For each entity $i$, the FRA table reports a mean annual rate in thousand hectares per year for the periods 2010-2015, 2015-2020 and 2020-2025. These are annual means over each period, not areas accumulated over five years. The most recent reported period is selected; a reported zero remains zero, and if all periods are missing the value remains NaN:

$$
t_i^{sel}=\begin{cases}
2020\text{-}2025 & \text{if reported},\\
2015\text{-}2020 & \text{otherwise, if reported},\\
2010\text{-}2015 & \text{otherwise, if reported},\\
\mathrm{NaN} & \text{if no period is reported},
\end{cases}
\qquad
D_i=1\,000\,D_{i,t_i^{sel}}^{FRA}\quad[\mathrm{ha/yr}].
$$

The mean rate per hectare used to value this loss is the rate from the GCW account for the same entity. If $A_{ib}$ is the forest area in biome $b$ already defined for GCW, the account's total area and its mean entity-level rate are:

$$
A_i^{total}=\sum_b A_{ib}\quad[\mathrm{ha}],
\qquad
\bar u_i^{GCW}=\frac{U_i}{A_i^{total}}
\quad[\mathrm{tCO_2\ ha^{-1}\ yr^{-1}}].
$$

$U_i$ is already expressed in tCO$_2$/yr and includes the $44/12$ conversion applied in the GCW calculation. It is therefore not applied a second time here. $\bar u_i^{GCW}$ is the rate across the entity's four biomes, weighted by their areas in the forest account. It varies from one entity to another.

The FRA rate $D_i$ is converted into the area deforested during one year and then valued using this entity-level mean rate:

$$
A_i^{loss}=D_i\Delta t\quad[\mathrm{ha}],
\qquad \Delta t=1\ \mathrm{yr},
$$

$$
\widehat L_i=A_i^{loss}\bar u_i^{GCW}
=D_i\Delta t\frac{U_i}{A_i^{total}}
\quad[\mathrm{tCO_2/yr}].
$$

This value represents the annual gross addition to living biomass that the area deforested during one year could have supported if its rate had been the entity's GCW mean rate. It measures neither the carbon stock present before conversion, nor emissions released by conversion, nor observed loss separately for each biome.

The monetary value of the lost annual capacity uses the same social-cost-of-carbon draws as the GCW account:

$$
\widehat V_{i,d}=\widehat L_i\,GSCC_d
\quad[\mathrm{USD\ 2015/yr}],
\qquad
P_p^{\widehat V_i}=Q_{p/100}\!\left(\{\widehat V_{i,d}\}_{d=1}^{20\,000}\right).
$$

The percentiles $P_{05}$ and $P_{95}$ give the central 90% interval of monetary values generated by the GSCC draws. The FRA area and mean rate $U_i/A_i^{total}$ remain fixed across these draws, so this interval reflects the GSCC distribution, not the full uncertainty in deforestation or the forest rate. If no FRA period is reported, physical loss and its value remain NaN; if FRA reports zero, they are zero. A positive loss remains NaN if the GCW account or its reference area does not allow $U_i/A_i^{total}$ to be calculated.

The calculation treats all deforestation area reported by FRA as converted forest area and applies the entity's mean rate to it. It does not claim to know which biome was actually lost. The reference area $A_i^{total}$ follows the forest scope used in GCW, which excludes only mangroves explicitly classified as forest in FRA reports. If some FRA-reported loss concerns mangroves or other areas outside this scope, it is valued here using the entity's mean forest rate.
Finally, this calculation does not measure emissions from the deforested stock.

The table also calculates the share of reference forest area represented by the area deforested during one year ($100A_i^{loss}/A_i^{total}$); with the shared entity-level mean rate, this share equals $100\widehat L_i/U_i$. For sensitivity analysis, this central result is compared with two scenarios. In both, the deforested area is assumed to have the same biome composition as the forest area counted for the entity. The low scenario reduces each biome's mean rate by one spatial standard deviation; the high scenario increases it by the same amount. These deterministic scenarios are not confidence intervals.

## 8. Emissions, GDP, population and accounting balances

Territorial fossil and industrial emissions for 2024 are published by the Global Carbon Budget in MtC/yr. The conversion factor provided by its source is 3.664 tCO$_2$/tC:

$$
E_i=E_i^{MtC}\times3.664\times10^6\quad[\mathrm{tCO_2/yr}].
$$

Territorial emissions are compared directly with the physical flows already defined: $U_i$ for forest additions and $S_{i,d}^{\mathrm{blue}}$ for coastal ecosystems and the biological carbon pump.

GDP (in constant 2015 dollars) and population come from the World Bank. For each variable separately, the 2024 value is used if reported; otherwise, 2023 is used, then 2022. Source years are retained for each entity. If none of these three years has a reported value, it remains missing; it is not replaced by zero or an estimate for the sovereign country.

Physical balances against 2024 emissions $E_i$ are:

$$
Z^{GCW}_{i,d}=U_i-E_i,
\qquad Z^{NCW}_{i,d}=U_i+S_{i,d}^{\mathrm{blue}}-E_i
\quad[\mathrm{tCO_2/yr}].
$$

The formula for $Z^{NCW}_{i,d}$ applies when both components are available; if one is missing, the total follows the available-component rule defined in Section 5, without treating missing data as an observed zero. These balances are accounting comparisons, not climate-neutrality tests: fossil and industrial emissions, gross forest additions and marine components do not have the same ecological scope. The descriptive economic ratio is $100\,\overline{GCW_i}/GDP_i^*$, as a percentage of GDP, where $GDP_i^*$ is the latest available value among 2024, 2023 and 2022. The per-capita ratio uses the latest available population in the same way; if the selected GDP and population years differ, their source years are reported separately.

## 9. Finance scenarios and restoration supply

### 9.1 Hypothetical allocation of a share of GCW

The finance scenario hypothetically allocates 2% of the annual GCW value to each entity $i$. The amount uses the same GSCC draw $d$ as GCW:

$$
\mathrm{Fin}_{i,d}^{2\%}=0.02\,GCW_{i,d}\quad[\mathrm{USD\ 2015/yr}].
$$

The factor $0.02$ is a scenario assumption, not an estimate. $\mathrm{Fin}_{i,d}^{2\%}$ denotes a theoretical annual allocation; it is not observed expenditure, a restoration cost or a funding need. This notation avoids confusing the allocation with $F_i$, already used for forest area.

### 9.2 Forest-restoration supply curves

This section explains how the data of Busch et al. (2024) are used to estimate, for each entity (country or territory), the CO$_2$ that forest restoration could capture and its cost. The supply curve shows the cumulative quantity of CO$_2$ that could be restored at each cost level; it helps compare this potential with annual forest-addition capacity lost.

![Forest-restoration supply curve for a fictional entity λ](courbe_offre_lambda.png)

*Fictional example: at a price ceiling of 35.72 USD 2015/tCO$_2$, the first three cells are selected and offer a combined 4,100 tCO$_2$ weighted over 30 years. These values illustrate how to read the curve; they are not results.*

The global forest-restoration opportunity map of Busch et al. (2024) contains cells of about 1 km in 138 low- and middle-income countries. Each cell $c$ in this map has an eligible restoration area, growth parameters, a plantation type and costs. $\mathcal C_i$ denotes the set of cells assigned to entity $i$ (country or territory). The calculation retains only cells with the required parameters that pass the eligibility criteria; deserts, xeric areas and mangroves are excluded ([Busch et al. (2024)](https://www.nature.com/articles/s41558-024-02068-1)).

A fictional two-cell example walks through the calculation ([see ILLUSTRATION_COR.md](ILLUSTRATION_COR.md)).

#### 9.2.1 From tree stock to carbon per hectare

Growth and costs are followed over the 30 years after restoration begins; this is the period studied. To add values that occur at different times, each year $t$ receives a weighting coefficient $d_t=0.95^{t-1}$. This coefficient is 1 in year 1 and then decreases by 5% each year, giving less weight to values further in the future. It represents neither tree weight nor a biological decline in growth.

For method $m\in\{\mathrm{NR}\ (\text{natural regeneration}),\mathrm{P}\ (\text{plantation})\}$, aboveground stock follows the Chapman-Richards growth function. $A_{c,m}$ denotes the theoretical maximum stock (in $\mathrm{tC/ha}$), and $k_{c,m}$ (in $\mathrm{yr}^{-1}$, or per year) controls how quickly that stock is approached. Stock at age $a$ and its change between two successive ages are:

$$
S_{c,m}(a)=A_{c,m}(1-e^{-k_{c,m}a})^2,
\qquad
\Delta S_{c,m,t}=S_{c,m}(t)-S_{c,m}(t-1).
$$

$S_{c,m}(a)$ is the live aboveground stock in one hectare at age $a$: it starts at zero at age 0 and approaches $A_{c,m}$ as the stand grows. $k_{c,m}$ controls the speed of this growth. $\Delta S_{c,m,t}$ is the stock change between two successive ages and represents that year's aboveground addition before applying the weight $d_t$. Before this calculation, any negative value of $A$ or $k$ is set to zero.

Under natural regeneration (NR), aboveground additions are weighted and accumulated over 30 years. Belowground carbon is estimated by multiplying this aboveground cumulative amount by the root-to-shoot ratio $r_c^{NR}$. This ratio follows rules associated with the FAO ecological zone, country or continent and, where specified, tree genus; if no specific rule applies, the value used is $0.26$. The annual soil-carbon addition follows the source model's rate of $0.415107735\ \mathrm{tC\,ha^{-1}\,yr^{-1}}$:

$$
\begin{aligned}
C_{c,\mathrm{aboveground}}^{NR}&=\sum_{t=1}^{30}d_t\Delta S_{c,NR,t},&
C_{c,\mathrm{roots}}^{NR}&=r_c^{NR}C_{c,\mathrm{aboveground}}^{NR},\\
C_{c,\mathrm{soil}}^{NR}&=0.415107735\sum_{t=1}^{30}d_t,&
C_{c,NR}^{*}&=C_{c,\mathrm{aboveground}}^{NR}
+C_{c,\mathrm{roots}}^{NR}+C_{c,\mathrm{soil}}^{NR}.
\end{aligned}
$$

$C_{c,NR}^{*}$ adds aboveground carbon, estimated root carbon and soil additions. It is a weighted cumulative amount per hectare over 30 years, not an annual rate.

The sensitivity analysis changes only the annual soil-carbon addition rate under natural regeneration:

| Scenario | NR soil rate (tC/ha/yr) |
|---|---:|
| Busch reference | 0.415107735 |
| No change in soil carbon | 0 |
| Post and Kwon (2000) | 0.338 |

The Post and Kwon rate is the conversion of their mean of $33.8\ \mathrm{gC/m^2/yr}$ for soil-carbon accumulation during forest establishment on agricultural land. It is a comparison scenario because this mean is specific neither to Busch cells nor to natural regeneration alone ([Post and Kwon, 2000](https://doi.org/10.1046/j.1365-2486.2000.00308.x)). The plantation soil rate remains fixed at the Busch value ($0.092749069\ \mathrm{tC\,ha^{-1}\,yr^{-1}}$). For each scenario, the calculation recomputes NR carbon, the cell-by-cell method choice, quantities, supply curves and target-attainment costs. These deterministic scenarios are not uncertainty intervals.

#### 9.2.2 Rotation, live stock and harvested carbon

In the plantation scenario, a **rotation** is the period between planting the trees and harvesting them. After harvest, the model assumes that a new plantation starts. The length of this period, denoted $H_c$, is measured in years and can vary across cells $c$. Harvest is simulated in the model; it does not describe an actual intervention. Natural regeneration has no rotation or harvest in this calculation.

The plantation type determines $A_{c,P}$ and $k_{c,P}$ from parameters available for Pinus, Cunninghamia, Eucalyptus and four functional groups (evergreen or deciduous broadleaves, and evergreen or deciduous needle-leaved trees). To select the rotation, relative growth between ages $a-1$ and $a$ is calculated:

$$
g_{c,a}=\frac{S_{c,P}(a)-S_{c,P}(a-1)}{S_{c,P}(a-1)}.
$$

$g_{c,a}$ is a relative increase (multiply by 100 to express it as a percentage). For each age $a=2,\ldots,29$, it is compared with the rotation threshold defined for a 5% annual discount rate:

$$
g_{c,a}>\frac{0.05}{1-(1.05)^{-a}}.
$$

The latest age $a^*$ that satisfies this criterion is retained, and the rotation length is set to $H_c=a^*+1$ (the plantation-cycle length used by the model to simulate harvests and replanting). For example, if the latest qualifying age is $a=9$, then $H_c=10$ years and the first harvest is simulated in year 10. If no age satisfies the criterion, $H_c=31$ is used only to indicate that there is no harvest during the 30 years studied; it does not mean that a harvest occurs at year 31.

At each harvest, plantation trees are harvested and the new plantation starts again at age zero. The remainder $t\bmod H_c$ (modulo) gives the age of the trees after the event in year $t$, while $(t-1)\bmod H_c$ gives their age at the end of the previous year. The difference between the two stocks therefore measures the annual change in live aboveground carbon:

$$
C_{c,\mathrm{aboveground}}^{P}
=\sum_{t=1}^{30}d_t
\left[S_{c,P}(t\bmod H_c)-S_{c,P}((t-1)\bmod H_c)\right].
$$

Why does this change become negative in the harvest year? For a rotation of $H_c=10$ years, the balance can be read in three steps:

1. At the end of year 9, live aboveground stock is $S_{c,P}(9)$.
2. During year 10, the trees grow to $S_{c,P}(10)$.
3. Harvest removes this stock and returns live stock to $S_{c,P}(0)=0$.

The change in year 10 is therefore that year's growth minus the entire harvested stock:

$$
S_{c,P}(0)-S_{c,P}(H_c-1)
=\underbrace{[S_{c,P}(H_c)-S_{c,P}(H_c-1)]}_{\text{growth during the year}}
-\underbrace{S_{c,P}(H_c)}_{\text{harvested stock}}.
$$

Thus, for $H_c=10$, the aboveground term in year 10 is $d_{10}[S_{c,P}(0)-S_{c,P}(9)]$. In the cell example, $S_{c,P}(9)=43.613407\ \mathrm{tC/ha}$ and $S_{c,P}(0)=0$. Live stock therefore changes by $-43.613407\ \mathrm{tC/ha}$ before weighting, or $-27.487324\ \mathrm{tC/ha}$ after multiplication by $d_{10}=0.630249$.

This is the decrease in carbon remaining in live stock; it does not replace the harvested-carbon term, which is counted separately. In harvest years $H_c,2H_c,\ldots$, harvested stock is $S_{c,P}(t)$; at the first harvest, this is $S_{c,P}(10)$. Only the share $w_i$ that remains stored in long-lived wood products is added to the cumulative amount. $w_i$ describes this retained share and is distinct from the wood-product revenue coefficient $p_i$, which enters the cost calculation later:

$$
\begin{aligned}
C_{c,\mathrm{roots}}^{P}&=r_c^P C_{c,\mathrm{aboveground}}^{P},\\
C_{c,\mathrm{soil}}^{P}&=0.092749069\sum_{t=1}^{30}d_t\,\mathbf 1(t<H_c),\\
C_{c,\mathrm{harvested}}^{P}&=\sum_{t=1}^{30}\mathbf 1(t\bmod H_c=0)\,d_tS_{c,P}(t),\\
C_{c,P}^{*}&=C_{c,\mathrm{aboveground}}^{P}+C_{c,\mathrm{roots}}^{P}
+C_{c,\mathrm{soil}}^{P}+w_iC_{c,\mathrm{harvested}}^{P}.
\end{aligned}
$$

$r_c^P$ is the plantation-specific root-to-shoot ratio and may differ from the natural-regeneration ratio. The annual soil addition is $0.092749069\ \mathrm{tC\,ha^{-1}\,yr^{-1}}$, but only up to the first harvest. $\mathbf 1(t<H_c)$ counts this soil addition before the first harvest, while $\mathbf 1(t\bmod H_c=0)$ selects harvest years. $C_{c,P}^{*}$ is the weighted cumulative amount over 30 years, per hectare, in $\mathrm{tC/ha}$.

#### 9.2.3 Costs and method choice for each cell

Cell area is denoted $A_c^{\mathrm{cell}}$ and expressed in $\mathrm{m^2}$. It is converted to hectares using $a_c=A_c^{\mathrm{cell}}/10\,000$. Monetary amounts in the Busch data are expressed in 2020 dollars; they are converted to 2015 dollars using the Bureau of Labor Statistics annual-average CPI-U (2015: 237.017; 2020: 258.811) ([source](https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm)):

$$
f_{20\rightarrow15}=\frac{237.017}{258.811}\simeq0.9158.
$$

The fields $nr\_cost$, $np\_cost$ and $ep\_cost$ are the implementation costs for natural regeneration, native plantations and exotic plantations. They cover establishment and management for approximately three to five years; the Busch data express them in 2020 dollars per hectare. The field $crop\_va$ is the annual land opportunity cost per hectare: the net income forgone when land is allocated to restoration. These four costs are converted to 2015 dollars using the factor above. The other parameters used here are:

| Symbol | Definition | Unit |
|---|---|---|
| $nr\_cost^{2015}$ | Establishment and initial management cost for natural regeneration | USD 2015/ha |
| $np\_cost^{2015}$ | Establishment and initial management cost for a native plantation | USD 2015/ha |
| $ep\_cost^{2015}$ | Establishment and initial management cost for an exotic plantation | USD 2015/ha |
| $crop\_va^{2015}$ | Annual land opportunity cost | USD 2015/(ha·yr) |
| $e_i$ | National share of plantations made up of exotic species, applied to cells in entity $i$; Busch value based on FRA 2020, Table 24 | Fraction from 0 to 1 |
| $p_i^{2015}$ | National net-revenue coefficient for wood products per tonne of harvested carbon, after harvest and delivery costs | USD 2015/tC |
| $C_{c,\mathrm{harvested}}^{P}$ | Harvested carbon per hectare over the 30-year period, weighted by $d_t$ | tC/ha |
| $E_{c,P}^{(0)}$ / $E_{c,P}^{(t)}$ / $E_{c,P}$ | Initial / cumulative through year $t$ / total plantation establishment cost over 30 years, per hectare | USD 2015/ha |
| $K_{c,NR}$, $K_{c,P}$ | Total net cell cost for natural regeneration or plantation | USD 2015/cell |

The parameter $e_i$ is the share of plantations in entity $i$ made up of exotic (non-native) tree species. It is used to calculate the average plantation cost by weighting exotic and native plantation costs. For example, when no genus-specific rule applies, $e_i=0.25$ gives $0.25\,ep\_cost+0.75\,np\_cost$. The program has two exceptions: it uses the exotic cost for Eucalyptus and Cunninghamia outside China, and the native cost for Cunninghamia in China.

The cell costs are calculated as follows:

$$
\begin{aligned}
E_{c,P}^{(0)}&=e_i ep\_cost^{2015}+(1-e_i)np\_cost^{2015},\\
E_{c,P}^{(t)}&=E_{c,P}^{(t-1)}
[1+d_t\mathbf 1(t\bmod H_c=0)],\qquad E_{c,P}=E_{c,P}^{(30)},\\
K_{c,NR}&=a_c\left[nr\_cost^{2015}+crop\_va^{2015}\sum_{t=1}^{30}d_t\right],\\
K_{c,P}&=a_c\left[E_{c,P}+crop\_va^{2015}\sum_{t=1}^{30}d_t-p_i^{2015}C_{c,\mathrm{harvested}}^{P}\right].
\end{aligned}
$$

$E_{c,P}^{(0)}$ is the initial cost, $E_{c,P}^{(t)}$ is the cumulative cost through year $t$, and $E_{c,P}$ is the total over 30 years. The plantation cost $E_{c,P}$ appears only in $K_{c,P}$ because it represents establishment and replanting. It does not appear in $K_{c,NR}$, which represents natural-regeneration costs.
When no harvest occurs in year $t$, $E_{c,P}^{(t)}$ remains equal to $E_{c,P}^{(t-1)}$. When harvest occurs, it is multiplied by $1+d_t$, following the program's rule ($d_t$ and $H_c$ were defined above).

$K_{c,NR}$ and $K_{c,P}$ are total net cell costs in 2015 dollars: establishment cost and land opportunity cost are added, then the net revenue from wood products associated with harvested carbon is subtracted for a plantation. The term $p_i^{2015}C_{c,\mathrm{harvested}}^{P}$ is revenue per hectare; multiplying it by $a_c$ gives total cell revenue.

Before calculating the ratios, the method-specific spatial filter is applied. $B_{c,m}=1$ if cell $c$ is within 5 km of existing natural forest for natural regeneration ($m=NR$), or within 40 km of an existing plantation for plantation ($m=P$); otherwise, $B_{c,m}=0$. These distances are proximity criteria for seed sources and for plantation and wood-processing infrastructure, respectively ([Busch et al. (2024)](https://doi.org/10.1038/s41558-024-02068-1)).

The method is selected by comparing discounted carbon per net dollar and per hectare:

$$
R_{c,NR}=\frac{C_{c,NR}^{*}B_{c,NR}}{K_{c,NR}/a_c},
\qquad
R_{c,P}=\frac{C_{c,P}^{*}B_{c,P}}{K_{c,P}/a_c}.
$$

These ratios compare carbon per hectare with net cost per hectare and are expressed in $\mathrm{tC/USD\ 2015}$. The method with the higher ratio is selected; under the Busch rule, plantation is also selected when its net cost is negative. The selected method is denoted $m_c^*$.

After this choice, the cost $K$ of the selected method is also used in Sections 9.2.4 and 9.2.5. It enters the curve price $p_{ic}^{\mathrm{curve}}$, which determines the price threshold at which a cell's quantity appears in the supply curve. It also enters the effective cost per additional tonne, $\widetilde p_{ic}$, defined in Section 9.2.5, which is used to rank cells when meeting the target. Finally, the costs of selected cells are added, accounting for the share used in the last cell, to obtain the total cost of meeting that target.

#### 9.2.4 Eligible quantity and national curve

The general filter $G_c$ equals 1 if the cell passes the geographic restoration-potential screen used by Busch et al. based on [Griscom et al. (2017)](https://doi.org/10.1073/pnas.1710465114), and 0 otherwise. This screen excludes, among others, deserts, existing forests, high-elevation areas, natural grasslands and croplands ([Busch et al. (2024)](https://doi.org/10.1038/s41558-024-02068-1)). It is applied in addition to the method-specific filters $B_{c,m}$ defined in Section 9.2.3.

Both feasibility filters are binary. A missing value is treated as 0. A cell contributes to supply only if $G_c=1$ and the filter for its selected method, $B_{c,m_c^*}$, is also 1.

$bau_{2020\text{--}2030,c}$, $bau_{2030\text{--}2040,c}$ and $bau_{2040\text{--}2050,c}$ are the fractions of reforestation expected without a project in cell $c$ for each of the three periods. Their weighted mean gives $BAU_c$ (business as usual, the no-project scenario), the share of carbon that would have been added even without a project. The share attributed to the project is therefore $1-BAU_c$. If the three inputs do not allow this mean to be calculated, the value used for $BAU_c$ is $0.0571795$:

$$
BAU_c=0.510928\,bau_{2020\text{--}2030,c}
+0.305911\,bau_{2030\text{--}2040,c}
+0.183161\,bau_{2040\text{--}2050,c}.
$$

Eligible quantity is calculated by multiplying carbon per hectare by area, the two masks and the additional share; $44/12$ converts carbon to CO$_2$:

$$
q_{ic}^{*}=a_cC_{c,m_c^*}^{*}G_cB_{c,m_c^*}(1-BAU_c)\frac{44}{12}
\quad[\mathrm{discounted\ tCO_2/cell}].
$$

Since $C^*$ is already weighted over 30 years, $q_{ic}^{*}$ represents the total amount of CO$_2$ a cell can offer over that period after applying the masks and additionality. It is a 30-year weighted cumulative amount, not an annual quantity. The reconstruction uses the exact ratio $44/12$; the rounded factor 3.67 is used only in the separate check against the published curve.

The curve price divides the total cost of the selected method by its total carbon before applying the masks and additionality:

$$
p_{ic}^{\mathrm{curve}}
=\frac{K_{c,m_c^*}}{(44/12)a_cC_{c,m_c^*}^{*}}
\quad[\mathrm{USD\ 2015/discounted\ tCO_2}].
$$

The masks and $1-BAU_c$ therefore reduce the quantity offered, but not this curve-classification price. Eligible cells with a positive, finite quantity and a calculable price form the set $\mathcal C_i^{+}$. At price threshold $p$, the national curve adds the quantities of cells whose curve price does not exceed that threshold:

$$
V_i(p)=\sum_{c\in\mathcal C_i^{+}}q_{ic}^{*}
\mathbf 1(p_{ic}^{\mathrm{curve}}\le p).
$$

The published curve's thresholds range from $-20$ to $100$ USD 2020/tCO$_2$, in steps of 5 USD 2020. To classify the reconstruction in 2015 dollars, each threshold is multiplied by $f_{20\rightarrow15}$. The check that reproduces the published workbook keeps the original thresholds in 2020 dollars separately.

#### 9.2.5 Cost required to reach the target

$\widehat L_i$ is the annual addition capacity lost, defined in Section 7. The target assumes that this annual loss recurs for 30 years, using the same weights $d_t$:

$$
D_{30}=\sum_{t=1}^{30}0.95^{t-1}=15.7072247,
\qquad
Q_i^{\mathrm{target}}=\widehat L_iD_{30}
\quad[\mathrm{discounted\ tCO_2}].
$$

If $\sum_{c\in\mathcal C_i^{+}}q_{ic}^{*}<Q_i^{\mathrm{target}}$, the available cells are insufficient to reach the target and no target cost is calculated. This comparison applies to entities with positive forest loss and a published national curve; only cells with positive quantity and a calculable cost enter the ranking.

When supply is sufficient, the target is reached by ranking cells according to net cost per additional quantity supplied after filtering:

$$
\widetilde p_{ic}=\frac{K_{c,m_c^*}}{q_{ic}^{*}}
\quad[\mathrm{USD\ 2015/discounted\ tCO_2}].
$$

$\widetilde p_{ic}$ is the effective cost per additional tonne for a cell; unlike curve price $p_{ic}^{\mathrm{curve}}$, its denominator includes the masks and additionality. Cells are selected in ascending order of $\widetilde p_{ic}$ until the target is reached. $\alpha_{ic}$ is the fraction of a cell used: 1 for a fully used cell, between 0 and 1 for the final cell if the target is reached partway through it, and 0 for later cells. If $\widetilde p_{i,\mathrm{marg}}$ is the effective cost per tonne for the last cell used, the three discounted costs in 2015 dollars are:

$$
\begin{aligned}
K_i^{\mathrm{net}}&=\sum_c\alpha_{ic}K_{c,m_c^*},\\
K_i^{+}&=\sum_c\alpha_{ic}\max(K_{c,m_c^*},0),\\
K_i^{\mathrm{uniform}}&=\max(\widetilde p_{i,\mathrm{marg}},0)Q_i^{\mathrm{target}}.
\end{aligned}
$$

$K_i^{\mathrm{net}}$ retains revenues and negative costs; $K_i^{+}$ adds only positive costs. $K_i^{\mathrm{uniform}}$ applies the last cell's price to every tonne of the target, without a negative payment; it is a uniform-payment scenario, not observed expenditure. Because costs are already in 2015 dollars, their annual equivalent is obtained by dividing the present value by $D_{30}$:

$$
K_i^{x,\mathrm{annual,2015}}
=\frac{K_i^{x,\mathrm{PV,2015}}}{D_{30}},
\qquad x\in\{\mathrm{net},+,\mathrm{uniform}\}.
$$

Dividing by $D_{30}$ spreads each present value across the 30 weighted years. The CPI ratio is therefore not applied a second time at this stage.

For a detailed worked example, see [ILLUSTRATION_COR.md](ILLUSTRATION_COR.md).

## 10. Descriptive and spatial analyses

Descriptive statistics summarize the available national values. The median divides a sample in half; the share of the ten largest entities is their sum divided by the overall sum; and the Gini coefficient summarizes distributional inequality (0 is perfect equality and 1 is maximum concentration). The Kruskal-Wallis test compares ranks across several groups; Mann-Whitney tests compare ranks for two groups at a time; the Holm correction adjusts the $p$-values of multiple tests to control the risk of false positives within the family of comparisons. Spearman's rank correlation measures the monotonic association between GCW and relative erosion ranks. These summaries and tests are descriptive; they do not establish a causal relationship.

Spatial analyses examine three main outcomes: annual lost capacity, in MtCO$_2$/yr; its ratio to GCW, as a percentage; and GCW relative to GDP, also as a percentage. $x_i$ is the observed numeric value of the outcome for the entity concerned; $y_i=\ln(1+x_i)$ is its natural-log transformation, which retains zeros. An extension adds 2024 territorial emissions, in MtCO$_2$/yr, as both an explanatory variable and an outcome. Each estimate uses the entities with all variables required for that relationship.

The core explanatory variables are log GDP per capita, $\ln(GDP_i^*/Pop_i^*)$; the log of one plus forest area in millions of hectares, $\ln(1+A_i^{\mathrm{total}}/10^6)$ when area is in hectares; and the tropical and subtropical share, $s_{i,\mathrm{tropical}}+s_{i,\mathrm{subtropical}}$. Below, $X$ denotes the matrix of these explanatory variables for the $n$ entities in the sample, with a constant; the extension adds territorial emissions when they are used as an explanatory variable.

Two neighbourhood definitions are compared for each sample. Let $a_{ij}=1$ when entities $i$ and $j$ are neighbours, and 0 otherwise; diagonal entries $a_{ii}$ are zero.

- Queen contiguity links two polygons that share a boundary or a vertex.
- The five-nearest-neighbour graph is built from the five closest representative geographic points for each entity, then symmetrized: a pair is linked if either $i$ selects $j$ or $j$ selects $i$.

Links are first restricted to entities in the complete sample for the analysis, then row-standardized:

$$
w_{ij}=\frac{a_{ij}}{\sum_{\ell=1}^{n}a_{i\ell}}
\quad\text{if } \sum_{\ell=1}^{n}a_{i\ell}>0;
\qquad
w_{ij}=0\quad\text{for an isolated entity}.
$$

The matrix $W=(w_{ij})$ contains these weights; $w_{ij}$ is the weight assigned to entity $j$ in the neighbourhood of $i$. The weights in each non-isolated row sum to 1.

For a transformed outcome $y_i$, $\bar y=n^{-1}\sum_i y_i$ is its sample mean, $z_i=y_i-\bar y$ is its centred value, and $z$ is the vector of centred values; the symbol $\top$ denotes the transpose of a vector or matrix. $n$ is the number of entities in that sample. The global Moran's index is:

$$
I=\frac{n}{S_0}\frac{z^\top Wz}{z^\top z},
\qquad S_0=\sum_i\sum_jw_{ij}.
$$

$S_0$ is the sum of all neighbourhood weights. Since rows are standardized, $S_0$ equals the number of non-isolated entities; it can be smaller than $n$ for Queen contiguity, which retains isolated entities as zero rows. The significance of $I$ is assessed with 9,999 permutations of values across entities while keeping $W$ fixed; the test is two-sided. It is calculated for transformed outcomes and for residuals $\hat u_i=y_i-X_i\hat\beta$ from the OLS model, where $X_i$ is the row of $X$ for entity $i$ and the hat indicates an estimated value.

Candidate spatial regressions are written as:

$$
\mathbf y=\rho W\mathbf y+X\boldsymbol\beta+WX\boldsymbol\theta+\mathbf u,
\qquad
\mathbf u=\lambda W\mathbf u+\boldsymbol\varepsilon.
$$

$\mathbf y$ is the vector of transformed outcomes ($n\times1$); $X$ is the explanatory-variable matrix ($n\times k$), where $k$ is the number of explanatory columns, including the constant; $W$ is the neighbourhood matrix ($n\times n$) defined above. $W\mathbf y$ gives the neighbour-weighted mean outcome for each entity; $WX$ similarly gives the neighbour-weighted means of explanatory variables. $\boldsymbol\beta$ and $\boldsymbol\theta$ are coefficient vectors; $\rho$ represents a spatial outcome-lag term; $\mathbf u$ is the model error; $\lambda$ represents spatial dependence in that error; and $\boldsymbol\varepsilon$ is the non-spatial error term.

**Sequence of diagnostics and comparisons.** Starting from the sample and neighbourhood matrix defined above, the analysis proceeds through the following steps:

1. **Estimate the OLS reference model (ordinary least squares).** It contains no spatial term: $\rho=\lambda=0$ and $\boldsymbol\theta=\mathbf0$.
2. **Check spatial autocorrelation with Moran's index.** The test is first applied to the transformed outcome, then to the OLS residuals. If the residuals remain spatially autocorrelated, this indicates that OLS does not fully account for spatial structure; autocorrelation in the outcome alone is not sufficient to establish this. Significance is assessed with 9,999 permutations and $p$-values are adjusted using Holm's method.
3. **Diagnose the form of dependence with LM tests (Lagrange multipliers).** The standard and robust tests use OLS residuals. They examine spatial-lag ($\rho$) and spatial-error ($\lambda$) terms, as well as the joint SARMA and SDM tests. A lag signal points to SAR and SDM for closer examination; an error signal points to SEM and SDEM; if the diagnostics indicate multiple terms, GNS is also among the models to compare. $p$-values are adjusted using Holm's method for each test type.
4. **Estimate all six candidate models in every case, regardless of the diagnostics.** SAR (spatial autoregressive model) estimates $\rho$; SEM (spatial error model) estimates $\lambda$; SDM (spatial Durbin model) estimates $\rho$ and $\boldsymbol\theta$; SDEM (spatial Durbin error model) estimates $\lambda$ and $\boldsymbol\theta$; GNS (general nesting spatial model) estimates all three spatial terms. OLS fixes all three terms at zero. The LM results therefore guide interpretation of the candidates but do not determine whether they are estimated in the implemented process.
5. **Compare nested models with LR tests (likelihood-ratio tests).** The comparisons are SDM against SAR (restriction $\boldsymbol\theta=\mathbf0$), SDEM against SEM (restriction $\boldsymbol\theta=\mathbf0$), and GNS against SDM (restriction $\lambda=0$). $p$-values are adjusted using Holm's method for each comparison. If a restriction is rejected, the model that relaxes it provides a better statistical fit in that comparison; otherwise, the test does not show that relaxing the restriction improves fit.
6. **Consider the comparison evidence together.** For each outcome and neighbourhood matrix, the Akaike information criterion (AIC) and Bayesian information criterion (BIC) rank the six candidates. The tests and rankings document differences but do not automatically select a final scientific model; estimated associations are not interpreted as causal effects.

## 11. Calculation consistency and final result

Dimensional consistency and account identities rely in particular on the following equalities:

| Step | Expected relation |
|---|---|
| Biome shares | $\sum_b s_{ib}=1$ |
| Corrected forest area | $\sum_{i,b}A_{ib}=\sum_i(F_i-O_i^F)$ |
| Forest additions | $\sum_iU_i=(44/12)\sum_{i,b}A_{ib}\bar r_b$ |
| Documented FRA mangrove area | $O_i^F+O_i^{OWL}+O_i^R+O_i^?=M_i^{FRA}$ |
| Corrected GMW area | $A_i^{GMW,corr}=0.9775\,A_i^{GMW,raw}$ |
| NCW account | $N_{i,d}=GCW_{i,d}+BCW_{i,d}$ for available components |
| GCW valuation | $GCW_{i,d}=U_i\,GSCC_d$ |

These identities check dimensional consistency and account closure. They do not resolve scientific choices, including the classification of mangroves without a breakdown or the interpretation of parameters published by another study.

The calculation follows this sequence: Gibbs/GFW raster data and forest mask → annual rates by biome → FRA forest areas distributed across biomes and corrected for mangrove overlap → physical flows and GCW valuation. In parallel, the selected mangrove area follows the GMW 2025/FRA 2025/area reported by Hilmi et al. (2026) hierarchy → the total blue flux is calculated directly from coastal areas, their rates and the reported BCP flux → it is valued as BCW. GCW and BCW are then added to form NCW, followed by comparisons with deforestation, emissions and GDP, and finance scenarios. Tables and figures summarize these steps and their scopes.

Primary sources: [Gibbs et al. (2025) methods article](https://essd.copernicus.org/articles/17/1217/2025/), [FRA definition of deforestation](https://fra-data.fao.org/definitions/fra/2020/en/tad), [FAO Global Ecological Zones 2010](https://www.fao.org/4/ap861e/ap861e00.pdf), [Marine Regions EEZ-land union](https://www.marineregions.org/downloads.php), [IPCC 2006 Guidelines, Chapter 4](https://www.ipcc-nggip.iges.or.jp/public/2006gl//pdf/4_Volume4/V4_04_Ch4_Forest_Land.pdf), [FAO net forest-flux estimates (Tubiello et al., 2026)](https://essd.copernicus.org/articles/18/6799/2026/), [Gibbs/GFW dataset](https://doi.org/10.7910/DVN/V2ISRH), [GMW dataset](https://zenodo.org/records/21346457), [BLS annual CPI-U](https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm), [Busch et al. (2024) article](https://doi.org/10.1038/s41558-024-02068-1), and [Busch cell-level input data and Stata program](https://zenodo.org/records/19239386).
