#!/usr/bin/env python3
"""
State Manager for Substrate AI - PostgreSQL ONLY!

NO SQLite - ALL data in PostgreSQL.

Stores:
- Core memory blocks (via PostgreSQL memories table)
- Conversation history (via PostgreSQL messages table)
- Agent state (via PostgreSQL agents.config JSONB)
"""

import os
import json
import uuid
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# Import broadcast for memory access tracking
try:
    from core.consciousness_broadcast import broadcast_memory_access
except ImportError:
    def broadcast_memory_access(*args, **kwargs):
        pass


class BlockType(str, Enum):
    """Memory block types"""
    PERSONA = "persona"
    HUMAN = "human"
    CUSTOM = "custom"


@dataclass
class MemoryBlock:
    """Core memory block - stored in PostgreSQL memories table"""
    label: str
    content: str
    block_type: BlockType
    created_at: datetime
    updated_at: datetime
    limit: int = 2000
    read_only: bool = False
    description: str = ""
    metadata: Dict[str, Any] = None
    hidden: bool = False
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        return {
            "label": self.label,
            "content": self.content,
            "block_type": self.block_type.value if isinstance(self.block_type, BlockType) else self.block_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "limit": self.limit,
            "read_only": self.read_only,
            "description": self.description,
            "metadata": self.metadata,
            "hidden": self.hidden
        }


@dataclass
class Message:
    """Message stored in PostgreSQL messages table"""
    id: str
    session_id: str
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    message_type: str = "inbox"
    thinking: str = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
            "message_type": self.message_type,
            "thinking": self.thinking
        }


class StateManagerError(Exception):
    """State Manager Error with context"""
    def __init__(self, message: str, context: Optional[Dict] = None):
        self.context = context or {}
        super().__init__(f"""
============================================================
❌ STATE MANAGER ERROR
============================================================

🔴 Problem: {message}

📋 Context:
{chr(10).join(f"   • {k}: {v}" for k, v in self.context.items())}

💡 Ensure PostgreSQL is running and configured in .env

============================================================
""")


