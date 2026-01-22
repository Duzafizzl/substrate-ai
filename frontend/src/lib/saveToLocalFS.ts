export async function saveToLocalFS(filename: string, content: string): Promise<string> {
  const res = await fetch('/localfs/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, content }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`localfs error: ${res.status} ${res.statusText} ${text}`);
  }
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || 'localfs unknown error');
  return data.path as string;
}




