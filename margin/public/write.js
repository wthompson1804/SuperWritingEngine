// Live draft check in the editor. Advisory only.
(function () {
  'use strict';
  var M = window.Margin, el = M.el;
  var ta = document.getElementById('body_md');
  var out = document.getElementById('check-results');
  if (!ta || !out) return;
  var t = null;
  function row(r) {
    return el('li', { class: 'chk chk-' + r.level }, [el('span', { class: 'rule', text: r.rule }), ' ', r.msg]);
  }
  function run() {
    if (!ta.value.trim()) { out.innerHTML = ''; out.appendChild(el('p', { class: 'muted small', text: 'Start writing…' })); return; }
    M.api('/api/check', { body_md: ta.value }).then(function (r) {
      out.innerHTML = '';
      out.appendChild(el('h4', { text: 'Opening sentence' }));
      out.appendChild(el('ul', { class: 'plain' }, (r.opening || []).map(row)));
      out.appendChild(el('h4', { text: 'Body' }));
      var body = r.body || [];
      out.appendChild(body.length ? el('ul', { class: 'plain' }, body.slice(0, 25).map(row)) : el('p', { class: 'small chk-ok', text: 'No hedges, filler, or negation framing found.' }));
    });
  }
  ta.addEventListener('input', function () { clearTimeout(t); t = setTimeout(run, 600); });
  run();
})();
