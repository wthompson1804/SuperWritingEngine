#!/usr/bin/env python3
"""Turn the hand-written drafts in data/reference/scene_text_source.txt into the two scene-text CSVs.

The drafts are prose written by hand. Numbers are never typed: each one is a token that names a measured field,
so the builder fills the number in from the data and writes the matching evidence item. Nothing is generated; if a
token's value is missing the build stops, and the sentence has to be rewritten without it.

Tokens
  {alias}            the value, rounded the alias's usual way      {drive} -> 38
  {alias:how}        the value, rounded another way                {drive:r5} -> 40   (int 1dp r5 r10 pct mi mi0 str time12)
  {!alias OP value}  nothing is printed; the sentence is recorded as resting on this field, and the checker
                     re-tests it later                             {!bars==0}  {!b_tollok==False}  {!viol missing}
  {w10}  {mile}      the fixed wordings for the 800 m and 1,600 m search radii ("10-minute walk", "1 mile")
  [[ ... ]]          an optional stretch of text: dropped whole when any value inside it is missing or any hidden
                     test inside it fails, so a fact that is not in the data is simply not said
Lines
  === year: <label>      then  display: / tagline: / subhead: / host_intro: / points: / moment1: moment2: moment3: /
                               promise: / catch:   (scene and host_walkthrough are written out as the three moments)
  === hood: <hood_id>    then  host_intro: / scene: / good: / watch: , and optionally
      rules: Municipality|rule ; Municipality|rule      numbers typed in the prose must come from these summaries
      voices: theme, theme                              themes whose balance of comments the prose paraphrases
  A block may appear twice (the host voice sits in its own section of the file); the two are merged, and their
  rules: and voices: lines are added together.
Year tokens: p_... the experience page's figure strip, read from the fields the strip reads (site/data.json years[]:
  counts, medians, all_in_range, hood_ids); u_... medians and shares over the apartments shown; m_ + alias the median
  neighborhood for census traits (lifestyle_groups.csv), used only inside hidden tests.
Neighborhood tokens: {drive} {transit} {b_toll} {sqft} {pg_n} {pg_bldgs} {pg_mid} {pg_lo} {pg_hi} are the neighborhood
  page's figure strip; {rest} {bars} {cafes} {parkwalk} {dogpark} {super} {station} {water} {beach} {parkha} are
  door-distance facts: the median over the BUILDINGS SHOWN in the neighborhood (HOOD_BLDGS; the building's own figure
  when one is shown); {own_dog} {own_garage} {dog_any} are the share of the shown buildings with a dog area, a garage,
  any dog amenity (0 where nothing is shown); the other aliases in HOOD are census fields, worded as area-wide. For a
  neighborhood with nothing shown, the distance tokens fall back to lifestyle_groups.csv. Prices print to the nearest
  $10, minutes whole.
  {door}       "from the door" (one building shown) or "from most buildings here" (several)
  {w10}        the first one in a lead or a scene reads "10-minute walk of most buildings here" when several are shown
  {owndog} {owngarage}   "the building has its own dog area / garage", "every building here has ...", "some buildings
               here have their own dog area"; used inside [[ ]], dropped where no shown building has it
  {@nj:teaneck drive}    in an experience's text: that neighborhood's own figure
  === year: <label> @small   the draft used while the experience shows fewer than 8 apartments (@full otherwise)
  not:own_garage==1          in a points or subhead condition: holds when the test fails or there is no value

Run from the house-hunt folder: python3 scripts/build_scene_text.py && python3 scripts/check_scene_text.py
"""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_scene_text as C  # noqa: E402

ROOT = C.ROOT
SOURCE = ROOT / "data/reference/scene_text_source.txt"
LG, MB, GX = "data/lifestyle_groups.csv", "data/master_buildings.csv", "data/group_exchange.csv"
RULES, QUOTES = "data/reference/local_rules.csv", "data/voices/neighborhood_quotes.csv"
RULES2, QUOTES2 = "data/reference/local_rules_round2.csv", "data/voices/neighborhood_quotes_round2.csv"
TOLLS, PAGE_Y, PAGE_H, PAGE_U = C.TOLLS, C.PAGE + "#years", C.PAGE + "#neighborhoods", C.PAGE + "#units"
PAGE_B = C.PAGE + "#buildings"

# alias: (field in lifestyle_groups.csv, usual rounding)
HOOD = {
    "drive": ("drive_min", "int"), "transit": ("transit_to_parents_min", "int"),
    "viol": ("violent", "1dp"), "prop": ("property", "1dp"), "mvt": ("motor_vehicle_theft", "1dp"),
    "rest": ("restaurants_800m", "int"), "bars": ("bars_800m", "int"), "cafes": ("cafes_800m", "int"),
    "rest1600": ("restaurants_1600m", "int"), "brew": ("breweries_1600m", "int"), "music": ("music_1600m", "int"),
    "parkwalk": ("park_walk_min", "int"), "parkha": ("park_ha_800m", "int"),
    "dogpark": ("dog_park_m", "mi"), "water": ("open_water_m", "mi"), "beach": ("beach_m", "mi"),
    "super": ("supermarket_m_c", "mi"), "tj": ("trader_joes_m", "mi"), "vet": ("vet_m", "mi"),
    "station": ("train_station_m_c", "mi"),
    "nocar": ("no_car_share", "pct"), "detached": ("detached_house_share", "pct"),
    "bigbldg": ("big_building_share", "pct"), "renters": ("renter_share", "pct"),
    "alone": ("living_alone_share", "pct"), "newcomers": ("newcomer_share", "pct"), "wfh": ("wfh_share", "pct"),
    "young": ("age_25_34_share", "pct"), "pre1940": ("built_before_1940_share", "pct"),
    "post2010": ("built_since_2010_share", "pct"), "yrbuilt": ("median_year_built", "int"),
    "kids": ("households_with_kids_share", "pct"), "sqft": ("unit_sqft", "r10"),
    "police": ("police", "str"),
}
# alias: (field in master_buildings.csv, aggregation over the neighborhood's buildings, usual rounding)
BLDG = {
    "b_toll": ("toll_round_trip_ezpass", "median", "int"), "b_tollmax": ("toll_round_trip_ezpass", "max", "int"),
    "b_tollok": ("complete", "all_true", "str"),
    "b_station": ("train_station", "mode", "str"), "b_dogpark": ("dog_park_name", "mode", "str"),
    "b_park": ("park_name", "mode", "str"), "b_super": ("supermarket", "mode", "str"),
    "b_lasttrain": ("last_sat_departure", "mode", "time12"),
}
FROM_TOLLS = {"b_toll", "b_tollmax", "b_tollok"}       # read from data/enriched, not master_buildings.csv
# alias: (column of site/data.json#neighborhoods, usual rounding)
HOOD_PAGE = {"pg_lo": ("all_in_lo", "usd10"), "pg_hi": ("all_in_hi", "usd10"), "pg_n": ("shown", "int"),
             "pg_mid": ("all_in_median", "usd10"), "pg_bldgs": ("buildings", "int"),
             "pg_spread": ("all_in_spread", "int"),
             "pg_sqft": ("sqft_median", "r10"), "pg_safe": ("violent_pctile", "pct"),
             # the page's 1-to-5 comparison with the Queens median (3 = about the same, 5 = much better for her)
             "q_cost": ("vq_all_in", "int"), "q_sqft": ("vq_sqft", "int"), "q_drive": ("vq_drive_min", "int"),
             "q_food": ("vq_food_and_drink_nearby", "int"), "q_green": ("vq_walk_to_green", "int")}
