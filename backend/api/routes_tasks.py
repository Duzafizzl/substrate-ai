"""
Task API Routes - CRUD operations for scheduled tasks.

Tasks are scheduled actions that can be executed at specific times.
Supports various schedule types: daily, weekly, monthly, custom intervals.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo
from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

tasks_bp = Blueprint('tasks', __name__)

# Module-level managers (initialized via init_tasks_routes)
_postgres_manager = None
_state_manager = None


def init_tasks_routes(state_manager, postgres_manager=None):
    """Initialize tasks routes with state manager and postgres manager"""
    global _state_manager, _postgres_manager
    _state_manager = state_manager
    _postgres_manager = postgres_manager


# ============================================
# HELPER FUNCTIONS
# ============================================

def parse_time_in_berlin_then_utc(time_str: str, reference_date: datetime) -> datetime:
    """
    Parse a time string (HH:MM) as Berlin time and convert to UTC.
    
    Args:
        time_str: Time in format "HH:MM" (e.g. "14:00")
        reference_date: Reference date to attach the time to
        
    Returns:
        Datetime in UTC with the specified time (interpreted as Berlin time)
    """
    hour, minute = map(int, time_str.split(':'))
    
    # Get the date parts in Berlin timezone
    berlin_tz = ZoneInfo('Europe/Berlin')
    if reference_date.tzinfo is None:
        reference_date = reference_date.replace(tzinfo=ZoneInfo('UTC'))
    
    berlin_date = reference_date.astimezone(berlin_tz)
    berlin_date_str = berlin_date.strftime('%Y-%m-%d')
    
    # Create datetime in Berlin timezone
    berlin_datetime = datetime.strptime(f"{berlin_date_str} {hour:02d}:{minute:02d}", "%Y-%m-%d %H:%M")
    berlin_datetime = berlin_datetime.replace(tzinfo=berlin_tz)
    
    # Convert to UTC and return naive datetime
    utc_datetime = berlin_datetime.astimezone(ZoneInfo('UTC'))
    return utc_datetime.replace(tzinfo=None)


def calculate_next_run(
    schedule: str,
    current_time: datetime,
    time: Optional[str] = None
) -> datetime:
    """
    Calculate next_run for tasks.
    
    Args:
        schedule: Schedule type (e.g. "daily", "hourly", "every_3_hours")
        current_time: Current datetime
        time: Time in HH:MM format (for daily/weekly/monthly schedules)
        
    Returns:
        Next run datetime
    """
    now = current_time
    new_next = now
    has_time_field = time and len(time.split(':')) == 2
    
    if schedule == 'secondly':
        new_next = now + timedelta(seconds=1)
    elif schedule == 'minutely':
        new_next = now + timedelta(minutes=1)
    elif schedule == 'hourly':
        new_next = now + timedelta(hours=1)
    elif schedule == 'daily':
        new_next = now + timedelta(days=1)
        if has_time_field:
            new_next = parse_time_in_berlin_then_utc(time, new_next)
    elif schedule == 'weekly':
        new_next = now + timedelta(days=7)
        if has_time_field:
            new_next = parse_time_in_berlin_then_utc(time, new_next)
    elif schedule == 'monthly':
        new_next = now + timedelta(days=30)
        if has_time_field:
            new_next = parse_time_in_berlin_then_utc(time, new_next)
    elif schedule == 'yearly':
        new_next = now + timedelta(days=365)
        if has_time_field:
            new_next = parse_time_in_berlin_then_utc(time, new_next)
    elif schedule.startswith('every_') and schedule.endswith('_minutes'):
        minutes = int(schedule.replace('every_', '').replace('_minutes', ''))
        new_next = now + timedelta(minutes=minutes)
    elif schedule.startswith('every_') and schedule.endswith('_hours'):
        hours = int(schedule.replace('every_', '').replace('_hours', ''))
        new_next = now + timedelta(hours=hours)
    elif schedule.startswith('every_') and schedule.endswith('_days'):
        days = int(schedule.replace('every_', '').replace('_days', ''))
        new_next = now + timedelta(days=days)
        if has_time_field:
            new_next = parse_time_in_berlin_then_utc(time, new_next)
    elif schedule.startswith('every_') and schedule.endswith('_weeks'):
        weeks = int(schedule.replace('every_', '').replace('_weeks', ''))
        new_next = now + timedelta(weeks=weeks)
        if has_time_field:
            new_next = parse_time_in_berlin_then_utc(time, new_next)
    elif schedule.startswith('every_') and schedule.endswith('_months'):
        months = int(schedule.replace('every_', '').replace('_months', ''))
        new_next = now + timedelta(days=months * 30)
        if has_time_field:
            new_next = parse_time_in_berlin_then_utc(time, new_next)
    else:
        # Unknown schedule - default to 1 hour
        new_next = now + timedelta(hours=1)
    
    return new_next


# ============================================
# TASK ENDPOINTS
# ============================================

@tasks_bp.route('/api/tasks', methods=['GET'])
def list_tasks():
    """
    List tasks for an agent.
    
    Query params:
        - agent_id: Agent ID (default: 'default')
        - active_only: Only show active tasks (default: false)
        
    Returns: {tasks: [...], count: N}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        agent_id = request.args.get('agent_id', 'default')
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        
        # Resolve 'default' to actual agent ID
        if agent_id == 'default' and _state_manager:
            agent_state = _state_manager.get_agent_state()
            agent_id = agent_state.get('id', 'default')
        
        tasks = _postgres_manager.list_tasks(
            agent_id=agent_id,
            active_only=active_only
        )
        
        logger.info(f"📊 GET /api/tasks → {len(tasks)} tasks for agent '{agent_id}'")
        return jsonify({
            'tasks': tasks,
            'count': len(tasks)
        })
    
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/api/tasks', methods=['POST'])
def create_task():
    """
    Create a new task.
    
    Body: {
        task_name: string (required),
        schedule: string (required),
        description?: string,
        time?: string (HH:MM),
        specific_date?: string (YYYY-MM-DD or DD.MM.YYYY),
        days_of_week?: int[],
        every_N_days?: int,
        every_N_minutes?: int,
        every_N_hours?: int,
        every_N_weeks?: int,
        every_N_months?: int,
        months_of_year?: int[],
        start_date?: string (YYYY-MM-DD),
        active?: bool (default: true),
        one_time?: bool (default: false),
        action_type?: string (default: 'self_task'),
        action_target?: string,
        action_template?: string
    }
    
    Returns: {success: true, task: {...}}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        data = request.get_json()
        
        agent_id = data.get('agent_id', 'default')
        task_name = data.get('task_name')
        description = data.get('description')
        schedule = data.get('schedule')
        time = data.get('time')
        specific_date = data.get('specific_date')
        days_of_week = data.get('days_of_week', [])
        every_N_days = data.get('every_N_days')
        every_N_minutes = data.get('every_N_minutes')
        every_N_hours = data.get('every_N_hours')
        every_N_weeks = data.get('every_N_weeks')
        every_N_months = data.get('every_N_months')
        months_of_year = data.get('months_of_year', [])
        start_date = data.get('start_date')
        active = data.get('active', True)
        one_time = data.get('one_time', False)
        action_type = data.get('action_type', 'self_task')
        action_target = data.get('action_target')
        action_template = data.get('action_template')
        
        # Handle "every_N_*" schedules
        if schedule == 'every_N_minutes' and every_N_minutes:
            schedule = f'every_{every_N_minutes}_minutes'
        elif schedule == 'every_N_hours' and every_N_hours:
            schedule = f'every_{every_N_hours}_hours'
        elif schedule == 'every_N_days' and every_N_days:
            schedule = f'every_{every_N_days}_days'
        elif schedule == 'every_N_weeks' and every_N_weeks:
            schedule = f'every_{every_N_weeks}_weeks'
        elif schedule == 'every_N_months' and every_N_months:
            schedule = f'every_{every_N_months}_months'
        
        # Validate required fields
        if not task_name:
            return jsonify({'error': 'task_name is required'}), 400
        
        if not schedule:
            return jsonify({'error': 'schedule is required'}), 400
        
        # Resolve 'default' to actual agent ID
        if agent_id == 'default' and _state_manager:
            agent_state = _state_manager.get_agent_state()
            agent_id = agent_state.get('id', 'default')
        
        # Calculate next_run
        next_run = None
        
        if schedule == "on_date":
            if not specific_date:
                return jsonify({'error': 'specific_date is required for schedule=on_date'}), 400
            
            try:
                if '.' in specific_date:
                    day, month, year = specific_date.split('.')
                    date_obj = datetime(int(year), int(month), int(day))
                else:
                    date_obj = datetime.fromisoformat(specific_date)
                
                if time:
                    next_run = parse_time_in_berlin_then_utc(time, date_obj)
                else:
                    next_run = parse_time_in_berlin_then_utc("09:00", date_obj)
                
                if next_run < datetime.now():
                    return jsonify({'error': f'specific_date is in the past'}), 400
            except Exception as e:
                return jsonify({'error': f'Invalid date format: {e}'}), 400
        else:
            next_run = calculate_next_run(schedule, datetime.now(), time)
        
        # Create task in database
        task_id = _postgres_manager.create_task(
            agent_id=agent_id,
            task_name=task_name,
            description=description,
            schedule=schedule,
            time=time,
            next_run=next_run,
            active=active,
            one_time=one_time,
            action_type=action_type,
            action_target=action_target,
            action_template=action_template,
            days_of_week=days_of_week if days_of_week else None,
            every_N_days=every_N_days,
            months_of_year=months_of_year if months_of_year else None,
            start_date=start_date
        )
        
        # Duplicate protection
        if task_id is None:
            return jsonify({
                'error': f'Task with name "{task_name}" already exists for this agent',
                'duplicate': True
            }), 409
        
        # Get created task
        task = _postgres_manager.get_task(task_id)
        
        logger.info(f"✅ Created task '{task_name}' for agent '{agent_id}'")
        return jsonify({
            'success': True,
            'task': task
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """
    Get a specific task.
    
    Returns: {task_id, task_name, schedule, ...}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        task = _postgres_manager.get_task(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(task)
    
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    """
    Update a task.
    
    Body: {task_name?, description?, schedule?, time?, active?, ...}
    Returns: {success: true, task: {...}}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        data = request.get_json()
        
        # Build update dict
        update_kwargs = {}
        
        if 'task_name' in data:
            update_kwargs['task_name'] = data['task_name']
        if 'description' in data:
            update_kwargs['description'] = data['description']
        if 'schedule' in data:
            schedule = data['schedule']
            # Handle "every_N_*" schedules
            if schedule == 'every_N_minutes' and 'every_N_minutes' in data:
                schedule = f'every_{data["every_N_minutes"]}_minutes'
            elif schedule == 'every_N_hours' and 'every_N_hours' in data:
                schedule = f'every_{data["every_N_hours"]}_hours'
            elif schedule == 'every_N_days' and 'every_N_days' in data:
                schedule = f'every_{data["every_N_days"]}_days'
            elif schedule == 'every_N_weeks' and 'every_N_weeks' in data:
                schedule = f'every_{data["every_N_weeks"]}_weeks'
            elif schedule == 'every_N_months' and 'every_N_months' in data:
                schedule = f'every_{data["every_N_months"]}_months'
            update_kwargs['schedule'] = schedule
            
            # Recalculate next_run if schedule changed
            if schedule != "on_date":
                task = _postgres_manager.get_task(task_id)
                if task:
                    next_run = calculate_next_run(
                        schedule,
                        datetime.now(),
                        data.get('time') or task.get('time')
                    )
                    update_kwargs['next_run'] = next_run
        
        if 'time' in data:
            update_kwargs['time'] = data['time']
        if 'days_of_week' in data:
            update_kwargs['days_of_week'] = data['days_of_week']
        if 'every_N_days' in data:
            update_kwargs['every_N_days'] = data['every_N_days']
        if 'months_of_year' in data:
            update_kwargs['months_of_year'] = data['months_of_year']
        if 'start_date' in data:
            update_kwargs['start_date'] = data['start_date']
        if 'active' in data:
            update_kwargs['active'] = data['active']
        if 'action_type' in data:
            update_kwargs['action_type'] = data['action_type']
        if 'action_target' in data:
            update_kwargs['action_target'] = data['action_target']
        if 'action_template' in data:
            update_kwargs['action_template'] = data['action_template']
        
        if not update_kwargs:
            return jsonify({'error': 'No fields to update'}), 400
        
        updated = _postgres_manager.update_task(task_id, **update_kwargs)
        
        if not updated:
            return jsonify({'error': 'Task not found'}), 404
        
        task = _postgres_manager.get_task(task_id)
        
        logger.info(f"✅ Updated task {task_id}")
        return jsonify({
            'success': True,
            'task': task
        })
    
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """
    Delete a task.
    
    Returns: {success: true}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        deleted = _postgres_manager.delete_task(task_id)
        
        if not deleted:
            return jsonify({'error': 'Task not found'}), 404
        
        logger.info(f"✅ Deleted task {task_id}")
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/api/tasks/due', methods=['GET'])
def get_due_tasks():
    """
    Get all tasks that are due for execution.
    
    Query params:
        - agent_id: Agent ID (default: 'default')
        
    Returns: {tasks: [...], count: N}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        agent_id = request.args.get('agent_id', 'default')
        
        # Resolve 'default' to actual agent ID
        if agent_id == 'default' and _state_manager:
            agent_state = _state_manager.get_agent_state()
            agent_id = agent_state.get('id', 'default')
        
        tasks = _postgres_manager.get_due_tasks(agent_id)
        
        logger.info(f"📊 GET /api/tasks/due → {len(tasks)} due tasks for agent '{agent_id}'")
        return jsonify({
            'tasks': tasks,
            'count': len(tasks)
        })
    
    except Exception as e:
        logger.error(f"Error getting due tasks: {e}")
        return jsonify({'error': str(e)}), 500

