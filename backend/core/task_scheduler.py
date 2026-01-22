"""
Task Scheduler - Automatic Task Execution

Supports multiple schedule types:
- Daily: Run at specific time every day
- Weekly: Run on specific weekdays
- Monthly: Run on specific days of month
- Custom: Every N days, specific dates

Features:
- DST-safe timezone handling (Europe/Berlin default)
- Automatic next_run calculation
- One-time and recurring tasks
- Channel-based message organization
- Integration with ConsciousnessLoop
"""

import os
import json
import uuid
import threading
import asyncio
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from core.postgres_manager import PostgresManager

if TYPE_CHECKING:
    from core.consciousness_loop import ConsciousnessLoop


def calculate_next_run(
    schedule: str,
    time_str: Optional[str],
    days_of_week: Optional[List[int]] = None,
    every_n_days: Optional[int] = None,
    months_of_year: Optional[List[int]] = None,
    start_date: Optional[date] = None,
    timezone: str = 'Europe/Berlin'
) -> Optional[datetime]:
    """
    Calculate the next run time for a task.
    
    Schedule types:
    - 'daily': Every day at specified time
    - 'weekly': On specific days of week at specified time
    - 'monthly': On specific days of month at specified time
    - 'custom': Every N days from start_date
    - 'once': One-time at specified time
    
    Args:
        schedule: Schedule type
        time_str: Time in HH:MM format
        days_of_week: List of weekday numbers (0=Monday, 6=Sunday)
        every_n_days: Interval for custom schedule
        months_of_year: List of month numbers (1-12) - not yet implemented
        start_date: Start date for custom schedules
        timezone: Timezone string
    
    Returns:
        Next run datetime in UTC
    """
    try:
        tz = ZoneInfo(timezone)
    except:
        tz = ZoneInfo('Europe/Berlin')
    
    now_local = datetime.now(tz)
    
    # Parse time
    if time_str:
        try:
            hour, minute = map(int, time_str.split(':'))
        except:
            hour, minute = 0, 0
    else:
        hour, minute = now_local.hour, now_local.minute
    
    if schedule == 'daily':
        # Run every day at specified time
        next_run = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_run <= now_local:
            next_run += timedelta(days=1)
        
        return next_run.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
    
    elif schedule == 'weekly':
        # Run on specific days of week
        if not days_of_week:
            days_of_week = [0]  # Default to Monday
        
        current_weekday = now_local.weekday()
        next_run = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Find next valid day
        for i in range(7):
            check_day = (current_weekday + i) % 7
            
            if check_day in days_of_week:
                potential_run = next_run + timedelta(days=i)
                
                if potential_run > now_local:
                    return potential_run.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
        
        # If no day found, go to next week
        days_until = (days_of_week[0] - current_weekday + 7) % 7
        if days_until == 0:
            days_until = 7
        
        next_run = next_run + timedelta(days=days_until)
        return next_run.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
    
    elif schedule == 'monthly':
        # Run on specific days of month
        next_run = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_run <= now_local:
            # Move to next month
            if now_local.month == 12:
                next_run = next_run.replace(year=now_local.year + 1, month=1)
            else:
                next_run = next_run.replace(month=now_local.month + 1)
        
        return next_run.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
    
    elif schedule == 'custom':
        # Every N days from start_date
        if not every_n_days:
            every_n_days = 1
        
        if start_date:
            # Calculate next occurrence based on start_date
            start_datetime = datetime.combine(start_date, datetime.min.time())
            start_datetime = tz.localize(start_datetime) if hasattr(tz, 'localize') else start_datetime.replace(tzinfo=tz)
            start_datetime = start_datetime.replace(hour=hour, minute=minute)
            
            days_since_start = (now_local.date() - start_date).days
            cycles_completed = days_since_start // every_n_days
            
            next_run = start_datetime + timedelta(days=(cycles_completed + 1) * every_n_days)
            
            if next_run <= now_local:
                next_run += timedelta(days=every_n_days)
        else:
            # Simple interval from now
            next_run = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if next_run <= now_local:
                next_run += timedelta(days=every_n_days)
        
        return next_run.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
    
    elif schedule == 'once':
        # One-time execution
        next_run = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_run <= now_local:
            next_run += timedelta(days=1)
        
        return next_run.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
    
    return None


