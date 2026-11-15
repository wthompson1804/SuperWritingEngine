"""Write data/reference/taxes.csv: income and sales tax rules for NY, NJ, CT, PA, NYC, Yonkers, Philadelphia.

Every row was read by hand on 2026-11-15 from the official page or PDF cached under raw/*_tax/ and is stated
as the source states it. Rules only, no advice. retrieved_at comes from the cache index.
Run: python3 scripts/tools/taxes_reference.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import lib  # noqa: E402

OUT = lib.DATA / "reference" / "taxes.csv"

IT201 = "https://www.tax.ny.gov/pdf/current_forms/it/it201i.pdf"
Y203 = "https://www.tax.ny.gov/pdf/current_forms/it/y203i.pdf"
PUB718 = "https://www.tax.ny.gov/pdf/publications/sales/pub718.pdf"
TSBM = "https://tax.ny.gov/pdf/memos/income/m06_5i.pdf"
NJ_RATES = "https://www.nj.gov/treasury/taxation/pdf/current/njtaxratesch.pdf"
NJ_TABLES = "https://www.nj.gov/treasury/taxation/taxtables.shtml"
NJ_GIT3W = "https://www.nj.gov/treasury/taxation/pdf/pubs/tgi-ee/git3w.pdf"
NJ_NEWS = "https://www.nj.gov/treasury/news/2024/10082024.shtml"
NJ_SALES = "https://www.nj.gov/treasury/taxation/businesses/salestax/index.shtml"
NJ_UEZ = "https://www.nj.gov/treasury/taxation/ratechange/su-urban.shtml"
CT1040 = "https://portal.ct.gov/-/media/drs/forms/2025/income/2025-ct-1040-instructions_1225.pdf"
CT_SALES = "https://portal.ct.gov/drs/sales-tax/tax-information"
PA_PIT = "https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/personal-income-tax.html"
PA_TELE = "https://www.pa.gov/agencies/revenue/resources/tax-law-policies-bulletins-notices/telework-guidance"
PA_SALES = "https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/sales-use-and-hotel-occupancy-tax.html"
PHL_WAGE = "https://www.phila.gov/services/payments-assistance-taxes/business-taxes/wage-tax-employers/"
PHL_EARN = "https://www.phila.gov/services/payments-assistance-taxes/income-taxes/earnings-tax-employees/"

# jurisdiction, topic, rule, value, period, source_url, notes
ROWS = [
    # ---- resident income tax, single filer, the brackets that cover roughly $100k-$150k
    ("New York State", "resident_income_tax", "Single: taxable income over $13,900 to $80,650: $600 plus 5.5% of the excess over $13,900",
     "5.5%", "tax year 2025", IT201, "Form IT-201 instructions, New York State tax rate schedule"),
    ("New York State", "resident_income_tax", "Single: taxable income over $80,650 to $215,400: $4,271 plus 6% of the excess over $80,650",
     "6%", "tax year 2025", IT201, "the bracket that holds $100k-$150k of taxable income"),
    ("New York State", "resident_income_tax", "If New York adjusted gross income is more than $107,650 the tax is figured with the "
     "tax computation worksheets instead of the rate schedule alone", "", "tax year 2025", IT201,
     "the worksheets phase out the benefit of the lower brackets"),
    ("New Jersey", "resident_income_tax", "Single: taxable income over $40,000 to $75,000: income x 5.525% minus $1,492.50",
     "5.525%", "schedule for 2020 and after", NJ_RATES, "the state's tax tables page lists this schedule as '2020 and After'"),
    ("New Jersey", "resident_income_tax", "Single: taxable income over $75,000 to $500,000: income x 6.37% minus $2,126.25",
     "6.37%", "schedule for 2020 and after", NJ_RATES, "the bracket that holds $100k-$150k of taxable income"),
    ("New Jersey", "resident_income_tax", "Taxable income of $100,000 or more must use the rate schedules rather than the tax table",
     "", "current", NJ_TABLES, ""),
    ("Connecticut", "resident_income_tax", "Single: taxable income over $50,000 to $100,000: $2,000 plus 5.5% of the excess over $50,000",
     "5.5%", "tax year 2025", CT1040, "Form CT-1040 instructions, Table B Initial Tax Calculation"),
    ("Connecticut", "resident_income_tax", "Single: taxable income over $100,000 to $200,000: $4,750 plus 6.0% of the excess over $100,000",
     "6.0%", "tax year 2025", CT1040, "the bracket that holds most of $100k-$150k"),
    ("Connecticut", "resident_income_tax", "The tax calculation schedule also applies Table A (personal exemption), Table C (2% rate "
     "phase-out add-back), Table D (tax recapture) and Table E (personal tax credits), each depending on Connecticut AGI",
     "", "tax year 2025", CT1040, "the bracket rate alone is not the whole calculation"),
    ("Pennsylvania", "resident_income_tax", "Flat rate on taxable income of residents and nonresidents", "3.07%", "current", PA_PIT, ""),
    # ---- local income taxes
    ("New York City", "local_income_tax", "City resident tax, single: taxable income over $50,000: $1,813 plus 3.876% of the excess over "
     "$50,000 (lower brackets 3.078%, 3.762%, 3.819%)", "3.876%", "tax year 2025", IT201,
     "filed on the state return; applies to New York City residents"),
    ("Yonkers", "local_income_tax", "Yonkers resident income tax surcharge: 16.75% of New York State tax after the credits on the line 55 worksheet", "16.75% of state tax",
     "tax year 2025", IT201, "Form IT-201 instructions, line 55 worksheet"),
    ("Yonkers", "local_income_tax", "Yonkers nonresident earnings tax: 0.5% of wages earned in Yonkers after the exclusion on Form Y-203",
     "0.5%", "current form", Y203, "applies to people who work in Yonkers and live elsewhere"),
    ("Philadelphia", "local_income_tax", "Wage Tax / Earnings Tax, resident rate", "3.735%", "from July 1, 2026 (3.74% from July 1, 2025)",
     PHL_WAGE, "Wage Tax is withheld by employers; residents whose employer does not withhold pay the Earnings Tax at the same rate"),
    ("Philadelphia", "local_income_tax", "Wage Tax / Earnings Tax, non-resident rate (work done in Philadelphia)", "3.425%",
     "from July 1, 2026 (3.43% from July 1, 2025)", PHL_EARN, ""),
    ("New Jersey", "local_income_tax", "not_found: no municipal resident income tax appears in the New Jersey Division of Taxation pages captured",
     "", "", NJ_TABLES, "not confirmed by an explicit statement; looked in the tax tables and rate schedule pages"),
    ("Connecticut", "local_income_tax", "not_found: no municipal income tax appears in the CT-1040 instructions",
     "", "tax year 2025", CT1040, "not confirmed by an explicit statement"),
    ("Pennsylvania", "local_income_tax", "not_found: local earned income taxes outside Philadelphia were not collected",
     "", "", PA_PIT, "Pennsylvania municipalities and school districts levy their own earned income taxes; rates vary and were not gathered"),
    # ---- convenience of the employer
    ("New York State", "convenience_of_employer", "For a nonresident whose assigned or primary work location is in New York State, a normal "
     "work day spent at a home office outside New York counts as a day worked in New York unless the home office is a bona fide employer "
     "office; days worked outside New York count as such only when the work is done there of necessity, not convenience",
     "", "tax years from 2006", TSBM, "TSB-M-06(5)I: a home office is a bona fide employer office if it meets the primary factor, or at "
     "least 4 secondary factors and 3 other factors"),
    ("New Jersey", "convenience_of_employer", "A New Jersey resident taxed by New York on wages claims New Jersey's credit for income taxes "
     "paid to other jurisdictions (Schedule NJ-COJ), using only the income actually taxed by New York", "", "publication dated January 2026",
     NJ_GIT3W, "GIT-3W, Income From New York"),
    ("New Jersey", "convenience_of_employer", "Under a 2023 law, a resident who works remotely for an out-of-state employer and wins a final "
     "judgment against the other state's taxing of that income can claim a refundable credit equal to 50% of the additional New Jersey tax "
     "that results", "50% refundable credit", "tax years 2020 through 2023", NJ_NEWS, "Treasury release of October 8, 2024"),
    ("Connecticut", "convenience_of_employer", "For the credit for income taxes paid to qualifying jurisdictions (Schedule 2), income derived "
     "from a qualifying jurisdiction includes pay for work done from a home office in Connecticut for an employer in a jurisdiction that "
     "applies a convenience of the employer test", "", "tax year 2025", CT1040, "Form CT-1040 instructions, Schedule 2"),
    ("Pennsylvania", "convenience_of_employer", "A Pennsylvania resident required to telework full-time from home in Pennsylvania treats the "
     "pay as Pennsylvania-source income; Pennsylvania allows no resident credit on Pennsylvania-source income, even if the employer's state "
     "taxes that pay", "", "current guidance", PA_TELE, "Department of Revenue telework guidance, Personal Income Tax and Employer Withholding"),
    # ---- combined sales tax
    ("New York State", "sales_tax_combined", "State rate alone", "4%", "effective March 1, 2025", PUB718, "Publication 718 (2/25)"),
    ("New York City", "sales_tax_combined", "State + city + MCTD (Bronx, Kings, New York, Queens, Richmond)", "8.875%", "effective March 1, 2025", PUB718, ""),
    ("Nassau County NY", "sales_tax_combined", "State + local", "8.625%", "effective March 1, 2025", PUB718, ""),
    ("Suffolk County NY", "sales_tax_combined", "State + local", "8.75%", "effective March 1, 2025", PUB718, ""),
    ("Westchester County NY (except Yonkers)", "sales_tax_combined", "State + local; Mount Vernon, New Rochelle and White Plains are also 8.375%",
     "8.375%", "effective March 1, 2025", PUB718, ""),
    ("Yonkers", "sales_tax_combined", "State + local", "8.875%", "effective March 1, 2025", PUB718, ""),
    ("Rockland County NY", "sales_tax_combined", "State + local", "8.375%", "effective March 1, 2025", PUB718, ""),
    ("Putnam County NY", "sales_tax_combined", "State + local", "8.375%", "effective March 1, 2025", PUB718, ""),
    ("Dutchess County NY", "sales_tax_combined", "State + local", "8.125%", "effective March 1, 2025", PUB718, ""),
    ("Orange County NY", "sales_tax_combined", "State + local", "8.125%", "effective March 1, 2025", PUB718, ""),
    ("Ulster County NY", "sales_tax_combined", "State + local", "8%", "effective March 1, 2025", PUB718, ""),
    ("New Jersey", "sales_tax_combined", "Statewide rate on most goods and certain services", "6.625%", "current", NJ_SALES,
     "no local add-on appears on the page"),
    ("New Jersey", "sales_tax_combined", "Reduced rate charged by authorized sellers in Urban Enterprise Zones and Salem County",
     "3.3125%", "since January 1, 2018", NJ_UEZ, "applies to qualifying sales only"),
    ("Connecticut", "sales_tax_combined", "Statewide general rate; no additional local sales taxes", "6.35%", "current", CT_SALES,
     "special rates apply to certain sales"),
    ("Pennsylvania", "sales_tax_combined", "State rate", "6%", "current", PA_SALES, ""),
    ("Philadelphia", "sales_tax_combined", "State 6% + 2% local", "8%", "current", PA_SALES, "Allegheny County is 6% + 1%"),
]


def _retrieved() -> dict:
    out = {}
    for idx in lib.RAW.glob("*_tax/_index.jsonl"):
        for line in idx.read_text().splitlines():
            m = json.loads(line)
            if m.get("status") == 200:
                out[m["url"]] = m["retrieved_at"]
    return out


def main() -> None:
    seen = _retrieved()
    missing = sorted({r[5] for r in ROWS} - set(seen))
    if missing:
        raise SystemExit(f"no cached copy for: {missing}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["jurisdiction", "topic", "rule", "value", "period", "value_type", "source_url", "retrieved_at", "notes"])
        for j, topic, rule, value, period, url, notes in ROWS:
            vt = "not_found" if rule.startswith("not_found") else "found"
            w.writerow([j, topic, rule, value, period, vt, url, seen[url], notes])
    print(f"wrote {len(ROWS)} rows to {OUT.relative_to(lib.ROOT)}")


if __name__ == "__main__":
    main()
