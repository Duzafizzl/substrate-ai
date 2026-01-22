import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ToolCallBlockProps {
  toolName: string;
  toolInput: Record<string, any>;
  toolOutput: Record<string, any> | string;
  duration?: number; // in seconds
}

/**
 * Tool Call Block
 * Collapsible block showing tool execution with Input/Output tabs
 */
const ToolCallBlock: React.FC<ToolCallBlockProps> = ({ 
  toolName, 
  toolInput, 
  toolOutput, 
  duration = 0 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'input' | 'output'>('output');
  
  const durationText = duration < 1 
    ? `${Math.round(duration * 1000)}ms`
    : `${duration.toFixed(1)}s`;
  
  // Format JSON nicely
  const formatJson = (data: any): string => {
    if (typeof data === 'string') return data;
    return JSON.stringify(data, null, 2);
  };
  
  // Extract preview from tool input (show what's happening!)
  const getToolPreview = (): string => {
    if (toolName === 'spotify_control') {
      const query = toolInput?.query || toolInput?.track_name || '';
      const action = toolInput?.action || '';
      if (action === 'add_to_queue' && query) return `Adding: ${query}`;
      if (action === 'play' && query) return `Playing: ${query}`;
      if (action === 'search' && query) return `Searching: ${query}`;
    }
    
    if (toolName === 'discord_tool') {
      const action = toolInput?.action || '';
      const message = toolInput?.message || '';
      if (action === 'send_message' && message) {
        const preview = message.substring(0, 40);
        return `Sending: ${preview}${message.length > 40 ? '...' : ''}`;
      }
      if (action === 'read_messages') return 'Reading messages';
    }
    
    // Default: show action from input
    if (toolInput?.action) return toolInput.action;
    
    return 'Executed';
  };
  
  return (
    <div className="mb-2 rounded-lg border border-gray-700/50 bg-gray-800/60 overflow-hidden">
      {/* Header (always visible) */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center gap-2 hover:bg-gray-700/30 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown size={16} className="text-blue-300/60 flex-shrink-0" />
        ) : (
          <ChevronRight size={16} className="text-blue-300/60 flex-shrink-0" />
        )}
        <span className="text-sm text-blue-300/80 font-medium flex-1 text-left truncate">
          {getToolPreview()}
        </span>
        <span className="text-xs text-blue-200/60 font-mono">
          {toolName}
        </span>
        <span className="text-xs text-gray-400 font-mono">
          {durationText}
        </span>
      </button>
      
      {/* Tool Details (expandable) */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-gray-700/50">
              {/* Tabs */}
              <div className="flex border-b border-gray-700/30 bg-gray-800/30">
                <button
                  onClick={() => setActiveTab('input')}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    activeTab === 'input'
                      ? 'text-blue-300 border-b-2 border-blue-400'
                      : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  Tool input
                </button>
                <button
                  onClick={() => setActiveTab('output')}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    activeTab === 'output'
                      ? 'text-blue-300 border-b-2 border-blue-400'
                      : 'text-gray-400 hover:text-gray-300'
                  }`}
                >
                  Tool output
                </button>
              </div>
              
              {/* Content */}
              <div className="px-3 py-2">
                {activeTab === 'input' ? (
                  <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words font-mono leading-relaxed">
                    {formatJson(toolInput)}
                  </pre>
                ) : (
                  <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words font-mono leading-relaxed">
                    {formatJson(toolOutput)}
                  </pre>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ToolCallBlock;

