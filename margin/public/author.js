(function () {
  'use strict';
  var M = window.Margin, D = M.data;
  var btn = document.getElementById('follow-btn');
  if (!btn || !D) return;
  var recs = document.getElementById('recs');
  function paint() {
    var on = M.isFollowing(D.handle);
    btn.textContent = on ? 'Following here ✓' : 'Follow here';
    btn.classList.toggle('primary', !on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  }
  btn.addEventListener('click', function () {
    var on = !M.isFollowing(D.handle);
    M.follow(D.handle, D.name, on);
    paint();
    if (on) M.renderRecs(recs, D.handle, D.name);
  });
  paint();

  var form = document.getElementById('email-follow');
  var msg = document.getElementById('ef-msg');
  if (form) form.addEventListener('submit', function (e) {
    e.preventDefault();
    M.emailFollow(D.handle, form.email.value).then(function (r) {
      if (!r.ok) { msg.textContent = r.error || 'That didn’t work.'; return; }
      msg.innerHTML = '';
      if (r.already) { msg.textContent = 'You’re already on ' + D.name + '’s list.'; return; }
      msg.appendChild(document.createTextNode('One step left: open the email we just sent and tap confirm. It works for 7 days, and we’ll remind you once. '));
      if (r.previewLink) msg.appendChild(M.el('span', { class: 'mono' }, ['(Prototype: email isn’t sent yet. ', M.el('a', { href: r.previewLink, text: 'confirm here' }), '.)']));
      if (!M.isFollowing(D.handle)) { M.follow(D.handle, D.name, true); paint(); }
      M.renderRecs(recs, D.handle, D.name);
    });
  });

  var s = M.load();
  document.querySelectorAll('.card[data-slug]').forEach(function (c) {
    if (s.finished[c.getAttribute('data-slug')]) { c.classList.add('done'); c.querySelector('.done-mark').hidden = false; }
  });
})();
