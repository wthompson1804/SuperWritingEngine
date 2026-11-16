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
    pts, j = [], 0
    yy = y
    while yy < y + h:
        xx = x + (4 if j % 2 else 0)
        while xx < x + w - 4:
            pts.append((xx, yy))
            xx += step * 2
        yy += row
        j += 1
    return dots(pts, 4, 1.5)


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
          '<path d="M0-4q0-6 6-6l5-7h14l6 7h5q4 0 4 6v4z" fill="%s"/>'
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
    s = S()
    sky = mix(A, PAPER, .14)
    lilac, pink, buff = mix(A, PAPER, .42), mix(BERRY, PAPER, .5), mix(BUTTER, PAPER, .75)
    cloud(s, 150, 20, .8)
    if tall:
        cloud(s, 250, -14, 1.1)
        cloud(s, 40, -22, .7)
    G = 104
    # five fronts: x, width, top, fill
    for x, w, top, f in ((-4, 70, 30, ROSE), (66, 78, 14, lilac), (144, 64, 38, buff), (208, 86, 22, pink),
                         (294, 70, 42, BLUSH)):
        s.r(x, top, w, G - top, f)
        s.r(x - 2, top - 5, w + 4, 7, WHITE, 1)
    s.p(bricks(70, 24, 70, 50), mix(A, PAPER, .65), 0)
    s.p(bricks(212, 32, 78, 42), mix(BERRY, PAPER, .72), 0)
    # upper windows
    s.p(grid(6, 40, 3, 2, 11, 14, 19, 20), WHITE)
    s.p(grid(76, 26, 4, 3, 10, 13, 17, 17), WHITE)
    s.p(grid(153, 49, 3, 1, 11, 15, 18, 0), WHITE)
    s.p(grid(218, 34, 4, 2, 11, 14, 19, 20), WHITE)
    s.p(grid(304, 52, 3, 1, 12, 15, 19, 0), WHITE)
    # flower boxes
    s.p(grid(217, 68, 4, 1, 13, 4, 19, 0), MINT)
    s.p(grid(152, 64, 3, 1, 13, 4, 18, 0), BERRY)
    # 1 brownstone stoop
    s.r(8, 80, 14, 18, WHITE)
    s.r(38, 76, 14, 22, PLUM, 2)
    s.p("M30 104v-6h28v6zM34 98v-0", mix(MUTED, PAPER, .4))
    s.line("M30 98v-12M58 98v-12")
    # 2 café
    s.r(74, 86, 40, 18, WHITE)
    s.r(122, 82, 14, 22, BERRY_D, 2)
    awning(s, 68, 74, 74, 10, BERRY)
    # 3 corner shop
    s.r(150, 84, 34, 16, WHITE)
    s.p(dots([(154, 94), (162, 92), (170, 94), (177, 91)], 4, 6), BUTTER_D, 0)
    s.r(190, 82, 12, 22, PLUM, 2)
    awning(s, 146, 72, 58, 10, A)
    # 4 pre-war entrance with canopy
    s.r(240, 80, 22, 24, PLUM, 2)
    s.line("M251 80v24")
    s.p("M232 80h38l-4-7h-30z", BUTTER)
    s.r(214, 84, 16, 14, WHITE)
    s.r(272, 84, 14, 14, WHITE)
    # 5 shop
    s.r(300, 84, 34, 20, WHITE)
    s.r(340, 82, 13, 22, MINT_INK, 2)
    awning(s, 296, 72, 62, 10, MINT)
    # pavement and street
    s.r(-4, G, 368, 14, PAPER)
    s.r(-4, 118, 368, 14 + (26 if tall else 0), mix(MUTED, PAPER, .32))
    s.p(dots([(20, 124), (70, 126), (150, 123), (230, 126), (300, 124), (340, 127)], 12, 1.5), WHITE, 0)
    # tree, lamp, café table, dog
    tree(s, 284, 112, 13, MINT, 24)
    lamp(s, 204, 114, 46)
    s.line("M92 114v-9M84 114v-8h5M100 114v-8h-5M116 114v-9M108 114v-8h5M124 114v-8h-5")
    s.e(92, 104, 7, 2, WHITE)
    s.e(116, 104, 7, 2, WHITE)
    s.c(92, 101, 1.6, BERRY, 0)
    s.c(116, 101, 1.6, BUTTER_D, 0)
    dog(s, 228, 116, .85, leash=(204, 100))
    if tall:
        s.r(-4, 136, 368, 22, PAPER)
        s.p(grid(8, 141, 12, 2, 20, 1.5, 30, 8), LINE, 0)
        s.r(40, 132, 26, 12, CORAL, 2)
        s.c(46, 130, 6, MINT)
        s.c(58, 129, 7, MINT)
        s.r(300, 132, 26, 12, CORAL, 2)
        s.c(307, 129, 7, MINT)
        s.c(319, 130, 6, MINT)
    return sky, s