# alias: (column of site/data.json#years, usual rounding)   the page's own tile figures
YEAR_PAGE = {
    # the figure strip of the experience page, read from the same fields the strip reads (2026-11-16, second fix: the
    # strip and the text once disagreed because the text recomputed these from the unit list)
    "p_allin": ("all_in", "usd10"), "p_sqft": ("sqft", "r10"), "p_drive": ("drive_min", "int"),
    "p_transit": ("transit_min", "int"), "p_rest": ("restaurants_800m", "int"), "p_parkwalk": ("park_walk_min", "int"),
    "p_places": ("shown", "int"), "p_hoods": ("n_hoods", "int"), "p_bldgs": ("buildings", "int"),
    "u_toll": ("toll_round_trip", "int"),
    "p_allin_lo": ("all_in_lo", "usd10"), "p_allin_hi": ("all_in_hi", "usd10"),
    "p_drive_lo": ("drive_min_lo", "int"), "p_drive_hi": ("drive_min_hi", "int"),
    "p_viol": ("violent_per_1000", "1dp"), "p_prop": ("property_per_1000", "1dp"),
    "p_near": ("nearest_name", "str"), "p_near_drive": ("nearest_drive_min", "int"),
    "q_cost": ("vq_all_in", "int"), "q_sqft": ("vq_sqft", "int"), "q_drive": ("vq_drive_min", "int"),
    "q_food": ("vq_food_and_drink_nearby", "int"), "q_green": ("vq_walk_to_green", "int"),
    # how the experience's apartments divide on the drive (D12), and its neighborhoods by name (D11)
    "hood_names": ("hood_names", "str"), "by_hood": ("by_hood", "str"), "close_n": ("close_n", "int"),
    "far_n": ("far_n", "int"), "close_share": ("close_share", "pct"), "close_areas": ("close_areas", "str"),
    "far_names": ("far_names", "str"), "close_drive_hi": ("close_drive_hi", "int"), "far_drive": ("far_drive", "int"),
    "far_toll": ("far_toll", "int"), "tollfree_share": ("tollfree_share", "pct"),
    "tollfree_areas": ("tollfree_areas", "str"), "toll_areas": ("toll_areas", "str"), "close_toll": ("close_toll", "int"),
    # the lowest and highest toll over the experience's apartments, and over each half of a split (N9)
    "u_toll_lo": ("toll_lo", "int"), "u_toll_hi": ("toll_hi", "int"), "u_toll_spread": ("toll_spread", "int"),
    "far_toll_lo": ("far_toll_lo", "int"), "far_toll_hi": ("far_toll_hi", "int"), "far_toll_spread": ("far_toll_spread", "int"),
    "close_toll_lo": ("close_toll_lo", "int"), "close_toll_hi": ("close_toll_hi", "int"),
    "close_toll_spread": ("close_toll_spread", "int"),
}
# alias: (column of site/data.json#units, aggregation over the year's shown units, usual rounding)
YEAR_UNITS = {
    # the experience's headline figures: the median over the units SHOWN in it (2026-11-16: these used to be read from
    # the page's tiles, which were computed over a wider set than the places listed)
    "u_tollmax": ("toll_rt", "max", "int"),
    "u_dogpark": ("dog_park_m", "median", "mi"), "u_super": ("supermarket_m", "median", "mi"),
    "u_cafes": ("cafes_800m", "median", "int"), "u_bars": ("bars_800m", "median", "int"),
    "u_rest1600": ("restaurants_1600m", "median", "int"), "u_bars1600": ("bars_1600m", "median", "int"),
    "u_garage": ("garage_or_covered", "mean", "pct"), "u_parkpub": ("parking_published", "mean", "pct"),
    "u_pool": ("pool", "mean", "pct"), "u_doorman": ("doorman", "mean", "pct"), "u_gym": ("gym", "mean", "pct"),
    "u_laundry": ("in_unit_laundry", "mean", "pct"), "u_n": ("listing_id", "count", "int"),
    "u_parkown": ("own_parking", "mean", "pct"), "u_owndog": ("own_dog_area", "mean", "pct"),
}
# In a neighborhood with places on the page, these aliases are computed from the SHOWN units (the median unit, or the
# commonest name), so the prose matches what the reader sees listed under it. alias: (column of #units, agg, rounding)
HOOD_SHOWN = {
    "rest": ("restaurants_800m", "median", "int"), "bars": ("bars_800m", "median", "int"),
    "cafes": ("cafes_800m", "median", "int"), "rest1600": ("restaurants_1600m", "median", "int"),
    "parkwalk": ("park_walk_min", "median", "int"), "dogpark": ("dog_park_m", "median", "mi"),
    "super": ("supermarket_m", "median", "mi"),
    "station": ("train_station_m", "median", "mi"),
    "b_tollmax": ("toll_rt", "max", "int"),
    "b_tollok": ("toll_complete", "all_true", "str"),
    "b_park": ("park", "mode", "str"), "b_dogpark": ("dog_park", "mode", "str"), "b_station": ("train_station", "mode", "str"),
    "s_open": ("open_gate", "mean", "pct"),               # share of them with a gate fact still to confirm
    "sqft_lo": ("sqft", "min", "r10"), "sqft_hi": ("sqft", "max", "r10"),   # so a plural "the apartments are large"
}                                                         # can be tested on the smallest one, not on the median
# Door-distance facts (independent check 4, D16). In a neighborhood with apartments on the page these describe the
# buildings SHOWN there: the median over the shown buildings, which is the building's own figure when one is shown.
# They used to be the neighborhood's frozen area profile (traits), which is measured over a wider sample than the
# apartments on the page (Fairfield "The supermarket is 0.9 miles away" for a building 0.3 miles from one).
# alias: (column of site/data.json#buildings, aggregation over the neighborhood's shown buildings, usual rounding)
HOOD_BLDGS = {
    "rest": ("restaurants_800m", "median", "int"), "bars": ("bars_800m", "median", "int"),
    "cafes": ("cafes_800m", "median", "int"), "rest1600": ("restaurants_1600m", "median", "int"),
    "parkwalk": ("park_walk_min", "median", "int"), "dogpark": ("dog_park_m", "median", "mi"),
    "super": ("supermarket_m", "median", "mi"), "station": ("train_station_m", "median", "mi"),
    "water": ("open_water_m", "median", "mi"), "beach": ("beach_m", "median", "mi"),
    "parkha": ("park_ha_800m", "median", "int"),
    "b_park": ("park", "mode", "str"), "b_dogpark": ("dog_park", "mode", "str"),
    "b_station": ("train_station", "mode", "str"),
    # what the shown buildings supply themselves (D6): the share of them with a dog park or dog run on the property,
    # with a garage or covered parking, with any parking of their own
    "own_dog": ("own_dog_area", "share", "pct"), "own_garage": ("own_garage", "share", "pct"),
    "own_parking": ("own_parking", "share", "pct"), "dog_any": ("dog_amenity_any", "share", "pct"),
    "rest_lo": ("restaurants_800m", "min", "int"), "rest_hi": ("restaurants_800m", "max", "int"),
    "nb": ("building_id", "count", "int"),                # buildings shown here: 0 where nothing is shown
    # the kind of the nearest station (train / subway / PATH / light rail; "mixed" where the shown buildings differ),
    # and the share of the shown buildings with a pet spa or dog wash (independent check 5: N3, N16)
    "stationkind": ("train_station_kind", "uniform", "str"), "pet_spa": ("pet_spa", "share", "pct"),
}
# ... and these are the neighborhood's figure strip, read from the fields the strip itself reads (never recomputed)
HOOD_STRIP = {"drive": ("drive_min", "int"), "transit": ("transit_min", "int"), "b_toll": ("toll_round_trip", "int"),
              # the lowest and highest toll among the buildings shown, and the gap between them (N9)
              "b_toll_lo": ("toll_lo", "int"), "b_toll_hi": ("toll_hi", "int"), "toll_spread": ("toll_spread", "int"),
              "sqft": ("sqft_median", "r10"), "s_n": ("shown", "int"), "s_bldgs": ("buildings", "int"),
              "in_queens": ("in_queens", "int")}
