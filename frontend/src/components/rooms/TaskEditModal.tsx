import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { motion } from 'framer-motion';

interface Task {
  task_id?: string;
  task_name: string;
  description?: string;
  schedule: string;
  time?: string;
  specific_date?: string;
  start_date?: string; // When the task should start (YYYY-MM-DD)
  days_of_week?: string[]; // ['monday', 'tuesday', ...]
  months_of_year?: number[]; // [1, 6, 12] for Jan, Jun, Dec - which months to run
  day_of_month?: number; // 1-31 for monthly/yearly tasks
  every_N_days?: number; // For "every_N_days" schedule
  every_N_minutes?: number; // For "every_N_minutes" schedule
  every_N_hours?: number; // For "every_N_hours" schedule
  every_N_weeks?: number; // For "every_N_weeks" schedule
  every_N_months?: number; // For "every_N_months" schedule
  every_N_years?: number; // For "every_N_years" schedule
  active: boolean;
  one_time: boolean;
  action_type: string;
  action_target?: string;
  action_template?: string;
}

const WEEKDAYS = [
  { id: 'monday', label: 'Mon', full: 'Monday' },
  { id: 'tuesday', label: 'Tue', full: 'Tuesday' },
  { id: 'wednesday', label: 'Wed', full: 'Wednesday' },
  { id: 'thursday', label: 'Thu', full: 'Thursday' },
  { id: 'friday', label: 'Fri', full: 'Friday' },
  { id: 'saturday', label: 'Sat', full: 'Saturday' },
  { id: 'sunday', label: 'Sun', full: 'Sunday' }
];

const MONTHS = [
  { id: 1, label: 'Jan', full: 'January' },
  { id: 2, label: 'Feb', full: 'February' },
  { id: 3, label: 'Mar', full: 'March' },
  { id: 4, label: 'Apr', full: 'April' },
  { id: 5, label: 'May', full: 'May' },
  { id: 6, label: 'Jun', full: 'June' },
  { id: 7, label: 'Jul', full: 'July' },
  { id: 8, label: 'Aug', full: 'August' },
  { id: 9, label: 'Sep', full: 'September' },
  { id: 10, label: 'Oct', full: 'October' },
  { id: 11, label: 'Nov', full: 'November' },
  { id: 12, label: 'Dec', full: 'December' }
];

// Main schedule types
const SCHEDULE_TYPES = [
  { id: 'daily', label: 'Daily', icon: '📅' },
  { id: 'weekly', label: 'Weekly', icon: '📆' },
  { id: 'monthly', label: 'Monthly', icon: '🗓️' },
  { id: 'yearly', label: 'Yearly', icon: '🎂' },
  { id: 'interval', label: 'Interval', icon: '⏰' },
  { id: 'on_date', label: 'One-time', icon: '📌' }
];

// Interval unit types
const INTERVAL_UNITS = [
  { id: 'minutes', label: 'Minutes', icon: '⏱️', max: 1440, default: 30 },
  { id: 'hours', label: 'Hours', icon: '🕐', max: 168, default: 1 },
  { id: 'days', label: 'Days', icon: '📅', max: 365, default: 3 },
  { id: 'weeks', label: 'Weeks', icon: '📆', max: 52, default: 1 },
  { id: 'months', label: 'Months', icon: '🗓️', max: 12, default: 1 }
];

// Action types - what kind of task is this?
const ACTION_TYPES = [
  { id: 'self_task', label: 'Self Task', icon: '🤖', description: 'Agent processes internally' },
  { id: 'channel_task', label: 'Channel Task', icon: '📢', description: 'Output to a specific channel' },
  { id: 'notification', label: 'Notification', icon: '🔔', description: 'Send a notification' }
];

