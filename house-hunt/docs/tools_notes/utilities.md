# Utilities tool: notes

`scripts/tools/utilities.py` → `monthly_utilities(lat, lon, beds=1, sqft=None, heat_included=None)`.
Returns `electric`, `gas`, `internet` and `total`, each with `amount`, `value_type` (`estimate` or `not_found`),
`method` and `sources` (`source_url` + `retrieved_at`). Also exported: `electric_utility(lat, lon)`, `locate(lat, lon)`.
Every amount is an estimate for the page's asterisk; none is a quote for an address.

Reference tables: `data/reference/utility_rates.csv` (107 rows; written by `--build`) and, secondary,
`data/reference/taxes.csv` (39 rows; written by `scripts/tools/taxes_reference.py`).

## Run

- `python3 scripts/tools/utilities.py` : self-test on the six contract points (`--more`, `--verbose`, `--json`).
- `python3 scripts/tools/utilities.py --build` : rebuild `raw/big/utilities/index.pkl` and `utility_rates.csv` from the
  cached downloads (about 5 s from cache; a cold rebuild downloads about 75 MB). Needs pandas, openpyxl, xlrd, pyshp
  (`pip install xlrd pyshp` was needed here). Lookups need only shapely.
- Speed: index load 0.03 s; about 0.5 ms per lookup (1,000 lookups in 0.55 s).

## Self-test results (1 bedroom, heat unknown)

| Point | Electric | Gas (cooking only) | Gas if tenant pays heat | Internet | Total |
|---|---|---|---|---|---|
| Jamaica station | $95, Con Edison, 36.74 c/kWh | $24, National Grid NY | $44 | $75 | $194 |
| Forest Hills | $95, Con Edison | $24, National Grid NY | $44 | $75 | $194 |
| Long Beach NY | $68, PSEG Long Island, 26.17 c/kWh | $28, National Grid LI | $48 | $75 | $171 |
| Stamford CT | $75, Eversource CT, 28.88 c/kWh | $29, Eversource CT gas | $48 | $75 | $179 |
| Jersey City Grove St | $65, PSE&G, 25.03 c/kWh | $12, PSE&G | $28 | $75 | $152 |
| Beacon NY | $72, Central Hudson, 27.67 c/kWh | not_found (Central Hudson gas tariff unreachable) | not_found | $75 | $147, `complete=False` |

## Electric

**Utility at the point.** Point-in-polygon on the HIFLD / ORNL "Electric Retail Service Territories" layer (2022 vintage,
95 polygons in the study box -76.2,39.2 to -71.7,42.7). The federal HIFLD Open host no longer serves the layer, so the
polygons come from an ArcGIS Online copy of it (`services3.arcgis.com/OYP7N6mAJJCyH6hd/.../Electric_Retail_Service_Territories_HIFLD`,
attribution ORNL / DOE CESER). Where polygons overlap the smallest wins, which puts municipal utilities (Rockville Centre,
Freeport, Greenport, Wallingford, Madison NJ and so on) ahead of the surrounding company. Documented overrides:

1. **United Illuminating** is drawn as all of Fairfield and New Haven counties. UI is used only in its 17 towns, taken from
   utility-by-municipality counts in the state's RSIP dataset (data.ct.gov `fvw8-89kt`, CT Green Bank); everywhere else in
   those counties is Eversource. Town comes from TIGER 2023 county subdivisions. UI's own service-area page could not be
   reached from this session (host not allowed).
2. **Norwalk**: the SNEW and Third Taxing District polygons each cover the whole city. No district boundary file was
   found, so Norwalk points return Eversource with SNEW and TTD (and their prices) under `alternatives`. **Gap.**
3. **Fishers Island** utility is drawn as all of Suffolk County; it is ignored except on the island.
4. Points in water or on piers snap to the nearest polygon within about 1 km, with a note.

