'use strict';
// Demo content so a fresh install has something to read. The writers are
// fictional. The optional demo signals are synthetic too, and they exist only
// so the dashboard and front page have something to show. Set
// MARGIN_DEMO_SIGNALS=0 to seed pieces without them.

const crypto = require('node:crypto');
const { hashPassword } = require('./auth');
const { render } = require('./markdown');

const DAY = 86400000;

const AUTHORS = [
  { handle: 'mara', name: 'Mara Okafor', accent: 'vermilion',
    bio: 'Writes about work, institutions, and the gap between the org chart and what actually happens.',
    now: 'Now: interviewing night-shift supervisors about who really runs a hospital.',
    blogroll: '@june\n@theo\nhttps://en.wikipedia.org/wiki/Commonplace_book On commonplace books' },
  { handle: 'theo', name: 'Theo Lindqvist', accent: 'teal',
    bio: 'Cities, infrastructure, and the boring systems that decide how your day goes.',
    now: 'Now: riding every crosstown bus line in one city, end to end.',
    blogroll: '@ravi\n@mara\nhttps://www.gutenberg.org Project Gutenberg' },
  { handle: 'june', name: 'June Hale', accent: 'plum',
    bio: 'New here. Writing about attention, reading, and what we owe the things we finish.',
    now: 'Now: keeping a paper list of everything I finish. Fourteen so far.',
    blogroll: '@mara' },
  { handle: 'ravi', name: 'Ravi Menon', accent: 'moss',
    bio: 'Fixes things for a living. Writes about repair, tools, and objects that outlive their warranties.',
    now: 'Now: rebuilding a 1987 sewing machine with parts from three others.',
    blogroll: '@theo\nhttps://www.ifixit.com iFixit repair guides' },
];

