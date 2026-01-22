"""
Daemon Mode - 24/7 Persistent Agent Runtime

Keeps agents running continuously with:
- Timer-based heartbeat rules (configurable per agent)
- Automatic task scheduling
- Channel-based message organization
- Connection pooling for instant response

Features:
- No restart overhead: agents stay warm in memory
- Continuous heartbeat with configurable rules
- Graceful shutdown with no data loss
- Error isolation per agent

Security:
- Resource limits prevent memory exhaustion
- Graceful error recovery
- Signal handling for clean shutdown
- Rate limiting per agent
"""

import os
import sys
import signal
import asyncio
import threading
import random
import json
import uuid
from typing import Dict, Optional, List, Tuple, TYPE_CHECKING
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from core.postgres_manager import PostgresManager
from core.message_continuity import PersistentMessageManager
from core.memory_coherence import MemoryCoherenceEngine

if TYPE_CHECKING:
    from core.consciousness_loop import ConsciousnessLoop


class SubstrateAIDaemonError(Exception):
    """Daemon mode errors"""
    pass


def _should_trigger_heartbeat(
    heartbeat_config: Dict, 
    rule_next_check_times: Dict[str, datetime],
    agent_name: str = "Agent"
) -> Tuple[bool, Optional[Dict], Dict[str, datetime]]:
    """
    Timer-based heartbeat logic:
    
    1. Calculate random interval (50-100% of configured interval)
    2. Wait for random interval
    3. Check probability when timer fires
    4. Reset timer regardless of fire/skip
    
    Returns:
        (should_trigger: bool, rule_info: Optional[Dict], updated_next_check_times: Dict)
    """
    if not heartbeat_config.get('enabled', True):
        return False, None, rule_next_check_times
    
    rules = heartbeat_config.get('rules', [])
    if not rules:
        return False, None, rule_next_check_times
    
    # Get current time in agent's timezone (DST-safe!)
    timezone_str = heartbeat_config.get('timezone', 'Europe/Berlin')
    try:
        tz = ZoneInfo(timezone_str)
    except:
        tz = ZoneInfo('Europe/Berlin')
    
    now = datetime.now(tz)
    current_time = now.strftime('%H:%M')
    current_day = now.strftime('%A').lower()
    
    # Find matching rule for current day and time
    matching_rule = None
    for rule in rules:
        days = rule.get('days', [])
        start_time = rule.get('start_time', '00:00')
        end_time = rule.get('end_time', '23:59')
        
        if current_day not in days:
            continue
        
        if start_time <= current_time <= end_time:
            matching_rule = rule
            break
    
    if not matching_rule:
        return False, None, rule_next_check_times
    
    rule_id = matching_rule.get('id')
    if not rule_id:
        return False, None, rule_next_check_times
    
    interval_minutes = matching_rule.get('interval_minutes', 60)
    probability = matching_rule.get('probability', 1.0)
    rule_name = matching_rule.get('name') or 'Rule'
    
    # Check if timer has fired
    next_check_time = rule_next_check_times.get(rule_id)
    
    if next_check_time is None or now >= next_check_time:
        # Timer fired! Check probability
        should_trigger = random.random() < probability
        
        # Calculate NEW random interval (50-100% of configured interval)
        min_interval = interval_minutes * 0.5
        max_interval = interval_minutes * 1.0
        random_interval = min_interval + random.random() * (max_interval - min_interval)
        random_interval_seconds = random_interval * 60
        
        # Set next check time
        new_next_check_time = now + timedelta(seconds=random_interval_seconds)
        rule_next_check_times[rule_id] = new_next_check_time
        
        rule_info = {
            'id': rule_id,
            'name': rule_name,
            'start_time': matching_rule.get('start_time'),
            'end_time': matching_rule.get('end_time'),
            'days': matching_rule.get('days'),
            'interval_minutes': interval_minutes,
            'probability': probability,
            'description': f"{rule_name} ({matching_rule.get('start_time')}-{matching_rule.get('end_time')}, {current_day})"
        }
        
        if should_trigger:
            print(f"💓 [{agent_name}] ✅ Heartbeat TRIGGERED | Rule: {rule_info['description']} | Next: {random_interval:.1f}min")
            return True, rule_info, rule_next_check_times
        else:
            print(f"💓 [{agent_name}] ⏭️  Heartbeat SKIPPED (probability) | Rule: {rule_info['description']} | Next: {random_interval:.1f}min")
            return False, rule_info, rule_next_check_times
    
    return False, None, rule_next_check_times


