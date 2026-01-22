import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { motion } from 'framer-motion';
import SessionSwitcher from './SessionSwitcher';
import { useChat } from '../../contexts/ChatContext';
import { Download, Save, Database } from 'lucide-react';
import { pushSessionToMemory } from '../../lib/memory';

interface HeaderProps {
  title?: string;
}

const Header: React.FC<HeaderProps> = ({ title }) => {
  const location = useLocation();
  const isHome = location.pathname === '/';
  const { exportActiveSession, saveForLater, sessions, activeSessionId, model, setModel, disablePresenceSeed, setDisablePresenceSeed, disableNormalizer, setDisableNormalizer, disableCorePrompt, setDisableCorePrompt } = useChat();
  
  const onPushMemory = async () => {
    const current = sessions.find((s) => s.id === activeSessionId);
    if (!current) return;
    await pushSessionToMemory(current, { id: model, name: 'Assistant', model: `ollama:${model}`, version: 'local' }).catch(() => {});
  };

  // SAVE MODEL TO BACKEND + .ENV
  const handleModelChange = async (newModel: string) => {
    // Update local state immediately
    setModel(newModel);
    
    // Save to backend (which also syncs to .env!)
    try {
      const API_URL = 'http://localhost:8284';
      const response = await fetch(`${API_URL}/api/agents/default/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          model: newModel,
          change_description: `Changed model to ${newModel} via header dropdown`
        })
      });
      
      if (response.ok) {
        console.log(`✅ Model saved to backend + .env: ${newModel}`);
      } else {
        console.error('❌ Failed to save model to backend:', await response.text());
      }
    } catch (error) {
      console.error('❌ Error saving model:', error);
    }
  };
  
  return (
    <motion.header 
      className="relative py-5 px-4 flex items-center justify-between border-b border-lightGlass backdrop-blur-md z-10"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center">
        {!isHome && (
          <Link to="/" className="mr-3 text-white/70 hover:text-white transition-colors">
            <ChevronLeft size={24} />
          </Link>
        )}
        
        <h1 className="text-xl font-semibold">
          {title || (
            <span className="text-gradient">Substrate AI</span>
          )}
        </h1>
      </div>
      
      {/* Sessions */}
      <div className="flex items-center space-x-2">
        <SessionSwitcher />
        <select
          className="glass-panel bg-darkGlass text-white rounded-lg px-3 py-2 border border-lightGlass"
          value={model}
          onChange={(e) => handleModelChange(e.target.value)}
          title="Select model (saves to Backend + .env)"
          aria-label="Select model"
        >
          <option value="google/gemini-2.0-flash-exp:free">🎉 Gemini 2.0 Flash (FREE!)</option>
          <option value="qwen/qwen-2.5-72b-instruct">💚 Qwen 2.5 72B (Affordable)</option>
          <option value="qwen/qwen3-vl-30b-a3b-thinking">💚 Qwen Thinking (Affordable)</option>
          <option value="anthropic/claude-haiku-4.5">💛 Claude Haiku 4.5 (⚠️ No Tools)</option>
          <option value="anthropic/claude-sonnet-4">🧡 Claude Sonnet 4</option>
          <option value="openrouter/polaris-alpha">🧡 Polaris Alpha (GPT-5.1)</option>
          <option value="anthropic/claude-opus-4.5">🔴 Claude Opus 4.5 (Expensive!)</option>
        </select>
        <label className="flex items-center gap-1 text-white/80 text-sm ml-2">
          <input type="checkbox" checked={disablePresenceSeed} onChange={(e) => setDisablePresenceSeed(e.target.checked)} /> Disable Seed
        </label>
        <label className="flex items-center gap-1 text-white/80 text-sm">
          <input type="checkbox" checked={disableNormalizer} onChange={(e) => setDisableNormalizer(e.target.checked)} /> Disable Normalizer
        </label>
        <label className="flex items-center gap-1 text-white/80 text-sm">
          <input type="checkbox" checked={disableCorePrompt} onChange={(e) => setDisableCorePrompt(e.target.checked)} /> Disable Core Prompt
        </label>
        <button
          onClick={exportActiveSession}
          className="p-2 rounded-lg bg-gradient-to-r from-sky-500 to-cyan-500 text-white"
          title="Export active session"
          aria-label="Export active session"
        >
          <Download size={16} />
        </button>
        <button
          onClick={saveForLater}
          className="p-2 rounded-lg bg-gradient-to-r from-emerald-500 to-green-500 text-white"
          title="Save for later (local file)"
          aria-label="Save for later"
        >
          <Save size={16} />
        </button>
        <button
          onClick={onPushMemory}
          className="p-2 rounded-lg bg-gradient-to-r from-fuchsia-500 to-pink-500 text-white"
          title="Push Memory (Neo4j)"
          aria-label="Push Memory"
        >
          <Database size={16} />
        </button>
      </div>
    </motion.header>
  );
};

export default Header;