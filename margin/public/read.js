// Article page: anonymous reading signal, keeping passages, passing them on,
// margin notes, and the one ask that appears only at the end of the piece.
(function () {
  'use strict';
  var M = window.Margin, D = M.data, el = M.el;
  if (!D) return;
  var body = document.getElementById('body');
  var finishEl = document.getElementById('finish');
  var pv = M.uuid();
  var coarse = window.matchMedia && matchMedia('(pointer: coarse)').matches;

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
  var maxDepth = 0, dwell = 0, lastActive = Date.now();
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
    var payload = JSON.stringify({ slug: D.slug, pv: pv, depth: maxDepth, dwell: dwell, source: source, keyed: !!M.load().readerKey, visible: visible });
    if (final && navigator.sendBeacon) { navigator.sendBeacon('/api/read', new Blob([payload], { type: 'text/plain' })); return; }
    fetch('/api/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true })
      .then(function (r) { return r.json(); })
      .then(function (r) { if (r && typeof r.now === 'number') setText('now-n', Math.max(1, r.now)); })
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
  document.addEventListener('visibilitychange', function () { beacon(document.visibilityState === 'hidden'); });
  window.addEventListener('pagehide', function () { beacon(true); });
  setTimeout(function () { maxDepth = Math.max(maxDepth, depthNow()); beacon(false); }, 1500);

  // ---------- finishing ----------
  // The box appears when the reader reaches the end. Whether it counts as a
  // verified read (enough time on the page) only affects the numbers.
  var shownFinish = false, verified = false;
  function checkFinish() {
    if (maxDepth >= 0.9 && !shownFinish) { shownFinish = true; finishEl.hidden = false; renderAsk(); }
    if (!verified && maxDepth >= 0.9 && dwell >= D.minMs) {
      verified = true;
      M.update(function (s) { s.finished[D.slug] = { handle: D.author.handle, ts: Date.now() }; });
      beacon(false);
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

  // One ask. Follow comes first, framed by how the updates arrive, with email
  // and the fediverse one tap away. Once the reader already follows, the ask
  // becomes a reader key, and only when they have something to lose.
  function renderAsk() {
    var root = document.getElementById('ask');
    root.innerHTML = '';
    var s = M.load();
    var name = D.author.name, handle = D.author.handle, first = name.split(' ')[0];
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
        // The recommendations repeat the "reads" box below; show them once.
        var reads = document.querySelector('.after .reads'); if (reads) reads.hidden = true;
      };
      var btn = el('button', { class: 'btn primary', type: 'button', text: 'Follow ' + first + ' here', on: { click: function () {
        M.follow(handle, name, true, D.slug);
        after('Following. ' + first + '’s new pieces will be at the top of Today in this browser.');
      } } });
      var more = el('details', { class: 'more-ways' }, [
        el('summary', { text: 'Or get them by email, or on Mastodon' }),
        M.emailForm(handle, name, null, function (r) { if (r.already) return; M.follow(handle, name, true, D.slug); after('Almost there: open the email we sent and confirm. Following here too.', r); }),
        D.fediHandle ? el('p', { class: 'small' }, ['On Mastodon, Threads or another fediverse app, search for ', el('code', { text: D.fediHandle }), '.']) : null,
      ]);
      root.appendChild(el('div', { class: 'ask' }, [
        el('p', {}, [el('strong', { text: 'Want the next one from ' + first + '?' })]),
        el('div', { class: 'row' }, [btn, el('span', { class: 'small muted', text: 'No account. New pieces show at the top of Today.' })]),
        more,
      ]));
      return;
    }
    if (!s.readerKey && (finishedN >= 3 || keptN >= 3)) {
      logAsk('key', 'shown');
      var box = el('div', { class: 'ask key-ask' });
      box.appendChild(el('p', {}, [el('strong', { text: 'You’ve finished ' + finishedN + ' piece' + (finishedN === 1 ? '' : 's') + ' and kept ' + keptN + ' passage' + (keptN === 1 ? '' : 's') + '.' }),
        ' Right now they live only in this browser. A reader key is four words and a code, with no email and no password. It keeps them safe and lets you write in the margin.']));
      var panel = el('div', { class: 'key-panel inline' });
      box.appendChild(el('button', { class: 'btn primary', type: 'button', text: 'Get a reader key', on: { click: function () {
        M.createKey().then(function (r) { if (r.key) { logAsk('key', 'accepted'); M.renderKeyPanel(panel, { justCreated: true }); box.querySelector('button').remove(); } });
      } } }));
      box.appendChild(panel);
      root.appendChild(box);
      return;
    }
    root.appendChild(el('p', { class: 'muted', text: 'You follow ' + first + '. Thanks for reading to the end.' }));
  }

  // ---------- paragraph furniture ----------
  function paraEl(i) { return body.querySelector('[data-p="' + i + '"]'); }
  Object.keys(D.noteCounts || {}).forEach(function (p) {
    var node = paraEl(p); if (!node) return;
    var n = D.noteCounts[p];
    node.appendChild(el('a', { class: 'mcount', href: '#notes-p' + p, 'aria-label': n + ' margin note' + (n === 1 ? '' : 's') + ' on this passage', text: String(n) }));
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
        node.normalize(); // no empty text nodes left behind
        return true;
      }
    }
    return false;
  }
  M.liveKept().filter(function (k) { return k.slug === D.slug; }).forEach(function (k) {
    var node = paraEl(k.para); if (!node) return;
    node.classList.add('kept');
    markText(node, k.text);
  });

  // Plain text of a block, without our own furniture inside it.
  function blockText(node) {
    var c = node.cloneNode(true);
    c.querySelectorAll('.mcount, .p-act, .fnref').forEach(function (x) { x.remove(); });
    return c.textContent.replace(/\s+/g, ' ').trim();
  }

  // Arriving from a passed-on link: label the passage itself, so the context
  // is on screen next to the highlight rather than scrolled away above it.
  var passedPara = source === 'passed' ? params.get('p') : null;
  if (passedPara != null && paraEl(passedPara)) {
    var pp = paraEl(passedPara);
    pp.classList.add('passed-hl');
    var tag = el('p', { class: 'passed-tag', role: 'note' }, [el('strong', { text: 'Someone passed you this passage.' }), ' The whole piece is here. ', el('a', { href: '#piece', text: 'Start from the top' })]);
    pp.parentNode.insertBefore(tag, pp);
    setTimeout(function () { tag.scrollIntoView({ block: 'center' }); }, 60);
  } else if (/^#p-\d+$/.test(location.hash)) {
    var target = paraEl(location.hash.slice(3));
    if (target) { target.scrollIntoView({ block: 'center' }); target.classList.add('flash'); }
  }

  // ---------- actions toolbar ----------
  // Two ways in: select text (any device), or the ⋯ button beside each
  // paragraph (keyboard and screen readers, or a whole paragraph at once).
  // On touch screens the toolbar docks to the bottom, clear of the phone's own
  // selection menu, which web pages can't suppress.
  var bar = document.getElementById('selbar');
  var barQuote = el('p', { class: 'selbar-quote' });
  bar.insertBefore(barQuote, bar.firstChild);
  if (coarse) bar.classList.add('docked');
  var current = null, opener = null;

  body.querySelectorAll('p[data-p], li[data-p], blockquote[data-p]').forEach(function (node) {
    var b = el('button', { type: 'button', class: 'p-act', 'aria-label': 'Keep, pass on, or note this paragraph', 'aria-haspopup': 'true', text: '⋯' });
    b.addEventListener('click', function (e) {
      e.stopPropagation();
      openBar({ para: Number(node.getAttribute('data-p')), text: blockText(node).slice(0, 600), rect: node.getBoundingClientRect() }, b);
    });
    node.appendChild(b);
  });

  var WORD = /[\p{L}\p{N}'’]/u;
  function snap(range) {
    // Don't cut words in half: "costs somewh" becomes "costs somewhere".
    var s = range.startContainer, e = range.endContainer, so = range.startOffset, eo = range.endOffset;
    if (s.nodeType === 3) while (so > 0 && WORD.test(s.data[so - 1]) && WORD.test(s.data[so] || '')) so--;
    if (e.nodeType === 3) while (eo < e.data.length && eo > 0 && WORD.test(e.data[eo]) && WORD.test(e.data[eo - 1])) eo++;
    var r = document.createRange(); r.setStart(s, so); r.setEnd(e, eo);
    return r;
  }
  function selectionInfo() {
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
    var range = snap(sel.getRangeAt(0));
    var start = range.startContainer.nodeType === 1 ? range.startContainer : range.startContainer.parentElement;
    var p = start && start.closest && start.closest('[data-p]');
    if (!p || !body.contains(p)) return null;
    var text;
    if (!p.contains(range.endContainer)) {
      // Keep within one paragraph; if the selection runs on, clip to this one.
      var r2 = document.createRange(); r2.setStart(range.startContainer, range.startOffset); r2.setEndAfter(p.lastChild);
      text = r2.toString();
    } else text = range.toString();
    text = text.replace(/[⋯]/g, '').replace(/\s+/g, ' ').trim();
    if (text.length < 3) return null;
    return { para: Number(p.getAttribute('data-p')), text: text.slice(0, 600), rect: range.getBoundingClientRect() };
  }
  function openBar(info, fromButton) {
    current = info; opener = fromButton || null;
    barQuote.textContent = '“' + (info.text.length > 90 ? info.text.slice(0, 88) + '…' : info.text) + '”';
    bar.hidden = false;
    if (!bar.classList.contains('docked')) {
      var top = window.scrollY + info.rect.top - bar.offsetHeight - 8;
      var left = window.scrollX + info.rect.left + Math.min(info.rect.width, 600) / 2 - bar.offsetWidth / 2;
      bar.style.top = Math.max(window.scrollY + 4, top) + 'px';
      bar.style.left = Math.max(8, Math.min(left, document.documentElement.clientWidth - bar.offsetWidth - 8)) + 'px';
    }
    if (fromButton) bar.querySelector('[data-act]').focus();
  }
  function closeBar(restore) {
    bar.hidden = true;
    if (restore && opener) opener.focus();
    current = null; opener = null;
  }
  function fromSelection() {
    var info = selectionInfo();
    if (info) openBar(info);
    else if (!opener) closeBar(false);
  }
  document.addEventListener('mouseup', function (e) { if (!bar.contains(e.target)) setTimeout(fromSelection, 0); });
  document.addEventListener('keyup', function (e) { if (e.shiftKey) setTimeout(fromSelection, 0); });
  document.addEventListener('selectionchange', function () { clearTimeout(fromSelection.t); fromSelection.t = setTimeout(fromSelection, coarse ? 150 : 300); });
  bar.addEventListener('mousedown', function (e) { e.preventDefault(); });
  bar.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-act]');
    if (!btn || !current) return;
    var act = btn.getAttribute('data-act');
    if (act === 'close') { closeBar(true); return; }
    var info = current;
    closeBar(false);
    window.getSelection().removeAllRanges();
    var hint = document.getElementById('hint'); if (hint) hint.hidden = true;
    if (act === 'keep') doKeep(info);
    else if (act === 'pass') doPass(info);
    else openNote(info);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (sheet && !sheet.hidden) { closeSheet(); return; }
    if (!bar.hidden) { closeBar(true); return; }
    if (!form.hidden) closeNote();
  });

  function toast(msg) {
    var t = el('div', { class: 'toast', role: 'status', text: msg });
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add('out'); }, 2600);
    setTimeout(function () { t.remove(); }, 3200);
  }

  // ---------- keep ----------
  function doKeep(info) {
    M.persist();
    M.keep({ slug: D.slug, title: D.title, author: D.author.name, handle: D.author.handle, para: info.para, text: info.text, note: '' });
    M.api('/api/keep', { slug: D.slug, para: info.para, pv: pv });
    var node = paraEl(info.para);
    if (node) { node.classList.add('kept'); markText(node, info.text); }
    var n = M.liveKept().length;
    toast('Kept. ' + n + ' passage' + (n === 1 ? '' : 's') + ' in your commonplace.');
  }

  // ---------- pass it on ----------
  function fragEnc(t) { return encodeURIComponent(t).replace(/-/g, '%2D').replace(/,/g, '%2C').replace(/&/g, '%26'); }
  function textFragment(text) {
    var words = text.replace(/[“”"]/g, ' ').trim().split(/\s+/).filter(Boolean);
    if (!words.length) return '';
    if (words.length <= 10) return '#:~:text=' + fragEnc(words.join(' '));
    return '#:~:text=' + fragEnc(words.slice(0, 5).join(' ')) + ',' + fragEnc(words.slice(-5).join(' '));
  }
  // The writer sees that the piece was passed on, never who passed it. The
  // text fragment makes browsers highlight the passage even without Margin's
  // script (Chrome, Edge, Safari 16.1+, Firefox 131+).
  function doPass(info) {
    M.api('/api/pass', { slug: D.slug, para: info.para }).then(function (r) {
      if (!r || !r.ok) { toast('Couldn’t make a link. Try again.'); return; }
      var url = location.origin + r.url + textFragment(info.text);
      var message = '“' + info.text + '”\n' + url;
      if (coarse && navigator.share) {
        navigator.share({ title: D.title, text: '“' + info.text + '”', url: url }).catch(function () {});
        return;
      }
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(message).then(function () { toast('Copied the quote and a link that opens right at it.'); }, function () { openSheet(info, url, message); });
      } else openSheet(info, url, message);
    });
  }
  var sheet = null, sheetInput = null;
  function openSheet(info, url, message) {
    if (!sheet) {
      sheetInput = el('textarea', { class: 'share-text', rows: '4', readonly: true, 'aria-label': 'Quote and link to copy' });
      var status = el('p', { class: 'small ok', 'aria-live': 'polite' });
      sheet = el('div', { class: 'share-sheet box', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Pass this passage on', hidden: true }, [
        el('p', { class: 'bar' }, [el('span', { text: 'pass it on' }), el('span', { class: 'dots', 'aria-hidden': 'true' })]),
        el('div', { class: 'box-body' }, [
          el('p', { class: 'small', text: 'Send this to someone. The link opens the piece with this passage highlighted. No account needed to read it.' }),
          sheetInput,
          el('div', { class: 'row' }, [
            el('button', { class: 'btn primary', type: 'button', text: 'Copy', on: { click: function () {
              sheetInput.focus(); sheetInput.select();
              var ok = false; try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
              status.textContent = ok ? 'Copied.' : 'Selected. Use your device’s copy.';
            } } }),
            el('button', { class: 'btn', type: 'button', text: 'Done', on: { click: closeSheet } }),
          ]),
          status,
        ]),
      ]);
      document.body.appendChild(sheet);
    }
    sheetInput.value = message;
    sheet.querySelector('.ok').textContent = '';
    sheet.hidden = false;
    sheetInput.focus(); sheetInput.select();
  }
  function closeSheet() { if (sheet) sheet.hidden = true; }

  // ---------- margin notes ----------
  // The gate and the form open right under the paragraph, so the reader
  // doesn't lose their place.
  var form = document.getElementById('note-form');
  var quoteEl = document.getElementById('note-quote');
  var home = document.createComment('note-form-home');
  form.parentNode.insertBefore(home, form);
  var pending = null;
  function placeAfter(node, info) {
    var p = paraEl(info.para);
    var anchor = p && (p.closest('ul,ol') || p);
    if (anchor) anchor.parentNode.insertBefore(node, anchor.nextSibling);
  }
  function openNote(info) {
    pending = info;
    var old = document.getElementById('note-gate'); if (old) old.remove();
    if (!M.load().readerKey) {
      var gate = el('div', { class: 'ask key-ask inline-gate', id: 'note-gate' }, [
        el('p', {}, [el('strong', { text: 'Margin notes need a reader key.' }), ' Four words and a code: no email, no name. It keeps spam out without asking who you are.']),
      ]);
      var panel = el('div', { class: 'key-panel inline' });
      gate.appendChild(el('div', { class: 'row' }, [
        el('button', { class: 'btn primary', type: 'button', text: 'Get a key and write the note', on: { click: function () {
          M.createKey().then(function (r) {
            if (!r.key) return;
            M.renderKeyPanel(panel, { justCreated: true });
            gate.querySelector('.row').remove();
            showForm();
          });
        } } }),
        el('button', { class: 'btn', type: 'button', text: 'Not now', on: { click: function () { gate.remove(); pending = null; } } }),
      ]));
      gate.appendChild(panel);
      placeAfter(gate, info);
      gate.querySelector('button').focus();
      return;
    }
    showForm();
  }
  function showForm() {
    quoteEl.textContent = pending.text;
    placeAfter(form, pending);
    form.hidden = false;
    form.querySelector('textarea').focus();
  }
  function closeNote() {
    form.hidden = true; form.reset(); pending = null;
    home.parentNode.insertBefore(form, home.nextSibling);
    var gate = document.getElementById('note-gate'); if (gate) gate.remove();
  }
  document.getElementById('note-cancel').addEventListener('click', closeNote);
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!pending) return;
    var fd = new FormData(form);
    M.api('/api/note', { key: M.load().readerKey, slug: D.slug, para: pending.para, quote: pending.text, body: fd.get('body'), name: fd.get('name') }).then(function (r) {
      if (!r.ok) { toast(r.error || 'Couldn’t add the note.'); return; }
      var empty = document.getElementById('notes-empty'); if (empty) empty.remove();
      var group = el('div', { class: 'note-group' }, [
        el('blockquote', { class: 'note-quote', text: r.note.quote }),
        el('div', { class: 'note' }, [el('p', { text: r.note.body }), el('p', { class: 'meta', text: '— ' + r.note.display_name + ', just now' })]),
      ]);
      home.parentNode.insertBefore(group, home);
      var p = paraEl(r.note.para);
      if (p && !p.querySelector('.mcount')) p.insertBefore(el('a', { class: 'mcount', href: '#notes', 'aria-label': 'Margin notes on this passage', text: '1' }), p.querySelector('.p-act'));
      closeNote();
      toast('Added to the margin.');
    });
  });

  document.querySelectorAll('.flag-note').forEach(function (b) {
    b.addEventListener('click', function () {
      if (!confirm('Flag this note as spam or abuse? Three flags hide it until the writer reviews it.')) return;
      M.api('/api/note/flag', { id: Number(b.getAttribute('data-note')) }).then(function () { b.textContent = 'flagged'; b.disabled = true; });
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