def settled(A, tall):
    s = S()
    sky = mix(A, PAPER, .13)
    brick, buff, steel = mix(CORAL, PAPER, .5), mix(BUTTER_D, PAPER, .38), mix(PLUM, PAPER, .55)
    cloud(s, 262, 18, .8)
    if tall:
        cloud(s, 60, -16, 1.1)
        cloud(s, 300, -24, .7)
    G = 104
    # far rooftops
    s.p("M226 104V66h22v-8h20v14h26v-10h24v12h46v30z", mix(A, PAPER, .28), 0)
    # elevated line and train
    s.r(238, 30, 130, 20, A, 4)
    s.p(grid(246, 34, 8, 1, 10, 7, 15, 0), WHITE, 1.5)
    s.r(238, 44, 130, 2.5, BUTTER, 0, 0)
    s.r(226, 50, 140, 7, steel)
    s.p(grid(232, 52, 14, 1, 4, 3, 10, 0), mix(PLUM, PAPER, .8), 0)
    s.p("M250 57h7v47h-7zM312 57h7v47h-7z", steel)
    s.line("M240 57l10 10M267 57l-10 10M302 57l10 10M329 57l-10 10")
    # building one: six storeys of brick, shops below
    s.r(4, 18, 148, 86, brick)
    s.r(2, 14, 152, 6, WHITE, 1)
    s.r(60, 5, 22, 10, brick)
    s.p(bricks(8, 22, 140, 56, 10, 6), mix(CORAL, PAPER, .68), 0)
    s.p(grid(12, 25, 8, 5, 10, 7, 17.5, 11), WHITE)
    s.r(4, 79, 148, 3, WHITE, 0, 0)
    # bakery
    s.r(10, 90, 40, 14, WHITE)
    s.p("M14 100q4-7 9 0zM25 100q4-7 9 0zM36 100q4-7 9 0z", BUTTER_D, 1.5)
    s.r(56, 86, 13, 18, PLUM, 2)
    awning(s, 8, 81, 66, 8, BERRY)
    # greengrocer with the stand outside
    s.r(84, 90, 44, 14, WHITE)
    s.r(134, 86, 13, 18, MINT_INK, 2)
    awning(s, 82, 81, 68, 8, MINT)
    # building two: buff brick, lobby in the middle
    s.r(152, 24, 76, 80, buff)
    s.r(150, 20, 80, 6, WHITE, 1)
    s.r(196, 11, 18, 10, buff)
    s.p(grid(159, 31, 4, 5, 11, 7, 17, 11), WHITE)
    s.r(152, 85, 76, 3, WHITE, 0, 0)
    s.r(181, 88, 18, 16, PLUM, 2)
    s.line("M190 88v16")
    s.p("M175 88h30l-3-5h-24z", A)
    s.c(165, 98, 6, MINT)
    s.c(215, 98, 6, MINT)
    # pavement and avenue
    s.r(-4, G, 368, 14, PAPER)
    s.r(-4, 118, 368, 14 + (26 if tall else 0), mix(MUTED, PAPER, .32))
    s.p(dots([(16, 124), (80, 126), (160, 123), (236, 126), (290, 124), (336, 127)], 12, 1.5), WHITE, 0)
    # fruit stand: three tilted crates
    for i, f in enumerate((BERRY, BUTTER, mix(MINT, PAPER, .8))):
        x = 82 + i * 17
        s.p("M%s 116v-7l15-3v10z" % x, mix(BUTTER_D, PAPER, .45))
        s.c(x + 4, 107.5, 2.6, f, 1.5)
        s.c(x + 9.5, 106.5, 2.6, f, 1.5)
        s.c(x + 7, 103.5, 2.6, f, 1.5)
    # hydrant and dog under the el
    s.p("M286 116v-9q0-4 4-4t4 4v9zM283 110h14", BERRY)
    dog(s, 268, 116, .85, flip=True)
    tree(s, 344, 112, 11, MINT, 22)
    if tall:
        s.r(-4, 136, 368, 22, PAPER)
        s.p(grid(8, 141, 12, 2, 20, 1.5, 30, 8), LINE, 0)
        s.p("M150 124h12M190 124h12M230 124h12", "none", 2, ' stroke="%s"' % WHITE)
    return sky, s


