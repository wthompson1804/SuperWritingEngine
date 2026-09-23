# Margin: design rationale (v2)

Margin is a long-form publishing platform where readers never need an account to read. This document covers who it's for, what changed between v1 and v2 and why, and what's still unproven.

> **Honesty note.** Every persona below is a hypothesis built from desk reasoning. None of it comes from interviews or usage data. §7 lists the cheapest way to test each one. Treat the design as a set of bets, not findings.

---

## 1. What v1 got wrong

v1 designed for one reader (the Deliberate Reader) and treated writers as one undifferentiated group. Going back over the personas turned up four problems:

1. **The front page was designed for regulars, but most readers arrive through a shared link.** On any platform that isn't already a habit, most first visits land on a single article, not the home page. The article page is the real front door, and in v1 it was a dead end.
2. **Readers were treated as isolated.** v1 had no role for the reader who *sends things to people*. That reader is the distribution engine, and the early web was built by people like them: link pages, webrings, "cool site of the day."
3. **Writers weren't differentiated.** A writer with no audience, an expert who writes four times a year, and an established newsletter writer who's tired of their platform need different things. v1 served the first one fairly well and the other two barely at all.
4. **The dashboard talked to writers like marketers.** Funnels and follower counts are fine, but the feeling this community should have is *"people read this, kept this line, and sent it to a friend,"* not *"conversion rate 21%."*

---

## 2. Reader personas

### R1. The Passer-by (most first visits)
- **Who:** Someone who clicked a link a friend sent, or one they saw in a group chat, on Bluesky, or in a Slack channel. They have no idea what Margin is and no intention of joining anything.
- **Their moment:** Phone, in a queue or on a couch, with 4 minutes and low patience.
- **What they need:** To read the piece instantly with no interruptions, then a reason to trust the *next* link they see here.
- **What makes them leave:** Any pop-up, "open in app," cookie wall, or a page that doesn't end.
- **What would bring them back:** A second piece that's as good as the first. A passage the friend picked, highlighted, so the link feels personal.
- **v2 response:** Arrival from a passed link highlights the passage and says "Someone passed this to you." The end of every piece has the writer's own reading list, one more piece by them, one elsewhere, and the ring. Nothing is asked of them until they finish.

### R2. The Deliberate Reader (the regular, from v1)
- **Who:** Reads to think. 30–65. Has more to read than time. Pays for a few things already.
- **What they need:** A short list that ends, and somewhere to keep what mattered.
- **v2 response:** Everything from v1 (finite Today, commonplace, resurfacing, reader key, The Brief), plus visited links now turn purple, so the page quietly shows what you've already read.

### R3. The Passer-on (new in v2: the connector)
- **Who:** The person in every friend group who says "you have to read this." They used to keep a links page. Now they paste URLs into chats.
- **What they need:** To share *the part that matters*, not the whole article, with confidence it will land well for the person receiving it.
- **What they get from the platform:** Being the source of something good, which is social capital. Ideally they'd see that it landed, without anyone being surveilled.
- **v2 response:** **Pass it on**: select a passage and get a quote plus a link that opens right at it, highlighted. On mobile it uses the phone's share sheet. It's counted anonymously for the writer ("passed on"). No account is needed to pass something on, and no identity travels with the link.

---

## 3. Writer personas

### W1. The Newcomer
- **Who:** Writes well and has no audience. Maybe started a newsletter that has 40 subscribers, mostly friends.
- **Core problem:** Distribution. They'll write for months into silence and quit.
- **What they need:** A fair first read, signal about whether it's working, and other writers pointing at them.
- **v2 response:** Two held front-page slots (as in v1). The **ring**, where every writer's homepage links to the next and "random" sends readers around. A **"from the ring" spotlight** on Today that favors writers with the fewest opens. **Blogrolls**: established writers list who they read, and those lists appear under every one of their pieces, so an established writer's readers flow to newcomers. **"Who lists you"** on the desk shows the newcomer that someone noticed.

### W2. The Occasional Expert
- **Who:** A nurse, engineer, or planner who writes three or four serious pieces a year. They don't want a newsletter business, a posting cadence, or a subscriber count to feed.
- **Core problem:** Every platform pushes them into the newsletter treadmill ("your subscribers haven't heard from you in 30 days").
- **What they need:** A *homepage* rather than a list to feed, with pieces that stay findable, and no pressure.
- **v2 response:** Writer pages are homepages: name, a "now" line ("Now: interviewing night-shift supervisors…"), their own accent color, what they've written, and who they read. Margin never nags about frequency. The ring lists writers by arrival order, not activity, so being quiet doesn't bury you.

### W3. The Refugee
- **Who:** An established writer with a list elsewhere who is tired of growth-hacking pop-ups being done to their readers in their name, and of not controlling their own list.
- **Core problem:** Trust and portability. They've been burned by a platform changing the rules.
- **What they need:** Their readers treated with respect, their list exportable, and an easy exit.
- **v2 response:** No pop-ups on their work, ever. A CSV list export (readers opt in to sharing their email). RSS for everything. Blogrolls that can link *off* Margin. The Declaration (§8 of it: "You can always leave") as a public commitment.
- **Still missing:** importing an existing Substack/Ghost archive and subscriber list. This is the biggest gap for W3, and it isn't built.

---

