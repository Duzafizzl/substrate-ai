/**
 * MessageContextMenu.tsx – Kontextmenü für Chat-Nachrichten (Threads).
 * Created: 2026-08-28
 * Last updated: 2026-08-28
 */
import React, { useEffect, useRef, useState } from 'react';
import { MessageSquare, Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface MessageContextMenuProps {
  messageId: string;
  x: number;
  y: number;
  onClose: () => void;
  onCreateThread: (messageId: string) => void;
  onAddToThread: (messageId: string, threadId: string) => void;
  existingThreads?: Array<{ id: string; name: string; message_count: number }>;
}

const MessageContextMenu: React.FC<MessageContextMenuProps> = ({
  messageId,
  x,
  y,
  onClose,
  onCreateThread,
  onAddToThread,
  existingThreads = [],
}) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [adjustedPosition, setAdjustedPosition] = useState({ x, y });

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  useEffect(() => {
    if (!menuRef.current) return;

    const rect = menuRef.current.getBoundingClientRect();
    let newX = x;
    let newY = y;

    if (x + rect.width > window.innerWidth) {
      newX = window.innerWidth - rect.width - 10;
    }
    if (newX < 10) newX = 10;

    if (y + rect.height > window.innerHeight) {
      newY = window.innerHeight - rect.height - 10;
    }
    if (newY < 10) newY = 10;

    setAdjustedPosition({ x: newX, y: newY });
  }, [x, y]);

  return (
    <AnimatePresence>
      <motion.div
        ref={menuRef}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.15 }}
        className="fixed z-50 bg-gray-800 border border-gray-700 rounded-lg shadow-xl py-1 min-w-[220px]"
        style={{
          left: `${adjustedPosition.x}px`,
          top: `${adjustedPosition.y}px`,
        }}
      >
        <button
          onClick={() => onCreateThread(messageId)}
          className="w-full px-4 py-2 text-left text-sm text-gray-200 hover:bg-gray-700 flex items-center gap-2 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Create thread</span>
        </button>

        {existingThreads.length > 0 && (
          <>
            <div className="border-t border-gray-700 my-1" />
            <div className="px-3 py-1 text-xs text-gray-500 uppercase tracking-wide">
              Add to thread
            </div>
            {existingThreads.map((thread) => (
              <button
                key={thread.id}
                onClick={() => onAddToThread(messageId, thread.id)}
                className="w-full px-4 py-2 text-left text-sm text-gray-200 hover:bg-gray-700 flex items-center gap-2 transition-colors"
              >
                <MessageSquare className="w-4 h-4" />
                <span className="truncate">
                  {thread.name} ({thread.message_count})
                </span>
              </button>
            ))}
          </>
        )}
      </motion.div>
    </AnimatePresence>
  );
};

export default MessageContextMenu;