def little(A, tall):
    s = S()
    sky = mix(A, PAPER, .09)
    red, cream, stone = mix(A, PAPER, .32), mix(BUTTER, PAPER, .45), mix(MUTED, PAPER, .3)
    cloud(s, 250, 16, .8)
    if tall:
        cloud(s, 84, -18, 1.1)
        cloud(s, 300, -26, .7)
    s.p("M-4 104V78q40-20 90-6t90-4t100-6t88 8v34z", mix(MINT, PAPER, .32), 0)
    G = 104
    # station with clock tower
    s.r(2, 74, 88, 30, stone)
    s.p("M-4 76l8-12h84l8 12z", mix(A, PAPER, .6))
    s.p("M10 104V88a6 6 0 0 1 12 0v16zM70 104V88a6 6 0 0 1 12 0v16z", WHITE)
    s.r(31, 28, 30, 76, stone)
    s.p("M27 30l19-20l19 20z", mix(A, PAPER, .6))
    s.c(46, 46, 10, WHITE)
    s.line("M46 46v-6M46 46l4 3")
    s.p("M40 104V86a6 6 0 0 1 12 0v18z", PLUM)
    s.p(grid(36, 64, 2, 1, 7, 10, 13, 0), WHITE)
    # theatre
    s.p("M100 104V38h18v-8h56v8h18v66z", cream)
    s.p("M108 46h76M108 52h76", "none", 0, ' stroke="%s" stroke-width="1.5"' % mix(BUTTER_D, PAPER, .6))
    s.r(138, 6, 16, 56, A, 3)
    s.p("".join("M%s %sa2 2 0 1 0 .1 0z" % (146, y) for y in (12, 21, 30, 39, 48)), BUTTER, 0)
    s.r(110, 84, 72, 20, PLUM)
    s.p(grid(115, 87, 2, 1, 9, 17, 12, 0) + grid(156, 87, 2, 1, 9, 17, 12, 0), mix(BUTTER, PAPER, .6), 1.5)
    s.r(139, 86, 14, 18, A, 2)
    s.r(142, 89, 8, 6, WHITE, 0, 1.5)
    s.p("M92 82l8-16h92l8 16z", WHITE)
    s.r(92, 82, 108, 5, A)
    s.p("".join("M%s 69.5a1.800 1.800 0 1 0 .1 0z" % x for x in range(104, 190, 9))
        + "".join("M%s 76.500a1.800 1.800 0 1 0 .1 0z" % x for x in range(100, 196, 9)), BUTTER_D, 0)
    # apartment building with garage entrance
    s.r(208, 20, 134, 84, red)
    s.r(206, 16, 138, 6, WHITE, 1)
    s.p(bricks(212, 24, 126, 52, 10, 7), mix(A, PAPER, .48), 0)
    s.p(grid(216, 28, 7, 4, 11, 8, 17.5, 13), WHITE)
    s.r(208, 79, 134, 3, WHITE, 0, 0)
    s.r(218, 86, 16, 18, PLUM, 2)
    s.p("M213 86h26l-3-5h-20z", BUTTER)
    s.r(246, 88, 20, 10, WHITE)
    s.r(278, 84, 54, 20, PLUM, 2)
    s.p(grid(280, 85.500, 7, 1, 4, 4, 7.6, 0), BUTTER, 0)
    car(s, 325, 109, BUTTER, .85, flip=True)
    # pavement and main street
    s.r(-4, G + 5 - 5, 368, 14, PAPER)
    s.r(-4, 118, 368, 14 + (26 if tall else 0), mix(MUTED, PAPER, .32))
    s.p(dots([(16, 124), (80, 126), (160, 123), (236, 126), (290, 124), (336, 127)], 12, 1.5), WHITE, 0)
    s.p("M276 104h58l8 14h-74z", mix(MUTED, PAPER, .32), 0)
    car(s, 325, 113, BUTTER, .9, flip=True)
    lamp(s, 202, 114, 40)
    tree(s, 352, 112, 11, MINT, 22)
    dog(s, 232, 116, .85)
    if tall:
        s.r(-4, 136, 368, 22, PAPER)
        s.p(grid(8, 141, 12, 2, 20, 1.5, 30, 8), LINE, 0)
        s.p("M60 124h12M100 124h12M140 124h12", "none", 2, ' stroke="%s"' % WHITE)
    return sky, s


