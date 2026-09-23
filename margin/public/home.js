// Front page: mark what you've finished, show new pieces from writers you
// follow, and resurface one passage you kept.
(function () {
  'use strict';
  var M = window.Margin, el = M.el;

  function paint() {
    var s = M.load();
    document.querySelectorAll('.card[data-slug]').forEach(function (c) {
      var done = !!s.finished[c.getAttribute('data-slug')];
      c.classList.toggle('done', done);
      var mark = c.querySelector('.done-mark'); if (mark) mark.hidden = !done;
    });

    var kept = M.liveKept(s);
    var box = document.getElementById('resurface');
    if (kept.length) {
      // Prefer something older than a day, so it's a reminder rather than an echo.
      var old = kept.filter(function (k) { return Date.now() - k.ts > 86400000; });
      var pool = old.length ? old : kept;
      var k = pool[Math.floor(Math.random() * pool.length)];
      document.getElementById('resurface-text').textContent = k.text;
      var meta = document.getElementById('resurface-meta');
      meta.innerHTML = '';
      meta.appendChild(el('a', { href: '/p/' + k.slug + '#p-' + k.para, text: k.title }));
      meta.appendChild(document.createTextNode(' · ' + k.author));
      box.hidden = false;
    }

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
    });
  }
  paint();
})();
