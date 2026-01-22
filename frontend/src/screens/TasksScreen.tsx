import React, { useState, useEffect, useRef } from 'react';
import { ArrowLeft, Calendar, Plus, Edit, Trash2, CheckCircle, XCircle, List, Grid } from 'lucide-react';
import { motion } from 'framer-motion';
import TaskEditModal from '../components/rooms/TaskEditModal';
import TaskContextMenu from '../components/rooms/TaskContextMenu';
import TaskCalendar from '../components/tasks/TaskCalendar';

interface Task {
  id: string;
  task_id?: string;
  task_name: string;
  description?: string;
  schedule: string;
  time?: string;
  specific_date?: string;
  days_of_week?: string[];
  every_N_days?: number;
  every_N_minutes?: number;
  every_N_hours?: number;
  every_N_weeks?: number;
  every_N_months?: number;
  every_N_years?: number;
  next_run: string;
  active: boolean;
  one_time: boolean;
  action_type: string;
  action_target?: string;
  action_template?: string;
  created_at?: string;
  updated_at?: string;
}

interface Channel {
  id: string;
  name: string;
  parent_id?: string | null;
}

interface TasksScreenProps {
  onBack: () => void;
  agentId?: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8284';

const TasksScreen: React.FC<TasksScreenProps> = ({ onBack, agentId = 'default' }) => {
  const currentAgentId = agentId;
  
  const [tasks, setTasks] = useState<Task[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateTaskModal, setShowCreateTaskModal] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [taskContextMenu, setTaskContextMenu] = useState<{ taskId: string; messageId: string; x: number; y: number } | null>(null);
  const [viewMode, setViewMode] = useState<'calendar' | 'list'>('calendar');
  const tasksEndRef = useRef<HTMLDivElement>(null);
  
  // Load tasks
  useEffect(() => {
    loadTasks();
    
    // Poll for updates every 5 seconds
    const interval = setInterval(() => {
      loadTasks();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [currentAgentId]);
  
  // Auto-scroll to bottom
  useEffect(() => {
    if (tasksEndRef.current) {
      tasksEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [tasks]);
  
  const loadTasks = async () => {
    try {
      let tasks: Task[] = [];
      
      // 🔥 Read tasks from task channel (like Discord bot!)
      // First, get task channel ID
      const channelsResponse = await fetch(`${API_URL}/api/channels?agent_id=${currentAgentId}`);
      if (channelsResponse.ok) {
        const channelsData = await channelsResponse.json();
        
        // Save channels for task routing dropdown
        if (channelsData.channels) {
          setChannels(channelsData.channels);
        }
        
        const taskChannel = channelsData.channels?.find((ch: any) => 
          ch.name === '📋 task' && !ch.parent_id
        );
        
        if (taskChannel) {
          // Read messages from task channel
          const messagesResponse = await fetch(`${API_URL}/api/channels/${taskChannel.id}/messages?limit=100`);
          if (messagesResponse.ok) {
            const messagesData = await messagesResponse.json();
            
            // Parse tasks from messages (JSON in code blocks)
            const parsedTasks: Task[] = [];
            const taskMessages = messagesData.messages || [];
            
            for (const msg of taskMessages) {
              if (msg.metadata?.is_task_definition && msg.metadata?.task_id) {
                // Extract JSON from message content
                const jsonMatch = msg.content.match(/```json\s*(\{[\s\S]*?\})\s*```/);
                if (jsonMatch) {
                  try {
                    const taskJson = JSON.parse(jsonMatch[1]);
                    parsedTasks.push({
                      id: taskJson.task_id,
                      task_id: taskJson.task_id,
                      task_name: taskJson.task_name,
                      description: taskJson.description,
                      schedule: taskJson.schedule,
                      time: taskJson.time,
                      specific_date: taskJson.specific_date,
                      days_of_week: taskJson.days_of_week || [],
                      every_N_days: taskJson.every_N_days,
                      next_run: taskJson.next_run,
                      active: taskJson.active !== false,
                      one_time: taskJson.one_time || false,
                      action_type: taskJson.action_type || 'self_task',
                      action_target: taskJson.action_target,
                      action_template: taskJson.action_template,
                      created_at: msg.created_at,
                      updated_at: msg.created_at
                    });
                  } catch (e) {
                    console.error('Error parsing task JSON:', e);
                  }
                }
              }
            }
            
            tasks = parsedTasks;
          }
        }
      }
      
      // Fallback: Also try API endpoint (for backwards compatibility)
      // Only use fallback if no tasks found in channel
      if (tasks.length === 0) {
        const response = await fetch(`${API_URL}/api/tasks?agent_id=${currentAgentId}`);
        if (response.ok) {
          const data = await response.json();
          if (data.tasks && data.tasks.length > 0) {
            tasks = data.tasks;
          }
        }
      }
      
      setTasks(tasks);
    } catch (error) {
      console.error('Error loading tasks:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleDeleteTask = async (taskId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/tasks/${taskId}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        loadTasks(); // Reload tasks
      } else {
        alert('Failed to delete task');
      }
    } catch (error) {
      console.error('Error deleting task:', error);
      alert('Failed to delete task');
    }
  };
  
  const handleEditTask = async (taskData: any) => {
    if (!taskData.task_id && !taskData.id) return;
    
    const taskId = taskData.task_id || taskData.id;
    const response = await fetch(`${API_URL}/api/tasks/${taskId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_name: taskData.task_name,
        description: taskData.description,
        schedule: taskData.schedule,
        time: taskData.time,
        specific_date: taskData.specific_date,
        days_of_week: taskData.days_of_week || [],
        every_N_days: taskData.every_N_days,
        every_N_minutes: taskData.every_N_minutes,
        every_N_hours: taskData.every_N_hours,
        every_N_weeks: taskData.every_N_weeks,
        every_N_months: taskData.every_N_months,
        every_N_years: taskData.every_N_years,
        active: taskData.active,
        one_time: taskData.one_time,
        action_type: taskData.action_type,
        action_target: taskData.action_target,
        action_template: taskData.action_template
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to save task');
    }
    
    loadTasks(); // Reload tasks
  };
  
  const handleCreateTask = async (taskData: any) => {
    const response = await fetch(`${API_URL}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: currentAgentId,
        task_name: taskData.task_name,
        description: taskData.description,
        schedule: taskData.schedule,
        time: taskData.time,
        specific_date: taskData.specific_date,
        days_of_week: taskData.days_of_week || [],
        every_N_days: taskData.every_N_days,
        every_N_minutes: taskData.every_N_minutes,
        every_N_hours: taskData.every_N_hours,
        every_N_weeks: taskData.every_N_weeks,
        every_N_months: taskData.every_N_months,
        every_N_years: taskData.every_N_years,
        active: taskData.active,
        one_time: taskData.one_time,
        action_type: taskData.action_type,
        action_target: taskData.action_target,
        action_template: taskData.action_template
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to create task');
    }
    
    loadTasks(); // Reload tasks
  };
  
  const formatNextRun = (nextRun: string) => {
    try {
      const date = new Date(nextRun);
      return date.toLocaleString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return nextRun;
    }
  };
  
  return (
    <div className="min-h-screen flex flex-col bg-gray-950">
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-gray-900/50 border-b border-gray-800 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              title="Back to home"
            >
              <ArrowLeft className="w-5 h-5 text-gray-400" />
            </button>
            
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-violet-400" />
              <div>
                <h2 className="text-lg font-bold text-white">Plan/Task</h2>
                <p className="text-xs text-gray-400">Task Scheduler & Management</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
              <button
                onClick={() => setViewMode('calendar')}
                className={`p-2 rounded transition-colors ${
                  viewMode === 'calendar'
                    ? 'bg-violet-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
                title="Calendar view"
              >
                <Grid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded transition-colors ${
                  viewMode === 'list'
                    ? 'bg-violet-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
                title="List view"
              >
                <List className="w-4 h-4" />
              </button>
            </div>
            
            <button
              onClick={() => setShowCreateTaskModal(true)}
              className="px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg transition-colors flex items-center gap-2 text-sm"
              title="Create new task"
            >
              <Plus className="w-4 h-4" />
              <span>Create Task</span>
            </button>
          </div>
        </div>
        
        {/* Tasks View */}
        <div className="flex-1 overflow-y-auto bg-gray-950">
          <div className="max-w-6xl mx-auto p-4">
            {loading ? (
              <div className="text-center text-gray-400 py-8">Loading tasks...</div>
            ) : tasks.length === 0 ? (
              <div className="text-center text-gray-400 py-12">
                <Calendar className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                <p className="text-sm mb-4">No tasks yet. Create your first task!</p>
                <button
                  onClick={() => setShowCreateTaskModal(true)}
                  className="px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg transition-colors"
                >
                  Create Task
                </button>
              </div>
            ) : viewMode === 'calendar' ? (
              /* Calendar View */
              <TaskCalendar
                tasks={tasks}
                onTaskClick={(task) => {
                  setEditingTask(task);
                }}
              />
            ) : (
              /* List View */
              <div className="space-y-4 py-4">
                {tasks.map((task) => {
                  const taskId = task.task_id || task.id;
                  const isActive = task.active;
                  
                  return (
                    <motion.div
                      key={taskId}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 hover:border-violet-500/50 transition-colors"
                      onContextMenu={(e) => {
                        e.preventDefault();
                        setTaskContextMenu({
                          taskId,
                          messageId: taskId,
                          x: e.clientX,
                          y: e.clientY
                        });
                      }}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h3 className="text-lg font-bold text-white">{task.task_name}</h3>
                            {isActive ? (
                              <CheckCircle className="w-4 h-4 text-green-400" />
                            ) : (
                              <XCircle className="w-4 h-4 text-gray-500" />
                            )}
                            {task.one_time && (
                              <span className="px-2 py-0.5 text-xs bg-yellow-500/20 text-yellow-400 rounded-full">
                                One-time
                              </span>
                            )}
                          </div>
                          
                          {task.description && (
                            <p className="text-sm text-gray-400 mb-2">{task.description}</p>
                          )}
                          
                          <div className="flex flex-wrap gap-4 text-xs text-gray-500">
                            <span>Schedule: <span className="text-gray-300">{task.schedule}</span></span>
                            {task.time && (
                              <span>Time: <span className="text-gray-300">{task.time}</span></span>
                            )}
                            <span>Next Run: <span className="text-gray-300">{formatNextRun(task.next_run)}</span></span>
                            <span>Type: <span className="text-gray-300">{task.action_type}</span></span>
                            {task.action_target && (
                              <span>→ <span className="text-emerald-400 font-medium">{task.action_target}</span></span>
                            )}
                          </div>
                          
                          {task.action_template && (
                            <div className="mt-3 p-2 bg-gray-900/50 rounded border border-gray-700">
                              <p className="text-xs text-gray-400 mb-1">Action Template:</p>
                              <p className="text-sm text-gray-300">{task.action_template}</p>
                            </div>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setEditingTask(task)}
                            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                            title="Edit task"
                          >
                            <Edit className="w-4 h-4 text-gray-400 hover:text-violet-400" />
                          </button>
                          <button
                            onClick={() => {
                              if (confirm('Are you sure you want to delete this task?')) {
                                handleDeleteTask(taskId);
                              }
                            }}
                            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                            title="Delete task"
                          >
                            <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-400" />
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
                <div ref={tasksEndRef} className="h-32" />
              </div>
            )}
          </div>
        </div>
      </main>
      
      {/* Task Context Menu */}
      {taskContextMenu && (
        <TaskContextMenu
          taskId={taskContextMenu.taskId}
          messageId={taskContextMenu.messageId}
          x={taskContextMenu.x}
          y={taskContextMenu.y}
          onClose={() => setTaskContextMenu(null)}
          onEdit={async (taskId) => {
            try {
              const response = await fetch(`${API_URL}/api/tasks/${taskId}`);
              if (response.ok) {
                const task = await response.json();
                setEditingTask(task);
              }
            } catch (error) {
              console.error('Error loading task:', error);
            }
          }}
          onDelete={handleDeleteTask}
        />
      )}
      
      {/* Task Edit Modal */}
      {editingTask && (
        <TaskEditModal
          task={editingTask}
          onClose={() => setEditingTask(null)}
          onSave={handleEditTask}
          agentId={currentAgentId}
          channels={channels}
        />
      )}
      
      {/* Create Task Modal */}
      {showCreateTaskModal && (
        <TaskEditModal
          task={null}
          onClose={() => setShowCreateTaskModal(false)}
          onSave={handleCreateTask}
          agentId={currentAgentId}
          channels={channels}
        />
      )}
    </div>
  );
};

export default TasksScreen;