# The same for an experience: figures over the units shown in it (m_ + alias used to be the median neighborhood).
YEAR_SHOWN = {"bars": ("bars_800m", "int"), "cafes": ("cafes_800m", "int"),
              "rest1600": ("restaurants_1600m", "int"),
              "dogpark": ("dog_park_m", "mi"), "super": ("supermarket_m", "mi"), "station": ("train_station_m", "mi")}
CONVENTION = {
    "w10": ("10-minute walk", "restaurants_800m", "800 m radius, written as a 10-minute walk"),
    "mile": ("1 mile", "restaurants_1600m", "1,600 m radius, written as 1 mile"),
}
# numbers that are part of a field's definition, allowed wherever that field is cited
DEFINITION = {"built_before_1940_share": "before 1940", "built_since_2010_share": "since 2010",
              "age_25_34_share": "aged 25 to 34"}
JAMAICA = {"jv": ("jamaica_violent", "1dp"), "jp": ("jamaica_property", "1dp")}
TOKEN = re.compile(r"\{(!?)(?:@([a-z]{2}:[a-z0-9\-]+)\s+)?([a-z_0-9]+)(?::([a-z0-9]+))?\s*"
                   r"(?:(==|!=|<=|>=|<|>|missing|present)\s*([^}]*))?\}")
# Scope words (D16). A door-distance figure in a neighborhood with several shown buildings is the median building's,
# so the text says whose door it is: {door} prints "from the door" where one building is shown and "from most
# buildings here" where several are, and the first {w10} of a lead or a scene gains "of most buildings here".
# "stationkind" is read the same way (2026-11-17, Beacon Falls after its five apartments went): with nothing shown there
# is no building to take the kind of station from, so the token is missing and any test on it fails, as for a missing value
OWN_ALIASES = ("own_dog", "own_garage", "own_parking", "dog_any", "nb", "pet_spa", "stationkind")
# {owndog} and {owngarage}: what the shown buildings supply themselves (D6), in fixed words that follow the count of
# buildings. They print nothing-and-fail (so sit inside [[ ]]) when no shown building has it.
OWN_WORDS = {
    "owndog": ("own_dog", {"one": "the building has its own dog area", "all": "every building here has its own dog area",
                           "some": "some buildings here have their own dog area"}),
    "owngarage": ("own_garage", {"one": "the building has its own garage", "all": "every building here has a garage"}),
}
# {eachb} / {everyb}: "each building" / "every building" where several are shown (or none: the text is then about
# the area), "the building" where one is: advice to "ask each building" above a single building reads as an error.
BUILDING_WORDS = {"eachb": "each building", "everyb": "every building"}
# WORD TOKENS (independent check 5). Each prints fixed words chosen by a field, and records the test it rests on.
# {thestation} {astation} {thetrain}: the nearest station named by its kind (N3). The kind is the one every shown
#   building shares; where they differ the words are neutral ("the nearest station"). A neighborhood with nothing
#   shown measures commuter rail (lifestyle_groups.csv), so it is a train station.
STATION_TOKENS = {
    "thestation": {"train": "the train station", "subway": "the subway", "PATH": "PATH", "light rail": "the light rail stop",
                   "mixed": "the nearest station"},
    "astation": {"train": "a train station", "subway": "a subway station", "PATH": "a PATH station",
                 "light rail": "a light rail stop", "mixed": "a station"},
    "thetrain": {"train": "the train", "subway": "the subway", "PATH": "PATH", "light rail": "the light rail",
                 "mixed": "a station"},
}
# {fewbars} {fewcafes} {fewrest}: "few bars" where there are some and "no bars" where there are none (N15: "Few bars
#   are within a 10-minute walk" stood beside "There are no bars within a 10-minute walk" on Jamaica's page).
FEW_TOKENS = {"fewbars": ("bars", "bars"), "fewcafes": ("cafes", "cafés"), "fewrest": ("rest", "restaurants")}
# {tollcost} {tollshort}: "about $24 round trip with a New York E-ZPass", or, where the tolls of the buildings shown
#   differ by more than TOLL_SPREAD dollars, "about $24 to $43 round trip with a New York E-ZPass, depending on the
#   building" (N9). {tollshort} leaves the last clause off, for an icon point.
TOLL_TOKENS = ("tollcost", "tollshort")
TOLL_WORDS = "round trip with a New York E-ZPass"
WORD_TOKENS = set(STATION_TOKENS) | set(FEW_TOKENS) | set(TOLL_TOKENS)
CONTINUES = re.compile(r"\btoo(?=[,.;!]|$)|\b(?:also|as well)\b|^(?:And|But)\b")   # a sentence that leans on the one before it
DROP_MARK = "\x01"                                     # left where an optional sentence was dropped
SCOPE_ONE, SCOPE_MANY = "from the door", "from most buildings here"
W10_MANY = " of most buildings here"


def n_buildings(ctx):
    """Buildings shown in this neighborhood (0 when nothing is shown, or for an experience)."""
    if ctx["kind"] != "hood" or ctx["id"] not in C.shown_hoods():
        return 0
    return int(C.lookup(PAGE_H, "buildings", {"hood_id": ctx["id"]}) or 0)


def own_words(alias, ctx):
    """-> (words or None, evidence items) for {owndog} / {owngarage} in a neighborhood."""
    src_alias, words = OWN_WORDS[alias]
    if ctx["kind"] != "hood":
        return None, []
    f, agg, _ = HOOD_BLDGS[src_alias]
    share = C.lookup(PAGE_B, f, {"hood_id": ctx["id"]}, agg) or 0
    nb = n_buildings(ctx)
    key = "one" if share == 1 and nb == 1 else "all" if share == 1 else "some" if share > 0 else None
    if key is None or key not in words:
        return None, []
    test = ["==", "1"] if key in ("one", "all") else [">", "0"]
    evs = [{"field": f, "value": share, "source_file": PAGE_B, "row": {"hood_id": ctx["id"]}, "agg": agg, "holds_if": test},
           {"field": "buildings", "value": nb, "source_file": PAGE_H, "row": {"hood_id": ctx["id"]},
            "holds_if": ["==", "1"] if key == "one" else [">=", "2"]}]
    if key == "some":
        evs.append({"field": f, "value": share, "source_file": PAGE_B, "row": {"hood_id": ctx["id"]}, "agg": agg,
                    "holds_if": ["<", "1"]})
    return words[key], evs


