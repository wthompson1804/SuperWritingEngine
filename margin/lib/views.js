'use strict';
const { esc } = require('./markdown');
const { readingMinutes } = require('./signals');

class Raw { constructor(s) { this.s = s; } toString() { return this.s; } }
const raw = (s) => new Raw(s);
function show(v) {
  if (v == null || v === false) return '';
  if (v instanceof Raw) return v.s;
  if (Array.isArray(v)) return v.map(show).join('');
  return esc(v);
}
function h(strings, ...vals) {
  let out = '';
  strings.forEach((s, i) => { out += s; if (i < vals.length) out += show(vals[i]); });
  return raw(out);
}

const fmtDate = (ms) => new Date(ms).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
const fmtTime = (ms) => new Date(ms).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC' }) + ' UTC';
const pct = (x) => `${Math.round(x * 100)}%`;
const money = (c) => `$${(c / 100).toFixed(2)}`;
const pad2 = (n) => String(n).padStart(2, '0');
const plural = (n, one, many = one + 's') => `${n} ${n === 1 ? one : many}`;
const SOURCE_LABEL = { front: 'Today page', direct: 'Direct / elsewhere', passed: 'Passed on by a reader', follow: 'Followers', ring: 'The ring', brief: 'The Brief', author: 'Your homepage', next: 'End of another piece' };

const NAV = [
  ['/', 'today', 'today'],
  ['/ring', 'the ring', 'ring'],
  ['/commonplace', 'commonplace', 'commonplace'],
  ['/brief', 'the brief', 'brief'],
  ['/declaration', 'declaration', 'declaration'],
];

function layout({ title, body, author, scripts = [], data, active = '', accent = '', path = '/' }) {
  return '<!doctype html>' + h`<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title ? `${title} · Margin` : 'Margin: read anything, keep what matters'}</title>
<meta name="description" content="Long-form writing you can read without an account. Keep what matters. Pass it on.">
<meta name="color-scheme" content="light dark">
<link rel="preload" href="/static/fonts/newsreader-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/static/style.css">
<link rel="alternate" type="application/rss+xml" title="Margin" href="/feed.xml">
</head>
<body${raw(accent ? ` class="acc-${esc(accent)}"` : '')}>
<a class="skip" href="#main">Skip to content</a>
<header class="site">
  <div class="site-inner">
    <a class="brand" href="/" aria-label="Margin, home"><span class="pilcrow" aria-hidden="true">¶</span>Margin</a>
    <p class="addr" aria-hidden="true">margin<span>${path}</span></p>
    <nav aria-label="Site">
      ${NAV.map(([href, label, key]) => h`<a href="${href}"${raw(active === key ? ' aria-current="page"' : '')}>${label}</a>`)}
      ${author ? h`<a href="/dashboard"${raw(active === 'dashboard' ? ' aria-current="page"' : '')}>desk</a>` : h`<a href="/write"${raw(active === 'write' ? ' aria-current="page"' : '')}>write</a>`}
    </nav>
  </div>
</header>
<main id="main">${body}</main>
<footer class="site">
  <div class="site-inner">
    <ul class="badges" aria-label="What this site promises">
      <li><span class="badge b-login"><b>NO</b> LOGIN</span></li>
      <li><span class="badge b-track"><b>NO</b> TRACKERS</span></li>
      <li><a class="badge b-rss" href="/feed.xml"><b>RSS</b> FEED</a></li>
      <li><a class="badge b-ring" href="/ring"><b>↻</b> THE RING</a></li>
      <li><a class="badge b-decl" href="/declaration"><b>§</b> DECLARED</a></li>
    </ul>
    <p>Best viewed in any browser, at any size, with no account. What you keep stays in your browser unless you ask us to hold it.</p>
    <p class="mono small"><a href="/about">how this works</a> · <a href="/ring">every writer here</a> · <a href="/feed.xml">rss</a></p>
  </div>
</footer>
${data ? h`<script type="application/json" id="page-data">${raw(JSON.stringify(data).replace(/</g, '\\u003c'))}</script>` : ''}
<script src="/static/local.js"></script>
${scripts.map((s) => h`<script src="/static/${s}"></script>`)}
</body>
</html>`.s;
}

function box(title, inner, cls = '') {
  return h`<section class="box ${cls}"><p class="bar"><span>${title}</span><span aria-hidden="true">□ ×</span></p><div class="box-body">${inner}</div></section>`;
}