**Price.** EIA-861 2025 annual (`f8612025.zip`), `Sales_Ult_Cust_2025.xlsx`: residential revenue / residential sales for
bundled-service customers (Part A), by utility and state. Small municipals file the short form (`Short_Form_2025.xlsx`),
which has no residential split, so their price is revenue / sales for all customer classes together and is labelled so
(Rockville Centre 11.25, SNEW 18.82, TTD 18.02 cents/kWh). EIA-861M (`sales_revenue.xlsx`) is newer (through August 2026)
but only state-level in that file, so it is kept as context (`state_average_context`, and rows in the CSV), not used.

**Use.** RECS 2020 public microdata v7, Northeast census region (Middle Atlantic + New England), apartments in buildings
with 5 or more units, households whose main heat is not electric, weighted mean of `KWH`:

| Size | kWh/year | kWh/month | n |
|---|---|---|---|
| Studio | 2,631 | 219 | 18 (small sample) |
| 1 bedroom | 3,112 | 259 | 165 |
| 2 bedrooms | 4,094 | 341 | 134 |
| 3+ bedrooms | 4,870 | 406 | 39 |

If `sqft` is given, the size band replaces bedrooms (up to 500: 2,644; 500-750: 3,296; 750-1,000: 3,742; 1,000-1,500: 4,289;
over 1,500: 5,743 kWh/year). Cross-check: published RECS Table CE2.2 (Northeast) gives 4,650 kWh/year for all apartments in
5+ unit buildings, electric heat included; the microdata reproduces it (4,650). Electric heat is not in the amount;
`if_heat_is_electric_add` gives the RECS space-heating kWh for electrically heated apartments, priced, for the case where the
tenant pays electric heat.

## Gas

A cooking-only bill is almost all fixed charge (RECS cooking use for a 1 bedroom is 18.8 therms/year, 1.6 a month), so the
line is built from each utility's own residential minimum or customer charge. Where none could be read, gas is
`not_found` with the reason (no $2-3 figure), and `total.complete` is False.

| Gas utility | Fixed monthly | Per therm / Ccf | Source (read 2026-11-15) | 1 BR cooking-only |
|---|---|---|---|---|
| Con Edison (NYC part, Westchester) | $33.23, first 3 therms | n/a at this use | coned.com `allrates.pdf`, SC 1, sheet for Nov 2026 | $33 |
| National Grid NY (KEDNY) | $23.50, first 3 therms | n/a | nationalgridus.com delivery charges, SC 1A, eff. 2026-04-01 | $24 |
| National Grid Long Island (KEDLI) | $28.50, first 3 therms | n/a | same, SC 1A, eff. 2026-04-01 | $28 |
| Orange & Rockland | $22.50, first 3 Ccf | n/a | oru.com gas tariff PSC No. 4, SC 1, leaf 114 eff. 2026-01-01 | $22 |
| Eversource CT gas (Yankee) | $25.00 | $2.5443 delivery, supply extra | eversource.com Summary of Residential Gas Rates (CT), Rate 01, updated 2026-11-01 | $29 |
| PSE&G | $9.99 (derived) | $1.1104 (derived) | BPU notice GR26060274, winter bill table | $12 |
| New Jersey Natural Gas | $12.00 | $1.5431 (delivery + supply) | BPU order 2026-09-09 item 2B, Exhibit A, non-heating, eff. 2026-10-01 | $14 |
| Elizabethtown Gas | $11.50 (derived) | $1.6395 (derived) | BPU notice GR26060277, heating bill table, 2026-07-01 | $14 |
| South Jersey Gas | $10.51 (derived) | $1.9324 (derived) | BPU notice ER26060356 (SJG), heating bill table, 2026-07-01 | $14 |
| Central Hudson, NYSEG, Southern Connecticut Gas, Connecticut Natural Gas, PGW, PECO | not_found | | hosts unreachable or bot wall (see below); PA not attempted | not_found |

- "Derived" = a straight line through two rows of the utility's published bill table (it also fits the third row); those
  figures include supply. Elizabethtown and South Jersey publish only a heating-class table, so the fixed part is the
  heating class's. NJ Natural's own tariff PDFs are disallowed by its robots.txt, so the BPU order was used.