def word_token(alias, ctx):
    """-> (words or None, evidence items) for a WORD_TOKENS alias in a neighborhood's text. None = nothing to say
    (the value is missing): inside [[ ]] the stretch is then dropped."""
    if ctx["kind"] != "hood":
        raise ValueError(f"{ctx['id']}: {{{alias}}} is for neighborhood text")
    row, shown = {"hood_id": ctx["id"]}, ctx["id"] in C.shown_hoods()
    if alias in STATION_TOKENS:
        if not shown:
            return STATION_TOKENS[alias]["train"], []
        kind = C.lookup(PAGE_B, "train_station_kind", row, "uniform")
        if kind is None:
            return None, []
        return STATION_TOKENS[alias][kind], [{"field": "train_station_kind", "value": kind, "source_file": PAGE_B, "row": row,
                                              "agg": "uniform", "holds_if": ["==", kind]}]
    if alias in FEW_TOKENS:
        src_alias, noun = FEW_TOKENS[alias]
        src, field, r, agg, _ = resolve(src_alias, ctx)
        value = C.lookup(src, field, r, agg)
        if C.is_missing(value):
            return None, []
        none = C.half_up(float(value)) == 0
        ev = {"field": field, "value": value, "source_file": src, "row": r, "holds_if": ["<", "0.5"] if none else [">=", "0.5"]}
        if agg:
            ev["agg"] = agg
        return ("no " if none else "few ") + noun, [ev]
    if alias in TOLL_TOKENS:
        def item(a):
            src, field, r, agg, how = resolve(a, ctx)
            value = C.lookup(src, field, r, agg)
            ev = {"field": field, "value": value, "source_file": src, "row": r}
            if agg:
                ev["agg"] = agg
            return value, ev, how
        mid, ev, how = item("b_toll")
        if C.is_missing(mid):
            return None, []
        spread = C.lookup(PAGE_H, "toll_spread", row) if shown else None
        if not C.is_missing(spread) and spread > C.TOLL_SPREAD:
            (lo, elo, hlo), (hi, ehi, hhi) = item("b_toll_lo"), item("b_toll_hi")
            a, b = C.transform(lo, hlo), C.transform(hi, hhi)
            elo.update({"transform": hlo, "shown": [a]})
            ehi.update({"transform": hhi, "shown": [b]})
            test = {"field": "toll_spread", "value": spread, "source_file": PAGE_H, "row": row, "holds_if": [">", str(C.TOLL_SPREAD)]}
            words = (f"up to about ${b} {TOLL_WORDS}" if a == "0" else f"about ${a} to ${b} {TOLL_WORDS}") + \
                (", depending on the building" if alias == "tollcost" else "")
            return words, [elo, ehi, test]
        ev.update({"transform": how, "shown": [C.transform(mid, how)]})
        evs = [ev]
        if shown:
            evs.append({"field": "toll_spread", "value": spread, "source_file": PAGE_H, "row": row,
                        "holds_if": ["<=", str(C.TOLL_SPREAD)]})
        return f"about ${C.transform(mid, how)} {TOLL_WORDS}", evs
    raise KeyError(alias)


def at_ctx(at, ctx):
    """{@ny:kew-gardens drive} in an experience's text reads that neighborhood's own figure."""
    return {"kind": "hood", "id": at} if at else ctx


def resolve(alias, ctx):
    """-> (source_file, field, row, agg, usual rounding)"""
    if alias in JAMAICA:
        f, how = JAMAICA[alias]
        return LG, f, {"hood_id": "ny:jamaica"}, None, how
    if ctx["kind"] == "hood":
        if alias in HOOD_BLDGS and ctx["id"] in C.shown_hoods():
            f, agg, how = HOOD_BLDGS[alias]
            return PAGE_B, f, {"hood_id": ctx["id"]}, agg, how
        if alias in OWN_ALIASES:                          # 0 where nothing is shown: no shown building supplies it
            f, agg, how = HOOD_BLDGS[alias]
            return PAGE_B, f, {"hood_id": ctx["id"]}, agg, how
        if alias in HOOD_STRIP and (ctx["id"] in C.shown_hoods() or alias.startswith("s_")):
            f, how = HOOD_STRIP[alias]
            return PAGE_H, f, {"hood_id": ctx["id"]}, None, how
        if alias in HOOD_SHOWN and (ctx["id"] in C.shown_hoods() or alias.startswith("s_")):
            f, agg, how = HOOD_SHOWN[alias]
            return PAGE_U, f, {"hood_id": ctx["id"]}, agg, how
        if alias in HOOD:
            f, how = HOOD[alias]
            return LG, f, {"hood_id": ctx["id"]}, None, how
        if alias in BLDG:
            f, agg, how = BLDG[alias]
            return (TOLLS if alias in FROM_TOLLS else MB), f, {"hood_id": ctx["id"]}, agg, how
        if alias in HOOD_PAGE:
            f, how = HOOD_PAGE[alias]
            return PAGE_H, f, {"hood_id": ctx["id"]}, None, how
    else:
        if alias in YEAR_PAGE:
            f, how = YEAR_PAGE[alias]
            return PAGE_Y, f, {"year_label": ctx["id"]}, None, how
        if alias in YEAR_UNITS:
            f, agg, how = YEAR_UNITS[alias]
            return PAGE_U, f, {"year_label": ctx["id"]}, agg, how
        row = {"group_label": ctx["id"], "safety_cut": False}
        for pre, agg in (("m_", "median"), ("max_", "max"), ("min_", "min")):
            if alias.startswith(pre) and alias[len(pre):] in YEAR_SHOWN:
                f, how = YEAR_SHOWN[alias[len(pre):]]
                return PAGE_U, f, {"year_label": ctx["id"]}, agg, how
            if alias.startswith(pre) and alias[len(pre):] in HOOD:
                f, how = HOOD[alias[len(pre):]]
                return LG, f, row, agg, how
        if alias == "n_hoods":
            return LG, "hood_id", row, "count", "int"
        if alias.startswith("x_") and alias[2:] in C.table(GX).columns:   # the page's own unit-weighted year figures
            return GX, alias[2:], {"group": ctx["id"]}, None, "int"
    raise KeyError(f"{ctx['id']}: unknown token {{{alias}}}")


PLURAL = {"restaurant": "restaurants", "bar": "bars", "café": "cafés", "brewery": "breweries", "minute": "minutes",
          "place": "places"}
COUNTED = re.compile(r"\b(?<![.,])(\d+) (restaurants?|bars?|cafés?|brewer(?:y|ies)|minutes?|places?)\b( is| are)?")


def agree(text):
    """The drafts type a noun after a number token, and the number moves with the data: make the noun (and an `is` /
    `are` right after it) agree, and write "no bars" for a count of 0."""
    def fix(m):
        n, noun, verb = int(m.group(1)), m.group(2), m.group(3)
        one = next(k for k, v in PLURAL.items() if noun in (k, v))
        if n == 0 and one not in ("minute", "place"):
            return f"no {PLURAL[one]}" + (" are" if verb else "")
        return f"{n} {one if n == 1 else PLURAL[one]}" + ((" is" if n == 1 else " are") if verb else "")
    text = COUNTED.sub(fix, text)
    return text[:1].upper() + text[1:]                # "no restaurants are ..." can now open the sentence


class Dropped(Exception):
    """A sentence whose hidden test on the page's shown units no longer holds."""


DROPPED = []