// Default channel routing based on task name patterns
// All sub-channels are under 🪞 reflection
const DEFAULT_ROUTING: Record<string, { channel: string; subChannel?: string }> = {
  // Logbook tasks → 📝 logbook (under reflection)
  'logbook': { channel: '🪞 reflection', subChannel: '📝 logbook' },
  'daily_logbook': { channel: '🪞 reflection', subChannel: '📝 logbook' },
  
  // Rolling days → 🧠 memory-work (under reflection)  
  'rolling_days': { channel: '🪞 reflection', subChannel: '🧠 memory-work' },
  'rolling_days_update': { channel: '🪞 reflection', subChannel: '🧠 memory-work' },
  'rolling_days_archive': { channel: '🪞 reflection', subChannel: '🧠 memory-work' },
  
  // Analysis tasks → 🔍 analysis (under reflection)
  'analysis': { channel: '🪞 reflection', subChannel: '🔍 analysis' },
  '3_day_analysis': { channel: '🪞 reflection', subChannel: '🔍 analysis' },
  
  // Memory tasks → 🧠 memory-work (under reflection)
  'memory_hygiene': { channel: '🪞 reflection', subChannel: '🧠 memory-work' },
  'memory': { channel: '🪞 reflection', subChannel: '🧠 memory-work' },
  
  // Reflection tasks → main reflection channel
  'reflection': { channel: '🪞 reflection' },
  
  // Heartbeat tasks → heartbeat-log channel
  'heartbeat': { channel: '💓 heartbeat-log' },
};

// Helper function to get default routing for a task name
const getDefaultRouting = (taskName: string): { channel: string; subChannel?: string } | null => {
  const normalizedName = taskName.toLowerCase().replace(/[\s-]+/g, '_');
  
  // Check for exact matches first
  if (DEFAULT_ROUTING[normalizedName]) {
    return DEFAULT_ROUTING[normalizedName];
  }
  
  // Check for partial matches
  for (const [key, routing] of Object.entries(DEFAULT_ROUTING)) {
    if (normalizedName.includes(key) || key.includes(normalizedName)) {
      return routing;
    }
  }
  
  // Default to task channel for self tasks
  return { channel: '📋 task' };
};

interface Channel {
  id: string;
  name: string;
  parent_id?: string | null;
}

interface TaskEditModalProps {
  task: Task | null;
  messageId?: string; // Optional, only used for editing existing tasks
  onClose: () => void;
  onSave: (task: Task) => Promise<void>;
  agentId: string;
  channels?: Channel[]; // Available channels for routing
}

