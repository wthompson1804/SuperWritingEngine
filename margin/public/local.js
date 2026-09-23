// Shared browser state. Everything a reader does lives in localStorage under
// one key. A reader key, if they get one, just mirrors that blob to the server.
(function () {
  'use strict';
  var STORE = 'margin:v1';

  function blank() { return { kept: {}, follows: {}, finished: {}, readerKey: null, prefs: null, asks: {} }; }
  function load() {
    try {
      var d = JSON.parse(localStorage.getItem(STORE) || '{}');
      var b = blank();
      for (var k in b) if (d[k] != null) b[k] = d[k];
      return b;
    } catch (e) { return blank(); }
  }
  function save(s) { try { localStorage.setItem(STORE, JSON.stringify(s)); } catch (e) { /* storage blocked: still works for this page */ } }

  function api(path, body) {
    return fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { return r.json(); })
      .catch(function () { return { ok: false, error: 'Network problem. Try again.' }; });
  }

  function payload(s) { return { kept: s.kept, follows: s.follows, finished: s.finished }; }
  function absorb(r) {
    if (!r || !r.data) return;
    var cur = load();
    cur.kept = r.data.kept || {}; cur.follows = r.data.follows || {}; cur.finished = r.data.finished || {};
    if (r.prefs) cur.prefs = r.prefs;
    save(cur);
  }
  var timer = null;
  function sync() {
    var s = load();
    if (!s.readerKey) return Promise.resolve(null);
    return api('/api/key/sync', { key: s.readerKey, data: payload(s) }).then(function (r) { if (r.ok) absorb(r); return r; });
  }
  function scheduleSync() { if (!load().readerKey) return; clearTimeout(timer); timer = setTimeout(sync, 800); }
  function update(fn) { var s = load(); fn(s); save(s); scheduleSync(); return s; }

  function follow(handle, name, on, slug) {
    update(function (s) { s.follows[handle] = { on: on, name: name, ts: Date.now() }; });
    return api('/api/follow', { handle: handle, delta: on ? 1 : -1, slug: slug, key: load().readerKey || undefined });
  }
  function isFollowing(handle) { var f = load().follows[handle]; return !!(f && f.on); }
  function liveKept(s) {
    s = s || load();
    return Object.keys(s.kept).map(function (id) { return s.kept[id]; }).filter(function (k) { return k && !k.deleted; });
  }
  function keep(entry) {
    var id = entry.slug + ':' + entry.para + ':' + Date.now().toString(36);
    update(function (s) { entry.id = id; entry.ts = Date.now(); s.kept[id] = entry; });
    return id;
  }
  function createKey() {
    return api('/api/key/new', { data: payload(load()) }).then(function (r) {
      if (r.key) { var s = load(); s.readerKey = r.key; s.prefs = r.prefs; save(s); absorb(r); }
      return r;
    });
  }
  function useKey(key) {
    var s = load(); var prev = s.readerKey; s.readerKey = key.trim(); save(s);
    return sync().then(function (r) {
      if (!r || !r.ok) { var t = load(); t.readerKey = prev; save(t); }
      return r;
    });
  }

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    var b = new Uint8Array(16); crypto.getRandomValues(b);
    b[6] = (b[6] & 15) | 64; b[8] = (b[8] & 63) | 128;
    var hx = Array.prototype.map.call(b, function (x) { return (x + 256).toString(16).slice(1); }).join('');
    return hx.slice(0, 8) + '-' + hx.slice(8, 12) + '-' + hx.slice(12, 16) + '-' + hx.slice(16, 20) + '-' + hx.slice(20);
  }

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    for (var k in (attrs || {})) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'on') for (var ev in attrs.on) n.addEventListener(ev, attrs.on[ev]);
      else if (attrs[k] != null && attrs[k] !== false) n.setAttribute(k, attrs[k] === true ? '' : attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c != null) n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return n;
  }

  var pageData = null;
  try { var pd = document.getElementById('page-data'); pageData = pd ? JSON.parse(pd.textContent) : null; } catch (e) { pageData = null; }

  // The reader-key panel appears on the commonplace and Brief pages, and a
  // smaller version appears inline after an earned ask.
  function renderKeyPanel(root, opts) {
    opts = opts || {};
    if (!root) return;
    var s = load();
    root.innerHTML = '';
    if (!s.readerKey) {
      var kept = liveKept(s).length;
      var follows = Object.keys(s.follows).filter(function (h) { return s.follows[h].on; }).length;
      root.appendChild(el('h2', { text: opts.focus === 'brief' ? 'Get The Brief' : 'Keep this for good' }));
      root.appendChild(el('p', { text: opts.focus === 'brief'
        ? 'The Brief needs somewhere to go, so it needs an email address. That address hangs off a reader key: four words and a code, and no password. Get a key, then add the address.'
        : 'Right now your ' + kept + ' kept passage' + (kept === 1 ? '' : 's') + ' and ' + follows + ' follow' + (follows === 1 ? '' : 's') + ' live only in this browser. A reader key is four words and a code, with no email and no password. It keeps them on every device and lets you write in the margin.' }));
      var status = el('p', { class: 'small muted', 'aria-live': 'polite' });
      var get = el('button', { class: 'btn', text: 'Get a reader key', on: { click: function () {
        get.disabled = true;
        createKey().then(function (r) {
          if (!r.key) { status.textContent = r.error || 'Could not create a key.'; get.disabled = false; return; }
          renderKeyPanel(root, Object.assign({}, opts, { justCreated: true }));
        });
      } } });
      var input = el('input', { placeholder: 'otter-granite-plum-fjord-7KQ2MX', 'aria-label': 'Your reader key', autocomplete: 'off', spellcheck: 'false' });
      var restore = el('form', { class: 'row', on: { submit: function (e) {
        e.preventDefault();
        useKey(input.value).then(function (r) {
          if (r && r.ok) { renderKeyPanel(root, opts); if (opts.onChange) opts.onChange(); }
          else status.textContent = (r && r.error) || 'That key didn\'t work.';
        });
      } } }, [input, el('button', { class: 'btn ghost', type: 'submit', text: 'Use my key' })]);
      root.appendChild(el('div', { class: 'row' }, [get]));
      root.appendChild(el('details', {}, [el('summary', { text: 'I already have a key' }), restore]));
      root.appendChild(status);
      return;
    }
    var prefs = s.prefs || { email: '', digest: false, share_email: false };
    root.appendChild(el('h2', { text: opts.justCreated ? 'Here is your reader key' : 'Your reader key' }));
    var keyText = el('code', { class: 'key' + (opts.justCreated ? '' : ' masked'), text: s.readerKey, tabindex: '0', title: 'Click to show' });
    keyText.addEventListener('click', function () { keyText.classList.remove('masked'); });
    root.appendChild(el('p', {}, [keyText]));
    root.appendChild(el('p', { class: 'small', text: 'Write it down or put it in your password manager. It\'s the only way back in: we store a scrambled version and can\'t recover it for you.' }));
    var email = el('input', { type: 'email', value: prefs.email || '', placeholder: 'you@example.com', 'aria-label': 'Email (optional)' });
    var digest = el('input', { type: 'checkbox' }); digest.checked = !!prefs.digest;
    var share = el('input', { type: 'checkbox' }); share.checked = !!prefs.share_email;
    var msg = el('p', { class: 'small muted', 'aria-live': 'polite' });
    var form = el('form', { class: 'stack prefs', on: { submit: function (e) {
      e.preventDefault();
      api('/api/key/prefs', { key: load().readerKey, email: email.value, digest: digest.checked, share_email: share.checked }).then(function (r) {
        if (r.ok) { var t = load(); t.prefs = r.prefs; save(t); msg.textContent = 'Saved.'; } else msg.textContent = r.error || 'Could not save.';
      });
    } } }, [
      el('label', {}, ['Email ', el('span', { class: 'small muted', text: '(optional, only needed for The Brief)' }), email]),
      el('label', { class: 'check' }, [digest, ' Send me The Brief: one email on Sundays, five pieces at most']),
      el('label', { class: 'check' }, [share, ' Share my email with writers I follow, so I stay on their list if I ever leave Margin']),
      el('div', { class: 'row' }, [el('button', { class: 'btn', type: 'submit', text: 'Save' }), el('button', { class: 'btn ghost', type: 'button', text: 'Sync now', on: { click: function () { sync().then(function (r) { msg.textContent = r && r.ok ? 'Synced.' : 'Sync failed.'; if (opts.onChange) opts.onChange(); }); } } }),
        el('button', { class: 'btn ghost', type: 'button', text: 'Forget key on this device', on: { click: function () {
          if (!confirm('Remove the key from this browser? Your passages stay here, and the key still works everywhere else.')) return;
          var t = load(); t.readerKey = null; t.prefs = null; save(t); renderKeyPanel(root, opts);
        } } })]),
      msg,
    ]);
    root.appendChild(form);
    if (opts.justCreated && opts.onChange) opts.onChange();
  }

  window.Margin = {
    load: load, save: save, api: api, update: update, sync: sync, follow: follow, isFollowing: isFollowing,
    keep: keep, liveKept: liveKept, createKey: createKey, useKey: useKey, uuid: uuid, el: el, data: pageData,
    renderKeyPanel: renderKeyPanel,
  };

  // Pull the latest from the server once per page if this browser holds a key.
  if (load().readerKey) sync();
})();