def drop_optional(raw, ctx):
    """[[ ... ]] stays only when every value inside it is present and every hidden test inside it holds."""
    gone = ""

    def keep(m):
        for t in TOKEN.finditer(m.group(1)):
            hidden, at, alias, _, op, operand = t.groups()
            if alias in CONVENTION or alias == "door" or alias in BUILDING_WORDS:
                continue
            if alias in OWN_WORDS:
                if own_words(alias, ctx)[0] is None:
                    return gone
                continue
            if alias in WORD_TOKENS:
                if word_token(alias, ctx)[0] is None:
                    return gone
                continue
            try:
                src, field, row, agg, _ = resolve(alias, at_ctx(at, ctx))
                value = C.lookup(src, field, row, agg)
            except LookupError:
                return gone
            if hidden and op:
                if not C.holds(value, [op] if op in ("missing", "present") else [op, operand.strip()]):
                    return gone
            elif C.is_missing(value):
                return gone
        return m.group(1)
    out, pos = [], 0
    for m in re.finditer(r"\[\[(.*?)\]\]", raw):
        # A dropped stretch that was a whole sentence of its own (it ends on a full stop and is not one half of an
        # either/or pair) leaves a mark, so render() can refuse a following sentence that leans on it ("... too").
        alone = m.group(1).rstrip().endswith((".", "!")) and not raw[m.end():].startswith("[[") and \
            not raw[:m.start()].endswith("]]")
        gone = DROP_MARK if alone else ""
        out.append(raw[pos:m.start()] + keep(m))
        pos = m.end()
    return "".join(out) + raw[pos:]


def render(raw, ctx, evidence, scope=False):
    """scope=True (a neighborhood's lead and scene): the first {w10} names whose walk it is when several buildings
    are shown."""
    raw = drop_optional(raw, ctx)
    out = []
    many = n_buildings(ctx) >= 2
    state = {"w10_scoped": not (scope and many)}
    held = []                                         # tokens are set aside so a full stop inside one cannot split a sentence

    def hold(m):
        held.append(m.group(0))
        return f"\x00{len(held) - 1}\x00"

    after_drop = False                                # the sentence before this one was dropped
    for sent in C.sentences(TOKEN.sub(hold, raw)):
        sent = re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], sent)
        if DROP_MARK in sent:
            after_drop = True
            sent = sent.replace(DROP_MARK, "").strip()
            if not sent:
                continue
        pending = []

        def sub(m):
            hidden, at, alias, how, op, operand = m.groups()
            if alias in CONVENTION:
                words, field, note = CONVENTION[alias]
                pending.append({"field": field, "value": note, "source_file": LG, "transform": "convention",
                                "shown": [words]})
                if alias == "w10" and not state["w10_scoped"]:
                    state["w10_scoped"] = True
                    pending.append({"field": "buildings", "value": n_buildings(ctx), "source_file": PAGE_H,
                                    "row": {"hood_id": ctx["id"]}, "holds_if": [">=", "2"]})
                    return words + W10_MANY
                return words
            if alias in BUILDING_WORDS:
                nb = n_buildings(ctx)
                if ctx["kind"] == "hood" and ctx["id"] in C.shown_hoods():
                    pending.append({"field": "buildings", "value": nb, "source_file": PAGE_H, "row": {"hood_id": ctx["id"]},
                                    "holds_if": ["==", "1"] if nb == 1 else [">=", "2"]})
                return "the building" if nb == 1 else BUILDING_WORDS[alias]
            if alias in OWN_WORDS:
                words, evs = own_words(alias, ctx)
                if words is None:
                    raise ValueError(f"{ctx['id']}: {{{alias}}} has nothing to say here; put it inside [[ ]]")
                pending.extend(evs)
                return words
            if alias in WORD_TOKENS:
                words, evs = word_token(alias, ctx)
                if words is None:
                    raise ValueError(f"{ctx['id']}: {{{alias}}} has no value here; put it inside [[ ]]")
                pending.extend(evs)
                return words
            if alias == "door":                           # whose door: the building's, or most buildings'
                if ctx["kind"] != "hood":
                    raise ValueError(f"{ctx['id']}: {{door}} is for neighborhood text")
                if ctx["id"] in C.shown_hoods():
                    pending.append({"field": "buildings", "value": n_buildings(ctx), "source_file": PAGE_H,
                                    "row": {"hood_id": ctx["id"]}, "holds_if": [">=", "2"] if many else ["==", "1"]})
                state["w10_scoped"] = state["w10_scoped"] or many
                return SCOPE_MANY if many else SCOPE_ONE
            src, field, row, agg, usual = resolve(alias, at_ctx(at, ctx))
            value = C.lookup(src, field, row, agg)
            ev = {"field": field, "value": value, "source_file": src, "row": row}
            extra = [DEFINITION[field]] if field in DEFINITION else []
            if agg:
                ev["agg"] = agg
            if hidden:
                if not op:
                    raise ValueError(f"{ctx['id']}: {{!{alias}}} needs a test, such as {{!{alias}==0}}")
                operand = operand.strip()
                test = [op] if op in ("missing", "present") else [op, operand]
                if not C.holds(value, test):
                    if src.startswith(C.PAGE):            # a claim about the places shown: the unit list moves with
                        raise Dropped(f"{ctx['id']}: {alias} is {value}, which fails {test}: {sent[:90]}")   # every rerun
                    raise ValueError(f"{ctx['id']}: {alias} is {value}, which fails {test}: {sent[:80]}")
                ev["holds_if"] = test
                if extra:
                    ev["transform"], ev["shown"] = usual, [C.transform(value, usual)] + extra
                pending.append(ev)
                return ""
            shown = C.transform(value, how or usual)
            if shown is None:
                raise ValueError(f"{ctx['id']}: {alias} is missing; rewrite without it: {sent[:80]}")
            ev["transform"], ev["shown"] = how or usual, [shown] + extra
            pending.append(ev)
            return shown

        try:
            text = TOKEN.sub(sub, sent)
        except Dropped as e:                              # the sentence is no longer true of the shown places:
            DROPPED.append(str(e))                        # it is left out (and listed), not printed
            after_drop = True
            continue
        if "{" in text or "}" in text:
            raise ValueError(f"{ctx['id']}: unparsed token in: {text}")
        text = re.sub(r"\s+([.,;])", r"\1", re.sub(r"\s{2,}", " ", text)).strip()
        text = agree(text)
        # When an optional sentence drops, the one after it must still stand alone (N16: "9 cafés are close too, ..."
        # opened a paragraph). A sentence that leans on a dropped one stops the build: rewrite it.
        if (after_drop or not out) and text and CONTINUES.search(text):
            raise ValueError(f"{ctx['id']}: a sentence that leans on the one before it (\"too\", \"also\", \"as well\", "
                             f"\"And\", \"But\") {'follows a dropped sentence' if after_drop else 'opens the text'}; "
                             f"it must stand alone: {text[:90]}")
        after_drop = False
        for ev in pending:
            evidence.append({"claim": text, **ev})
        out.append(text)
    return " ".join(out)


