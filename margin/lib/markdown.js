'use strict';
// A deliberately small Markdown renderer. Everything is escaped first, then a
// short list of inline forms is re-enabled. Every readable block gets a
// data-p index so highlights, margin notes and drop-off can anchor to it.

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

// Images may only come from Margin's own /media/ store. Hotlinked images
// would hand every reader's IP address to a third party.
const IMG = /!\[([^\]]*)\]\((\/media\/[\w.-]+)\)/g;

function inline(src, fn) {
  let out = esc(src);
  out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
  out = out.replace(IMG, (m, alt, url) => `<img src="${url}" alt="${alt}" loading="lazy" decoding="async">`);
  out = out.replace(/!\[([^\]]*)\]\((https?:\/\/[^)\s]+)\)/g, (m, alt, url) => `[Image: ${alt || 'external'}](${url})`);
  if (fn) out = out.replace(/\[\^([\w-]{1,20})\]/g, (m, id) => fn(id) || m);
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)/g, '$1<em>$2</em>');
  out = out.replace(/(^|[^\w])_([^_\s][^_]*?)_(?!\w)/g, '$1<em>$2</em>');
  out = out.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, text, url) => {
    const u = url.replace(/&amp;/g, '&');
    if (!/^(https?:\/\/|\/|#|mailto:)/i.test(u)) return text;
    return `<a href="${esc(u)}" rel="noopener nofollow">${text}</a>`;
  });
  return out;
}

function plain(src) {
  return String(src)
    .replace(IMG, '$1')
    .replace(/\[\^[\w-]{1,20}\]/g, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/(^|[^\w])_([^_]+)_(?!\w)/g, '$1$2')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
}

// Returns { html, blocks: [{ i, kind, text, words }], words }
function render(md) {
  // Footnote definitions ("[^1]: text") are pulled out first and listed at the end.
  const defs = new Map();
  const lines = String(md || '').replace(/\r\n?/g, '\n').split('\n').filter((l) => {
    const m = l.match(/^\[\^([\w-]{1,20})\]:\s+(.*)$/);
    if (m) { defs.set(m[1], m[2]); return false; }
    return true;
  });
  const used = [];
  const fn = (id) => {
    if (!defs.has(id)) return null;
    let n = used.indexOf(id) + 1;
    if (!n) { used.push(id); n = used.length; }
    return `<sup class="fnref"><a href="#fn-${esc(id)}" id="fnref-${esc(id)}-${n}" aria-label="Footnote ${n}">${n}</a></sup>`;
  };
  const inl = (t) => inline(t, fn);
  const html = [];
  const blocks = [];
  let para = [];
  let list = null; // { ordered, items: [] }
  let quote = [];
  let code = null;

  const addBlock = (kind, text) => {
    const i = blocks.length;
    const t = plain(text);
    blocks.push({ i, kind, text: t, words: countWords(t) });
    return i;
  };
  const flushPara = () => {
    if (!para.length) return;
    const text = para.join(' ');
    const fig = text.match(/^!\[([^\]]*)\]\((\/media\/[\w.-]+)\)$/);
    const i = addBlock(fig ? 'img' : 'p', text);
    html.push(fig
      ? `<figure data-p="${i}"><img src="${fig[2]}" alt="${esc(fig[1])}" loading="lazy" decoding="async">${fig[1] ? `<figcaption>${esc(fig[1])}</figcaption>` : ''}</figure>`
      : `<p data-p="${i}">${inl(text)}</p>`);
    para = [];
  };
  const flushList = () => {
    if (!list) return;
    const tag = list.ordered ? 'ol' : 'ul';
    const items = list.items.map((t) => `<li data-p="${addBlock('li', t)}">${inl(t)}</li>`);
    html.push(`<${tag}>${items.join('')}</${tag}>`);
    list = null;
  };
  const flushQuote = () => {
    if (!quote.length) return;
    const text = quote.join(' ');
    const i = addBlock('quote', text);
    html.push(`<blockquote data-p="${i}"><p>${inl(text)}</p></blockquote>`);
    quote = [];
  };
  const flushAll = () => { flushPara(); flushList(); flushQuote(); };

  for (const line of lines) {
    if (code) {
      if (/^```/.test(line)) {
        html.push(`<pre><code>${esc(code.join('\n'))}</code></pre>`);
        code = null;
      } else code.push(line);
      continue;
    }
    if (/^```/.test(line)) { flushAll(); code = []; continue; }
    if (!line.trim()) { flushAll(); continue; }
    let m;
    if ((m = line.match(/^(#{1,3})\s+(.*)$/))) {
      flushAll();
      const level = m[1].length === 3 ? 3 : 2; // the title owns h1; # and ## are sections, ### subsections
      const i = addBlock('h', m[2]);
      html.push(`<h${level} data-p="${i}">${inl(m[2])}</h${level}>`);
      continue;
    }
    if (/^(-{3,}|\*{3,})\s*$/.test(line)) { flushAll(); html.push('<hr>'); continue; }
    if ((m = line.match(/^>\s?(.*)$/))) { flushPara(); flushList(); quote.push(m[1]); continue; }
    if ((m = line.match(/^\s*([-*]|\d+\.)\s+(.*)$/))) {
      flushPara(); flushQuote();
      const ordered = /\d/.test(m[1]);
      if (!list || list.ordered !== ordered) { flushList(); list = { ordered, items: [] }; }
      list.items.push(m[2]);
      continue;
    }
    if (list && /^\s+\S/.test(line)) { list.items[list.items.length - 1] += ' ' + line.trim(); continue; }
    flushList(); flushQuote();
    para.push(line.trim());
  }
  if (code) html.push(`<pre><code>${esc(code.join('\n'))}</code></pre>`);
  flushAll();
  if (used.length) {
    html.push(`<section class="footnotes" aria-label="Footnotes"><ol>${used.map((id) =>
      `<li id="fn-${esc(id)}">${inline(defs.get(id))} <a href="#fnref-${esc(id)}-${used.indexOf(id) + 1}" aria-label="Back to text">↩</a></li>`).join('')}</ol></section>`);
  }

  const words = blocks.reduce((n, b) => n + b.words, 0);
  return { html: html.join('\n'), blocks, words };
}

function countWords(s) {
  const m = String(s).match(/[A-Za-z0-9À-ɏ'’-]+/g);
  return m ? m.length : 0;
}

function firstSentence(md) {
  const { blocks } = render(md);
  const first = blocks.find((b) => b.kind === 'p');
  if (!first) return '';
  const m = first.text.match(/^.*?[.!?](?=\s|$)/);
  return (m ? m[0] : first.text).trim();
}

module.exports = { render, esc, inline, plain, countWords, firstSentence };
