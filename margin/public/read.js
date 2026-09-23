// Article page: anonymous reading signal, keeping passages, margin notes, and
// the earned ask that only shows up once a reader has finished the piece.
(function () {
  'use strict';
  var M = window.Margin, D = M.data, el = M.el;
  if (!D) return;
  var body = document.getElementById('body');
  var finishEl = document.getElementById('finish');
  var pv = M.uuid();

  // ---------- where did this reader come from ----------
  var source = 'direct';
  var params = new URLSearchParams(location.search);
  var via = params.get('via');
  if (via) source = via;
  else if (document.referrer) {
    try {
      var ref = new URL(document.referrer);
      if (ref.origin === location.origin) source = ref.pathname === '/' ? 'front' : ref.pathname.indexOf('/@') === 0 ? 'author' : ref.pathname.indexOf('/p/') === 0 ? 'next' : 'direct';
    } catch (e) { /* ignore */ }
  }

  // ---------- depth + visible, active dwell ----------
  var maxDepth = 0, dwell = 0, lastActive = Date.now(), sent = { depth: -1, dwell: -1 };
  function depthNow() {
    var r = body.getBoundingClientRect();
    if (r.height <= 0) return 0;
    return Math.max(0, Math.min(1, (window.innerHeight - r.top) / r.height));
  }
  ['scroll', 'keydown', 'mousemove', 'touchstart', 'wheel'].forEach(function (ev) {
    window.addEventListener(ev, function () { lastActive = Date.now(); }, { passive: true });
  });
  function tick() {
    maxDepth = Math.max(maxDepth, depthNow());
    if (document.visibilityState === 'visible' && Date.now() - lastActive < 30000) dwell += 1000;
    checkFinish();
  }
  // Beacons go out every 10s while visible (that's what "reading now" counts),
  // and once more with visible:false when the tab is hidden or closed.
  function beacon(final) {
    var visible = !final && document.visibilityState === 'visible';
    sent = { depth: maxDepth, dwell: dwell };
    var payload = JSON.stringify({ slug: D.slug, pv: pv, depth: maxDepth, dwell: dwell, source: source, keyed: !!M.load().readerKey, visible: visible });
    if (final && navigator.sendBeacon) { navigator.sendBeacon('/api/read', new Blob([payload], { type: 'text/plain' })); return; }
    fetch('/api/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true })
      .then(function (r) { return r.json(); })
      .then(function (r) { if (r && typeof r.now === 'number') setText('now-n', r.now); })
      .catch(function () {});
  }
  function setText(id, v) { var n = document.getElementById(id); if (n) n.textContent = String(v); }
  function presence() {
    fetch('/api/presence?slug=' + encodeURIComponent(D.slug)).then(function (r) { return r.json(); }).then(function (r) {
      if (!r || !r.ok) return;
      setText('now-n', Math.max(1, r.now)); setText('fin-n', r.reads);
    }).catch(function () {});
  }
  // The server-rendered count doesn't include this tab yet; you are reading too.
  var nowEl = document.getElementById('now-n');
  if (nowEl) nowEl.textContent = String((parseInt(nowEl.textContent, 10) || 0) + 1);
  setInterval(tick, 1000);
  setInterval(function () { if (document.visibilityState === 'visible') beacon(false); }, 10000);
  setInterval(function () { if (document.visibilityState === 'visible') presence(); }, 30000);
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') beacon(true); else beacon(false); });
  window.addEventListener('pagehide', function () { beacon(true); });
  setTimeout(function () { maxDepth = Math.max(maxDepth, depthNow()); beacon(false); }, 1500);

  // ---------- finishing ----------
  var shownFinish = false, verified = false;
  function checkFinish() {
    if (maxDepth >= 0.9 && !shownFinish) { shownFinish = true; finishEl.hidden = false; }
    if (!verified && maxDepth >= 0.9 && dwell >= D.minMs) {
      verified = true;
      M.update(function (s) { s.finished[D.slug] = { handle: D.author.handle, ts: Date.now() }; });
      beacon(false);
      renderAsk();
    }
  }
  window.addEventListener('scroll', function () { maxDepth = Math.max(maxDepth, depthNow()); if (maxDepth >= 0.9 && !shownFinish) checkFinish(); }, { passive: true });

  function logAsk(kind, event) {
    var id = D.slug + ':' + kind + ':' + event;
    var s = M.load();
    if (s.asks[id]) return;
    s.asks[id] = Date.now(); M.save(s);
    M.api('/api/ask', { slug: D.slug, kind: kind, event: event });
  }

  // One ask, and only after the piece is finished: follow first, then a key
  // once the reader has something worth keeping.
  function renderAsk() {
    var root = document.getElementById('ask');
    root.innerHTML = '';
    var s = M.load();
    var name = D.author.name, handle = D.author.handle;
    var finishedN = Object.keys(s.finished).length;
    var keptN = M.liveKept(s).length;
    if (!M.isFollowing(handle)) {
      logAsk('follow', 'shown');
      var recs = el('div', { class: 'recs-slot' });
      var after = function (text, r) {
        logAsk('follow', 'accepted');
        root.innerHTML = '';
        var p = el('p', { text: text });
        if (r && r.previewLink) p.appendChild(el('span', { class: 'mono small' }, [' (Prototype: email isn’t sent yet. ', el('a', { href: r.previewLink, text: 'confirm here' }), '.)']));
        root.appendChild(el('div', { class: 'ask' }, [p, recs]));
        M.renderRecs(recs, handle, name, D.slug);
      };
      var btn = el('button', { class: 'btn primary', text: 'Follow ' + name, on: { click: function () {
        M.follow(handle, name, true, D.slug);
        after('Following. New pieces from ' + name + ' will sit at the top of Today in this browser.');
      } } });
      root.appendChild(el('div', { class: 'ask' }, [
        el('p', {}, [el('strong', { text: 'Want the next one from ' + name + '?' }), ' Follow here with no account, or get new pieces by email.']),
        el('div', { class: 'row' }, [btn]),
        M.emailForm(handle, name, null, function (r) { if (r.already) return; M.follow(handle, name, true, D.slug); after('Almost there: confirm the email and you’re on ' + name + '’s list. Following here too.', r); }),
      ]));
      return;
    }
    if (!s.readerKey && (finishedN >= 3 || keptN >= 3)) {
      logAsk('key', 'shown');
      var box = el('div', { class: 'ask key-ask' });
      box.appendChild(el('p', {}, [el('strong', { text: 'You\'ve finished ' + finishedN + ' piece' + (finishedN === 1 ? '' : 's') + ' and kept ' + keptN + ' passage' + (keptN === 1 ? '' : 's') + '.' }),
        ' They only live in this browser. A reader key is four words and a code: no email, no password. It keeps everything and lets you write in the margin.']));
      var panel = el('div', { class: 'key-panel inline' });
      box.appendChild(el('button', { class: 'btn primary', text: 'Get a reader key', on: { click: function () {
        M.createKey().then(function (r) { if (r.key) { logAsk('key', 'accepted'); M.renderKeyPanel(panel, { justCreated: true }); box.querySelector('button').remove(); } });
      } } }));
      box.appendChild(panel);
      root.appendChild(box);
      return;
    }
    root.appendChild(el('p', { class: 'muted', text: 'You follow ' + name + '. That\'s ' + finishedN + ' piece' + (finishedN === 1 ? '' : 's') + ' finished on Margin.' }));
  }

  // ---------- paragraph furniture: note counts, most-kept marker, saved keeps ----------
  function paraEl(i) { return body.querySelector('[data-p="' + i + '"]'); }
  Object.keys(D.noteCounts || {}).forEach(function (p) {
    var node = paraEl(p); if (!node) return;
    node.appendChild(el('a', { class: 'mcount', href: '#notes-p' + p, title: 'Margin notes on this passage', text: String(D.noteCounts[p]) }));
  });
  if (D.topKeep) {
    var tk = paraEl(D.topKeep.para);
    if (tk) { tk.classList.add('most-kept'); tk.setAttribute('data-kept', 'Kept by ' + D.topKeep.n + ' readers'); }
  }
  function markText(node, text) {
    var walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
    var t;
    while ((t = walker.nextNode())) {
      var i = t.nodeValue.indexOf(text);
      if (i >= 0) {
        var r = document.createRange(); r.setStart(t, i); r.setEnd(t, i + text.length);
        try { r.surroundContents(el('mark', { class: 'kept-mark' })); } catch (e) { /* spans elements */ }
        return true;
      }
    }
    return false;
  }
  function paintKeeps() {
    M.liveKept().filter(function (k) { return k.slug === D.slug; }).forEach(function (k) {
      var node = paraEl(k.para); if (!node) return;
      node.classList.add('kept');
      markText(node, k.text);
    });
  }
  paintKeeps();
  var passedPara = source === 'passed' ? params.get('p') : null;
  if (passedPara != null && paraEl(passedPara)) {
    var pp = paraEl(passedPara);
    pp.classList.add('passed-hl');
    document.getElementById('passed-banner').hidden = false;
    setTimeout(function () { pp.scrollIntoView({ block: 'center' }); }, 60);
  } else if (/^#p-\d+$/.test(location.hash)) {
    var target = paraEl(location.hash.slice(3));
    if (target) { target.scrollIntoView({ block: 'center' }); target.classList.add('flash'); }
  }

  // ---------- selection toolbar ----------
  var bar = document.getElementById('selbar');
  var current = null;
  function selectionInfo() {
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
    var range = sel.getRangeAt(0);
    var start = range.startContainer.nodeType === 1 ? range.startContainer : range.startContainer.parentElement;
    var p = start && start.closest && start.closest('[data-p]');
    if (!p || !body.contains(p)) return null;
    var text = sel.toString().replace(/\s+/g, ' ').trim();
    if (text.length < 3) return null;
    // Keep within one paragraph; if the selection runs on, clip to this one.
    if (!p.contains(range.endContainer)) {
      var r2 = document.createRange(); r2.setStart(range.startContainer, range.startOffset); r2.setEndAfter(p.lastChild);
      text = r2.toString().replace(/\s+/g, ' ').trim();
    }
    return { para: Number(p.getAttribute('data-p')), text: text.slice(0, 600), rect: range.getBoundingClientRect() };
  }
  function showBar() {
    current = selectionInfo();
    if (!current) { bar.hidden = true; return; }
    bar.hidden = false;
    var top = window.scrollY + current.rect.top - bar.offsetHeight - 8;
    var left = window.scrollX + current.rect.left + current.rect.width / 2 - bar.offsetWidth / 2;
    bar.style.top = Math.max(window.scrollY + 4, top) + 'px';
    bar.style.left = Math.max(8, Math.min(left, document.documentElement.clientWidth - bar.offsetWidth - 8)) + 'px';
  }
  document.addEventListener('mouseup', function () { setTimeout(showBar, 0); });
  document.addEventListener('keyup', function (e) { if (e.shiftKey) setTimeout(showBar, 0); });
  document.addEventListener('selectionchange', function () {
    clearTimeout(showBar.t); showBar.t = setTimeout(showBar, 350);
  });
  bar.addEventListener('mousedown', function (e) { e.preventDefault(); });
  bar.addEventListener('click', function (e) {
    var act = e.target.getAttribute('data-act');
    if (!act || !current) return;
    var info = current;
    bar.hidden = true;
    window.getSelection().removeAllRanges();
    var hint = document.getElementById('hint'); if (hint) hint.hidden = true;
    if (act === 'keep') doKeep(info);
    else if (act === 'pass') doPass(info);
    else openNote(info);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (!bar.hidden) { bar.hidden = true; return; }
    if (!form.hidden) { form.hidden = true; pending = null; }
  });

  function fragEnc(t) { return encodeURIComponent(t).replace(/-/g, '%2D').replace(/,/g, '%2C').replace(/&/g, '%26'); }
  function textFragment(text) {
    var words = text.replace(/[“”"]/g, ' ').trim().split(/\s+/).filter(Boolean);
    if (!words.length) return '';
    if (words.length <= 10) return '#:~:text=' + fragEnc(words.join(' '));
    return '#:~:text=' + fragEnc(words.slice(0, 5).join(' ')) + ',' + fragEnc(words.slice(-5).join(' '));
  }

  // Pass it on: a link that opens this piece with this passage highlighted.
  // The writer sees that the piece was passed on, not who passed it.
  function doPass(info) {
    M.api('/api/pass', { slug: D.slug, para: info.para }).then(function (r) {
      if (!r || !r.ok) { toast('Could not make a link. Try again.'); return; }
      // A text fragment (#:~:text=) makes browsers highlight the passage
      // natively (Chrome, Edge, Safari 16.1+, Firefox 131+), even without our
      // script. The ?p= parameter is for our own highlight and the preview.
      var url = location.origin + r.url + textFragment(info.text);
      var coarse = window.matchMedia && matchMedia('(pointer: coarse)').matches;
      if (coarse && navigator.share) {
        navigator.share({ title: D.title, text: '“' + info.text + '”', url: url }).catch(function () {});
        return;
      }
      var copy = navigator.clipboard && window.isSecureContext ? navigator.clipboard.writeText('“' + info.text + '” ' + url) : Promise.reject();
      copy.then(function () { toast('Copied the quote and a link that opens right at it. Send it to someone.'); })
        .catch(function () { window.prompt('Copy this link. It opens right at the passage:', url); });
    });
  }

  function toast(msg) {
    var t = el('div', { class: 'toast', role: 'status', text: msg });
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add('out'); }, 2200);
    setTimeout(function () { t.remove(); }, 2800);
  }

  document.querySelectorAll('.flag-note').forEach(function (b) {
    b.addEventListener('click', function () {
      if (!confirm('Flag this note as spam or abuse? Three flags hide it until the writer reviews it.')) return;
      M.api('/api/note/flag', { id: Number(b.getAttribute('data-note')) }).then(function () { b.textContent = 'flagged'; b.disabled = true; });
    });
  });

  function doKeep(info) {
    M.persist();
    M.keep({ slug: D.slug, title: D.title, author: D.author.name, handle: D.author.handle, para: info.para, text: info.text, note: '' });
    M.api('/api/keep', { slug: D.slug, para: info.para, pv: pv });
    var node = paraEl(info.para);
    if (node) { node.classList.add('kept'); markText(node, info.text); }
    var n = M.liveKept().length;
    toast('Kept. ' + n + ' passage' + (n === 1 ? '' : 's') + ' in your commonplace.');
  }

  // ---------- margin notes ----------
  var form = document.getElementById('note-form');
  var quoteEl = document.getElementById('note-quote');
  var pending = null;
  function openNote(info) {
    pending = info;
    if (!M.load().readerKey) {
      var gate = document.getElementById('note-gate');
      if (gate) gate.remove();
      gate = el('div', { class: 'ask key-ask', id: 'note-gate' }, [
        el('p', {}, [el('strong', { text: 'Margin notes need a reader key.' }), ' It\'s four words and a code, with no email and no name. That keeps the margin free of spam without asking you who you are.']),
      ]);
      var panel = el('div', { class: 'key-panel inline' });
      gate.appendChild(el('button', { class: 'btn primary', text: 'Get a key and write the note', on: { click: function () {
        M.createKey().then(function (r) {
          if (!r.key) return;
          M.renderKeyPanel(panel, { justCreated: true });
          gate.querySelector('button').remove();
          showForm();
        });
      } } }));
      gate.appendChild(panel);
      form.parentNode.insertBefore(gate, form);
      gate.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    showForm();
  }
  function showForm() {
    quoteEl.textContent = pending.text;
    form.hidden = false;
    form.scrollIntoView({ behavior: 'smooth', block: 'center' });
    form.querySelector('textarea').focus({ preventScroll: true });
  }
  document.getElementById('note-cancel').addEventListener('click', function () { form.hidden = true; pending = null; });
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!pending) return;
    var fd = new FormData(form);
    M.api('/api/note', { key: M.load().readerKey, slug: D.slug, para: pending.para, quote: pending.text, body: fd.get('body'), name: fd.get('name') }).then(function (r) {
      if (!r.ok) { toast(r.error || 'Could not add the note.'); return; }
      var empty = document.getElementById('notes-empty'); if (empty) empty.remove();
      var group = el('div', { class: 'note-group' }, [
        el('blockquote', { class: 'note-quote', text: r.note.quote }),
        el('div', { class: 'note' }, [el('p', { text: r.note.body }), el('p', { class: 'meta', text: r.note.display_name + ' · just now' })]),
      ]);
      form.parentNode.insertBefore(group, form);
      form.reset(); form.hidden = true; pending = null;
      toast('Added to the margin.');
    });
  });

  // ---------- tips ----------
  document.querySelectorAll('[data-tip]').forEach(function (b) {
    b.addEventListener('click', function () {
      M.api('/api/tip', { slug: D.slug, cents: Number(b.getAttribute('data-tip')) }).then(function (r) {
        if (r.ok) { document.getElementById('tip-thanks').hidden = false; document.querySelectorAll('[data-tip]').forEach(function (x) { x.disabled = true; }); }
      });
    });
  });
})();