def attach_rules(ctx, spec, texts, evidence):
    cited = []
    for part in [p.strip() for p in spec.split(";") if p.strip()]:
        muni, rule = [x.strip() for x in part.split("|")]
        found = False
        for rules_file in (RULES, RULES2):
            row = {"municipality": muni, "rule": rule, "value_type": "found"}
            for s in C.lookup(rules_file, "summary", row, "any_row"):
                found = True
                cited.append({"claim": f"local rule cited: {muni}, {rule}", "field": "summary", "value": s,
                              "source_file": rules_file, "row": row, "agg": "any_row", "transform": "in_text",
                              "shown": []})
        if not found:
            raise ValueError(f"{ctx['id']}: no found rule {muni}|{rule}")
    covered = set()
    for ev in evidence:
        covered |= set(C.numbers_in(" ".join(ev.get("shown", []))))
    used = []
    for text in texts.values():
        for n in C.numbers_in(text):
            if n in covered:
                continue
            for ev in cited:
                if n in C.numbers_in(ev["value"]):
                    ev["shown"].append(n)
                    if ev not in used:
                        used.append(ev)
                    break
    # keep every rule summary that supplied a number, and the first summary of each cited rule
    seen = set()
    for ev in cited:
        k = (ev["source_file"], ev["row"]["municipality"], ev["row"]["rule"])
        if ev in used or k not in seen and not any(u["row"] == ev["row"] and u["source_file"] == ev["source_file"] for u in used):
            evidence.append(ev)
        seen.add(k)


def attach_voices(ctx, spec, texts, evidence):
    claim = " ".join(s for t in texts.values() for s in C.sentences(t) if C.VOICE_PHRASE.search(s))
    if not claim:                                     # the themes are listed, but no text paraphrases residents any more
        return
    for theme in dict.fromkeys(t.strip() for t in spec.split(",") if t.strip()):
        row, n = {"hood_id": ctx["id"], "theme": theme}, 0
        for quotes_file in (QUOTES, QUOTES2):
            counts = C.lookup(quotes_file, "sentiment", row, "sentiment_counts")
            if counts != "positive=0;mixed=0;negative=0":
                n += 1
                evidence.append({"claim": claim, "field": "sentiment", "value": counts, "source_file": quotes_file,
                                 "row": row, "agg": "sentiment_counts"})
        if not n:
            raise ValueError(f"{ctx['id']}: no quotes on {theme}")


def parse(path):
    blocks, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = re.match(r"=== sub: (year|hood)\.(\w+)", line)
        if m:                                             # conditional drafts for a section subhead
            cur = {"kind": "sub", "id": (m.group(1), m.group(2)), "rules": []}
            blocks.append(cur)
            continue
        m = re.match(r"=== points: (hood)", line)
        if m:                                             # conditional drafts for the icon points of a neighborhood
            cur = {"kind": "points", "id": m.group(1), "rules": []}
            blocks.append(cur)
            continue
        if cur is not None and cur["kind"] == "points":
            if not line.startswith("==="):
                head, sep, variants = line.partition("::")
                parts = [x.strip() for x in head.split("|")]
                if not sep or len(parts) < 3:
                    raise ValueError(f"cannot read point draft: {line[:80]}")
                topic, icon, conds = parts[0], parts[1], "|".join(parts[2:])
                cur["rules"].append((topic, icon, [c.strip() for c in conds.split(",") if c.strip()],
                                     [v.strip() for v in variants.split(" | ") if v.strip()]))
                continue
        if cur is not None and cur["kind"] == "sub":
            if not line.startswith("==="):
                conds, sep, variants = line.partition("::")
                if not sep:
                    raise ValueError(f"cannot read subhead draft: {line[:80]}")
                cur["rules"].append(([c.strip() for c in conds.split(",") if c.strip()],
                                     [v.strip() for v in variants.split("|") if v.strip()]))
                continue
        m = re.match(r"=== (year|hood): (.+?)(?:\s+@(small|full))?\s*$", line)
        if m:
            key = (m.group(1), m.group(2).strip())
            variant = m.group(3) or ""
            cur = next((b for b in blocks if (b["kind"], b["id"]) == key and b.get("variant", "") == variant), None)
            if cur is None:
                cur = {"kind": key[0], "id": key[1], "f": {}, "variant": variant}
                blocks.append(cur)
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if cur is None or not _:
            raise ValueError(f"cannot read line: {line[:80]}")
        if k in ("rules", "voices"):                  # a second block adds to the first block's citations
            sep = "; " if k == "rules" else ", "
            cur["f"][k] = sep.join(x for x in (cur["f"].get(k, ""), v) if x)
        elif k in cur["f"]:
            raise ValueError(f"{cur['id']}: '{k}:' appears twice")
        else:
            cur["f"][k] = v
    return blocks


COND = re.compile(r"^(?:v:(\w+):(positive|mixed|negative)|rule:(\w+)(?:~(.+))?|([a-z_0-9]+))\s*(==|!=|<=|>=|<|>)?\s*(.*)$")


def hood_rules(hood_id, rule, pattern=None):
    """Found local rules of this kind that apply to the neighborhood (and whose summary matches `pattern`, when one
    is given: "rule:overnight_parking~banned|prohibited") -> [(file, municipality, summary)]."""
    out = []
    for f in (RULES, RULES2):
        t = C.table(f)
        if "applies_to_hood_ids" not in t.columns:
            continue
        for r in t[(t.value_type == "found") & (t.rule == rule)].itertuples():
            ids = [x.strip() for x in str(r.applies_to_hood_ids).split(";")]
            if pattern and not re.search(pattern, str(r.summary), re.I):
                continue
            if any(hood_id == i or hood_id.startswith(i + "-") for i in ids if i and i != "nan"):
                out.append((f, r.municipality, r.summary))
    return out


NEGATED = {"==": "!=", "!=": "==", ">": "<=", ">=": "<", "<": ">=", "<=": ">"}
SUB_MIN_WORDINGS = 3                                   # wordings per condition in the "=== sub:" drafts
POINT_MIN_WORDINGS = 1                                 # wordings per line in the "=== points:" drafts
POINT_SHARE = 0.35                                     # a point wording on at most 8% of the neighborhoods
MAX_PLAIN_POINTS = 5                                   # plus the one warning
SUB_USED = {}                                          # (kind, section) -> Counter of wordings used so far in this build


def seeded(variants, key):
    import hashlib
    i = int(hashlib.sha1(key.encode()).hexdigest()[:8], 16) % len(variants)
    return variants[i:] + variants[:i]


def conds_hold(conds, ctx):
    """Do all the conditions of a draft line hold for this row? -> (True, evidence items) or (False, []).
    Every condition becomes an evidence item with a test, so the checker re-runs it after a data change."""
    evs = []
    for cond in conds:
        negate = cond.startswith("not:")                  # not:own_garage==1 holds when the test fails OR there is no
        cond = cond[4:] if negate else cond               # value (a neighborhood with nothing shown has no buildings)
        m = COND.match(cond)
        if not m:
            raise ValueError(f"cannot read condition '{cond}'")
        theme, sent, rule, pattern, alias, op, operand = m.groups()
        operand = operand.strip()
        if theme:                                     # v:parking:negative>=1  (residents' comments, both files)
            if ctx["kind"] != "hood":
                return False, []
            n, items = 0, []
            for qf in (QUOTES, QUOTES2):
                row = {"hood_id": ctx["id"], "theme": theme}
                counts = C.lookup(qf, "sentiment", row, "sentiment_counts")
                n += int(dict(x.split("=") for x in counts.split(";"))[sent])
                if counts != "positive=0;mixed=0;negative=0":
                    items.append({"field": "sentiment", "value": counts, "source_file": qf, "row": row,
                                  "agg": "sentiment_counts"})
            if not C.holds(n, [op or ">=", operand or "1"]):
                return False, []
            evs += items
        elif rule:                                    # rule:overnight_parking  (a found local rule applies here)
            found = hood_rules(ctx["id"], rule, pattern) if ctx["kind"] == "hood" else []
            if not found:
                return False, []
            f, muni, summary = found[0]
            evs.append({"field": "summary", "value": summary, "source_file": f,
                        "row": {"municipality": muni, "rule": rule, "value_type": "found"}, "agg": "any_row",
                        "transform": "in_text", "shown": []})
        else:
            try:
                src, field, row, agg, _ = resolve(alias, ctx)
                value = C.lookup(src, field, row, agg)
            except (KeyError, LookupError):
                if negate:
                    continue
                return False, []
            test = [op, operand]
            if negate:
                if not op or C.is_missing(value):
                    continue
                if C.holds(value, test):
                    return False, []
                test = [NEGATED[op], operand]
            if not op or not C.holds(value, test):
                return False, []
            ev = {"field": field, "value": value, "source_file": src, "row": row, "holds_if": test}
            if agg:
                ev["agg"] = agg
            evs.append(ev)
    return True, evs


