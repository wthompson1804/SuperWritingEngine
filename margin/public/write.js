// The editor: live draft check, autosave, image upload, scheduling, and a
// confirmation before a first publish emails everyone.
(function () {
  'use strict';
  var M = window.Margin, el = M.el, D = M.data || {};
  var form = document.getElementById('editor-form');
  var ta = document.getElementById('body_md');
  var out = document.getElementById('check-results');
  var state = document.getElementById('save-state');
  if (!form || !ta) return;
  var title = form.elements.title, dek = form.elements.dek;
  var LOCAL = 'margin:draft:' + D.id;

  // ---------- draft check ----------
  var t = null;
  function row(r) { return el('li', { class: 'chk chk-' + r.level }, [el('span', { class: 'rule', text: r.rule }), ' ', r.msg]); }
  function check() {
    if (!ta.value.trim()) { out.innerHTML = ''; out.appendChild(el('p', { class: 'muted small', text: 'Start writing…' })); return; }
    M.api('/api/check', { body_md: ta.value }).then(function (r) {
      out.innerHTML = '';
      out.appendChild(el('h4', { text: 'Opening sentence' }));
      out.appendChild(el('ul', { class: 'plain' }, (r.opening || []).map(row)));
      out.appendChild(el('h4', { text: 'Body' }));
      var b = r.body || [];
      out.appendChild(b.length ? el('ul', { class: 'plain' }, b.slice(0, 25).map(row)) : el('p', { class: 'small chk-ok', text: 'No hedges, filler, or negation framing found.' }));
    });
  }

  // ---------- autosave ----------
  // Every change goes to this browser at once, and to the server a couple of
  // seconds later (drafts only: a published piece changes only on Update).
  var dirty = false, saveTimer = null;
  function snapshot() { return { title: title.value, dek: dek.value, body_md: ta.value, at: Date.now() }; }
  function say(text) { if (state) state.textContent = text; }
  function saveLocal() { try { localStorage.setItem(LOCAL, JSON.stringify(snapshot())); } catch (e) { /* ignore */ } }
  function saveServer() {
    if (D.id === 'new' || D.status === 'published') { say(D.status === 'published' ? 'unsaved changes: press Update to publish them' : 'saved in this browser; Save draft to keep it on Margin'); return; }
    say('saving…');
    var sent = snapshot();
    fetch('/write/' + D.id + '/autosave', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sent) })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (!r.ok) { say('not saved: check your connection'); return; }
        D.updatedAt = r.savedAt;
        // Only call it saved if nothing was typed while the request was out.
        var now = snapshot();
        if (now.title === sent.title && now.dek === sent.dek && now.body_md === sent.body_md) {
          dirty = false;
          say('saved ' + new Date(r.savedAt).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }));
          try { localStorage.removeItem(LOCAL); } catch (e) { /* ignore */ }
        }
      })
      .catch(function () { say('offline: saved in this browser only'); });
  }
  function changed() {
    dirty = true;
    var stale = document.querySelector('.editor > .ok[role="status"]'); if (stale) stale.remove();
    saveLocal();
    say('editing…');
    clearTimeout(saveTimer); saveTimer = setTimeout(saveServer, 2000);
    clearTimeout(t); t = setTimeout(check, 600);
  }
  [title, dek, ta].forEach(function (f) { f.addEventListener('input', changed); });

  // Offer to restore a local copy that's newer than what the server has.
  try {
    var saved = JSON.parse(localStorage.getItem(LOCAL) || 'null');
    // Offer it only if it differs and is newer than the copy Margin holds.
    if (saved && (saved.body_md !== ta.value || saved.title !== title.value) && (saved.body_md || saved.title) && (!D.updatedAt || saved.at > D.updatedAt)) {
      var bar = el('div', { class: 'restore', role: 'status' }, [
        el('span', { text: 'There’s a newer copy of this draft in this browser, from ' + new Date(saved.at).toLocaleString() + '.' }),
        el('button', { class: 'btn', type: 'button', text: 'Restore it', on: { click: function () { title.value = saved.title; dek.value = saved.dek; ta.value = saved.body_md; bar.remove(); changed(); } } }),
        el('button', { class: 'btn', type: 'button', text: 'Discard', on: { click: function () { try { localStorage.removeItem(LOCAL); } catch (e) { /* ignore */ } bar.remove(); } } }),
      ]);
      form.parentNode.insertBefore(bar, form);
    }
  } catch (e) { /* ignore */ }

  var submitting = false;
  window.addEventListener('beforeunload', function (e) {
    if (dirty && !submitting) { e.preventDefault(); e.returnValue = ''; }
  });

  // ---------- submit: schedule in local time, confirm the first publish ----------
  var when = document.getElementById('publish_at');
  if (when && when.getAttribute('data-ms')) {
    var d = new Date(Number(when.getAttribute('data-ms')));
    when.value = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  }
  form.addEventListener('submit', function (e) {
    var action = e.submitter && e.submitter.value;
    if (action === 'schedule') {
      if (!when.value) { e.preventDefault(); when.focus(); say('pick a date and time first'); return; }
      // datetime-local has no zone; send an exact instant.
      var hidden = el('input', { type: 'hidden', name: 'publish_at', value: new Date(when.value).toISOString() });
      when.removeAttribute('name');
      form.appendChild(hidden);
    }
    if (action === 'publish' && D.firstPublish) {
      var r = D.reach || { email: 0, fedi: 0 };
      var msg = 'Publish now?\n\nIt goes live on Margin and is sent to ' + r.email + ' email follower' + (r.email === 1 ? '' : 's') + ' and ' + r.fedi + ' fediverse follower' + (r.fedi === 1 ? '' : 's') + '. Emails can’t be unsent.';
      if (!confirm(msg)) { e.preventDefault(); return; }
    }
    submitting = true;
    try { localStorage.removeItem(LOCAL); } catch (err) { /* ignore */ }
  });

  // ---------- images: button, paste, or drop ----------
  var upState = document.getElementById('upload-state');
  function insertAtCursor(text, selectFrom, selectTo) {
    var s = ta.selectionStart, en = ta.selectionEnd, before = ta.value.slice(0, s), after = ta.value.slice(en);
    var pad = (before && !/\n\n$/.test(before) ? (before.endsWith('\n') ? '\n' : '\n\n') : '');
    ta.value = before + pad + text + '\n\n' + after;
    var base = before.length + pad.length;
    ta.focus();
    ta.setSelectionRange(base + selectFrom, base + selectTo);
    changed();
  }
  function upload(file) {
    if (!file || !/^image\/(png|jpeg|gif|webp)$/.test(file.type)) { upState.textContent = 'Use a PNG, JPEG, GIF or WebP image.'; return; }
    if (file.size > 5 * 1024 * 1024) { upState.textContent = 'That image is over 5 MB.'; return; }
    upState.textContent = 'Uploading ' + file.name + '…';
    fetch('/desk/upload', { method: 'POST', headers: { 'Content-Type': file.type }, body: file })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (!r.ok) { upState.textContent = r.error || 'Upload failed.'; return; }
        var alt = 'Describe the image for people who can’t see it';
        insertAtCursor('![' + alt + '](' + r.url + ')', 2, 2 + alt.length);
        upState.textContent = 'Added. Replace the highlighted words with a short description; it becomes the caption too.';
      })
      .catch(function () { upState.textContent = 'Upload failed. Try again.'; });
  }
  var picker = document.getElementById('image-file');
  if (picker) picker.addEventListener('change', function () { upload(picker.files[0]); picker.value = ''; });
  ta.addEventListener('paste', function (e) {
    var f = [].slice.call((e.clipboardData && e.clipboardData.files) || []).find(function (x) { return /^image\//.test(x.type); });
    if (f) { e.preventDefault(); upload(f); }
  });
  ta.addEventListener('dragover', function (e) { if (e.dataTransfer && [].some.call(e.dataTransfer.items || [], function (i) { return i.kind === 'file'; })) { e.preventDefault(); ta.classList.add('drop'); } });
  ta.addEventListener('dragleave', function () { ta.classList.remove('drop'); });
  ta.addEventListener('drop', function (e) {
    ta.classList.remove('drop');
    var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) { e.preventDefault(); upload(f); }
  });

  check();
})();
