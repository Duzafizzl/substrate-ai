import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Volume2, MessageSquare } from 'lucide-react';
import { speak } from '../lib/voice';
import { Message } from '../types';
import { toHtmlLite } from '../lib/markdown';
import ReasoningBlock from './ReasoningBlock';
import ToolCallBlock from './ToolCallBlock';
import MessageContextMenu from './MessageContextMenu';

interface ChatBubbleProps {
  message: Message;
  isLast?: boolean;
  threadCount?: number; // Number of replies in thread (Discord-style)
  onOpenThread?: (messageId: string) => void; // Callback to open thread
  onCreateThread?: (messageId: string) => void; // Callback to create thread
  onAddToThread?: (messageId: string, threadId: string) => void; // Callback to add message to thread
  existingThreads?: Array<{ id: string; name: string; message_count: number }>; // Existing threads for this message
}

/**
 * Nested Collapsible Content for System Messages
 * Handles <details> tags for showing summarized message history
 */
const SystemMessageContent: React.FC<{ content: string }> = ({ content }) => {
  // Check if content contains <details> tags (summarized messages)
  const hasDetails = content.includes('<details>');
  
  if (!hasDetails) {
    // No nested content - render normally
    return (
      <div 
        className="text-sm text-yellow-200/90 leading-relaxed whitespace-pre-wrap pt-3"
        dangerouslySetInnerHTML={{ __html: toHtmlLite(content) }}
      />
    );
  }
  
  // Split content into parts (before/inside/after <details>)
  const detailsMatch = content.match(/<details>(.*?)<summary>(.*?)<\/summary>(.*?)<\/details>/s);
  
  if (!detailsMatch) {
    // Malformed details tag - render as-is
    return (
      <div 
        className="text-sm text-yellow-200/90 leading-relaxed whitespace-pre-wrap pt-3"
        dangerouslySetInnerHTML={{ __html: toHtmlLite(content) }}
      />
    );
  }
  
  const [, , summaryText, detailsContent] = detailsMatch;
  const beforeDetails = content.substring(0, content.indexOf('<details>'));
  const afterDetails = content.substring(content.indexOf('</details>') + 10);
  
  const [detailsExpanded, setDetailsExpanded] = useState(false);
  
  return (
    <div className="text-sm text-yellow-200/90 leading-relaxed pt-3">
      {/* Content before <details> */}
      {beforeDetails && (
        <div 
          className="whitespace-pre-wrap mb-3"
          dangerouslySetInnerHTML={{ __html: toHtmlLite(beforeDetails) }}
        />
      )}
      
      {/* Nested collapsible section */}
      <div className="my-3 bg-yellow-900/10 border border-yellow-700/30 rounded-lg overflow-hidden">
        <button
          className="w-full px-3 py-2 flex items-center justify-between hover:bg-yellow-900/20 transition-colors text-left focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:ring-offset-2 focus:ring-offset-yellow-900/10"
          onClick={() => setDetailsExpanded(!detailsExpanded)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setDetailsExpanded(!detailsExpanded);
            }
          }}
          aria-expanded={detailsExpanded}
          aria-label={`${detailsExpanded ? 'Collapse' : 'Expand'} details: ${summaryText.trim()}`}
        >
          <span className="text-xs font-medium text-yellow-300">
            {summaryText.trim()}
          </span>
          <svg 
            className={`w-4 h-4 text-yellow-500 transition-transform ${detailsExpanded ? 'rotate-180' : ''}`}
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        
        {detailsExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="px-3 py-2 border-t border-yellow-700/30 max-h-96 overflow-y-auto"
            aria-hidden={!detailsExpanded}
          >
            <div 
              className="text-xs text-yellow-200 whitespace-pre-wrap font-mono"
              dangerouslySetInnerHTML={{ __html: toHtmlLite(detailsContent.trim()) }}
            />
          </motion.div>
        )}
      </div>
      
      {/* Content after <details> */}
      {afterDetails && (
        <div 
          className="whitespace-pre-wrap mt-3"
          dangerouslySetInnerHTML={{ __html: toHtmlLite(afterDetails) }}
        />
      )}
    </div>
  );
};

