// The commonplace book: every kept passage, grouped by piece, with a note field.
// Pocket's shutdown (2025) is the cautionary tale: what people keep has to be
// easy to back up and take elsewhere, so three export formats are always on.
(function () {
  'use strict';
  var M = window.Margin, el = M.el;
  var list = document.getElementById('cp-list');
  var keptAt = function (k) { return k.keptAt || k.ts; };

  function backupNotice(kept) {
    var s = M.load();
    if (s.readerKey || kept.length < 3) return null;
    return el('div', { class: 'backup box' }, [
      el('p', { class: 'bar' }, [el('span', { text: 'only on this device' }), el('span', { 'aria-hidden': 'true', text: '!' })]),
      el('div', { class: 'box-body' }, [
        el('p', { text: kept.length + ' passages live only in this browser. Clearing its data, or switching phones, loses them. Get a reader key (four words, no email) or download a copy.' }),
        el('div', { class: 'row' }, [
          el('a', { class: 'btn primary', href: '#key-panel', text: 'Get a reader key' }),
          el('button', { class: 'btn', type: 'button', text: 'Download a copy', on: { click: exportJson } }),
        ]),
      ]),
    ]);
  }

  function render() {
    var kept = M.liveKept().sort(function (a, b) { return keptAt(b) - keptAt(a); });
    list.innerHTML = '';
    if (!kept.length) {
      list.appendChild(el('p', { class: 'empty', text: 'Nothing kept yet. While you read, select any passage and choose keep. It lands here with a link back to where you found it.' }));
      return;
    }
    var notice = backupNotice(kept);
    if (notice) list.appendChild(notice);
    var groups = {}, order = [];
    kept.forEach(function (k) { if (!groups[k.slug]) { groups[k.slug] = []; order.push(k.slug); } groups[k.slug].push(k); });
    list.appendChild(el('p', { class: 'muted', text: kept.length + ' passage' + (kept.length === 1 ? '' : 's') + ' from ' + order.length + ' piece' + (order.length === 1 ? '' : 's') + '. The front page brings them back on a schedule: after 1, 3, 7, 21 and 60 days.' }));
    order.forEach(function (slug) {
      var items = groups[slug].sort(function (a, b) { return a.para - b.para; });
      var sec = el('section', { class: 'cp-group' }, [
        el('h2', {}, [el('a', { href: '/p/' + slug, text: items[0].title })]),
        el('p', { class: 'meta' }, [el('a', { href: '/@' + items[0].handle, text: items[0].author })]),
      ]);
      items.forEach(function (k) {
        var note = el('textarea', { rows: '2', placeholder: 'Why did this matter?', 'aria-label': 'Your note on this passage' });
        note.value = k.note || '';
        var noteState = el('span', { class: 'small muted note-state', 'aria-live': 'polite' });
        var timer = null;
        note.addEventListener('input', function () {
          noteState.textContent = '…';
          clearTimeout(timer);
          timer = setTimeout(function () {
            M.update(function (s) { var x = s.kept[k.id]; if (x) { x.keptAt = keptAt(x); x.note = note.value; x.ts = Date.now(); } });
            noteState.textContent = 'saved';
          }, 500);
        });
        sec.appendChild(el('div', { class: 'cp-item' }, [
          el('blockquote', {}, [el('a', { href: '/p/' + slug + '#p-' + k.para, text: k.text })]),
          note,
          el('div', { class: 'row' }, [noteState, el('button', { class: 'link small', type: 'button', text: 'Remove passage', on: { click: function () {
            M.update(function (s) { var x = s.kept[k.id]; if (x) { x.keptAt = keptAt(x); x.deleted = true; x.ts = Date.now(); } });
            render();
          } } })]),
        ]));
      });
      list.appendChild(sec);
    });
  }

  function sorted() {
    return M.liveKept().sort(function (a, b) { return a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : a.para - b.para; });
  }
  function exportMd() {
    var out = ['# Commonplace', ''], last = null;
    sorted().forEach(function (k) {
      if (k.slug !== last) { out.push('## ' + k.title + ' (' + k.author + ')', location.origin + '/p/' + k.slug, ''); last = k.slug; }
      out.push('> ' + k.text, '');
      if (k.note) out.push(k.note, '');
    });
    M.download('commonplace.md', out.join('\n'), 'text/markdown');
  }
  function exportJson() {
    M.download('commonplace.json', JSON.stringify({ exported: new Date().toISOString(), source: location.origin, passages: sorted().map(function (k) {
      return { text: k.text, note: k.note || '', title: k.title, author: k.author, url: location.origin + '/p/' + k.slug + '#p-' + k.para, kept: new Date(keptAt(k)).toISOString() };
    }) }, null, 2), 'application/json');
  }
  // Readwise's CSV import takes Highlight, Title, Author, URL, Note, Location, Date.
  function exportReadwise() {
    var q = function (v) { return '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"'; };
    var rows = ['Highlight,Title,Author,URL,Note,Location,Date'];
    sorted().forEach(function (k) {
      rows.push([k.text, k.title, k.author, location.origin + '/p/' + k.slug, k.note || '', k.para + 1, new Date(keptAt(k)).toISOString().slice(0, 19).replace('T', ' ')].map(q).join(','));
    });
    M.download('commonplace-readwise.csv', rows.join('\n') + '\n', 'text/csv');
  }

  document.getElementById('export-md').addEventListener('click', exportMd);
  document.getElementById('export-json').addEventListener('click', exportJson);
  document.getElementById('export-readwise').addEventListener('click', exportReadwise);
  document.getElementById('clear-local').addEventListener('click', function () {
    if (!confirm('Erase every passage, note, follow and finished piece in this browser? This can’t be undone here. (A reader key’s copy on Margin stays.)')) return;
    try { localStorage.removeItem('margin:v1'); } catch (e) { /* ignore */ }
    render(); M.renderKeyPanel(document.getElementById('key-panel'), { onChange: render });
  });

  M.persist();
  M.renderKeyPanel(document.getElementById('key-panel'), { onChange: render });
  render();
  M.sync().then(function (r) { if (r && r.ok) render(); });
})();