## 4. Value, re-categorized by persona

| Value | R1 Passer-by | R2 Deliberate | R3 Passer-on | W1 Newcomer | W2 Occasional | W3 Refugee |
|---|---|---|---|---|---|---|
| **Access** (no wall) | ★★★ | ★★ | ★★ (the person they send to gets in) | ★★ (more finishers) | ★ | ★★★ |
| **Time** (finite) | ★ | ★★★ | · | · | · | · |
| **Memory** (commonplace) | · | ★★★ | ★ | · | · | · |
| **Connection** (pass on, ring, blogroll) | ★★ | ★ | ★★★ | ★★★ | ★★ | ★ |
| **Signal** (what readers did) | · | · | ★ | ★★★ | ★★ | ★★ |
| **Ownership** (export, RSS, homepage) | · | ★ | · | ★ | ★★★ | ★★★ |

**The v2 insight:** v1 bet on *Memory*. v2 keeps that bet for the regular reader, but the value that serves the most personas at once is **Connection**: people pointing at each other. It's also the value most in keeping with the early web, and it's the direct answer to cold start, because distribution comes from readers and writers pointing at things, not from an algorithm.

---

## 5. The look: "the 1996 default web, remade with care"

The brief was "the early internet, when people cared about each other and were weird, but not a carbon copy." The approach was to take the *defaults* of the early web and rebuild each one properly.

| Then | Now in Margin | Why it matters |
|---|---|---|
| Times New Roman body | **Newsreader**, a modern variable serif designed for screens | Same feeling, much better reading |
| Courier for anything technical | **IBM Plex Mono** for all navigation, labels, and counters | The "machinery" of the page stays visible |
| Blue underlined links, purple when visited | Kept exactly, in a deeper ultramarine / violet | "You've been here" is useful, and it's honest |
| Grey window chrome | Hard-edged boxes with title bars (`status.txt`) and offset shadows | Pages feel handmade, not glassy |
| Graph-paper/tiled backgrounds | A faint 24px grid | Texture without noise |
| Hit counter | **"N reading now · finished by N people"**: the counter made honest (counts real attention, not page loads) | The sense that other people are here |
| Webring | **The ring**: prev · random · next on every homepage and piece | Distribution between writers |
| Links page | **Blogroll**: "theo reads", including links off Margin | Generosity as a feature |
| 88×31 buttons | CSS-drawn badges in the footer: NO LOGIN, NO TRACKERS, RSS, THE RING, DECLARED | Promises stated as small artifacts |
| `[bracketed] nav` | Kept | Instantly familiar, keyboard-friendly |
| Declaration of independence manifestos | **Our own Declaration for Readers & Writers**: eight short commitments, original text | Values stated publicly so they can be held to |

Modern commitments that the early web didn't have: accessible contrast (4.5:1 minimum, checked for every writer accent color in light and dark), 44px touch targets, visible focus, a respected reduced-motion setting, a mobile-first layout, dark mode, and self-hosted fonts so no third party sees a reader's IP.

---

## 6. Privacy model (unchanged, plus two additions)

- Readers get no cookies. Each open tab mints a random id and reports scroll depth, visible time, and paragraph *numbers* kept or passed on.
- **New:** "reading now" counts page views that sent a heartbeat in the last 90 seconds *while visible*. Hiding the tab removes you from the count.
- **New:** passed-on links carry only the piece and paragraph number, `?via=passed&p=7`. Nothing about who passed it.
- No IPs stored (in-memory rate limiting only). Fonts are self-hosted.

---

## 7. How to test these hypotheses cheaply

| Hypothesis | Cheapest test | What would change our mind |
|---|---|---|
| Most readers arrive via shared links (R1) | Deploy, share 10 pieces, look at the `source` breakdown on the desk after 2 weeks | Most opens come from Today → the home page matters more than we think |
| People will pass on *passages*, not whole links (R3) | Count passes per verified read | Under ~2% → the feature is decoration; fold it into Keep |
| Blogrolls move readers to newcomers (W1) | Compare `ring` and `next` opens for listed vs unlisted newcomers | No difference → the ring is nostalgia, not distribution |
| Occasional experts want a homepage, not a newsletter (W2) | 5 interviews with people who've written one strong post in the last year | They want email-first → put The Brief-per-writer ahead of homepages |
| Refugees need import more than anything (W3) | 5 interviews with writers who have 1k+ subscribers elsewhere | Import is table stakes → build it before anything else |

---

## 8. Open questions and known weaknesses

1. **Import is missing** (W3). It's the most important unbuilt feature.
2. **Anonymous signals are gameable.** Follows, passes, tips and "reading now" can be inflated by a script. Rate limits only slow this down. Mitigation later: weight keyed actions more heavily, and look for anomalies.
3. **Key loss** is still unrecoverable by design. Whether to offer email recovery is your call.
4. **Moderation**: margin notes have no report or hide flow, and writers can't remove notes on their own pieces yet.
5. **The ring doesn't scale as a flat list.** At 500 writers it needs topics or smaller sub-rings. That's a nice problem to have.
6. **Payments and email are simulated.** Both are well-solved problems, deliberately deferred.
7. **The moat question** from v1 still stands. "No login" isn't defensible. The combination of passage-level sharing, a ring that routes readers to newcomers, and a reader-owned commonplace might be. That's the bet.
