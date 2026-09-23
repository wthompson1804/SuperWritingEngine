// Front page: mark what you've finished, show new pieces from writers you
// follow, and bring back one kept passage on a spaced schedule.
(function () {
  'use strict';
  var M = window.Margin, el = M.el;
  var DAY = 86400000;
  // Spaced resurfacing, the loop Readwise is built on: a passage comes back
  // after 1, 3, 7, 21, then 60 days. "Still true" moves it along;
  // "not now" brings it back tomorrow.
  var STEPS = [1, 3, 7, 21, 60];

  function keptAt(k) { return k.keptAt || k.ts; }
  function due(k) {
    var step = STEPS[Math.min(k.rs || 0, STEPS.length - 1)] * DAY;
    return Math.max((k.rsAt || keptAt(k)) + step, k.snooze || 0);
  }
  // Every change bumps ts (sync is newest-wins) but keeps the original keep date.
  function touch(id, fn) {
    M.update(function (s) { var x = s.kept[id]; if (!x) return; x.keptAt = keptAt(x); fn(x); x.ts = Date.now(); });
    resurface();
  }

  function resurface() {
    var kept = M.liveKept();
    var box = document.getElementById('resurface');
    if (!kept.length) { box.hidden = true; return; }
    var now = Date.now();
    var ready = kept.filter(function (k) { return due(k) <= now; }).sort(function (a, b) { return due(a) - due(b); });
    // Nothing due: show nothing. The page shouldn't nag.
    var k = ready[0];
    if (!k) { box.hidden = true; return; }
    document.getElementById('resurface-text').textContent = k.text;
    var meta = document.getElementById('resurface-meta');
    meta.innerHTML = '';
    meta.appendChild(el('a', { href: '/p/' + k.slug + '#p-' + k.para, text: k.title }));
    meta.appendChild(document.createTextNode(' · ' + k.author + ' · kept ' + Math.max(1, Math.round((now - keptAt(k)) / DAY)) + 'd ago'));
    var controls = el('div', { class: 'row resurface-actions' }, [
      el('button', { class: 'btn', type: 'button', text: 'Still true', on: { click: function () { touch(k.id, function (x) { x.rs = (x.rs || 0) + 1; x.rsAt = Date.now(); x.snooze = 0; }); } } }),
      el('button', { class: 'btn', type: 'button', text: 'Not now', on: { click: function () { touch(k.id, function (x) { x.snooze = Date.now() + DAY; }); } } }),
    ]);
    var old = box.querySelector('.resurface-actions'); if (old) old.remove();
    meta.parentNode.appendChild(controls);
    var more = ready.length - 1;
    var label = box.querySelector('.bar span');
    if (label) label.textContent = 'from your commonplace' + (more > 0 ? ' · ' + more + ' more due' : '');
    box.hidden = false;
  }

  function paint() {
    var s = M.load();
    document.querySelectorAll('.card[data-slug]').forEach(function (c) {
      var done = !!s.finished[c.getAttribute('data-slug')];
      c.classList.toggle('done', done);
      var mark = c.querySelector('.done-mark'); if (mark) mark.hidden = !done;
    });
    resurface();

    var handles = Object.keys(s.follows).filter(function (h) { return s.follows[h].on; });
    if (!handles.length) return;
    fetch('/api/latest?handles=' + encodeURIComponent(handles.join(','))).then(function (r) { return r.json(); }).then(function (r) {
      var fresh = (r.posts || []).filter(function (p) { return !s.finished[p.slug]; }).slice(0, 3);
      if (!fresh.length) return;
      var list = document.getElementById('following-list');
      list.innerHTML = '';
      fresh.forEach(function (p) {
        list.appendChild(el('article', { class: 'card compact' }, [
          el('h3', {}, [el('a', { href: '/p/' + p.slug + '?via=follow', text: p.title })]),
          el('p', { class: 'meta', text: p.author_name + ' · ' + p.minutes + ' min' }),
        ]));
      });
      document.getElementById('following').hidden = false;
    }).catch(function () {});
  }
  paint();
})();
