import React, { useState, useMemo } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';

interface Task {
  id: string;
  task_id?: string;
  task_name: string;
  description?: string;
  schedule: string;
  time?: string;
  specific_date?: string;
  next_run: string;
  active: boolean;
  one_time: boolean;
  action_type: string;
  action_target?: string;
  action_template?: string;
  days_of_week?: string[];
  every_N_days?: number;
}

interface TaskCalendarProps {
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  onDateClick?: (date: Date) => void;
}

// Helper: Check if task occurs on a specific date
const taskOccursOnDate = (task: Task, date: Date): boolean => {
  if (!task.active) return false;
  
  const schedule = task.schedule?.toLowerCase() || '';
  const dayOfWeek = date.getDay(); // 0 = Sunday, 6 = Saturday
  const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  
  // Daily tasks appear every day
  if (schedule === 'daily') {
    // Check days_of_week if specified
    if (task.days_of_week && task.days_of_week.length > 0) {
      return task.days_of_week.some(d => d.toLowerCase() === dayNames[dayOfWeek]);
    }
    return true;
  }
  
  // Weekly tasks appear on specific days
  if (schedule === 'weekly') {
    if (task.days_of_week && task.days_of_week.length > 0) {
      return task.days_of_week.some(d => d.toLowerCase() === dayNames[dayOfWeek]);
    }
    // Default to same day as next_run
    try {
      const nextRun = new Date(task.next_run);
      return nextRun.getDay() === dayOfWeek;
    } catch { return false; }
  }
  
  // For other schedules (every_N_days, etc.), just show on next_run
  try {
    const nextRun = new Date(task.next_run);
    return (
      nextRun.getDate() === date.getDate() &&
      nextRun.getMonth() === date.getMonth() &&
      nextRun.getFullYear() === date.getFullYear()
    );
  } catch { return false; }
}

// Color mapping for different task types
const getTaskColor = (task: Task): string => {
  const taskName = task.task_name.toLowerCase();
  
  if (taskName.includes('logbuch') || taskName.includes('daily')) {
    return 'bg-blue-500/80 border-blue-400';
  }
  if (taskName.includes('analyse') || taskName.includes('3-tage')) {
    return 'bg-purple-500/80 border-purple-400';
  }
  if (taskName.includes('archive') || taskName.includes('hygiene')) {
    return 'bg-yellow-500/80 border-yellow-400';
  }
  if (taskName.includes('rolling')) {
    return 'bg-green-500/80 border-green-400';
  }
  
  // Default color based on action_type
  switch (task.action_type) {
    case 'self_task':
      return 'bg-violet-500/80 border-violet-400';
    case 'user_reminder':
      return 'bg-pink-500/80 border-pink-400';
    case 'channel_post':
      return 'bg-cyan-500/80 border-cyan-400';
    default:
      return 'bg-gray-500/80 border-gray-400';
  }
};