def fresh(A, tall):
    s = S()
    sky = mix(A, PAPER, .12)
    water, glass, brick = mix(MINT, PAPER, .34), mix(MINT, WHITE, .18), mix(BERRY_D, PAPER, .45)
    box = mix(BUTTER_D, PAPER, .55)
    s.c(306, 20, 11, BUTTER, 0)
    cloud(s, 200, 22, .8)
    if tall:
        cloud(s, 60, -18, 1.1)
        cloud(s, 250, -26, .7)
    # skyline across the water
    s.p("M170 76V60h12V44h14v10h10V34h12v14h14v-8h10v20h14V28h10v24h12V40h16v14h12V48h12v12h12v16z",
        mix(A, PAPER, .36), 0)
    s.p(grid(209, 40, 2, 3, 2, 2, 5, 6) + grid(259, 34, 2, 4, 2, 2, 5, 6) + grid(284, 46, 3, 3, 2, 2, 5, 6),
        mix(A, PAPER, .12), 0)
    s.r(-4, 76, 368, 30, water, 0, 0)
    s.p(dots([(176, 82), (214, 88), (250, 81), (300, 86), (334, 80), (190, 95), (280, 94), (336, 93)], 12, 1.5),
        WHITE, 0)
    # sailboat
    s.p("M286 86h20l-4 5h-12z", WHITE, 1.5)
    s.p("M296 84v-16l9 16z", BERRY, 1.5)
    # glass tower
    s.r(12, 4, 64, 100, glass)
    s.r(12, 4, 16, 100, brick)
    s.p("M28 20h48M28 36h48M28 52h48M28 68h48M28 84h48M44 4v80M60 4v80", "none", 0,
        ' stroke="%s" stroke-width="1.5"' % mix(MINT, WHITE, .6))
    s.p(grid(16, 10, 1, 5, 7, 9, 0, 16), WHITE, 1.5)
    # brick-and-glass tower with balconies
    s.r(84, 26, 68, 78, brick)
    s.r(82, 22, 72, 6, WHITE, 1)
    s.p(bricks(88, 32, 60, 48, 10, 7), mix(BERRY_D, PAPER, .62), 0)
    s.p(grid(92, 34, 3, 3, 14, 11, 19, 18), glass)
    for y in (45, 63, 81):
        s.p("M150 %sh30v-9M160 %sv-9M170 %sv-9M150 %sh30" % (y, y, y, y - 9), "none")
    # moving boxes on the middle balcony and at the door
    s.r(154, 53, 10, 9, box, 0, 1.5)
    s.r(165, 55, 9, 7, box, 0, 1.5)
    s.r(157, 46, 9, 7, box, 0, 1.5)
    s.r(40, 86, 18, 18, PLUM, 2)
    s.p("M34 86h30l-3-5h-24z", A)
    s.r(108, 88, 18, 16, PLUM, 2)
    # walkway
    s.r(-4, 104, 368, 28 + (26 if tall else 0), PAPER)
    s.p(grid(0, 111, 9, 3 + (3 if tall else 0), 26, 1.5, 42, 8), LINE, 0)
    s.p("M152 104V92h212M178 92v12M204 92v12M230 92v12M256 92v12M282 92v12M308 92v12M334 92v12M152 98h212",
        "none")
    lamp(s, 196, 118, 46)
    s.r(66, 106, 14, 12, box, 0)
    s.r(81, 110, 11, 8, box, 0)
    s.r(69, 97, 10, 9, box, 0)
    s.p("M70 112h6M84 114h5M72 101.500h4", "none", 0, ' stroke="%s" stroke-width="2"' % BERRY)
    # bench and planter
    s.p("M236 110h30M236 116h30M240 116v6M262 116v6", "none", 2.5)
    s.r(118, 110, 30, 10, mix(A, PAPER, .5), 2)
    s.c(126, 107, 6, MINT)
    s.c(138, 106, 7, MINT)
    dog(s, 312, 124, .9)
    if tall:
        s.r(-4, 150, 368, 8, water, 0, 0)
        s.r(-4, 147, 368, 4, MUTED, 0, 0)
    return sky, s


