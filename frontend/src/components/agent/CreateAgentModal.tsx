/**
 * CreateAgentModal.tsx – Dialog zum Anlegen eines neuen Agents.
 * Created: 2026-08-28
 * Last updated: 2026-08-28
 */
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, X } from 'lucide-react';

interface CreateAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

const CreateAgentModal: React.FC<CreateAgentModalProps> = ({
  isOpen,
  onClose,
  onCreated,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [model, setModel] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setName('');
    setDescription('');
    setModel('');
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Agent name is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const body: Record<string, string> = { name: name.trim() };
      if (description.trim()) body.description = description.trim();
      if (model.trim()) body.model = model.trim();

      const response = await fetch('http://localhost:8284/api/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || 'Failed to create agent');
        return;
      }

      resetForm();
      onCreated();
    } catch {
      setError('Could not reach backend. Is the server running on port 8284?');
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
        onClick={handleClose}
      >
        <motion.form
          className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-w-md w-full p-6"
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          onSubmit={(e) => void handleSubmit(e)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-agent-title"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-2 text-purple-400">
              <Plus className="w-5 h-5" />
              <h2 id="create-agent-title" className="text-lg font-semibold text-white">
                Create new agent
              </h2>
            </div>
            <button
              type="button"
              onClick={handleClose}
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label htmlFor="agent-name" className="block text-sm text-gray-400 mb-1">
                Name *
              </label>
              <input
                id="agent-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="My Agent"
                disabled={loading}
                autoFocus
              />
            </div>

            <div>
              <label htmlFor="agent-description" className="block text-sm text-gray-400 mb-1">
                Description
              </label>
              <textarea
                id="agent-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                rows={2}
                placeholder="Optional description"
                disabled={loading}
              />
            </div>

            <div>
              <label htmlFor="agent-model" className="block text-sm text-gray-400 mb-1">
                Model (optional)
              </label>
              <input
                id="agent-model"
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="qwen/qwen-2.5-72b-instruct"
                disabled={loading}
              />
            </div>

            {error && (
              <p className="text-sm text-red-400" role="alert">
                {error}
              </p>
            )}
          </div>

          <div className="flex gap-3 mt-6">
            <button
              type="button"
              onClick={handleClose}
              disabled={loading}
              className="flex-1 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-medium transition-colors disabled:opacity-50"
            >
              {loading ? 'Creating…' : 'Create agent'}
            </button>
          </div>
        </motion.form>
      </motion.div>
    </AnimatePresence>
  );
};

export default CreateAgentModal;