const TaskCalendar: React.FC<TaskCalendarProps> = ({ tasks, onTaskClick, onDateClick }) => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  
  // Get first and last day of current month
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const daysInMonth = lastDay.getDate();
  const startingDayOfWeek = firstDay.getDay(); // 0 = Sunday, 1 = Monday, etc.
  
  // Adjust for Monday as first day (German calendar style)
  const adjustedStartingDay = startingDayOfWeek === 0 ? 6 : startingDayOfWeek - 1;
  
  // Get tasks for a specific date (using recurring logic)
  const getTasksForDate = (day: number): Task[] => {
    const date = new Date(year, month, day);
    return tasks.filter(task => taskOccursOnDate(task, date));
  };
  
  // Get tasks for selected date (for day view)
  const selectedDateTasks = useMemo(() => {
    if (!selectedDate) return [];
    return tasks.filter(task => taskOccursOnDate(task, selectedDate));
  }, [selectedDate, tasks]);
  
  // Navigate months
  const goToPreviousMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };
  
  const goToNextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };
  
  const goToToday = () => {
    setCurrentDate(new Date());
  };
  
  // Month names
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  
  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  
  const today = new Date();
  const isToday = (day: number) => {
    return (
      day === today.getDate() &&
      month === today.getMonth() &&
      year === today.getFullYear()
    );
  };
  
  // Handle day click
  const handleDayClick = (day: number) => {
    const clickedDate = new Date(year, month, day);
    setSelectedDate(clickedDate);
    if (onDateClick) {
      onDateClick(clickedDate);
    }
  };

  // Format selected date
  const formatSelectedDate = (date: Date) => {
    const weekDays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return `${weekDays[date.getDay()]}, ${date.getDate()}. ${monthNames[date.getMonth()]} ${date.getFullYear()}`;
  };

  return (
    <div className="flex gap-6">
      {/* Calendar */}
      <div className={`bg-gray-800/50 border border-gray-700 rounded-lg p-6 ${selectedDate ? 'flex-1' : 'w-full'}`}>
        {/* Calendar Header */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={goToPreviousMonth}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            title="Previous month"
          >
            <ChevronLeft className="w-5 h-5 text-gray-400" />
          </button>
          
          <div className="flex items-center gap-4">
            <h3 className="text-xl font-bold text-white">
              {monthNames[month]} {year}
            </h3>
            <button
              onClick={goToToday}
              className="px-3 py-1 text-sm bg-violet-600 hover:bg-violet-700 text-white rounded-lg transition-colors"
            >
              Today
            </button>
          </div>
          
          <button
            onClick={goToNextMonth}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            title="Next month"
          >
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        
        {/* Calendar Grid */}
        <div className="grid grid-cols-7 gap-2">
          {/* Day names header */}
          {dayNames.map((dayName) => (
            <div
              key={dayName}
              className="text-center text-sm font-semibold text-gray-400 py-2"
            >
              {dayName}
            </div>
          ))}
          
          {/* Empty cells for days before month starts */}
          {Array.from({ length: adjustedStartingDay }).map((_, index) => (
            <div key={`empty-${index}`} className="aspect-square" />
          ))}
          
          {/* Days of the month */}
          {Array.from({ length: daysInMonth }).map((_, index) => {
            const day = index + 1;
            const dayTasks = getTasksForDate(day);
            const isCurrentDay = isToday(day);
            const isSelected = selectedDate && 
              selectedDate.getDate() === day && 
              selectedDate.getMonth() === month && 
              selectedDate.getFullYear() === year;
            
            return (
              <motion.div
                key={day}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={`
                  aspect-square border rounded-lg p-1 cursor-pointer transition-all
                  ${isSelected
                    ? 'border-violet-400 bg-violet-500/30 ring-2 ring-violet-500/50'
                    : isCurrentDay 
                      ? 'border-violet-500 bg-violet-500/10' 
                      : 'border-gray-700 hover:border-gray-600'
                  }
                  hover:bg-gray-700/50
                `}
                onClick={() => handleDayClick(day)}
              >
                {/* Day number */}
                <div className={`
                  text-xs font-medium mb-1
                  ${isSelected ? 'text-violet-300' : isCurrentDay ? 'text-violet-400' : 'text-gray-300'}
                `}>
                  {day}
                </div>
                
                {/* Tasks indicator (compact when day view is open) */}
                <div className="space-y-0.5 max-h-[calc(100%-1.5rem)] overflow-y-auto">
                  {dayTasks.slice(0, selectedDate ? 2 : 3).map((task) => (
                    <motion.div
                      key={`${task.task_id || task.id}-${day}`}
                      initial={{ scale: 0.9 }}
                      animate={{ scale: 1 }}
                      className={`
                        ${getTaskColor(task)}
                        text-xs px-1 py-0.5 rounded border truncate
                        hover:opacity-80 cursor-pointer
                      `}
                      onClick={(e) => {
                        e.stopPropagation();
                        onTaskClick(task);
                      }}
                      title={task.task_name}
                    >
                      {selectedDate ? '' : task.task_name}
                    </motion.div>
                  ))}
                  {dayTasks.length > (selectedDate ? 2 : 3) && (
                    <div className="text-xs text-gray-400 px-1">
                      +{dayTasks.length - (selectedDate ? 2 : 3)}
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Day Detail View */}
      {selectedDate && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="w-80 bg-gray-800/50 border border-gray-700 rounded-lg p-6"
        >
          {/* Day View Header */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-white">
              {formatSelectedDate(selectedDate)}
            </h3>
            <button
              onClick={() => setSelectedDate(null)}
              className="p-1 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
              title="Close"
            >
              ✕
            </button>
          </div>
          
          {/* Tasks List */}
          <div className="space-y-3">
            {selectedDateTasks.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                Keine Tasks für diesen Tag
              </div>
            ) : (
              selectedDateTasks.map((task) => (
                <motion.div
                  key={task.task_id || task.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`
                    ${getTaskColor(task)}
                    p-3 rounded-lg border cursor-pointer
                    hover:opacity-90 transition-opacity
                  `}
                  onClick={() => onTaskClick(task)}
                >
                  <div className="font-medium text-white">{task.task_name}</div>
                  {task.time && (
                    <div className="text-sm text-white/80 mt-1">
                      🕐 {task.time} Uhr
                    </div>
                  )}
                  {task.description && (
                    <div className="text-sm text-white/70 mt-1 line-clamp-2">
                      {task.description}
                    </div>
                  )}
                  <div className="text-xs text-white/60 mt-2 flex gap-2">
                    <span className="bg-white/20 px-2 py-0.5 rounded">
                      {task.schedule}
                    </span>
                    {task.one_time && (
                      <span className="bg-red-500/30 px-2 py-0.5 rounded">
                        Einmalig
                      </span>
                    )}
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default TaskCalendar;

