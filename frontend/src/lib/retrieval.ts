export interface GroundingRow { ts: string; command: string; ack: boolean }
export interface DriftRow { kind: string; n: number }

export async function fetchRecentGroundings(kind = 'third_person', limit = 5): Promise<GroundingRow[]> {
  const res = await fetch(`/graphsync/queries/recent-groundings?kind=${encodeURIComponent(kind)}&limit=${limit}`);
  if (!res.ok) return [];
  return (await res.json()) as GroundingRow[];
}

export async function fetchSessionDriftMap(sessionId: string): Promise<DriftRow[]> {
  const res = await fetch(`/graphsync/queries/session-drift-map?sessionId=${encodeURIComponent(sessionId)}`);
  if (!res.ok) return [];
  return (await res.json()) as DriftRow[];
}

export async function buildAssemblerBlock(sessionId?: string): Promise<string> {
  try {
    const lines: string[] = [];
    lines.push('[RECENT GROUNDINGS]');
    const g = await fetchRecentGroundings('third_person', 5);
    for (const row of g) {
      lines.push(`- ts: ${row.ts} | command: ${row.command} | ack: ${row.ack}`);
    }
    if (sessionId) {
      lines.push('[CURRENT SESSION DRIFT MAP]');
      const d = await fetchSessionDriftMap(sessionId);
      for (const row of d) {
        lines.push(`- ${row.kind}: ${row.n}`);
      }
    }
    return lines.join('\n');
  } catch {
    return '';
  }
}
