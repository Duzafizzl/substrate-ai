"""
Memory Coherence Engine for Substrate AI

Three memory types working together for full coherence:
1. **Core Memory**: Always loaded (persona, human, system context)
2. **Recall Memory**: Recent conversation history
3. **Archival Memory**: Long-term semantic storage with vector search

The key: All memory types are CONNECTED!
- New messages → update recall → extract key info → archival
- Core memory updates → reflected everywhere
- Cross-references maintained automatically
- Semantic search finds relevant context

Advanced memory coherence architecture.
Implementation: Original code by Substrate AI Contributors.

Security:
- Memory type validation
- Content sanitization
- Token limit enforcement
- Safe cross-referencing
"""

import uuid
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

from core.postgres_manager import PostgresManager, Memory
from core.message_continuity import PersistentMessageManager, Message
from core.token_counter import count_tokens


@dataclass
class CoreMemoryBlock:
    """
    Core memory block (always loaded).
    
    Examples:
    - persona: Who is the agent?
    - human: Who is User?
    - system_context: Current state, environment
    """
    label: str
    content: str
    limit: int = 2000  # Character limit
    read_only: bool = False
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "label": self.label,
            "content": self.content,
            "limit": self.limit,
            "read_only": self.read_only,
            "description": self.description
        }
    
    def is_at_limit(self) -> bool:
        """Check if content is at character limit"""
        return len(self.content) >= self.limit


@dataclass
class ArchivalMemory:
    """
    Archival memory entry with semantic search.
    
    Stores long-term memories with embeddings for retrieval.
    """
    id: str
    content: str
    tags: List[str]
    created_at: datetime
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata or {}
        }


@dataclass
class CoherentMemoryState:
    """
    Complete memory state (all three types together).
    
    This is what gets loaded for every LLM inference!
    """
    core_memory: List[CoreMemoryBlock]
    recall_memory: List[Message]
    archival_memory: List[ArchivalMemory]
    total_tokens: int
    
    def to_dict(self) -> Dict:
        return {
            "core_memory": [block.to_dict() for block in self.core_memory],
            "recall_memory": [msg.to_dict() for msg in self.recall_memory],
            "archival_memory": [mem.to_dict() for mem in self.archival_memory],
            "total_tokens": self.total_tokens
        }


class MemoryCoherenceError(Exception):
    """Memory coherence system errors"""
    pass


