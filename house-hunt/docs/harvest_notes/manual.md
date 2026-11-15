# Manual addition: Envy by Gomes, 58-84 Norfolk St, Newark NJ 07103 (2026-11-15)

Added at Will's request (screenshot). Script: `scripts/h_manual.py` (idempotent; `--refresh` refetches). Raw: `raw/manual_envy/`.
Also serves as the evidence note for `data/evidence/*_batch_manual.csv`.

## Sources used
- Own site: `https://bygomes.com/property/envy/` (envybygomes.com redirects here). robots.txt disallows only
  `/property/envy/landing`. Gatsby site; `/page-data/property/envy/<unit>/page-data.json` carries the RentCafe feed
  values per unit (availableDate, minPrice, maxPrice, floor). It shows only 6 units (4 one-bedrooms).
- Trulia building page (`/building/envy-by-gomes-58-norfolk-st-newark-nj-07103-2734055214`; a second URL ending
  `-2550653520` serves the same content): full unit table (10 one-bedrooms, 9 two-bedrooms), sqft, pet policy,
  elevator, unit count 165.
- Jersey Digs (Crawl-delay 1): opening article 2023-06-02, proposal article 2021-09-09, developer profile 2025-12-19.
- Census geocoder for lat/lon.

## Blocked (not worked around)
- `envy-by-gomes-rentcafewebsite.securecafe.com` (the Apply / leasing portal): Cloudflare challenge on robots.txt, 403.
- `www.rentcafe.com/apartments/nj/newark/envy-by-gomes/`: 403 Cloudflare block.
- `www.bbb.org` profile for Gomes Group LLC: bot challenge, 403. Rating seen only in a search snippet, so not recorded.
- No Zumper or Apartment List page found. Apartments.com, Zillow, StreetEasy not touched.

## Things to know
- No studios available. 10 one-bedrooms, $2,000 to $2,427.
- Prices are net of concessions on the own site ("* PRICE INCLUDES CONCESSIONS"); gross rent is not published.
  Trulia calls its prices "base rent" but they match the own site on 3 of 4 shared units.
- G02 conflict: own site $2,100, Trulia $1,858 (the feed's minPrice 1858, maxPrice 2100).
- Dog weight limit 35 lb (Trulia, from the manager's feed). Own site publishes no pet policy.
- Parking fee, amenity fee amount and which utilities are included are not published.
- Unit 127: the building has a separate G level, so whether floor 1 is at street level is unconfirmed.
- No tenant reviews or incident reports found anywhere allowed.
