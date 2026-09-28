'use strict';
// Sends the mail queued in the `mail` table over SMTP (STARTTLS or implicit
// TLS) with no dependencies. Nothing is sent unless MARGIN_SMTP_URL is set,
// e.g. smtp://user:pass@smtp.example.com:587 or smtps://user:pass@host:465.
// Each row is tried up to 5 times with backoff, then marked failed. Rows are
// claimed one at a time, so a crash mid-send loses at most one retry.

const net = require('node:net');
const tls = require('node:tls');
const crypto = require('node:crypto');

const MAX_ATTEMPTS = 5;

function parseSmtpUrl(url) {
  const u = new URL(url);
  if (!/^smtps?:$/.test(u.protocol)) throw new Error('MARGIN_SMTP_URL must start with smtp:// or smtps://');
  return {
    host: u.hostname, port: Number(u.port) || (u.protocol === 'smtps:' ? 465 : 587),
    secure: u.protocol === 'smtps:', user: decodeURIComponent(u.username), pass: decodeURIComponent(u.password),
    starttls: u.searchParams.get('starttls') !== '0',
  };
}

// A tiny SMTP client: enough for AUTH PLAIN/LOGIN over TLS and one message.
function smtpSend(cfg, { from, to, subject, text, messageId }) {
  return new Promise((resolve, reject) => {
    let sock = cfg.secure ? tls.connect({ host: cfg.host, port: cfg.port, servername: cfg.host }) : net.connect({ host: cfg.host, port: cfg.port });
    let buf = '';
    let step = 0;
    const timer = setTimeout(() => fail(new Error('SMTP timeout')), 30000);
    const fail = (e) => { clearTimeout(timer); try { sock.destroy(); } catch { /* ignore */ } reject(e); };
    const write = (line) => sock.write(line + '\r\n');
    const body = [
      `From: ${from}`, `To: ${to}`, `Subject: ${encodeHeader(subject)}`, `Date: ${new Date().toUTCString()}`,
      `Message-ID: <${messageId}>`, 'MIME-Version: 1.0', 'Content-Type: text/plain; charset=utf-8', 'Content-Transfer-Encoding: 8bit',
      'Auto-Submitted: auto-generated', '', text.replace(/\r?\n/g, '\r\n').replace(/^\./gm, '..'),
    ].join('\r\n');
    const steps = [
      () => write(`EHLO ${cfg.ehlo || 'margin'}`),
      () => { if (!cfg.secure && cfg.starttls && /STARTTLS/i.test(buf)) { write('STARTTLS'); return 'starttls'; } return 'auth'; },
      () => { write('AUTH PLAIN ' + Buffer.from(`\0${cfg.user}\0${cfg.pass}`).toString('base64')); },
      () => write(`MAIL FROM:<${addr(from)}>`),
      () => write(`RCPT TO:<${addr(to)}>`),
      () => write('DATA'),
      () => write(body + '\r\n.'),
      () => write('QUIT'),
    ];
    const attach = () => {
      sock.setEncoding('utf8');
      sock.on('data', onData);
      sock.on('error', fail);
    };
    const onData = (chunk) => {
      buf += chunk;
      // Wait for a complete final line (code followed by a space).
      if (!/^\d{3} [^\n]*\n$/m.test(buf) || !/\n$/.test(buf)) return;
      const code = Number(buf.match(/^(\d{3}) /m)[1]);
      const reply = buf; buf = '';
      if (code >= 400) return fail(new Error(`SMTP ${code}: ${reply.trim().slice(0, 200)}`));
      if (step === 1 && !cfg.user) { step = 3; steps[step](); step++; return; }
      const r = steps[step] ? steps[step]() : null;
      if (r === 'starttls') {
        // Upgrade in place, then start over from EHLO on the secure socket.
        sock.removeAllListeners('data');
        sock = tls.connect({ socket: sock, servername: cfg.host }, () => { buf = ''; step = 1; attach(); write(`EHLO ${cfg.ehlo || 'margin'}`); });
        sock.on('error', fail);
        return;
      }
      if (r === 'auth') { step = cfg.user ? 2 : 3; steps[step](); step++; return; }
      step++;
      if (step > steps.length) { clearTimeout(timer); sock.end(); resolve(); }
    };
    sock.on('connect', () => { if (!cfg.secure) attach(); });
    sock.on('secureConnect', () => { if (cfg.secure) attach(); });
    sock.on('error', fail);
    sock.on('close', () => { clearTimeout(timer); if (step < steps.length) reject(new Error('SMTP connection closed early')); else resolve(); });
  });
}

const addr = (s) => (String(s).match(/<([^>]+)>/) || [null, s.trim()])[1];
const encodeHeader = (s) => (/^[\x20-\x7e]*$/.test(s) ? s : `=?UTF-8?B?${Buffer.from(s).toString('base64')}?=`);

function createMailer(h, { smtpUrl = process.env.MARGIN_SMTP_URL || '', from = process.env.MARGIN_MAIL_FROM || '', domain = 'margin', log = () => {}, send = null } = {}) {
  const cfg = smtpUrl ? parseSmtpUrl(smtpUrl) : null;
  const enabled = !!(cfg || send);
  if (cfg && !from) throw new Error('MARGIN_MAIL_FROM is required when MARGIN_SMTP_URL is set');
  const deliver = send || ((msg) => smtpSend(cfg, msg));
  let draining = false;

  async function drain() {
    if (!enabled || draining) return 0;
    draining = true;
    let sent = 0;
    try {
      for (;;) {
        const row = h.get(`SELECT * FROM mail WHERE status = 'pending' AND next_at <= ? ORDER BY id LIMIT 1`, Date.now());
        if (!row) break;
        // Claim it before sending, so two workers never send the same mail.
        const claimed = h.run(`UPDATE mail SET status = 'sending' WHERE id = ? AND status = 'pending'`, row.id).changes;
        if (!claimed) continue;
        try {
          await deliver({ from, to: row.to_email, subject: row.subject, text: row.body, messageId: `${row.id}.${crypto.randomBytes(6).toString('hex')}@${domain}` });
          h.run(`UPDATE mail SET status = 'sent', sent_at = ?, attempts = attempts + 1 WHERE id = ?`, Date.now(), row.id);
          sent++;
        } catch (e) {
          const attempts = row.attempts + 1;
          h.run(`UPDATE mail SET status = ?, attempts = ?, next_at = ?, last_error = ? WHERE id = ?`,
            attempts >= MAX_ATTEMPTS ? 'failed' : 'pending', attempts, Date.now() + 60000 * 2 ** attempts, String(e.message).slice(0, 200), row.id);
          log(`mail to ${row.to_email} failed (${attempts}/${MAX_ATTEMPTS}): ${e.message}`);
          if (attempts < MAX_ATTEMPTS) break; // don't hammer a struggling server
        }
      }
    } finally { draining = false; }
    return sent;
  }
  return { enabled, drain };
}

module.exports = { createMailer, parseSmtpUrl, smtpSend };
