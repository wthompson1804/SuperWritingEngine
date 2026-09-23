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
const pct = (x) => `${Math.round(x * 100)}%`;
const money = (c) => `$${(c / 100).toFixed(2)}`;

function layout({ title, body, author, scripts = [], data, active = '' }) {
  const nav = [
    ['/', 'Today', 'today'],
    ['/commonplace', 'Commonplace', 'commonplace'],
    ['/brief', 'The Brief', 'brief'],
    ['/about', 'Why Margin', 'about'],
  ];
  return '<!doctype html>' + h`<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title ? `${title} · Margin` : 'Margin'}</title>
<meta name="description" content="Read anything. No account. Keep what matters.">
<link rel="stylesheet" href="/static/style.css">
<link rel="alternate" type="application/rss+xml" title="Margin" href="/feed.xml">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site">
  <a class="brand" href="/">Margin</a>
  <nav>
    ${nav.map(([href, label, key]) => h`<a href="${href}"${raw(active === key ? ' aria-current="page"' : '')}>${label}</a>`)}
    ${author ? h`<a href="/dashboard"${raw(active === 'dashboard' ? ' aria-current="page"' : '')}>Desk</a>` : h`<a href="/write"${raw(active === 'write' ? ' aria-current="page"' : '')}>Write</a>`}
  </nav>
</header>
<main id="main">${body}</main>
<footer class="site">
  <p>No reader accounts. No tracking cookies. What you keep stays in this browser unless you ask us to hold it.</p>
  <p><a href="/feed.xml">RSS</a> · <a href="/about">How this works</a></p>
</footer>
${data ? h`<script type="application/json" id="page-data">${raw(JSON.stringify(data).replace(/</g, '\\u003c'))}</script>` : ''}
<script src="/static/local.js"></script>
${scripts.map((s) => h`<script src="/static/${s}"></script>`)}
</body>
</html>`.s;
}

function card(s) {
  return h`<article class="card${s.newVoice ? ' new-voice' : ''}" data-slug="${s.slug}">
    <p class="why">${s.reason}</p>
    <h2><a href="/p/${s.slug}">${s.title}</a></h2>
    ${s.dek ? h`<p class="dek">${s.dek}</p>` : ''}
    <p class="meta"><a href="/@${s.handle}">${s.author_name}</a> · ${s.minutes} min · <span class="done-mark" hidden>Finished</span></p>
  </article>`;
}

function home({ picks, author }) {
  const minutes = picks.reduce((n, s) => n + s.minutes, 0);
  return layout({
    author, active: 'today', scripts: ['home.js'],
    data: { picks: picks.map((s) => s.slug) },
    body: h`
<section class="intro">
  <h1>Today's reading</h1>
  <p class="lede">${picks.length} pieces, about ${minutes} minutes. That's the whole page. Nothing to sign up for, nothing to scroll past.</p>
</section>
<aside class="resurface" id="resurface" hidden>
  <p class="label">From your commonplace</p>
  <blockquote id="resurface-text"></blockquote>
  <p class="meta" id="resurface-meta"></p>
</aside>
<section class="following" id="following" hidden>
  <h2 class="section-label">From writers you follow</h2>
  <div id="following-list"></div>
</section>
<section class="picks">
  ${picks.map(card)}
</section>
<section class="finish-line">
  <p><strong>That's today.</strong> You've reached the bottom, and there's nothing below this line on purpose.</p>
  <p class="muted">Pieces get here by how many people <em>finish</em> them, not how many click. Two slots are always held for writers without an audience yet.</p>
</section>`,
  });
}

