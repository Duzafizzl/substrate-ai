import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Heart, X, Plus, Trash2, Clock, Save, ChevronDown, MousePointer2, Edit2 } from 'lucide-react';

interface HeartbeatRule {
  id: string;
  name?: string;       // Optional rule name (e.g., "Morning (Wake-up Check)")
  start_time: string;  // HH:MM
  end_time: string;    // HH:MM
  days: string[];      // ['monday', 'tuesday', ...]
  interval_minutes: number;
  probability: number; // 0.0 to 1.0
  color: string;       // Hex color
}

interface OnTopInformationTool {
  tool_name: string;
  function: string;
  enabled: boolean;
  display_name: string;
  format?: 'short' | 'full';
  params?: Record<string, any>;
}

interface OnTopInformation {
  enabled: boolean;
  tools: OnTopInformationTool[];
}

interface HeartbeatConfig {
  timezone: string;
  enabled: boolean;
  rules: HeartbeatRule[];
  default_message?: string;  // Optional: Custom heartbeat message
  on_top_information?: OnTopInformation;  // Optional: On Top Information config
}

interface HeartbeatConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: string;
}

// Drag state for clock handles
interface DragState {
  ruleId: string;
  handleType: 'start' | 'end';
}

// Predefined colors for rules (matching the design system)
const RULE_COLORS = [
  '#C6FF00', // limeGlow
  '#00F5A0', // aquaGlow
  '#9B5DE5', // violetGlow
  '#FF6B6B', // coral
  '#FFE66D', // yellow
  '#4ECDC4', // teal
  '#FF8C42', // orange
  '#95E1D3', // mint
];

const WEEKDAYS = [
  { id: 'monday', label: 'M', full: 'Monday' },
  { id: 'tuesday', label: 'T', full: 'Tuesday' },
  { id: 'wednesday', label: 'W', full: 'Wednesday' },
  { id: 'thursday', label: 'T', full: 'Thursday' },
  { id: 'friday', label: 'F', full: 'Friday' },
  { id: 'saturday', label: 'S', full: 'Saturday' },
  { id: 'sunday', label: 'S', full: 'Sunday' },
];

const TIMEZONES = [
  'Europe/Berlin',
  'Europe/London',
  'Europe/Paris',
  'America/New_York',
  'America/Los_Angeles',
  'America/Chicago',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
  'UTC',
];

// Convert time string (HH:MM) to angle (0-360)
const timeToAngle = (time: string): number => {
  const [hours, minutes] = time.split(':').map(Number);
  const totalMinutes = hours * 60 + minutes;
  return (totalMinutes / (24 * 60)) * 360 - 90; // -90 to start at top
};

// Convert angle to time string (HH:MM)
const angleToTime = (angle: number): string => {
  // Normalize angle to 0-360 range (add 90 because we offset by -90)
  let normalizedAngle = (angle + 90) % 360;
  if (normalizedAngle < 0) normalizedAngle += 360;
  
  const totalMinutes = Math.round((normalizedAngle / 360) * 24 * 60);
  const hours = Math.floor(totalMinutes / 60) % 24;
  const minutes = Math.round((totalMinutes % 60) / 5) * 5; // Round to 5-minute increments
  
  return `${hours.toString().padStart(2, '0')}:${(minutes % 60).toString().padStart(2, '0')}`;
};

// Generate UUID
const generateId = () => crypto.randomUUID();

