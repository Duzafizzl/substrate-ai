import { saveToLocalFS } from './saveToLocalFS';

export interface BrainGraphNode { id: string; freq?: number; type?: string }
export interface BrainGraphLink { source: string; target: string; value?: number }
export interface BrainGraph { nodes: BrainGraphNode[]; links: BrainGraphLink[] }

export async function buildBrainFromCSV(csvPath: string, pushToNeo4j = false): Promise<BrainGraph> {
  const res = await fetch(csvPath);
  if (!res.ok) throw new Error(`Failed to load CSV: ${res.status} ${res.statusText}`);
  const blob = await res.blob();
  const form = new FormData();
  form.append('file', blob, 'messages.csv');

  const r = await fetch(`/graphsync/upload?push=${pushToNeo4j ? 'true' : 'false'}`, {
    method: 'POST',
    body: form,
  });
  if (!r.ok) throw new Error(`GraphSync error: ${r.status} ${r.statusText}`);
  const graph = (await r.json()) as BrainGraph;
  const ts = new Date().toISOString().replace(/[:]/g, '-');
  await saveToLocalFS(`brain_graph_${ts}.json`, JSON.stringify(graph, null, 2));
  return graph;
}

export async function writeGraphToPublic(graph: BrainGraph): Promise<void> {
  // Persist a canonical copy for the app to load
  await saveToLocalFS('graph_data_full.json', JSON.stringify(graph));
}

export async function syncBrain(csvPath = '/parsed_conversation_filtered.csv', pushToNeo4j = false): Promise<BrainGraph> {
  const graph = await buildBrainFromCSV(csvPath, pushToNeo4j);
  await writeGraphToPublic(graph);
  return graph;
}