function article({ post, author, rendered, notes, topKeep, keepCounts, next, viewer }) {
  const minutes = readingMinutes(post.words);
  const notesByPara = new Map();
  for (const n of notes) { if (!notesByPara.has(n.para)) notesByPara.set(n.para, []); notesByPara.get(n.para).push(n); }
  return layout({
    title: post.title, author: viewer, scripts: ['read.js'],
    data: {
      slug: post.slug, title: post.title, words: post.words, minMs: post.words * 87,
      author: { handle: author.handle, name: author.name },
      noteCounts: Object.fromEntries([...notesByPara].map(([p, ns]) => [p, ns.length])),
      topKeep, keepCounts,
    },
    body: h`
<article class="piece" id="piece">
  <header class="piece-head">
    <h1>${post.title}</h1>
    ${post.dek ? h`<p class="dek">${post.dek}</p>` : ''}
    <p class="meta"><a href="/@${author.handle}">${author.name}</a> · ${fmtDate(post.published_at)} · ${minutes} min read</p>
  </header>
  <div class="body" id="body">${raw(rendered.html)}</div>
</article>

<section class="finish" id="finish" hidden aria-live="polite">
  <p class="finish-title">You finished it.</p>
  <div id="ask"></div>
  <div class="tip" id="tip">
    <p><strong>Pay what it was worth.</strong> No account needed. All of it goes to ${author.name}.</p>
    <div class="tip-row">
      ${[300, 500, 1000].map((c) => h`<button class="btn ghost" data-tip="${c}">${money(c)}</button>`)}
    </div>
    <p class="muted small">Prototype: payments are simulated, and the tip is only recorded.</p>
    <p class="tip-thanks" id="tip-thanks" hidden>Thank you. ${author.name} will see it.</p>
  </div>
</section>

<section class="next">
  ${next.same ? h`<a class="next-card" href="/p/${next.same.slug}"><span class="label">More from ${author.name}</span><span class="t">${next.same.title}</span><span class="muted">${readingMinutes(next.same.words)} min</span></a>` : ''}
  ${next.other ? h`<a class="next-card" href="/p/${next.other.slug}"><span class="label">Elsewhere on Margin</span><span class="t">${next.other.title}</span><span class="muted">${next.other.author_name} · ${readingMinutes(next.other.words)} min</span></a>` : ''}
</section>

<section class="margin-notes" id="notes">
  <h2>In the margin</h2>
  <p class="muted">Readers with a reader key can leave a note on any paragraph. Everyone can read them.</p>
  ${notes.length ? [...notesByPara].sort((a, b) => a[0] - b[0]).map(([p, ns]) => h`
    <div class="note-group" id="notes-p${p}" data-p="${p}">
      ${ns[0].quote ? h`<blockquote class="note-quote">${ns[0].quote}</blockquote>` : h`<p class="muted small">On paragraph ${p + 1}</p>`}
      ${ns.map((n) => h`<div class="note"><p>${n.body}</p><p class="meta">${n.display_name} · ${fmtDate(n.created_at)}</p></div>`)}
    </div>`) : h`<p class="empty" id="notes-empty">Nothing in the margin yet. Select any passage to add the first note.</p>`}
  <form class="note-form" id="note-form" hidden>
    <blockquote class="note-quote" id="note-quote"></blockquote>
    <label>Your note <textarea name="body" maxlength="1200" rows="3" required></textarea></label>
    <label>Sign it as <input name="name" maxlength="40" placeholder="A reader"></label>
    <div class="row"><button class="btn" type="submit">Add to the margin</button> <button class="btn ghost" type="button" id="note-cancel">Cancel</button></div>
  </form>
</section>

<div class="selbar" id="selbar" hidden role="toolbar" aria-label="Selection">
  <button type="button" data-act="keep">Keep</button>
  <button type="button" data-act="note">Note in margin</button>
</div>`,
  });
}

function authorPage({ author, posts, viewer }) {
  return layout({
    title: author.name, author: viewer, scripts: ['author.js'],
    data: { handle: author.handle, name: author.name },
    body: h`
<section class="intro author-head">
  <h1>${author.name}</h1>
  <p class="lede">${author.bio}</p>
  <p><button class="btn" id="follow-btn" data-handle="${author.handle}">Follow</button>
     <span class="muted small">No account. We remember it in this browser. <a href="/feed.xml?author=${author.handle}">RSS</a></span></p>
</section>
<section class="picks">
  ${posts.length ? posts.map((p) => h`<article class="card" data-slug="${p.slug}">
    <h2><a href="/p/${p.slug}">${p.title}</a></h2>
    ${p.dek ? h`<p class="dek">${p.dek}</p>` : ''}
    <p class="meta">${fmtDate(p.published_at)} · ${readingMinutes(p.words)} min · <span class="done-mark" hidden>Finished</span></p>
  </article>`) : h`<p class="empty">Nothing published yet.</p>`}
</section>`,
  });
}