function card(s, i) {
  return h`<li class="card${s.newVoice ? ' new-voice' : ''}" data-slug="${s.slug}">
    <span class="num" aria-hidden="true">${pad2(i + 1)}</span>
    <div class="card-main">
      <p class="why">${s.newVoice ? h`<span class="flag">new voice</span> ` : ''}${s.newVoice ? 'Here so it gets a fair read.' : s.reason}</p>
      <h2><a href="/p/${s.slug}">${s.title}</a></h2>
      ${s.dek ? h`<p class="dek">${s.dek}</p>` : ''}
      <p class="meta"><a href="/@${s.handle}">${s.author_name}</a> · ${s.minutes} min<span class="done-mark" hidden> · ✓ finished</span></p>
    </div>
  </li>`;
}

function home({ picks, author, liveNow, spot, now }) {
  const minutes = picks.reduce((n, s) => n + s.minutes, 0);
  return layout({
    author, active: 'today', scripts: ['home.js'], path: '/today',
    data: { picks: picks.map((s) => s.slug) },
    body: h`
<div class="home">
  <section class="masthead">
    <h1>Today’s reading</h1>
    <p class="lede">${plural(picks.length, 'piece')}, about ${minutes} minutes. That’s the whole page. Read what you like, keep the lines that matter, and pass them on.</p>
  </section>

  <ol class="picks" aria-label="Today's pieces">
    ${picks.map(card)}
  </ol>
  <section class="finish-line" aria-label="End of page">
    <p class="mono">— end of today —</p>
    <p>There’s nothing below this line on purpose. Pieces are here because people <em>finished</em> them. Two places are always held for writers nobody has heard of yet.</p>
  </section>

  <aside class="rail" aria-label="Around the site">
    ${box('status.txt', h`<dl class="status">
      <div><dt>pieces</dt><dd>${picks.length}</dd></div>
      <div><dt>minutes</dt><dd>${minutes}</dd></div>
      <div><dt>reading now</dt><dd><span class="live" aria-hidden="true"></span>${liveNow}</dd></div>
      <div><dt>accounts required</dt><dd>0</dd></div>
      <div><dt>updated</dt><dd>${fmtTime(now)}</dd></div>
    </dl>`)}
    <div id="resurface" hidden>${box('from your commonplace', h`<blockquote id="resurface-text"></blockquote><p class="meta" id="resurface-meta"></p>`, 'resurface')}</div>
    <div id="following" hidden>${box('writers you follow', h`<div id="following-list"></div>`)}</div>
    ${spot ? box('from the ring', h`<p class="spot-name"><a href="/@${spot.handle}?via=ring">${spot.name}</a></p>
      ${spot.now_line ? h`<p class="now-line">${spot.now_line}</p>` : ''}
      ${spot.latest_slug ? h`<p class="small">Latest: <a href="/p/${spot.latest_slug}?via=ring">${spot.latest_title}</a></p>` : ''}
      <p class="small mono"><a href="/ring">see every writer →</a></p>`, 'spot') : ''}
  </aside>
</div>`,
  });
}

function ringBar(handle) {
  return h`<nav class="ringbar" aria-label="The Margin ring">
    <a href="/ring/prev?from=${handle}" rel="prev">← prev</a>
    <a href="/ring" class="ring-home"><span aria-hidden="true">↻</span> the margin ring</a>
    <a href="/ring/random?from=${handle}">random</a>
    <a href="/ring/next?from=${handle}" rel="next">next →</a>
  </nav>`;
}

function blogrollList(items) {
  return h`<ul class="blogroll">${items.map((b) => h`<li><a href="${b.href}"${raw(b.kind === 'web' ? ' rel="noopener"' : '')}>${b.title}</a>${b.note ? h` <span class="muted small">${b.kind === 'web' ? `(${b.note})` : `· ${b.note}`}</span>` : ''}</li>`)}</ul>`;
}