export default function HeartbeatConfigModal({ isOpen, onClose, agentId }: HeartbeatConfigModalProps) {
  const [config, setConfig] = useState<HeartbeatConfig>({
    timezone: 'Europe/Berlin',
    enabled: true,
    rules: [],
    // default_message is optional - if not set, will be auto-generated with tool suggestions
    on_top_information: {
      enabled: false,
      tools: []
    }
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedRule, setSelectedRule] = useState<string | null>(null);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [creationMode, setCreationMode] = useState(false); // For click-to-create
  const [viewDay, setViewDay] = useState<string>('all'); // Filter rules by day
  const [editingField, setEditingField] = useState<'interval' | 'probability' | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  
  const svgRef = useRef<SVGSVGElement>(null);
  const intervalInputRef = useRef<HTMLInputElement>(null);
  const probabilityInputRef = useRef<HTMLInputElement>(null);

  // Calculate angle from mouse/touch position relative to SVG center
  const getAngleFromEvent = useCallback((clientX: number, clientY: number): number => {
    if (!svgRef.current) return 0;
    
    const rect = svgRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    const deltaX = clientX - centerX;
    const deltaY = clientY - centerY;
    
    // Calculate angle in degrees (atan2 returns radians)
    let angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI);
    
    return angle;
  }, []);

  // Handle drag move
  const handleDragMove = useCallback((clientX: number, clientY: number) => {
    if (!dragState) return;
    
    const angle = getAngleFromEvent(clientX, clientY);
    const time = angleToTime(angle);
    
    if (dragState.handleType === 'start') {
      updateRule(dragState.ruleId, { start_time: time });
    } else {
      updateRule(dragState.ruleId, { end_time: time });
    }
  }, [dragState, getAngleFromEvent]);

  // Mouse/touch event handlers
  useEffect(() => {
    if (!dragState) return;
    
    const handleMouseMove = (e: MouseEvent) => {
      e.preventDefault();
      handleDragMove(e.clientX, e.clientY);
    };
    
    const handleTouchMove = (e: TouchEvent) => {
      e.preventDefault();
      const touch = e.touches[0];
      handleDragMove(touch.clientX, touch.clientY);
    };
    
    const handleEnd = () => {
      setDragState(null);
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleEnd);
    window.addEventListener('touchmove', handleTouchMove, { passive: false });
    window.addEventListener('touchend', handleEnd);
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleEnd);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleEnd);
    };
  }, [dragState, handleDragMove]);

  // Start dragging a handle
  const startDrag = (ruleId: string, handleType: 'start' | 'end', e: React.MouseEvent | React.TouchEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setDragState({ ruleId, handleType });
    setSelectedRule(ruleId);
  };

  // Handle click on the clock (for creation mode)
  const handleClockClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!creationMode || dragState) return;
    
    const angle = getAngleFromEvent(e.clientX, e.clientY);
    const clickedTime = angleToTime(angle);
    
    // Calculate end time (1 hour after start, wrapped at 24h)
    const [hours, minutes] = clickedTime.split(':').map(Number);
    let endHours = hours + 2; // 2 hour default span
    if (endHours >= 24) endHours -= 24;
    const endTime = `${endHours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    
    // Create new rule at clicked position
    const colorIndex = config.rules.length % RULE_COLORS.length;
    const newRule: HeartbeatRule = {
      id: generateId(),
      name: '', // Optional name, can be set by user
      start_time: clickedTime,
      end_time: endTime,
      days: viewDay === 'all' 
        ? ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        : [viewDay], // Use current view day if filtering
      interval_minutes: 30,
      probability: 0.5,
      color: RULE_COLORS[colorIndex]
    };
    
    setConfig(prev => ({
      ...prev,
      rules: [...prev.rules, newRule]
    }));
    setSelectedRule(newRule.id);
    setCreationMode(false); // Exit creation mode after creating
  };

  // Load config on mount
  useEffect(() => {
    if (isOpen) {
      fetchConfig();
    }
  }, [isOpen, agentId]);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8284/api/agents/${agentId}/heartbeat/config`);
      if (response.ok) {
        const data = await response.json();
        // Ensure on_top_information exists with default structure
        if (!data.on_top_information) {
          data.on_top_information = {
            enabled: false,
            tools: []
          };
        }
        // default_message is optional - if not set, will be auto-generated
        // No need to set a default here, let backend handle it dynamically
        setConfig(data);
      }
    } catch (error) {
      console.error('Failed to fetch heartbeat config:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      console.log('💾 Saving heartbeat config:', {
        agentId,
        timezone: config.timezone,
        enabled: config.enabled,
        rulesCount: config.rules.length
      });
      
      const response = await fetch(`http://localhost:8284/api/agents/${agentId}/heartbeat/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('✅ Heartbeat config saved successfully:', result);
        
        // Show success message
        alert(`✅ Heartbeat rhythm saved!\n\nTimezone: ${config.timezone}\nEnabled: ${config.enabled ? 'Yes' : 'No'}\nRules: ${config.rules.length}\n\nThe rhythm will be applied immediately in daemon mode.`);
        
        onClose();
      } else {
        const error = await response.json();
        console.error('❌ Failed to save heartbeat config:', error);
        alert(`❌ Failed to save: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('❌ Failed to save heartbeat config:', error);
      alert(`❌ Failed to save heartbeat config: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  const addRule = () => {
    if (creationMode) {
      // If already in creation mode, create a default rule at a standard position
      const colorIndex = config.rules.length % RULE_COLORS.length;
      const newRule: HeartbeatRule = {
        id: generateId(),
        name: '', // Optional name, can be set by user
        start_time: '09:00',
        end_time: '18:00',
        days: viewDay === 'all' 
          ? ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
          : [viewDay],
        interval_minutes: 30,
        probability: 0.5,
        color: RULE_COLORS[colorIndex]
      };
      setConfig(prev => ({
        ...prev,
        rules: [...prev.rules, newRule]
      }));
      setSelectedRule(newRule.id);
      setCreationMode(false);
    } else {
      // Toggle creation mode - user can then click on the clock to create rule
      setCreationMode(true);
    }
  };

  const updateRule = (ruleId: string, updates: Partial<HeartbeatRule>) => {
    setConfig(prev => ({
      ...prev,
      rules: prev.rules.map(r => r.id === ruleId ? { ...r, ...updates } : r)
    }));
  };

  const deleteRule = (ruleId: string) => {
    setConfig(prev => ({
      ...prev,
      rules: prev.rules.filter(r => r.id !== ruleId)
    }));
    if (selectedRule === ruleId) {
      setSelectedRule(null);
    }
  };

  const toggleDay = (ruleId: string, day: string) => {
    const rule = config.rules.find(r => r.id === ruleId);
    if (!rule) return;
    
    const newDays = rule.days.includes(day)
      ? rule.days.filter(d => d !== day)
      : [...rule.days, day];
    
    updateRule(ruleId, { days: newDays });
  };

  // Edit mode handlers for interval and probability
  const startEditing = (field: 'interval' | 'probability') => {
    if (!selectedRuleData) return;
    
    setEditingField(field);
    if (field === 'interval') {
      setEditValue(selectedRuleData.interval_minutes.toString());
    } else {
      setEditValue(Math.round(selectedRuleData.probability * 100).toString());
    }
  };

  const saveEdit = () => {
    if (!selectedRuleData || !editingField) return;
    
    const numValue = parseInt(editValue);
    if (isNaN(numValue)) {
      // Invalid input, cancel edit
      setEditingField(null);
      return;
    }
    
    if (editingField === 'interval') {
      // Validate interval: 5-120 minutes, step 5
      const clamped = Math.max(5, Math.min(120, Math.round(numValue / 5) * 5));
      updateRule(selectedRuleData.id, { interval_minutes: clamped });
    } else {
      // Validate probability: 0-100, step 5
      const clamped = Math.max(0, Math.min(100, Math.round(numValue / 5) * 5));
      updateRule(selectedRuleData.id, { probability: clamped / 100 });
    }
    
    setEditingField(null);
  };

  const cancelEdit = () => {
    setEditingField(null);
    setEditValue('');
  };

  // Focus input when entering edit mode
  useEffect(() => {
    if (editingField === 'interval' && intervalInputRef.current) {
      intervalInputRef.current.focus();
      intervalInputRef.current.select();
    } else if (editingField === 'probability' && probabilityInputRef.current) {
      probabilityInputRef.current.focus();
      probabilityInputRef.current.select();
    }
  }, [editingField]);

  const selectedRuleData = config.rules.find(r => r.id === selectedRule);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="w-full max-w-4xl max-h-[90vh] bg-gray-900 rounded-2xl shadow-2xl border border-gray-700 overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between bg-gray-900/80 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-red-500 flex items-center justify-center">
                <Heart className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Heartbeat Rhythm</h2>
                <p className="text-xs text-gray-400">Configure autonomous heartbeat schedule</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left: Clock Visualization */}
                <div>
                  {/* Enable Toggle + Timezone */}
                  <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-xl border border-gray-700 mb-4">
                    <div className="flex items-center gap-3">
                      <label className="text-sm text-gray-300">Heartbeat Active</label>
                      <button
                        onClick={() => setConfig(prev => ({ ...prev, enabled: !prev.enabled }))}
                        className={`relative w-12 h-6 rounded-full transition-colors ${
                          config.enabled ? 'bg-limeGlow' : 'bg-gray-700'
                        }`}
                      >
                        <div
                          className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                            config.enabled ? 'translate-x-7' : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </div>
                    <select
                      value={config.timezone}
                      onChange={(e) => setConfig(prev => ({ ...prev, timezone: e.target.value }))}
                      className="px-3 py-1.5 bg-gray-800 border border-gray-600 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-purple-500"
                    >
                      {TIMEZONES.map(tz => (
                        <option key={tz} value={tz}>{tz}</option>
                      ))}
                    </select>
                  </div>

                  {/* Heartbeat Message */}
                  <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700 mb-4">
                    <label className="block text-sm text-gray-300 mb-2">
                      Heartbeat Message
                      <span className="text-xs text-gray-500 ml-2">(Optional: Customize the message sent during heartbeats)</span>
                    </label>
                    <textarea
                      value={config.default_message || ''}
                      onChange={(e) => setConfig(prev => ({ ...prev, default_message: e.target.value }))}
                      placeholder="Leave empty for auto-generated message with tool suggestions..."
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-purple-500 resize-y min-h-[80px] font-mono"
                      rows={4}
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      <strong>Empty = Auto-generated:</strong> If left empty, a generic message will be generated automatically based on your available tools (Discord, Spotify, Memory, Web Search, etc.). You can use {'{rule_name}'} or {'{rule_description}'} as placeholders.
                    </p>
                  </div>

                  {/* On Top Information */}
                  <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700 mb-4">
                    <div className="flex items-center justify-between mb-3">
                      <label className="block text-sm text-gray-300">
                        📊 On Top Information
                        <span className="text-xs text-gray-500 ml-2">(Show Spotify, Weather, Costs, etc. in heartbeat)</span>
                      </label>
                      <button
                        onClick={() => setConfig(prev => ({
                          ...prev,
                          on_top_information: {
                            ...(prev.on_top_information || { enabled: false, tools: [] }),
                            enabled: !(prev.on_top_information?.enabled ?? false)
                          }
                        }))}
                        className={`relative w-12 h-6 rounded-full transition-colors ${
                          config.on_top_information?.enabled ? 'bg-limeGlow' : 'bg-gray-700'
                        }`}
                      >
                        <div
                          className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                            config.on_top_information?.enabled ? 'translate-x-7' : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </div>
                    
                    {config.on_top_information?.enabled && (
                      <div className="space-y-2 mt-3">
                        {/* Available Tools */}
                        {[
                          { tool_name: 'spotify_control', function: 'get_now_playing', display_name: '🎵 Spotify (Now Playing)' },
                          { tool_name: 'cost_tracker', function: 'get_today_costs', display_name: '💰 API Costs (Today)' },
                          { tool_name: 'weather_tool', function: 'get_current_weather', display_name: '🌤️ Weather (Coming Soon)' },
                          { tool_name: 'power_consumption_tool', function: 'get_current_power', display_name: '⚡ Power Consumption (Custom)' }
                        ].map((availableTool) => {
                          const existingTool = config.on_top_information?.tools?.find(
                            t => t.tool_name === availableTool.tool_name && t.function === availableTool.function
                          );
                          const isEnabled = existingTool?.enabled ?? false;
                          
                          return (
                            <div
                              key={`${availableTool.tool_name}-${availableTool.function}`}
                              className="flex items-center justify-between p-2 bg-gray-900/50 rounded-lg border border-gray-700"
                            >
                              <span className="text-sm text-gray-300">{availableTool.display_name}</span>
                              <button
                                onClick={() => {
                                  const currentTools = config.on_top_information?.tools || [];
                                  const toolIndex = currentTools.findIndex(
                                    t => t.tool_name === availableTool.tool_name && t.function === availableTool.function
                                  );
                                  
                                  if (isEnabled) {
                                    // Remove tool
                                    setConfig(prev => ({
                                      ...prev,
                                      on_top_information: {
                                        ...(prev.on_top_information || { enabled: true, tools: [] }),
                                        tools: currentTools.filter((_, i) => i !== toolIndex)
                                      }
                                    }));
                                  } else {
                                    // Add tool
                                    const newTool: OnTopInformationTool = {
                                      ...availableTool,
                                      enabled: true,
                                      format: 'short'
                                    };
                                    setConfig(prev => ({
                                      ...prev,
                                      on_top_information: {
                                        ...(prev.on_top_information || { enabled: true, tools: [] }),
                                        tools: [...currentTools, newTool]
                                      }
                                    }));
                                  }
                                }}
                                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                                  isEnabled
                                    ? 'bg-limeGlow/20 text-limeGlow border border-limeGlow/50'
                                    : 'bg-gray-700 text-gray-400 border border-gray-600 hover:bg-gray-600'
                                }`}
                              >
                                {isEnabled ? '✓ Enabled' : '+ Enable'}
                              </button>
                            </div>
                          );
                        })}
                        
                        <p className="text-xs text-gray-500 mt-2">
                          Select which information to include in heartbeat messages. Information will be fetched automatically when heartbeat triggers.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Day Filter Dropdown */}
                  <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-xl border border-gray-700 mb-4">
                    <span className="text-sm text-gray-400">View day:</span>
                    <div className="relative">
                      <select
                        value={viewDay}
                        onChange={(e) => setViewDay(e.target.value)}
                        className="pl-3 pr-8 py-1.5 bg-gray-800 border border-gray-600 rounded-lg text-sm text-gray-200 appearance-none focus:outline-none focus:border-purple-500 cursor-pointer"
                      >
                        <option value="all">All Days</option>
                        {WEEKDAYS.map(day => (
                          <option key={day.id} value={day.id}>{day.full}</option>
                        ))}
                      </select>
                      <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                    </div>
                  </div>

                  {/* Add Rule Button */}
                  <button
                    onClick={addRule}
                    className={`relative z-20 w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-all mb-1 ${
                      creationMode
                        ? 'bg-purple-600 hover:bg-purple-500 border border-purple-400 text-white animate-pulse'
                        : 'bg-gray-800 hover:bg-gray-700 border border-gray-600 hover:border-purple-500 text-gray-300'
                    }`}
                  >
                    {creationMode ? (
                      <>
                        <MousePointer2 className="w-4 h-4" />
                        Click on Clock or Here for Default
                      </>
                    ) : (
                      <>
                        <Plus className="w-4 h-4" />
                        Add Time Rule
                      </>
                    )}
                  </button>
                  
                  {/* Cancel creation mode */}
                  {creationMode && (
                    <button
                      onClick={() => setCreationMode(false)}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 text-xs text-gray-500 hover:text-gray-300 transition-colors mb-1"
                    >
                      <X className="w-3 h-3" />
                      Cancel
                    </button>
                  )}

                  {/* Creation mode indicator - outside clock container */}
                  {creationMode && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="relative z-30 flex items-center justify-center mb-2"
                    >
                      <div className="px-3 py-1.5 bg-purple-600/90 rounded-full text-xs text-white font-medium shadow-lg">
                        <MousePointer2 className="inline w-3 h-3 mr-1" />
                        Click on clock to place rule
                      </div>
                    </motion.div>
                  )}

                  {/* 24-Hour Clock */}
                  <div className="relative z-10 aspect-square max-w-xl mx-auto px-12 pt-0 pb-4 -mt-16 overflow-visible pointer-events-none">
                    <svg
                      ref={svgRef}
                      viewBox="0 0 500 500"
                      className={`w-full h-full ${creationMode ? 'cursor-crosshair' : ''}`}
                      style={{ touchAction: 'none', pointerEvents: 'auto' }}
                      onClick={handleClockClick}
                    >
                      
                      {/* Background circle */}
                      <circle
                        cx="250"
                        cy="250"
                        r="180"
                        fill="none"
                        stroke="#374151"
                        strokeWidth="40"
                        className="opacity-50"
                      />

                      {/* Rule segments - filtered by selected day */}
                      {config.rules
                        .filter(rule => viewDay === 'all' || rule.days.includes(viewDay))
                        .map((rule) => {
                        const startAngle = timeToAngle(rule.start_time);
                        const endAngle = timeToAngle(rule.end_time);
                        
                        // Calculate arc path
                        const startRad = (startAngle * Math.PI) / 180;
                        const endRad = (endAngle * Math.PI) / 180;
                        const radius = 180;
                        const cx = 250, cy = 250;
                        
                        const x1 = cx + radius * Math.cos(startRad);
                        const y1 = cy + radius * Math.sin(startRad);
                        const x2 = cx + radius * Math.cos(endRad);
                        const y2 = cy + radius * Math.sin(endRad);
                        
                        // Determine if arc should be large (> 180 degrees)
                        let angleDiff = endAngle - startAngle;
                        if (angleDiff < 0) angleDiff += 360;
                        const largeArc = angleDiff > 180 ? 1 : 0;
                        
                        const isSelected = selectedRule === rule.id;
                        const isDragging = dragState?.ruleId === rule.id;

                        return (
                          <g key={rule.id}>
                            {/* Arc segment */}
                            <path
                              d={`M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`}
                              fill="none"
                              stroke={rule.color}
                              strokeWidth="40"
                              strokeLinecap="round"
                              className={`cursor-pointer transition-opacity ${
                                isSelected ? 'opacity-100' : 'opacity-70 hover:opacity-90'
                              }`}
                              onClick={() => setSelectedRule(rule.id)}
                            />
                            {/* Glow effect for selected */}
                            {isSelected && (
                              <path
                                d={`M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`}
                                fill="none"
                                stroke={rule.color}
                                strokeWidth="44"
                                strokeLinecap="round"
                                className="opacity-30"
                                style={{ filter: 'blur(4px)' }}
                              />
                            )}
                            
                            {/* Drag handle - START */}
                            <g
                              className="cursor-grab active:cursor-grabbing"
                              onMouseDown={(e) => startDrag(rule.id, 'start', e)}
                              onTouchStart={(e) => startDrag(rule.id, 'start', e)}
                            >
                              {/* Larger invisible hit area */}
                              <circle
                                cx={x1}
                                cy={y1}
                                r={20}
                                fill="transparent"
                                className="cursor-grab"
                              />
                              {/* Visible handle */}
                              <circle
                                cx={x1}
                                cy={y1}
                                r={isDragging && dragState.handleType === 'start' ? 14 : 12}
                                fill="#1F2937"
                                stroke={rule.color}
                                strokeWidth="3"
                                className={`transition-all ${
                                  isSelected || isDragging ? 'opacity-100' : 'opacity-0 hover:opacity-100'
                                }`}
                              />
                              {/* Inner dot */}
                              <circle
                                cx={x1}
                                cy={y1}
                                r={4}
                                fill={rule.color}
                                className={`transition-all ${
                                  isSelected || isDragging ? 'opacity-100' : 'opacity-0 hover:opacity-100'
                                }`}
                              />
                              {/* Time label for start */}
                              {(isSelected || isDragging) && (
                                <g>
                                  {/* Background rectangle for readability */}
                                  <rect
                                    x={(x1 + (x1 > 250 ? 25 : -25)) - 20}
                                    y={y1 - 8}
                                    width="40"
                                    height="16"
                                    rx="4"
                                    fill="#1F2937"
                                    fillOpacity="0.9"
                                    stroke={rule.color}
                                    strokeWidth="1.5"
                                  />
                                  <text
                                    x={x1 + (x1 > 250 ? 25 : -25)}
                                    y={y1}
                                    textAnchor="middle"
                                    dominantBaseline="middle"
                                    className="fill-white text-xs font-bold"
                                    style={{ fontSize: '11px', pointerEvents: 'none' }}
                                  >
                                    {rule.start_time}
                                  </text>
                                </g>
                              )}
                            </g>
                            
                            {/* Drag handle - END */}
                            <g
                              className="cursor-grab active:cursor-grabbing"
                              onMouseDown={(e) => startDrag(rule.id, 'end', e)}
                              onTouchStart={(e) => startDrag(rule.id, 'end', e)}
                            >
                              {/* Larger invisible hit area */}
                              <circle
                                cx={x2}
                                cy={y2}
                                r={20}
                                fill="transparent"
                                className="cursor-grab"
                              />
                              {/* Visible handle */}
                              <circle
                                cx={x2}
                                cy={y2}
                                r={isDragging && dragState.handleType === 'end' ? 14 : 12}
                                fill="#1F2937"
                                stroke={rule.color}
                                strokeWidth="3"
                                className={`transition-all ${
                                  isSelected || isDragging ? 'opacity-100' : 'opacity-0 hover:opacity-100'
                                }`}
                              />
                              {/* Inner dot */}
                              <circle
                                cx={x2}
                                cy={y2}
                                r={4}
                                fill={rule.color}
                                className={`transition-all ${
                                  isSelected || isDragging ? 'opacity-100' : 'opacity-0 hover:opacity-100'
                                }`}
                              />
                              {/* Time label for end */}
                              {(isSelected || isDragging) && (
                                <g>
                                  {/* Background rectangle for readability */}
                                  <rect
                                    x={(x2 + (x2 > 250 ? 25 : -25)) - 20}
                                    y={y2 - 8}
                                    width="40"
                                    height="16"
                                    rx="4"
                                    fill="#1F2937"
                                    fillOpacity="0.9"
                                    stroke={rule.color}
                                    strokeWidth="1.5"
                                  />
                                  <text
                                    x={x2 + (x2 > 250 ? 25 : -25)}
                                    y={y2}
                                    textAnchor="middle"
                                    dominantBaseline="middle"
                                    style={{ fontSize: '11px', pointerEvents: 'none' }}
                                    className="fill-white text-xs font-bold"
                                  >
                                    {rule.end_time}
                                  </text>
                                </g>
                              )}
                            </g>
                          </g>
                        );
                      })}

                      {/* Hour markers */}
                      {[...Array(24)].map((_, i) => {
                        const angle = ((i / 24) * 360 - 90) * (Math.PI / 180);
                        const innerRadius = 145;
                        const outerRadius = 155;
                        const textRadius = 130;
                        const x1 = 250 + innerRadius * Math.cos(angle);
                        const y1 = 250 + innerRadius * Math.sin(angle);
                        const x2 = 250 + outerRadius * Math.cos(angle);
                        const y2 = 250 + outerRadius * Math.sin(angle);
                        const tx = 250 + textRadius * Math.cos(angle);
                        const ty = 250 + textRadius * Math.sin(angle);
                        
                        return (
                          <g key={i}>
                            <line
                              x1={x1}
                              y1={y1}
                              x2={x2}
                              y2={y2}
                              stroke="#6B7280"
                              strokeWidth={i % 6 === 0 ? 2 : 1}
                            />
                            {i % 3 === 0 && (
                              <text
                                x={tx}
                                y={ty}
                                textAnchor="middle"
                                dominantBaseline="middle"
                                className="fill-gray-400 text-xs font-medium"
                                style={{ fontSize: '12px' }}
                              >
                                {i}
                              </text>
                            )}
                          </g>
                        );
                      })}

                      {/* Center circle */}
                      <circle
                        cx="250"
                        cy="250"
                        r="100"
                        fill="#1F2937"
                        stroke="#374151"
                        strokeWidth="2"
                      />

                      {/* Center text - Rules count */}
                      <text
                        x="250"
                        y="235"
                        textAnchor="middle"
                        className="fill-white text-lg font-semibold"
                        style={{ fontSize: '28px', fontWeight: '600' }}
                      >
                        {config.rules.filter(r => viewDay === 'all' || r.days.includes(viewDay)).length}
                      </text>
                      <text
                        x="250"
                        y="260"
                        textAnchor="middle"
                        className="fill-gray-400"
                        style={{ fontSize: '12px' }}
                      >
                        {config.rules.filter(r => viewDay === 'all' || r.days.includes(viewDay)).length === 1 ? 'Rule' : 'Rules'}
                      </text>
                      
                      {/* Status indicator */}
                      <text
                        x="250"
                        y="285"
                        textAnchor="middle"
                        className={config.enabled ? 'fill-limeGlow' : 'fill-gray-500'}
                        style={{ fontSize: '11px', fontWeight: '500' }}
                      >
                        {config.enabled ? '● Active' : '○ Disabled'}
                      </text>
                      
                      {/* Show selected rule info */}
                      {selectedRuleData && (
                        <text
                          x="250"
                          y="305"
                          textAnchor="middle"
                          className="fill-purple-400"
                          style={{ fontSize: '10px' }}
                        >
                          {selectedRuleData.start_time} - {selectedRuleData.end_time}
                        </text>
                      )}
                    </svg>
                  </div>
                </div>

                {/* Right: Rule Editor */}
                <div className="space-y-4">
                  {/* Rules List */}
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      Time Rules
                    </h3>
                    
                    {config.rules.length === 0 ? (
                      <div className="p-8 text-center bg-gray-800/30 rounded-xl border border-dashed border-gray-700">
                        <Heart className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                        <p className="text-sm text-gray-500">No rules configured</p>
                        <p className="text-xs text-gray-600 mt-1">Click "Add Time Rule" to create one</p>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-48 overflow-y-auto pr-2">
                        {config.rules.map((rule) => (
                          <div
                            key={rule.id}
                            onClick={() => setSelectedRule(rule.id)}
                            className={`p-3 rounded-lg border cursor-pointer transition-all ${
                              selectedRule === rule.id
                                ? 'bg-gray-800 border-purple-500'
                                : 'bg-gray-800/50 border-gray-700 hover:border-gray-600'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div
                                  className="w-3 h-3 rounded-full"
                                  style={{ backgroundColor: rule.color }}
                                />
                                <div className="flex flex-col">
                                  <span className="text-sm text-white font-medium">
                                    {rule.name || 'Rule'}
                                  </span>
                                  <span className="text-xs text-gray-400">
                                    {rule.start_time} - {rule.end_time}
                                  </span>
                                </div>
                              </div>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  deleteRule(rule.id);
                                }}
                                className="p-1 hover:bg-red-500/20 rounded transition-colors"
                              >
                                <Trash2 className="w-4 h-4 text-red-400" />
                              </button>
                            </div>
                            
                            {/* Day indicators - mini visual */}
                            <div className="flex items-center gap-1.5 mt-2">
                              {WEEKDAYS.map((day) => (
                                <div
                                  key={day.id}
                                  className={`w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold transition-all ${
                                    rule.days.includes(day.id)
                                      ? 'text-gray-900'
                                      : 'bg-gray-700/50 text-gray-600'
                                  }`}
                                  style={{
                                    backgroundColor: rule.days.includes(day.id) ? rule.color : undefined
                                  }}
                                  title={day.full}
                                >
                                  {day.label}
                                </div>
                              ))}
                              <span className="text-xs text-gray-500 ml-2">
                                {rule.interval_minutes}min • {Math.round(rule.probability * 100)}%
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Selected Rule Editor */}
                  {selectedRuleData && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="p-4 bg-gray-800/50 rounded-xl border border-gray-700 space-y-4"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-4 h-4 rounded-full"
                            style={{ backgroundColor: selectedRuleData.color }}
                          />
                          <h4 className="text-sm font-medium text-white">Edit Rule</h4>
                        </div>
                      </div>
                      
                      {/* Rule Name */}
                      <div>
                        <label className="text-xs text-gray-400 block mb-2">
                          Rule Name <span className="text-gray-600">(optional)</span>
                        </label>
                        <input
                          type="text"
                          placeholder="e.g., Morning (Wake-up Check)"
                          value={selectedRuleData.name || ''}
                          onChange={(e) => updateRule(selectedRuleData.id, { name: e.target.value || undefined })}
                          className="w-full px-3 py-2 bg-gray-900/50 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        />
                        <p className="text-xs text-gray-600 mt-1">
                          Give this rule a descriptive name (like in Discord bot)
                        </p>
                      </div>
                      
                      {/* Animated heartbeat preview - completely floating, no container */}
                      <motion.div
                        className="flex flex-col items-center my-2"
                        animate={{
                          scale: [1, 1 + (selectedRuleData.probability * 0.25), 1, 1 + (selectedRuleData.probability * 0.15), 1]
                        }}
                        transition={{
                          duration: Math.max(0.4, Math.min(2, selectedRuleData.interval_minutes / 20)),
                          repeat: Infinity,
                          ease: "easeInOut"
                        }}
                      >
                        {/* Heart SVG with integrated glow - no wrapper divs */}
                        <svg width="52" height="52" viewBox="0 0 24 24" style={{ overflow: 'visible' }}>
                          {/* Glow filter */}
                          <defs>
                            <filter id={`heartGlow-${selectedRuleData.id}`} x="-50%" y="-50%" width="200%" height="200%">
                              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                              <feMerge>
                                <feMergeNode in="coloredBlur"/>
                                <feMergeNode in="SourceGraphic"/>
                              </feMerge>
                            </filter>
                          </defs>
                          {/* Heart path */}
                          <path
                            d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
                            fill={selectedRuleData.color}
                            filter={`url(#heartGlow-${selectedRuleData.id})`}
                          />
                        </svg>
                      </motion.div>
                      
                      {/* Live stats - separate from heart animation */}
                      <div className="text-center">
                        <span 
                          className="text-sm font-semibold"
                          style={{ color: selectedRuleData.color }}
                        >
                          {selectedRuleData.interval_minutes}min
                        </span>
                        <span className="text-gray-500 mx-1">•</span>
                        <span 
                          className="text-sm font-semibold"
                          style={{ color: selectedRuleData.color }}
                        >
                          {Math.round(selectedRuleData.probability * 100)}%
                        </span>
                        <p className="text-[10px] text-gray-500 mt-0.5">
                          {selectedRuleData.interval_minutes <= 15 
                            ? 'Very frequent' 
                            : selectedRuleData.interval_minutes <= 30 
                              ? 'Regular rhythm' 
                              : selectedRuleData.interval_minutes <= 60 
                                ? 'Relaxed pace' 
                                : 'Slow & steady'}
                        </p>
                      </div>

                      {/* Time Range */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs text-gray-400 block mb-1">Start Time</label>
                          <input
                            type="time"
                            value={selectedRuleData.start_time}
                            onChange={(e) => updateRule(selectedRuleData.id, { start_time: e.target.value })}
                            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-sm text-white focus:outline-none focus:border-purple-500"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-400 block mb-1">End Time</label>
                          <input
                            type="time"
                            value={selectedRuleData.end_time}
                            onChange={(e) => updateRule(selectedRuleData.id, { end_time: e.target.value })}
                            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-sm text-white focus:outline-none focus:border-purple-500"
                          />
                        </div>
                      </div>

                      {/* Days - Enhanced UI */}
                      <div>
                        <label className="text-xs text-gray-400 block mb-2">Active Days</label>
                        
                        {/* Visual day circles */}
                        <div className="flex justify-between mb-3">
                          {WEEKDAYS.map((day, index) => {
                            const isActive = selectedRuleData.days.includes(day.id);
                            const isWeekend = index >= 5;
                            return (
                              <button
                                key={day.id}
                                onClick={() => toggleDay(selectedRuleData.id, day.id)}
                                className={`group relative w-9 h-9 rounded-full transition-all duration-200 ${
                                  isActive
                                    ? 'scale-110'
                                    : 'hover:scale-105'
                                }`}
                                style={{
                                  backgroundColor: isActive ? selectedRuleData.color : '#374151',
                                  boxShadow: isActive ? `0 0 15px ${selectedRuleData.color}50` : 'none'
                                }}
                                title={day.full}
                              >
                                <span className={`text-xs font-bold ${
                                  isActive ? 'text-gray-900' : isWeekend ? 'text-gray-500' : 'text-gray-400'
                                }`}>
                                  {day.label}
                                </span>
                                {/* Indicator ring on hover when not active */}
                                {!isActive && (
                                  <span 
                                    className="absolute inset-0 rounded-full border-2 opacity-0 group-hover:opacity-100 transition-opacity"
                                    style={{ borderColor: selectedRuleData.color }}
                                  />
                                )}
                              </button>
                            );
                          })}
                        </div>
                        
                        {/* Quick select buttons */}
                        <div className="flex gap-2">
                          <button
                            onClick={() => updateRule(selectedRuleData.id, { 
                              days: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'] 
                            })}
                            className={`flex-1 px-2 py-1.5 text-xs rounded-lg transition-all ${
                              selectedRuleData.days.length === 5 && 
                              !selectedRuleData.days.includes('saturday') && 
                              !selectedRuleData.days.includes('sunday')
                                ? 'bg-purple-600/30 text-purple-300 border border-purple-500'
                                : 'bg-gray-700 hover:bg-gray-600 text-gray-300 border border-transparent'
                            }`}
                          >
                            Mon-Fri
                          </button>
                          <button
                            onClick={() => updateRule(selectedRuleData.id, { 
                              days: ['saturday', 'sunday'] 
                            })}
                            className={`flex-1 px-2 py-1.5 text-xs rounded-lg transition-all ${
                              selectedRuleData.days.length === 2 && 
                              selectedRuleData.days.includes('saturday') && 
                              selectedRuleData.days.includes('sunday')
                                ? 'bg-purple-600/30 text-purple-300 border border-purple-500'
                                : 'bg-gray-700 hover:bg-gray-600 text-gray-300 border border-transparent'
                            }`}
                          >
                            Weekend
                          </button>
                          <button
                            onClick={() => updateRule(selectedRuleData.id, { 
                              days: WEEKDAYS.map(d => d.id) 
                            })}
                            className={`flex-1 px-2 py-1.5 text-xs rounded-lg transition-all ${
                              selectedRuleData.days.length === 7
                                ? 'bg-purple-600/30 text-purple-300 border border-purple-500'
                                : 'bg-gray-700 hover:bg-gray-600 text-gray-300 border border-transparent'
                            }`}
                          >
                            Every Day
                          </button>
                          <button
                            onClick={() => updateRule(selectedRuleData.id, { days: [] })}
                            className={`px-2 py-1.5 text-xs rounded-lg transition-all ${
                              selectedRuleData.days.length === 0
                                ? 'bg-red-600/30 text-red-300 border border-red-500'
                                : 'bg-gray-700 hover:bg-gray-600 text-gray-400 border border-transparent'
                            }`}
                            title="Clear all days"
                          >
                            ✕
                          </button>
                        </div>
                      </div>

                      {/* Interval */}
                      <div>
                        <label className="text-xs text-gray-400 flex items-center justify-between mb-2">
                          <span>Check Interval</span>
                          {editingField === 'interval' ? (
                            <input
                              ref={intervalInputRef}
                              type="number"
                              min="5"
                              max="120"
                              step="5"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={saveEdit}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  saveEdit();
                                } else if (e.key === 'Escape') {
                                  cancelEdit();
                                }
                              }}
                              className="w-16 px-2 py-0.5 text-purple-400 bg-gray-800 border border-purple-500 rounded text-xs text-right focus:outline-none focus:ring-2 focus:ring-purple-400"
                            />
                          ) : (
                            <button
                              type="button"
                              onClick={() => startEditing('interval')}
                              className="group flex items-center gap-1.5 px-2 py-0.5 text-purple-400 bg-gray-800/50 border border-gray-700 rounded hover:border-purple-500 hover:bg-gray-800 transition-all cursor-pointer"
                              title="Click to edit"
                            >
                              <span className="text-xs font-medium">{selectedRuleData.interval_minutes} min</span>
                              <Edit2 className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </button>
                          )}
                        </label>
                        <input
                          type="range"
                          min="5"
                          max="120"
                          step="5"
                          value={selectedRuleData.interval_minutes}
                          onChange={(e) => updateRule(selectedRuleData.id, { interval_minutes: parseInt(e.target.value) })}
                          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
                        />
                        <div className="flex justify-between text-xs text-gray-600 mt-1">
                          <span>5 min</span>
                          <span>60 min</span>
                          <span>120 min</span>
                        </div>
                      </div>

                      {/* Probability */}
                      <div>
                        <label className="text-xs text-gray-400 flex items-center justify-between mb-2">
                          <span>Trigger Probability</span>
                          {editingField === 'probability' ? (
                            <input
                              ref={probabilityInputRef}
                              type="number"
                              min="0"
                              max="100"
                              step="5"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={saveEdit}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  saveEdit();
                                } else if (e.key === 'Escape') {
                                  cancelEdit();
                                }
                              }}
                              className="w-16 px-2 py-0.5 text-limeGlow bg-gray-800 border border-limeGlow rounded text-xs text-right focus:outline-none focus:ring-2 focus:ring-limeGlow"
                            />
                          ) : (
                            <button
                              type="button"
                              onClick={() => startEditing('probability')}
                              className="group flex items-center gap-1.5 px-2 py-0.5 text-limeGlow bg-gray-800/50 border border-gray-700 rounded hover:border-limeGlow hover:bg-gray-800 transition-all cursor-pointer"
                              title="Click to edit"
                            >
                              <span className="text-xs font-medium">{Math.round(selectedRuleData.probability * 100)}%</span>
                              <Edit2 className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </button>
                          )}
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="5"
                          value={selectedRuleData.probability * 100}
                          onChange={(e) => updateRule(selectedRuleData.id, { probability: parseInt(e.target.value) / 100 })}
                          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-limeGlow"
                        />
                        <div className="flex justify-between text-xs text-gray-600 mt-1">
                          <span>Rarely</span>
                          <span>Sometimes</span>
                          <span>Always</span>
                        </div>
                      </div>

                      {/* Color */}
                      <div>
                        <label className="text-xs text-gray-400 block mb-2">Color</label>
                        <div className="flex gap-2">
                          {RULE_COLORS.map(color => (
                            <button
                              key={color}
                              onClick={() => updateRule(selectedRuleData.id, { color })}
                              className={`w-8 h-8 rounded-lg transition-all ${
                                selectedRuleData.color === color
                                  ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-800'
                                  : 'hover:scale-110'
                              }`}
                              style={{ backgroundColor: color }}
                            />
                          ))}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-700 flex items-center justify-end gap-3 bg-gray-900/80 backdrop-blur-sm">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={saveConfig}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50"
            >
              {saving ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

