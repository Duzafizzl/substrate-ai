/**
 * Token Counter Component
 * 
 * Shows context window usage:
 * "21.77k of 131.07k tokens (83% left)"
 * 
 * With color-coded progress bar:
 * - Green: < 60%
 * - Yellow: 60-80%
 * - Red: > 80% (needs summarization!)
 */

import { useEffect, useState } from 'react';

interface TokenUsage {
  system_tokens: number;
  memory_blocks_tokens: number;
  tool_schemas_tokens: number;
  conversation_tokens: number;
  total_tokens: number;
  max_tokens: number;
  percentage_used: number;
  tokens_remaining: number;
  needs_summarization: boolean;
}

interface TokenCounterProps {
  sessionId?: string;
  className?: string;
}

export function TokenCounter({ sessionId = 'default', className = '' }: TokenCounterProps) {
  const [usage, setUsage] = useState<TokenUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch token usage from backend
  useEffect(() => {
    const fetchUsage = async () => {
      try {
        const res = await fetch(`http://localhost:8284/api/context/usage?session_id=${sessionId}`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        setUsage(data);
        setError(null);
      } catch (err) {
        console.error('Token counter error:', err);
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    };

    fetchUsage();
    
    // Refresh every 30 seconds (reduced from 10s!)
    const interval = setInterval(fetchUsage, 30000);
    
    // 🔥 Listen for summary complete events!
    const handleSummaryComplete = async () => {
      console.log('📡 TOKEN COUNTER: Received summary-completed event!');
      console.log('🔄 TOKEN COUNTER: Fetching new usage data...');
      await fetchUsage();
      console.log('✅ TOKEN COUNTER: Refresh complete!');
      // Acknowledge refresh complete
      window.dispatchEvent(new Event('token-counter-refreshed'));
    };
    
    // 🔥 Listen for model update events!
    const handleModelUpdated = async (event: Event) => {
      const customEvent = event as CustomEvent;
      console.log('📡 TOKEN COUNTER: Received agentModelUpdated event!', customEvent.detail);
      console.log('🔄 TOKEN COUNTER: Model changed, fetching new usage data...');
      await fetchUsage();
      console.log('✅ TOKEN COUNTER: Refresh complete after model change!');
    };
    
    console.log('🎧 TOKEN COUNTER: Listening for summary-completed and agentModelUpdated events...');
    window.addEventListener('summary-completed', handleSummaryComplete);
    window.addEventListener('agentModelUpdated', handleModelUpdated);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('summary-completed', handleSummaryComplete);
      window.removeEventListener('agentModelUpdated', handleModelUpdated);
    };
  }, [sessionId]);

  if (loading) {
    return (
      <div className={`flex items-center gap-2 text-xs text-gray-500 ${className}`}>
        <div className="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
        <span>Loading tokens...</span>
      </div>
    );
  }

  if (error || !usage) {
    return (
      <div className={`flex items-center gap-2 text-xs text-red-500 ${className}`}>
        <span>⚠️ Token counter offline</span>
      </div>
    );
  }

  // Format numbers like "21.77k"
  const formatCount = (count: number): string => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(2)}k`;
    }
    return count.toString();
  };

  const used = formatCount(usage.total_tokens);
  const total = formatCount(usage.max_tokens);
  const percentLeft = Math.round(100 - usage.percentage_used);

  // Color based on usage
  const getColor = () => {
    if (usage.percentage_used >= 80) return 'text-red-500';
    if (usage.percentage_used >= 60) return 'text-yellow-500';
    return 'text-green-500';
  };


  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {/* Text Display */}
      <div className={`flex items-center gap-2 text-xs ${getColor()}`}>
        <span className="font-mono">
          {used} of {total} tokens ({percentLeft}% left)
        </span>
        {usage.needs_summarization && (
          <span className="text-red-500 font-semibold animate-pulse">⚠️ NEEDS SUMMARY</span>
        )}
      </div>

      {/* Stacked Progress Bar with Colors! */}
      <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden flex">
        {/* System - Blue */}
        <div
          className="h-full bg-blue-500 transition-all duration-500"
          style={{ width: `${(usage.system_tokens / usage.max_tokens) * 100}%` }}
          title={`System: ${usage.system_tokens.toLocaleString()} tokens`}
        />
        
        {/* Memory - Purple */}
        <div
          className="h-full bg-purple-500 transition-all duration-500"
          style={{ width: `${(usage.memory_blocks_tokens / usage.max_tokens) * 100}%` }}
          title={`Memory: ${usage.memory_blocks_tokens.toLocaleString()} tokens`}
        />
        
        {/* Tools - Cyan */}
        <div
          className="h-full bg-cyan-500 transition-all duration-500"
          style={{ width: `${(usage.tool_schemas_tokens / usage.max_tokens) * 100}%` }}
          title={`Tools: ${usage.tool_schemas_tokens.toLocaleString()} tokens`}
        />
        
        {/* Chat - Green/Yellow/Red based on PERCENTAGE (not absolute tokens!) */}
        <div
          className={`h-full transition-all duration-500 ${
            usage.percentage_used >= 80 ? 'bg-red-500' :
            usage.percentage_used >= 60 ? 'bg-yellow-500' :
            'bg-green-500'
          }`}
          style={{ width: `${(usage.conversation_tokens / usage.max_tokens) * 100}%` }}
          title={`Chat: ${usage.conversation_tokens.toLocaleString()} tokens`}
        />
      </div>

      {/* Breakdown with COLORS! */}
      <details className="text-[0.65rem] cursor-pointer group">
        <summary className="text-gray-500 hover:text-gray-300 transition-colors">
          Breakdown
        </summary>
        <div className="mt-2 space-y-1 pl-2 font-mono">
          {/* System - Blue */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-blue-500"></div>
              <span className="text-gray-400">System</span>
            </div>
            <span className="text-blue-400 font-semibold">
              {usage.system_tokens.toLocaleString()}
            </span>
          </div>
          
          {/* Memory - Purple */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-purple-500"></div>
              <span className="text-gray-400">Memory</span>
            </div>
            <span className="text-purple-400 font-semibold">
              {usage.memory_blocks_tokens.toLocaleString()}
            </span>
          </div>
          
          {/* Tools - Cyan */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-cyan-500"></div>
              <span className="text-gray-400">Tools</span>
            </div>
            <span className="text-cyan-400 font-semibold">
              {usage.tool_schemas_tokens.toLocaleString()}
            </span>
          </div>
          
          {/* Chat - Green/Yellow/Red based on PERCENTAGE */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${
                usage.percentage_used >= 80 ? 'bg-red-500' :
                usage.percentage_used >= 60 ? 'bg-yellow-500' :
                'bg-green-500'
              }`}></div>
              <span className="text-gray-400">Chat</span>
            </div>
            <span className={`font-semibold ${
              usage.percentage_used >= 80 ? 'text-red-400' :
              usage.percentage_used >= 60 ? 'text-yellow-400' :
              'text-green-400'
            }`}>
              {usage.conversation_tokens.toLocaleString()}
            </span>
          </div>
        </div>
      </details>
    </div>
  );
}

