# Navigation patterns for the collapse-to-headlines page (2026-11-16)

For the agent editing `site/index.html`. A working, tested copy of everything below is `site/pattern_demo.html`
(screens: `site/screens/pattern_demo.png`, `pattern_demo_hood.png`, `pattern_demo_compare.png`, `pattern_demo_sheet.png`).

**How far to trust the sources.** This session could not open nngroup.com, baymard.com, developer.mozilla.org or any other
page directly (hosts outside the allowed network). Every claim below rests on search-result summaries of those pages, and
quotes are the wording those summaries returned. Dates marked "not checked" could not be confirmed. Nothing was scraped
from Zillow, Redfin, Airbnb, Booking or StreetEasy, and no usable design write-up was found for Redfin, Booking or StreetEasy.

## 1. Why the current page overloads

Measured from the `after-*` screenshots at 390 px: the place page is 5,027 px tall (6 screens), the neighborhood page
12,936 px (15 screens) and compare 5,194 px (6 screens). The content is right; the page shows every level of it at once.
Progressive disclosure means showing the few things most people need first and putting the rest one step away (NN/g);
here the cost receipt, the rent terms, the sources and the full resident quotes all sit open at the same weight as the
price. There is no overview layer, so there is nothing to "zoom" from (Shneiderman: overview first, details on demand),
and on a phone people often stop scrolling before the end of a very long page (NN/g), so the lower sections are in
effect hidden already, only without a headline to say what they hold. Existing folds use labels that say what is inside
("The building, fact by fact") rather than what it concludes, which gives a weak cue for deciding whether to tap.

## 2. The recommended structure

### 2.1 The one building block: the headline row

```
┌──────────────────────────────────────────────┐
│ WHAT IT COSTS                    [$326 under]│  label 11px caps · state chip (optional)
│ $2,674 a month, all-in                     ⌄ │  headline 16px bold, built by a function · caret
│ Rent $2,345, then garage, pet rent and ut…   │  subhead 13px muted, written, one line (optional)
└──────────────────────────────────────────────┘  whole row is the tap target; 72 to 76 px tall
```

- **Label**: the section's fixed name, 1 to 4 words. Same label on every place, so she learns the positions.
- **Headline**: the section's conclusion, from a pure function of the data (`H.cost(u)`), 36 characters or fewer so it
  stays on one line at 390 px (two lines costs 16 px a row). It must make sense to someone who never opens the row.
- **Subhead**: optional hand-written line (`row.sub`), ellipsis when collapsed, wraps when open. If absent, render nothing.
- **State chip**: at most one, only when it changes what she does: `ok` (mint), `ask` (butter). No chip is the normal case.
  Two or three chips a page at most, or they stop meaning anything.
- **Caret**: a down caret that flips when open. NN/g's icon test found the caret the clearest "opens here" signal; the
  plus did not clearly beat no icon.
- **How many rows**: 5 to 7 a page. No source gives a tested maximum. The nearest evidence is Baymard's product-page
  model, which collapses about five major sections (description, reviews, Q&A, shipping, specs). Seven rows at 76 px is
  532 px, which is what leaves room for the strip and host line inside 1.5 screens. An eighth section means merging two.
- **Start open**: none. The always-visible block above the rows (title, strip, host line) is the "open" content.
  Rows reopen as she left them when she comes back to the same page (session storage).
- **Independent, not exclusive**: opening one row does not close another. Add one "Open all / Close all" control.

### 2.2 Accordion, bottom sheet or separate page

| Use | When | Here |
|---|---|---|
| Row (in-place accordion) | Part of the page's own reading order; she may want two open at once; up to about one screen when open | Cost, a day here, the car, the dog, the building, residents, Queens |
| Bottom sheet | Short, tied to one figure or word she just tapped, read and dismissed; under 70% of screen height; never one sheet on top of another | A strip figure's breakdown, "How we got this", sources, leasing office, the meaning of `*` |
| Separate page | Has its own identity, its own list, or its own Hold action | Experience, neighborhood, place, compare |

A row whose open content runs past two screens (all 14 resident quotes) shows the top three and a "more" button inside.

### 2.3 Place page. Target 1.5 screens (measured in the demo: 1,215 px including tray padding)