function article({ post, author, rendered, notes, topKeep, keepCounts, next, viewer, stats, blogroll }) {
  const minutes = readingMinutes(post.words);
  const notesByPara = new Map();
  for (const n of notes) { if (!notesByPara.has(n.para)) notesByPara.set(n.para, []); notesByPara.get(n.para).push(n); }
  return layout({
    title: post.title, author: viewer, scripts: ['read.js'], accent: author.accent, path: `/p/${post.slug}`,
    data: {
      slug: post.slug, title: post.title, words: post.words, minMs: post.words * 87,
      author: { handle: author.handle, name: author.name },
      noteCounts: Object.fromEntries([...notesByPara].map(([p, ns]) => [p, ns.length])),
      topKeep, keepCounts,
    },
    body: h`
<div class="reading">
<article class="piece sheet" id="piece">
  <header class="piece-head">
    <p class="kicker mono"><a href="/@${author.handle}">${author.name}</a></p>
    <h1>${post.title}</h1>
    ${post.dek ? h`<p class="dek">${post.dek}</p>` : ''}
    <p class="meta mono">${fmtDate(post.published_at)} · ${minutes} min read</p>
    <p class="counter mono" id="counter" aria-live="off">
      <span class="live" aria-hidden="true"></span><span id="now-n">${stats.now}</span> reading now · ${stats.reads ? h`finished by <span id="fin-n">${stats.reads}</span> ${stats.reads === 1 ? 'person' : 'people'}` : 'be the first to finish it'}
    </p>
  </header>
  <div class="passed-banner" id="passed-banner" hidden role="note">
    <p><strong>Someone passed this to you.</strong> The passage they picked is highlighted below.</p>
  </div>
  <div class="body" id="body">${raw(rendered.html)}</div>
  <p class="hint mono" id="hint">tip: select any sentence to keep it, pass it on, or write in the margin</p>
</article>

<section class="finish box" id="finish" hidden aria-live="polite">
  <p class="bar"><span>you finished it</span><span aria-hidden="true">✓</span></p>
  <div class="box-body">
    <div id="ask"></div>
    <div class="tip" id="tip">
      <p><strong>Pay what it was worth.</strong> No account. All of it goes to ${author.name}.</p>
      <div class="row">
        ${[300, 500, 1000].map((c) => h`<button class="btn" type="button" data-tip="${c}">${money(c)}</button>`)}
      </div>
      <p class="muted small">Prototype: no money moves; the tip is only recorded.</p>
      <p class="ok small" id="tip-thanks" hidden role="status">Thank you. ${author.name} will see it.</p>
    </div>
  </div>
</section>

<section class="after">
  ${blogroll.length ? box(`${author.name.split(' ')[0].toLowerCase()} reads`, blogrollList(blogroll.slice(0, 5)), 'reads') : ''}
  <div class="next">
    ${next.same ? h`<a class="next-card" href="/p/${next.same.slug}?via=next"><span class="label">more from ${author.name}</span><span class="t">${next.same.title}</span><span class="muted small">${readingMinutes(next.same.words)} min</span></a>` : ''}
    ${next.other ? h`<a class="next-card" href="/p/${next.other.slug}?via=next"><span class="label">elsewhere on margin</span><span class="t">${next.other.title}</span><span class="muted small">${next.other.author_name} · ${readingMinutes(next.other.words)} min</span></a>` : ''}
  </div>
  ${ringBar(author.handle)}
</section>

<section class="margin-notes" id="notes" aria-labelledby="notes-h">
  <h2 id="notes-h">In the margin</h2>
  <p class="muted">Notes readers left on particular passages. Anyone can read them. Writing one takes a reader key: four words, no email.</p>
  ${notes.length ? [...notesByPara].sort((a, b) => a[0] - b[0]).map(([p, ns]) => h`
    <div class="note-group" id="notes-p${p}" data-p="${p}">
      ${ns[0].quote ? h`<blockquote class="note-quote"><a href="#p-${p}">${ns[0].quote}</a></blockquote>` : h`<p class="muted small">On paragraph ${p + 1}</p>`}
      ${ns.map((n) => h`<div class="note"><p>${n.body}</p><p class="meta mono">— ${n.display_name}, ${fmtDate(n.created_at)}</p></div>`)}
    </div>`) : h`<p class="empty" id="notes-empty">Nothing in the margin yet. Select a passage and choose “note” to write the first one.</p>`}
  <form class="note-form box" id="note-form" hidden>
    <p class="bar"><span>new margin note</span></p>
    <div class="box-body stack">
      <blockquote class="note-quote" id="note-quote"></blockquote>
      <label>Your note <textarea name="body" maxlength="1200" rows="3" required></textarea></label>
      <label>Sign it as <input name="name" maxlength="40" placeholder="a reader"></label>
      <div class="row"><button class="btn primary" type="submit">Add to the margin</button> <button class="btn" type="button" id="note-cancel">Cancel</button></div>
    </div>
  </form>
</section>
</div>

<div class="selbar" id="selbar" hidden role="toolbar" aria-label="Do something with this passage">
  <button type="button" data-act="keep">keep</button>
  <button type="button" data-act="pass">pass it on</button>
  <button type="button" data-act="note">note</button>
</div>`,
  });
}

