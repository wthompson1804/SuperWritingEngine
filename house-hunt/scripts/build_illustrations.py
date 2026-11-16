#!/usr/bin/env python3
"""Build the six experience illustrations (inline SVG) for the house-hunt page.

Writes:
  site/illustrations.json          keyed by years[].label, display_label and id
  site/illustrations_preview.html  standalone review page (all twelve drawings)

Idempotent: re-running overwrites both files. No network, no dependencies.
See docs/ILLUSTRATIONS.md for the style rules and how to add a scene.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Page tokens (site/index.html :root). Literal hex only: the page is single-theme light.
PAPER, INK, MUTED = "#FFF4F7", "#3A1630", "#7A5670"
BERRY, BERRY_D, ROSE, BLUSH = "#E0457B", "#C12C62", "#FFD3E1", "#FFE7EF"
BUTTER, BUTTER_D, MINT, MINT_INK = "#FFD86B", "#D9A91A", "#3FB98A", "#1B6F50"
PLUM, CORAL, WHITE, LINE = "#55234A", "#A5342B", "#FFFFFF", "#F3CADA"
# The one exception to the token palette: a soft blue-teal and its lighter tint, used for water and nothing else.
WATER, WATER_L = "#7FC4CF", "#BFE3E8"

# Identifying colour per experience id (docs/MAP_COMPONENT.md, in years[] order).
ACCENT = {"enclave": "#4192C8", "middle": "#AA0E0E", "new_water": "#F04288",
          "pre_car": "#AA42F0", "settled": "#324BAE", "space": "#AA8B0E"}

BW, BH, TH, LIFT = 360, 130, 200, 44  # banner size, tall height, sky added on top in the tall variant


def mix(a, b, t):
    """t of colour a over colour b, as a literal hex."""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x * t + y * (1 - t)) for x, y in zip(pa, pb))


def n(v):
    s = ("%.1f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class S:
    """A list of shapes; consecutive shapes with the same stroke width share one <g>."""

    def __init__(self):
        self.items = []

    def add(self, el, st=2):
        self.items.append((st, el))

    def r(self, x, y, w, h, f, rx=0, st=2, extra=""):
        self.add('<rect x="%s" y="%s" width="%s" height="%s"%s fill="%s"%s/>' % (
            n(x), n(y), n(w), n(h), (' rx="%s"' % n(rx)) if rx else "", f, extra), st)

    def c(self, x, y, r, f, st=2, extra=""):
        self.add('<circle cx="%s" cy="%s" r="%s" fill="%s"%s/>' % (n(x), n(y), n(r), f, extra), st)

    def e(self, x, y, rx, ry, f, st=2):
        self.add('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"/>' % (n(x), n(y), n(rx), n(ry), f), st)

    def p(self, d, f, st=2, extra=""):
        self.add('<path d="%s" fill="%s"%s/>' % (d, f, extra), st)

    def line(self, d, st=2, extra=""):
        self.add('<path d="%s" fill="none"%s/>' % (d, extra), st)

    def tex(self, d, f, step=9, dash=4):
        """Texture marks: short dashes along the lines in d (brick courses, paving joints)."""
        self.add('<path d="%s" fill="none" stroke="%s" stroke-width="1.5" stroke-dasharray="%s %s"/>'
                 % (d, f, n(dash), n(2 * step - dash)), 0)

    def out(self):
        res, cur = [], None
        for st, el in self.items:
            if st != cur:
                if cur:
                    res.append("</g>")
                if st:
                    res.append('<g stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round">'
                               % (INK, n(st)))
                cur = st
            res.append(el)
        if cur:
            res.append("</g>")
        return "".join(res)


# ---------- shared parts ----------

def grid(x, y, cols, rows, w, h, dx, dy, skip=()):
    """Path data for a grid of small rectangles (windows, bricks, dots)."""
    d = []
    for j in range(rows):
        for i in range(cols):
            if (i, j) in skip:
                continue
            d.append("M%s %sh%sv%sh%sz" % (n(x + i * dx), n(y + j * dy), n(w), n(h), n(-w)))
    return "".join(d)


def dots(pts, w=3, h=1.5):
    return "".join("M%s %sh%sv%sh%sz" % (n(x), n(y), n(w), n(h), n(-w)) for x, y in pts)


def bricks(x, y, w, h, step=9, row=7):
    """Path data for brick courses: horizontal lines, alternate rows offset. Draw with S.tex (dashed)."""
    d, j, yy = [], 0, y
    while yy < y + h:
        off = step if j % 2 else 0
        d.append("M%s %sh%s" % (n(x + off), n(yy), n(w - off)))
        yy += row
        j += 1
    return "".join(d)


def awning(s, x, y, w, h, c1, c2=WHITE, step=8):
    s.p("M%s %sh%sl3 %sh%sz" % (n(x), n(y), n(w), n(h), n(-w - 6)), c1)
    d = "".join("M%s %sh%sv%sh%sz" % (n(x + i), n(y + 1), n(step / 2), n(h - 2), n(-step / 2))
                for i in range(step // 2, int(w) - 3, step))
    s.p(d, c2, 0)


def tree(s, x, y, r, f, th=12):
    s.r(x - 1.5, y - th, 3, th, PLUM, 0, 2)
    s.c(x, y - th - r + 3, r, f)
    s.p(dots([(x - r / 2, y - th - r), (x + r / 4, y - th - r + 5), (x - r / 4, y - th - r / 3 + 4)], 3, 1.5),
        mix(WHITE, f, .5), 0)


def cloud(s, x, y, k=1.0, f=WHITE):
    s.p("M%s %sh%sa%s %s 0 0 0 %s %sa%s %s 0 0 0 %s %sa%s %s 0 0 0 %s %sz" % (
        n(x), n(y), n(34 * k), n(6 * k), n(6 * k), n(-3 * k), n(-11 * k), n(9 * k), n(9 * k), n(-16 * k), n(-4 * k),
        n(7 * k), n(7 * k), n(-13 * k), n(4 * k)) + "", f, 0)
    s.r(x - 4 * k, y - 11 * k, 12 * k, 11 * k, f, 5.5 * k, 0)


def lamp(s, x, y, h=44):
    s.line("M%s %sv%s" % (n(x), n(y), n(-h)))
    s.c(x, y - h - 4, 4, BUTTER)


def car(s, x, y, f, k=1.0, flip=False):
    s.add('<g transform="translate(%s %s) scale(%s %s)">'
          '<path d="M0 0v-4q0-6 6-6l5-7h14l6 7h5q4 0 4 6v4z" fill="%s"/>'
          '<path d="M10-11l3-4h5v4zM21-11v-4h3l3 4z" fill="%s" stroke-width="1"/>'
          '<circle cx="9" cy="-3" r="4" fill="%s"/><circle cx="31" cy="-3" r="4" fill="%s"/></g>'
          % (n(x), n(y), n(-k if flip else k), n(k), f, WHITE, PLUM, PLUM))


def dog(s, x, y, k=0.85, flip=False, leash=None):
    """The recurring small dog: white, caramel ear and patch, berry collar. (x, y) = ground under her."""
    if leash:
        lx, ly = leash
        hx = x + (-6 if flip else 6) * k
        s.line("M%s %sQ%s %s %s %s" % (n(hx), n(y - 11 * k), n((hx + lx) / 2), n(y - 2), n(lx), n(ly)), 1.5,
               ' stroke="%s"' % BERRY_D)
    s.add('<g transform="translate(%s %s) scale(%s %s)">'
          '<path d="M-11-11q-5-2-4-8" fill="none"/>'
          '<path d="M-10-7h4v7h-4zM3-7h4v7h-4z" fill="%s"/>'
          '<rect x="-12" y="-15" width="21" height="10" rx="5" fill="%s"/>'
          '<path d="M-8-15h7q0 5-4 5t-3-5z" fill="%s" stroke="none"/>'
          '<path d="M6-12l3 4" fill="none" stroke="%s" stroke-width="3"/>'
          '<path d="M5-17a6 6 0 0 1 11-2h3q3 0 3 3t-3 3h-4a6 6 0 0 1-10-4z" fill="%s"/>'
          '<path d="M5-21q-4 5 0 9q4-3 3-9z" fill="%s"/>'
          '<circle cx="12.500" cy="-18" r="1.200" fill="%s" stroke="none"/>'
          '<circle cx="21" cy="-16.500" r="1.500" fill="%s" stroke="none"/></g>'
          % (n(x), n(y), n(-k if flip else k), n(k), WHITE, WHITE, BUTTER_D, BERRY, WHITE, BUTTER_D, INK, INK))


def wrap(sky, body, label, tall):
    h = TH if tall else BH
    inner = body if not tall else '<g transform="translate(0 %d)">%s</g>' % (LIFT, body)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" role="img" aria-label="%s" '
            'preserveAspectRatio="xMidYMid slice"><rect x="0" y="0" width="%d" height="%d" fill="%s"/>%s</svg>'
            % (BW, h, label.replace('"', "&quot;"), BW, h, sky, inner)).replace(".500", ".5").replace(".200", ".2")


# ---------- the six scenes ----------
# Each returns (sky colour, S). Scene coordinates are the banner's (0..360 x 0..130); when tall is set the
# scene also draws sky extras above y=0 (down to -44) and a foreground strip from y=130 to y=156.

def walk(A, tall):
    """Evening on a dense pre-war block: narrow fronts, stoops, cafe tables under string lights, no road."""
    s = S()
    sky = mix(mix(A, PLUM, .72), PAPER, .5)
    lilac, brick, buff = mix(A, PAPER, .5), mix(CORAL, PAPER, .55), mix(BUTTER, PAPER, .7)
    pink, sage, stone = mix(BERRY, PAPER, .5), mix(MINT, PAPER, .42), mix(MUTED, PAPER, .4)
    st = [(22, 9), (118, 10), (138, 19), (226, 12), (246, 21), (342, 8)]
    if tall:
        st += [(40, -18), (96, -30), (170, -12), (330, -22)]
        s.c(276, -20, 10, WHITE, 0)
        s.c(280, -23, 9, sky, 0)
    s.p("".join("M%s %sa1.500 1.500 0 1 0 .1 0z" % p for p in st), WHITE, 0)
    G, F = 98, 74
    fronts = ((-6, 52, 22, ROSE), (46, 58, 6, lilac), (104, 46, 28, buff), (150, 60, 12, brick),
              (210, 50, 30, sage), (260, 56, 8, pink), (316, 50, 20, BLUSH))
    dark, lit = [], []
    for k, (x, w, top, f) in enumerate(fronts):
        s.r(x, top, w, G - top, f)
        s.r(x - 2, top - 4, w + 4, 6, WHITE, 1)
        rows = 4 if top <= 12 else 3
        cols = 3 if w >= 50 else 2
        pitch = (F - top - 4) / rows
        gap = (w - cols * 8) / (cols + 1)
        for j in range(rows):
            for i in range(cols):
                (lit if (i + 2 * j + k) % 3 == 0 else dark).append((round(x + gap + i * (8 + gap)), round(top + 6 + j * pitch)))
    s.tex(bricks(48, 9, 54, 62, 8, 8), mix(A, PAPER, .7), 8)
    s.tex(bricks(152, 15, 56, 56, 8, 8), mix(CORAL, PAPER, .72), 8)
    s.p(dots(dark, 8, 9), WHITE, 1.5)
    s.p(dots(lit, 8, 9), BUTTER, 1.5)
    # fire escape on the short buff front
    s.line("M109 45h36M109 59h36M109 45v-5h36v5M109 59v-5h36v5M117 59l20-14", 1.5)
    # 1 brownstone stoop
    s.r(12, 70, 12, 20, PLUM, 2)
    s.r(32, 76, 9, 13, BUTTER)
    s.p("M4 98v-4h4v-4h20v4h4v4z", stone)
    s.line("M5 94v-11M31 94v-11")
    # 2 cafe: lit window, solid awning
    s.r(52, 83, 32, 13, mix(BUTTER, WHITE, .6))
    s.r(88, 81, 11, 17, BERRY_D, 2)
    s.p("M50 72h50l3 9h-56z", BERRY)
    # 3 bar
    s.r(108, 80, 22, 15, mix(BUTTER, WHITE, .6))
    s.r(134, 78, 11, 20, PLUM, 2)
    # 4 stoop
    s.r(174, 70, 12, 20, PLUM, 2)
    s.p(dots([(156, 77), (194, 77)], 10, 12), WHITE)
    s.p("M166 98v-4h4v-4h20v4h4v4z", stone)
    s.line("M167 94v-11M193 94v-11")
    # 5 bookshop
    s.r(215, 84, 26, 12, WHITE)
    s.p(dots([(218, 89), (222, 87), (226, 90), (230, 88), (234, 89)], 3, 7), CORAL, 0)
    s.r(245, 81, 10, 17, MINT_INK, 2)
    s.p("M214 74h42l3 8h-48z", A)
    # 6 arched entrance with flower boxes
    s.p("M281 98V82a7 7 0 0 1 14 0v16z", PLUM)
    s.p(dots([(265, 78), (301, 78)], 10, 11), BUTTER)
    s.p(dots([(264, 89), (300, 89)], 12, 3.5), MINT)
    # 7 corner shop
    s.r(321, 84, 26, 12, mix(BUTTER, WHITE, .6))
    s.r(351, 81, 10, 17, PLUM, 2)
    s.p("M320 74h44l3 8h-50z", MINT)
    # wide sidewalk, no road
    s.r(-4, G, 368, 34 + (26 if tall else 0), PAPER)
    s.tex("".join("M-2 %sh364" % y for y in range(106, 156 if tall else 130, 8)), LINE, 21, 26)
    # string lights from the facades to a pole
    s.line("M132 122V60", 2.5)
    for x0, y0, x1, y1 in ((46, 68, 132, 61), (132, 61, 212, 70)):
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + 22
        s.line("M%s %sQ%s %s %s %s" % (n(x0), n(y0), n(mx), n(my), n(x1), n(y1)), 1.5)
        b = ""
        for i in range(1, 7):
            t = i / 7
            bx = (1 - t) ** 2 * x0 + 2 * t * (1 - t) * mx + t * t * x1
            by = (1 - t) ** 2 * y0 + 2 * t * (1 - t) * my + t * t * y1
            b += "M%s %sa2.800 2.800 0 1 0 .1 0z" % (round(bx), round(by) - 1)
        s.p(b, BUTTER, 1)
    # cafe tables
    for x, f in ((66, BERRY), (100, BUTTER_D), (162, BERRY)):
        s.line("M%s 122v-11M%s 122v-15M%s 114h6v8M%s 122v-15M%s 114h-6v8" % (x, x - 16, x - 16, x + 16, x + 16))
        s.e(x, 110, 9, 2.5, WHITE)
        s.c(x, 106.5, 2, f, 1)
    # street tree in its guard, bicycle
    tree(s, 262, 120, 13, MINT, 32)
    s.line("M255 120v-9h14v9M259.500 111v9M264.500 111v9", 1.5)
    s.p("M284 115l7-10h11l5 10M291 105l6 10h-13M302 105l-2-4h-4M307 115l-4-14h4", "none", 0,
        ' stroke="%s" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"' % BERRY)
    s.c(284, 115, 7, "none", 1.5)
    s.c(307, 115, 7, "none", 1.5)
    dog(s, 204, 124, .9, flip=True, leash=(179, 114))
    if tall:
        s.c(27, 141, 6, MINT)
        s.c(39, 140, 7, MINT)
        s.r(20, 143, 26, 10, CORAL, 2)
    return sky, s


def settled(A, tall):
    """Daytime avenue: two big six-storey brick blocks, courtyard gate, the el close by, bus stop, parked car."""
    s = S()
    sky = mix(A, PAPER, .13)
    brick, buff, steel = mix(CORAL, PAPER, .5), mix(BUTTER_D, PAPER, .38), mix(PLUM, PAPER, .55)
    road = mix(MUTED, PAPER, .32)
    cloud(s, 150, 14, .7)
    if tall:
        cloud(s, 60, -16, 1.1)
        cloud(s, 290, -22, .8)
    G = 100
    # far rooftops, then the elevated line with a train on it
    s.p("M210 100V72h22v-8h20v12h32v-10h26v14h56v20z", mix(A, PAPER, .28), 0)
    s.r(224, 12, 150, 28, A, 6)
    s.p(grid(233, 17, 7, 1, 13, 11, 19, 0), WHITE, 1.5)
    s.r(225, 33, 148, 3, BUTTER, 0, 0)
    s.r(212, 40, 160, 10, steel)
    # courtyard between the blocks: tree and iron gate
    s.c(111, 72, 13, MINT)
    s.p("M99 100V87a12 12 0 0 1 24 0v13z", mix(A, PAPER, .22))
    s.line("M105 100V78M111 100V75M117 100V78M99 88h24")
    # block one: red brick, roof tank, canopied entrance
    s.line("M67 18v-4M79 18v-4", 1.5)
    s.p("M65 14V9l8-5l8 5v5z", mix(BUTTER_D, PAPER, .5), 1.5)
    s.r(4, 22, 94, 78, brick)
    s.r(2, 18, 98, 6, WHITE, 1)
    s.tex(bricks(6, 25, 90, 60, 9, 6.2), mix(CORAL, PAPER, .68), 9)
    s.p(grid(11, 27, 6, 5, 9, 8, 15, 12.400), WHITE, 1.5)
    s.r(42, 87, 18, 13, PLUM)
    s.line("M51 87v13", 1.5)
    s.c(20, 96, 5, MINT)
    s.c(82, 96, 5, MINT)
    # block two: buff brick, greengrocer
    s.r(124, 26, 90, 74, buff)
    s.r(122, 22, 94, 6, WHITE, 1)
    s.r(180, 14, 16, 9, buff)
    s.tex(bricks(126, 35, 86, 50, 9, 5.800), mix(BUTTER_D, PAPER, .6), 9)
    s.p(grid(131, 31, 6, 5, 9, 7.500, 14.400, 11.600), WHITE, 1.5)
    s.r(130, 90, 50, 10, WHITE)
    s.r(194, 87, 12, 13, MINT_INK, 2)
    s.r(127, 85, 58, 4.500, MINT_INK, 1)
    # sidewalk and avenue
    s.r(-4, G, 368, 12, PAPER)
    s.r(-4, 112, 368, 20 + (26 if tall else 0), road)
    s.p(dots([(8, 121), (112, 121), (164, 121), (216, 121), (268, 121), (320, 121)], 22, 2), WHITE, 0)
    # entrance canopy out to the kerb
    s.p("M36 87h30l6 8h-42z", A)
    s.line("M31 95v11M71 95v11", 1.5)
    # fruit stand
    for i, f in enumerate((BERRY, BUTTER, MINT)):
        x = 129 + i * 18
        s.p("M%s 110v-8l16-3v11z" % x, mix(BUTTER_D, PAPER, .45), 1.5)
        s.p("M%s 100.500a3 3 0 1 0 .1 0zM%s 99.500a3 3 0 1 0 .1 0zM%s 96a3 3 0 1 0 .1 0z" % (x + 4, x + 11, x + 7.5),
            f, 1)
    # el columns in the street
    s.p("M232 50h9v62h-9zM326 50h9v62h-9z", steel)
    s.line("M221 50l11 13M252 50l-11 13M315 50l11 13M346 50l-11 13")
    # bus stop under the el
    s.r(254, 85, 46, 23, mix(A, WHITE, .14), 0, 1.5)
    s.line("M262 100h30M266 100v8M288 100v8")
    s.r(250, 80, 54, 5, A, 1)
    s.line("M312 110V78")
    s.c(312, 73, 5.500, BUTTER)
    car(s, 60, 126, BERRY, 1)
    dog(s, 214, 111, .85, flip=True)
    if tall:
        s.p(dots([(34, 140), (138, 140), (242, 140), (346, 140)], 22, 2), WHITE, 0)
        s.r(-4, 150, 368, 8, PAPER)
    return sky, s


def little(A, tall):
    """Small-city downtown: clock-tower station with a train, bakery, theatre with a blade sign, garage."""
    s = S()
    sky = mix(A, PAPER, .09)
    red, cream, stone = mix(A, PAPER, .32), mix(BUTTER, PAPER, .45), mix(MUTED, PAPER, .3)
    roof, road = mix(A, PAPER, .6), mix(MUTED, PAPER, .32)
    cloud(s, 98, 30, .8)
    if tall:
        cloud(s, 250, -16, 1.1)
        cloud(s, 120, -26, .7)
    G = 104
    # station hall, clock tower
    s.r(30, 74, 62, 30, stone)
    s.p("M26 76l6-10h58l6 10z", roof)
    s.p("M74 104V90a6 6 0 0 1 12 0v14z", WHITE)
    s.r(40, 30, 28, 74, stone)
    s.p("M36 32l18-21l18 21z", roof)
    s.c(54, 47, 10, WHITE)
    s.line("M54 47v-6M54 47l4 3")
    s.p("M48 104V90a6 6 0 0 1 12 0v14z", PLUM)
    s.p(grid(45, 66, 2, 1, 7, 10, 11, 0), WHITE, 1.5)
    # train nose under the platform canopy
    s.p("M-8 103V82h26l10 10v11z", MINT)
    s.p("M-8 86h24l6 6h-30z", WHITE, 1.5)
    s.r(-7, 96, 34, 2.500, BUTTER, 0, 0)
    s.c(24, 99.500, 1.800, WHITE, 1)
    s.line("M33 104V78")
    s.r(-8, 73, 46, 5, WHITE, 1)
    # bakery
    s.r(96, 54, 44, 50, mix(BERRY, PAPER, .3))
    s.r(94, 50, 48, 6, WHITE, 1)
    s.p(grid(103, 61, 2, 1, 11, 13, 19, 0), WHITE)
    s.r(100, 90, 24, 11, WHITE)
    s.p("M103 99q3.500-7 7 0zM113 99q3.500-7 7 0z", BUTTER_D, 1)
    s.r(128, 88, 9, 16, PLUM, 2)
    awning(s, 97, 79, 42, 8, BUTTER_D)
    # theatre: stepped front, blade sign, marquee with bulbs, posters
    s.p("M146 104V40h14v-8h52v8h14v64z", cream)
    s.p("M152 48h68M152 54h68", "none", 0, ' stroke="%s" stroke-width="1.5"' % mix(BUTTER_D, PAPER, .6))
    s.p("M178 6h16v52l-8 6l-8-6z", A)
    s.p("".join("M186 %sa2.200 2.200 0 1 0 .1 0z" % y for y in (10, 19, 28, 37, 46)), BUTTER, 0)
    s.r(150, 88, 72, 16, PLUM)
    s.p(grid(153, 90.500, 2, 1, 9, 12, 54, 0), BUTTER, 1.5)
    s.p("M155.500 93h4v7h-4z", BERRY, 0)
    s.p("M209.500 93h4v7h-4z", MINT, 0)
    s.p(grid(173, 90, 2, 1, 12, 14, 14, 0), A, 1.5)
    s.p("M140 84l9-15h74l9 15z", WHITE)
    s.r(140, 84, 92, 5, A)
    s.p("".join("M%s 72.500a1.800 1.800 0 1 0 .1 0z" % x for x in range(154, 220, 8))
        + "".join("M%s 79a1.800 1.800 0 1 0 .1 0z" % x for x in range(150, 224, 8)), BUTTER_D, 0)
    # mid-rise with the garage entrance
    s.r(244, 20, 124, 84, red)
    s.r(242, 16, 128, 6, WHITE, 1)
    s.tex(bricks(246, 24, 120, 54, 9, 6.500), mix(A, PAPER, .48), 9)
    s.p(grid(252, 28, 6, 4, 11, 8, 18, 13), WHITE)
    s.r(244, 79, 124, 3, WHITE, 0, 0)
    s.r(253, 87, 14, 17, PLUM, 2)
    s.p("M249 87h22l-3-5h-16z", BUTTER)
    s.r(286, 84, 58, 20, PLUM, 2)
    s.p(grid(288, 85.500, 8, 1, 4, 3.500, 7.200, 0), BUTTER, 0)
    # sidewalk, main street, driveway
    s.r(-4, G, 368, 14, PAPER)
    s.r(-4, 118, 368, 14 + (26 if tall else 0), road)
    s.p(dots([(16, 124), (80, 126), (160, 123), (236, 126), (336, 127)], 12, 1.5), WHITE, 0)
    s.p("M284 104h62l8 14h-78z", road, 0)
    # her car, seen from behind, pulling in
    s.p("M303 109v6h6v-6zM321 109v6h6v-6z", PLUM, 1.5)
    s.p("M300 110v-11q0-3 3-3h1l3-8h16l3 8h1q3 0 3 3v11z", BERRY)
    s.p("M308 95l2-5h10l2 5z", WHITE, 1)
    s.p("M302 100h5v3h-5zM323 100h5v3h-5z", BUTTER, 1)
    # street lamp with flower baskets
    s.line("M234 116V66M225 76h18")
    s.c(234, 62, 4.500, BUTTER)
    for x in (225, 243):
        s.c(x, 77, 4, MINT, 1.5)
        s.p("M%s 78h9a4.500 4.500 0 0 1-9 0z" % n(x - 4.5), CORAL, 1.5)
    s.p(dots([(223, 74), (227, 76), (241, 76), (245, 74)], 2, 2), BERRY, 0)
    dog(s, 196, 116, .85)
    if tall:
        s.r(-4, 136, 368, 22, PAPER)
        s.tex("M8 142h352M8 150h352", LINE, 15, 20)
    return sky, s


def fresh(A, tall):
    """New towers on the water: glass panels, roof terrace, open door, moving boxes, skyline reflected."""
    s = S()
    sky = mix(A, PAPER, .12)
    glass, brick = mix(MINT, WHITE, .18), mix(BERRY_D, PAPER, .45)
    box = mix(BUTTER_D, PAPER, .55)
    s.c(312, 16, 10, BUTTER, 0)
    cloud(s, 190, 18, .8)
    if tall:
        cloud(s, 60, -18, 1.1)
        cloud(s, 250, -26, .7)
    # skyline across the water, the water, the skyline's reflection
    sk = "M156 64V50h12V36h14v10h10V26h12v14h14v-8h10v20h14V20h10v24h12V32h16v14h12V40h12v10h14v-6h18v20z"
    s.p(sk, mix(A, PAPER, .36), 0)
    s.r(-4, 64, 368, 44, WATER, 0, 0)
    s.p(sk, WATER_L, 0, ' transform="matrix(1 0 0 -.5 0 96)"')
    s.p("M150 69.500h214M150 75.500h214M150 81.500h214", "none", 0, ' stroke="%s" stroke-width="1.5"' % WATER)
    s.p(dots([(302, 67), (306, 72), (300, 77), (308, 82)], 14, 1.5) + dots([(176, 87), (236, 90), (330, 88)], 10, 1.5),
        WHITE, 0)
    s.p("M160 78q3-3 6 0t6 0M204 84q3-3 6 0t6 0M262 80q3-3 6 0t6 0M334 76q3-3 6 0t6 0M290 90q3-3 6 0t6 0",
        "none", 0, ' stroke="%s" stroke-width="1.5"' % WHITE)
    # sailboat
    s.p("M252 78h22l-4 6h-14z", WHITE, 1.5)
    s.p("M263 76v-18l10 18z", BERRY, 1.5)
    # glass tower
    s.r(10, 4, 66, 100, glass)
    s.r(10, 4, 14, 100, brick)
    s.p(grid(25, 5, 2, 4, 12, 11, 26, 24) + grid(38, 17, 2, 3, 12, 11, 26, 24), WHITE, 0)
    s.p("M24 16h52M24 28h52M24 40h52M24 52h52M24 64h52M24 76h52M24 88h52M37 4v84M50 4v84M63 4v84", "none", 0,
        ' stroke="%s" stroke-width="1.5"' % mix(MINT, WHITE, .65))
    s.line("M24 88h52M24 4v100")
    # brick-and-glass tower with a roof terrace
    s.p("M106 13q12-11 24 0z", BERRY)
    s.line("M118 26V13")
    s.c(92, 22, 4.500, MINT)
    s.c(144, 22, 4.500, MINT)
    s.line("M86 26v-7h64v7M102 19v7M134 19v7", 1.5)
    s.r(84, 30, 68, 74, brick)
    s.r(82, 26, 72, 6, WHITE, 1)
    s.p(grid(91, 37, 3, 3, 15, 10, 20, 14), glass)
    for y in (47, 61, 75):
        s.r(152, y - 8, 18, 8, WHITE, 0, 1.5)
    # open front door
    s.r(106, 82, 22, 22, mix(BUTTER, WHITE, .55))
    s.p("M106 82l-10 3v21l10-2z", PLUM)
    s.p("M100 82h34l-3-6h-28z", A)
    # walkway and railing
    s.r(-4, 104, 368, 28 + (26 if tall else 0), PAPER)
    s.tex("".join("M0 %sh364" % y for y in range(112, 156 if tall else 130, 8)), LINE, 21, 26)
    s.p("M170 104V92h194M196 92v12M222 92v12M248 92v12M274 92v12M300 92v12M326 92v12M352 92v12M170 98h194", "none")
    lamp(s, 226, 118, 46)
    # moving boxes by the door
    s.r(138, 90, 15, 12, box)
    s.r(134, 102, 23, 18, box)
    s.c(74, 96, 5, MINT, 1.5)
    s.c(82, 93, 5.500, MINT, 1.5)
    s.r(66, 100, 22, 20, box)
    s.p("M66 106h22M134 108h23M138 95h15", "none", 1.5)
    s.p("M77 100v10M145.500 102v10M145.500 90v7", "none", 0, ' stroke="%s" stroke-width="3"' % BERRY)
    # bench
    s.p("M262 110h30M262 116h30M266 116v6M288 116v6", "none", 2.5)
    dog(s, 196, 124, .9, flip=True)
    if tall:
        s.r(296, 140, 30, 10, mix(A, PAPER, .5), 2)
        s.c(304, 137, 6, MINT)
        s.c(316, 136, 7, MINT)
    return sky, s


def space(A, tall):
    """Older suburb, wide sky: the home-office bay window and balcony, big lawn, big trees, small car park."""
    s = S()
    sky = mix(A, PAPER, .11)
    lawn, buff, lot = mix(MINT, PAPER, .42), mix(A, PAPER, .34), mix(MUTED, PAPER, .3)
    s.c(322, 20, 11, BUTTER, 0)
    cloud(s, 56, 24, 1)
    cloud(s, 190, 16, .8)
    if tall:
        cloud(s, 150, -16, 1.2)
        cloud(s, 300, -24, .7)
    # far tree line and lawn
    s.p("M-4 92V72q14-10 26 0q12-12 26-2q16-8 28 2h150q14-12 30-2q14-10 28 0q14-8 26 2q16-10 30 0v20z",
        mix(MINT, PAPER, .62), 0)
    s.r(-4, 88, 368, 44 + (26 if tall else 0), lawn, 0, 0)
    s.p(dots([(10, 104), (36, 126), (112, 124), (150, 112), (190, 122), (130, 104), (214, 108)], 2, 4),
        mix(MINT, PAPER, .75), 0)
    tree(s, 30, 102, 22, MINT, 20)
    tree(s, 342, 94, 12, mix(MINT, PAPER, .8), 14)
    # the low building
    s.r(64, 38, 176, 60, buff)
    s.r(60, 33, 184, 7, WHITE, 1)
    s.p("M64 65h176", "none", 0, ' stroke="%s" stroke-width="1.5"' % mix(A, PAPER, .55))
    s.p(grid(71, 46, 1, 2, 14, 12, 0, 30) + grid(188, 46, 2, 1, 16, 12, 26, 0) + "M218 76h12v12h-12z", WHITE)
    # balcony over the bay
    s.r(118, 44, 26, 21, WHITE)
    s.line("M131 44v21", 1.5)
    s.c(160, 54, 5, MINT, 1.5)
    s.r(156, 57, 8, 7, BERRY, 0, 1.5)
    s.p("M92 64V52h80v12M102 52v12M112 52v12M122 52v12M132 52v12M142 52v12M152 52v12M162 52v12", "none", 1.5)
    # the big bay window: desk, screen, lamp, plant
    s.r(94, 66, 76, 29, mix(BUTTER, WHITE, .3))
    s.r(125, 86, 12, 9, MUTED, 2, 0)
    s.r(110, 83, 46, 3, CORAL, 0, 0)
    s.p("M113 86v9M153 86v9", "none", 0, ' stroke="%s" stroke-width="2"' % CORAL)
    s.r(122, 70, 18, 11, PLUM, 1.5, 0)
    s.r(130, 81, 2, 2, PLUM, 0, 0)
    s.p("M149 83v-7M144 76h10l-2-6h-6z", BUTTER_D, 1)
    s.c(102, 78, 5.500, MINT, 1)
    s.p("M98 95v-9h8v9z", BERRY, 1)
    s.r(90, 63, 84, 4, WHITE, 1)
    s.r(90, 94, 84, 4, WHITE, 1)
    # entrance
    s.r(194, 74, 16, 24, PLUM, 2)
    s.p("M188 74h28l-3-5h-22z", A)
    # path, small car park with marked spaces, her car
    s.p("M196 98h12l34 12h-18z", PAPER, 0)
    s.p("M256 102h108v28h-124z" if not tall else "M256 102h108v54h-139z", lot)
    s.p("M274 104l-6 22M302 104l-3 22M330 104v22M358 104l2 22", "none", 0, ' stroke="%s" stroke-width="2"' % WHITE)
    tree(s, 268, 100, 18, MINT, 18)
    car(s, 271, 123, BERRY, .68)
    car(s, 329, 123, WHITE, .68)
    # dog running after her ball, lawn all round
    s.line("M40 109h9M35 115h11M41 121h7", 1.5)
    s.c(110, 105, 3.500, BERRY, 1.5)
    dog(s, 70, 122, .9)
    if tall:
        s.p(dots([(30, 140), (70, 148), (110, 138), (16, 150), (170, 144)], 2, 4), mix(MINT, PAPER, .75), 0)
        s.c(140, 146, 2.5, WHITE, 0)
        s.c(84, 150, 2.5, BUTTER, 0)
    return sky, s


def quiet(A, tall):
    s = S()
    sky = mix(mix(A, PLUM, .62), PAPER, .5)
    glow = mix(BERRY, PAPER, .32)
    lawn, hedge = mix(MINT_INK, PAPER, .5), mix(MINT_INK, PAPER, .75)
    apt, lit, dark = mix(A, PAPER, .5), BUTTER, mix(PLUM, PAPER, .7)
    halo = ' fill-opacity=".35"'
    s.r(-4, 56, 368, 50, glow, 0, 0)
    s.r(-4, 46, 368, 10, mix(glow, sky, .5), 0, 0)
    # moon and stars
    s.c(300, 22, 10, WHITE, 0)
    s.c(304, 19, 9, sky, 0)
    st = [(40, 14), (96, 26), (150, 10), (214, 20), (250, 36), (340, 44), (20, 38)]
    if tall:
        st += [(60, -20), (130, -30), (200, -14), (270, -26), (330, -8), (16, -8)]
    s.p("".join("M%s %sa1.500 1.500 0 1 0 .1 0z" % p for p in st), WHITE, 0)
    # dark trees behind
    s.p("M-4 104V70q10-14 22-4q10-16 24-2v40zM92 104V66q12-14 22 0v38zM226 104V62q14-16 26-2q12-10 20 4v40z"
        "M334 104V64q14-14 30 0v40z", mix(MINT_INK, sky, .55), 0)
    G = 104
    # left house
    s.r(14, 66, 66, 38, ROSE)
    s.p("M8 68l39-28l39 28z", mix(CORAL, PAPER, .6))
    s.p(grid(22, 74, 1, 1, 12, 12, 0, 0), lit)
    s.r(40, 52, 12, 10, lit)
    s.r(60, 80, 12, 24, PLUM, 2)
    s.p("M50 80h30v-4h-30zM52 80v24M78 80v24", WHITE)
    s.c(56, 86, 7, BUTTER, 0, halo)
    s.c(56, 86, 2.5, BUTTER, 1.5)
    # apartment building tucked between
    s.r(112, 30, 112, 74, apt)
    s.r(110, 26, 116, 6, WHITE, 1)
    s.p(grid(121, 38, 6, 3, 11, 10, 17, 16, skip=((1, 0), (4, 0), (0, 1), (3, 1), (2, 2), (5, 2))), dark)
    s.p(grid(121, 38, 6, 3, 11, 10, 17, 16, skip=((0, 0), (2, 0), (3, 0), (5, 0), (1, 1), (2, 1), (4, 1), (5, 1),
                                                  (0, 2), (1, 2), (3, 2), (4, 2))), lit)
    s.r(159, 86, 18, 18, PLUM, 2)
    s.p("M153 86h30l-3-5h-24z", WHITE)
    s.c(150, 91, 7, BUTTER, 0, halo)
    s.c(150, 91, 2.5, BUTTER, 1.5)
    s.c(186, 91, 7, BUTTER, 0, halo)
    s.c(186, 91, 2.5, BUTTER, 1.5)
    s.p(grid(121, 90, 2, 1, 11, 9, 17, 0) + grid(196, 90, 1, 1, 18, 9, 0, 0), dark)
    # right house
    s.r(262, 70, 70, 34, mix(BUTTER, PAPER, .6))
    s.p("M256 72l22-24h38l22 24z", mix(A, PLUM, .45))
    s.r(290, 54, 14, 10, lit)
    s.p(grid(304, 78, 2, 1, 10, 12, 13, 0), lit)
    s.r(272, 82, 12, 22, BERRY_D, 2)
    s.p("M264 82h30v-4h-30zM266 82v22M292 82v22", WHITE)
    s.c(288, 88, 7, BUTTER, 0, halo)
    s.c(288, 88, 2.5, BUTTER, 1.5)
    # lawns, hedges, pavement, street
    s.r(-4, G, 368, 10, lawn, 0, 0)
    s.p("M-4 104h368", "none")
    s.p("M228 106q0-10 11-10t11 10zM336 106q0-9 10-9t10 9z", hedge)
    s.p("M62 104h8l-2 10h-10zM162 104h12l2 10h-16zM274 104h8l2 10h-10z", PAPER, 0)
    s.r(-4, 113, 368, 6, PAPER)
    s.r(-4, 119, 368, 13 + (26 if tall else 0), mix(PLUM, PAPER, .42))
    s.p(dots([(30, 125), (120, 127), (210, 125), (300, 127)], 14, 1.5), mix(PLUM, PAPER, .2), 0)
    # mailbox at the kerb
    s.line("M98 119v-12", 3)
    s.p("M86 108v-7q0-7 7-7h12q5 0 5 5v9z", A)
    s.p("M104 99v-9h6v4h-6", BERRY, 1.5)
    dog(s, 204, 117, .85)
    if tall:
        s.p(dots([(60, 138), (170, 141), (270, 138)], 14, 1.5), mix(PLUM, PAPER, .2), 0)
        s.r(-4, 146, 368, 5, PAPER)
        s.r(-4, 151, 368, 8, lawn, 0, 0)
    return sky, s


SCENES = {
    "pre_car": (walk, "Evening on a dense old city block: narrow four- and five-storey pre-war fronts in different "
                      "colours with stoops and a fire escape, cafe tables under string lights on a wide sidewalk, "
                      "a street tree and a bicycle, with a small white dog leashed by a table."),
    "settled": (settled, "A long-settled avenue by day: two big six-storey brick apartment blocks with an entrance "
                         "canopy and a courtyard gate, a fruit stand, a car parked at the kerb, and an elevated "
                         "train passing over a bus stop, with a small white dog on the sidewalk."),
    "middle": (little, "A small-city downtown: a clock-tower train station with a train at the platform, a bakery, "
                       "a theatre with a tall sign and a lit marquee, a lamp post with flower baskets, and a "
                       "mid-rise apartment building with a car pulling into its garage, with a small white dog on "
                       "the sidewalk."),
    "new_water": (fresh, "New glass-and-brick towers with a roof terrace on a waterfront walkway: moving boxes by "
                         "an open front door, a railing, a bench and a sailboat, a skyline reflected in the water, "
                         "and a small white dog on the walkway."),
    "space": (space, "An older suburb under a wide sky: a low apartment building with a big bay window showing a "
                     "desk, lamp and plant under a balcony, broad lawns, big trees and a small car park, with a "
                     "small white dog chasing a ball on the grass."),
    "enclave": (quiet, "A quiet street at dusk: a small apartment building tucked between two houses with lit "
                       "porch lights and windows, lawns, hedges and a mailbox at the kerb, with a small white dog "
                       "on the sidewalk."),
}


def build():
    data = json.load(open(os.path.join(ROOT, "site", "data.json")))
    out, order = {}, []
    for y in data["years"]:
        fn, alt = SCENES[y["id"]]
        entry = {"alt": alt}
        for key, tall in (("banner", False), ("tall", True)):
            sky, s = fn(ACCENT[y["id"]], tall)
            entry[key] = wrap(sky, s.out(), alt, tall)
        out[y["label"]] = entry
        for k in (y.get("display_label"), y.get("id")):
            if k and k not in out:
                out[k] = y["label"]  # alias: a string naming the key that holds the drawings
        order.append((y.get("display_label") or y["label"], y["id"], entry))
    path = os.path.join(ROOT, "site", "illustrations.json")
    with open(path + ".tmp", "w") as f:  # atomic: the page may be reading the file
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(path + ".tmp", path)
    # preview
    cards = []
    for name, yid, e in order:
        cards.append(
            '<section><h2><i style="background:%s"></i>%s</h2>'
            '<p class="k">banner, 360 by 130 (as on the tile)</p><div class="tile"><div class="art b">%s</div>'
            '<div class="cap"><b>%s</b><span>Tile text sits here.</span></div></div>'
            '<p class="k">tall, 360 by 200 (top of the experience page)</p><div class="art t">%s</div></section>'
            % (ACCENT[yid], name, e["banner"], name, e["tall"]))
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Experience illustrations: preview</title>
<style>
body{margin:0;background:#FFF4F7;color:#3A1630;font-family:"Figtree","Segoe UI",system-ui,sans-serif;font-size:17px;line-height:1.4}
.wrap{max-width:560px;margin:0 auto;padding:16px}
h1{font-family:"Bricolage Grotesque","Arial Narrow",system-ui,sans-serif;font-size:26px;margin:0 0 4px}
h2{font-family:"Bricolage Grotesque","Arial Narrow",system-ui,sans-serif;font-size:21px;margin:26px 0 6px;display:flex;align-items:center;gap:8px}
h2 i{width:14px;height:14px;border-radius:3px;flex:none}
p{margin:0}.k{font-size:13px;color:#7A5670;margin:8px 0 4px}
.tile{background:#FFFFFF;border:2px solid #F3CADA;border-radius:18px;overflow:hidden}
.art{line-height:0}.art svg{display:block;width:100%;height:auto}
.art.t{border-radius:18px;overflow:hidden;border:2px solid #F3CADA}
.cap{padding:10px 14px 12px}.cap b{display:block;font-family:"Bricolage Grotesque","Arial Narrow",system-ui,sans-serif;font-size:19px}
.cap span{font-size:15px;color:#7A5670}
</style></head><body><div class="wrap"><h1>Experience illustrations</h1>
<p class="k">Six scenes, two crops each, built by scripts/build_illustrations.py. Review only: not linked from the page.</p>
""" + "\n".join(cards) + "</div></body></html>\n"
    hp = os.path.join(ROOT, "site", "illustrations_preview.html")
    with open(hp + ".tmp", "w") as f:
        f.write(html)
    os.replace(hp + ".tmp", hp)
    print("illustrations.json %d bytes" % os.path.getsize(path))
    for name, yid, e in order:
        print("  %-34s banner %5d B   tall %5d B" % (name, len(e["banner"].encode()), len(e["tall"].encode())))


if __name__ == "__main__":
    build()