```
‹ Harbor Point                                  back link, 44px
HARBOR POINT · THE WATERFRONT YEAR              kicker
The Marlow, 5C                                  h1
1 bedroom · floor 5 · 150 Dock St · seen Nov 15 one line
┌─────────┬─────────┬─────────┬─────────┐
│ $2,674  │  502    │ 53 min  │  Yes    │      key-facts strip, each cell opens a sheet
│ all-in  │ sq ft   │ to M&D  │ dogs    │
└─────────┴─────────┴─────────┴─────────┘
│ Host line, two lines, then…  More │           host voice, clamped
STILL TO CONFIRM  [Ask]   1 thing to ask before you sign      ⌄   (only if any; always first)
WHAT IT COSTS  [$326 under]  $2,674 a month, all-in           ⌄
A DAY HERE          3 min to green space, 29 places to eat    ⌄
THE CAR             53 min to Mom and Dad, no tolls           ⌄
FOR THE DOG  [Yes]  Dogs welcome, any size                    ⌄
THE BUILDING        Elevator, floor 5, laundry in the unit    ⌄
COMPARED TO STAYING IN QUEENS  $93 more a month, 47 more min  ⌄
How we got this · Leasing office                text links, open sheets
Up next: Parallel 41                  $2,755
[ Hold this place ]                             fixed bottom bar
```

- At a glance (in order): back link, name, one-line facts, 4-cell strip, host line (2 lines), 5 to 7 row headlines, Hold.
- One tap: any row's body; any strip cell's sheet; full host line; how we got this; leasing office; photos.
- Two taps: the cost receipt's "what does * mean"; resident quotes beyond three; the listing itself (new tab).
- Moves: rent terms and tour questions go inside "Still to confirm"; parking goes inside "The car"; "You'll love / Gives
  us pause" goes inside "Compared to staying in Queens"; the day strip becomes the body of "A day here"; the footer
  notes become the "How we got this" sheet.

### 2.4 Neighborhood page. Target 2 screens (demo: 1,743 px with 6 rows, 3 place cards, 2 list rows)

```
‹ The Waterfront Year
NUMBER 1 OF 4 IN THIS EXPERIENCE
Harbor Point
Stamford, Connecticut · among the safest on the list
┌ $2,674 typical ┬ 53 min ┬ $0 tolls ┬ 10 places ┐   strip; "10 places" jumps to the list
│ Host line, two lines…  More │
( The area )( Places (10) )( Skip these (2) )( Worth a call (3) )   sticky jump chips
GOOD FOR YOU, WATCH FOR   4 things to love, 2 to watch          ⌄
WHAT'S HERE               Garage parking, dog park, 29 to eat   ⌄
WHAT RESIDENTS SAY        Quiet at night, pricey garages        ⌄
HOW OTHERS DESCRIBE IT    "A small city's new front porch"      ⌄
LOCAL RULES  [2 to know]  Dog license; no overnight parking     ⌄
COMPARED TO STAYING IN QUEENS  $93 more a month, 47 more min    ⌄
Places to see
┌ 1. The Marlow, 5C                    $2,674 ┐   compact card: name + price, one facts line,
│ 1 bed · 502 sq ft · garage · 1 to confirm   │   host line clamped to two lines; whole card is the link
└ Bright, five floors up, garage downstairs…  ┘   (three cards, then "Show 7 more places")
LOOKS GOOD, BUT AVOID     2 we'd skip, and why                  ⌄
WORTH A PHONE CALL        3 more if the office confirms…        ⌄
```

- At a glance: name, where, strip, host line, jump chips, six row headlines, top three place cards.
- One tap: any row; "Show 7 more"; a place page; the avoid list; the call list; the map (as a sheet or a row body).
- Two taps: a place's detail; quotes beyond three; an avoid card's evidence.
- The avoid cards and the call list each become **one row** whose headline is the count and the reason. Today they add
  about 5,000 px.
- Jump chips earn their place here because the place list pushes the page past two screens once "show more" is used.

### 2.5 Experience page. Target 1.5 screens

```
‹ All experiences
The Waterfront Year                              h1 + one written line
┌ $2,674 median ┬ 53 min ┬ $0 tolls ┬ 14 places ┐   median big, range small beneath (owner's rule)
│    $2,345 to $2,867                            │
│ The promise… / The catch…  (two lines each)   │
A DAY IN THIS EXPERIENCE   Boardwalk mornings, garage at night  ⌄
WHAT IT COSTS YOU          $2,674 a month typical, all-in       ⌄
COMPARED TO STAYING IN QUEENS  $93 more, 47 more minutes home   ⌄
Tour a neighborhood
┌ 1. Harbor Point        from $2,345 · 10 places ┐  compact cards, top three, then "Show 1 more"
┌ 2. …
┌ 3. …
WORTH A PHONE CALL, IN OTHER TOWNS   3 places, two things each  ⌄
```

- At a glance: title, strip, promise and catch, three row headlines, top three neighborhoods.
- One tap: a row; a neighborhood page; the map (a row "On the map", body holds the map); how we got this (sheet).
- Two taps: a place. Home (the six experiences) stays a list of cards; each card is name, one line, median all-in and
  place count, with promise and catch clamped to two lines.

