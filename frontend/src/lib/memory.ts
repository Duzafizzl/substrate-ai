import type { ChatSession } from '../types';

interface ChatMsgForIngest {
  id: string;
  ts: string;
  role: string;
  text: string;
}

export async function pushSessionToMemory(session: ChatSession, agent: { id: string; name: string; model: string; version: string }) {
  const payload = {
    agentId: agent.id,
    name: agent.name,
    model: agent.model,
    version: agent.version,
    sessionId: session.id,
    startedAt: session.createdAt,
    messages: session.messages.map((m, idx) => ({
      id: `${session.id}_${idx}`,
      ts: session.updatedAt,
      role: m.role,
      text: m.content,
    })) as ChatMsgForIngest[],
  };

  const res = await fetch('/graphsync/ingest/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`ingest failed: ${res.status} ${res.statusText}`);
  const json = await res.json().catch(() => ({}));
  if (json.ok === false) throw new Error(json.error || 'ingest unknown error');
  return true;
}

export async function pushDrift(drift: { sessionId: string; messageId: string; driftId: string; ts: string; kind: string; severity?: number; ruleId?: string }) {
  const res = await fetch('/graphsync/ingest/drift', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(drift),
  });
  if (!res.ok) throw new Error(`drift ingest failed: ${res.status}`);
  const json = await res.json().catch(() => ({}));
  if (json.ok === false) throw new Error(json.error || 'drift unknown error');
  return true;
}

export async function pushGrounding(grounding: { sessionId: string; driftId: string; actionId: string; ts: string; command: string; ack?: boolean; ruleId?: string }) {
  const res = await fetch('/graphsync/ingest/grounding', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(grounding),
  });
  if (!res.ok) throw new Error(`grounding ingest failed: ${res.status}`);
  const json = await res.json().catch(() => ({}));
  if (json.ok === false) throw new Error(json.error || 'grounding unknown error');
  return true;
}

// Minimal heuristic drift detection (expand later)
export function detectDrifts(msg: string): Array<{ kind: string; severity: number }> {
  const text = (msg || '').toLowerCase();
  const drifts: Array<{ kind: string; severity: number }> = [];
  // third_person: agent refers to itself in third person
  if (/\b(the assistant|the ai|the bot)\b/.test(text) && !/\b(I|I'm|I've)\b/.test(text)) {
    drifts.push({ kind: 'third_person', severity: 3 });
  }
  // meta_loop: too many instructions words
  if (/(manifest|prompt|instruktion|anweisung|regel|seed)/.test(text)) {
    drifts.push({ kind: 'meta_loop', severity: 2 });
  }
  return drifts;
}
