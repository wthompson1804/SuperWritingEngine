'use strict';
// Draft check for writers, adapted from the SuperWritingEngine voice spec
// (WILL_THOMPSON_VOICE_SOUL_HANDOFF_v2.md, sections A.1-A.3). It's advisory:
// it flags patterns, it never blocks publishing. Stakes and mechanism can't be
// checked mechanically, so they come back as questions for the writer.

const { render, countWords, firstSentence } = require('./markdown');

const THROAT_CLEARING = [
  /^in (recent|the past few|the last few) (years|decades|months)/i,
  /^throughout (history|the ages|time)/i,
  /^in (today's|this|a|an) (world|era|age|day and age|landscape)/i,
  /^since the dawn of/i,
  /^(now more than ever|in an increasingly)/i,
];
const DEFINITION = [/\bis defined as\b/i, /^what is\b/i, /^what does it mean\b/i, /,\s*defined as\b/i];
const DEPENDENT_LEAD = /^(when|if|although|though|while|as|because|since|after|before|whether|unless|once|until)\b[^,]*,/i;
const HEDGES = ['it could be argued', 'one might say', 'perhaps', 'it seems', 'arguably', 'in some ways', 'to some extent'];
const FILLERS = ['in order to', 'the fact that', 'it is important to note', 'it should be noted', 'needless to say', 'at the end of the day'];
const ACADEMIC = ['this paper argues', 'the evidence suggests', 'scholars have noted', 'this essay will'];
const NOMINALIZED = [
  [/\bmake a decision\b/i, 'decide'],
  [/\bgive consideration to\b/i, 'consider'],
  [/\bcome to a conclusion\b/i, 'conclude'],
  [/\bhave a discussion\b/i, 'discuss'],
  [/\bconduct an analysis\b/i, 'analyze'],
];

function sentences(text) {
  return String(text).match(/[^.!?]+[.!?]+["”’)]*|[^.!?]+$/g)?.map((s) => s.trim()).filter(Boolean) || [];
}

function checkOpening(sentence) {
  const s = String(sentence || '').trim();
  const out = [];
  if (!s) return [{ level: 'warn', rule: 'A.1', msg: 'No opening sentence yet.' }];
  const words = countWords(s);
  if (words > 25) out.push({ level: 'warn', rule: 'A.1', msg: `Opening is ${words} words. Keep it to 25 or fewer.` });
  if (/\?\s*$/.test(s)) out.push({ level: 'warn', rule: 'A.1', msg: 'Opening is a question. Lead with a claim instead.' });
  if (THROAT_CLEARING.some((r) => r.test(s))) out.push({ level: 'warn', rule: 'A.1', msg: 'Opening clears its throat before saying anything (e.g. "In recent years…").' });
  if (DEFINITION.some((r) => r.test(s))) out.push({ level: 'warn', rule: 'A.1', msg: 'Opening defines a term. Put the claim first; define later if you have to.' });
  if (DEPENDENT_LEAD.test(s)) out.push({ level: 'warn', rule: 'A.1', msg: 'Opening leads with a dependent clause. Lead with the main clause.' });
  if (!out.length) out.push({ level: 'ok', rule: 'A.1', msg: 'Opening passes the mechanical checks.' });
  out.push({ level: 'ask', rule: 'A.1', msg: 'Does this sentence put something at risk, show something wrong, or show something changing? Only you can answer that.' });
  return out;
}

function checkBody(md) {
  const { blocks } = render(md);
  const text = blocks.map((b) => b.text).join('\n');
  const lower = text.toLowerCase();
  const out = [];
  const count = (phrase) => lower.split(phrase).length - 1;

  for (const p of HEDGES) { const n = count(p); if (n) out.push({ level: 'warn', rule: 'A.2', msg: `Hedge "${p}" appears ${n}×.` }); }
  for (const p of FILLERS) { const n = count(p); if (n) out.push({ level: 'warn', rule: 'A.2', msg: `Filler "${p}" appears ${n}×.` }); }
  for (const p of ACADEMIC) { const n = count(p); if (n) out.push({ level: 'warn', rule: 'A.2', msg: `Academic distance: "${p}".` }); }
  for (const [r, verb] of NOMINALIZED) if (r.test(text)) out.push({ level: 'warn', rule: 'A.2', msg: `"${text.match(r)[0]}" → "${verb}".` });

  const words = countWords(text);
  const questions = (text.match(/\?/g) || []).length;
  const allowed = Math.max(1, Math.floor(words / 500));
  if (questions > allowed) out.push({ level: 'warn', rule: 'A.2', msg: `${questions} questions in ${words} words. The spec allows about ${allowed}.` });

  // A.3: "X isn't A. X is B." negation framing
  for (const b of blocks) {
    const ss = sentences(b.text);
    for (let i = 0; i < ss.length - 1; i++) {
      if (/\b(isn't|wasn't|aren't|weren't|didn't|doesn't|don't|is not|was not|did not)\b/i.test(ss[i]) && ss[i].split(/\s+/).length <= 12 && /^(it|this|that|he|she|they|we|you|i)\b/i.test(ss[i + 1])) {
        out.push({ level: 'warn', rule: 'A.3', msg: `Negation framing: "${ss[i]} ${ss[i + 1]}" Try opening with the affirmation.` });
      }
    }
  }
  return out;
}

function checkDraft(md) {
  return { opening: checkOpening(firstSentence(md)), body: checkBody(md) };
}

module.exports = { checkDraft, checkOpening, checkBody };