def pick_sub(rules, ctx, salt, cap=None):
    """The first draft whose conditions all hold for this row -> (sentence, evidence). ('' , []) when none does.
    The wording is the first one, in an order seeded by the row's id, that has not reached `cap` uses in this build;
    when every wording of the matching draft has, the subhead stays empty (better than the same line once more)."""
    from collections import Counter
    used = SUB_USED.setdefault((ctx["kind"], salt), Counter())
    for conds, variants in rules:
        ok, evs = conds_hold(conds, ctx)
        if ok:
            for text in seeded(variants, f"{ctx['id']}|{salt}"):
                if cap is None or used[text] < cap:
                    used[text] += 1
                    extra = []
                    shown = render(text, ctx, extra) if "{" in text else text    # {eachb} and the like
                    return shown, [{"claim": shown, **e} for e in evs] + extra
            return "", []
    return "", []


def hood_points(rules, ctx, evidence, cap=None, lead="", lead_fields=()):
    """The icon points of a neighborhood, from the "=== points: hood" drafts -> [{icon, text}].
    Each draft line is `topic | icon | conditions :: wording | wording`. The first `warning` line whose conditions
    hold is the one honest catch; then, in the order written, the first matching line of each other topic, up to
    MAX_PLAIN_POINTS, skipping the topic the warning already covers. The warning is listed last."""
    from collections import Counter
    used = SUB_USED.setdefault(("hood", "points"), Counter())

    def take(topic, icon, conds, variants):
        ok, evs = conds_hold(conds, ctx)
        if not ok:
            return None
        order = seeded(variants, f"{ctx['id']}|point|{topic}")
        order = [v for v in order if cap is None or used[v] < cap] or order
        for raw in order:
            trial = []
            try:
                text = render(raw, ctx, trial)
            except (ValueError, LookupError, KeyError):
                continue
            said = icon != "warning" and any(e.get("shown") and e.get("transform") != "convention"
                                             and e.get("field") in lead_fields for e in trial)
            if text and not said and not C.shared_runs({"lead": [lead], "points": [text]}):   # never what the lead already says
                used[raw] += 1
                evidence.extend(trial + [{"claim": text, **e} for e in evs])
                return {"icon": icon, "text": text}
        return None

    warning, w_topic = None, None
    for topic, icon, conds, variants in rules:
        if icon == "warning":
            warning = take(topic, icon, conds, variants)
            if warning:
                w_topic = topic
                break
    points, topics = [], {w_topic}
    for topic, icon, conds, variants in rules:
        if icon == "warning" or topic in topics or len(points) >= MAX_PLAIN_POINTS:
            continue
        got = take(topic, icon, conds, variants)
        if got:
            points.append(got)
            topics.add(topic)
    return points + ([warning] if warning else [])


def written_points(spec, ctx, evidence):
    """`points: icon | text ;; icon | text` in an experience block -> [{icon, text}]. A point whose text renders
    empty (every optional stretch dropped) is left out."""
    out = []
    for part in [x.strip() for x in spec.split(";;") if x.strip()]:
        icon, _, raw = part.partition("|")
        text = render(raw.strip(), ctx, evidence)
        if text:
            out.append({"icon": icon.strip(), "text": text})
    return out


def written_moments(f, ctx, evidence):
    out = []
    for key, title in zip(MOMENTS, C.MOMENT_TITLES):
        icon, _, raw = f[key].partition("|")
        out.append({"icon": icon.strip(), "title": title, "text": render(raw.strip(), ctx, evidence)})
    return out


MOMENTS = ["moment1", "moment2", "moment3"]           # a weekday, Saturday night, Sunday with Mom and Dad
YEAR_COLS = {"display": "display_label", "tagline": "tagline", "subhead": "subhead", "promise": "promise", "catch": "catch",
             "host_intro": "host_intro"}
HOOD_COLS = {"scene": "scene", "good": "good_for_her", "watch": "watch_for", "host_intro": "host_intro"}


def pd_num(s):
    import pandas as pd
    return pd.to_numeric(s, errors="coerce").fillna(0)


