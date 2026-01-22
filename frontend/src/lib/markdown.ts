// Enhanced markdown-to-HTML with Discord-style formatting
// Supports: **bold**, *italic*, `code`, and -# subtext (Discord style)

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function toHtmlLite(md: string): string {
  if (!md) return '';
  
  // First: Convert escaped newlines to real newlines (backend sometimes sends \\n as string)
  let text = md.replace(/\\n/g, '\n');
  
  // Extract code blocks BEFORE any processing
  const codeBlocks: Map<string, string> = new Map();
  let blockIndex = 0;
  
  text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, (_match, lang, code) => {
    const trimmedCode = code.trim();
    const escapedCode = trimmedCode
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    
    const language = lang || 'code';
    
    const codeBlockHtml = `<div class="code-block my-3 rounded-lg bg-gray-900/80 border border-gray-700/50 overflow-hidden w-full max-w-full">
      <div class="px-3 py-1.5 bg-gray-800/50 border-b border-gray-700/50 flex items-center justify-between min-w-0">
        <span class="text-xs text-purple-300/60 truncate">${language}</span>
        <button class="copy-code-btn text-gray-400 hover:text-white transition-colors text-xs px-2 py-0.5 rounded hover:bg-gray-700/50 flex-shrink-0" title="Copy code">
          Copy
        </button>
      </div>
      <pre class="px-3 py-2 overflow-x-auto max-w-full"><code class="text-sm font-mono text-gray-200">${escapedCode}</code></pre>
    </div>`;
    
    // Use a placeholder that survives escapeHtml (no special chars!)
    const placeholder = `XOXOCODEBLOCKXOXO${blockIndex}XOXO`;
    codeBlocks.set(placeholder, codeBlockHtml);
    blockIndex++;
    return placeholder;
  });

  // Now escape HTML for the rest of the content
  let html = escapeHtml(text);

  // Discord Subtext: -# text (on its own line) → smaller text with dynamic color based on bubble type
  html = html.replace(/(^|\n)-#\s+(.+?)(\n|$)/g, (_match, before, content, after) => {
    return `${before}<span class="markdown-subtext block text-sm mt-1 italic">${content}</span>${after}`;
  });

  // Inline code: `code` → monospace with background
  html = html.replace(/`([^`]+?)`/g, '<code class="px-1.5 py-0.5 bg-black/30 rounded text-sm font-mono">$1</code>');

  // Bold: **text** or __text__ (non-greedy)
  html = html.replace(/(\*\*|__)(.+?)\1/g, '<strong class="font-bold">$2</strong>');

  // Italic: *text* or _text_ (avoid spaces just inside markers)
  html = html.replace(/(^|[^*_])(\*|_)(?!\s)(.+?)(?<!\s)\2(?![\w*_])/g, (_m, pre, _m1, inner) => {
    return `${pre}<em class="italic">${inner}</em>`;
  });

  // Restore code blocks from placeholders
  codeBlocks.forEach((block, placeholder) => {
    html = html.replace(placeholder, block);
  });

  return html;
}


