import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ReasoningBlockProps {
  thinking: string;
  duration?: number; // in seconds
}

/**
 * Reasoning Block
 * Collapsible grey block showing AI's internal thinking process
 */
const ReasoningBlock: React.FC<ReasoningBlockProps> = ({ thinking, duration = 0 }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const durationText = duration < 1 
    ? 'less than 1 second' 
    : duration < 60 
      ? `${Math.round(duration)} seconds`
      : `${Math.round(duration / 60)} minutes`;
  
  return (
    <div className="mb-2 rounded-lg border border-gray-700/30 bg-gray-800/40 overflow-hidden">
      {/* Header (always visible) */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center gap-2 hover:bg-gray-700/20 transition-colors text-left"
      >
        {isExpanded ? (
          <ChevronDown size={16} className="text-purple-300/60 flex-shrink-0" />
        ) : (
          <ChevronRight size={16} className="text-purple-300/60 flex-shrink-0" />
        )}
        <span className="text-sm text-purple-300/70 font-medium flex-1">
          Reasoned for {durationText}...
        </span>
      </button>
      
      {/* Thinking Content (expandable) */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 pt-1 border-t border-gray-700/30">
              <pre className="text-xs text-purple-200/70 whitespace-pre-wrap break-words font-mono leading-relaxed">
                {thinking}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ReasoningBlock;

