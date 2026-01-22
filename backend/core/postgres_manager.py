"""
PostgreSQL Manager with Coherence Magic!

Persistent storage layer for Substrate AI agents.

Production-grade persistence architecture.
Implementation: Original code by Substrate AI Contributors.

Features:
- Normalized schema (agents, messages, memories)
- pgvector support for semantic search
- Message continuity across restarts
- Automatic compaction and summarization
- Full state coherence: Everything stays connected!

Security: SQL injection prevention via parameterized queries
"""

import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass

try:
    import psycopg2
    from psycopg2 import pool, extras
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("⚠️  psycopg2 not installed. Run: pip install psycopg2-binary")


@dataclass
class Agent:
    """Agent metadata"""
    id: str
    name: str
    created_at: datetime
    last_heartbeat: Optional[datetime] = None
    config: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "config": self.config or {}
        }


@dataclass
class Message:
    """Conversation message with full persistence"""
    id: str
    agent_id: str
    session_id: str
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    created_at: datetime
    tool_calls: Optional[Dict] = None
    tool_results: Optional[Dict] = None
    thinking: Optional[str] = None  # Native reasoning!
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "thinking": self.thinking,
            "metadata": self.metadata or {}
        }


@dataclass
class Memory:
    """Memory block with pgvector embedding support"""
    id: str
    agent_id: str
    memory_type: str  # 'core', 'archival', 'recall'
    label: str  # e.g., 'persona', 'human', or custom
    content: str
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "memory_type": self.memory_type,
            "label": self.label,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tags": self.tags or [],
            "metadata": self.metadata or {}
        }


class PostgresManagerError(Exception):
    """PostgreSQL manager errors"""
    def __init__(self, message: str, context: Optional[Dict] = None):
        self.context = context or {}
        full_message = f"PostgresManagerError: {message}"
        if context:
            full_message += f"\nContext: {json.dumps(context, indent=2)}"
        super().__init__(full_message)


