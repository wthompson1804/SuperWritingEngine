// Uploads a Substack export zip as the raw request body and shows the report.
(function () {
  'use strict';
  var M = window.Margin, el = M.el;
  var form = document.getElementById('import-form');
  var out = document.getElementById('import-result');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var file = document.getElementById('import-file').files[0];
    if (!file) return;
    var btn = form.querySelector('button');
    btn.disabled = true; btn.textContent = 'Importing…';
    out.innerHTML = '';
    fetch('/desk/import', { method: 'POST', headers: { 'Content-Type': 'application/zip' }, body: file })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        btn.disabled = false; btn.textContent = 'Import';
        if (!r.ok) { out.appendChild(el('p', { class: 'error', role: 'alert', text: r.error || 'Import failed.' })); return; }
        var p = r.report.posts, s = r.report.subscribers;
        var n = function (x, one, many) { return x + ' ' + (x === 1 ? one : many); };
        out.appendChild(el('div', { class: 'stack' }, [
          el('p', { class: 'ok', role: 'status', text: 'Done.' }),
          el('ul', { class: 'plain' }, [
            el('li', { text: n(p.published, 'post', 'posts') + ' published with original dates' }),
            el('li', { text: n(p.drafts, 'post', 'posts') + ' came in as drafts' }),
            el('li', { text: n(s.imported, 'email subscriber', 'email subscribers') + ' added to your list' + (s.already ? ' (' + s.already + ' already there)' : '') }),
            p.already ? el('li', { text: n(p.already, 'post was', 'posts were') + ' already imported and skipped' }) : null,
            p.skipped || s.skipped ? el('li', { class: 'muted', text: (p.skipped + s.skipped) + ' rows skipped (threads, missing files, or unsubscribed addresses)' }) : null,
          ]),
          r.report.warnings.length ? el('ul', { class: 'plain warnings' }, r.report.warnings.map(function (w) { return el('li', { text: '! ' + w }); })) : null,
          el('p', {}, [el('a', { class: 'btn primary', href: '/dashboard', text: 'Go to your desk' })]),
        ]));
      })
      .catch(function () { btn.disabled = false; btn.textContent = 'Import'; out.appendChild(el('p', { class: 'error', text: 'Upload failed. Try again.' })); });
  });
})();