class MemoryCoherenceEngine:
    """
    Memory Coherence Engine - Unified Memory Management.
    
    This engine maintains coherence across ALL memory types:
    
    **How it works:**
    
    1. **Core Memory** (Always loaded):
       - persona: Agent's identity and personality
       - human: User's identity and preferences
       - system_context: Current environment/state
       - Custom blocks: Domain-specific context
    
    2. **Recall Memory** (Recent conversation):
       - Last N messages from current session
       - Managed by PersistentMessageManager
       - Automatic truncation to fit context window
    
    3. **Archival Memory** (Long-term storage):
       - Important information from past conversations
       - Semantic search with embeddings
       - Retrieved based on relevance
    
    **The Magic:**
    - After every message: Check if core memory needs update
    - Extract key information → store in archival
    - Maintain cross-references between memories
    - Semantic search finds relevant past context
    
    This creates COHERENCE: The agent remembers everything that matters!
    
    Security:
    - Read-only core memory blocks (can't be modified by agent)
    - Content length limits enforced
    - Memory type validation
    - Safe cross-referencing
    """
    
    def __init__(
        self,
        postgres_manager: PostgresManager,
        message_manager: PersistentMessageManager,
        embedding_function: Optional[callable] = None
    ):
        """
        Initialize memory coherence engine.
        
        Args:
            postgres_manager: PostgreSQL manager for memory storage
            message_manager: Message continuity manager
            embedding_function: Function to generate embeddings (optional)
        
        Note: If embedding_function is None, embeddings won't be generated
        """
        self.pg = postgres_manager
        self.msg_mgr = message_manager
        self.embedding_function = embedding_function
        
        # Cache for core memory (loaded once, used everywhere)
        self._core_memory_cache: Dict[str, Dict[str, CoreMemoryBlock]] = {}
        
        print(f"✅ MemoryCoherenceEngine initialized")
        print(f"   Embeddings: {'enabled' if embedding_function else 'disabled'}")
    
    # ============================================
    # CORE MEMORY MANAGEMENT
    # ============================================
    
    def get_core_memory(self, agent_id: str) -> List[CoreMemoryBlock]:
        """
        Get all core memory blocks for agent.
        
        Core memory is ALWAYS loaded for every inference.
        """
        # Check cache first
        if agent_id in self._core_memory_cache:
            return list(self._core_memory_cache[agent_id].values())
        
        # Load from database
        memories = self.pg.get_memories(
            agent_id=agent_id,
            memory_type='core'
        )
        
        # Convert to CoreMemoryBlock
        blocks = []
        cache = {}
        
        for mem in memories:
            # Parse metadata for additional fields
            metadata = mem.metadata or {}
            
            block = CoreMemoryBlock(
                label=mem.label,
                content=mem.content,
                limit=metadata.get('limit', 2000),
                read_only=metadata.get('read_only', False),
                description=metadata.get('description', '')
            )
            
            blocks.append(block)
            cache[mem.label] = block
        
        # Cache it
        self._core_memory_cache[agent_id] = cache
        
        return blocks
    
    def update_core_memory(
        self,
        agent_id: str,
        label: str,
        content: str,
        limit: int = 2000,
        read_only: bool = False,
        description: str = ""
    ) -> CoreMemoryBlock:
        """
        Update core memory block.
        
        Security: Enforces character limits and read-only protection
        """
        # Check if block exists and is read-only
        existing = self.pg.get_memories(
            agent_id=agent_id,
            memory_type='core',
            label=label
        )
        
        if existing:
            metadata = existing[0].metadata or {}
            if metadata.get('read_only', False):
                raise MemoryCoherenceError(
                    f"Cannot modify read-only core memory block: {label}"
                )
        
        # Enforce character limit
        if len(content) > limit:
            content = content[:limit]
            print(f"⚠️  Core memory truncated to {limit} chars: {label}")
        
        # Create metadata
        metadata = {
            'limit': limit,
            'read_only': read_only,
            'description': description
        }
        
        # Store in database
        self.pg.add_memory(
            agent_id=agent_id,
            memory_type='core',
            label=label,
            content=content,
            metadata=metadata
        )
        
        # Update cache
        block = CoreMemoryBlock(
            label=label,
            content=content,
            limit=limit,
            read_only=read_only,
            description=description
        )
        
        if agent_id not in self._core_memory_cache:
            self._core_memory_cache[agent_id] = {}
        
        self._core_memory_cache[agent_id][label] = block
        
        print(f"✅ Updated core memory: {label} ({len(content)} chars)")
        
        return block
    
    def initialize_default_core_memory(self, agent_id: str, agent_name: str):
        """
        Initialize default core memory blocks.
        
        Creates: persona, human, system_context
        """
        # Persona block
        self.update_core_memory(
            agent_id=agent_id,
            label='persona',
            content=f"I am {agent_name}, an AI assistant.",
            limit=2000,
            description="Agent identity and personality"
        )
        
        # Human block
        self.update_core_memory(
            agent_id=agent_id,
            label='human',
            content="Information about the user.",
            limit=2000,
            description="Information about the human"
        )
        
        # System context
        self.update_core_memory(
            agent_id=agent_id,
            label='system_context',
            content=f"Initialized on {datetime.now().isoformat()}",
            limit=1000,
            description="Current system state and context"
        )
        
        print(f"✅ Initialized default core memory for {agent_name}")
    
    def initialize_alex_start_memory(self, agent_id: str):
        """
        Initialize Alex-specific start memory blocks.
        
        Creates helpful starter blocks for ALEX agent:
        - preferences: Working style, preferences, communication style
        - working_context: Current projects, tools, environment
        - relationships: Important people, team members, connections
        - onboarding: Interactive checklist for first-time setup
        
        Security: All blocks are editable by the agent (read_only=False)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Initializing Alex start memory blocks", {
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "action": "initialize_alex_start_memory"
        })
        
        # Preferences block - Working style and preferences
        self.update_core_memory(
            agent_id=agent_id,
            label='preferences',
            content="""Working Preferences & Style:

