# Margin: design rationale

Margin is a publishing platform where readers never need an account to read. This document covers who it's for, what their problem is, which value we chose to offer and why, and the parts that are still unsolved.

## 1. The persona: the Deliberate Reader

Relatively few people still read long-form writing to the end, and that small group is easy to describe.

**Who they are**
- 30–65, mostly working professionals: managers, analysts, clinicians, teachers, engineers, policy people.
- They read to *think*, not to be informed. They want the argument, not the headline.
- They already pay for something: a newspaper, two or three Substacks, a podcast network.
- Their reading happens in 10–25 minute windows: early morning, a commute, late evening.

**What their week looks like**
- An inbox with a dozen newsletters, most unread, each one a small debt.
- Three or four sign-up pop-ups a day before a first paragraph finishes loading.
- Pieces they meant to finish lost in open tabs.
- They remember reading something brilliant last month and can't find it or quote it.
- Nobody they know read the same piece, so they have no one to argue with about it.

**Problem statement (design-thinking form)**
> The Deliberate Reader needs a way to spend a limited reading budget on a few pieces that are worth it, and to keep what they learned from them, because today's platforms charge for attention up front (sign-ups, pop-ups, inboxes) and give nothing back afterward (no memory, no conversation, no end).

**What they're really hiring a reading platform to do (jobs to be done)**
1. *Help me pick.* "Tell me which three things are worth my 20 minutes."
2. *Let me just read.* "Don't make me pay with my email before I know it's any good."
3. *Help me keep it.* "When a line hits, let me hold on to it and find it again."
4. *Let me be done.* "Give me an end, so I can close the tab without guilt."
5. *Let me talk about it*, but only with people who also read it.

## 2. The value, categorized

We listed every value a reading platform could offer this reader and scored each on (a) how much it relieves their actual pain, (b) whether it works *without an account* on day one, and (c) whether it gets more valuable over time, which is what creates a reason to come back and eventually to get a key.

| Category | What it means here | Pain relieved | Works with no account? | Compounds? |
|---|---|---|---|---|
| **Access** | No wall, no pop-up, no app nag | High | Yes | No |
| **Time / curation** | A short, finite page ranked by completion | High | Yes | Slightly |
| **Memory** | Keep passages, resurface them, export them | High | Yes (local) | **Yes, strongly** |
| **Conversation** | Notes anchored to paragraphs, from people who read it | Medium | Read: yes. Write: needs key | Yes |
| **Trust / privacy** | No cookies, no tracking, no identity | Medium | Yes | No |
| **Status / identity** | Profiles, badges, streaks | Low for this persona | No | Yes, but corrosive |
| **Discovery** | Fair exposure for new writers | Medium | Yes | Yes |

**Decision:** Margin leads with **Memory**, with **Time** in support. Access and privacy are the minimum requirement, the thing we promise, but they're easy to copy, and a free Substack post is already mostly readable. What nobody gives this reader is a place to *keep* what they read, plus a feed that *ends*. Memory is also the value that builds up: every passage kept makes the next visit more valuable, and it's the natural reason to get a reader key. Status features were rejected outright. Streaks and badges optimize for coming back, and this persona wants to *finish and leave*.

## 3. How that turns into product

### Reader, no account (the default)
- **Every piece in full.** No modal, no "continue in app." Readers get no cookies at all.
- **Today** is at most 7 pieces with a total reading time and a hard bottom ("That's today."). Each card says *why* it's there ("Finished by 56% of people who opened it", "New voice").
- **Keep** any selected passage. It goes into a local commonplace book with a link back to the paragraph, and one kept passage resurfaces at the top of Today on later visits.
- **Follow** a writer without email. New pieces from them sit at the top of Today on that device.
- **RSS** for everything and for each writer, the oldest no-account follow there is.

### The earned ask (the enticement to go further)
The reader is never asked for anything before they've **finished** a piece, meaning they reached 90% depth and the page was visible for at least a third of normal reading time. Then exactly one ask appears, in this order:
1. Follow this writer (no account, local).
2. Once they follow and have finished 3 pieces or kept 3 passages: get a **reader key**, framed around what they'd lose ("You've kept 4 passages. They only live in this browser.").
3. Always: "Pay what it was worth." A tip with no account (simulated in this prototype).

### The reader key (the "account" that isn't one)
Four words and a code (`otter-granite-plum-fjord-7KQ2MX`). The server stores only a hash. It adds:
- sync of commonplace, follows and finished pieces across devices, with merge by newest edit;
- the right to write **margin notes**. The key requirement is the spam control, and no identity is needed for it;
- optionally an email for **The Brief**: one email a week, five pieces at most, followed writers first;
- optionally "share my email with writers I follow." This is how a writer's list forms, and it's the reader's explicit choice.

### Writer value (even with no network)
- **More finishers.** Every login wall and pop-up loses readers. Here there aren't any.
- **Better signal than open rates**: opens, *verified* reads, finish rate, median depth, a per-paragraph map of where readers leave and what they kept, and margin notes.
- **Earned-ask funnel**: how often finishing readers were asked to follow, and how often they said yes.
- **A portable list**: opted-in reader emails, exportable as CSV at any time. Writers own their audience.
- **A draft check** taken from the SuperWritingEngine voice spec (A.1 openings, A.2 hedges/filler/nominalizations, A.3 negation framing). It's advisory and never blocks.

## 4. Cold start, honestly

The network is worth nothing on day one. What we do about it:

- **Single-player value for readers.** The commonplace and a finite page are useful even with only five pieces on the site. A reader doesn't need other readers to get value.
- **Single-player value for writers.** The analytics and draft check are useful with 50 readers. A writer can post here *instead of* a bare blog and get more information back.
- **Held slots for new writers.** Two of the seven front-page slots go to writers with under 150 total opens, ranked by smoothed completion rate. A new writer is judged on whether people finish them, not on how many followers they have.
- **Ranking uses a prior**: quality = (reads + ½·keeps + 2·tips + 2) / (opens + 4), so two unlucky early views don't bury a piece.

What we *haven't* solved (see §6): why a writer with an existing Substack audience would move. The realistic wedge is **writers without an audience yet**, and **writers who hate what the login wall does to their completion rate**.

## 5. Privacy model

- Readers get no cookies. Each page view gets a random id in page memory and sends depth plus visible, active dwell time.
- IP addresses are used only for in-memory rate limiting and never stored.
- Kept passages are stored server-side as *paragraph index only*, never text or identity, for the "Kept by N readers" marker and the writer's map. The text lives in the reader's browser, or in their key's blob if they choose to sync.
- Writers (and only writers) have a session cookie.

## 6. Open questions and known weaknesses

1. **Gameable anonymous signals.** Follows and tips are anonymous and can be inflated, and rate limiting only slows that down. Real payments (Stripe) would make tips trustworthy. For follows, weight keyed follows more heavily over time.
2. **Key loss.** A lost key can't be recovered, by design. Adding an optional email makes recovery possible but weakens the "no identity" promise. This is a real product decision, and I haven't made it.
3. **Email delivery.** The Brief is built (`npm run digest`) but written to an outbox, not sent.
4. **Moderation.** Margin notes need a key, but there's no report or hide flow yet, and writers can't remove notes on their own pieces. That needs adding before any public launch.
5. **The moat question.** "No login to read" is not defensible by itself. Any blog, and Ghost, already does it. The defensible part, if there is one, is the kept-passage graph, the completion-ranked discovery, and the reader key that follows you. Validate this with real Deliberate Readers before building more.
6. **Import.** Writers can't import a Substack/Ghost archive or subscriber CSV yet. That's the most important feature for the cold start, and it isn't built.
