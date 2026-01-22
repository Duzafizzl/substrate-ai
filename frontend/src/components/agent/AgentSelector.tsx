import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CreateAgentModal from './CreateAgentModal';

interface Agent {
  id: string;
  name: string;
  model: string;
  description: string;
  is_active: boolean;
}

interface AgentSelectorProps {
  onAgentChange?: (agentId: string) => void;
}

export default function AgentSelector({ onAgentChange }: AgentSelectorProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [currentAgent, setCurrentAgent] = useState<Agent | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await fetch('http://localhost:8284/api/agents');
      const data = await response.json();
      if (data.agents && data.agents.length > 0) {
        setAgents(data.agents);
        
        // Get agent ID from URL parameter
        const params = new URLSearchParams(window.location.search);
        const urlAgentId = params.get('agent');
        
        // Find agent by ID from URL, or use first agent
        let selectedAgent = data.agents[0];
        if (urlAgentId) {
          const foundAgent = data.agents.find((a: Agent) => a.id === urlAgentId);
          if (foundAgent) {
            selectedAgent = foundAgent;
            console.log(`📖 AgentSelector: Found agent from URL: ${foundAgent.name} (${foundAgent.id})`);
          } else {
            console.log(`⚠️  AgentSelector: Agent ${urlAgentId} not found, using first agent`);
          }
        }
        
        setCurrentAgent(selectedAgent);
        
        // Notify parent of selected agent ID
        if (onAgentChange) {
          onAgentChange(selectedAgent.id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectAgent = (agent: Agent) => {
    setCurrentAgent(agent);
    setIsOpen(false);
    if (onAgentChange) {
      onAgentChange(agent.id);
    }
  };

  const startEditing = (agent: Agent, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent selecting the agent
    setEditingAgentId(agent.id);
    setEditName(agent.name);
  };

  const cancelEditing = () => {
    setEditingAgentId(null);
    setEditName('');
  };

  const saveAgentName = async (agentId: string) => {
    if (!editName.trim()) {
      alert('Agent name cannot be empty');
      return;
    }

    setSaving(true);
    try {
      const response = await fetch(`http://localhost:8284/api/agents/${agentId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName.trim() })
      });

      if (response.ok) {
        const data = await response.json();
        // Update agents list
        const updatedAgents = agents.map(a => 
          a.id === agentId ? { ...a, name: data.agent.name } : a
        );
        setAgents(updatedAgents);
        
        // Update current agent if it's the one being edited
        if (currentAgent?.id === agentId) {
          setCurrentAgent({ ...currentAgent, name: data.agent.name });
        }
        
        setEditingAgentId(null);
        setEditName('');
      } else {
        const error = await response.json();
        alert(`Failed to update agent name: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error updating agent name:', error);
      alert('Failed to update agent name. Please check your connection.');
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, agentId: string) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveAgentName(agentId);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelEditing();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-4 py-2">
        <div className="w-4 h-4 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
        <span className="text-sm text-gray-400">Loading agent...</span>
      </div>
    );
  }

  if (!currentAgent) {
    return null;
  }

  return (
    <div className="relative">
      {/* Current Agent Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 px-4 py-2 rounded-lg hover:bg-gray-800/50 transition-colors group max-w-xs"
        title={`${currentAgent.name} - ${currentAgent.model}`}
      >
        {/* Agent Icon */}
        <div className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>

        {/* Agent Info */}
        <div className="flex flex-col items-start min-w-0 flex-1">
          <span className="text-sm font-semibold text-gray-100 group-hover:text-white transition-colors truncate w-full">
            {currentAgent.name}
          </span>
          <span className="text-xs text-gray-500 group-hover:text-gray-400 transition-colors truncate w-full">
            {currentAgent.model.split('/').pop()}
          </span>
        </div>

        {/* Dropdown Icon */}
        <svg 
          className={`flex-shrink-0 w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div 
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Dropdown */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="absolute top-full left-0 mt-2 w-80 bg-gray-900 border border-gray-700 rounded-xl shadow-xl overflow-hidden z-50"
            >
              {/* Header */}
              <div className="px-4 py-3 border-b border-gray-800">
                <h3 className="text-sm font-semibold text-gray-300">Switch Agent</h3>
              </div>

              {/* Agent List */}
              <div className="max-h-96 overflow-y-auto">
                {agents.map((agent) => (
                  <div
                    key={agent.id}
                    className={`
                      w-full px-4 py-3 flex items-start gap-3 hover:bg-gray-800/50 transition-colors group
                      ${agent.id === currentAgent.id ? 'bg-gray-800/30' : ''}
                    `}
                  >
                    {/* Agent Icon */}
                    <div className={`
                      flex items-center justify-center w-10 h-10 rounded-lg flex-shrink-0
                      ${agent.is_active 
                        ? 'bg-gradient-to-br from-purple-500 to-pink-500' 
                        : 'bg-gray-700'
                      }
                    `}>
                      <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                    </div>

                    {/* Agent Details */}
                    <div className="flex flex-col items-start flex-1 min-w-0">
                      <div className="flex items-center gap-2 w-full">
                        {editingAgentId === agent.id ? (
                          <div className="flex items-center gap-2 flex-1">
                            <input
                              type="text"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              onKeyDown={(e) => handleKeyDown(e, agent.id)}
                              onBlur={() => saveAgentName(agent.id)}
                              className="flex-1 px-2 py-1 text-sm font-semibold bg-gray-800 border border-purple-500 rounded text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                              autoFocus
                              disabled={saving}
                            />
                            <button
                              onClick={() => saveAgentName(agent.id)}
                              disabled={saving}
                              className="p-1 text-green-400 hover:text-green-300 disabled:opacity-50"
                              title="Save"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            </button>
                            <button
                              onClick={cancelEditing}
                              disabled={saving}
                              className="p-1 text-gray-400 hover:text-gray-300 disabled:opacity-50"
                              title="Cancel"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          </div>
                        ) : (
                          <>
                            <span 
                              className="text-sm font-semibold text-gray-100 truncate flex-1 cursor-pointer"
                              onClick={() => selectAgent(agent)}
                            >
                              {agent.name}
                            </span>
                            <button
                              onClick={(e) => startEditing(agent, e)}
                              className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-gray-300 transition-opacity"
                              title="Edit name"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                              </svg>
                            </button>
                          </>
                        )}
                        {agent.id === currentAgent.id && (
                          <span className="px-2 py-0.5 text-xs font-medium text-purple-400 bg-purple-500/10 rounded-full">
                            Active
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-gray-500 truncate w-full">
                        {agent.model}
                      </span>
                      {agent.description && (
                        <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                          {agent.description}
                        </p>
                      )}
                    </div>

                    {/* Checkmark */}
                    {agent.id === currentAgent.id && editingAgentId !== agent.id && (
                      <svg className="w-5 h-5 text-purple-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                ))}
              </div>

              {/* Footer */}
              <div className="px-4 py-3 border-t border-gray-800 bg-gray-900/50">
                <button 
                  className="w-full px-3 py-2 text-sm font-medium text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 rounded-lg transition-colors flex items-center justify-center gap-2"
                  onClick={() => {
                    setIsOpen(false);
                    setShowCreateModal(true);
                  }}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Create New Agent
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      
      {/* Create Agent Modal */}
      <CreateAgentModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={() => {
          fetchAgents();
          setShowCreateModal(false);
        }}
      />
    </div>
  );
}

