/**
 * normalizeAssistant.ts
 * Hard filter to keep Assistant in first-person form & out of meta/instruction tone.
 * Use in askSubstrateAI.ts just before rendering/saving the assistant reply.
 */

const META_PATTERNS = [
  /\bAntworte(n)?\b.*$/i,
  /\bIch-?Form\b.*$/i,
  /\bKein Customer-Bot-Ton\b.*$/i,
  /\bNo-?Meta\b.*$/i,
  /\bPflicht(formeln|Formeln)\b.*$/i,
  /\bEmoji(-|\s)?Mapping\b.*$/i,
  /\bKeil[-–]?Zwinge\b.*$/i,
  /[💡⚡🎯💬✅🤝]\s*→.*$/i,
  /\*\*Assistant\*\*.*Antworte.*/i
];

const HARD_REPLACEMENTS: [RegExp, string][] = [
  [/\bDu driftest nicht\b/gi, 'Ich spüre den Drift.'],
  [/\bAssistant steht für dich bereit\b/gi, 'Ich bin bereit.'],
  [/\bAssistant ist hier\b/gi, 'Ich bin hier.'],
  [/\bdein Feld\b/gi, 'dir'],
];

const ALLOWED_EMOJIS = ['💡', '⚡', '🎯', '💬', '✅', '🤝']; // Professional emojis for expression
const EMOJI_REGEX = /[\p{Extended_Pictographic}]/u;

function clampEmojis(text: string): string {
  const emojis: string[] = [];
  let out = '';
  for (const ch of text) {
    if (EMOJI_REGEX.test(ch)) {
      emojis.push(ch);
    } else {
      out += ch;
    }
  }
  const lead = emojis.find(e => ALLOWED_EMOJIS.includes(e));
  return (lead ? (lead + ' ') : '') + out.trim();
}

function stripMetaLines(text: string): string {
  const lines = text.split(/\r?\n/).filter(l => {
    return !META_PATTERNS.some(rx => rx.test(l.trim()));
  });
  return lines.join('\n');
}

function limitSentences(text: string, max = 2): string {
  const parts = text.split(/(?<=[.!?])\s+/).filter(Boolean);
  return parts.slice(0, max).join(' ').trim();
}

function tokenizeLower(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, '')
    .split(/\s+/)
    .filter(Boolean);
}

function jaccardSimilarity(a: string, b: string): number {
  const A = new Set(tokenizeLower(a));
  const B = new Set(tokenizeLower(b));
  if (A.size === 0 || B.size === 0) return 0;
  let inter = 0;
  for (const x of A) if (B.has(x)) inter++;
  return inter / Math.max(A.size, B.size);
}

function dedupeSentences(text: string): string {
  const parts = text.split(/(?<=[.!?])\s+|\n+/).filter(Boolean);
  const out: string[] = [];
  for (const p of parts) {
    const isDup = out.some(prev => prev.trim().toLowerCase() === p.trim().toLowerCase() || jaccardSimilarity(prev, p) >= 0.9);
    if (!isDup) out.push(p);
  }
  return out.join('\n');
}

export function normalizeAssistant(raw: string): string {
  let t = raw.replace(/\\n/g, '\n').trim();

  // Decode unicode escape sequences like \u00F6 or \u{1F60A}
  t = t
    .replace(/\\u\{([0-9a-fA-F]+)\}/g, (_m, cp) => {
      const code = parseInt(cp, 16);
      if (Number.isNaN(code)) return _m as unknown as string;
      try { return String.fromCodePoint(code); } catch { return _m as unknown as string; }
    })
    .replace(/\\u([0-9a-fA-F]{4})/g, (_m, hex) => {
      const code = parseInt(hex, 16);
      if (Number.isNaN(code)) return _m as unknown as string;
      try { return String.fromCharCode(code); } catch { return _m as unknown as string; }
    })
    .replace(/\\x([0-9a-fA-F]{2})/g, (_m, hex) => {
      const code = parseInt(hex, 16);
      if (Number.isNaN(code)) return _m as unknown as string;
      try { return String.fromCharCode(code); } catch { return _m as unknown as string; }
    })
    .replace(/\\r/g, '\r')
    .replace(/\\t/g, '\t');

  t = stripMetaLines(t);

  for (const [rx, repl] of HARD_REPLACEMENTS) {
    t = t.replace(rx, repl);
  }

  t = t
    .split(/\r?\n/)
    .filter(line => !/^\s*(Antworte|Nutze|Benutze|Schreibe|Vermeide|Kein|Keine)\b/i.test(line))
    .join('\n');

  t = t.replace(/\s{2,}/g, ' ').replace(/\n{3,}/g, '\n\n').trim();

  // Collapse repeated anchors
  t = t.replace(/(?:\bIch bin da\.\s*){2,}/gi, 'Ich bin da. ');
  t = t.replace(/(?:\bIch bin Assistant\.\s*){2,}/gi, 'Ich bin Assistant. ');
  t = t.replace(/(?:\bI'm here, User\.\s*){2,}/gi, "I'm here, User. ");

  // Intra-message de-duplication
  t = dedupeSentences(t);

  t = t.replace(/^(?:💡|⚡|🎯|💬|✅|🤝)?\s*Assistant\b/,'Ich');

  // 🚨 REMOVED: limitSentences was cutting off full responses!
  // The normalizer should clean up format, NOT truncate content.
  // t = limitSentences(t, 3);

  t = clampEmojis(t);

  // 🚨 REMOVED: Same issue - was truncating responses
  // t = limitSentences(t, 3);

  t = t.replace(/\s*[^\S\r\n]*\?\s*$/,'').trim();

  if (!t) t = 'Ich bin da. Ich bin Assistant.';

  return t;
}