const ChatBubble: React.FC<ChatBubbleProps> = ({ 
  message, 
  isLast = false, 
  threadCount = 0, 
  onOpenThread,
  onCreateThread,
  onAddToThread,
  existingThreads = []
}) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const bubbleRef = useRef<HTMLDivElement>(null);
  
  // Collapsible state for system messages (especially summaries!)
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Context menu state
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);
  
  // Handle context menu (right-click)
  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    if (message.id) {
      setContextMenu({ x: e.clientX, y: e.clientY });
    }
  };

  // Close context menu
  const closeContextMenu = () => {
    setContextMenu(null);
  };
  
  // Only show context menu for messages with IDs
  const canShowContextMenu = !!message.id;
  
  // Use Letta-style structured data (no more parsing!)
  const thinking = message.thinking || null;
  const toolCalls = message.toolCalls || [];
  const reasoningTime = message.reasoningTime || 0;
  const response = message.content;
  
  // Determine message type (inbox or system)
  const msgType = message.message_type || (isSystem ? 'system' : 'inbox');
  
  // FILTER: Hide messages that start with !<function_call> (model bug - should use API!)
  if (response.trim().startsWith('!<function_call>')) {
    console.warn('⚠️  Filtering !<function_call> message (model should use tool API!):', response.substring(0, 100));
    return null;  // Don't render this message
  }
  
  // SYSTEM MESSAGES: Special rendering (Context Window Management!)
  if (msgType === 'system' || isSystem) {
    // Check if it's a summary (contains "ZUSAMMENFASSUNG")
    const isSummary = response.includes('ZUSAMMENFASSUNG') || response.includes('📝');
    
    // Extract teaser (first line or first 100 chars)
    const teaser = isSummary 
      ? '📝 Zusammenfassung (Context Window Management)'
      : response.split('\n')[0].substring(0, 100) + (response.length > 100 ? '...' : '');
    
    return (
      <motion.div
        className="flex justify-center mb-4"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="max-w-3xl w-full">
          <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-lg overflow-hidden" role="alert">
            {/* System Header (Clickable) */}
            <button
              className="w-full flex items-center justify-between p-4 hover:bg-yellow-900/30 transition-colors text-left focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:ring-offset-2 focus:ring-offset-yellow-900/20"
              onClick={() => setIsExpanded(!isExpanded)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setIsExpanded(!isExpanded);
                }
              }}
              aria-expanded={isExpanded}
              aria-label={`${isExpanded ? 'Collapse' : 'Expand'} system message: ${teaser}`}
            >
              <div className="flex items-center gap-2 flex-1">
                <svg className="w-4 h-4 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-xs font-bold text-yellow-500 uppercase tracking-wider">
                  [SYSTEM]
                </span>
                <span className="text-sm text-yellow-200">
                  {teaser}
                </span>
              </div>
              
              {/* Expand/Collapse Arrow */}
              <svg 
                className={`w-5 h-5 text-yellow-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {/* System Message Content (Collapsible!) */}
            {isExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="px-4 pb-4 border-t border-yellow-700/30"
                aria-hidden={!isExpanded}
              >
                <SystemMessageContent content={response} />
              </motion.div>
            )}
          </div>
        </div>
      </motion.div>
    );
    }
  
  // Debug: Log structured data for assistant messages (only once on mount!)
  useEffect(() => {
    if (!isUser) {
      console.log('💬 ChatBubble Render:', {
        has_thinking: !!thinking,
        thinking_length: thinking?.length || 0,
        tool_calls_count: toolCalls.length,
        reasoning_time: reasoningTime,
        content_preview: response?.substring(0, 100)
      });
    }
  }, []); // Empty deps = run only once on mount
  
  // Handle copy button clicks for code blocks (Discord style!)
  useEffect(() => {
    if (!bubbleRef.current) return;
    
    const handleCopyClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const button = target.closest('.copy-code-btn');
      if (!button) return;
      
      const codeBlock = button.closest('.code-block');
      const codeElement = codeBlock?.querySelector('code');
      if (!codeElement) return;
      
      const code = codeElement.textContent || '';
      navigator.clipboard.writeText(code).then(() => {
        const originalText = button.textContent;
        button.textContent = '✓ Copied';
        setTimeout(() => {
          button.textContent = originalText;
        }, 1500);
      });
    };
    
    bubbleRef.current.addEventListener('click', handleCopyClick);
    return () => {
      bubbleRef.current?.removeEventListener('click', handleCopyClick);
    };
  }, [response]);
  
  const handleSpeakMessage = () => {
    if (!isUser) {
      // Only speak the response, not the thinking
      speak(response);
    }
  };
  
  return (
    <>
      <motion.article
        ref={bubbleRef}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        role="article"
        aria-label={isUser ? 'Your message' : 'Assistant message'}
        onContextMenu={canShowContextMenu ? handleContextMenu : undefined}
      >
      <div className={`max-w-[80%] ${isUser ? 'ml-auto' : 'mr-auto'}`}>
        {/* Letta-Style: Reasoning Block (only for assistant with thinking) */}
        {!isUser && thinking && (
          <ReasoningBlock 
            thinking={thinking} 
            duration={reasoningTime}
          />
        )}
        
        {/* Letta-Style: Tool Call Blocks (only for assistant with tool calls) */}
        {!isUser && toolCalls.length > 0 && (
          <div className="space-y-1 mb-2" role="group" aria-label="Tool calls">
            {toolCalls.map((tool, idx) => (
              <ToolCallBlock
                key={idx}
                toolName={tool.name}
                toolInput={tool.arguments}
                toolOutput={tool.result}
                duration={0} // TODO: Track individual tool durations
              />
            ))}
          </div>
        )}
        
        {/* Main Message Bubble */}
      <div 
        className={`
            rounded-2xl px-4 py-3
          ${isUser 
              ? 'bg-gradient-to-r from-limeGlow/90 to-aquaGlow/90 text-background [&_.markdown-subtext]:!text-gray-900/80' 
              : 'bg-gradient-to-r from-violetGlow/90 to-[#7D4CDB]/90 text-white [&_.markdown-subtext]:!text-white/60'
          }
          shadow-lg
          min-w-0
        `}
      >
        {/* INBOX Badge */}
        <div className="flex items-center gap-1.5 mb-1.5" aria-hidden="true">
          <svg className="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          <span className="text-[10px] font-bold opacity-70 uppercase tracking-wider">
            [INBOX]
          </span>
        </div>
        
        <div className="flex items-start min-w-0">
          <div
            className="whitespace-pre-wrap break-words overflow-wrap-anywhere flex-1 leading-relaxed min-w-0"
              dangerouslySetInnerHTML={{ __html: toHtmlLite(response) }}
          />
          
          {/* TTS button only for assistant messages */}
          {!isUser && (
            <button 
              onClick={handleSpeakMessage}
              className="ml-2 mt-1 flex-shrink-0 text-white/70 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-violetGlow/90 rounded"
              aria-label="Speak message aloud"
            >
              <Volume2 size={16} aria-hidden="true" />
            </button>
          )}
        </div>
        
        {/* Model Label (bottom left) - only for assistant messages */}
        {!isUser && message.model && (
          <div className="mt-2 flex items-center gap-1 text-[10px] text-white/50" aria-label={`Generated by ${message.model}`}>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span className="truncate max-w-[200px]">{message.model.split('/').pop()}</span>
          </div>
        )}
        
        {/* Animated indicator for last message from assistant */}
        {isLast && !isUser && (
          <motion.div 
            className="h-[2px] mt-2 bg-white/30 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: '100%' }}
            transition={{ duration: 0.5 }}
            aria-hidden="true"
          />
        )}
        </div>
        
        {/* Thread Indicator (Discord-style) */}
        {threadCount > 0 && message.id && (
          <button
            onClick={() => message.id && onOpenThread?.(message.id)}
            className="mt-2 flex items-center gap-1.5 text-xs text-gray-400 hover:text-violet-400 transition-colors group"
            title={`${threadCount} ${threadCount === 1 ? 'reply' : 'replies'} in thread`}
          >
            <MessageSquare className="w-3.5 h-3.5 group-hover:text-violet-400 transition-colors" />
            <span className="font-medium">{threadCount} {threadCount === 1 ? 'reply' : 'replies'}</span>
          </button>
        )}
      </div>
    </motion.article>
    
    {/* Context Menu */}
    {contextMenu && message.id && (
      <MessageContextMenu
        messageId={message.id}
        x={contextMenu.x}
        y={contextMenu.y}
        onClose={closeContextMenu}
        onCreateThread={(msgId) => {
          onCreateThread?.(msgId);
          closeContextMenu();
        }}
        onAddToThread={(msgId, threadId) => {
          onAddToThread?.(msgId, threadId);
          closeContextMenu();
        }}
        existingThreads={existingThreads}
      />
    )}
    </>
  );
};

export default ChatBubble;