def _post_to_channel_and_thread(
    postgres_manager: PostgresManager,
    agent_id: str,
    channel_name: str,
    content: str,
    role: str = 'system',
    metadata: Optional[Dict] = None
) -> bool:
    """
    Post message to both a channel and the main thread.
    
    CRITICAL: All channel messages must also appear in the main thread!
    """
    try:
        with postgres_manager._get_connection() as conn:
            cursor = conn.cursor()
            
            # Find channel
            cursor.execute("""
                SELECT id FROM channels
                WHERE agent_id = %s AND name LIKE %s
                LIMIT 1
            """, (agent_id, f'%{channel_name}%'))
            
            row = cursor.fetchone()
            if not row:
                cursor.close()
                print(f"⚠️  Channel '{channel_name}' not found")
                return False
            
            channel_id = row[0]
            metadata_json = json.dumps(metadata or {})
            
            # Post to channel
            channel_message_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO messages (id, agent_id, session_id, role, content, created_at, channel_id, metadata)
                VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s::jsonb)
            """, (channel_message_id, agent_id, channel_name, role, content, channel_id, metadata_json))
            
            # Post to main thread
            thread_message_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO messages (id, agent_id, session_id, role, content, created_at, channel_id, metadata)
                VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s::jsonb)
            """, (thread_message_id, agent_id, agent_id, role, content, channel_id, metadata_json))
            
            cursor.close()
            return True
            
    except Exception as e:
        print(f"⚠️  Failed to post to channel: {e}")
        return False


def execute_task(
    postgres_manager: PostgresManager,
    consciousness_loop: "ConsciousnessLoop",
    task: Dict
) -> bool:
    """
    Execute a scheduled task.
    
    Supports action types:
    - self_task: Send message to agent (most common)
    - channel_message: Post to specific channel
    - system: Execute system action
    """
    agent_id = task.get('agent_id')
    task_name = task.get('task_name', 'Task')
    description = task.get('description', '')
    action_type = task.get('action_type', 'self_task')
    action_template = task.get('action_template', '')
    action_target = task.get('action_target', '')
    
    print(f"🗓️  Executing task: {task_name}")
    
    try:
        if action_type == 'self_task':
            # Build task message
            now = datetime.now()
            task_message = f"""[SCHEDULED TASK: {task_name}]

Time: {now.strftime('%Y-%m-%d %H:%M')}

{description}

{action_template or 'Please complete this task.'}"""
            
            # Post to task channel
            _post_to_channel_and_thread(
                postgres_manager,
                agent_id,
                'task',
                task_message,
                'system',
                {
                    'scheduled_task': True,
                    'task_name': task_name,
                    'task_id': task.get('id')
                }
            )
            
            # Process via consciousness loop
            consciousness_loop.agent_id = agent_id
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    consciousness_loop.process_message(
                        user_message=task_message,
                        session_id=agent_id,
                        model=None,
                        include_history=True,
                        history_limit=20,
                        message_type='task'
                    )
                )
                
                response_text = result.get('response', '')
                print(f"🗓️  Task '{task_name}' executed | Response: {len(response_text)} chars")
                
                # Save response to task channel
                if response_text:
                    _post_to_channel_and_thread(
                        postgres_manager,
                        agent_id,
                        'task',
                        response_text,
                        'assistant',
                        {'task_response': True, 'task_name': task_name}
                    )
                
                return True
            finally:
                loop.close()
        
        elif action_type == 'channel_message':
            # Post to specific channel
            target_channel = action_target or 'task'
            
            _post_to_channel_and_thread(
                postgres_manager,
                agent_id,
                target_channel,
                action_template or f'[Task: {task_name}] {description}',
                'system',
                {'scheduled_task': True, 'task_name': task_name}
            )
            
            return True
        
        else:
            print(f"⚠️  Unknown action type: {action_type}")
            return False
    
    except Exception as e:
        print(f"⚠️  Task execution failed: {e}")
        return False


def process_due_tasks(
    postgres_manager: PostgresManager,
    consciousness_loop: "ConsciousnessLoop",
    agent_id: Optional[str] = None
) -> int:
    """
    Process all due tasks.
    
    Args:
        postgres_manager: PostgreSQL manager
        consciousness_loop: Consciousness loop for processing
        agent_id: Optional - only process tasks for this agent
    
    Returns:
        Number of tasks processed
    """
    tasks = postgres_manager.get_due_tasks(agent_id)
    processed = 0
    
    for task in tasks:
        task_id = task.get('id')
        task_name = task.get('task_name', 'Unknown')
        one_time = task.get('one_time', False)
        
        print(f"🗓️  Processing due task: {task_name}")
        
        try:
            success = execute_task(postgres_manager, consciousness_loop, task)
            
            if success:
                processed += 1
                
                if one_time:
                    # Deactivate one-time task
                    postgres_manager.update_task(task_id, {'active': False})
                    print(f"🗓️  One-time task '{task_name}' deactivated")
                else:
                    # Calculate next run for recurring task
                    next_run = calculate_next_run(
                        schedule=task.get('schedule', 'daily'),
                        time_str=task.get('time'),
                        days_of_week=task.get('days_of_week'),
                        every_n_days=task.get('every_n_days'),
                        months_of_year=task.get('months_of_year'),
                        start_date=task.get('start_date'),
                        timezone='Europe/Berlin'
                    )
                    
                    if next_run:
                        postgres_manager.update_task(task_id, {'next_run': next_run})
                        print(f"🗓️  Task '{task_name}' next run: {next_run}")
        
        except Exception as e:
            print(f"⚠️  Failed to process task '{task_name}': {e}")
    
    return processed


