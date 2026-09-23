(function () {
  'use strict';
  var M = window.Margin, D = M.data;
  var btn = document.getElementById('follow-btn');
  if (!btn || !D) return;
  function paint() {
    var on = M.isFollowing(D.handle);
    btn.textContent = on ? 'Following' : 'Follow';
    btn.classList.toggle('ghost', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  }
  btn.addEventListener('click', function () { M.follow(D.handle, D.name, !M.isFollowing(D.handle)); paint(); });
  paint();
  var s = M.load();
  document.querySelectorAll('.card[data-slug]').forEach(function (c) {
    if (s.finished[c.getAttribute('data-slug')]) { c.classList.add('done'); c.querySelector('.done-mark').hidden = false; }
  });
})();