### 2.6 Compare page. Target 1.5 screens with ties hidden (demo: 1,061 px)

```
‹ Back to the tour
The decision
( 1 and 2 | 1 and 3 | 2 and 3 )                  segmented control, 2 to 3 segments
│ Marlow costs $81 less a month than Parallel 41. Parallel 41 gives you 298 more square feet. │
[x] Only show what differs      "2 rows where they tie are hidden."
1. The Marlow   2. Parallel 41   3. Scribe House   ← sticks to the top while rows scroll
$2,674          $2,755           $2,345
MONTHLY, ALL-IN
[$2,674 21-mo] [$2,755 12-mo] [$2,345 12-mo]     label on its own line, then three equal cells
SPACE … THE 9PM DOG WALK … STILL TO CONFIRM …
COMPARED TO STAYING IN QUEENS   Two cost more, one costs less   ⌄   (collapsed row; today it is a second full table)
[ Copy my tour list ]                            fixed bottom bar
```

- At a glance: the plain-words trade for one pair, names and prices pinned, only the rows that differ.
- One tap: another pair; rows that tie; the Queens comparison; a cell's sheet (how we got this figure).
- Row label sits above its cells, not in a left column: a left label column costs about 100 px and leaves room for two
  places only. Three cells fit at 112 px each on a 390 px phone; narrower phones swipe, with the names row kept in step.

## 3. Rules

| | Rule | Source |
|---|---|---|
| DO | Show the few most-needed things first; put the rest one step away, with labels that set clear expectations. | NN/g, Progressive Disclosure: "defers advanced or rarely used features to a secondary screen" |
| DO | Use vertical collapsed sections, not horizontal tabs. | Baymard: "only 8% of users overlooked this content (compared with 27% for 'Horizontal Tabs')" |
| DO | Collapse every major section the same way; do not mix collapsed rows with sub-pages for sibling content. | Baymard, Avoid Using Subpages (paraphrase): partial use makes the page harder to learn |
| DO | Write the headline as the conclusion; the label is the strongest cue for whether to tap. | NN/g, Information Scent (paraphrase): people judge a destination by its label |
| DO | Use a caret on the right. | NN/g, Accordion Icons (paraphrase): only the caret clearly signalled "expands in place" |
| DO | After a long section closes, put her back at its heading; give a close control at the bottom. | NN/g, Accordions on Mobile (paraphrase): accordions "can cause disorientation and excess scrolling" |
| DO | Let several rows be open at once. | NN/g, Accordions on Desktop (paraphrase): auto-collapse makes it hard to see all content |
| DO | Pin place names and prices while compare rows scroll. | NN/g, Mobile Tables: "sticky column headers help users know what they are looking at" |
| DO | Offer "only show differences" and default it on. | Baymard, Comparison Tools: "hiding is more helpful, so you could kind of parse out the differences faster" |
| DO | Give every sheet a visible Close, and let Back/Esc dismiss it. | NN/g, Bottom Sheets (paraphrase): top problems were no clear dismissal and stacked sheets |
| DON'T | Hide what nearly everyone needs, or what she must not miss, only inside a row. | NN/g, Avoid Accordions (paraphrase): hiding lowers visibility and adds interaction cost |
| DON'T | Stack sheets or open a sheet from a sheet. | NN/g, Bottom Sheets (as above) |
| DON'T | Put long or wordy cells in a three-column phone table. | NN/g, Mobile Tables: "only 2 columns may fit legibly on a narrow mobile screen" for wordy entries |
| DON'T | Rely on a sticky table of contents alone for finding things. | NN/g, Table of Contents: "many users failed to notice the sticky table of contents" |
| DON'T | Treat `<details>` as a full ARIA accordion; keep a real heading inside `<summary>` and test with a screen reader. | Dave Rupert, 2019-12 (paraphrase): `summary` acts as a button and can drop heading semantics |

## 4. Copy-paste code

All six are dependency-free, use the page's existing tokens (`--paper --ink --muted --berry-deep --blush --butter --line
--white`), plus `--mint-bg:#DDF5EA; --tap:44px; --r:14px`. Tested in Chromium at 390×844: no console errors, no
horizontal page scroll, no tap target under 44 px, and the page loads with JavaScript off. The full versions, including
the shared helpers `$`, `$$` and `store` (a try/catch wrapper around `sessionStorage`), are in `site/pattern_demo.html`
under comments `(a)` to `(f)`. Put `document.documentElement.classList.add("js")` first in the script.

### (a) Headline row: native `<details>`, animated where supported, works without JS