function commonplace({ viewer }) {
  return layout({
    title: 'Commonplace', author: viewer, active: 'commonplace', scripts: ['commonplace.js'],
    body: h`
<section class="intro">
  <h1>Your commonplace</h1>
  <p class="lede">Every passage you keep lands here, grouped by piece, with room for your own notes. It lives in this browser and nowhere else until you get a reader key.</p>
</section>
<section class="key-panel" id="key-panel"></section>
<section id="cp-list"><p class="empty">Loading…</p></section>
<section class="cp-tools">
  <button class="btn ghost" id="export-md">Export as Markdown</button>
  <button class="btn ghost" id="clear-local">Forget everything on this device</button>
</section>`,
  });
}

function brief({ picks, viewer }) {
  const minutes = picks.reduce((n, s) => n + s.minutes, 0);
  return layout({
    title: 'The Brief', author: viewer, active: 'brief', scripts: ['brief.js'],
    body: h`
<section class="intro">
  <h1>The Brief</h1>
  <p class="lede">One email a week with no more than five pieces, and it goes out on Sunday. New pieces from writers you follow come first, then the most-finished pieces on Margin. When you've read it, you're done.</p>
</section>
<section class="brief-preview">
  <p class="label">This week's Brief would look like this · about ${minutes} min</p>
  <ol class="brief-list">
    ${picks.map((s) => h`<li><a href="/p/${s.slug}">${s.title}</a><span class="muted"> · ${s.author_name} · ${s.minutes} min</span><br><span class="small">${s.dek}</span></li>`)}
  </ol>
</section>
<section class="key-panel" id="key-panel"></section>`,
  });
}

function about({ viewer }) {
  return layout({
    title: 'Why Margin', author: viewer, active: 'about',
    body: h`
<section class="prose">
  <h1>Why Margin</h1>
  <p class="lede">A place to read long-form writing without being asked for anything first.</p>

  <h2>Who it's for</h2>
  <p>People who still read to the end. There aren't many of them, and they're easy to describe. They have more to read than time to read it. Ten newsletters they meant to read are sitting in their inbox. They closed three sign-up pop-ups today. And they can't remember where they read the best line of the week.</p>

  <h2>What you get without an account</h2>
  <ul>
    <li><strong>Every piece, whole.</strong> No wall, no pop-up, no "continue reading in the app."</li>
    <li><strong>A finite front page.</strong> Seven pieces at most, ranked by how many people <em>finished</em> them. It has a bottom.</li>
    <li><strong>A commonplace book.</strong> Select any passage and hit Keep. It's saved in your browser with a link back, and it resurfaces on the front page later so you actually remember it.</li>
    <li><strong>Follows without email.</strong> Follow a writer and new pieces show up at the top of Today. Nothing is sent anywhere.</li>
  </ul>

  <h2>What a reader key adds</h2>
  <p>A reader key is four words and a code, like <code>otter-granite-plum-fjord-7KQ2MX</code>. It's the whole account: no email, no password, no name. It gets you:</p>
  <ul>
    <li>Your commonplace and follows on every device, and still there if you clear your browser.</li>
    <li>Notes in the margin that other readers can see.</li>
    <li>If you want it, The Brief: one capped email a week. Only then do we need an address.</li>
  </ul>

  <h2>What writers get</h2>
  <ul>
    <li><strong>More people who finish.</strong> Every login wall loses readers. Here there isn't one.</li>
    <li><strong>Better numbers than open rates.</strong> Writers see verified reads (people who reached the end and stayed long enough to have read it), where readers stop, which paragraphs they kept, and what they wrote in the margin.</li>
    <li><strong>A fair shot on day one.</strong> Two front-page slots are held for writers with no audience yet, and ranking goes by completion rate, not follower count.</li>
    <li><strong>An audience you can take with you.</strong> Readers who choose to share their email with writers they follow go into a list you can export as CSV at any time.</li>
    <li><strong>A drafting check</strong> built from the SuperWritingEngine voice spec. It flags weak openings, hedges, filler, and negation framing before you publish.</li>
  </ul>

  <h2>What we don't collect</h2>
  <p>Readers get no cookies. Each page view gets a random id that exists only in the open tab. We record how far it scrolled, how long it was visible, and which paragraphs were kept. We don't record who you are, your IP address, or what you read elsewhere.</p>
</section>`,
  });
}

