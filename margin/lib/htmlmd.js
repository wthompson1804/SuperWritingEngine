'use strict';
// Converts the HTML in a Substack export into Margin's Markdown subset. It's
// a pragmatic tag walker, not a full HTML parser: it keeps paragraphs,
// headings, emphasis, links, quotes, lists, code and rules; turns images into
// captioned links; and drops Substack's widgets (subscribe buttons, share
// buttons, embeds it can't represent).
//
// Everything here runs in linear time. Uploaded HTML is untrusted, and lazy
// regexes like /<p>[\s\S]*?<\/p>/ rescan to the end of the input from every
// unclosed "<p": a 150 KB file of "<" once blocked the server for 9 seconds.

const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', mdash: '—', ndash: '–', hellip: '…', rsquo: '’', lsquo: '‘', rdquo: '”', ldquo: '“' };
function decode(s) {
  return String(s).replace(/&(#x[0-9a-f]{1,6}|#\d{1,7}|[a-z]{1,10});/gi, (m, e) => {
    if (e[0] === '#') {
      const n = e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return Number.isFinite(n) && n <= 0x10ffff ? String.fromCodePoint(n) : m;
    }
    return ENTITIES[e.toLowerCase()] ?? m;
  });
}

const WIDGET = /\bclass\s*=\s*"[^"]*\b(subscription-widget|subscribe-widget|share-dialog|button-wrapper|captioned-button|digest-post-embed|embedded-publication|footnote-anchor-hidden)\b/i;

function attr(tag, name) {
  const m = tag.match(new RegExp(`\\b${name}\\s*=\\s*("([^"]*)"|'([^']*)')`, 'i'));
  return m ? decode(m[2] ?? m[3] ?? '') : '';
}

// Replaces each <name ...>inner</name> (the nearest closing tag, like a lazy
// regex) in one left-to-right pass. fn(openTag, inner, name) returns the
// replacement, or null to leave the opening tag and keep scanning inside it.
function pairs(s, names, fn) {
  const open = new RegExp(`<(${names})\\b[^<>]*>`, 'gi');
  const lower = s.toLowerCase();
  const noClose = new Set();
  let out = '';
  let last = 0;
  let m;
  while ((m = open.exec(s))) {
    const name = m[1].toLowerCase();
    if (noClose.has(name)) continue;
    const at = lower.indexOf(`</${name}`, open.lastIndex);
    const end = at < 0 ? -1 : lower.indexOf('>', at);
    if (end < 0) { noClose.add(name); continue; } // nothing closes it from here on
    const rep = fn(m[0], s.slice(open.lastIndex, at), name);
    if (rep === null) continue;
    out += s.slice(last, m.index) + rep;
    last = end + 1;
    open.lastIndex = last;
  }
  return out + s.slice(last);
}

function collect(s, names) {
  const found = [];
  pairs(s, names, (o, inner) => { found.push(inner); return ''; });
  return found;
}

function htmlToMarkdown(html) {
  let s = String(html || '').replace(/\r\n?/g, '\n');
  s = pairs(s, 'script|style|svg|button|form|iframe|noscript', () => '');
  s = pairs(s, 'div', (openTag) => (WIDGET.test(openTag) ? '' : null));
  // Images: keep as a link so nothing silently disappears.
  s = pairs(s, 'figure', (o, fig) => {
    const img = fig.match(/<img\b[^<>]*>/i);
    if (!img) return '';
    const cap = collect(fig, 'figcaption')[0];
    const src = attr(img[0], 'src');
    const text = cap != null ? stripTags(cap).trim() : (attr(img[0], 'alt') || 'Image');
    return /^https?:\/\//.test(src) ? `\n\n[Image: ${text}](${src})\n\n` : '';
  });
  s = s.replace(/<img\b[^<>]*>/gi, (img) => { const src = attr(img, 'src'); return /^https?:\/\//.test(src) ? `[Image: ${attr(img, 'alt') || 'image'}](${src})` : ''; });
  // Code blocks are set aside untouched and restored after every other pass.
  const code = [];
  s = pairs(s, 'pre', (o, c) => `\n\n\u0000${code.push(decode(stripTags(c))) - 1}\u0000\n\n`);
  s = pairs(s, 'h[1-6]', (o, c, name) => `\n\n${'#'.repeat(Math.min(3, Math.max(1, Number(name[1]) - 1)))} ${inline(c)}\n\n`);
  s = pairs(s, 'blockquote', (o, c) => `\n\n${blocks(c).map((b) => `> ${b}`).join('\n>\n')}\n\n`);
  s = pairs(s, 'ul|ol', (o, c, name) => {
    let i = 0;
    const items = collect(c, 'li').map((li) => `${name === 'ol' ? `${++i}.` : '-'} ${inline(li.replace(/<\/?p\b[^<>]*>/gi, ' '))}`);
    return `\n\n${items.join('\n')}\n\n`;
  });
  s = s.replace(/<hr\b[^<>]*>/gi, '\n\n---\n\n');
  s = pairs(s, 'p', (o, c) => `\n\n${inline(c)}\n\n`);
  s = s.replace(/<br\s*\/?>/gi, '\n');
  // Whatever tags remain are wrappers; their text still counts.
  s = s.split(/\n{2,}/).map((b) => (b.includes('<') ? inline(b) : b.trim())).filter(Boolean).join('\n\n');
  // Entities are decoded once, at the end, so "&lt;div&gt;" in prose stays
  // text instead of being mistaken for a tag by an earlier pass.
  s = decode(s).replace(/\u0000(\d+)\u0000/g, (m, n) => `\`\`\`\n${code[Number(n)]}\n\`\`\``);
  return s.replace(/\n{3,}/g, '\n\n').trim();
}

function blocks(c) {
  const ps = collect(c, 'p').map(inline);
  return ps.length ? ps : [inline(c)];
}

function inline(c) {
  let s = String(c);
  // Links first, so a link inside bold or italic survives.
  s = pairs(s, 'a', (openTag, x) => {
    const href = attr(openTag, 'href');
    const text = stripTags(x).trim();
    if (!text) return '';
    return /^(https?:\/\/|mailto:)/i.test(href) ? `[${text.replace(/[[\]]/g, '')}](${href.replace(/[()\s]/g, encodeURIComponent)})` : text;
  });
  s = pairs(s, 'code', (o, x) => `\`${stripTags(x)}\``);
  s = pairs(s, 'strong|b', (o, x) => { const v = x.trim(); return stripTags(v) ? `**${v}**` : ''; });
  s = pairs(s, 'em|i', (o, x) => { const v = x.trim(); return stripTags(v) ? `*${v}*` : ''; });
  return stripTags(s).replace(/[ \t]*\n[ \t]*/g, ' ').replace(/\s{2,}/g, ' ').trim();
}

function stripTags(s) { return String(s).replace(/<[^<>]*>/g, ''); }

module.exports = { htmlToMarkdown, decode };