def space(A, tall):
    s = S()
    sky = mix(A, PAPER, .11)
    lawn, buff, lot = mix(MINT, PAPER, .42), mix(A, PAPER, .34), mix(MUTED, PAPER, .3)
    s.c(318, 22, 11, BUTTER, 0)
    cloud(s, 60, 26, 1)
    cloud(s, 226, 18, .8)
    if tall:
        cloud(s, 150, -16, 1.2)
        cloud(s, 300, -24, .7)
    # far tree line and lawns
    s.p("M-4 92V72q14-10 26 0q12-12 26-2q16-8 28 2h150q14-12 30-2q14-10 28 0q14-8 26 2q16-10 30 0v20z",
        mix(MINT, PAPER, .62), 0)
    s.r(-4, 88, 368, 44 + (26 if tall else 0), lawn, 0, 0)
    s.p(dots([(10, 100), (40, 112), (96, 124), (150, 114), (20, 124), (190, 104), (130, 104)], 2, 4),
        mix(MINT, PAPER, .75), 0)
    tree(s, 14, 94, 16, MINT, 16)
    tree(s, 236, 94, 15, MINT, 16)
    tree(s, 340, 94, 13, mix(MINT, PAPER, .8), 14)
    # the low building
    s.r(36, 40, 172, 56, buff)
    s.r(32, 35, 180, 7, WHITE, 1)
    s.p("M36 59h172M36 78h172", "none", 0, ' stroke="%s" stroke-width="1.5"' % mix(A, PAPER, .55))
    s.p(grid(44, 45, 8, 1, 14, 10, 20.500, 0) + grid(44, 64, 2, 1, 14, 10, 20.500, 0)
        + grid(167, 64, 2, 1, 14, 10, 20.500, 0) + grid(44, 83, 3, 1, 14, 9, 20.500, 0)
        + grid(167, 83, 2, 1, 14, 9, 20.500, 0), WHITE)
    # the big window with the desk
    s.r(88, 60, 70, 20, WHITE, 2)
    s.r(100, 73, 44, 2.5, CORAL, 0, 0)
    s.p("M103 75.500v4M141 75.500v4", "none", 0, ' stroke="%s" stroke-width="2"' % CORAL)
    s.r(113, 63, 15, 8, PLUM, 1, 0)
    s.r(119.500, 71, 2, 2, PLUM, 0, 0)
    s.p("M135 73v-6M131 67h8l-2-4h-4z", BUTTER_D, 1)
    s.p("M92 80v-9q0-3 3-3t3 3v9z", BERRY, 0)
    s.r(115, 82, 16, 14, PLUM, 2)
    s.p("M110 82h26l-3-4h-20z", A)
    # path, parking lot, cars
    s.p("M118 96h10l14 12h-16z", PAPER, 0)
    s.p("M150 104h214v28h-232z" if not tall else "M150 104h214v40h-244z", lot)
    s.p("M178 106l-8 20M208 106l-6 20M238 106l-4 20M268 106l-2 20M298 106v20M328 106l2 20",
        "none", 0, ' stroke="%s" stroke-width="2"' % WHITE)
    car(s, 208, 120, BERRY, .68)
    car(s, 268, 120, mix(A, PAPER, .7), .68)
    car(s, 328, 120, WHITE, .68)
    lamp(s, 352, 106, 40)
    # dog and ball on the lawn
    s.c(92, 117, 3, BERRY, 1.5)
    dog(s, 64, 120, .9)
    if tall:
        s.p(dots([(30, 140), (70, 148), (110, 138), (16, 150)], 2, 4), mix(MINT, PAPER, .75), 0)
        s.c(40, 144, 2.5, WHITE, 0)
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
    s.p("M86 106q0-9 9-9t9 9zM228 106q0-10 11-10t11 10zM336 106q0-9 10-9t10 9z", hedge)
    s.p("M62 104h8l-2 10h-10zM162 104h12l2 10h-16zM274 104h8l2 10h-10z", PAPER, 0)
    s.r(-4, 113, 368, 6, PAPER)
    s.r(-4, 119, 368, 13 + (26 if tall else 0), mix(PLUM, PAPER, .42))
    s.p(dots([(30, 125), (120, 127), (210, 125), (300, 127)], 14, 1.5), mix(PLUM, PAPER, .2), 0)
    # mailbox at the kerb
    s.line("M100 118v-12", 2.5)
    s.p("M92 106v-5q0-5 5-5h8q4 0 4 4v6z", A)
    s.p("M106 100v-6h5v3h-5", BERRY, 1.5)
    dog(s, 204, 117, .85)
    if tall:
        s.p(dots([(60, 138), (170, 141), (270, 138)], 14, 1.5), mix(PLUM, PAPER, .2), 0)
        s.r(-4, 146, 368, 5, PAPER)
        s.r(-4, 151, 368, 8, lawn, 0, 0)
    return sky, s