```html
<div class="rows">
  <details class="row" id="p-cost">
    <summary>
      <span class="row-l">What it costs</span>
      <h3 class="row-h">$2,674 a month, all-in</h3>
      <span class="row-s">Rent $2,345, then garage, pet rent and utilities.</span>
      <span class="chip ok">$326 under</span>
      <svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 8l5 5 5-5"/></svg>
    </summary>
    <div class="row-b">…body…<button type="button" class="link row-close">Close ↑</button></div>
  </details>
</div>
```
```css
.rows{margin:14px 0 0;border:1px solid var(--line);border-radius:var(--r);background:var(--white);overflow:hidden}
.row+.row{border-top:1px solid var(--line)}
.row>summary{display:grid;grid-template-columns:minmax(0,1fr) auto;column-gap:8px;align-items:center;min-height:56px;padding:9px 12px;cursor:pointer;list-style:none}
.row>summary::-webkit-details-marker{display:none}
.row>summary:focus-visible{outline:3px solid var(--berry-deep);outline-offset:-3px}
.row-l{grid-column:1;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:700}
.row-h{grid-column:1;margin:0;font-size:16px;font-weight:700;line-height:1.25}
.row-s{grid-column:1;font-size:13px;color:var(--muted);overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.row[open] .row-s{white-space:normal}
.chip{grid-column:2;grid-row:1;justify-self:end;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;white-space:nowrap;background:var(--blush)}
.chip.ok{background:var(--mint-bg);color:var(--mint-ink)} .chip.ask{background:var(--butter)}
.chev{grid-column:2;grid-row:2;justify-self:end;width:20px;height:20px;stroke:var(--berry-deep);fill:none;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}
.row[open] .chev{transform:rotate(180deg)}
.row-b{padding:0 12px 12px;font-size:15px}
.row-close{display:none} .js .row-close{display:block;min-height:var(--tap);margin:8px 0 -8px auto}
@media (prefers-reduced-motion:no-preference){
  .chev{transition:transform .2s}
  @supports (interpolate-size:allow-keywords){            /* Chromium today; elsewhere it opens instantly */
    :root{interpolate-size:allow-keywords}
    .row::details-content{block-size:0;overflow:clip;transition:block-size .25s ease,content-visibility .25s allow-discrete}
    .row[open]::details-content{block-size:auto}
  }
}
```
```js
// headline functions: small, pure, asserted. One row = {id,label,headline,sub?,chip?,body}
var H={ cost:function(u){return money(u.all_in)+" a month, all-in"},
  costChip:function(u){return u.all_in<=u.cap?["ok",money(u.cap-u.all_in)+" under"]:["ask",money(u.all_in-u.cap)+" over"]},
  confirm:function(u){var n=u.confirm.length;return n?n+(n===1?" thing":" things")+" to ask before you sign":"Nothing left to confirm"},
  drive:function(u){return u.drive_min+" min to Mom and Dad, "+(u.toll?money(u.toll)+" in tolls":"no tolls")} };
console.assert(H.drive({drive_min:40,toll:14})==="40 min to Mom and Dad, $14 in tolls");
function rowHtml(r){return '<details class="row" id="'+r.id+'"><summary><span class="row-l">'+esc(r.label)+'</span><h3 class="row-h">'+esc(r.headline)+'</h3>'+
  (r.sub?'<span class="row-s">'+esc(r.sub)+'</span>':'')+(r.chip?'<span class="chip '+r.chip[0]+'">'+esc(r.chip[1])+'</span>':'')+
  '<svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 8l5 5 5-5"/></svg></summary><div class="row-b">'+r.body+
  '<button type="button" class="link row-close">Close ↑</button></div></details>'}
// behaviour: remember open rows per page, close from the bottom, never strand her below a closed section
function initRows(root,key){
  var rows=$$("details.row",root),saved=store(key)||[];
  rows.forEach(function(d){
    if(saved.indexOf(d.id)>-1)d.open=true;
    d.addEventListener("toggle",function(){
      if(!d.open){var t=d.getBoundingClientRect().top;if(t<56)window.scrollBy({top:t-64,behavior:"instant"})}
      store(key,rows.filter(function(x){return x.open}).map(function(x){return x.id}))});
    var c=$(".row-close",d);if(c)c.addEventListener("click",function(){d.open=false;$("summary",d).focus({preventScroll:true})});
  });
}
```
Notes. Call `initRows(view,"rows:"+routeKey)` after each render. Do **not** add `name="…"` to these rows: it makes the
group exclusive (Chrome 120, Firefox 130, Safari 17.2), which is the auto-collapse NN/g warns about. Native `<details>`
is opened by find-in-page in Chromium. If a row ever has to be a `button[aria-expanded]` + panel instead, hide the panel
with `hidden="until-found"` (listen for `beforematch` to set `aria-expanded`; Chromium only, check Firefox and Safari
before relying on it) and animate with `display:grid; grid-template-rows:0fr` to `1fr` on the wrapper and
`overflow:hidden; min-height:0` on its one child, which works in every current browser.