def main(argv=None):
    # --data <path> / --out-suffix <text> (C.use_files): the same drafts over another page-data file, written to
    # scene_text_*<suffix>.csv. With --data a draft whose experience or neighborhood has no apartment in that file
    # is passed over. With no options the run is exactly as before.
    C._options(argv, "Fill the scene drafts with numbers from the data.")
    lg = C.table(LG).set_index("hood_id")
    years, hoods, errors, stale = [], [], [], []
    blocks = parse(SOURCE)
    absent = []
    # With --out-suffix, data/reference/scene_text_source<suffix>.csv (columns kind, id, field, draft) replaces single
    # fields of a draft where the sentence written for the whole page is not true of the subset. The replacement is a
    # draft like any other: tokens, hidden tests, every guard. A field "sub_<section>" replaces the section subhead the
    # "=== sub:" rules would pick (they are shared by every row, so no draft of the source file can replace them).
    over = SOURCE.with_name(SOURCE.stem + C.OUT_SUFFIX + ".csv") if C.OUT_SUFFIX else None
    if over is not None and over.exists():
        with open(over, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            hit = [b for b in blocks if b["kind"] == r["kind"] and b["id"] == r["id"]]
            if not hit:
                raise SystemExit(f"{over.name}: no draft for {r['kind']} {r['id']}")
            for b in hit:
                b["f"][r["field"]] = r["draft"]
        print(f"{len(rows)} draft fields replaced from {over.name}")
    if C.SUBSET:
        yt = C.table(PAGE_Y)
        on_page = set(yt[pd_num(yt["shown"]) > 0]["year_label"].astype(str))
        keep = lambda b: (b["kind"] not in ("year", "hood") or (b["id"] in C.shown_hoods() if b["kind"] == "hood"
                                                                 else C.year_key(b["id"]) in on_page))
        absent = sorted({b["id"] for b in blocks if not keep(b)})
        blocks = [b for b in blocks if keep(b)]
    subs = {b["id"]: b["rules"] for b in blocks if b["kind"] == "sub"}
    point_rules = next((b["rules"] for b in blocks if b["kind"] == "points"), [])
    for topic, icon, conds, variants in point_rules:
        if icon not in C.ICONS:
            errors.append(f"points [{topic}]: unknown icon '{icon}'")
        if len(set(variants)) < POINT_MIN_WORDINGS:
            errors.append(f"points [{topic} | {icon} | {', '.join(conds)}]: {len(set(variants))} wordings, wanted at "
                          f"least {POINT_MIN_WORDINGS}")
    SUB_USED.clear()
    DROPPED.clear()
    for (kind, section), rules in subs.items():
        for conds, variants in rules:
            if len(variants) < SUB_MIN_WORDINGS or len(set(variants)) < len(variants):
                errors.append(f"sub {kind}.{section} [{', '.join(conds)}]: {len(set(variants))} different wordings, "
                              f"wanted at least {SUB_MIN_WORDINGS}")
    n_hoods = sum(1 for b in blocks if b["kind"] == "hood" and b["id"] in lg.index)
    sub_cap = {"hood": int(n_hoods * C.SUB_SHARE), "year": None}
    point_cap = max(3, int(n_hoods * POINT_SHARE))
    closes = {}
    # An experience may have two drafts: "@small" is used while it shows fewer than C.SMALL_EXPERIENCE apartments
    # (written as what it is: a short note naming its neighborhoods), "@full" or the plain block otherwise.
    def wanted(b):
        if b["kind"] != "year":
            return True
        small = C.is_small_experience(b["id"])
        mine = [x for x in blocks if x["kind"] == "year" and x["id"] == b["id"]]
        has = {x.get("variant", "") for x in mine}
        want = "small" if small and "small" in has else ("full" if "full" in has else "")
        return b.get("variant", "") == want
    for b in blocks:
        if b["kind"] in ("sub", "points"):
            continue
        if not wanted(b):
            continue
        ctx, f, evidence = {"kind": b["kind"], "id": b["id"]}, b["f"], []
        cols = YEAR_COLS if b["kind"] == "year" else HOOD_COLS
        if b["kind"] == "hood" and b["id"] not in lg.index:       # the data no longer has this neighborhood
            stale.append(b["id"])
            continue
        try:
            lacking = [k for k in list(cols) + (MOMENTS + ["points"] if b["kind"] == "year" else []) if not f.get(k)]
            if lacking:
                raise ValueError(f"{b['id']}: no text for {lacking}")
            texts = {out: render(f[src], ctx, evidence, scope=src in ("host_intro", "scene"))
                     for src, out in cols.items()}
            if b["kind"] == "year":
                texts["about_points_json"] = json.dumps(written_points(f["points"], ctx, evidence), ensure_ascii=False)
                moments = written_moments(f, ctx, evidence)
                texts["day_moments_json"] = json.dumps(moments, ensure_ascii=False)
                # Two older columns the page reads only when it has no day moments. They are now the moments
                # themselves, so nothing unseen is left to drift: the walkthrough as three paragraphs, the scene as one.
                texts["host_walkthrough"] = "\n\n".join(m["text"] for m in moments)
                texts["scene"] = " ".join(m["text"] for m in moments)
            if b["kind"] == "hood":
                if f.get("rules"):
                    attach_rules(ctx, f["rules"], texts, evidence)
                if f.get("voices"):
                    attach_voices(ctx, f["voices"], texts, evidence)
                elif any(C.VOICE_PHRASE.search(t) for t in texts.values()):
                    raise ValueError(f"{b['id']}: paraphrases residents without a voices: line")
                closes[b["id"]] = "drive" if C.ends_on_drive(texts["host_intro"]) else "other"
            for section in C.SUB_SECTIONS[b["kind"]]:
                if ("sub_" + section) in f:              # a subhead given in the --out-suffix override table replaces
                    texts["sub_" + section] = render(f["sub_" + section], ctx, evidence)   # the one the rules pick
                    continue
                texts["sub_" + section], evs = pick_sub(subs.get((b["kind"], section), []), ctx, section,
                                                         sub_cap[b["kind"]])
                evidence += evs
            if b["kind"] == "hood":
                lead_sents = set(C.sentences(texts["host_intro"]))
                lead_fields = {e["field"] for e in evidence if e.get("claim") in lead_sents and e.get("shown")
                               and e.get("transform") not in ("convention", "in_text")}
                pts = hood_points(point_rules, ctx, evidence, point_cap, texts["host_intro"], lead_fields)
                texts["about_points_json"] = json.dumps(pts, ensure_ascii=False)
                # A one-sentence field whose only sentence the shown places no longer support falls back to the
                # matching icon point (the catch, or the first fact), which is chosen from the current data.
                for col, pick in (("watch_for", [x for x in pts if x["icon"] == "warning"]),
                                  ("good_for_her", [x for x in pts if x["icon"] != "warning"])):
                    if not texts[col].strip() and pick:
                        texts[col] = pick[0]["text"]
                        DROPPED.append(f"{ctx['id']}: {col} now reads as its icon point: {texts[col]}")
            problems, _ = C.check_row(b["kind"], b["id"], texts, evidence)
            errors += [f"{b['id']}: {p}" for p in problems]
        except (KeyError, ValueError, LookupError) as e:
            errors.append(str(e))
            continue
        ej = json.dumps(evidence, ensure_ascii=False)
        if b["kind"] == "year":
            years.append({"year_label": b["id"], **{c: texts[c] for c in C.COLUMNS["year"]}, "evidence_json": ej})
        else:
            hoods.append({"hood_id": b["id"], "hood_name": lg.loc[b["id"], "hood"],
                          "year_label": lg.loc[b["id"], "group_label"], **{c: texts[c] for c in C.COLUMNS["hood"]},
                          # "At a glance", from the buildings shown (D16); attached to the page as at_a_glance
                          "glance_json": json.dumps(C.glance(b["id"]), ensure_ascii=False),
                          "evidence_json": ej})
    for col, rows, key in (("host_intro", years, "year_label"), ("host_intro", hoods, "hood_id")):
        errors += C.check_repetition(col, {r[key]: r[col] for r in rows})
    if not C.SUBSET:                                     # the two page-wide spreads are not tested on a subset
        errors += C.check_closings("host_intro", {r["hood_id"]: r["host_intro"] for r in hoods})
        errors += C.check_sub_shares("hood", hoods)
    errors += C.check_leads([{**r, "evidence": json.loads(r["evidence_json"])} for r in hoods])
    from collections import Counter
    kinds = Counter(closes.values())
    for name, rows in ((C.YEARS, years), (C.HOODS, hoods)):
        if rows:
            with open(name, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    print(f"{len(years)} years, {len(hoods)} neighborhoods written; {len(errors)} problems")
    print(f"host_intro closes by kind: {dict(kinds.most_common())}")
    for section in C.SUB_SECTIONS["hood"]:
        c = Counter(r["sub_" + section] for r in hoods if r["sub_" + section])
        if c:
            text, n = c.most_common(1)[0]
            print(f"  sub_{section:20} {sum(c.values()):3} neighborhoods, {len(c):2} wordings, commonest {n} "
                  f"({n / len(hoods):.1%}): {text[:50]}")
    for e in errors:
        print("  ", e)
    if DROPPED:
        print(f"{len(DROPPED)} sentences left out because the places now shown no longer support them "
              f"(rewrite them in the drafts when the unit list settles):")
        for d in DROPPED:
            print("   ", d)
    if absent:
        print(f"passed over {len(absent)} drafts with no apartment in {C.PAGE_FILE.name}")
    if stale:
        print(f"skipped {len(stale)} drafts whose neighborhood is no longer in {LG}: {stale}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