class StateManager:
    """
    PostgreSQL-ONLY State Manager.
    
    All operations delegate to PostgresManager.
    NO SQLite storage.
    """
    
    def __init__(self, db_path: str = None, postgres_manager=None):
        """
        Initialize state manager.
        
        Args:
            db_path: IGNORED (legacy compatibility)
            postgres_manager: PostgresManager instance (REQUIRED!)
        """
        if not postgres_manager:
            raise StateManagerError(
                "PostgresManager is REQUIRED! Pass postgres_manager parameter.",
                context={"action": "init"}
            )
        
        self.postgres_manager = postgres_manager
        self._agent_id_cache = None
        
        print("✅ State Manager initialized (PostgreSQL-ONLY)")
    
    def _get_agent_id(self) -> str:
        """Get the active agent ID from PostgreSQL"""
        if self._agent_id_cache:
            return self._agent_id_cache
        
        agents = self.postgres_manager.get_all_agents()
        if agents:
            self._agent_id_cache = agents[0].id
            return self._agent_id_cache
        
        # Create default agent if none exists
        agent = self.postgres_manager.create_agent(
            agent_id=str(uuid.uuid4()),
            name="ALEX",
            config={"model": "qwen/qwen-2.5-72b-instruct"}
        )
        self._agent_id_cache = agent.id
        return self._agent_id_cache
    
    # ============================================
    # MEMORY BLOCKS (stored as PostgreSQL memories)
    # ============================================
    
    def create_block(
        self, 
        label: str, 
        content: str = "", 
        block_type: BlockType = BlockType.CUSTOM,
        limit: int = 2000,
        read_only: bool = False,
        description: str = "",
        metadata: Optional[Dict] = None,
        hidden: bool = False
    ) -> MemoryBlock:
        """Create a new memory block in PostgreSQL"""
        agent_id = self._get_agent_id()
        
        # Store as archival memory with special type
        memory_id = f"block-{label}"
        
        self.postgres_manager.add_memory(
            memory_id=memory_id,
            agent_id=agent_id,
            content=content,
            memory_type="core_block",
            importance=1.0,
            metadata={
                "label": label,
                "block_type": block_type.value if isinstance(block_type, BlockType) else block_type,
                "limit": limit,
                "read_only": read_only,
                "description": description,
                "hidden": hidden,
                **(metadata or {})
            }
        )
        
        now = datetime.now()
        return MemoryBlock(
            label=label,
            content=content,
            block_type=block_type,
            created_at=now,
            updated_at=now,
            limit=limit,
            read_only=read_only,
            description=description,
            metadata=metadata or {},
            hidden=hidden
        )
    
    def get_block(self, label: str) -> Optional[MemoryBlock]:
        """Get a memory block by label"""
        agent_id = self._get_agent_id()
        
        # Get from PostgreSQL memories
        memories = self.postgres_manager.get_memories(
            agent_id=agent_id,
            memory_type="core_block"
        )
        
        for mem in memories:
            meta = mem.metadata or {}
            if meta.get("label") == label:
                broadcast_memory_access("read", label)
                return MemoryBlock(
                    label=label,
                    content=mem.content,
                    block_type=BlockType(meta.get("block_type", "custom")),
                    created_at=mem.created_at or datetime.now(),
                    updated_at=mem.updated_at or datetime.now(),
                    limit=meta.get("limit", 2000),
                    read_only=meta.get("read_only", False),
                    description=meta.get("description", ""),
                    metadata=meta,
                    hidden=meta.get("hidden", False)
                )
        
        return None
    
    def update_block(
        self, 
        label: str, 
        content: str,
        check_read_only: bool = True
    ) -> Optional[MemoryBlock]:
        """Update a memory block's content"""
        block = self.get_block(label)
        if not block:
            return None
        
        if check_read_only and block.read_only:
            raise StateManagerError(
                f"Block '{label}' is read-only",
                context={"label": label, "action": "update"}
            )
        
        agent_id = self._get_agent_id()
        memory_id = f"block-{label}"
        
        # Update in PostgreSQL
        self.postgres_manager.add_memory(
            memory_id=memory_id,
            agent_id=agent_id,
            content=content,
            memory_type="core_block",
            importance=1.0,
            metadata={
                "label": label,
                "block_type": block.block_type.value if isinstance(block.block_type, BlockType) else block.block_type,
                "limit": block.limit,
                "read_only": block.read_only,
                "description": block.description,
                "hidden": block.hidden,
                **block.metadata
            }
        )
        
        broadcast_memory_access("write", label)
        
        block.content = content
        block.updated_at = datetime.now()
        return block
    
    def list_blocks(self, include_hidden: bool = False) -> List[MemoryBlock]:
        """List all memory blocks"""
        agent_id = self._get_agent_id()
        
        memories = self.postgres_manager.get_memories(
            agent_id=agent_id,
            memory_type="core_block"
        )
        
        blocks = []
        for mem in memories:
            meta = mem.metadata or {}
            if not include_hidden and meta.get("hidden", False):
                continue
            
            blocks.append(MemoryBlock(
                label=meta.get("label", mem.id),
                content=mem.content,
                block_type=BlockType(meta.get("block_type", "custom")),
                created_at=mem.created_at or datetime.now(),
                updated_at=mem.updated_at or datetime.now(),
                limit=meta.get("limit", 2000),
                read_only=meta.get("read_only", False),
                description=meta.get("description", ""),
                metadata=meta,
                hidden=meta.get("hidden", False)
            ))
        
        return blocks
    
    def delete_block(self, label: str):
        """Delete a memory block"""
        # PostgreSQL memories don't have direct delete, but we can mark as deleted
        # For now, just log it
        print(f"⚠️  Block deletion not fully implemented for PostgreSQL: {label}")
    
    # ============================================
    # MESSAGES (stored in PostgreSQL messages table)
    # ============================================
    
    def add_message(
        self,
        message_id: str,
        session_id: str,
        role: str,
        content: str,
        message_type: str = "inbox",
        thinking: str = None,
        metadata: Dict = None,
        **kwargs
    ):
        """Add a message to PostgreSQL"""
        agent_id = self._get_agent_id()
        
        self.postgres_manager.add_message(
            message_id=message_id,
            agent_id=agent_id,
            session_id=session_id,
            role=role,
            content=content,
            thinking=thinking,
            metadata={
                "message_type": message_type,
                **(metadata or {})
            },
            **kwargs
        )
    
    def get_conversation(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get conversation history from PostgreSQL"""
        agent_id = self._get_agent_id()
        
        pg_messages = self.postgres_manager.get_messages(
            agent_id=agent_id,
            session_id=session_id,
            limit=limit or 1000
        )
        
        messages = []
        for msg in pg_messages:
            meta = msg.metadata or {}
            messages.append(Message(
                id=msg.id,
                session_id=session_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.created_at,
                metadata=meta,
                message_type=meta.get("message_type", "inbox"),
                thinking=msg.thinking
            ))
        
        return messages
    
    def clear_messages(self, session_id: Optional[str] = None):
        """Clear messages from PostgreSQL"""
        agent_id = self._get_agent_id()
        self.postgres_manager.delete_messages(
            agent_id=agent_id,
            session_id=session_id
        )
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a single message"""
        self.postgres_manager.delete_message_by_id(message_id)
        return True
    
    # ============================================
    # AGENT STATE (stored in PostgreSQL agents.config)
    # ============================================
    
    def set_state(self, key: str, value: Any):
        """Set agent state in PostgreSQL"""
        agent_id = self._get_agent_id()
        
        agent = self.postgres_manager.get_agent(agent_id)
        config = agent.config.copy() if agent and agent.config else {}
        config[key] = value
        
        self.postgres_manager.update_agent(
            agent_id=agent_id,
            config=config
        )
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get agent state from PostgreSQL"""
        agent_id = self._get_agent_id()
        
        agent = self.postgres_manager.get_agent(agent_id)
        if agent and agent.config:
            return agent.config.get(key, default)
        
        return default
    
    def get_agent_state(self) -> Dict[str, Any]:
        """Get full agent state"""
        agent_id = self._get_agent_id()
        agent = self.postgres_manager.get_agent(agent_id)
        
        if agent:
            return {
                "id": agent.id,
                "name": agent.name,
                "model": (agent.config or {}).get("model", "qwen/qwen-2.5-72b-instruct"),
                "system_prompt": (agent.config or {}).get("system_prompt", ""),
                "config": agent.config or {}
            }
        
        return {
            "id": agent_id,
            "name": "ALEX",
            "model": "qwen/qwen-2.5-72b-instruct",
            "system_prompt": "",
            "config": {}
        }
    
    def update_agent_state(self, agent_state: Dict[str, Any]):
        """Update agent state in PostgreSQL"""
        agent_id = self._get_agent_id()
        
        self.postgres_manager.update_agent(
            agent_id=agent_id,
            name=agent_state.get("name"),
            config={
                "model": agent_state.get("model"),
                "system_prompt": agent_state.get("system_prompt"),
                **agent_state.get("config", {})
            }
        )
    
    # ============================================
    # SUMMARIES (stored as special memories)
    # ============================================
    
    def save_summary(
        self,
        session_id: str,
        summary: str,
        from_timestamp: datetime,
        to_timestamp: datetime,
        message_count: int,
        token_count: int = 0
    ) -> str:
        """Save a conversation summary"""
        agent_id = self._get_agent_id()
        summary_id = f"summary-{session_id}-{datetime.now().timestamp()}"
        
        self.postgres_manager.add_memory(
            memory_id=summary_id,
            agent_id=agent_id,
            content=summary,
            memory_type="summary",
            importance=0.9,
            metadata={
                "session_id": session_id,
                "from_timestamp": from_timestamp.isoformat(),
                "to_timestamp": to_timestamp.isoformat(),
                "message_count": message_count,
                "token_count": token_count
            }
        )
        
        return summary_id
    
    def get_latest_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest summary for a session"""
        agent_id = self._get_agent_id()
        
        memories = self.postgres_manager.get_memories(
            agent_id=agent_id,
            memory_type="summary",
            limit=100
        )
        
        # Filter by session and get latest
        session_summaries = [
            m for m in memories 
            if (m.metadata or {}).get("session_id") == session_id
        ]
        
        if not session_summaries:
            return None
        
        # Sort by timestamp and get latest
        latest = max(session_summaries, key=lambda m: m.created_at or datetime.min)
        meta = latest.metadata or {}
        
        return {
            "id": latest.id,
            "summary": latest.content,
            "from_timestamp": meta.get("from_timestamp"),
            "to_timestamp": meta.get("to_timestamp"),
            "message_count": meta.get("message_count", 0),
            "token_count": meta.get("token_count", 0),
            "created_at": latest.created_at.isoformat() if latest.created_at else None
        }
    
    def get_all_summaries(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all summaries for a session"""
        agent_id = self._get_agent_id()
        
        memories = self.postgres_manager.get_memories(
            agent_id=agent_id,
            memory_type="summary",
            limit=1000
        )
        
        summaries = []
        for m in memories:
            meta = m.metadata or {}
            if meta.get("session_id") == session_id:
                summaries.append({
                    "id": m.id,
                    "summary": m.content,
                    "from_timestamp": meta.get("from_timestamp"),
                    "to_timestamp": meta.get("to_timestamp"),
                    "message_count": meta.get("message_count", 0),
                    "created_at": m.created_at.isoformat() if m.created_at else None
                })
        
        return summaries
    
    # ============================================
    # LEGACY COMPATIBILITY METHODS
    # ============================================
    
    def get_all_memory_blocks(self) -> List[Dict[str, Any]]:
        """Get all memory blocks as dicts"""
        return [b.to_dict() for b in self.list_blocks(include_hidden=True)]
    
    def get_memory_block(self, label: str) -> Optional[Dict[str, Any]]:
        """Get a memory block as dict"""
        block = self.get_block(label)
        return block.to_dict() if block else None
    
    def update_memory_block(self, label: str, value: str, block_data: Dict[str, Any], check_read_only: bool = True):
        """Update a memory block (legacy interface)"""
        return self.update_block(label, value, check_read_only)
    
    def create_memory_block(self, label: str, value: str, block_data: Dict[str, Any]):
        """Create a memory block (legacy interface)"""
        return self.create_block(
            label=label,
            content=value,
            block_type=BlockType(block_data.get("block_type", "custom")),
            limit=block_data.get("limit", 2000),
            read_only=block_data.get("read_only", False),
            description=block_data.get("description", ""),
            metadata=block_data.get("metadata", {}),
            hidden=block_data.get("hidden", False)
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = self.postgres_manager.get_stats()
        return {
            "database": "PostgreSQL",
            "messages": stats.get("messages", 0),
            "memories": stats.get("memories", 0),
            "agents": stats.get("agents", 0)
        }