### (b) Two-line clamp with "More"

```html
<p class="clamp" id="host-1">Long host line…</p>
<button type="button" class="more" aria-controls="host-1" aria-expanded="false" hidden>More</button>
```
```css
.js .clamp:not(.open){display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-clamp:2;overflow:hidden}
.more{min-height:var(--tap);padding:0 12px 0 0;border:0;background:none;color:var(--berry-deep);font-weight:700}
```
```js
function initClamps(root){$$(".more",root).forEach(function(b){var p=document.getElementById(b.getAttribute("aria-controls"));
  if(!p)return;if(!p.classList.contains("open"))b.hidden=p.scrollHeight<=p.clientHeight+1;   // no button when nothing is cut
  if(b.dataset.on)return;b.dataset.on=1;
  b.addEventListener("click",function(){var o=p.classList.toggle("open");b.setAttribute("aria-expanded",String(o));b.textContent=o?"Less":"More"})})}
```
Without JS the text is simply unclamped. Call `initClamps` after the view is visible (it measures).

### (c) Sticky jump chips with scrollspy

```html
<nav class="jump" aria-label="On this page" id="hoodJump">
  <a href="#hood-area">The area</a><a href="#hood-places">Places (10)</a><a href="#hood-avoid">Skip these (2)</a>
</nav>
<section class="spy" id="hood-area">…</section>
```
```css
.jump{position:sticky;top:0;z-index:5;display:flex;gap:6px;margin:10px -16px 0;padding:6px 16px;overflow-x:auto;background:var(--paper);border-bottom:1px solid var(--line);scrollbar-width:none}
.jump::-webkit-scrollbar{display:none}
.jump a{flex:none;display:inline-flex;align-items:center;min-height:var(--tap);padding:0 14px;border:1px solid var(--line);border-radius:999px;background:var(--white);color:var(--ink);font-size:14px;font-weight:600;text-decoration:none}
.jump a[aria-current=true]{background:var(--ink);color:var(--white);border-color:var(--ink)}
.spy{scroll-margin-top:64px}
```
```js
function initJump(nav){
  var links=$$("a",nav),secs=links.map(function(a){return document.getElementById(a.hash.slice(1))}),pin=0,tick=0;
  function mark(i){links.forEach(function(a,j){if(j===i)a.setAttribute("aria-current","true");else a.removeAttribute("aria-current")});
    var a=links[i];nav.scrollTo({left:a.offsetLeft-nav.clientWidth/2+a.offsetWidth/2,behavior:"instant"})}
  function spy(){if(nav.offsetParent===null||Date.now()<pin)return;var line=nav.getBoundingClientRect().bottom+24,cur=0;
    secs.forEach(function(s,i){if(s&&s.getBoundingClientRect().top<=line)cur=i});mark(cur)}
  window.addEventListener("scroll",function(){if(!tick){tick=1;requestAnimationFrame(function(){tick=0;spy()})}},{passive:true});
  links.forEach(function(a,i){a.addEventListener("click",function(e){e.preventDefault();var s=secs[i];if(!s)return;
    var ds=$$("details.row",s);if(ds.length===1)ds[0].open=true;        // a chip that lands on a single row opens it
    pin=Date.now()+900;mark(i);                                          // tapped chip stays lit even if a short last section cannot reach the top
    s.scrollIntoView({block:"start"});s.setAttribute("tabindex","-1");s.focus({preventScroll:true})})});
  spy();
}
```
`preventDefault` matters here because the page routes on the hash. If the page's own sticky header sits above the chips,
set `.jump{top:<header height>}` and raise `scroll-margin-top` to match.

### (d) "At a glance" key-facts strip

```html
<dl class="glance" aria-label="At a glance">
  <div><button type="button" data-sheet="sh-cost"><dt>a month, all-in</dt><dd>$2,674<small>$2,345 to $2,867</small></dd></button></div>
  <div><button type="button" data-sheet="sh-drive"><dt>to Mom and Dad</dt><dd>53 min</dd></button></div>
  <div>…</div><div>…</div>
</dl>
```
```css
.glance{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;margin:12px 0 0;background:var(--line);border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.glance>div{background:var(--white)}
.glance button{display:flex;flex-direction:column-reverse;justify-content:center;width:100%;min-height:64px;padding:8px 4px;border:0;background:none;text-align:center;cursor:pointer}
.glance dd{margin:0;font-size:17px;font-weight:800;line-height:1.1;white-space:nowrap}
.glance dt{font-size:11px;color:var(--muted);line-height:1.2;margin-top:3px}
.glance small{display:block;font-size:10px;font-weight:500;color:var(--muted)}   /* the range under a median */
```
Four cells is the limit at 390 px (values up to 7 characters, labels up to two short lines). Three cells:
`repeat(3,…)`. Same four facts in the same order on every place, so she can compare by flipping pages. The `<small>`
line is for experience and neighborhood level only.