class TaskScheduler:
    """
    Background task scheduler.
    
    Runs in a separate thread and checks for due tasks periodically.
    """
    
    def __init__(
        self,
        postgres_manager: PostgresManager,
        consciousness_loop: "ConsciousnessLoop",
        agent_id: Optional[str] = None,
        check_interval: int = 60
    ):
        self.pg = postgres_manager
        self.consciousness_loop = consciousness_loop
        self.agent_id = agent_id
        self.check_interval = check_interval
        
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        print(f"✅ TaskScheduler initialized")
        print(f"   Check interval: {check_interval}s")
        if agent_id:
            print(f"   Agent filter: {agent_id}")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        print(f"🗓️  Task scheduler started (checking every {self.check_interval}s)")
        
        while self.running:
            try:
                processed = process_due_tasks(
                    self.pg,
                    self.consciousness_loop,
                    self.agent_id
                )
                
                if processed > 0:
                    print(f"🗓️  Processed {processed} due task(s)")
                
                threading.Event().wait(self.check_interval)
                
            except Exception as e:
                print(f"⚠️  Scheduler error: {e}")
                threading.Event().wait(5)
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            print("⚠️  Scheduler already running")
            return
        
        self.running = True
        
        self.thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name=f"TaskScheduler-{self.agent_id or 'global'}"
        )
        self.thread.start()
        
        print(f"✅ Task scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        
        print(f"🛑 Task scheduler stopped")


# Global scheduler instances
_schedulers: Dict[str, TaskScheduler] = {}


def start_task_scheduler(
    postgres_manager: PostgresManager,
    consciousness_loop: "ConsciousnessLoop",
    agent_id: Optional[str] = None,
    check_interval: int = 60
) -> TaskScheduler:
    """
    Start a task scheduler (creates new or returns existing).
    
    Args:
        postgres_manager: PostgreSQL manager
        consciousness_loop: Consciousness loop for processing
        agent_id: Optional - only process tasks for this agent
        check_interval: Seconds between checks
    
    Returns:
        TaskScheduler instance
    """
    key = agent_id or 'global'
    
    if key in _schedulers:
        return _schedulers[key]
    
    scheduler = TaskScheduler(
        postgres_manager=postgres_manager,
        consciousness_loop=consciousness_loop,
        agent_id=agent_id,
        check_interval=check_interval
    )
    
    scheduler.start()
    _schedulers[key] = scheduler
    
    return scheduler


def stop_task_scheduler(agent_id: Optional[str] = None):
    """Stop a task scheduler"""
    key = agent_id or 'global'
    
    if key in _schedulers:
        _schedulers[key].stop()
        del _schedulers[key]


def stop_all_schedulers():
    """Stop all task schedulers"""
    for scheduler in _schedulers.values():
        scheduler.stop()
    _schedulers.clear()


if __name__ == "__main__":
    """Test task scheduler"""
    print("🧪 Testing TaskScheduler...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        print("❌ POSTGRES_PASSWORD not set")
        exit(1)
    
    pg = PostgresManager(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "substrate_ai"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=password
    )
    
    # Test next_run calculation
    print("\n📅 Testing next_run calculation...")
    
    next_daily = calculate_next_run('daily', '09:00')
    print(f"   Daily at 09:00: {next_daily}")
    
    next_weekly = calculate_next_run('weekly', '10:00', days_of_week=[0, 2, 4])  # Mon, Wed, Fri
    print(f"   Weekly Mon/Wed/Fri at 10:00: {next_weekly}")
    
    next_custom = calculate_next_run('custom', '12:00', every_n_days=3)
    print(f"   Every 3 days at 12:00: {next_custom}")
    
    print("\n🎉 Task Scheduler test complete!")