function authorPage({ author, posts, viewer, blogroll, recommendedBy }) {
  return layout({
    title: author.name, author: viewer, scripts: ['author.js'], accent: author.accent, path: `/@${author.handle}`,
    data: { handle: author.handle, name: author.name },
    body: h`
<div class="homepage">
  <section class="hp-head">
    <p class="kicker mono">@${author.handle}’s homepage</p>
    <h1>${author.name}</h1>
    ${author.bio ? h`<p class="lede">${author.bio}</p>` : ''}
    ${author.now_line ? h`<p class="now-line">${author.now_line}</p>` : ''}
    <div class="row">
      <button class="btn primary" type="button" id="follow-btn" data-handle="${author.handle}" aria-pressed="false">Follow</button>
      <a class="btn" href="/feed.xml?author=${author.handle}">RSS</a>
    </div>
    <p class="small muted">Following needs no account. It’s remembered in this browser.</p>
  </section>
  <section class="hp-posts">
    <h2 class="label">Writing</h2>
    ${posts.length ? h`<ol class="picks plain-picks">${posts.map((p) => h`<li class="card" data-slug="${p.slug}"><div class="card-main">
      <h2><a href="/p/${p.slug}?via=author">${p.title}</a></h2>
      ${p.dek ? h`<p class="dek">${p.dek}</p>` : ''}
      <p class="meta">${fmtDate(p.published_at)} · ${readingMinutes(p.words)} min<span class="done-mark" hidden> · ✓ finished</span></p>
    </div></li>`)}</ol>` : h`<p class="empty">Nothing published yet. Check back, or follow to see it first.</p>`}
  </section>
  <aside class="rail">
    ${blogroll.length ? box(`${author.name.split(' ')[0].toLowerCase()} reads`, blogrollList(blogroll)) : ''}
    ${recommendedBy.length ? box('read by', h`<ul class="blogroll">${recommendedBy.map((a) => h`<li><a href="/@${a.handle}">${a.name}</a></li>`)}</ul>`) : ''}
  </aside>
  ${ringBar(author.handle)}
</div>`,
  });
}

function ringPage({ ring, viewer }) {
  return layout({
    title: 'The ring', author: viewer, active: 'ring', path: '/ring',
    body: h`
<section class="masthead">
  <h1>The ring</h1>
  <p class="lede">Every writer on Margin, in the order they arrived. No follower counts and no leaderboard. Each homepage links to the next one, like webrings did.</p>
</section>
<ol class="ring-list">
  ${ring.map((a, i) => h`<li class="ring-item acc-${a.accent}">
    <span class="num" aria-hidden="true">${pad2(i + 1)}</span>
    <div>
      <h2><a href="/@${a.handle}?via=ring">${a.name}</a> <span class="muted small mono">@${a.handle}</span></h2>
      ${a.now_line ? h`<p class="now-line">${a.now_line}</p>` : ''}
      <p class="meta mono">${plural(a.pieces, 'piece')} · last ${fmtDate(a.last_at)}</p>
    </div>
  </li>`)}
</ol>
<p class="mono small center"><a href="/ring/random">↻ take me somewhere random</a></p>`,
  });
}

function commonplace({ viewer }) {
  return layout({
    title: 'Commonplace', author: viewer, active: 'commonplace', scripts: ['commonplace.js'], path: '/commonplace',
    body: h`
<section class="masthead">
  <h1>Your commonplace</h1>
  <p class="lede">Every passage you keep ends up here, grouped by piece, with room for your own notes. It lives in this browser only, unless you get a reader key.</p>
</section>
<div class="cp-layout">
  <section id="cp-list" aria-live="polite"><p class="empty">Loading your passages…</p></section>
  <aside class="rail">
    <section class="box key-box"><p class="bar"><span>reader key</span><span aria-hidden="true">⚿</span></p><div class="box-body key-panel" id="key-panel"></div></section>
    <div class="cp-tools">
      <button class="btn" type="button" id="export-md">Export as Markdown</button>
      <button class="btn danger" type="button" id="clear-local">Forget this device</button>
    </div>
  </aside>
</div>`,
  });
}

