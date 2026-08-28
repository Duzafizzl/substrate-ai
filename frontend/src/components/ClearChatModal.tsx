/**
 * ClearChatModal.tsx – Bestätigungsdialog zum Leeren des Chats (UI vs. Backend).
 * Created: 2026-08-28
 * Last updated: 2026-08-28
 */
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, X } from 'lucide-react';

interface ClearChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  onClearUIOnly: () => void;
  onClearBackend: () => Promise<void>;
}

const ClearChatModal: React.FC<ClearChatModalProps> = ({
  isOpen,
  onClose,
  onClearUIOnly,
  onClearBackend,
}) => {
  const [loading, setLoading] = React.useState(false);

  const handleClearUI = () => {
    onClearUIOnly();
    onClose();
  };

  const handleClearBackend = async () => {
    setLoading(true);
    try {
      await onClearBackend();
      onClose();
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="bg-gray-900 border border-red-900/50 rounded-xl shadow-2xl max-w-md w-full p-6"
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-labelledby="clear-chat-title"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="w-5 h-5" />
              <h2 id="clear-chat-title" className="text-lg font-semibold text-white">
                Clear chat
              </h2>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <p className="text-sm text-gray-300 mb-6">
            Choose how much data to remove. Backend clear is permanent.
          </p>

          <div className="space-y-3">
            <button
              onClick={handleClearUI}
              disabled={loading}
              className="w-full px-4 py-3 rounded-lg bg-gray-800 hover:bg-gray-700 text-left transition-colors disabled:opacity-50"
            >
              <div className="font-medium text-white">Clear UI only</div>
              <div className="text-xs text-gray-400 mt-1">
                Removes messages from the screen. Backend history stays intact.
              </div>
            </button>

            <button
              onClick={() => void handleClearBackend()}
              disabled={loading}
              className="w-full px-4 py-3 rounded-lg bg-red-900/40 hover:bg-red-900/60 border border-red-800 text-left transition-colors disabled:opacity-50"
            >
              <div className="font-medium text-red-200">
                {loading ? 'Clearing…' : 'Clear backend (permanent)'}
              </div>
              <div className="text-xs text-red-300/80 mt-1">
                Deletes conversation data from PostgreSQL / SQLite.
              </div>
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default ClearChatModal;
