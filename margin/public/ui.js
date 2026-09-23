// Site-wide bits: the reading settings panel (text size and theme), local
// times, and copy buttons. Settings are stored in this browser only.
(function () {
  'use strict';
  var KEY = 'margin:prefs';
  function load() { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } }
  function save(p) { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) { /* ignore */ } }
  function apply(p) {
    var root = document.documentElement;
    if (p.size && p.size !== 'm') root.setAttribute('data-size', p.size); else root.removeAttribute('data-size');
    if (p.theme === 'light' || p.theme === 'dark') root.setAttribute('data-theme', p.theme); else root.removeAttribute('data-theme');
  }

  var btn = document.getElementById('aa-btn');
  var panel = document.getElementById('aa-panel');
  if (btn && panel) {
    var paint = function () {
      var p = load();
      panel.querySelectorAll('.seg').forEach(function (seg) {
        var cur = p[seg.getAttribute('data-pref')] || (seg.getAttribute('data-pref') === 'size' ? 'm' : 'system');
        seg.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-v') === cur ? 'true' : 'false'); });
      });
    };
    var open = function () { panel.hidden = false; btn.setAttribute('aria-expanded', 'true'); paint(); var b = panel.querySelector('[aria-pressed="true"]'); if (b) b.focus(); };
    var close = function (restore) { panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); if (restore) btn.focus(); };
    btn.addEventListener('click', function () { if (panel.hidden) open(); else close(true); });
    document.getElementById('aa-close').addEventListener('click', function () { close(true); });
    panel.addEventListener('click', function (e) {
      var b = e.target.closest('.seg button');
      if (!b) return;
      var p = load();
      p[b.parentNode.getAttribute('data-pref')] = b.getAttribute('data-v');
      save(p); apply(p); paint();
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) close(true); });
    document.addEventListener('click', function (e) { if (!panel.hidden && !panel.contains(e.target) && e.target !== btn) close(false); });
  }

  // Server-rendered times are UTC; show them in the reader's own zone.
  document.querySelectorAll('time.local-time').forEach(function (t) {
    var d = new Date(t.getAttribute('datetime'));
    if (!isNaN(d)) t.textContent = d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  });

  var copy = document.getElementById('copy-fedi');
  if (copy) copy.addEventListener('click', function () {
    var text = document.getElementById('fedi-handle').textContent;
    var done = function () { copy.textContent = 'copied'; };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, function () {});
    else { var r = document.createRange(); r.selectNodeContents(document.getElementById('fedi-handle')); var s = getSelection(); s.removeAllRanges(); s.addRange(r); copy.textContent = 'selected'; }
  });
})();