const POSTS = [
  {
    author: 'mara', slug: 'the-meeting-is-the-work-now', daysAgo: 2,
    title: 'The Meeting Is the Work Now',
    dek: 'We keep treating meetings as interruptions. For most knowledge workers, they are the job.',
    body: `Most knowledge workers now spend more of their week coordinating work than doing it, and we still talk about meetings as if they were an interruption.

That framing costs us. If meetings are interruptions, the fix is fewer of them: a no-meeting Wednesday, a shorter default, a rule about agendas. Those fixes are fine. They also miss what happened.

## The work moved

Twenty years ago a mid-level analyst spent most of the day producing something: a model, a memo, a design. The meeting was where that thing got judged. Now the analyst's output is mostly *alignment*. It's the decision that four teams can live with, the dependency somebody agreed to unblock, the priority that survived the quarterly review.

That output only exists in rooms. You can't produce it alone at your desk, because it doesn't exist until other people agree to it.

> A calendar full of meetings isn't a sign the work is being avoided. Often it's the only place the work can happen.

## What changes if you believe that

First, you'd staff meetings the way you staff projects. Somebody owns the outcome. Somebody prepares. Somebody writes down what was decided, and the decision is the deliverable, not the notes.

Second, you'd measure them. We measure code shipped and tickets closed, and nobody measures whether the Tuesday sync produced a decision. Most don't. They produce a date for the next sync.

Third, you'd stop rewarding the people who "protect their focus time" by declining everything. In an organization where the work is coordination, declining the meeting doesn't protect the work. It moves the work onto someone else.

## The uncomfortable part

None of this means meetings are good. Most are bad, the way most first drafts are bad. The point is that bad meetings are bad *work*, and we fix bad work by getting better at it, not by pretending it isn't work.

The companies that figure this out will look strange from the outside. Fewer meetings, maybe, but every one of them will end with something written down that did not exist when it started.`,
  },
  {
    author: 'mara', slug: 'your-org-chart-is-a-fiction', daysAgo: 9,
    title: 'Your Org Chart Is a Fiction You Maintain',
    dek: 'Every company runs on two structures. Only one of them is written down.',
    body: `Every company has two org charts, and the one on the intranet is the less accurate of the two.

The written one says who reports to whom. The real one says who you actually go to when something breaks at 4 p.m. on a Friday. Those two maps overlap less than any HR department would like to admit.

## How the real chart forms

It forms around three things: who knows where the bodies are buried, who can say yes without asking anyone, and who answers messages. None of those are titles.

I once watched a finance team route every urgent approval through a senior analyst named Priya. She had no authority to approve anything. She knew which VP was in which time zone, which one read email on weekends, and which one would sign without reading if you framed it right. The formal chart had eleven boxes between the request and the signature. The real chart had one person.

## Why we keep the fiction

The written chart does real work. It tells people who evaluates them, who can fire them, and whose budget they sit in. It's a map of accountability, and it was never meant to be a map of how things get done.

The trouble starts when leaders mistake one for the other. A reorg redraws the boxes and leaves the real network untouched, then everyone is surprised when nothing changes. Or worse, a layoff removes someone like Priya because her box looked small, and three departments slow down for reasons nobody can name.

## What to do with this

Ask your team one question: *who do you go to when you're stuck?* Draw the answers. That is your company. Protect those people, pay them, and stop letting the reorg slides pretend they don't exist.`,
  },
  {
    author: 'theo', slug: 'the-bus-stop-is-the-city', daysAgo: 4,
    title: 'The Bus Stop Is the City',
    dek: 'You can learn more about a city from one bus stop than from its master plan.',
    body: `A city's real priorities are posted at its bus stops, and most of them say the same thing: you are not who this place was built for.

Look at what's there. Is there a bench, or a lean bar designed so nobody can lie down? Shelter from rain, or a pole with a sign? A schedule you can read, or a QR code that assumes you have data left this month?

## Small objects, big decisions

Every one of those choices went through a budget meeting. A shelter costs somewhere between eight and twenty thousand dollars installed. A city with three thousand stops that shelters a third of them has made a decision about who waits in the rain, and it made that decision one line item at a time.

The riders who wait longest are the ones least likely to show up to the meeting where it gets decided. They are working. That's why they're on the bus.

## The master plan tells a different story

The master plan has renderings: wide sidewalks, trees, people with tote bags. It talks about "mobility hubs." The plan isn't lying, exactly. It describes what the city wants to be, and the bus stop shows what it currently chooses to fund.

When I visit a new city I skip the downtown and ride one crosstown line end to end. By the third transfer you know whether the place takes its own plans seriously.

## A cheap test for any city

Count the benches on the route with the lowest-income riders, then count them on the route to the airport. If the airport route wins, you have your answer about whose time the city values. Every city I've tried this in, it wins.`,
  },
  {
    author: 'theo', slug: 'nobody-owns-the-sidewalk', daysAgo: 16,
    title: 'Nobody Owns the Sidewalk',
    dek: 'Why the most-used piece of public infrastructure is the one nobody is responsible for.',
    body: `In most American cities, the sidewalk in front of your house is legally your problem and practically nobody's.

The city owns the land. You, the adjacent property owner, are often required to repair it. The utility company is allowed to dig it up. The street tree that cracks it belongs to the parks department. When it breaks, four parties can each point at the other three.

## Fragmented ownership, predictable results

This is why sidewalks decay in patches. A block with a wealthy homeowner who repairs on time sits next to a block with a landlord who waits for the city to send a notice, which takes years because the inspection team is two people.

The people hurt most are the ones who can't step around a heaved slab: wheelchair users, parents with strollers, anyone over seventy-five. A street can be "fully accessible" on a city map and impassable in practice for three blocks.

## Some cities fixed it

A handful of cities took sidewalk repair back from property owners and treated it like streets: a city program, a budget, a schedule. It costs more on paper. It costs less once you count the lawsuits from trip-and-fall injuries, which a lot of cities pay quietly every year.

> The cheapest infrastructure is the kind someone is clearly responsible for.

The lesson generalizes. Whenever you see something shared that's falling apart, ask who owns it. The answer is usually "several people, sort of," and that's the whole problem.`,
  },
  {
    author: 'ravi', slug: 'the-screw-you-cant-turn', daysAgo: 3,
    title: 'The Screw You Can\u2019t Turn',
    dek: 'A single fastener tells you whether a company expects you to own the thing you bought.',
    body: `Every product tells you who it thinks owns it, and the message is usually hidden in a screw head.

A standard Phillips screw says: open me, you're allowed. A pentalobe or a tri-wing says the opposite. It isn't there for strength or cost. It's there so that the person holding the device can't get inside it without buying a special tool, and most people won't.

## What the fastener decides

Last month a neighbor brought me a coffee grinder that had stopped turning. The motor was fine. A plastic gear the size of a coin had split. The part costs about two dollars. To reach it I had to get past four security screws and a clip designed to snap on the way out.

The manufacturer's answer was a new grinder for ninety dollars. The fastener made that decision long before the gear broke.

## Repair is a design choice

We talk about repair as a skill, something you either have or don't. Mostly it's a permission. When the case opens with a coin, the manual lists part numbers, and the gear is sold separately, ordinary people fix things. When any one of those is missing, only professionals do, and they charge accordingly.

> A screw you can't turn is a policy you didn't vote for.

## What to look for

Before you buy anything with a motor or a battery, flip it over. Count the screw types. Search for the model number plus "teardown." If the first result is someone prying it open with a guitar pick and swearing, you're not buying the thing. You're renting it until the first part fails.`,
  },
  {
    author: 'june', slug: 'finishing-is-a-feature', daysAgo: 1,
    title: 'Finishing Is a Feature',
    dek: 'Almost everything on a screen is built so you never reach the end. Reading used to be the exception.',
    body: `The most radical thing a piece of writing can do now is end.

Feeds don't end. Video autoplays the next one. News sites put six more headlines under the one you came for. The whole design vocabulary of the last fifteen years has one goal, which is to make sure you never hit bottom.

## What finishing gives you

When you finish something you get a verdict. You get to decide whether it was worth it, whether you agree, whether you'll remember it. That judgment is where most of reading's value lives, and endless formats never let you reach it.

I started keeping a paper list of things I finished: essays, long articles, the occasional book. The list is short. It also contains nearly everything I can still remember reading last year. The things I scrolled past are gone.

## The reader I'm writing for

I think there are more of us than the metrics suggest. People who still read to the end, and who would read more if the reading didn't come wrapped in pop-ups asking for an email address before the first paragraph finished loading.

We don't need more content. We need *fewer, better* things, somewhere to put the lines that mattered, and permission to close the tab when we're done.

## A small promise

This piece ends in one more sentence, and nothing will play after it. If a line in it was worth keeping, keep it.`,
  },
];

