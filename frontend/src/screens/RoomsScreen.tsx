import React, { useState, useEffect } from 'react';
import { Hash, Plus, ChevronRight, ChevronDown, Copy, Check, MessageSquare, ArrowLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import RoomChatView from '../components/rooms/RoomChatView';

interface Channel {
  id: string;
  name: string;
  description: string;
  parent_id: string | null;
  discord_channel_id: string | null;
  discord_webhook_url: string | null;
  created_at: string;
  updated_at: string;
}

interface RoomsScreenProps {
  onBack: () => void;
  agentId?: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8284';

const RoomsScreen: React.FC<RoomsScreenProps> = ({ onBack, agentId = 'default' }) => {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRooms, setExpandedRooms] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedParentId, setSelectedParentId] = useState<string | null>(null);
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);

  const currentAgentId = agentId;

  useEffect(() => {
    loadChannels();
  }, [currentAgentId]);

  const loadChannels = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/channels?agent_id=${currentAgentId}&include_children=true`);
      if (response.ok) {
      const data = await response.json();
      setChannels(data.channels || []);
      } else {
        console.error('Failed to load channels');
      }
    } catch (error) {
      console.error('Error loading channels:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleRoom = (roomId: string) => {
    setExpandedRooms(prev => {
      const newSet = new Set(prev);
      if (newSet.has(roomId)) {
        newSet.delete(roomId);
      } else {
        newSet.add(roomId);
      }
      return newSet;
    });
  };

  const copyId = async (id: string) => {
    try {
      await navigator.clipboard.writeText(id);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (error) {
      console.error('Failed to copy ID:', error);
    }
  };

  // Build hierarchical structure
  // Filter out task channel - tasks are managed via Plan/Task UI, not Rooms
  const topLevelRooms = channels.filter(ch => !ch.parent_id && !ch.name.includes('task'));
  const subRoomsByParent: Record<string, Channel[]> = {};
  channels.forEach(ch => {
    if (ch.parent_id) {
      if (!subRoomsByParent[ch.parent_id]) {
        subRoomsByParent[ch.parent_id] = [];
      }
      subRoomsByParent[ch.parent_id].push(ch);
    }
  });
  
  // If a room is selected, show chat view for that room
  if (selectedRoomId) {
    const selectedRoom = channels.find(ch => ch.id === selectedRoomId);
    if (selectedRoom) {
      return (
        <div className="h-screen flex flex-col bg-gray-950">
          <RoomChatView 
            channel={selectedRoom}
            onBack={() => setSelectedRoomId(null)}
            agentId={currentAgentId}
            onNavigateToChannel={(channelId) => setSelectedRoomId(channelId)}
          />
        </div>
      );
    }
  }

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      {/* Header */}
      <header className="h-16 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
            title="Back to Chat"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
              <Hash className="w-4 h-4 text-white" />
            </div>
            <span className="text-gray-300 font-medium">Heartbeat Rooms</span>
          </div>
        </div>
        
        <button
          onClick={() => {
            setSelectedParentId(null);
            setShowCreateModal(true);
          }}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span className="text-sm">New Room</span>
        </button>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar: Rooms List */}
        <div className="w-80 bg-gray-900/50 border-r border-gray-800 flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-gray-800">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Hash className="w-5 h-5 text-violet-400" />
                Rooms
              </h2>
            </div>
          </div>
          
          {/* Rooms List */}
          <div className="flex-1 overflow-y-auto p-2">
            {loading ? (
              <div className="text-center text-gray-400 py-8">Loading rooms...</div>
            ) : topLevelRooms.length === 0 ? (
              <div className="text-center text-gray-400 py-8">
                <p className="mb-2">No rooms yet</p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="text-violet-400 hover:text-violet-300 text-sm"
                >
                  Create your first room
                </button>
              </div>
            ) : (
              <div className="space-y-1">
                {topLevelRooms.map(room => (
                  <RoomItem
                    key={room.id}
                    room={room}
                    subRooms={subRoomsByParent[room.id] || []}
                    isExpanded={expandedRooms.has(room.id)}
                    onToggle={() => toggleRoom(room.id)}
                    onSelect={(id) => setSelectedRoomId(id)}
                    onCopyId={copyId}
                    copiedId={copiedId}
                    onCreateSubRoom={(parentId) => {
                      setSelectedParentId(parentId);
                      setShowCreateModal(true);
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Main Content: Welcome */}
        <div className="flex-1 flex items-center justify-center bg-gray-950">
          <div className="text-center text-gray-400 max-w-md px-6">
            <Hash className="w-16 h-16 mx-auto mb-4 text-gray-600" />
            <h3 className="text-xl font-semibold text-white mb-2">Select a room</h3>
            <p className="text-sm">
              Choose a room from the sidebar to start chatting, or create a new room to get started.
            </p>
                  </div>
                </div>
              </div>

      {/* Create Room Modal */}
      {showCreateModal && (
        <CreateRoomModal
          parentId={selectedParentId}
          onClose={() => {
            setShowCreateModal(false);
            setSelectedParentId(null);
          }}
          onCreated={() => {
            loadChannels();
            setShowCreateModal(false);
            setSelectedParentId(null);
          }}
          existingRooms={channels}
          agentId={currentAgentId}
        />
      )}
    </div>
  );
};

interface RoomItemProps {
  room: Channel;
  subRooms: Channel[];
  isExpanded: boolean;
  onToggle: () => void;
  onSelect: (id: string) => void;
  onCopyId: (id: string) => void;
  copiedId: string | null;
  onCreateSubRoom: (parentId: string) => void;
}

const RoomItem: React.FC<RoomItemProps> = ({
  room,
  subRooms,
  isExpanded,
  onToggle,
  onSelect,
  onCopyId,
  copiedId,
  onCreateSubRoom
}) => {
  const hasSubRooms = subRooms.length > 0;
  
  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 hover:border-gray-600/50 transition-colors">
      {/* Main Room Item */}
      <div className="flex items-center gap-2 p-3">
        <button
          onClick={onToggle}
          className="p-1 hover:bg-gray-700/50 rounded transition-colors"
          title={isExpanded ? "Collapse sub-rooms" : "Expand sub-rooms"}
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
        </button>
        
        <button
          onClick={() => onSelect(room.id)}
          className="flex-1 flex items-center gap-2 text-left hover:bg-gray-700/30 rounded px-2 py-1.5 transition-colors group"
        >
          <Hash className="w-4 h-4 text-violet-400 flex-shrink-0" />
          <span className="text-sm font-medium text-white flex-1 truncate">{room.name}</span>
          <MessageSquare className="w-3.5 h-3.5 text-gray-500 group-hover:text-violet-400 transition-colors" />
        </button>
        
        <button
          onClick={(e) => {
            e.stopPropagation();
            onCopyId(room.id);
          }}
          className="p-1.5 hover:bg-gray-700/50 rounded transition-colors"
          title="Copy room ID"
        >
          {copiedId === room.id ? (
            <Check className="w-3.5 h-3.5 text-green-400" />
          ) : (
            <Copy className="w-3.5 h-3.5 text-gray-400" />
          )}
        </button>
        
        <button
          onClick={(e) => {
            e.stopPropagation();
            onCreateSubRoom(room.id);
          }}
          className="p-1.5 hover:bg-gray-700/50 rounded transition-colors"
          title="Create sub-room"
        >
          <Plus className="w-3.5 h-3.5 text-gray-400 hover:text-violet-400 transition-colors" />
        </button>
      </div>
      
      {/* Sub-Rooms */}
      <AnimatePresence>
        {isExpanded && (
                      <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
                      >
            <div className="pl-8 pr-2 pb-2 space-y-1">
              {hasSubRooms ? (
                subRooms.map(subRoom => (
                  <div
                    key={subRoom.id}
                    className="bg-gray-800/30 rounded border border-gray-700/30 hover:border-gray-600/50 transition-colors"
                        >
                    <div className="flex items-center gap-2 p-2.5">
                      <button
                        onClick={() => onSelect(subRoom.id)}
                        className="flex-1 flex items-center gap-2 text-left hover:bg-gray-700/30 rounded px-2 py-1 transition-colors group"
                      >
                        <Hash className="w-3.5 h-3.5 text-violet-400/70 flex-shrink-0" />
                        <span className="text-xs font-medium text-gray-300 flex-1 truncate">{subRoom.name}</span>
                        <MessageSquare className="w-3 h-3 text-gray-500 group-hover:text-violet-400 transition-colors" />
                      </button>
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onCopyId(subRoom.id);
                        }}
                        className="p-1 hover:bg-gray-700/50 rounded transition-colors"
                        title="Copy room ID"
                      >
                        {copiedId === subRoom.id ? (
                          <Check className="w-3 h-3 text-green-400" />
                        ) : (
                          <Copy className="w-3 h-3 text-gray-400" />
                        )}
                      </button>
                      
                  <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onCreateSubRoom(subRoom.id);
                        }}
                        className="p-1 hover:bg-gray-700/50 rounded transition-colors"
                        title="Create sub-room"
                  >
                        <Plus className="w-3 h-3 text-gray-400" />
                  </button>
                </div>
              </div>
                ))
          ) : (
                <div className="text-center text-gray-500 py-4 text-xs">
                  <p>No sub-rooms</p>
              </div>
              )}
            </div>
          </motion.div>
          )}
      </AnimatePresence>
      </div>
  );
};

interface CreateRoomModalProps {
  parentId: string | null;
  onClose: () => void;
  onCreated: () => void;
  existingRooms: Channel[];
  agentId: string;
}

const CreateRoomModal: React.FC<CreateRoomModalProps> = ({
  parentId,
  onClose,
  onCreated,
  existingRooms,
  agentId
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [discordChannelId, setDiscordChannelId] = useState('');
  const [discordWebhookUrl, setDiscordWebhookUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const currentAgentId = agentId || 'default';
  
  const parentRoom = parentId ? existingRooms.find(r => r.id === parentId) : null;
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/channels`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: currentAgentId,
          name: name.trim(),
          description: description.trim() || null,
          parent_id: parentId || null,
          discord_channel_id: discordChannelId.trim() || null,
          discord_webhook_url: discordWebhookUrl.trim() || null
        })
      });
      
      if (response.ok) {
        onCreated();
      } else {
        const error = await response.json();
        alert(`Failed to create room: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error creating room:', error);
      alert('Failed to create room');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-gray-900 rounded-2xl border border-gray-700 p-6 w-full max-w-md"
          >
        <h3 className="text-xl font-bold text-white mb-4">
          {parentId ? `Create Sub-Room in "${parentRoom?.name}"` : 'Create New Room'}
        </h3>
            
        <form onSubmit={handleSubmit} className="space-y-4">
              <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Room Name *
            </label>
                <input
                  type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., reflection, logbuch, thoughts"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
              required
              autoFocus
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description for this room"
              rows={2}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
                />
              </div>
              
              <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Discord Channel ID (optional)
            </label>
            <input
              type="text"
              value={discordChannelId}
              onChange={(e) => setDiscordChannelId(e.target.value)}
              placeholder="Paste Discord channel ID or link"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Future: Messages in this room will sync to Discord
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Discord Webhook URL (optional)
            </label>
                <input
                  type="text"
              value={discordWebhookUrl}
              onChange={(e) => setDiscordWebhookUrl(e.target.value)}
              placeholder="Paste Discord webhook URL"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
                />
            </div>
            
          <div className="flex gap-3 pt-2">
              <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-white transition-colors"
              >
                Cancel
              </button>
              <button
              type="submit"
              disabled={loading || !name.trim()}
              className="flex-1 px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors"
              >
              {loading ? 'Creating...' : 'Create Room'}
              </button>
            </div>
        </form>
          </motion.div>
    </div>
  );
};

export default RoomsScreen;