### (e) Peek bottom sheet on native `<dialog>`

```html
<dialog class="sheet" id="sheet" aria-labelledby="sheetTitle">
  <div class="sheet-top"><h2 id="sheetTitle"></h2><button type="button" id="sheetClose">Close</button></div>
  <div class="sheet-body" id="sheetBody"></div>
</dialog>
<template id="sh-cost" data-title="What is in the $2,674">…receipt…</template>
```
```css
dialog.sheet{position:fixed;inset:auto 0 0 0;width:100%;max-width:430px;max-height:70dvh;margin:0 auto;padding:0;border:0;border-radius:18px 18px 0 0;background:var(--white);color:var(--ink);overflow:auto;overscroll-behavior:contain}
dialog.sheet::backdrop{background:rgb(58 22 48/.45)}
.sheet-top{position:sticky;top:0;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px 8px;background:var(--white)}
.sheet-top::before{content:"";position:absolute;top:6px;left:50%;width:36px;height:4px;margin-left:-18px;border-radius:2px;background:var(--line)}
.sheet-top button{min-width:var(--tap);min-height:var(--tap);padding:0 14px;border:1px solid var(--line);border-radius:999px;background:var(--white);font-weight:700}
.sheet-body{padding:0 16px 20px;font-size:15px}
@media (prefers-reduced-motion:no-preference){dialog.sheet[open]{animation:sheet-up .22s ease-out} @keyframes sheet-up{from{transform:translateY(40%);opacity:0}}}
```
```js
var sheet=document.getElementById("sheet");
document.addEventListener("click",function(e){
  var b=e.target.closest("[data-sheet]");
  if(b){var t=document.getElementById(b.dataset.sheet);if(!t||!sheet.showModal)return;
    document.getElementById("sheetTitle").textContent=t.dataset.title;
    document.getElementById("sheetBody").replaceChildren(t.content.cloneNode(true));sheet.showModal();return}
  if(e.target===sheet||e.target.id==="sheetClose")sheet.close();      // backdrop tap or Close
});
```
`showModal()` gives the focus trap, Esc to close, the backdrop, inert background and focus return for free, and one
shared dialog makes stacking impossible. The grab bar is decoration only (no drag): the Close button is the control.
In the router, add `if(sheet.open){sheet.close();return}` at the top of the `hashchange`/Back handler so Back closes
the sheet first. The page already has a sheet (`.sh-top`, `data-act="close-sheet"`); reuse it if it already does these things.

### (f) Compare: pinned names, swipeable columns, differences only