function brief({ picks, viewer }) {
  const minutes = picks.reduce((n, s) => n + s.minutes, 0);
  return layout({
    title: 'The Brief', author: viewer, active: 'brief', scripts: ['brief.js'], path: '/brief',
    body: h`
<section class="masthead">
  <h1>The Brief</h1>
  <p class="lede">One email on Sunday with five pieces at most. New work from writers you follow comes first, then what people finished most. When you’ve read it, you’re done for the week.</p>
</section>
<div class="cp-layout">
  ${box(`preview · about ${minutes} min`, h`<ol class="brief-list">
    ${picks.map((s) => h`<li><a href="/p/${s.slug}?via=brief">${s.title}</a><span class="muted small"> · ${s.author_name} · ${s.minutes} min</span><br><span class="small">${s.dek}</span></li>`)}
  </ol>`)}
  <aside class="rail"><section class="box key-box"><p class="bar"><span>get the brief</span><span aria-hidden="true">✉</span></p><div class="box-body key-panel" id="key-panel"></div></section></aside>
</div>`,
  });
}

function declaration({ viewer }) {
  const articles = [
    ['Reading is free to begin.', 'No one should have to hand over an email, a phone number, or a password to find out whether a piece is any good. The first paragraph, and every paragraph after it, belongs to whoever shows up.'],
    ['Attention is borrowed, not owned.', 'We won’t use tricks to hold it. Pages end. Feeds end. The Brief has five things in it, not fifty. When you’re done, you’re done, and that counts as success.'],
    ['What you keep is yours.', 'Kept passages and notes live on your device. If you ask us to hold them, you get a key, not an account, and you can export or erase everything at any time.'],
    ['We point at each other.', 'Writers here list who they read, including people who aren’t on Margin. Every homepage links to the next one in the ring. Sending a reader somewhere else is a courtesy, not a leak.'],
    ['Newcomers get a fair read.', 'Part of every front page is held for writers without an audience. We rank by whether people finish, not by who already has followers.'],
    ['Writers own their readers’ trust, not their data.', 'Writers see what readers did with the words: where they stopped, what they kept, what they passed on. They never see who a reader is, unless that reader chooses to tell them.'],
    ['The margin is for conversation.', 'Notes are attached to the passage they’re about. They’re signed with a key rather than a name, so the voice has to carry the note.'],
    ['You can always leave.', 'RSS for everything. Markdown export for your commonplace. CSV export for a writer’s list. Nothing here depends on you staying.'],
  ];
  return layout({
    title: 'Declaration', author: viewer, active: 'declaration', path: '/declaration',
    body: h`
<article class="sheet declaration">
  <p class="kicker mono">a declaration for readers &amp; writers · v2</p>
  <h1>We would like the web back, please.</h1>
  <p class="lede">A lot of the early web was personal pages that linked to each other and assumed good faith. It was weird, and it cared about its readers. We’re trying to build that again, with better tools, and to write down what we owe each other.</p>
  <ol class="articles">
    ${articles.map(([t, b], i) => h`<li><h2><span class="mono">§${i + 1}</span> ${t}</h2><p>${b}</p></li>`)}
  </ol>
  <p class="mono small">Signed by everyone who reads to the end. You don’t need to sign anything.</p>
</article>`,
  });
}

function about({ viewer }) {
  return layout({
    title: 'How it works', author: viewer, path: '/about',
    body: h`
<article class="sheet prose">
  <h1>How Margin works</h1>
  <p class="lede">The short version: you read without an account, keep what matters, and pass it on. The long version is below.</p>
  <h2>If you’re reading</h2>
  <ul>
    <li><strong>No wall, no pop-up.</strong> Every piece is complete, and nothing asks for anything until you’ve finished it.</li>
    <li><strong>Keep.</strong> Select a sentence and choose keep. It goes to your <a href="/commonplace">commonplace</a> and comes back on the front page later.</li>
    <li><strong>Pass it on.</strong> Select a sentence and choose pass it on. You get a link that opens the piece with that passage highlighted. The writer sees the piece was passed on. They never learn who passed it.</li>
    <li><strong>Follow</strong> a writer without an email. Their new pieces appear at the top of Today.</li>
    <li><strong>A reader key</strong> is four words and a code. It syncs your commonplace across devices and lets you write margin notes. If you want <a href="/brief">The Brief</a>, you can add an email to it.</li>
  </ul>
  <h2>If you’re writing</h2>
  <ul>
    <li>A homepage with a “now” line, your own accent color, and a list of who you read.</li>
    <li>Numbers that mean something: <strong>verified reads</strong> (reached the end, and was on the page long enough to have read it), where people stop, what they keep, and how often the piece gets passed on.</li>
    <li>A place in <a href="/ring">the ring</a>. Two front-page spots are held for writers with small audiences.</li>
    <li>A list you can export. Readers can choose to share their email with writers they follow.</li>
    <li>A draft check based on a writing-voice specification. It flags throat-clearing openings, hedges, and “it isn’t X, it’s Y” framing.</li>
  </ul>
  <h2>What we record</h2>
  <p>Readers get no cookies. Each open tab makes up a random id and reports how far it scrolled, how long it was visible, and which paragraph numbers were kept or passed on. That’s all. No IP addresses are stored, no identity is recorded, and nothing follows you to other sites.</p>
</article>`,
  });
}

