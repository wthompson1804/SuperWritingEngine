// The commonplace book: every kept passage, grouped by piece, with a note field.
(function () {
  'use strict';
  var M = window.Margin, el = M.el;
  var list = document.getElementById('cp-list');

  function render() {
    var kept = M.liveKept().sort(function (a, b) { return b.ts - a.ts; });
    list.innerHTML = '';
    if (!kept.length) {
      list.appendChild(el('p', { class: 'empty', text: 'Nothing kept yet. While you read, select any passage and choose Keep. It lands here with a link back to where you found it.' }));
      return;
    }
    var groups = {}, order = [];
    kept.forEach(function (k) { if (!groups[k.slug]) { groups[k.slug] = []; order.push(k.slug); } groups[k.slug].push(k); });
    list.appendChild(el('p', { class: 'muted', text: kept.length + ' passage' + (kept.length === 1 ? '' : 's') + ' from ' + order.length + ' piece' + (order.length === 1 ? '' : 's') + '.' }));
    order.forEach(function (slug) {
      var items = groups[slug].sort(function (a, b) { return a.para - b.para; });
      var sec = el('section', { class: 'cp-group' }, [
        el('h2', {}, [el('a', { href: '/p/' + slug, text: items[0].title })]),
        el('p', { class: 'meta' }, [el('a', { href: '/@' + items[0].handle, text: items[0].author })]),
      ]);
      items.forEach(function (k) {
        var note = el('textarea', { rows: '2', placeholder: 'Why did this matter?', 'aria-label': 'Your note' });
        note.value = k.note || '';
        note.addEventListener('change', function () {
          M.update(function (s) { if (s.kept[k.id]) { s.kept[k.id].note = note.value; s.kept[k.id].ts = Date.now(); } });
        });
        sec.appendChild(el('div', { class: 'cp-item' }, [
          el('blockquote', {}, [el('a', { href: '/p/' + slug + '#p-' + k.para, text: k.text })]),
          note,
          el('button', { class: 'link small', type: 'button', text: 'Remove', on: { click: function () {
            M.update(function (s) { if (s.kept[k.id]) { s.kept[k.id].deleted = true; s.kept[k.id].ts = Date.now(); } });
            render();
          } } }),
        ]));
      });
      list.appendChild(sec);
    });
  }

  document.getElementById('export-md').addEventListener('click', function () {
    var kept = M.liveKept().sort(function (a, b) { return a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : a.para - b.para; });
    var out = ['# Commonplace', ''], last = null;
    kept.forEach(function (k) {
      if (k.slug !== last) { out.push('## ' + k.title + ' (' + k.author + ')', location.origin + '/p/' + k.slug, ''); last = k.slug; }
      out.push('> ' + k.text, '');
      if (k.note) out.push(k.note, '');
    });
    var a = el('a', { href: URL.createObjectURL(new Blob([out.join('\n')], { type: 'text/markdown' })), download: 'commonplace.md' });
    document.body.appendChild(a); a.click(); a.remove();
  });

  document.getElementById('clear-local').addEventListener('click', function () {
    if (!confirm('Forget every passage, follow and finished piece on this device? If you have a reader key, your copy on the server stays.')) return;
    try { localStorage.removeItem('margin:v1'); } catch (e) { /* ignore */ }
    render(); M.renderKeyPanel(document.getElementById('key-panel'), { onChange: render });
  });

  M.renderKeyPanel(document.getElementById('key-panel'), { onChange: render });
  render();
  M.sync().then(function (r) { if (r && r.ok) render(); });
})();