class AgentInstance:
    """
    In-memory agent instance with heartbeat support.
    """
    def __init__(
        self,
        agent_id: str,
        name: str,
        memory_engine: MemoryCoherenceEngine,
        message_manager: PersistentMessageManager,
        postgres_manager: Optional[PostgresManager] = None,
        consciousness_loop: Optional["ConsciousnessLoop"] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.memory_engine = memory_engine
        self.message_manager = message_manager
        self.postgres_manager = postgres_manager
        self.consciousness_loop = consciousness_loop
        
        # State
        self.last_heartbeat = datetime.now()
        self.message_count = 0
        self.created_at = datetime.now()
        
        # Timer-based heartbeat: next check time for each rule
        self.rule_next_check_times: Dict[str, datetime] = {}
        
        print(f"✅ AgentInstance created: {name} ({agent_id})")
    
    def get_heartbeat_config(self) -> Dict:
        """Load heartbeat config from PostgreSQL"""
        if not self.postgres_manager:
            return {}
        
        try:
            with self.postgres_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT config FROM agents WHERE id = %s", (self.agent_id,))
                row = cursor.fetchone()
                if row:
                    config_data = row[0]
                    if isinstance(config_data, str):
                        config_data = json.loads(config_data)
                    config = config_data if isinstance(config_data, dict) else {}
                    heartbeat_config = config.get('heartbeat_config', {})
                    cursor.close()
                    return heartbeat_config
                cursor.close()
        except Exception as e:
            print(f"⚠️  Failed to load heartbeat config: {e}")
        
        return {}
    
    def _generate_heartbeat_message(self) -> str:
        """Generate default heartbeat message"""
        return """[SYSTEM HEARTBEAT]

Presence check-in. You can:
• Use your available tools
• Organize memories
• Search for information
• Or simply process and reflect

You can choose to act or simply be present."""
    
    def _post_to_channel_and_thread(
        self,
        channel_name: str,
        content: str,
        role: str = 'system',
        metadata: Optional[Dict] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Post message to BOTH a channel AND the normal agent thread.
        
        CRITICAL: All channel messages MUST also appear in the main thread!
        """
        if not self.postgres_manager:
            return None, None
        
        try:
            with self.postgres_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                # Find channel
                cursor.execute("""
                    SELECT id FROM channels
                    WHERE agent_id = %s AND name LIKE %s
                    LIMIT 1
                """, (self.agent_id, f'%{channel_name}%'))
                
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    print(f"⚠️  Channel '{channel_name}' not found for agent '{self.agent_id}'")
                    return None, None
                
                channel_id = row[0]
                metadata_json = json.dumps(metadata or {})
                
                # Post to channel
                channel_message_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO messages (id, agent_id, session_id, role, content, created_at, channel_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s::jsonb)
                """, (channel_message_id, self.agent_id, channel_name, role, content, channel_id, metadata_json))
                
                # Also post to main thread
                thread_message_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO messages (id, agent_id, session_id, role, content, created_at, channel_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s::jsonb)
                """, (thread_message_id, self.agent_id, self.agent_id, role, content, channel_id, metadata_json))
                
                cursor.close()
                print(f"✅ Posted to '{channel_name}' AND main thread")
                return channel_message_id, thread_message_id
                
        except Exception as e:
            print(f"⚠️  Failed to post to channel: {e}")
            return None, None
    
    def heartbeat(self):
        """
        Agent heartbeat with timer-based rules.
        
        Only triggers if probability check passes.
        """
        heartbeat_config = self.get_heartbeat_config()
        
        # Check if heartbeat should trigger
        should_trigger, rule_info, updated_next_check_times = _should_trigger_heartbeat(
            heartbeat_config,
            self.rule_next_check_times,
            self.name
        )
        
        self.rule_next_check_times = updated_next_check_times
        
        if should_trigger:
            self.last_heartbeat = datetime.now()
            
            # Update in database
            if self.postgres_manager:
                self.postgres_manager.update_agent_heartbeat(self.agent_id)
            
            # Get heartbeat message
            content = heartbeat_config.get('default_message') or self._generate_heartbeat_message()
            
            # Build metadata
            timezone_str = heartbeat_config.get('timezone', 'Europe/Berlin')
            try:
                tz = ZoneInfo(timezone_str)
            except:
                tz = ZoneInfo('Europe/Berlin')
            
            now_tz = datetime.now(tz)
            metadata = {
                'heartbeat_event': True,
                'timestamp': now_tz.isoformat(),
                'timezone': timezone_str
            }
            
            if rule_info:
                metadata['rule_id'] = rule_info.get('id')
                metadata['rule_name'] = rule_info.get('name', 'Rule')
                metadata['rule_interval_minutes'] = rule_info.get('interval_minutes')
                metadata['rule_probability'] = rule_info.get('probability')
            
            # Post to heartbeat-log channel AND main thread
            self._post_to_channel_and_thread('heartbeat-log', content, 'system', metadata)
            
            # Process via ConsciousnessLoop if available
            if self.consciousness_loop:
                try:
                    self.consciousness_loop.agent_id = self.agent_id
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            self.consciousness_loop.process_message(
                                user_message=content,
                                session_id=self.agent_id,
                                model=None,
                                include_history=True,
                                history_limit=20,
                                message_type='heartbeat'
                            )
                        )
                        response_text = result.get('response', '')
                        print(f"💓 [{self.name}] ✅ Heartbeat processed | Response: {len(response_text)} chars")
                        
                        # Save response to heartbeat channel too
                        if response_text:
                            self._post_to_channel_and_thread('heartbeat-log', response_text, 'assistant', {'heartbeat_response': True})
                    finally:
                        loop.close()
                except Exception as e:
                    print(f"⚠️  [{self.name}] Failed to process heartbeat: {e}")
    
    def get_status(self) -> Dict:
        """Get agent status"""
        uptime = datetime.now() - self.created_at
        last_beat = datetime.now() - self.last_heartbeat
        
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "uptime_seconds": int(uptime.total_seconds()),
            "last_heartbeat_seconds": int(last_beat.total_seconds()),
            "message_count": self.message_count
        }


class SubstrateAIDaemon:
    """
    24/7 Daemon for Substrate AI - Always-On Agent Runtime.
    
    Features:
    - Timer-based heartbeat with configurable rules
    - Task scheduler integration
    - Channel-based message organization
    - Graceful shutdown
    """
    
    def __init__(
        self,
        postgres_manager: PostgresManager,
        heartbeat_interval: int = 15,  # Check every 15 seconds
        max_agents: int = 100,
        consciousness_loop: Optional["ConsciousnessLoop"] = None
    ):
        self.pg = postgres_manager
        self.heartbeat_interval = heartbeat_interval
        self.max_agents = max_agents
        self.consciousness_loop = consciousness_loop
        
        # Agent instances (in-memory cache)
        self.agents: Dict[str, AgentInstance] = {}
        
        # Managers
        self.message_manager = PersistentMessageManager(self.pg)
        
        # Task scheduler threads
        self.task_scheduler_threads: Dict[str, threading.Thread] = {}
        
        # State
        self.running = False
        self.heartbeat_thread: Optional[threading.Thread] = None
        
        # Signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print(f"✅ SubstrateAIDaemon initialized")
        print(f"   Heartbeat check interval: {heartbeat_interval}s")
        print(f"   Max agents: {max_agents}")
        if consciousness_loop:
            print(f"   ✅ Consciousness Loop enabled")
    
    def get_or_create_agent(
        self,
        agent_id: str,
        name: Optional[str] = None
    ) -> AgentInstance:
        """Get existing agent or create new one."""
        if agent_id in self.agents:
            return self.agents[agent_id]
        
        if len(self.agents) >= self.max_agents:
            raise SubstrateAIDaemonError(f"Max agents reached ({self.max_agents})")
        
        db_agent = self.pg.get_agent(agent_id)
        
        if not db_agent:
            if not name:
                name = f"Agent-{agent_id[:8]}"
            db_agent = self.pg.create_agent(agent_id, name)
        
        # Create memory engine
        memory_engine = MemoryCoherenceEngine(
            postgres_manager=self.pg,
            message_manager=self.message_manager
        )
        
        # Initialize core memory if needed
        core_memories = memory_engine.get_core_memory(agent_id)
        if not core_memories:
            memory_engine.initialize_default_core_memory(agent_id, db_agent.name)
            # Reload after initialization
            core_memories = memory_engine.get_core_memory(agent_id)
        
        # If this is ALEX, check if Alex-specific blocks exist, if not create them
        if db_agent.name.upper() == "ALEX" or "alex" in db_agent.name.lower():
            # Check if Alex-specific blocks exist
            alex_blocks = ['preferences', 'working_context', 'relationships', 'onboarding']
            existing_labels = {mem.label for mem in core_memories}
            missing_blocks = [label for label in alex_blocks if label not in existing_labels]
            
            if missing_blocks:
                print(f"📝 Alex-specific blocks missing: {missing_blocks}")
                print(f"   Creating Alex start memory blocks for agent {agent_id}...")
                try:
                    memory_engine.initialize_alex_start_memory(agent_id)
                    print(f"✅ Alex start memory blocks created")
                    # Reload after creation
                    core_memories = memory_engine.get_core_memory(agent_id)
                except Exception as e:
                    print(f"⚠️  Failed to initialize Alex start memory: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"✅ Alex-specific blocks already exist for agent {agent_id}")
        
        # Create default channels
        self.pg._create_default_channels(agent_id)
        
        # Create agent instance
        agent_instance = AgentInstance(
            agent_id=agent_id,
            name=db_agent.name,
            memory_engine=memory_engine,
            message_manager=self.message_manager,
            postgres_manager=self.pg,
            consciousness_loop=self.consciousness_loop
        )
        
        self.agents[agent_id] = agent_instance
        
        # Start task scheduler for this agent
        if self.consciousness_loop and agent_id not in self.task_scheduler_threads:
            from core.task_scheduler import start_task_scheduler
            start_task_scheduler(
                postgres_manager=self.pg,
                consciousness_loop=self.consciousness_loop,
                agent_id=agent_id,
                check_interval=60
            )
            self.task_scheduler_threads[agent_id] = threading.current_thread()
            print(f"🗓️  Task Scheduler started for agent {agent_id}")
        
        print(f"🚀 Agent loaded into daemon: {db_agent.name}")
        return agent_instance
    
    def remove_agent(self, agent_id: str):
        """Remove agent from memory (data stays in database)."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            print(f"👋 Removing agent from daemon: {agent.name}")
            del self.agents[agent_id]
    
    def _heartbeat_loop(self):
        """Continuous heartbeat loop - checks every N seconds."""
        print(f"💓 Heartbeat loop started (checking every {self.heartbeat_interval}s)")
        
        while self.running:
            try:
                for agent_id, agent in list(self.agents.items()):
                    try:
                        agent.heartbeat()
                    except Exception as e:
                        print(f"⚠️  Heartbeat failed for {agent.name}: {e}")
                
                threading.Event().wait(self.heartbeat_interval)
                
            except Exception as e:
                print(f"⚠️  Heartbeat loop error: {e}")
                threading.Event().wait(5)
    
    def start(self):
        """Start the daemon."""
        if self.running:
            print("⚠️  Daemon already running")
            return
        
        print(f"🚀 Starting SubstrateAIDaemon...")
        
        self.running = True
        
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="SubstrateAIHeartbeat"
        )
        self.heartbeat_thread.start()
        
        print(f"✅ SubstrateAIDaemon started!")
        print(f"   Status: RUNNING 🟢")
    
    def stop(self):
        """Stop the daemon gracefully."""
        if not self.running:
            print("⚠️  Daemon not running")
            return
        
        print(f"🛑 Stopping SubstrateAIDaemon...")
        
        self.running = False
        
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            print(f"⏳ Waiting for heartbeat thread...")
            self.heartbeat_thread.join(timeout=10)
        
        self.pg.close()
        
        agent_count = len(self.agents)
        self.agents.clear()
        
        print(f"✅ SubstrateAIDaemon stopped!")
        print(f"   Agents unloaded: {agent_count}")
        print(f"   Status: STOPPED 🔴")
    
    def restart(self):
        """Restart the daemon"""
        print(f"🔄 Restarting SubstrateAIDaemon...")
        self.stop()
        self.start()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        signal_names = {
            signal.SIGTERM: "SIGTERM",
            signal.SIGINT: "SIGINT"
        }
        signal_name = signal_names.get(signum, f"Signal {signum}")
        print(f"\n🛑 Received {signal_name} - shutting down...")
        self.stop()
        sys.exit(0)
    
    def get_status(self) -> Dict:
        """Get daemon status"""
        agent_statuses = [agent.get_status() for agent in self.agents.values()]
        
        return {
            "running": self.running,
            "agents_loaded": len(self.agents),
            "max_agents": self.max_agents,
            "heartbeat_interval": self.heartbeat_interval,
            "agents": agent_statuses
        }
    
    def print_status(self):
        """Print pretty status"""
        status = self.get_status()
        
        print(f"\n{'='*60}")
        print(f"🤖 SUBSTRATE AI DAEMON STATUS")
        print(f"{'='*60}")
        print(f"Running: {'🟢 YES' if status['running'] else '🔴 NO'}")
        print(f"Agents: {status['agents_loaded']}/{status['max_agents']}")
        print(f"Heartbeat Check: Every {status['heartbeat_interval']}s")
        
        if status['agents']:
            print(f"\n{'─'*60}")
            print(f"ACTIVE AGENTS:")
            for agent in status['agents']:
                uptime_min = agent['uptime_seconds'] // 60
                last_beat_sec = agent['last_heartbeat_seconds']
                print(f"  • {agent['name']} ({agent['agent_id'][:16]}...)")
                print(f"    Uptime: {uptime_min}m | Last heartbeat: {last_beat_sec}s ago")
        
        print(f"{'='*60}\n")