function authForm({ mode, error, values = {} }) {
  const isSignup = mode === 'signup';
  return layout({
    title: isSignup ? 'Start writing' : 'Sign in', active: 'write', path: `/${mode}`,
    body: h`
<div class="narrow">
  ${box(isSignup ? 'new writer' : 'writer sign-in', h`
    <h1>${isSignup ? 'Get a homepage on Margin' : 'Welcome back'}</h1>
    <p class="muted">${isSignup ? 'Readers never need an account. Writers do, so your pages stay yours.' : 'Only writers sign in. Readers never have to.'}</p>
    ${error ? h`<p class="error" role="alert">${error}</p>` : ''}
    <form method="post" action="/${mode}" class="stack">
      ${isSignup ? h`<label>Name <input name="name" required maxlength="60" autocomplete="name" value="${values.name || ''}"></label>
      <label>Handle <input name="handle" required pattern="[a-z0-9_]{2,24}" maxlength="24" autocomplete="username" value="${values.handle || ''}"><span class="small muted">Lowercase letters, numbers, underscores. Your homepage is /@handle.</span></label>` : h`<label>Handle <input name="handle" required autocomplete="username" value="${values.handle || ''}"></label>`}
      <label>Password <input type="password" name="password" required minlength="${isSignup ? 10 : 1}" autocomplete="${isSignup ? 'new-password' : 'current-password'}"></label>
      <button class="btn primary" type="submit">${isSignup ? 'Create my homepage' : 'Sign in'}</button>
    </form>
    <p class="small">${isSignup ? h`Already here? <a href="/login">Sign in</a>` : h`New? <a href="/signup">Start writing</a> · demo: <code>theo</code> / <code>demo-password</code>`}</p>`)}
</div>`,
  });
}

