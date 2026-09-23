'use strict';
// A deliberately small Markdown renderer. Everything is escaped first, then a
// short list of inline forms is re-enabled. Every readable block gets a
// data-p index so highlights, margin notes and drop-off can anchor to it.

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function inline(src) {
  let out = esc(src);
  out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
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
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/(^|[^\w])_([^_]+)_(?!\w)/g, '$1$2')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
}

// Returns { html, blocks: [{ i, kind, text, words }], words }
function render(md) {
  const lines = String(md || '').replace(/\r\n?/g, '\n').split('\n');
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
    const i = addBlock('p', text);
    html.push(`<p data-p="${i}">${inline(text)}</p>`);
    para = [];
  };
  const flushList = () => {
    if (!list) return;
    const tag = list.ordered ? 'ol' : 'ul';
    const items = list.items.map((t) => `<li data-p="${addBlock('li', t)}">${inline(t)}</li>`);
    html.push(`<${tag}>${items.join('')}</${tag}>`);
    list = null;
  };
  const flushQuote = () => {
    if (!quote.length) return;
    const text = quote.join(' ');
    const i = addBlock('quote', text);
    html.push(`<blockquote data-p="${i}"><p>${inline(text)}</p></blockquote>`);
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
      const level = Math.min(m[1].length + 1, 4); // # -> h2; the title owns h1
      const i = addBlock('h', m[2]);
      html.push(`<h${level} data-p="${i}">${inline(m[2])}</h${level}>`);
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
