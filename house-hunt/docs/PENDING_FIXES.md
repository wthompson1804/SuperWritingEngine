# Pending fixes (to apply in one pass after the third independent check reports)

From the ratings census (search-result summaries; second-hand, so each needs a verdict by reading, not a blind removal):
- **30 Broad Street, Port Chester** (units 703, 904 shown): an August 2026 article says the building is under construction,
  completion early 2027. "Available now" cannot be true if so. Verdict: remove unless a page shows it is occupied.
- **1244 New York Ave, Brooklyn 3A** (shown): a search summary describes a 2-unit, 2-story 1910 building; the city record
  matched to it says class D1, 6 floors. Check the lot match (house number, BBL). If the lot is a near-miss, the elevator is open.
- **61 Clarkson Ave, Brooklyn 2B** (shown): summary says 3-story, 11 units; city record says D3, 6 floors. Same check.
- **Regency on Hudson, Yonkers** (318, 417 shown): a Google review claims units were advertised with no occupancy permit.
  One open "listing real and available" fact.
- **Kensington Place** is at an East Brunswick address, not South River: check its neighborhood.
- Building names found for unnamed addresses: 475 Main St Orange = The Elks; 270 Luis M Marin Blvd = Metropolis Towers;
  26-25 4th St = The Winslow; 187 Culver Ave = The Tetris; 479 Front St = Village Lofts; 12 Brooklyn Ave = Sun Valley Towers;
  5 Linden St = The Hampton. Add as building_name (basis: search result, medium).
- Vermella Harrison's address is split across address and city columns in the targets file ("1100 Frank" / "E Rodgers Blvd. S Harrison").

From the page agent:
- `meta.notes` and twelve `confirm.why` texts still say "counted as $0": the builder should say "not published".
- `rent.offer_text` sometimes carries raw key:value text.

From the contacts agent:
- `scripts/building_contacts.py` has no rule against recording a single-unit lister's own number as "property-supplied".
  The page and call sheet now hide broker and owner numbers; the table itself should be re-graded.