function dashboard({ author, dash }) {
  const totals = dash.posts.reduce((t, p) => ({ views: t.views + p.views, reads: t.reads + p.reads, keeps: t.keeps + p.keeps, passes: t.passes + p.passes, tips: t.tips + p.tip_cents }), { views: 0, reads: 0, keeps: 0, passes: 0, tips: 0 });
  const f = dash.funnel.follow || { shown: 0, accepted: 0 };
  const k = dash.funnel.key || { shown: 0, accepted: 0 };
  const srcTotal = dash.sources.reduce((n, s) => n + s.n, 0) || 1;
  const stat = (n, l) => h`<div class="stat"><span class="n">${n}</span><span class="l">${l}</span></div>`;
  return layout({
    title: 'Your desk', author, active: 'dashboard', accent: author.accent, path: '/desk',
    body: h`
<section class="masthead">
  <p class="kicker mono">${author.name}’s desk</p>
  <h1>What readers did with your words</h1>
  <div class="row">
    <a class="btn primary" href="/write/new">New piece</a>
    <a class="btn" href="/desk/profile">Edit homepage</a>
    <a class="btn" href="/@${author.handle}">View homepage</a>
    <form method="post" action="/logout" class="inline"><button class="btn" type="submit">Sign out</button></form>
  </div>
</section>
<div class="stats">
  ${stat(h`<span class="live" aria-hidden="true"></span>${dash.now}`, 'reading now')}
  ${stat(totals.views, 'opens')}
  ${stat(totals.reads, 'verified reads')}
  ${stat(totals.views ? pct(totals.reads / totals.views) : '—', 'finish rate')}
  ${stat(totals.keeps, 'passages kept')}
  ${stat(totals.passes, 'passed on')}
  ${stat(dash.followers, 'followers')}
  ${stat(money(totals.tips), 'tips (simulated)')}
</div>
<p class="muted small">A verified read means someone reached 90% of the piece and the page was visible for at least a third of normal reading time. Followers includes anonymous follows; ${plural(dash.keyedFollowers, 'follower')} ${dash.keyedFollowers === 1 ? 'has' : 'have'} a reader key.</p>

<h2>Pieces</h2>
${dash.posts.length ? h`<div class="table-wrap" tabindex="0" role="region" aria-label="Pieces table"><table class="data">
  <thead><tr><th scope="col">Piece</th><th scope="col">Opens</th><th scope="col">Reads</th><th scope="col">Finish</th><th scope="col">Median depth</th><th scope="col">Kept</th><th scope="col">Passed on</th><th scope="col">Follows</th><th scope="col">Notes</th><th scope="col">Tips</th></tr></thead>
  <tbody>
  ${dash.posts.map((p) => h`<tr>
    <td><a href="/dashboard/p/${p.slug}">${p.title}</a> <a class="small muted" href="/write/${p.id}">edit</a></td>
    <td>${p.views}</td><td>${p.reads}</td><td>${p.views ? pct(p.completion) : '—'}</td><td>${p.views ? pct(p.medianDepth) : '—'}</td>
    <td>${p.keeps}</td><td>${p.passes}</td><td>${p.follows}</td><td>${p.notes}</td><td>${money(p.tip_cents)}</td></tr>`)}
  </tbody>
</table></div>` : h`<p class="empty">Nothing published yet. <a href="/write/new">Write your first piece.</a></p>`}
${dash.drafts.length ? h`<h2>Drafts</h2><ul class="plain">${dash.drafts.map((d) => h`<li><a href="/write/${d.id}">${d.title || 'Untitled'}</a> <span class="muted small">saved ${fmtDate(d.updated_at)}</span></li>`)}</ul>` : ''}

<div class="two-col">
  <section>
    <h2>Where readers came from</h2>
    ${dash.sources.length ? h`<ul class="bars">${dash.sources.map((s) => h`<li><span class="bl">${SOURCE_LABEL[s.source] || s.source}</span><span class="bv"><span class="bf" style="width:${Math.max(2, Math.round((100 * s.n) / srcTotal))}%"></span></span><span class="bn">${s.n}</span></li>`)}</ul>` : h`<p class="empty">No opens yet.</p>`}
    <p class="muted small">“Passed on” counts people who arrived through a passage link another reader shared. That’s word of mouth, measured without knowing who said it.</p>
  </section>
  <section>
    <h2>The earned ask</h2>
    <p class="muted small">Readers are only asked for something after they finish a piece.</p>
    <div class="stats tight">
      ${stat(f.shown ? pct(f.accepted / f.shown) : '—', `follow: ${f.accepted} of ${f.shown}`)}
      ${stat(k.shown ? pct(k.accepted / k.shown) : '—', `reader key: ${k.accepted} of ${k.shown}`)}
    </div>
    <h2>Who lists you</h2>
    ${dash.recommendedBy.length ? h`<p>${dash.recommendedBy.map((a, i) => h`${i ? ', ' : ''}<a href="/@${a.handle}">${a.name}</a>`)} ${dash.recommendedBy.length === 1 ? 'lists' : 'list'} you on their homepage.</p>` : h`<p class="empty">No one yet. Add writers you like to <a href="/desk/profile">your list</a>. People tend to return the favor.</p>`}
  </section>
</div>

<h2>Your list</h2>
<p class="muted">Readers who follow you with a reader key and chose to share their email. You can take it anywhere.</p>
${dash.list.length ? h`<ul class="plain">${dash.list.slice(0, 20).map((r) => h`<li class="mono small">${r.email} <span class="muted">since ${fmtDate(r.created_at)}</span></li>`)}</ul>` : h`<p class="empty">Empty so far. It fills when readers get a key, follow you, and choose to share their email.</p>`}
<p><a class="btn" href="/dashboard/list.csv">Export CSV</a></p>`,
  });
}

function profileForm({ author, accents, error, saved }) {
  return layout({
    title: 'Edit homepage', author, active: 'dashboard', accent: author.accent, path: '/desk/profile',
    body: h`
<div class="narrow wide">
  <p class="small mono"><a href="/dashboard">← desk</a></p>
  ${box('edit homepage', h`
    <h1>Your homepage</h1>
    ${error ? h`<p class="error" role="alert">${error}</p>` : ''}
    ${saved ? h`<p class="ok" role="status">Saved. <a href="/@${author.handle}">See it →</a></p>` : ''}
    <form method="post" action="/desk/profile" class="stack">
      <label>Name <input name="name" required maxlength="60" value="${author.name}"></label>
      <label>About you <textarea name="bio" maxlength="280" rows="3">${author.bio}</textarea></label>
      <label>Now line <span class="small muted">What you’re working on or obsessed with this month. It shows in the ring.</span>
        <input name="now_line" maxlength="140" value="${author.now_line}" placeholder="Now: …"></label>
      <fieldset class="swatches"><legend>Accent color</legend>
        ${accents.map((a) => h`<label class="swatch acc-${a}"><input type="radio" name="accent" value="${a}"${raw(a === author.accent ? ' checked' : '')}><span class="chip" aria-hidden="true"></span>${a}</label>`)}
      </fieldset>
      <label>Who you read <span class="small muted">One per line: <code>@handle</code> for writers here, or <code>https://… Title</code> for anywhere on the web. Up to 12.</span>
        <textarea name="blogroll" rows="6" class="mono-input">${author.blogroll}</textarea></label>
      <button class="btn primary" type="submit">Save homepage</button>
    </form>`)}
</div>`,
  });
}

