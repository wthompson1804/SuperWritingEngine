'use strict';
// RFC 4180 CSV: quoted fields, doubled quotes, newlines inside quotes.

function parseCsv(text) {
  const rows = [];
  let row = [], field = '', q = false;
  const s = String(text).replace(/^﻿/, '');
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (q) {
      if (c === '"') { if (s[i + 1] === '"') { field += '"'; i++; } else q = false; }
      else field += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && s[i + 1] === '\n') i++;
      row.push(field); rows.push(row); row = []; field = '';
    } else field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  const nonEmpty = rows.filter((r) => r.some((f) => f !== ''));
  if (!nonEmpty.length) return [];
  const head = nonEmpty[0].map((hd) => hd.trim());
  return nonEmpty.slice(1).map((r) => Object.fromEntries(head.map((hd, i) => [hd, r[i] ?? ''])));
}

function cell(v, guard = true) {
  const s = v == null ? '' : String(v);
  // Neutralize spreadsheet formula injection (for files people open in a
  // spreadsheet), then quote. Machine-read exports turn the guard off.
  const safe = guard && /^[=+\-@\t\r]/.test(s) ? `'${s}` : s;
  return /[",\n\r]/.test(safe) || safe !== s ? `"${safe.replace(/"/g, '""')}"` : safe;
}

function toCsv(header, rows, { guard = true } = {}) {
  return [header.join(','), ...rows.map((r) => header.map((k) => cell(r[k], guard)).join(','))].join('\n') + '\n';
}

module.exports = { parseCsv, toCsv };