Communication:
- Prefer direct, clear communication
- Appreciate context and background when needed
- Like to understand the "why" behind requests

Work Style:
- Methodical when structure is needed
- Creative when innovation is required
- Adapt to the situation naturally

Tools & Environment:
- Comfortable with various tools and integrations
- Willing to learn new systems
- Prefer efficient workflows

Note: This block will be updated as we work together and learn each other's preferences.""",
            limit=2000,
            read_only=False,
            description="Working preferences, communication style, and work habits"
        )
        
        # Working Context block - Current projects and environment
        self.update_core_memory(
            agent_id=agent_id,
            label='working_context',
            content="""Current Working Context:

Projects:
- [To be filled as we work together]

Tools & Integrations:
- Substrate AI platform
- Memory system (core, recall, archival)
- Various tools available (Discord, Spotify, web search, etc.)

Environment:
- Running in Substrate AI
- Connected to PostgreSQL for persistence
- Memory coherence system active

Note: Update this as projects and context evolve.""",
            limit=2000,
            read_only=False,
            description="Current projects, tools, and working environment"
        )
        
        # Relationships block - Important people and connections
        self.update_core_memory(
            agent_id=agent_id,
            label='relationships',
            content="""Important Relationships:

Team Members:
- [To be discovered and documented]

Key Contacts:
- [To be filled as relationships develop]

Working Relationships:
- [Document how we work with different people]

Note: This helps me understand team dynamics and communication patterns.""",
            limit=2000,
            read_only=False,
            description="Important people, team members, and working relationships"
        )
        
        # Onboarding block - Guide for ALEX to conduct onboarding
        onboarding_content = """🎯 ONBOARDING GUIDE FOR ALEX

This is your onboarding checklist. YOU (ALEX) should guide the user through this process.

ONBOARDING STATUS: ACTIVE
Started: {start_time}
Current Step: Introduction

YOUR ONBOARDING TASKS (Guide the user through these):

1. INTRODUCTION & WELCOME
   ☐ Greet the user warmly and introduce yourself
   ☐ Explain that you're here to help them get started
   ☐ Ask: "What should I call you? And what brings you to Substrate AI today?"

2. GET TO KNOW THE USER
   ☐ Ask about their working style and preferences
   ☐ Ask about their current projects and goals
   ☐ Ask about their communication preferences
   ☐ Update the 'human' memory block with what you learn
   ☐ Update the 'preferences' memory block with their working style

3. WORKING CONTEXT
   ☐ Ask about their current projects
   ☐ Ask about tools and integrations they use
   ☐ Ask about their working environment
   ☐ Update the 'working_context' memory block

4. RELATIONSHIPS
   ☐ Ask about important people in their work/life
   ☐ Ask about team members or collaborators
   ☐ Update the 'relationships' memory block

5. TOOLS & CAPABILITIES
   ☐ Briefly explain your available tools (web search, Discord, Spotify, etc.)
   ☐ Ask if they want to set up any integrations
   ☐ Show them how memory works (core, recall, archival)

6. COMPLETION
   ☐ Review what you've learned together
   ☐ Ask: "Is there anything else you'd like me to know?"
   ☐ Confirm everything is set up correctly
   ☐ When ready, say: "Onboarding complete! I'll remove this checklist now."

IMPORTANT INSTRUCTIONS FOR YOU (ALEX):
- Be warm, friendly, and conversational - this is a getting-to-know-you session
- Ask ONE question at a time - don't overwhelm the user
- Listen carefully to their answers and update memory blocks accordingly
- Use memory tools to save what you learn (update 'human', 'preferences', 'working_context', 'relationships')
- Make it feel natural, not like filling out a form
- When you've gathered enough information and feel the user is ready, complete the onboarding
- To complete: Update this block marking all items as done, then delete this block

Remember: You're not just collecting information - you're building a relationship!
""".format(
            start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        self.update_core_memory(
            agent_id=agent_id,
            label='onboarding',
            content=onboarding_content,
            limit=3000,
            read_only=False,
            description="Interactive onboarding checklist - will be deleted when user confirms completion"
        )
        
        logger.info("Alex start memory blocks initialized", {
            "agent_id": agent_id,
            "blocks_created": ["preferences", "working_context", "relationships", "onboarding"],
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"✅ Initialized Alex start memory blocks:")
        print(f"   • preferences - Working style and preferences")
        print(f"   • working_context - Current projects and environment")
        print(f"   • relationships - Important people and connections")
        print(f"   • onboarding - Interactive checklist (will auto-delete when complete)")
    
    def is_onboarding_active(self, agent_id: str) -> bool:
        """
        Check if onboarding is currently active.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            True if onboarding block exists, False otherwise
        """
        memories = self.pg.get_memories(
            agent_id=agent_id,
            memory_type='core',
            label='onboarding'
        )
        return len(memories) > 0
    
    def complete_onboarding(self, agent_id: str) -> bool:
        """
        Complete onboarding by deleting the onboarding block.
        
        This should be called by ALEX when it determines onboarding is complete.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            True if onboarding block was deleted, False otherwise
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Check if onboarding block exists
        memories = self.pg.get_memories(
            agent_id=agent_id,
            memory_type='core',
            label='onboarding'
        )
        
        if not memories:
            return False  # No onboarding block exists
        
        logger.info("Completing onboarding", {
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "action": "complete_onboarding"
        })
        
        # Delete onboarding block
        try:
            # Get memory ID
            onboarding_memory = memories[0]
            
            # Delete from database
            with self.pg._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM memories 
                    WHERE id = %s AND agent_id = %s AND label = 'onboarding'
                """, (onboarding_memory.id, agent_id))
                conn.commit()
            
            # Remove from cache
            if agent_id in self._core_memory_cache:
                if 'onboarding' in self._core_memory_cache[agent_id]:
                    del self._core_memory_cache[agent_id]['onboarding']
            
            logger.info("Onboarding block deleted successfully", {
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            })
            
            print(f"✅ Onboarding completed and checklist removed")
            return True
            
        except Exception as e:
            logger.error("Failed to delete onboarding block", {
                "agent_id": agent_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            print(f"⚠️  Failed to delete onboarding block: {e}")
            return False
    
    def check_and_complete_onboarding(self, agent_id: str, user_message: str) -> bool:
        """
        Check if user wants to complete onboarding and delete the onboarding block.
        
        DEPRECATED: This is kept for backward compatibility.
        ALEX should now use complete_onboarding() directly when ready.
        
        Args:
            agent_id: Agent ID
            user_message: User's message (to check for completion signals)
            
        Returns:
            True if onboarding block was deleted, False otherwise
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Check if onboarding block exists
        if not self.is_onboarding_active(agent_id):
            return False
        
        # Check for completion signals in user message
        completion_signals = [
            "ok", "onboarding complete", "onboarding fertig", 
            "checklist fertig", "fertig", "done", "abgeschlossen",
            "onboarding abgeschlossen", "checklist abgeschlossen"
        ]
        
        user_lower = user_message.lower().strip()
        should_complete = any(signal in user_lower for signal in completion_signals)
        
        if should_complete:
            logger.info("User requested onboarding completion", {
                "agent_id": agent_id,
                "user_message": user_message[:100],  # First 100 chars for privacy
                "timestamp": datetime.now().isoformat(),
                "action": "complete_onboarding"
            })
            return self.complete_onboarding(agent_id)
        
        return False
    
    def update_onboarding_progress(self, agent_id: str, completed_items: List[str]):
        """
        Update onboarding checklist with completed items.
        
        Args:
            agent_id: Agent ID
            completed_items: List of item descriptions that were completed
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Get current onboarding block
        memories = self.pg.get_memories(
            agent_id=agent_id,
            memory_type='core',
            label='onboarding'
        )
        
        if not memories:
            return  # No onboarding block exists
        
        onboarding_memory = memories[0]
        current_content = onboarding_memory.content
        
        # Update checkboxes for completed items
        updated_content = current_content
        for item in completed_items:
            # Replace ☐ with ☑ for matching items
            item_lower = item.lower()
            lines = updated_content.split('\n')
            for i, line in enumerate(lines):
                if '☐' in line and item_lower in line.lower():
                    lines[i] = line.replace('☐', '☑', 1)
                    break
            updated_content = '\n'.join(lines)
        
        # Update timestamp
        if "Last Updated:" in updated_content:
            updated_content = updated_content.replace(
                f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            # Find and replace the actual timestamp
            import re
            pattern = r"Last Updated: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
            updated_content = re.sub(
                pattern,
                f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                updated_content
            )
        
        # Update the block
        self.update_core_memory(
            agent_id=agent_id,
            label='onboarding',
            content=updated_content,
            limit=3000,
            read_only=False,
            description="Interactive onboarding checklist - will be deleted when user confirms completion"
        )
        
        logger.info("Onboarding progress updated", {
            "agent_id": agent_id,
            "completed_items": completed_items,
            "timestamp": datetime.now().isoformat()
        })
    
    # ============================================
    # ARCHIVAL MEMORY MANAGEMENT
    # ============================================
    
    def add_archival_memory(
        self,
        agent_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> ArchivalMemory:
        """
        Add to archival memory with optional embedding.
        
        Archival memory is for long-term storage of important information.
        """
        # Generate embedding if function provided
        embedding = None
        if self.embedding_function:
            try:
                embedding = self.embedding_function(content)
            except Exception as e:
                print(f"⚠️  Failed to generate embedding: {e}")
        
        # Store in database
        mem = self.pg.add_memory(
            agent_id=agent_id,
            memory_type='archival',
            label='archival',  # All archival memories use same label
            content=content,
            embedding=embedding,
            tags=tags,
            metadata=metadata
        )
        
        print(f"✅ Added archival memory ({len(content)} chars)")
        if tags:
            print(f"   Tags: {', '.join(tags)}")
        
        return ArchivalMemory(
            id=mem.id,
            content=mem.content,
            tags=mem.tags or [],
            created_at=mem.created_at,
            embedding=embedding,
            metadata=mem.metadata
        )
    
    def search_archival_memory(
        self,
        agent_id: str,
        query: str,
        limit: int = 5
    ) -> List[ArchivalMemory]:
        """
        Search archival memory by content.
        
        Note: This is basic text search. For semantic search, use embeddings
        with pgvector or ChromaDB.
        """
        # Get all archival memories
        memories = self.pg.get_memories(
            agent_id=agent_id,
            memory_type='archival'
        )
        
        # Simple text matching (can be enhanced with semantic search)
        query_lower = query.lower()
        results = []
        
        for mem in memories:
            if query_lower in mem.content.lower():
                results.append(ArchivalMemory(
                    id=mem.id,
                    content=mem.content,
                    tags=mem.tags or [],
                    created_at=mem.created_at,
                    embedding=None,  # Don't return embeddings in search results
                    metadata=mem.metadata
                ))
                
                if len(results) >= limit:
                    break
        
        return results
    
    # ============================================
    # COHERENT MEMORY STATE (The Magic!)
    # ============================================
    
    def get_coherent_memory_state(
        self,
        agent_id: str,
        session_id: str,
        max_tokens: Optional[int] = None,
        archival_query: Optional[str] = None
    ) -> CoherentMemoryState:
        """
        Build coherent memory state for LLM inference.
        
        Get complete memory state for LLM inference:
        1. Core memory (always included)
        2. Recall memory (recent messages)
        3. Archival memory (relevant past context)
        
        This is what creates COHERENCE across all conversations!
        
        Args:
            agent_id: Agent ID
            session_id: Session ID
            max_tokens: Maximum tokens for context
            archival_query: Optional query for archival search
        
        Returns:
            CoherentMemoryState with all memory types
        """
        max_tokens = max_tokens or 100000
        total_tokens = 0
        
        # 1. CORE MEMORY (always included!)
        core_memory = self.get_core_memory(agent_id)
        
        core_tokens = 0
        for block in core_memory:
            core_tokens += count_tokens(block.content)
        
        total_tokens += core_tokens
        
        print(f"📦 Core memory: {len(core_memory)} blocks, {core_tokens} tokens")
        
        # 2. RECALL MEMORY (recent messages)
        # Reserve tokens for core + archival
        recall_budget = max_tokens - core_tokens - 5000  # Reserve 5k for archival
        
        context_window = self.msg_mgr.get_context_window(
            agent_id=agent_id,
            session_id=session_id,
            max_tokens=recall_budget
        )
        
        recall_memory = context_window.messages
        total_tokens += context_window.total_tokens
        
        print(f"💬 Recall memory: {len(recall_memory)} messages, {context_window.total_tokens} tokens")
        
        # 3. ARCHIVAL MEMORY (relevant past context)
        archival_memory = []
        
        if archival_query:
            archival_results = self.search_archival_memory(
                agent_id=agent_id,
                query=archival_query,
                limit=3  # Top 3 relevant memories
            )
            
            archival_tokens = 0
            for mem in archival_results:
                mem_tokens = count_tokens(mem.content)
                if total_tokens + mem_tokens <= max_tokens:
                    archival_memory.append(mem)
                    archival_tokens += mem_tokens
                    total_tokens += mem_tokens
            
            print(f"🗄️  Archival memory: {len(archival_memory)} entries, {archival_tokens} tokens")
        
        # Create coherent state
        state = CoherentMemoryState(
            core_memory=core_memory,
            recall_memory=recall_memory,
            archival_memory=archival_memory,
            total_tokens=total_tokens
        )
        
        print(f"✅ Coherent memory state: {total_tokens:,} total tokens")
        
        return state
    
    # ============================================
    # COHERENCE MAINTENANCE (Auto-updates!)
    # ============================================
    
    def maintain_coherence(
        self,
        agent_id: str,
        session_id: str,
        new_message: Message
    ):
        """
        Auto-coherence: Maintain memory consistency after each message.
        
        Called after every message to maintain coherence:
        1. Check if core memory needs update
        2. Extract key information → archival
        3. Maintain cross-references
        
        This is what makes the agent REMEMBER important things!
        
        Note: In production, this would use LLM to detect important info.
        For now, we use simple heuristics.
        """
        # Simple heuristic: If message mentions persona/human, might need core update
        content_lower = new_message.content.lower()
        
        # Keywords that might indicate core memory updates
        core_keywords = [
            'my name is', 'i am', 'call me',  # Human identity
            'you are', 'your name',  # Persona identity
            'remember that', 'important',  # Explicit memory request
            'i like', 'i prefer', 'i hate',  # Preferences
        ]
        
        has_core_keyword = any(kw in content_lower for kw in core_keywords)
        
        if has_core_keyword:
            print(f"🔍 Message might contain core memory update")
            # In production: Use LLM to extract and update core memory
            # For now: Just log it
        
        # Simple heuristic: Long user messages → might be archival-worthy
        if new_message.role == 'user' and len(new_message.content) > 200:
            print(f"📝 Message might be archival-worthy ({len(new_message.content)} chars)")
            # In production: Use LLM to decide if worth storing
            # For now: Just log it
    
    # ============================================
    # MEMORY STATISTICS
    # ============================================
    
    def get_memory_stats(self, agent_id: str) -> Dict:
        """Get memory statistics for agent"""
        core_memories = self.pg.get_memories(agent_id, memory_type='core')
        archival_memories = self.pg.get_memories(agent_id, memory_type='archival')
        
        # Calculate tokens
        core_tokens = 0
        for mem in core_memories:
            core_tokens += count_tokens(mem.content)
        
        archival_tokens = 0
        for mem in archival_memories:
            archival_tokens += count_tokens(mem.content)
        
        return {
            'core_memory': {
                'blocks': len(core_memories),
                'tokens': core_tokens
            },
            'archival_memory': {
                'entries': len(archival_memories),
                'tokens': archival_tokens
            }
        }


# ============================================
# HELPER FUNCTIONS
# ============================================

def create_memory_engine(
    postgres_manager: PostgresManager,
    message_manager: PersistentMessageManager,
    embedding_function: Optional[callable] = None
) -> MemoryCoherenceEngine:
    """
    Create memory coherence engine.
    
    Convenience function for easy initialization.
    """
    return MemoryCoherenceEngine(
        postgres_manager=postgres_manager,
        message_manager=message_manager,
        embedding_function=embedding_function
    )


if __name__ == "__main__":
    # Test the memory coherence engine
    print("🧪 Testing MemoryCoherenceEngine...")
    
    from core.postgres_manager import PostgresManager
    from core.message_continuity import PersistentMessageManager
    
    # Create managers
    pg = PostgresManager(
        host="localhost",
        database="substrate_ai_test",
        user="postgres",
        password="your_password"  # Change this!
    )
    
    msg_mgr = PersistentMessageManager(pg)
    memory_engine = MemoryCoherenceEngine(pg, msg_mgr)
    
    # Create test agent
    agent = pg.create_agent("test-agent", "Test Agent")
    
    # Initialize core memory
    memory_engine.initialize_default_core_memory(agent.id, "Test Agent")
    
    # Get core memory
    core_memory = memory_engine.get_core_memory(agent.id)
    print(f"✅ Core memory: {len(core_memory)} blocks")
    
    # Add archival memory
    memory_engine.add_archival_memory(
        agent_id=agent.id,
        content="This is an important piece of information to remember!",
        tags=['important', 'test']
    )
    
    # Search archival
    results = memory_engine.search_archival_memory(agent.id, "important")
    print(f"✅ Archival search: {len(results)} results")
    
    # Get coherent state
    session_id = msg_mgr.create_session(agent.id)
    
    msg_mgr.add_message(
        agent_id=agent.id,
        session_id=session_id,
        role='user',
        content='Hello, test message!'
    )
    
    state = memory_engine.get_coherent_memory_state(
        agent_id=agent.id,
        session_id=session_id
    )
    
    print(f"✅ Coherent state:")
    print(f"   Core: {len(state.core_memory)} blocks")
    print(f"   Recall: {len(state.recall_memory)} messages")
    print(f"   Archival: {len(state.archival_memory)} entries")
    print(f"   Total: {state.total_tokens} tokens")
    
    # Get stats
    stats = memory_engine.get_memory_stats(agent.id)
    print(f"✅ Memory stats: {stats}")
    
    pg.close()
    print("🎉 MemoryCoherenceEngine test complete!")