function postDetail({ author, post, stats, paras }) {
  return layout({
    title: `${post.title}: signals`, author, active: 'dashboard', accent: author.accent, path: `/desk/${post.slug}`,
    body: h`
<section class="masthead">
  <p class="small mono"><a href="/dashboard">← desk</a></p>
  <h1>${post.title}</h1>
  <p class="muted mono small">${stats.views} opens · ${stats.reads} verified reads · ${stats.keeps} kept · ${stats.passes || 0} passed on · ${stats.notes} margin notes</p>
</section>
<p class="muted">Each row is one block of the piece. The grey bar shows how many readers got that far, so a sudden drop is where people left. The colored bar shows how often that passage was kept or passed on, compared with the most popular passage.</p>
<ol class="paramap">
  ${paras.map((p) => h`<li class="pm-row pm-${p.kind}">
    <div class="pm-bars" aria-hidden="true">
      <span class="pm-reach" style="width:${Math.round(p.reached * 100)}%"></span>
      <span class="pm-keep" style="width:${Math.round(p.keepShare * 100)}%"></span>
    </div>
    <div class="pm-text"><span class="pm-n mono">${pct(p.reached)} reached · ${p.keeps} kept${p.passes ? ` · ${p.passes} passed` : ''}${p.notes ? ` · ${p.notes} notes` : ''}</span>${p.text.length > 180 ? p.text.slice(0, 180) + '…' : p.text}</div>
  </li>`)}
</ol>`,
  });
}

function editor({ author, post, error }) {
  const p = post || { id: 'new', title: '', dek: '', body_md: '', status: 'draft', slug: '' };
  return layout({
    title: p.id === 'new' ? 'New piece' : `Edit: ${p.title}`, author, active: 'dashboard', scripts: ['write.js'], accent: author.accent, path: '/desk/write',
    body: h`
<section class="editor">
  <p class="small mono"><a href="/dashboard">← desk</a> ${p.status === 'published' ? h`· <a href="/p/${p.slug}">view published</a>` : ''}</p>
  ${error ? h`<p class="error" role="alert">${error}</p>` : ''}
  <form method="post" action="/write/${String(p.id)}" class="stack" id="editor-form">
    <label>Title <input name="title" required maxlength="140" value="${p.title}" class="title-input"></label>
    <label>Dek <span class="small muted">One sentence that goes under the title.</span><input name="dek" maxlength="240" value="${p.dek}"></label>
    <div class="editor-grid">
      <label>Body <span class="small muted">Markdown: ## heading, *italic*, **bold**, &gt; quote, - list, [link](https://…)</span>
        <textarea name="body_md" id="body_md" rows="24">${p.body_md}</textarea></label>
      ${box('draft check', h`<p class="muted small">Based on the SuperWritingEngine voice spec. It’s advice only and never blocks publishing.</p><div id="check-results" aria-live="polite"><p class="muted small">Start writing…</p></div>`, 'checks')}
    </div>
    <div class="row">
      <button class="btn" name="action" value="save">Save draft</button>
      <button class="btn primary" name="action" value="publish">${p.status === 'published' ? 'Update' : 'Publish'}</button>
      ${p.status === 'published' ? h`<button class="btn danger" name="action" value="unpublish">Unpublish</button>` : ''}
    </div>
  </form>
</section>`,
  });
}

function notFound({ viewer } = {}) {
  return layout({ title: 'Not found', author: viewer, path: '/404', body: h`<div class="narrow">${box('404.txt', h`<h1>Nothing here.</h1><p>That page moved, or never existed. The web is like that sometimes.</p><p><a href="/">Back to today’s reading</a> · <a href="/ring/random">somewhere random</a></p>`)}</div>` });
}

module.exports = { layout, home, article, authorPage, ringPage, commonplace, brief, declaration, about, authForm, dashboard, profileForm, postDetail, editor, notFound, h, raw, fmtDate };
