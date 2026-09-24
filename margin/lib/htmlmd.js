'use strict';
// Converts the HTML in a Substack export into Margin's Markdown subset. It's
// a pragmatic tag walker, not a full HTML parser: it keeps paragraphs,
// headings, emphasis, links, quotes, lists, code and rules; turns images into
// captioned links; and drops Substack's widgets (subscribe buttons, share
// buttons, embeds it can't represent).

const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', mdash: '—', ndash: '–', hellip: '…', rsquo: '’', lsquo: '‘', rdquo: '”', ldquo: '“' };
function decode(s) {
  return String(s).replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
    if (e[0] === '#') { const n = e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10); return Number.isFinite(n) ? String.fromCodePoint(n) : m; }
    return ENTITIES[e.toLowerCase()] ?? m;
  });
}

const DROP = /<(script|style|svg|button|form|iframe|noscript)\b[\s\S]*?<\/\1>/gi;
const WIDGETS = /<div[^>]*class="[^"]*(subscription-widget|subscribe-widget|share-dialog|button-wrapper|captioned-button|digest-post-embed|embedded-publication|footnote-anchor-hidden)[^"]*"[\s\S]*?<\/div>/gi;

function attr(tag, name) {
  const m = tag.match(new RegExp(`\\b${name}\\s*=\\s*("([^"]*)"|'([^']*)')`, 'i'));
  return m ? decode(m[2] ?? m[3] ?? '') : '';
}

function htmlToMarkdown(html) {
  let s = String(html || '').replace(/\r\n?/g, '\n').replace(DROP, '').replace(WIDGETS, '');
  // Images: keep as a link so nothing silently disappears.
  s = s.replace(/<figure\b[\s\S]*?<\/figure>/gi, (fig) => {
    const img = fig.match(/<img\b[^>]*>/i);
    const cap = fig.match(/<figcaption\b[^>]*>([\s\S]*?)<\/figcaption>/i);
    if (!img) return '';
    const src = attr(img[0], 'src');
    const text = cap ? stripTags(cap[1]).trim() : (attr(img[0], 'alt') || 'Image');
    return /^https?:\/\//.test(src) ? `\n\n[Image: ${text}](${src})\n\n` : '';
  });
  s = s.replace(/<img\b[^>]*>/gi, (img) => { const src = attr(img, 'src'); return /^https?:\/\//.test(src) ? `[Image: ${attr(img, 'alt') || 'image'}](${src})` : ''; });
  // Code blocks are set aside untouched and restored after every other pass.
  const code = [];
  s = s.replace(/<pre\b[^>]*>([\s\S]*?)<\/pre>/gi, (m, c) => `\n\n\u0000${code.push(decode(stripTags(c))) - 1}\u0000\n\n`);
  s = s.replace(/<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi, (m, n, c) => `\n\n${'#'.repeat(Math.min(3, Math.max(1, Number(n) - 1)))} ${inline(c)}\n\n`);
  s = s.replace(/<blockquote\b[^>]*>([\s\S]*?)<\/blockquote>/gi, (m, c) => `\n\n${blocks(c).map((b) => `> ${b}`).join('\n>\n')}\n\n`);
  s = s.replace(/<(ul|ol)\b[^>]*>([\s\S]*?)<\/\1>/gi, (m, t, c) => {
    let i = 0;
    const items = [...c.matchAll(/<li\b[^>]*>([\s\S]*?)<\/li>/gi)].map((li) => `${t.toLowerCase() === 'ol' ? `${++i}.` : '-'} ${inline(li[1].replace(/<\/?p\b[^>]*>/gi, ' '))}`);
    return `\n\n${items.join('\n')}\n\n`;
  });
  s = s.replace(/<hr\b[^>]*>/gi, '\n\n---\n\n');
  s = s.replace(/<p\b[^>]*>([\s\S]*?)<\/p>/gi, (m, c) => `\n\n${inline(c)}\n\n`);
  s = s.replace(/<br\s*\/?>/gi, '\n');
  // Whatever tags remain are wrappers; their text still counts.
  s = s.split(/\n{2,}/).map((b) => (b.includes('<') ? inline(b) : b.trim())).filter(Boolean).join('\n\n');
  // Entities are decoded once, at the end, so "&lt;div&gt;" in prose stays
  // text instead of being mistaken for a tag by an earlier pass.
  s = decode(s).replace(/\u0000(\d+)\u0000/g, (m, n) => `\`\`\`\n${code[Number(n)]}\n\`\`\``);
  return s.replace(/\n{3,}/g, '\n\n').trim();
}

function blocks(c) {
  const ps = [...c.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/gi)].map((m) => inline(m[1]));
  return ps.length ? ps : [inline(c)];
}

function inline(c) {
  let s = String(c);
  // Links first, so a link inside bold or italic survives.
  s = s.replace(/<a\b([^>]*)>([\s\S]*?)<\/a>/gi, (m, a, x) => {
    const href = attr(`<a ${a}>`, 'href');
    const text = stripTags(x).trim();
    if (!text) return '';
    return /^(https?:\/\/|mailto:)/i.test(href) ? `[${text.replace(/[[\]]/g, '')}](${href.replace(/[()\s]/g, encodeURIComponent)})` : text;
  });
  s = s.replace(/<code\b[^>]*>([\s\S]*?)<\/code>/gi, (m, x) => `\`${stripTags(x)}\``);
  s = s.replace(/<(strong|b)\b[^>]*>([\s\S]*?)<\/\1>/gi, (m, t, x) => { const v = x.trim(); return stripTags(v) ? `**${v}**` : ''; });
  s = s.replace(/<(em|i)\b[^>]*>([\s\S]*?)<\/\1>/gi, (m, t, x) => { const v = x.trim(); return stripTags(v) ? `*${v}*` : ''; });
  return stripTags(s).replace(/[ \t]*\n[ \t]*/g, ' ').replace(/\s{2,}/g, ' ').trim();
}

function stripTags(s) { return String(s).replace(/<[^>]+>/g, ''); }

module.exports = { htmlToMarkdown, decode };
