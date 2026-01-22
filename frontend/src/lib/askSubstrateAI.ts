import type { Message } from '../types';
// Note: normalizeAssistant is applied in ChatContext, not here

type OllamaRole = 'user' | 'assistant' | 'system';

interface OllamaMessage {
  role: OllamaRole;
  content: string;
}

interface OllamaChatRequest {
  model: string;
  messages: OllamaMessage[];
  stream?: boolean;
  session_id?: string;  // For PostgreSQL persistence!
  options?: Record<string, unknown>;
}

// No longer needed - we use streaming SSE format now
// interface OllamaChatResponse { ... }

export interface AskResult {
  content: string;
  thinking?: string;
  toolCalls?: Array<{
    name: string;
    arguments: Record<string, any>;
    result: any;
  }>;
  reasoningTime?: number;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    cost: number;
  };
  flags?: { watchdog?: boolean };
}

export async function askSubstrateAI(
  messages: Message[],
  sessionId?: string,
  modelOverride?: string,
  _opts?: { disablePresenceSeed?: boolean; disableNormalizer?: boolean; disableCorePrompt?: boolean },
  mediaData?: string,
  mediaType?: string,
  onChunk?: (chunk: string) => void  // 🌊 NEW: Callback for streaming chunks
): Promise<AskResult> {
  const model = modelOverride || import.meta.env.VITE_OLLAMA_MODEL || 'openrouter/polaris-alpha';

  // Filter out fallback/error messages BEFORE sending to backend
  const filteredMessages = messages.filter((m) => {
    const content = m.content.toLowerCase();
    // Skip fallback messages
    if (content.includes('backend connection failed')) return false;
    if (content.includes('encountered an error')) return false;
    if (content.includes('i apologize')) return false;
    return true;
  });

  // SIMPLIFIED: Let the backend handle system prompt, memory, etc!
  // Just send user/assistant messages
  const mapped: OllamaMessage[] = filteredMessages.map((m) => ({
    role: (m.role === 'assistant' ? 'assistant' : 'user') as OllamaRole,
    content: m.content,
  }));

  const payload: OllamaChatRequest = {
    model,
    messages: mapped,
    stream: true,  // 🌊 STREAMING ENABLED with fixed tool schemas!
    // Session ID for message persistence
    session_id: sessionId || 'default',
    // Multi-modal support!
    ...(mediaData && mediaType ? { media_data: mediaData, media_type: mediaType } : {})
  };

  try {
    // Substrate AI Backend (with OpenRouter!)
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8284';
    
    // #region agent log
    fetch('http://127.0.0.1:7244/ingest/97890b67-d5b0-4b89-8eef-ef19b4152480',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'askSubstrateAI.ts:95',message:'Starting streaming request',data:{stream:payload.stream,model:payload.model,messageCount:payload.messages.length},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H5'})}).catch(()=>{});
    // #endregion
    
    const res = await fetch(`${API_URL}/ollama/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    // #region agent log
    fetch('http://127.0.0.1:7244/ingest/97890b67-d5b0-4b89-8eef-ef19b4152480',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'askSubstrateAI.ts:104',message:'Response received',data:{ok:res.ok,status:res.status,hasBody:!!res.body,contentType:res.headers.get('content-type')},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H3'})}).catch(()=>{});
    // #endregion

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`Ollama API error: ${res.status} ${res.statusText} ${text}`);
    }

    // 🌊 STREAMING RESPONSE HANDLING
    const reader = res.body?.getReader();
    const decoder = new TextDecoder();
    
    // #region agent log
    fetch('http://127.0.0.1:7244/ingest/97890b67-d5b0-4b89-8eef-ef19b4152480',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'askSubstrateAI.ts:119',message:'Stream reader initialized',data:{hasReader:!!reader},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H3'})}).catch(()=>{});
    // #endregion
    
    let fullContent = '';
    let thinking = '';
    let toolCalls: any[] = [];
    let reasoningTime: number | undefined;
    let usage: any;
    
    if (reader) {
      console.log('🌊 Starting stream...');
      let chunkCount = 0;
      let totalBytes = 0;
      
      while (true) {
        const { done, value } = await reader.read();
        
        // #region agent log
        fetch('http://127.0.0.1:7244/ingest/97890b67-d5b0-4b89-8eef-ef19b4152480',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'askSubstrateAI.ts:135',message:'Stream chunk received',data:{done:done,hasValue:!!value,valueLength:value?.length,chunkNumber:chunkCount},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H2'})}).catch(()=>{});
        // #endregion
        
        if (done) {
          console.log('🌊 Stream complete!');
          // #region agent log
          fetch('http://127.0.0.1:7244/ingest/97890b67-d5b0-4b89-8eef-ef19b4152480',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'askSubstrateAI.ts:143',message:'Stream ended',data:{totalChunks:chunkCount,totalBytes:totalBytes,fullContentLength:fullContent.length},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H4'})}).catch(()=>{});
          // #endregion
          break;
        }
        
        chunkCount++;
        totalBytes += value?.length || 0;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n').filter(line => line.trim() !== '');
        
        // #region agent log
        fetch('http://127.0.0.1:7244/ingest/97890b67-d5b0-4b89-8eef-ef19b4152480',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'askSubstrateAI.ts:156',message:'Decoded chunk',data:{chunkLength:chunk.length,lineCount:lines.length,firstLine:lines[0]?.substring(0,100)},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1'})}).catch(()=>{});
        // #endregion
        
        for (const line of lines) {
          // Skip SSE comments
          if (line.startsWith(':')) continue;
          
          // Parse SSE data: format
          let jsonStr = line;
          if (line.startsWith('data: ')) {
            jsonStr = line.substring(6);
          }
          
          try {
            const data = JSON.parse(jsonStr);
            
            // #region agent log
            fetch('http://127.0.0.1:7244/ingest/97890b67-d5b0-4b89-8eef-ef19b4152480',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'askSubstrateAI.ts:176',message:'Parsed stream event',data:{type:data.type,hasChunk:!!data.chunk,chunkLength:data.chunk?.length,hasDone:!!data.result},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1'})}).catch(()=>{});
            // #endregion
            
            // Handle different event types
            if (data.type === 'content' && data.chunk) {
              fullContent += data.chunk;
              // 🌊 Call onChunk callback for live updates
              if (onChunk) {
                onChunk(data.chunk);
              }
            } else if (data.type === 'thinking' && data.content) {
              thinking = data.content;
            } else if (data.type === 'tool_call' && data.data) {
              toolCalls.push(data.data);
            } else if (data.type === 'error' && data.error) {
              // 🔥 Handle error responses - show the error message
              fullContent = data.error;
            } else if (data.type === 'done') {
              // Final metadata - check both 'result' and 'response' (error case)
              if (data.result) {
                thinking = data.result.thinking || thinking;
                toolCalls = data.result.tool_calls || toolCalls;
                reasoningTime = data.result.reasoning_time;
                usage = data.result.usage;
              } else if (data.response) {
                // Error case: backend sends 'response' instead of 'result'
                fullContent = fullContent || data.response;
              }
            }
          } catch (e) {
            // Ignore parse errors (incomplete chunks)
            console.debug('Stream parse warning:', e);
            // #region agent log
            fetch('http://127.0.0.1:7244/ingest/97890b67-d5b0-4b89-8eef-ef19b4152480',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'askSubstrateAI.ts:202',message:'Parse error',data:{error:String(e),line:line.substring(0,200)},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1'})}).catch(()=>{});
            // #endregion
          }
        }
      }
    }
    
    // Debug: Log structured data
    const debugInfo = {
      has_thinking: !!thinking,
      thinking_length: thinking?.length || 0,
      tool_calls_count: toolCalls?.length || 0,
      content_length: fullContent.length,
      thinking_preview: thinking ? thinking.substring(0, 150) + '...' : 'NONE',
      content_preview: fullContent.substring(0, 100) + '...'
    };
    console.log('🧠 Backend Response (Streamed):', debugInfo);
    
    // #region agent log
    fetch('http://127.0.0.1:7244/ingest/97890b67-d5b0-4b89-8eef-ef19b4152480',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'askSubstrateAI.ts:221',message:'Final result prepared',data:{contentLength:fullContent.length,hasThinking:!!thinking,toolCallsCount:toolCalls.length,hasUsage:!!usage},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H4'})}).catch(()=>{});
    // #endregion
    
    // Return structured data
    return { 
      content: fullContent || 'No response generated',
      thinking: thinking,
      toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
      reasoningTime: reasoningTime,
      usage: usage
    };
  } catch (e) {
    // #region agent log
    fetch('http://127.0.0.1:7244/ingest/97890b67-d5b0-4b89-8eef-ef19b4152480',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'askSubstrateAI.ts:130',message:'Backend error caught',data:{error:String(e)},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'D'})}).catch(()=>{});
    // #endregion
    console.error('Backend error:', e);
    return { content: 'Sorry, backend connection failed. Please check the server.' };
  }
}