SCENES = {
    "pre_car": (walk, "Old city blocks: brownstone and pre-war apartment fronts over a cafe with striped awning "
                      "and sidewalk tables, a corner shop, a street lamp and a tree, with a small white dog "
                      "leashed to the lamp post."),
    "settled": (settled, "A long-settled avenue: two six-storey brick elevator buildings over a bakery and a "
                         "greengrocer with crates of fruit outside, an elevated train passing behind, and a small "
                         "white dog on the sidewalk."),
    "middle": (little, "A small-city main street: a train station with a clock tower, a theatre with a lit "
                       "marquee, and a mid-rise apartment building with a car leaving its garage, with a small "
                       "white dog on the sidewalk."),
    "new_water": (fresh, "New glass-and-brick towers on a riverfront walkway: moving boxes on a balcony and by "
                         "the door, a railing, a bench and a sailboat, a skyline across the water, and a small "
                         "white dog on the walkway."),
    "space": (space, "An older suburb under a wide sky: a low apartment building with a desk in a big window, "
                     "broad lawns, big trees and a large parking lot, with a small white dog and a ball on the "
                     "grass."),
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
        for k in (y.get("label"), y.get("display_label"), y.get("id")):
            if k:
                out[k] = entry
        order.append((y.get("display_label") or y["label"], y["id"], entry))
    path = os.path.join(ROOT, "site", "illustrations.json")
    with open(path, "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
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
    with open(os.path.join(ROOT, "site", "illustrations_preview.html"), "w") as f:
        f.write(html)
    print("illustrations.json %d bytes" % os.path.getsize(path))
    for name, yid, e in order:
        print("  %-34s banner %5d B   tall %5d B" % (name, len(e["banner"].encode()), len(e["tall"].encode())))


if __name__ == "__main__":
    build()