class PostgresManager:
    """
    PostgreSQL Manager with Full State Coherence.
    
    Features:
    - Normalized schema (agents, messages, memories)
    - pgvector for semantic search (FAST!)
    - Connection pooling (no restart overhead!)
    - Message continuity across restarts
    - Automatic compaction/summarization
    
    Security:
    - Parameterized queries (SQL injection prevention)
    - Connection pooling with limits
    - Transaction management with rollback
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "substrate_ai",
        user: str = "postgres",
        password: str = "",
        min_connections: int = 1,
        max_connections: int = 10
    ):
        """
        Initialize PostgreSQL manager with connection pooling.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
        
        Security: Uses connection pooling to prevent connection exhaustion attacks
        """
        if not POSTGRES_AVAILABLE:
            raise PostgresManagerError(
                "psycopg2 not available. Install: pip install psycopg2-binary"
            )
        
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        
        # Create database if it doesn't exist
        self._ensure_database_exists()
        
        # Initialize connection pool (keep connections warm for performance!)
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                min_connections,
                max_connections,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=10
            )
            print(f"✅ PostgreSQL Connection Pool initialized")
            print(f"   Database: {database}@{host}:{port}")
            print(f"   Pool: {min_connections}-{max_connections} connections")
        except psycopg2.Error as e:
            raise PostgresManagerError(
                f"Failed to create connection pool: {str(e)}",
                context={"host": host, "database": database}
            )
        
        # Initialize schema
        self._init_schema()
        
        print(f"✅ PostgresManager ready - Coherence Engine activated!")
    
    def _ensure_database_exists(self):
        """
        Create database if it doesn't exist.
        
        Security: Uses AUTOCOMMIT to prevent transaction issues during DB creation
        """
        try:
            # Connect to postgres database to create our database
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database="postgres",  # Connect to default postgres DB
                user=self.user,
                password=self.password
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.database,)
            )
            
            if not cursor.fetchone():
                # Create database
                print(f"📦 Creating database: {self.database}")
                cursor.execute(f"CREATE DATABASE {self.database}")
                print(f"✅ Database created: {self.database}")
            
            cursor.close()
            conn.close()
        except psycopg2.Error as e:
            raise PostgresManagerError(
                f"Failed to ensure database exists: {str(e)}",
                context={"database": self.database}
            )
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections from pool.
        
        Security: Automatic rollback on error, ensures connection returns to pool
        """
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
            conn.commit()
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            raise PostgresManagerError(
                f"Database operation failed: {str(e)}",
                context={"database": self.database}
            )
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def _init_schema(self):
        """
        Initialize database schema with pgvector support.
        
        Schema design with normalized approach.
        Security: All tables use proper constraints and indexes.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Enable pgvector extension (for embeddings!)
            # Note: This requires pgvector to be installed on PostgreSQL
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                print("✅ pgvector extension enabled")
            except psycopg2.Error:
                print("⚠️  pgvector extension not available - embeddings will be stored as JSONB")
                print("   Install: https://github.com/pgvector/pgvector")
            
            # 1. AGENTS TABLE
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    last_heartbeat TIMESTAMP,
                    config JSONB DEFAULT '{}'
                )
            """)
            
            # 2. MESSAGES TABLE (Full conversation history!)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    tool_calls JSONB,
                    tool_results JSONB,
                    thinking TEXT,
                    metadata JSONB DEFAULT '{}'
                )
            """)
            
            # Index for fast message retrieval
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_agent_session 
                ON messages(agent_id, session_id, created_at DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_created_at 
                ON messages(created_at DESC)
            """)
            
            # 3. MEMORIES TABLE (Core + Archival + Recall!)
            # Try with vector type, fall back to JSONB if pgvector not available
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                        memory_type TEXT NOT NULL CHECK (memory_type IN ('core', 'archival', 'recall')),
                        label TEXT NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector(1536),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        tags TEXT[],
                        metadata JSONB DEFAULT '{}'
                    )
                """)
                print("✅ Memories table created with vector embeddings")
            except psycopg2.Error:
                # Fallback: use JSONB for embeddings
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                        memory_type TEXT NOT NULL CHECK (memory_type IN ('core', 'archival', 'recall')),
                        label TEXT NOT NULL,
                        content TEXT NOT NULL,
                        embedding JSONB,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        tags TEXT[],
                        metadata JSONB DEFAULT '{}'
                    )
                """)
                print("✅ Memories table created (JSONB embeddings - no pgvector)")
            
            # Indexes for memory queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_agent_type 
                ON memories(agent_id, memory_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_label 
                ON memories(agent_id, label)
            """)
            
            # 4. SESSIONS TABLE
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    last_active TIMESTAMP NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_agent 
                ON sessions(agent_id, last_active DESC)
            """)
            
            # 5. MESSAGE SUMMARIES TABLE (Context window management!)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_summaries (
                    id SERIAL PRIMARY KEY,
                    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    from_timestamp TIMESTAMP NOT NULL,
                    to_timestamp TIMESTAMP NOT NULL,
                    message_count INTEGER NOT NULL,
                    token_count INTEGER,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_summaries_session 
                ON message_summaries(session_id, created_at DESC)
            """)
            
            # 6. CHANNELS TABLE (Rooms/Channels for organizing messages!)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    description TEXT,
                    parent_id TEXT REFERENCES channels(id) ON DELETE SET NULL,
                    parent_message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
                    discord_channel_id TEXT,
                    discord_webhook_url TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(agent_id, name)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_channels_agent_id 
                ON channels(agent_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_channels_parent_id 
                ON channels(parent_id)
            """)
            print("✅ Channels table created")
            
            # 7. TASKS TABLE (Scheduled tasks!)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                    task_name TEXT NOT NULL,
                    description TEXT,
                    schedule TEXT NOT NULL,
                    time TEXT,
                    next_run TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE,
                    one_time BOOLEAN DEFAULT FALSE,
                    action_type TEXT DEFAULT 'self_task',
                    action_target TEXT,
                    action_template TEXT,
                    days_of_week INTEGER[],
                    every_N_days INTEGER,
                    months_of_year INTEGER[],
                    start_date DATE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(agent_id, task_name)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_agent_id 
                ON tasks(agent_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_next_run 
                ON tasks(next_run) WHERE active = TRUE
            """)
            print("✅ Tasks table created")
            
            # 8. COSTS TABLE (API usage tracking!)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS costs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    input_cost NUMERIC(12, 8) NOT NULL,
                    output_cost NUMERIC(12, 8) NOT NULL,
                    total_cost NUMERIC(12, 8) NOT NULL,
                    agent_id TEXT REFERENCES agents(id) ON DELETE SET NULL,
                    session_id TEXT,
                    metadata JSONB DEFAULT '{}'
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_costs_timestamp 
                ON costs(timestamp DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_costs_model 
                ON costs(model)
            """)
            print("✅ Costs table created")
            
            # 9. AGENT VERSIONS TABLE (Git-like versioning!)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_versions (
                    version_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    config JSONB NOT NULL,
                    system_prompt TEXT NOT NULL,
                    memory_blocks JSONB NOT NULL,
                    change_description TEXT,
                    parent_version TEXT REFERENCES agent_versions(version_id) ON DELETE SET NULL,
                    is_current BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_versions_agent 
                ON agent_versions(agent_id, timestamp DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_versions_current 
                ON agent_versions(agent_id) WHERE is_current = TRUE
            """)
            print("✅ Agent versions table created")
            
            # Migration: Add channel_id to messages table if not exists
            try:
                cursor.execute("""
                    ALTER TABLE messages ADD COLUMN IF NOT EXISTS channel_id TEXT REFERENCES channels(id) ON DELETE SET NULL
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON messages(channel_id)
                """)
                print("✅ Messages table extended with channel_id")
            except Exception as e:
                # Column might already exist
                print(f"ℹ️  channel_id migration: {e}")
            
            cursor.close()
            print("✅ PostgreSQL schema initialized - ALL TABLES READY!")
    
    # ============================================
    # AGENT METHODS
    # ============================================
    
    def create_agent(self, agent_id: str, name: str, config: Optional[Dict] = None) -> Agent:
        """
        Create new agent.
        
        Security: Parameterized query prevents SQL injection
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()
            
            cursor.execute(
                """
                INSERT INTO agents (id, name, created_at, config)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name, config = EXCLUDED.config
                RETURNING id, name, created_at, last_heartbeat, config
                """,
                (agent_id, name, now, json.dumps(config or {}))
            )
            
            row = cursor.fetchone()
            cursor.close()
            
            return Agent(
                id=row[0],
                name=row[1],
                created_at=row[2],
                last_heartbeat=row[3],
                config=row[4]
            )
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, name, created_at, last_heartbeat, config FROM agents WHERE id = %s",
                (agent_id,)
            )
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            return Agent(
                id=row[0],
                name=row[1],
                created_at=row[2],
                last_heartbeat=row[3],
                config=row[4]
            )
    
    def get_all_agents(self) -> List[Agent]:
        """Get all agents from the database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, name, created_at, last_heartbeat, config FROM agents ORDER BY created_at DESC"
            )
            
            rows = cursor.fetchall()
            cursor.close()
            
            return [
                Agent(
                    id=row[0],
                    name=row[1],
                    created_at=row[2],
                    last_heartbeat=row[3],
                    config=row[4]
                )
                for row in rows
            ]
    
    def update_agent_heartbeat(self, agent_id: str):
        """Update agent's last heartbeat timestamp"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE agents SET last_heartbeat = NOW() WHERE id = %s",
                (agent_id,)
            )
            cursor.close()
    
    def update_agent(self, agent_id: str, name: Optional[str] = None, config: Optional[Dict] = None) -> Optional[Agent]:
        """
        Update agent name and/or config.
        
        Security: Parameterized query prevents SQL injection
        Returns: Updated Agent object or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query dynamically
            updates = []
            params = []
            
            if name is not None:
                name = name.strip()
                if not name:
                    raise ValueError("Agent name cannot be empty")
                updates.append("name = %s")
                params.append(name)
            
            if config is not None:
                updates.append("config = %s::jsonb")
                params.append(json.dumps(config))
            
            if not updates:
                cursor.close()
                return None  # Nothing to update
            
            # Add agent_id to params
            params.append(agent_id)
            
            # Execute update
            query = f"""
                UPDATE agents 
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, name, created_at, last_heartbeat, config
            """
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            return Agent(
                id=row[0],
                name=row[1],
                created_at=row[2],
                last_heartbeat=row[3],
                config=row[4]
            )
    
    # ============================================
    # MESSAGE METHODS - Conversation Persistence
    # ============================================
    
    def add_message(
        self,
        agent_id: str,
        session_id: str,
        role: str,
        content: str,
        message_id: Optional[str] = None,
        tool_calls: Optional[Dict] = None,
        tool_results: Optional[Dict] = None,
        thinking: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Message:
        """
        Add message to persistent storage.
        
        Security: All parameters validated and sanitized via psycopg2
        """
        if role not in ['user', 'assistant', 'system', 'tool']:
            raise PostgresManagerError(
                f"Invalid role: {role}. Must be user/assistant/system/tool"
            )
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            msg_id = message_id or str(uuid.uuid4())
            now = datetime.now()
            
            cursor.execute(
                """
                INSERT INTO messages 
                (id, agent_id, session_id, role, content, created_at, 
                 tool_calls, tool_results, thinking, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, agent_id, session_id, role, content, created_at,
                          tool_calls, tool_results, thinking, metadata
                """,
                (
                    msg_id, agent_id, session_id, role, content, now,
                    json.dumps(tool_calls) if tool_calls else None,
                    json.dumps(tool_results) if tool_results else None,
                    thinking,
                    json.dumps(metadata or {})
                )
            )
            
            row = cursor.fetchone()
            cursor.close()
            
            # Update session last_active
            self._update_session_activity(agent_id, session_id)
            
            return Message(
                id=row[0],
                agent_id=row[1],
                session_id=row[2],
                role=row[3],
                content=row[4],
                created_at=row[5],
                tool_calls=row[6],
                tool_results=row[7],
                thinking=row[8],
                metadata=row[9]
            )
    
    def get_messages(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """
        Get messages with pagination.
        
        Returns most recent messages first (DESC order).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute(
                    """
                    SELECT id, agent_id, session_id, role, content, created_at,
                           tool_calls, tool_results, thinking, metadata
                    FROM messages
                    WHERE agent_id = %s AND session_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s OFFSET %s
                    """,
                    (agent_id, session_id, limit, offset)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, agent_id, session_id, role, content, created_at,
                           tool_calls, tool_results, thinking, metadata
                    FROM messages
                    WHERE agent_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s OFFSET %s
                    """,
                    (agent_id, limit, offset)
                )
            
            rows = cursor.fetchall()
            cursor.close()
            
            messages = []
            for row in rows:
                messages.append(Message(
                    id=row[0],
                    agent_id=row[1],
                    session_id=row[2],
                    role=row[3],
                    content=row[4],
                    created_at=row[5],
                    tool_calls=row[6],
                    tool_results=row[7],
                    thinking=row[8],
                    metadata=row[9]
                ))
            
            return messages
    
    def get_context_window(
        self,
        agent_id: str,
        session_id: str,
        max_messages: int = 50
    ) -> List[Message]:
        """
        Get optimized context window with recent messages.
        
        Returns recent messages for context, automatically managing window size.
        """
        return self.get_messages(agent_id, session_id, limit=max_messages)
    
    def delete_messages(self, agent_id: str, session_id: Optional[str] = None):
        """Delete messages (for conversation reset)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute(
                    "DELETE FROM messages WHERE agent_id = %s AND session_id = %s",
                    (agent_id, session_id)
                )
            else:
                cursor.execute(
                    "DELETE FROM messages WHERE agent_id = %s",
                    (agent_id,)
                )
            
            deleted = cursor.rowcount
            cursor.close()
            return deleted
    
    def delete_message_by_id(self, message_id: str):
        """Delete a single message by its ID (for summarization cleanup)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM messages WHERE message_id = %s",
                (message_id,)
            )
            deleted = cursor.rowcount
            cursor.close()
            return deleted > 0
    
    # ============================================
    # MEMORY METHODS
    # ============================================
    
    def add_memory(
        self,
        agent_id: str,
        memory_type: str,
        label: str,
        content: str,
        embedding: Optional[List[float]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        memory_id: Optional[str] = None
    ) -> Memory:
        """
        Add memory block.
        
        Security: Validated memory_type via CHECK constraint in DB
        """
        if memory_type not in ['core', 'archival', 'recall']:
            raise PostgresManagerError(
                f"Invalid memory_type: {memory_type}"
            )
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            mem_id = memory_id or str(uuid.uuid4())
            now = datetime.now()
            
            # Convert embedding to proper format
            embedding_value = None
            if embedding:
                try:
                    # Try vector format first (if pgvector available)
                    embedding_value = str(embedding)
                except:
                    # Fallback to JSONB
                    embedding_value = json.dumps(embedding)
            
            cursor.execute(
                """
                INSERT INTO memories 
                (id, agent_id, memory_type, label, content, embedding, created_at, tags, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata
                RETURNING id, agent_id, memory_type, label, content, created_at, tags, metadata
                """,
                (
                    mem_id, agent_id, memory_type, label, content,
                    embedding_value, now,
                    tags or [],
                    json.dumps(metadata or {})
                )
            )
            
            row = cursor.fetchone()
            cursor.close()
            
            return Memory(
                id=row[0],
                agent_id=row[1],
                memory_type=row[2],
                label=row[3],
                content=row[4],
                created_at=row[5],
                tags=row[6],
                metadata=row[7]
            )
    
    def get_memories(
        self,
        agent_id: str,
        memory_type: Optional[str] = None,
        label: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """
        Get memories by type and/or label.
        
        Args:
            agent_id: Agent ID to filter by
            memory_type: Optional memory type filter ('core', 'archival', 'recall')
            label: Optional label filter
            limit: Optional maximum number of memories to return
        
        Returns:
            List of Memory objects matching the criteria
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, agent_id, memory_type, label, content, created_at, tags, metadata
                FROM memories
                WHERE agent_id = %s
            """
            params = [agent_id]
            
            if memory_type:
                query += " AND memory_type = %s"
                params.append(memory_type)
            
            if label:
                query += " AND label = %s"
                params.append(label)
            
            query += " ORDER BY created_at ASC"
            
            if limit:
                query += " LIMIT %s"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            
            memories = []
            for row in rows:
                memories.append(Memory(
                    id=row[0],
                    agent_id=row[1],
                    memory_type=row[2],
                    label=row[3],
                    content=row[4],
                    created_at=row[5],
                    tags=row[6],
                    metadata=row[7]
                ))
            
            return memories
    
    # ============================================
    # SESSION METHODS
    # ============================================
    
    def _update_session_activity(self, agent_id: str, session_id: str):
        """Update session last_active timestamp"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO sessions (id, agent_id, created_at, last_active)
                VALUES (%s, %s, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                SET last_active = NOW()
                """,
                (session_id, agent_id)
            )
            
            cursor.close()
    
    # ============================================
    # UTILITIES
    # ============================================
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count agents
            cursor.execute("SELECT COUNT(*) FROM agents")
            stats['agents'] = cursor.fetchone()[0]
            
            # Count messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            stats['messages'] = cursor.fetchone()[0]
            
            # Count memories
            cursor.execute("SELECT COUNT(*) FROM memories")
            stats['memories'] = cursor.fetchone()[0]
            
            # Count sessions
            cursor.execute("SELECT COUNT(*) FROM sessions")
            stats['sessions'] = cursor.fetchone()[0]
            
            cursor.close()
            
            return stats
    
    # ============================================
    # CHANNEL METHODS
    # ============================================
    
    def _create_default_channels(self, agent_id: str):
        """
        Create default channels for a new agent.
        Standard channels: heartbeat-log, task, reflection
        """
        default_channels = [
            {"name": "💓 heartbeat-log", "description": "Heartbeat events and autonomous activity"},
            {"name": "📋 task", "description": "Scheduled tasks and reminders"},
            {"name": "🧠 reflection", "description": "Self-reflection and introspection"}
        ]
        
        for ch in default_channels:
            try:
                self.create_channel(agent_id, ch["name"], ch["description"])
            except Exception as e:
                # Channel might already exist
                print(f"ℹ️  Default channel '{ch['name']}' might already exist: {e}")
    
    def create_channel(
        self,
        agent_id: str,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[str] = None,
        discord_channel_id: Optional[str] = None,
        discord_webhook_url: Optional[str] = None
    ) -> Dict:
        """Create a new channel for an agent"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            channel_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO channels (id, agent_id, name, description, parent_id, 
                                     discord_channel_id, discord_webhook_url, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id, name, description, parent_id, discord_channel_id, discord_webhook_url, created_at, updated_at
            """, (channel_id, agent_id, name, description, parent_id, discord_channel_id, discord_webhook_url))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2] or "",
                    "parent_id": row[3],
                    "discord_channel_id": row[4],
                    "discord_webhook_url": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                    "updated_at": row[7].isoformat() if row[7] else None
                }
            return None
    
    def get_channel(self, channel_id: str, agent_id: str) -> Optional[Dict]:
        """Get a channel by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, description, parent_id, discord_channel_id, discord_webhook_url, created_at, updated_at
                FROM channels
                WHERE id = %s AND agent_id = %s
            """, (channel_id, agent_id))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2] or "",
                    "parent_id": row[3],
                    "discord_channel_id": row[4],
                    "discord_webhook_url": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                    "updated_at": row[7].isoformat() if row[7] else None
                }
            return None
    
    def list_channels(self, agent_id: str, parent_id: Optional[str] = None, include_children: bool = False) -> List[Dict]:
        """List all channels for an agent"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, name, description, parent_id, discord_channel_id, discord_webhook_url, created_at, updated_at
                FROM channels
                WHERE agent_id = %s
            """
            params = [agent_id]
            
            if parent_id:
                query += " AND parent_id = %s"
                params.append(parent_id)
            elif not include_children:
                query += " AND parent_id IS NULL"
            
            query += " ORDER BY created_at ASC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            
            channels = []
            for row in rows:
                channels.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2] or "",
                    "parent_id": row[3],
                    "discord_channel_id": row[4],
                    "discord_webhook_url": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                    "updated_at": row[7].isoformat() if row[7] else None
                })
            
            return channels
    
    def update_channel(self, channel_id: str, agent_id: str, **kwargs) -> bool:
        """Update a channel"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            for key, value in kwargs.items():
                if key in ['name', 'description', 'discord_channel_id', 'discord_webhook_url']:
                    updates.append(f"{key} = %s")
                    params.append(value)
            
            if not updates:
                return False
            
            updates.append("updated_at = NOW()")
            params.extend([channel_id, agent_id])
            
            cursor.execute(f"""
                UPDATE channels SET {', '.join(updates)}
                WHERE id = %s AND agent_id = %s
            """, params)
            
            updated = cursor.rowcount > 0
            cursor.close()
            return updated
    
    def delete_channel(self, channel_id: str, agent_id: str) -> bool:
        """Delete a channel"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM channels WHERE id = %s AND agent_id = %s
            """, (channel_id, agent_id))
            
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted
    
    def get_channel_messages(
        self,
        channel_id: str,
        agent_id: str,
        limit: int = 100,
        rule_id: Optional[str] = None,
        rule_name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict]:
        """Get messages from a channel with optional filtering"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, role, content, created_at, metadata
                FROM messages
                WHERE channel_id = %s AND agent_id = %s
            """
            params = [channel_id, agent_id]
            
            if rule_id:
                query += " AND metadata->>'rule_id' = %s"
                params.append(rule_id)
            
            if rule_name:
                query += " AND metadata->>'rule_name' = %s"
                params.append(rule_name)
            
            if date_from:
                query += " AND DATE(created_at) >= %s"
                params.append(date_from)
            
            if date_to:
                query += " AND DATE(created_at) <= %s"
                params.append(date_to)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            
            messages = []
            for row in rows:
                metadata = row[4] if isinstance(row[4], dict) else (json.loads(row[4]) if row[4] else {})
                messages.append({
                    "id": row[0],
                    "role": row[1],
                    "content": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "metadata": metadata,
                    "rule_id": metadata.get('rule_id'),
                    "rule_name": metadata.get('rule_name')
                })
            
            return messages
    
    # ============================================
    # TASK METHODS
    # ============================================
    
    def create_task(
        self,
        agent_id: str,
        task_name: str,
        schedule: str,
        description: Optional[str] = None,
        time: Optional[str] = None,
        next_run: Optional[datetime] = None,
        active: bool = True,
        one_time: bool = False,
        action_type: str = 'self_task',
        action_target: Optional[str] = None,
        action_template: Optional[str] = None,
        days_of_week: Optional[List[int]] = None,
        every_N_days: Optional[int] = None,
        months_of_year: Optional[List[int]] = None,
        start_date: Optional[str] = None
    ) -> Optional[str]:
        """Create a new task"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            task_id = str(uuid.uuid4())
            
            try:
                cursor.execute("""
                    INSERT INTO tasks (id, agent_id, task_name, description, schedule, time, next_run,
                                      active, one_time, action_type, action_target, action_template,
                                      days_of_week, every_N_days, months_of_year, start_date, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (task_id, agent_id, task_name, description, schedule, time, next_run,
                      active, one_time, action_type, action_target, action_template,
                      days_of_week, every_N_days, months_of_year, start_date))
                
                row = cursor.fetchone()
                cursor.close()
                return row[0] if row else None
            except Exception as e:
                if 'unique constraint' in str(e).lower() or 'duplicate' in str(e).lower():
                    cursor.close()
                    return None  # Task already exists
                raise
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a task by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, agent_id, task_name, description, schedule, time, next_run,
                       active, one_time, action_type, action_target, action_template,
                       days_of_week, every_N_days, months_of_year, start_date, created_at, updated_at
                FROM tasks
                WHERE id = %s
            """, (task_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    "task_id": row[0],
                    "agent_id": row[1],
                    "task_name": row[2],
                    "description": row[3],
                    "schedule": row[4],
                    "time": row[5],
                    "next_run": row[6].isoformat() if row[6] else None,
                    "active": row[7],
                    "one_time": row[8],
                    "action_type": row[9],
                    "action_target": row[10],
                    "action_template": row[11],
                    "days_of_week": row[12] or [],
                    "every_N_days": row[13],
                    "months_of_year": row[14] or [],
                    "start_date": str(row[15]) if row[15] else None,
                    "created_at": row[16].isoformat() if row[16] else None,
                    "updated_at": row[17].isoformat() if row[17] else None
                }
            return None
    
    def list_tasks(self, agent_id: str, active_only: bool = False) -> List[Dict]:
        """List all tasks for an agent"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, agent_id, task_name, description, schedule, time, next_run,
                       active, one_time, action_type, action_target, action_template,
                       days_of_week, every_N_days, months_of_year, start_date, created_at, updated_at
                FROM tasks
                WHERE agent_id = %s
            """
            params = [agent_id]
            
            if active_only:
                query += " AND active = TRUE"
            
            query += " ORDER BY next_run ASC NULLS LAST"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            
            tasks = []
            for row in rows:
                tasks.append({
                    "task_id": row[0],
                    "agent_id": row[1],
                    "task_name": row[2],
                    "description": row[3],
                    "schedule": row[4],
                    "time": row[5],
                    "next_run": row[6].isoformat() if row[6] else None,
                    "active": row[7],
                    "one_time": row[8],
                    "action_type": row[9],
                    "action_target": row[10],
                    "action_template": row[11],
                    "days_of_week": row[12] or [],
                    "every_N_days": row[13],
                    "months_of_year": row[14] or [],
                    "start_date": str(row[15]) if row[15] else None,
                    "created_at": row[16].isoformat() if row[16] else None,
                    "updated_at": row[17].isoformat() if row[17] else None
                })
            
            return tasks
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update a task"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            valid_fields = ['task_name', 'description', 'schedule', 'time', 'next_run',
                           'active', 'one_time', 'action_type', 'action_target', 'action_template',
                           'days_of_week', 'every_N_days', 'months_of_year', 'start_date']
            
            for key, value in kwargs.items():
                if key in valid_fields:
                    updates.append(f"{key} = %s")
                    params.append(value)
            
            if not updates:
                return False
            
            updates.append("updated_at = NOW()")
            params.append(task_id)
            
            cursor.execute(f"""
                UPDATE tasks SET {', '.join(updates)}
                WHERE id = %s
            """, params)
            
            updated = cursor.rowcount > 0
            cursor.close()
            return updated
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted
    
    def get_due_tasks(self, agent_id: str) -> List[Dict]:
        """Get all tasks that are due for execution"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, agent_id, task_name, description, schedule, time, next_run,
                       active, one_time, action_type, action_target, action_template,
                       days_of_week, every_N_days, months_of_year, start_date, created_at, updated_at
                FROM tasks
                WHERE agent_id = %s AND active = TRUE AND next_run <= NOW()
                ORDER BY next_run ASC
            """, (agent_id,))
            
            rows = cursor.fetchall()
            cursor.close()
            
            tasks = []
            for row in rows:
                tasks.append({
                    "task_id": row[0],
                    "agent_id": row[1],
                    "task_name": row[2],
                    "description": row[3],
                    "schedule": row[4],
                    "time": row[5],
                    "next_run": row[6].isoformat() if row[6] else None,
                    "active": row[7],
                    "one_time": row[8],
                    "action_type": row[9],
                    "action_target": row[10],
                    "action_template": row[11],
                    "days_of_week": row[12] or [],
                    "every_N_days": row[13],
                    "months_of_year": row[14] or [],
                    "start_date": str(row[15]) if row[15] else None,
                    "created_at": row[16].isoformat() if row[16] else None,
                    "updated_at": row[17].isoformat() if row[17] else None
                })
            
            return tasks
    
    def close(self):
        """Close connection pool"""
        if self.pool:
            self.pool.closeall()
            print("🔌 PostgreSQL connection pool closed")


# ============================================
# HELPER FUNCTION
# ============================================

def create_postgres_manager_from_env() -> Optional[PostgresManager]:
    """
    Create PostgresManager from environment variables.
    
    Env vars:
    - POSTGRES_HOST (default: localhost)
    - POSTGRES_PORT (default: 5432)
    - POSTGRES_DB (default: substrate_ai)
    - POSTGRES_USER (default: current system user)
    - POSTGRES_PASSWORD (optional for local connections)
    """
    from dotenv import load_dotenv
    import getpass
    load_dotenv()
    
    # Password is optional for local peer/trust connections (Homebrew default)
    password = os.getenv("POSTGRES_PASSWORD", "")
    
    # Default user to current system user (Homebrew PostgreSQL default)
    default_user = getpass.getuser()
    
    try:
        return PostgresManager(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "substrate_ai"),
            user=os.getenv("POSTGRES_USER", default_user),
            password=password,
            min_connections=int(os.getenv("POSTGRES_MIN_CONN", "1")),
            max_connections=int(os.getenv("POSTGRES_MAX_CONN", "10"))
        )
    except Exception as e:
        print(f"⚠️  Failed to initialize PostgreSQL: {e}")
        return None


if __name__ == "__main__":
    # Test the PostgreSQL manager
    print("🧪 Testing PostgreSQL Manager...")
    
    # This will use local PostgreSQL
    pg = PostgresManager(
        host="localhost",
        database="substrate_ai_test",
        user="postgres",
        password="your_password"  # Change this!
    )
    
    # Create test agent
    agent = pg.create_agent("test-agent", "Test Agent")
    print(f"✅ Created agent: {agent.id}")
    
    # Add test message
    msg = pg.add_message(
        agent_id=agent.id,
        session_id="test-session",
        role="user",
        content="Hello!"
    )
    print(f"✅ Added message: {msg.id}")
    
    # Get messages
    messages = pg.get_messages(agent.id, "test-session")
    print(f"✅ Retrieved {len(messages)} messages")
    
    # Get stats
    stats = pg.get_stats()
    print(f"✅ Database stats: {stats}")
    
    pg.close()
    print("🎉 PostgreSQL Manager test complete!")