const TaskEditModal: React.FC<TaskEditModalProps> = ({ task, messageId, onClose, onSave, agentId, channels = [] }) => {
  // Get today's date in YYYY-MM-DD format
  const today = new Date().toISOString().split('T')[0];
  
  const [formData, setFormData] = useState<Task>({
    task_name: '',
    description: '',
    schedule: 'daily',
    time: '',
    start_date: today, // Default to today
    days_of_week: [],
    months_of_year: [],
    day_of_month: 1,
    every_N_days: 3,
    every_N_minutes: 30,
    every_N_hours: 1,
    every_N_weeks: 1,
    every_N_months: 1,
    every_N_years: 1,
    active: true,
    one_time: false,
    action_type: 'self_task',
    action_template: ''
  });
  const [loading, setLoading] = useState(false);
  
  // UI State for better UX
  const [scheduleType, setScheduleType] = useState<string>('daily');
  const [intervalUnit, setIntervalUnit] = useState<string>('days');
  const [intervalValue, setIntervalValue] = useState<number>(3);

  // Parse schedule to get type and interval info
  const parseSchedule = (schedule: string): { type: string; unit: string; value: number } => {
    if (schedule === 'daily' || schedule === 'weekly' || schedule === 'monthly' || schedule === 'yearly' || schedule === 'on_date') {
      return { type: schedule, unit: 'days', value: 1 };
    }
    if (schedule.startsWith('every_')) {
      const match = schedule.match(/every_(\d+)_(\w+)/);
      if (match) {
        return { type: 'interval', unit: match[2], value: parseInt(match[1]) };
      }
      // Handle every_N_X format
      if (schedule === 'every_N_minutes') return { type: 'interval', unit: 'minutes', value: 30 };
      if (schedule === 'every_N_hours') return { type: 'interval', unit: 'hours', value: 1 };
      if (schedule === 'every_N_days') return { type: 'interval', unit: 'days', value: 3 };
      if (schedule === 'every_N_weeks') return { type: 'interval', unit: 'weeks', value: 1 };
      if (schedule === 'every_N_months') return { type: 'interval', unit: 'months', value: 1 };
    }
    return { type: 'daily', unit: 'days', value: 1 };
  };

  useEffect(() => {
    if (task) {
      const parsed = parseSchedule(task.schedule || 'daily');
      setScheduleType(parsed.type);
      setIntervalUnit(parsed.unit);
      
      // Get interval value from the appropriate field
      let value = parsed.value;
      if (task.every_N_minutes) value = task.every_N_minutes;
      else if (task.every_N_hours) value = task.every_N_hours;
      else if (task.every_N_days) value = task.every_N_days;
      else if (task.every_N_weeks) value = task.every_N_weeks;
      else if (task.every_N_months) value = task.every_N_months;
      setIntervalValue(value);
      
      setFormData({
        task_id: task.task_id,
        task_name: task.task_name || '',
        description: task.description || '',
        schedule: task.schedule || 'daily',
        time: task.time || '',
        specific_date: task.specific_date,
        start_date: task.start_date || today,
        days_of_week: task.days_of_week || [],
        months_of_year: task.months_of_year || [],
        day_of_month: task.day_of_month || 1,
        every_N_days: task.every_N_days || 3,
        every_N_minutes: task.every_N_minutes || 30,
        every_N_hours: task.every_N_hours || 1,
        every_N_weeks: task.every_N_weeks || 1,
        every_N_months: task.every_N_months || 1,
        every_N_years: task.every_N_years || 1,
        active: task.active !== false,
        one_time: task.one_time || false,
        action_type: task.action_type || 'self_task',
        action_target: task.action_target,
        action_template: task.action_template || ''
      });
    }
  }, [task, today]);
  
  // Update formData.schedule when scheduleType or intervalUnit changes
  useEffect(() => {
    let newSchedule = scheduleType;
    if (scheduleType === 'interval') {
      newSchedule = `every_${intervalValue}_${intervalUnit}`;
    }
    setFormData(prev => ({ ...prev, schedule: newSchedule }));
  }, [scheduleType, intervalUnit, intervalValue]);
  
  // Toggle weekday selection
  const toggleWeekday = (dayId: string) => {
    setFormData(prev => {
      const currentDays = prev.days_of_week || [];
      const newDays = currentDays.includes(dayId)
        ? currentDays.filter(d => d !== dayId)
        : [...currentDays, dayId];
      return { ...prev, days_of_week: newDays };
    });
  };
  
  // Select all weekdays
  const selectAllWeekdays = () => {
    setFormData(prev => ({
      ...prev,
      days_of_week: WEEKDAYS.map(d => d.id)
    }));
  };
  
  // Clear all weekdays
  const clearWeekdays = () => {
    setFormData(prev => ({
      ...prev,
      days_of_week: []
    }));
  };
  
  // Toggle month selection
  const toggleMonth = (monthId: number) => {
    setFormData(prev => {
      const currentMonths = prev.months_of_year || [];
      const newMonths = currentMonths.includes(monthId)
        ? currentMonths.filter(m => m !== monthId)
        : [...currentMonths, monthId].sort((a, b) => a - b);
      return { ...prev, months_of_year: newMonths };
    });
  };
  
  // Select all months
  const selectAllMonths = () => {
    setFormData(prev => ({
      ...prev,
      months_of_year: MONTHS.map(m => m.id)
    }));
  };
  
  // Clear all months
  const clearMonths = () => {
    setFormData(prev => ({
      ...prev,
      months_of_year: []
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.task_name.trim()) return;

    setLoading(true);
    try {
      await onSave(formData);
      onClose();
    } catch (error) {
      console.error('Error saving task:', error);
      alert('Failed to save task');
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
        className="bg-gray-800 rounded-lg border border-gray-700 p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-white">Edit Task</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-700 rounded transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Task Name *
            </label>
            <input
              type="text"
              value={formData.task_name}
              onChange={(e) => setFormData({ ...formData, task_name: e.target.value })}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
              placeholder="Enter task name..."
              required
            />
            
            {/* Default Routing Display */}
            {formData.task_name && formData.action_type === 'self_task' && (
              <div className="mt-2 p-2 bg-gray-900/50 border border-gray-700/50 rounded-lg">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-400">📍 Default routing:</span>
                  {(() => {
                    const routing = getDefaultRouting(formData.task_name);
                    if (routing) {
                      return (
                        <span className="text-emerald-400 font-medium">
                          {routing.channel}
                          {routing.subChannel && (
                            <span className="text-gray-500"> → {routing.subChannel}</span>
                          )}
                        </span>
                      );
                    }
                    return <span className="text-gray-500">No default routing</span>;
                  })()}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  ℹ️ Self tasks are automatically routed based on task name
                </p>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
              placeholder="Enter description..."
              rows={2}
            />
          </div>

          {/* Schedule Type Selection - Clickable Buttons */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Schedule *
            </label>
            <div className="flex flex-wrap gap-2">
              {SCHEDULE_TYPES.map((type) => {
                const isSelected = scheduleType === type.id;
                return (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => setScheduleType(type.id)}
                    className={`
                      px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2
                      ${isSelected
                        ? 'bg-violet-600 text-white border-2 border-violet-400 shadow-lg shadow-violet-500/40'
                        : 'bg-gray-800 text-gray-400 border-2 border-gray-700 hover:border-violet-500/50 hover:text-gray-200'
                      }
                    `}
                  >
                    <span>{type.icon}</span>
                    <span>{type.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
          
          {/* Interval Configuration - Only shown when "Intervall" is selected */}
          {scheduleType === 'interval' && (
            <div className="mb-6 p-4 bg-gray-900/50 rounded-lg border border-gray-700">
              <label className="block text-sm font-medium text-gray-300 mb-3">
                ⏰ Interval Settings
              </label>
              
              {/* Interval Unit Buttons */}
              <div className="flex flex-wrap gap-2 mb-4">
                {INTERVAL_UNITS.map((unit) => {
                  const isSelected = intervalUnit === unit.id;
                  return (
                    <button
                      key={unit.id}
                      type="button"
                      onClick={() => {
                        setIntervalUnit(unit.id);
                        setIntervalValue(unit.default);
                      }}
                      className={`
                        px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5
                        ${isSelected
                          ? 'bg-cyan-600 text-white border-2 border-cyan-400 shadow-lg shadow-cyan-500/40'
                          : 'bg-gray-800 text-gray-400 border-2 border-gray-700 hover:border-cyan-500/50'
                        }
                      `}
                    >
                      <span>{unit.icon}</span>
                      <span>{unit.label}</span>
                    </button>
                  );
                })}
              </div>
              
              {/* Interval Value Input */}
              <div className="flex items-center gap-3">
                <span className="text-gray-400">Every</span>
                <input
                  type="number"
                  min="1"
                  max={INTERVAL_UNITS.find(u => u.id === intervalUnit)?.max || 100}
                  value={intervalValue}
                  onChange={(e) => setIntervalValue(parseInt(e.target.value) || 1)}
                  className="w-24 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-center focus:outline-none focus:ring-2 focus:ring-cyan-500"
                />
                <span className="text-gray-400">
                  {INTERVAL_UNITS.find(u => u.id === intervalUnit)?.label}
                </span>
              </div>
            </div>
          )}
          
          {/* Weekday Selection - For daily, weekly, interval */}
          {(scheduleType === 'daily' || scheduleType === 'weekly' || scheduleType === 'interval') && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <label className="block text-sm font-medium text-gray-300">
                  📅 Weekdays
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={selectAllWeekdays}
                    className="text-xs px-2 py-1 bg-violet-600/30 hover:bg-violet-600/50 text-violet-300 rounded transition-colors"
                  >
                    All
                  </button>
                  <button
                    type="button"
                    onClick={clearWeekdays}
                    className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
                  >
                    None
                  </button>
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                {WEEKDAYS.map((day) => {
                  // Bei "Täglich" leuchten ALLE Wochentage
                  const isSelected = scheduleType === 'daily' || (formData.days_of_week || []).includes(day.id);
                  return (
                    <button
                      key={day.id}
                      type="button"
                      onClick={() => toggleWeekday(day.id)}
                      disabled={scheduleType === 'daily'} // Bei Täglich nicht klickbar
                      className={`
                        w-12 h-12 rounded-lg text-sm font-bold transition-all
                        ${isSelected
                          ? 'bg-gradient-to-br from-violet-500 to-purple-600 text-white border-2 border-violet-400 shadow-lg shadow-violet-500/50 scale-105'
                          : 'bg-gray-800 text-gray-500 border-2 border-gray-700 hover:border-violet-500/50 hover:text-gray-300'
                        }
                        ${scheduleType === 'daily' ? 'cursor-default' : ''}
                      `}
                      title={day.full}
                    >
                      {day.label}
                    </button>
                  );
                })}
              </div>
              {scheduleType === 'daily' && (
                <p className="text-xs text-green-400 mt-2">
                  ✅ Daily = runs on all weekdays
                </p>
              )}
              {scheduleType !== 'daily' && (formData.days_of_week || []).length === 0 && (
                <p className="text-xs text-gray-500 mt-2">
                  ℹ️ No weekdays selected = runs every day
                </p>
              )}
            </div>
          )}
          
          {/* Start Date - When should the task start? (for recurring tasks) */}
          {scheduleType !== 'on_date' && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                🚀 Start Date
              </label>
              <input
                type="date"
                value={formData.start_date || today}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                className="w-48 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                ℹ️ When should this task start running? Default: today
              </p>
            </div>
          )}
          
          {/* Month Selection - For ALL recurring schedules (limit which months to run) */}
          {scheduleType !== 'on_date' && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <label className="block text-sm font-medium text-gray-300">
                  🗓️ Active Months <span className="text-xs text-gray-500">(optional)</span>
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={selectAllMonths}
                    className="text-xs px-2 py-1 bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 rounded transition-colors"
                  >
                    All
                  </button>
                  <button
                    type="button"
                    onClick={clearMonths}
                    className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
                  >
                    None
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-6 gap-2">
                {MONTHS.map((month) => {
                  const isSelected = (formData.months_of_year || []).includes(month.id);
                  return (
                    <button
                      key={month.id}
                      type="button"
                      onClick={() => toggleMonth(month.id)}
                      className={`
                        px-3 py-2 rounded-lg text-sm font-medium transition-all
                        ${isSelected
                          ? 'bg-gradient-to-br from-amber-500 to-orange-600 text-white border-2 border-amber-400 shadow-lg shadow-amber-500/40'
                          : 'bg-gray-800 text-gray-500 border-2 border-gray-700 hover:border-amber-500/50 hover:text-gray-300'
                        }
                      `}
                      title={month.full}
                    >
                      {month.label}
                    </button>
                  );
                })}
              </div>
              {(formData.months_of_year || []).length === 0 && (
                <p className="text-xs text-green-400 mt-2">
                  ✅ No months selected = runs every month (all year)
                </p>
              )}
              {(formData.months_of_year || []).length > 0 && (formData.months_of_year || []).length < 12 && (
                <p className="text-xs text-amber-400 mt-2">
                  ⚡ Only runs in {(formData.months_of_year || []).length} selected month(s)
                </p>
              )}
            </div>
          )}
          
          {/* Day of Month - For monthly and yearly */}
          {(scheduleType === 'monthly' || scheduleType === 'yearly') && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                📆 Day of Month
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min="1"
                  max="31"
                  value={formData.day_of_month || 1}
                  onChange={(e) => setFormData({ ...formData, day_of_month: parseInt(e.target.value) || 1 })}
                  className="w-20 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-center focus:outline-none focus:ring-2 focus:ring-violet-500"
                />
                <span className="text-gray-400">of the month</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                ℹ️ If 31 → last day if month has fewer days
              </p>
            </div>
          )}
          
          {/* Specific Date - For one-time */}
          {scheduleType === 'on_date' && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                📌 Date
              </label>
              <input
                type="date"
                value={formData.specific_date || ''}
                onChange={(e) => setFormData({ ...formData, specific_date: e.target.value, one_time: true })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                required={scheduleType === 'on_date'}
              />
            </div>
          )}
          
          {/* Time Selection - Not for minute/hour intervals */}
          {scheduleType !== 'on_date' && 
           !(scheduleType === 'interval' && (intervalUnit === 'minutes' || intervalUnit === 'hours')) && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                🕐 Time
              </label>
              <input
                type="time"
                value={formData.time}
                onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                className="w-40 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                ℹ️ Berlin timezone
              </p>
            </div>
          )}

          {/* Action Type Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-3">
              🎯 Task Type *
            </label>
            <div className="flex gap-2 flex-wrap">
              {ACTION_TYPES.map((type) => {
                const isSelected = formData.action_type === type.id;
                return (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => setFormData({ ...formData, action_type: type.id })}
                    className={`
                      px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2
                      ${isSelected
                        ? 'bg-gradient-to-br from-emerald-500 to-green-600 text-white border-2 border-emerald-400 shadow-lg shadow-emerald-500/40 scale-105'
                        : 'bg-gray-800 text-gray-400 border-2 border-gray-700 hover:border-emerald-500/50 hover:text-gray-300'
                      }
                    `}
                    title={type.description}
                  >
                    <span>{type.icon}</span>
                    <span>{type.label}</span>
                  </button>
                );
              })}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              {ACTION_TYPES.find(t => t.id === formData.action_type)?.description || ''}
            </p>
          </div>

          {/* Target Channel - For channel_task or self_task */}
          {(formData.action_type === 'channel_task' || formData.action_type === 'self_task') && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                📍 Output Channel {formData.action_type === 'channel_task' ? '*' : '(optional)'}
              </label>
              {channels.length > 0 ? (
                <select
                  value={formData.action_target || ''}
                  onChange={(e) => setFormData({ ...formData, action_target: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                  required={formData.action_type === 'channel_task'}
                >
                  <option value="">
                    {formData.action_type === 'self_task' 
                      ? '(Use default routing based on task name)' 
                      : 'Select a channel...'}
                  </option>
                  {channels.map((channel) => (
                    <option key={channel.id} value={channel.name}>
                      {channel.name}
                    </option>
                  ))}
                </select>
              ) : (
                <p className="text-xs text-amber-400">
                  ⚠️ No channels available. Create a channel first.
                </p>
              )}
              <p className="text-xs text-gray-500 mt-1">
                {formData.action_type === 'self_task' 
                  ? 'ℹ️ Leave empty to use default routing, or select a specific channel'
                  : 'ℹ️ Task output will be sent to this channel'}
              </p>
              {/* Show current action_target if set */}
              {formData.action_target && (
                <div className="mt-2 p-2 bg-emerald-900/30 border border-emerald-700/50 rounded-lg">
                  <p className="text-sm text-emerald-400">
                    <span className="font-medium">Current target:</span> {formData.action_target}
                  </p>
                </div>
              )}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              📝 Action Template</label>
            <textarea
              value={formData.action_template}
              onChange={(e) => setFormData({ ...formData, action_template: e.target.value })}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
              placeholder="Enter action template (what the agent should do)..."
              rows={4}
            />
          </div>

          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.active}
                onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                className="w-4 h-4 text-violet-600 bg-gray-900 border-gray-700 rounded focus:ring-violet-500"
              />
              <span className="text-sm text-gray-300">Active</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.one_time}
                onChange={(e) => setFormData({ ...formData, one_time: e.target.checked })}
                className="w-4 h-4 text-violet-600 bg-gray-900 border-gray-700 rounded focus:ring-violet-500"
              />
              <span className="text-sm text-gray-300">One-time</span>
            </label>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!formData.task_name.trim() || loading}
              className="flex-1 px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              {loading ? 'Saving...' : 'Save Task'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};

export default TaskEditModal;