function authForm({ mode, error, values = {} }) {
  const isSignup = mode === 'signup';
  return layout({
    title: isSignup ? 'Start writing' : 'Sign in',
    body: h`
<section class="narrow">
  <h1>${isSignup ? 'Start writing on Margin' : 'Writer sign-in'}</h1>
  <p class="muted">${isSignup ? 'Readers never need an account. Writers do, so your work stays yours.' : 'Only writers sign in here. Readers never need to.'}</p>
  ${error ? h`<p class="error">${error}</p>` : ''}
  <form method="post" action="/${mode}" class="stack">
    ${isSignup ? h`<label>Name <input name="name" required maxlength="60" value="${values.name || ''}"></label>
    <label>Handle <input name="handle" required pattern="[a-z0-9_]{2,24}" maxlength="24" value="${values.handle || ''}"><span class="small muted">Lowercase letters, numbers, underscores.</span></label>` : h`<label>Handle <input name="handle" required value="${values.handle || ''}"></label>`}
    <label>Password <input type="password" name="password" required minlength="${isSignup ? 10 : 1}"></label>
    <button class="btn" type="submit">${isSignup ? 'Create writer account' : 'Sign in'}</button>
  </form>
  <p class="small">${isSignup ? h`Already writing here? <a href="/login">Sign in</a>` : h`New? <a href="/signup">Start writing</a> · Demo: handle <code>mara</code>, password <code>demo-password</code>`}</p>
</section>`,
  });
}

function dashboard({ author, dash }) {
  const totals = dash.posts.reduce((t, p) => ({ views: t.views + p.views, reads: t.reads + p.reads, keeps: t.keeps + p.keeps, tips: t.tips + p.tip_cents }), { views: 0, reads: 0, keeps: 0, tips: 0 });
  const f = dash.funnel.follow || { shown: 0, accepted: 0 };
  const k = dash.funnel.key || { shown: 0, accepted: 0 };
  return layout({
    title: 'Your desk', author, active: 'dashboard',
    body: h`
<section class="intro">
  <h1>${author.name}'s desk</h1>
  <div class="row"><a class="btn" href="/write/new">New piece</a> <a class="btn ghost" href="/@${author.handle}">Public page</a>
     <form method="post" action="/logout" class="inline"><button class="btn ghost">Sign out</button></form></div>
</section>
<section class="stats">
  <div class="stat"><span class="n">${totals.views}</span><span class="l">Opens</span></div>
  <div class="stat"><span class="n">${totals.reads}</span><span class="l">Verified reads</span></div>
  <div class="stat"><span class="n">${totals.views ? pct(totals.reads / totals.views) : '—'}</span><span class="l">Finish rate</span></div>
  <div class="stat"><span class="n">${totals.keeps}</span><span class="l">Passages kept</span></div>
  <div class="stat"><span class="n">${dash.followers}</span><span class="l">Followers</span></div>
  <div class="stat"><span class="n">${money(totals.tips)}</span><span class="l">Tips (simulated)</span></div>
</section>
<p class="muted small">A verified read means the reader reached 90% of the piece and the page was visible for at least a third of normal reading time. Followers include anonymous follows. ${dash.keyedFollowers} of them hold a reader key.</p>

<h2>Pieces</h2>
<div class="table-wrap"><table class="data">
  <thead><tr><th>Piece</th><th>Opens</th><th>Reads</th><th>Finish</th><th>Median depth</th><th>Kept</th><th>Follows</th><th>Notes</th><th>Tips</th></tr></thead>
  <tbody>
  ${dash.posts.map((p) => h`<tr>
    <td><a href="/dashboard/p/${p.slug}">${p.title}</a> <a class="small muted" href="/write/${p.id}">edit</a></td>
    <td>${p.views}</td><td>${p.reads}</td><td>${p.views ? pct(p.completion) : '—'}</td><td>${p.views ? pct(p.medianDepth) : '—'}</td>
    <td>${p.keeps}</td><td>${p.follows}</td><td>${p.notes}</td><td>${money(p.tip_cents)}</td></tr>`)}
  </tbody>
</table></div>
${dash.drafts.length ? h`<h2>Drafts</h2><ul class="plain">${dash.drafts.map((d) => h`<li><a href="/write/${d.id}">${d.title || 'Untitled'}</a> <span class="muted small">saved ${fmtDate(d.updated_at)}</span></li>`)}</ul>` : ''}

<h2>The earned ask</h2>
<p class="muted">Margin never asks a reader for anything until they've finished a piece. Here's how often the ask was shown and how often it worked.</p>
<div class="stats">
  <div class="stat"><span class="n">${f.shown ? pct(f.accepted / f.shown) : '—'}</span><span class="l">Follow ask: ${f.accepted} of ${f.shown}</span></div>
  <div class="stat"><span class="n">${k.shown ? pct(k.accepted / k.shown) : '—'}</span><span class="l">Reader key ask: ${k.accepted} of ${k.shown}</span></div>
</div>

<h2>Your list</h2>
<p class="muted">Readers who follow you with a reader key and chose to share their email with writers they follow. It's yours to keep.</p>
${dash.list.length ? h`<ul class="plain">${dash.list.slice(0, 20).map((r) => h`<li>${r.email} <span class="muted small">since ${fmtDate(r.created_at)}</span></li>`)}</ul>` : h`<p class="empty">No one yet. This list grows when readers get a key, follow you, and opt in.</p>`}
<p><a class="btn ghost" href="/dashboard/list.csv">Export CSV</a></p>`,
  });
}

