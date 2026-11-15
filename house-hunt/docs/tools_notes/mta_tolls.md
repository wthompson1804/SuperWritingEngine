# MTA Bridges and Tunnels toll rates (closing the "MTA gap")

Written 2026-11-15. Fills the nine MTA rows of `data/reference/tolls.csv` that were `not_found`.
mta.info, e-zpassny.com and the NYCRR site were **not** requested (bot walls).

## Source used (official)

New York State Register, 2025-12-24, Vol. XLVII, Issue 51 (Department of State):

- URL: https://dos.ny.gov/december-24-2025vol-xlvii-issue-51 (returns the PDF itself)
- Retrieved 2026-11-15T23:45:07+00:00, cached as `raw/nys_register/946d64549b18f37d.html` (it is a PDF, 102 pages;
  the `.html` extension is only because the URL has no `.pdf`).
- Page 16: **Notice of Adoption**, I.D. No. TBA-28-25-00011-A, Filing No. 1056, filing date and effective date
  2025-12-08. Repeal and replacement of 21 NYCRR 1021.1, "To establish a new crossing charge schedule for use of
  bridges and tunnels operated by Triborough Bridge and Tunnel Authority".
- Appendix pages 91 to 96 (PDF pages 97 to 102): the adopted schedule. The tables are **page images**, so
  `pdftotext` returns nothing; they were rendered with `pdftoppm` and read by eye.

Why the earlier pass missed it: the issue is not at the usual `/system/files/documents/2025/12/122425.pdf` path
(404). The issue landing-page slug `/<month>-<day>-<year>vol-<roman>-issue-<n>` serves the PDF directly.

## Rates recorded (class 31, two-axle passenger vehicle, per crossing, charged in both directions)

| Crossing | NYCSC E-ZPass (schedule a) | Tolls by Mail / other media (schedule b) | NYCSC mid-tier (schedule c, not used) |
|---|---|---|---|
| Verrazzano-Narrows Bridge | 7.46 | 12.03 | 9.79 |
| Throgs Neck Bridge | 7.46 | 12.03 | 9.79 |
| Bronx-Whitestone Bridge | 7.46 | 12.03 | 9.79 |
| Robert F. Kennedy Bridge | 7.46 | 12.03 | 9.79 |
| Queens-Midtown Tunnel | 7.46 | 12.03 | 9.79 |
| Hugh L. Carey Tunnel | 7.46 | 12.03 | 9.79 |
| Henry Hudson Bridge | 3.42 | 8.87 | 5.42 |
| Cross Bay Veterans Memorial Bridge | 2.80 | 6.02 | 4.42 |
| Marine Parkway-Gil Hodges Memorial Bridge | 2.80 | 6.02 | 4.42 |

Rows carry `value_type = found_manual` (so they survive `drive.py --build-reference`), `source_url` = the Register
issue, `retrieved_at` = the fetch time above.

Schedule b is headed "For customers using fare media other than NYCSC E-ZPass tag or account": that is Tolls by Mail
and also E-ZPass tags issued outside New York. An E-ZPass from New Jersey or Connecticut pays the schedule b rate.

## Effective date

- The Register gives the rule's effective date as 2025-12-08 (filing). It does not print the day collection started.
- `effective_date` is recorded as **2026-01-04**, the day the new charges began to be collected. That date comes from
  a **secondary** source read directly: English Wikipedia, "Verrazzano-Narrows Bridge", revision 1384273277 of
  2026-11-07 ("As of January 4, 2026, the toll is $12.03 per car ... New York E-ZPass ... pay $7.46 per car ...
  Mid-Tier ... $9.79"), fetched through the MediaWiki API 2026-11-15T23:46:32+00:00, cached in `raw/mta_tolls/`.
  It also confirms the Verrazzano amounts. No official page stating the 2026-01-04 date could be read.
- Still current on 2026-11-15? The Register of 2026-11-10 (Vol. XLVIII, Issue 45, cached
  `raw/nys_register/e4397fff94a195f9.pdf`) has no Triborough Bridge and Tunnel Authority rule making in it or in
  its action-pending index, and the Wikipedia revision of 2026-11-07 still shows the January 2026 rates. Register
  issues between February and October 2026 were **not** read one by one, so a 2026 change is ruled out by these two
  checks and by the roughly two-year cycle (previous change August 2023), not by exhaustive search.

## Resident programs (noted, not applied)

From the same adopted schedule:

- Verrazzano-Narrows: registered Staten Island residents, eligible vehicle, NYCSC E-ZPass: 4.19. E-Token for
  registered Staten Island residents: 5.97.
- Cross Bay and Marine Parkway: registered Rockaway Peninsula / Broad Channel residents, NYCSC E-ZPass: 1.83;
  E-Token for those residents: 2.50; E-Token for anyone: 3.86.

Not in the schedule, seen only in search results and Wikipedia (not verified against an official page, mta.info is
walled): a further Staten Island rebate to an effective 2.75; a Queens-resident rebate on the Cross Bay Bridge; a
Bronx-resident rebate on the Henry Hudson Bridge. These are rebate programs funded outside the toll rule.

## Looked at and not used

- data.ny.gov catalog (Socrata catalog API, queries "MTA Bridges and Tunnels toll rates", "toll rates bridges
  tunnels"): only traffic, crossings, summons and E-ZPass-usage datasets; **no toll-rate dataset**.
- nbcnewyork.com article on the fare and toll change: robots.txt disallows ClaudeBot / anthropic-ai, not fetched.
- Search-result snippets quoting mta.info agree with every figure above but were not used as a source.

## Not found

- An official page stating the 2026-01-04 start of collection (see above).
- Official text of the rebate programs beyond what the schedule prints.
- The Henry Hudson Bridge line applies only to parkway-authorized vehicles (schedule footnote); nothing else missing
  for passenger cars.

## To use

Rerun the drive lookups (owner of `scripts/tools/drive.py`); nothing under `scripts/` was changed or run here.