```html
<div class="cmp" id="cmp" style="--n:3">
  <label class="switch"><input type="checkbox" id="diffOnly" checked> Only show what differs</label>
  <p class="note" id="diffNote" role="status"></p>
  <div class="cmp-head" id="cmpHead" aria-hidden="true"><div class="cmp-grid">
    <div><b>1. The Marlow</b><span>$2,674</span></div><div><b>2. Parallel 41</b><span>$2,755</span></div><div><b>3. Scribe House</b><span>$2,345</span></div>
  </div></div>
  <div class="cmp-body" id="cmpBody" tabindex="0" role="region" aria-label="Side by side">
    <section class="cmp-row"><h3><span>Monthly, all-in</span></h3><div class="cmp-grid">
      <div><span class="vh">The Marlow: </span><b>$2,674</b>21-month price</div>
      <div><span class="vh">Parallel 41: </span><b>$2,755</b>12-month price</div>
      <div><span class="vh">Scribe House: </span><b>$2,345</b>12-month price</div></div></section>
    …more rows…
  </div>
</div>
```
```css
.cmp{--col:112px}
.cmp-head{position:sticky;top:0;z-index:4;overflow:hidden;background:var(--paper);border-bottom:1px solid var(--line)}
.cmp-body{overflow-x:auto;scroll-snap-type:x proximity;overscroll-behavior-x:contain}
.cmp-grid{display:grid;grid-template-columns:repeat(var(--n,3),minmax(var(--col),1fr));gap:6px;min-width:calc(var(--n,3)*var(--col) + (var(--n,3) - 1)*6px)}
.cmp-row{padding:8px 0;border-bottom:1px solid var(--line)}
.cmp-row h3{margin:0 0 4px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.cmp-row h3 span{position:sticky;left:0;display:inline-block}          /* label stays put while cells swipe */
.cmp-row .cmp-grid>div{scroll-snap-align:start;padding:8px;background:var(--white);border:1px solid var(--line);border-radius:10px;font-size:14px}
.cmp-row .cmp-grid b{display:block;font-size:17px}
.cmp.diff .cmp-row[data-same]{display:none}
.switch{display:flex;align-items:center;gap:10px;min-height:var(--tap);font-weight:600}
.switch input{width:22px;height:22px;accent-color:var(--berry-deep)}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
```
```js
(function(){var cmp=$("#cmp"),body=$("#cmpBody"),head=$("#cmpHead"),box=$("#diffOnly"),note=$("#diffNote"),same=0;
  $$(".cmp-row",cmp).forEach(function(r){var v=$$(".cmp-grid>div",r).map(function(c){var k=c.cloneNode(true),h=$(".vh",k);if(h)h.remove();return k.textContent.trim()});
    if(v.every(function(x){return x===v[0]})){r.setAttribute("data-same","");same++}});
  function apply(){cmp.classList.toggle("diff",box.checked);
    note.textContent=same?(box.checked?same+" rows where they tie are hidden.":"Showing all rows, "+same+" of them ties."):""}
  box.addEventListener("change",apply);apply();
  body.addEventListener("scroll",function(){head.scrollLeft=body.scrollLeft},{passive:true});   // names row follows the swipe
})();
```
The names row is a separate element from the swiping body on purpose: a sticky header inside a horizontally scrolling
box sticks to that box, not to the page. Better than comparing rendered text: set `data-same` in the renderer from the
underlying values (and treat "within a rounding step" as a tie).

### Long pages and scroll position

- Keep `content-visibility:auto; contain-intrinsic-size:auto 120px` for **list items below the fold** (place cards after
  "show more", avoid cards). Not on the rows: closed `<details>` content is already skipped.
- Scroll restoration with a hash router: set `history.scrollRestoration="manual"`; before leaving a view
  `store("y:"+route,scrollY)`; after rendering a view reached by Back, `scrollTo(0,store("y:"+route)||0)`; a forward
  navigation starts at 0. Open rows are restored by `initRows`, which must run before the `scrollTo`.

## 5. What not to adopt

- **Horizontal tabs** for sections (Costs | Building | Area). Baymard: 27% overlook tabbed content against 8% for
  collapsed sections, and on a phone some tabs are off-screen to begin with.
- **Exclusive accordions** (`name` attribute, or closing siblings in JS). The page jumps when the row above closes, and
  she cannot keep cost and the car open together.
- **Carousels of facts or stat cards** she has to swipe to discover. Off-screen means unseen; the strip shows all four at once.
- **Truncation by fade or character count with a tiny "…more" inline link.** Use a line clamp and a 44 px control, and
  only where the first two lines carry the point. Never clamp a figure, a date or a thing to confirm.
- **Draggable multi-height sheets** (peek, half, full). Hard to do well on the web, conflicts with page scroll and with
  pull-to-refresh, and gives nothing here over a fixed-height sheet with a Close button.
- **Sheets for long content or for navigation.** A sheet holding a whole section is a page with a worse Back button.
- **A left-hand label column in compare.** Costs a third of the width; forces two places or sideways scrolling.
- **Winner colouring or a totals row in compare.** The brief's own evidence (distinction bias) is the reason: small
  countable gaps look bigger side by side than they will feel.
- **Hover- or long-press-only detail** (tooltips). No hover on a phone; long-press is undiscoverable.
- **Chips everywhere.** A chip on every row is decoration. Keep them for "ask" and the one or two "ok" gates that matter.

## 6. Sources

Read as search-result summaries only (see the note at the top). "Not checked" means the date could not be confirmed.