def create_daemon_from_env() -> Optional[SubstrateAIDaemon]:
    """Create daemon from environment variables."""
    from dotenv import load_dotenv
    load_dotenv()
    
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        print("⚠️  POSTGRES_PASSWORD not set - daemon disabled")
        return None
    
    try:
        pg = PostgresManager(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "substrate_ai"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=password
        )
        
        daemon = SubstrateAIDaemon(
            postgres_manager=pg,
            heartbeat_interval=int(os.getenv("DAEMON_HEARTBEAT_INTERVAL", "15")),
            max_agents=int(os.getenv("DAEMON_MAX_AGENTS", "100"))
        )
        
        return daemon
        
    except Exception as e:
        print(f"⚠️  Failed to create daemon: {e}")
        return None


if __name__ == "__main__":
    """Test daemon mode."""
    print("🧪 Testing SubstrateAIDaemon...")
    
    daemon = create_daemon_from_env()
    
    if not daemon:
        print("❌ Failed to create daemon")
        print("   Make sure POSTGRES_PASSWORD is set in .env")
        sys.exit(1)
    
    daemon.start()
    agent = daemon.get_or_create_agent("test-agent", "Test Agent")
    daemon.print_status()
    
    print(f"⏳ Running for 30 seconds (Ctrl+C to stop)...")
    
    try:
        import time
        time.sleep(30)
    except KeyboardInterrupt:
        print(f"\n🛑 Interrupted")
    
    daemon.print_status()
    daemon.stop()
    print("🎉 Test complete!")