function postDetail({ author, post, stats, paras }) {
  return layout({
    title: `${post.title}: signals`, author, active: 'dashboard',
    body: h`
<section class="intro">
  <p class="small"><a href="/dashboard">← Desk</a></p>
  <h1>${post.title}</h1>
  <p class="muted">${stats.views} opens · ${stats.reads} verified reads · ${stats.keeps} passages kept · ${stats.notes} margin notes</p>
</section>
<p class="muted">Each row is a block of the piece. The grey bar shows how many readers got that far. The accent bar shows how often that passage was kept, relative to the most-kept one. A sharp drop in the grey bar is where readers left.</p>
<ol class="paramap">
  ${paras.map((p) => h`<li class="pm-row pm-${p.kind}">
    <div class="pm-bars">
      <span class="pm-reach" style="width:${Math.round(p.reached * 100)}%"></span>
      <span class="pm-keep" style="width:${Math.round(p.keepShare * 100)}%"></span>
    </div>
    <div class="pm-text"><span class="pm-n">${pct(p.reached)} reached · ${p.keeps} kept${p.notes ? ` · ${p.notes} notes` : ''}</span>${p.text.length > 180 ? p.text.slice(0, 180) + '…' : p.text}</div>
  </li>`)}
</ol>`,
  });
}

function editor({ author, post, error }) {
  const p = post || { id: 'new', title: '', dek: '', body_md: '', status: 'draft', slug: '' };
  return layout({
    title: p.id === 'new' ? 'New piece' : `Edit: ${p.title}`, author, active: 'dashboard', scripts: ['write.js'],
    body: h`
<section class="editor">
  <p class="small"><a href="/dashboard">← Desk</a> ${p.status === 'published' ? h`· <a href="/p/${p.slug}">View published</a>` : ''}</p>
  ${error ? h`<p class="error">${error}</p>` : ''}
  <form method="post" action="/write/${String(p.id)}" class="stack" id="editor-form">
    <label>Title <input name="title" required maxlength="140" value="${p.title}"></label>
    <label>Dek <span class="small muted">One sentence under the title.</span><input name="dek" maxlength="240" value="${p.dek}"></label>
    <div class="editor-grid">
      <label>Body <span class="small muted">Markdown: ## headings, *italic*, **bold**, &gt; quotes, - lists, [links](https://…)</span>
        <textarea name="body_md" id="body_md" rows="24">${p.body_md}</textarea></label>
      <aside class="checks" id="checks" aria-live="polite">
        <h3>Draft check</h3>
        <p class="muted small">From the SuperWritingEngine voice spec. It's advisory and won't stop you publishing.</p>
        <div id="check-results"><p class="muted small">Start writing…</p></div>
      </aside>
    </div>
    <div class="row">
      <button class="btn ghost" name="action" value="save">Save draft</button>
      <button class="btn" name="action" value="publish">${p.status === 'published' ? 'Update' : 'Publish'}</button>
      ${p.status === 'published' ? h`<button class="btn ghost" name="action" value="unpublish">Unpublish</button>` : ''}
    </div>
  </form>
</section>`,
  });
}

function notFound({ viewer } = {}) {
  return layout({ title: 'Not found', author: viewer, body: h`<section class="narrow"><h1>Nothing here.</h1><p><a href="/">Back to today's reading</a></p></section>` });
}

module.exports = { layout, home, article, authorPage, commonplace, brief, about, authForm, dashboard, postDetail, editor, notFound, h, raw, fmtDate };
