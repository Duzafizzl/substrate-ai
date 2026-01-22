#!/usr/bin/env python3
"""
Neo4j Sync Service for Substrate AI (PostgreSQL-ONLY)

Synchronizes PostgreSQL + ChromaDB data into Neo4j graph database.

Real-time pipeline:
PostgreSQL (Core Memories) + ChromaDB (Archival Memories) → Neo4j Graph

100% PostgreSQL - NO SQLite!

Built with attention to detail! 🧠🔥
"""

import os
import sys
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state_manager import StateManager, BlockType
from core.memory_system import MemorySystem
from core.postgres_manager import create_postgres_manager_from_env


class Neo4jSyncError(Exception):
    """Neo4j sync errors"""
    pass


class Neo4jSyncService:
    """
    Synchronizes the AI's memories into Neo4j graph (PostgreSQL-only!).
    
    Features:
    - Full sync (PostgreSQL + ChromaDB → Neo4j)
    - Incremental sync (detect changes, update delta)
    - Relationship detection (tags, references, etc.)
    - Real-time updates via WebSocket broadcast
    """
    
    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        postgres_manager=None,
        chromadb_path: Optional[str] = None
    ):
        """
        Initialize Neo4j sync service.
        
        Args:
            neo4j_uri: Neo4j connection URI (defaults to env var)
            neo4j_user: Neo4j username (defaults to env var)
            neo4j_password: Neo4j password (defaults to env var)
            postgres_manager: PostgreSQL manager instance (REQUIRED!)
            chromadb_path: ChromaDB storage path
        """
        # Load from environment if not provided
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD", "neo4j_pw")
        
        chromadb_path = chromadb_path or os.getenv("CHROMADB_PATH", "./data/chromadb")
        
        # PostgreSQL is REQUIRED!
        if not postgres_manager:
            postgres_manager = create_postgres_manager_from_env()
        if not postgres_manager:
            raise Neo4jSyncError("PostgreSQL manager is REQUIRED! Configure .env and ensure PostgreSQL is running.")
        
        # Initialize state manager (PostgreSQL-backed)
        self.state_manager = StateManager(postgres_manager=postgres_manager)
        
        # Initialize memory system (optional - only if Ollama available)
        try:
            self.memory_system = MemorySystem(
                chromadb_path=chromadb_path,
                ollama_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
            )
        except Exception as e:
            print(f"⚠️  Memory system not available: {e}")
            self.memory_system = None
        
        # Initialize Neo4j driver
        try:
            self.driver: Driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
                max_connection_lifetime=3600
            )
            
            # Test connection
            self.driver.verify_connectivity()
            print(f"✅ Neo4j connected: {self.neo4j_uri}")
            
            # Create indexes
            self._create_indexes()
        
        except (ServiceUnavailable, AuthError) as e:
            raise Neo4jSyncError(f"Failed to connect to Neo4j: {e}")
        
        except Exception as e:
            raise Neo4jSyncError(f"Unexpected Neo4j error: {e}")
    
    def close(self):
        """Close Neo4j driver"""
        if self.driver:
            self.driver.close()
            print("✅ Neo4j connection closed")
    
    def _create_indexes(self):
        """Create Neo4j indexes for performance"""
        with self.driver.session() as session:
            indexes = [
                "CREATE INDEX core_memory_id IF NOT EXISTS FOR (cm:CoreMemory) ON (cm.id)",
                "CREATE INDEX archival_memory_id IF NOT EXISTS FOR (am:ArchivalMemory) ON (am.id)",
                "CREATE INDEX tag_name IF NOT EXISTS FOR (t:Tag) ON (t.name)",
                "CREATE INDEX conversation_id IF NOT EXISTS FOR (conv:Conversation) ON (conv.id)",
                "CREATE INDEX message_id IF NOT EXISTS FOR (msg:Message) ON (msg.id)",
                "CREATE INDEX tool_name IF NOT EXISTS FOR (tool:Tool) ON (tool.name)",
                "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    print(f"⚠️  Index creation warning: {e}")
        
        print("✅ Neo4j indexes created")
    
    def execute_query(self, query: str, params: Dict[str, Any]) -> List[Dict]:
        """
        Execute Cypher query and return results.
        
        Args:
            query: Cypher query string
            params: Query parameters
            
        Returns:
            List of result records as dicts
        """
        with self.driver.session() as session:
            result = session.run(query, params)
            return [dict(record) for record in result]
    
    def clear_graph(self):
        """Delete all nodes and relationships (use with caution!)"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("✅ Graph cleared")
    
    # ============================================
    # SYNC CORE MEMORIES
    # ============================================
    
    def sync_core_memories(self):
        """Sync core memory blocks from SQLite to Neo4j"""
        blocks = self.state_manager.list_blocks(include_hidden=True)
        
        print(f"🔄 Syncing {len(blocks)} core memory blocks...")
        
        with self.driver.session() as session:
            for block in blocks:
                # Calculate fill percentage
                fill_percent = (len(block.content) / block.limit * 100) if block.limit > 0 else 0
                
                # MERGE node (upsert)
                session.run("""
                    MERGE (cm:CoreMemory {id: $id})
                    SET cm.label = $label,
                        cm.content = $content,
                        cm.block_type = $block_type,
                        cm.limit = $limit,
                        cm.fill_percent = $fill_percent,
                        cm.read_only = $read_only,
                        cm.description = $description,
                        cm.hidden = $hidden,
                        cm.created_at = datetime($created_at),
                        cm.updated_at = datetime($updated_at),
                        cm.metadata = $metadata
                """, {
                    "id": block.label,
                    "label": block.label,
                    "content": block.content,
                    "block_type": block.block_type.value,
                    "limit": block.limit,
                    "fill_percent": round(fill_percent, 2),
                    "read_only": block.read_only,
                    "description": block.description,
                    "hidden": block.hidden,
                    "created_at": block.created_at.isoformat(),
                    "updated_at": block.updated_at.isoformat(),
                    "metadata": str(block.metadata)
                })
        
        print(f"✅ Synced {len(blocks)} core memories")
    
    # ============================================
    # SYNC ARCHIVAL MEMORIES
    # ============================================
    
    def sync_archival_memories(self, limit: int = 1000):
        """
        Sync archival memories from ChromaDB to Neo4j.
        
        Args:
            limit: Max memories to sync (prevents overload)
        """
        if not self.memory_system:
            print("⚠️  Memory system not available - skipping archival sync")
            return
        
        try:
            stats = self.memory_system.get_stats()
            total_memories = stats.get('total_memories', 0)
            
            if total_memories == 0:
                print("ℹ️  No archival memories to sync")
                return
            
            print(f"🔄 Syncing up to {min(limit, total_memories)} archival memories...")
            
            # Get all memories (TODO: paginate for large datasets)
            collection = self.memory_system.collection
            results = collection.get(limit=limit, include=['metadatas', 'documents'])
            
            with self.driver.session() as session:
                for i, doc in enumerate(results['documents']):
                    memory_id = results['ids'][i]
                    metadata = results['metadatas'][i]
                    
                    # Parse metadata
                    category = metadata.get('category', 'fact')
                    importance = int(metadata.get('importance', 5))
                    tags_str = metadata.get('tags', '')
                    tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                    timestamp = metadata.get('timestamp', datetime.utcnow().isoformat())
                    
                    # MERGE archival memory node
                    session.run("""
                        MERGE (am:ArchivalMemory {id: $id})
                        SET am.content = $content,
                            am.category = $category,
                            am.importance = $importance,
                            am.tags = $tags,
                            am.timestamp = datetime($timestamp),
                            am.metadata = $metadata
                    """, {
                        "id": memory_id,
                        "content": doc,
                        "category": category,
                        "importance": importance,
                        "tags": tags,
                        "timestamp": timestamp,
                        "metadata": str(metadata)
                    })
                    
                    # Create tag nodes and relationships
                    for tag in tags:
                        if not tag:
                            continue
                        
                        # MERGE tag node
                        session.run("""
                            MERGE (t:Tag {id: $tag_id})
                            ON CREATE SET t.name = $tag_name,
                                          t.count = 1,
                                          t.category = 'general',
                                          t.created_at = datetime()
                            ON MATCH SET t.count = t.count + 1
                        """, {
                            "tag_id": tag.lower().replace(' ', '_'),
                            "tag_name": tag
                        })
                        
                        # Create TAGGED_WITH relationship
                        session.run("""
                            MATCH (am:ArchivalMemory {id: $memory_id})
                            MATCH (t:Tag {id: $tag_id})
                            MERGE (am)-[:TAGGED_WITH {assigned_at: datetime()}]->(t)
                        """, {
                            "memory_id": memory_id,
                            "tag_id": tag.lower().replace(' ', '_')
                        })
            
            print(f"✅ Synced {len(results['documents'])} archival memories")
        
        except Exception as e:
            print(f"❌ Error syncing archival memories: {e}")
    
    # ============================================
    # SYNC CONVERSATIONS
    # ============================================
    
    def sync_conversations(self):
        """Sync conversation sessions and messages from SQLite to Neo4j"""
        # Get all sessions
        with self.state_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, created_at, last_active, metadata FROM sessions")
            sessions = cursor.fetchall()
        
        if not sessions:
            print("ℹ️  No conversations to sync")
            return
        
        print(f"🔄 Syncing {len(sessions)} conversations...")
        
        with self.driver.session() as neo_session:
            for session in sessions:
                session_id = session[0]
                created_at = session[1]
                last_active = session[2]
                metadata = session[3]
                
                # Get messages for this session
                messages = self.state_manager.get_conversation(session_id)
                message_count = len(messages)
                
                # Calculate duration
                created_dt = datetime.fromisoformat(created_at)
                active_dt = datetime.fromisoformat(last_active)
                duration_minutes = (active_dt - created_dt).total_seconds() / 60
                
                # MERGE conversation node
                neo_session.run("""
                    MERGE (conv:Conversation {id: $id})
                    SET conv.created_at = datetime($created_at),
                        conv.last_active = datetime($last_active),
                        conv.message_count = $message_count,
                        conv.duration_minutes = $duration_minutes,
                        conv.metadata = $metadata
                """, {
                    "id": session_id,
                    "created_at": created_at,
                    "last_active": last_active,
                    "message_count": message_count,
                    "duration_minutes": round(duration_minutes, 2),
                    "metadata": metadata or "{}"
                })
                
                # Sync messages
                for i, msg in enumerate(messages):
                    content_preview = msg.content[:100] if msg.content else ""
                    token_count = len(msg.content) // 4  # Rough estimate
                    
                    # MERGE message node
                    neo_session.run("""
                        MERGE (msg:Message {id: $id})
                        SET msg.session_id = $session_id,
                            msg.role = $role,
                            msg.content = $content,
                            msg.content_preview = $content_preview,
                            msg.timestamp = datetime($timestamp),
                            msg.token_count = $token_count,
                            msg.metadata = $metadata
                    """, {
                        "id": msg.id,
                        "session_id": msg.session_id,
                        "role": msg.role,
                        "content": msg.content,
                        "content_preview": content_preview,
                        "timestamp": msg.timestamp.isoformat(),
                        "token_count": token_count,
                        "metadata": str(msg.metadata or {})
                    })
                    
                    # Create HAS_MESSAGE relationship
                    neo_session.run("""
                        MATCH (conv:Conversation {id: $session_id})
                        MATCH (msg:Message {id: $msg_id})
                        MERGE (conv)-[:HAS_MESSAGE {sequence: $sequence}]->(msg)
                    """, {
                        "session_id": session_id,
                        "msg_id": msg.id,
                        "sequence": i + 1
                    })
        
        print(f"✅ Synced {len(sessions)} conversations")
    
    # ============================================
    # SYNC TOOLS
    # ============================================
    
    def sync_tools(self):
        """Create tool nodes (static for now - from memory_tools.py)"""
        tools = [
            {
                "id": "core_memory_append",
                "name": "Core Memory Append",
                "description": "Append content to a core memory block",
                "category": "core_memory",
                "parameters": '{"content": "string", "block_name": "string"}'
            },
            {
                "id": "core_memory_replace",
                "name": "Core Memory Replace",
                "description": "Replace content in a core memory block",
                "category": "core_memory",
                "parameters": '{"old_content": "string", "new_content": "string", "block_name": "string"}'
            },
            {
                "id": "archival_memory_insert",
                "name": "Archival Memory Insert",
                "description": "Insert new memory into archival storage",
                "category": "archival_memory",
                "parameters": '{"content": "string", "category": "string", "importance": "integer", "tags": "list"}'
            },
            {
                "id": "archival_memory_search",
                "name": "Archival Memory Search",
                "description": "Search archival memories semantically",
                "category": "archival_memory",
                "parameters": '{"query": "string", "n_results": "integer", "min_importance": "integer"}'
            },
            {
                "id": "conversation_search",
                "name": "Conversation Search",
                "description": "Search conversation history",
                "category": "conversation",
                "parameters": '{"query": "string", "limit": "integer"}'
            },
            {
                "id": "send_message",
                "name": "Send Message",
                "description": "Send message to user",
                "category": "communication",
                "parameters": '{"message": "string"}'
            }
        ]
        
        print(f"🔄 Syncing {len(tools)} tools...")
        
        with self.driver.session() as session:
            for tool in tools:
                session.run("""
                    MERGE (tool:Tool {id: $id})
                    SET tool.name = $name,
                        tool.description = $description,
                        tool.category = $category,
                        tool.parameters = $parameters,
                        tool.usage_count = coalesce(tool.usage_count, 0),
                        tool.last_used = coalesce(tool.last_used, datetime())
                """, tool)
        
        print(f"✅ Synced {len(tools)} tools")
    
    # ============================================
    # SYNC PEOPLE (TODO: Extract from memories)
    # ============================================
    
    def sync_people(self):
        """
        Create person nodes (hardcoded for now - TODO: extract from memories).
        """
        people = [
            {
                "id": "user",
                "name": "User",
                "relationship": "user",
                "description": "The user who interacts with the assistant",
                "first_mentioned": datetime.utcnow().isoformat(),
                "mention_count": 0,
                "metadata": '{"pronouns": "they/them", "timezone": "UTC"}'
            },
            {
                "id": "assistant",
                "name": "Assistant",
                "relationship": "friend",
                "description": "User's friend",
                "first_mentioned": datetime.utcnow().isoformat(),
                "mention_count": 0,
                "metadata": '{}'
            }
        ]
        
        print(f"🔄 Syncing {len(people)} people...")
        
        with self.driver.session() as session:
            for person in people:
                session.run("""
                    MERGE (p:Person {id: $id})
                    SET p.name = $name,
                        p.relationship = $relationship,
                        p.description = $description,
                        p.first_mentioned = datetime($first_mentioned),
                        p.mention_count = coalesce(p.mention_count, $mention_count),
                        p.metadata = $metadata
                """, person)
        
        print(f"✅ Synced {len(people)} people")
    
    # ============================================
    # FULL SYNC
    # ============================================
    
    async def sync_all(self):
        """Run full sync of all data"""
        print("\n" + "="*60)
        print("🔄 FULL GRAPH SYNC STARTED")
        print("="*60)
        
        try:
            # Sync in order (dependencies matter!)
            self.sync_core_memories()
            self.sync_archival_memories(limit=1000)
            self.sync_conversations()
            self.sync_tools()
            self.sync_people()
            
            print("\n" + "="*60)
            print("✅ FULL GRAPH SYNC COMPLETED")
            print("="*60)
        
        except Exception as e:
            print(f"\n❌ SYNC FAILED: {e}")
            raise


# ============================================
# CLI TESTING
# ============================================

async def main():
    """Test the sync service"""
    print("\n🧪 TESTING NEO4J SYNC SERVICE")
    print("="*60)
    
    try:
        # Initialize sync service
        sync = Neo4jSyncService()
        
        # Run full sync
        await sync.sync_all()
        
        # Get stats
        print("\n📊 Graph Statistics:")
        stats = sync.execute_query("""
            MATCH (n)
            RETURN labels(n)[0] as type, count(*) as count
            ORDER BY count DESC
        """, {})
        
        for stat in stats:
            print(f"   {stat['type']}: {stat['count']}")
        
        # Close connection
        sync.close()
        
        print("\n✅ TEST COMPLETED!")
    
    except Neo4jSyncError as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nℹ️  Make sure Neo4j is running:")
        print("   1. Start Neo4j Desktop")
        print("   2. Create database 'substrate-graph'")
        print("   3. Set password (default: neo4j_pw)")
        print("   4. Start the database")


if __name__ == "__main__":
    asyncio.run(main())