function seed(h, { demoSignals = true, now = Date.now() } = {}) {
  if (h.get('SELECT count(*) AS n FROM authors').n > 0) return false;
  const pw = hashPassword('demo-password');
  h.tx(() => {
    const ids = {};
    AUTHORS.forEach((a, i) => {
      ids[a.handle] = Number(h.run('INSERT INTO authors (handle, name, bio, now_line, accent, blogroll, pw_hash, created_at) VALUES (?,?,?,?,?,?,?,?)',
        a.handle, a.name, a.bio, a.now, a.accent, a.blogroll, pw, now - (60 - i) * DAY).lastInsertRowid);
    });
    for (const p of POSTS) {
      const at = now - p.daysAgo * DAY;
      const words = render(p.body).words;
      const postId = Number(h.run(`INSERT INTO posts (author_id, slug, title, dek, body_md, words, status, published_at, created_at, updated_at)
        VALUES (?,?,?,?,?,?, 'published', ?,?,?)`, ids[p.author], p.slug, p.title, p.dek, p.body, words, at, at, at).lastInsertRowid);
      if (demoSignals) seedSignals(h, postId, ids[p.author], p, words, now);
    }
  });
  return true;
}

// Deterministic pseudo-random so demo numbers are stable across runs.
function rng(seedStr) {
  let x = parseInt(crypto.createHash('md5').update(seedStr).digest('hex').slice(0, 8), 16) || 1;
  return () => ((x = (x * 1103515245 + 12345) % 2147483648) / 2147483648);
}

function seedSignals(h, postId, authorId, p, words, now) {
  if (p.author === 'june' || p.author === 'ravi') return; // new voices start cold, like real ones would
  const r = rng(p.slug);
  const views = 180 + Math.floor(r() * 260);
  const blocks = render(p.body).blocks.length;
  for (let i = 0; i < views; i++) {
    const roll = r();
    const depth = roll < 0.28 ? r() * 0.3 : roll < 0.45 ? 0.3 + r() * 0.55 : 0.9 + r() * 0.1;
    const dwell = Math.floor(depth * words * (120 + r() * 260));
    h.run('INSERT INTO views (pv, post_id, max_depth, dwell_ms, source, created_at) VALUES (?,?,?,?,?,?)',
      crypto.randomUUID(), postId, depth, dwell, ['front', 'front', 'front', 'direct', 'passed', 'follow', 'ring', 'brief'][Math.floor(r() * 8)], now - Math.floor(r() * p.daysAgo * DAY));
  }
  const hot = Math.floor(r() * blocks);
  const keeps = 10 + Math.floor(r() * 30);
  for (let i = 0; i < keeps; i++) {
    const para = r() < 0.5 ? hot : Math.floor(r() * blocks);
    h.run('INSERT INTO keeps (post_id, para, created_at) VALUES (?,?,?)', postId, para, now);
  }
  const follows = 4 + Math.floor(r() * 12);
  for (let i = 0; i < follows; i++) h.run('INSERT INTO follow_events (author_id, post_id, delta, created_at) VALUES (?,?,1,?)', authorId, postId, now);
  const passes = 2 + Math.floor(r() * 9);
  for (let i = 0; i < passes; i++) h.run('INSERT INTO passes (post_id, para, created_at) VALUES (?,?,?)', postId, hot, now);
  for (let i = 0; i < 3; i++) h.run('INSERT INTO tips (post_id, amount_cents, created_at) VALUES (?,?,?)', postId, [300, 500, 1000][i], now);
  const shown = 30 + Math.floor(r() * 40);
  for (let i = 0; i < shown; i++) h.run(`INSERT INTO asks (post_id, kind, event, created_at) VALUES (?, 'follow', 'shown', ?)`, postId, now);
  for (let i = 0; i < follows; i++) h.run(`INSERT INTO asks (post_id, kind, event, created_at) VALUES (?, 'follow', 'accepted', ?)`, postId, now);
}

module.exports = { seed, AUTHORS, POSTS };