| Source | Date | URL |
|---|---|---|
| NN/g, Progressive Disclosure (J. Nielsen) | 2006-12 (from memory, not checked) | https://www.nngroup.com/articles/progressive-disclosure/ |
| NN/g, Accordions on Mobile (R. Budiu, video and article) | not checked | https://www.nngroup.com/videos/accordions-on-mobile/ · https://www.nngroup.com/articles/mobile-accordions/ |
| NN/g, Accordions Are Not Always the Answer for Complex Content on Desktops (H. Loranger) | 2014-05-18 (secondary citation) | https://www.nngroup.com/articles/accordions-complex-content/ |
| NN/g, Accordions on Desktop | not checked | https://www.nngroup.com/articles/accordions-on-desktop/ |
| NN/g, Accordions: 5 Scenarios to Avoid Them (video) | not checked | https://www.nngroup.com/videos/avoid-accordions/ |
| NN/g, Accordion Icons | not checked | https://www.nngroup.com/articles/accordion-icons/ |
| NN/g, Information Scent | not checked | https://www.nngroup.com/articles/information-scent/ |
| NN/g, Bottom Sheets: Definition and UX Guidelines | not checked | https://www.nngroup.com/articles/bottom-sheet/ |
| NN/g, Mobile Tables: Comparisons and Other Data Tables | not checked | https://www.nngroup.com/articles/mobile-tables/ |
| NN/g, Table of Contents; In-Page Links | not checked | https://www.nngroup.com/articles/table-of-contents/ · https://www.nngroup.com/articles/in-page-links-content-navigation/ |
| Baymard, Avoid Horizontal Tabs (guideline 753 updated 2026-07) | 2026-07 | https://baymard.com/blog/avoid-horizontal-tabs |
| Baymard, Avoid Using Subpages | not checked | https://baymard.com/blog/avoid-using-subpages |
| Baymard, "Collapsed Sections" Layout on Mobile (guideline 1129, paywalled) | not checked | https://baymard.com/guidelines/1129-collapsed-sections-layout-on-mobile |
| Baymard, User-Friendly Comparison Tools (E. Scott) | 2022-10 (secondary citation) | https://baymard.com/blog/user-friendly-comparison-tools |
| Shneiderman, The Eyes Have It | 1996 | https://drum.lib.umd.edu/items/155a868e-fb83-4115-9899-9187ea8c0498 |
| Chrome for Developers, Exclusive Accordion (`name`) | 2023-12, Chrome 120 | https://developer.chrome.com/docs/css-ui/exclusive-accordion |
| Chrome for Developers, More options for styling `<details>` (`::details-content`) | 2024-11, Chrome 131 | https://developer.chrome.com/blog/styling-details |
| Chrome for Developers, `hidden=until-found` | not checked | https://developer.chrome.com/docs/css-ui/hidden-until-found |
| MDN, `<details>`; MDN blog, exclusive accordions | not checked | https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details · https://developer.mozilla.org/en-US/blog/html-details-exclusive-accordions |
| Dave Rupert, Why `<details>` is Not an Accordion | 2019-12 | https://daverupert.com/2019/12/why-details-is-not-an-accordion/ |
| The state of `<details>` in 2024 | 2024 | https://hellogreg.netlify.app/posts/the-state-of-details |
| Smashing Magazine, Designing the Perfect Accordion | 2017-06 | https://www.smashingmagazine.com/2017/06/designing-perfect-accordion-checklist/ |
| Apple HIG, Sheets; Segmented controls; Disclosure controls | not checked | https://developer.apple.com/design/human-interface-guidelines/sheets |
| Material Design, Bottom sheets | not checked | https://m3.material.io/components/bottom-sheets |
| Zillow press release, property page redesign (sections "What's Special", "Monthly Cost", "Neighborhood"; larger type for key facts) | 2023-10-23 | https://zillow.mediaroom.com/2023-10-23-Zillow-unveils-a-new-look-for-property-pages,-their-biggest-redesign-in-5-years |

What the platform guides added: Apple treats a half-height sheet as a progressive-disclosure step and asks for a visible
grabber only when the sheet can be resized; Material separates a standard sheet (page stays usable) from a modal one
(scrim, blocks the page). Both support the fixed-height modal sheet above. Nothing found gives a segment limit from
Apple itself; the "2 to 5 segments" figure is a community rule of thumb.

## 7. Where the research cuts against the request

1. **"Collapse every section."** NN/g's position is that collapsing costs visibility and a tap, and should be kept for
   content people can afford to miss. Baymard still saw 8% overlook collapsed sections. The request is safe only because
   each headline states the conclusion. So anything she must not miss (things to confirm, a lease-term catch, a price
   over her limit) has to be in the headline or chip, not only in the body.
2. **"See everything at a glance" in 1.5 screens.** Seven rows is what fits. A place carries more than seven topics, so
   some merge (parking into the car, tour questions into still-to-confirm). No source gives a tested maximum row count.
3. **Three places side by side.** NN/g: wordy cells fit about two columns on a phone. Three works only with short
   values (a figure and two or three words) and the label above the cells.
4. **Sticky jump chips** were on the list of patterns to cover. NN/g found many people do not notice a sticky table of
   contents, and a page that already fits in 1.5 screens does not need one. Recommended on the neighborhood page only.
5. **Animated height.** The one-line CSS technique is Chromium-only as of the sources found; Safari and Firefox open
   instantly. That is acceptable. A JavaScript height animation is not worth its bugs.