- **Not reachable**: nyseg.com, cngcorp.com, soconngas.com (Avangrid hosts are outside this session's allowed network);
  centralhudson.com / cenhud.com return an empty bot-check page; nothing on dps.ny.gov states either charge. To fill these,
  allow those hosts or supply the four rate sheets.
- **Cooking + heat** (`heat_included=False`): cooking-only figure + EIA state price x RECS space-heating therms for gas-heated
  apartments (1 bedroom 140 therms/year). An annual average; winter bills are several times higher. Water heating is
  separate (`if_gas_water_heater_add`). Where gas is not_found, `heating_component_if_tenant_pays` gives the heating part alone.
- **State price**: EIA residential price, latest annual, converted with EIA's state heat content: NY $17.58/Mcf = $1.70/therm
  (2025); NJ $14.21 = $1.37 (2025); PA $15.04 = $1.45 (2025); CT $16.83 = $1.63 (2024; 2025 not yet published).
- **Gas utility at the point**: point-in-polygon on an ArcGIS Online copy of HIFLD "Natural Gas Service Territories"
  (2016-17 vintage, built from EIA company territories; coarse), then by county where the layer is too coarse: Nassau and
  Suffolk are KEDLI; Brooklyn, Queens and Staten Island are KEDNY; a Queens point whose electric utility is LIPA (the
  Rockaways) is KEDLI; every Queens result notes that northern Queens is Con Edison gas ($33.23). Westchester falls in the
  Con Edison polygon. In Connecticut the layer gives Stamford and Norwalk to Eversource, Greenwich to CNG, Bridgeport and
  New Haven to SCG. Each result's `notes` states the mapping used.
- The line assumes a gas stove. An all-electric unit has no gas bill; the tool cannot know.

## Internet

One flat figure for every address: **$75/month**, Verizon Fios 500 Mbps (the middle of its five tiers), the published price
before the $10 Auto Pay discount; the page says taxes, fees and router are included. Listed alongside, not used: Fios
300 Mbps $40; Optimum 300 Mbps $35 (new-customer price for 12 months, plus taxes and fees); FCC 2026 Urban Rate Survey
benchmark for 100/20 Mbps unlimited $96.46 (DA 25-1088), which is a ceiling (urban average plus two standard deviations),
not a typical price. Fios is not sold in Connecticut, so the figure is a stand-in there. No address-level availability
was checked. Not obtained: fcc.gov survey data, Spectrum and Xfinity pages (all 403), Optimum's rate card (robots.txt
disallows it for Claude agents).

## Caveats

- RECS is 2020 and regional; prices are 2025 annual averages. Real bills vary with season, supplier (ESCO) and use.
- Average price x a low apartment use understates slightly, since fixed customer charges weigh more on small users.
- Territory polygons are approximate near boundaries (2022 electric, 2016-17 gas).
- Outside NY, NJ, CT and PA the electric and gas lines return `not_found`.
- `total.complete` is False when a line is not_found.

## Taxes (secondary): `data/reference/taxes.csv`

Hand-read from the official pages and PDFs cached in `raw/ny_tax`, `nj_tax`, `ct_tax`, `pa_tax`, `phila_tax`; rules only.
Covers single-filer brackets around $100k-$150k (NY, NJ, CT 2025 schedules; PA flat 3.07%), NYC resident tax, Yonkers
surcharge and nonresident earnings tax, Philadelphia wage tax, the New York convenience-of-the-employer rule
(TSB-M-06(5)I) and how NJ, CT and PA treat residents taxed under it, and combined sales tax rates.
Gaps: NY sales tax rates are from Publication 718 dated March 1, 2025 (a later edition was not checked); the New Jersey
schedule PDF is the "2020 and after" one; Pennsylvania local earned income taxes outside Philadelphia were not collected;
"no local income tax" in NJ and CT is marked not_found because no page states it outright.
