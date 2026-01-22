#!/usr/bin/env python3
"""
Graph API Routes for Substrate AI

RESTful endpoints for graph visualization + Graph RAG.
Works with or without Neo4j - falls back to local DB if Neo4j unavailable.

Endpoints:
- GET  /api/graph/nodes - Get all nodes (with filters)
- GET  /api/graph/edges - Get all relationships (with filters)
- GET  /api/graph/search - Search graph by content
- GET  /api/graph/node/:id - Get single node with neighbors
- GET  /api/graph/stats - Get graph statistics
- POST /api/graph/sync - Trigger manual sync (Neo4j only)
- POST /api/graph/rag - Graph RAG context retrieval

Built for public release - no hardcoded paths or personal data!
"""

import os
import json
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime
from flask import Blueprint, jsonify, request
import sys
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Graph API blueprint
graph_bp = Blueprint('graph', __name__)

# Import Neo4j sync service (optional)
try:
    from services.neo4j_sync import Neo4jSyncService
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("⚠️  Neo4j sync service not available - using local DB fallback")

# Global managers (set via init function)
_postgres_manager = None
_state_manager = None
_memory_system = None
_emotional_analyzer = None


def init_graph_routes(postgres_manager=None, state_manager=None, memory_system=None):
    """Initialize graph routes with dependencies"""
    global _postgres_manager, _state_manager, _memory_system, _emotional_analyzer
    _postgres_manager = postgres_manager
    _state_manager = state_manager
    _memory_system = memory_system
    try:
        from services.emotional_analyzer import EmotionalAnalyzer
        _emotional_analyzer = EmotionalAnalyzer()
    except:
        _emotional_analyzer = None


# ============================================
# LOCAL DB FALLBACK (No Neo4j needed!)
# ============================================

def get_nodes_from_local_db():
    """Get graph nodes directly from PostgreSQL (no Neo4j)"""
    if not _state_manager and not _postgres_manager:
        return jsonify({'error': 'Database not available', 'nodes': [], 'count': 0}), 503
    
    nodes = []
    tags = {}  # Track tags: {tag_name: count}
    people = {}  # Track people mentions: {name: count}
    tools = {}  # Track tools: {tool_name: count}
    
    # Get core memory blocks from PostgreSQL (preferred) or SQLite (fallback)
    blocks = state_manager.get_all_memory_blocks()
    for block in blocks:
        # Handle both dict (PostgreSQL) and object (SQLite) formats
        label = block.get('label') if isinstance(block, dict) else block.label
        content = block.get('content', '') if isinstance(block, dict) else block.content
        limit = block.get('limit', 2000) if isinstance(block, dict) else block.limit
        block_type = block.get('block_type', 'custom') if isinstance(block, dict) else block.block_type.value
        read_only = block.get('read_only', False) if isinstance(block, dict) else block.read_only
        
        fill_percent = (len(content) / limit * 100) if limit > 0 else 0
        
        # Main block node
        nodes.append({
            'id': label,
            'type': 'CoreMemory',
            'label': label.title(),
            'color': '#FF8C00',
            'size': 35 + (fill_percent / 3),
            'properties': {
                'content': content[:200] + '...' if len(content) > 200 else content,
                'fill_percent': round(fill_percent, 1),
                'block_type': block_type,
                'read_only': read_only
            }
        })
        
        # Extract hashtags from content
        hashtags = re.findall(r'#(\w+)', content.lower())
        for tag in hashtags:
            tags[tag] = tags.get(tag, 0) + 1
    
    # Get archival memories from PostgreSQL (preferred) or ChromaDB (fallback)
    try:
        from core.postgres_manager import create_postgres_manager_from_env
        pg = create_postgres_manager_from_env()
        if pg:
            with pg._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT agent_id FROM memories WHERE memory_type = 'archival'")
                agent_ids = [row[0] for row in cursor.fetchall()]
                cursor.close()
            
            for agent_id in agent_ids[:1]:  # Only first agent for now
                memories = pg.get_memories(agent_id, memory_type='archival')
                for memory in memories[:100]:  # Limit to 100 for graph
                    metadata = memory.metadata or {}
                    importance = metadata.get('importance', 5)
                    if isinstance(importance, str):
                        importance = int(float(importance))
                    category = metadata.get('category', 'fact')
                    
                    nodes.append({
                        'id': memory.id,
                        'type': 'ArchivalMemory',
                        'label': memory.content[:30] + '...' if len(memory.content) > 30 else memory.content,
                        'color': '#4ECDC4',
                        'size': 20 + (importance * 3),
                        'properties': {
                            'content': memory.content[:200] + '...' if len(memory.content) > 200 else memory.content,
                            'importance': importance,
                            'category': category,
                            'agent_id': agent_id
                        }
                    })
                    
                    if category:
                        tags[category] = tags.get(category, 0) + 1
        else:
            raise Exception("PostgreSQL not available")
    except Exception as pg_error:
        # Fallback to ChromaDB
        if memory_system:
            try:
                stats = memory_system.get_stats()
                total = stats.get('total_memories', 0)
                if total > 0:
                    collection = memory_system.collection
                    results = collection.get(limit=min(50, total), include=['metadatas', 'documents'])
                    
                    for i, doc in enumerate(results['documents']):
                        mem_id = results['ids'][i]
                        metadata = results['metadatas'][i]
                        importance = int(metadata.get('importance', 5))
                        category = metadata.get('category', 'fact')
                        
                        nodes.append({
                            'id': mem_id,
                            'type': 'ArchivalMemory',
                            'label': doc[:30] + '...' if len(doc) > 30 else doc,
                            'color': '#4ECDC4',
                            'size': 20 + (importance * 3),
                            'properties': {
                                'content': doc[:200] + '...' if len(doc) > 200 else doc,
                                'importance': importance,
                                'category': category
                            }
                        })
                        
                        if category:
                            tags[category] = tags.get(category, 0) + 1
            except Exception as e:
                print(f"⚠️  Could not load archival memories from ChromaDB: {e}")
    
    # Get conversations (significant ones only)
    try:
        with state_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.created_at, s.last_active, COUNT(m.id) as msg_count
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                GROUP BY s.id
                HAVING msg_count > 5
                ORDER BY msg_count DESC
                LIMIT 50
            """)
            sessions = cursor.fetchall()
            
            for session in sessions:
                session_id = session[0]
                msg_count = session[3] if len(session) > 3 else 0
                
                if msg_count == 0:
                    continue
                
                # Get first user message as label
                messages = state_manager.get_conversation(session_id, limit=1)
                conversation_label = f"Session ({msg_count} msgs)"
                if messages:
                    first_user = next((m for m in messages if m.role == 'user'), None)
                    if first_user:
                        theme = first_user.content[:50].strip()
                        if len(theme) > 47:
                            theme = theme[:47] + "..."
                        conversation_label = theme
                
                nodes.append({
                    'id': session_id,
                    'type': 'Conversation',
                    'label': conversation_label,
                    'color': '#1E90FF',
                    'size': 25 + min(msg_count * 2, 40),
                    'properties': {
                        'message_count': msg_count,
                        'created_at': session[1],
                        'last_active': session[2]
                    }
                })
    except Exception as e:
        print(f"⚠️  Could not load conversations: {e}")
    
    # Add Tag nodes
    for tag_name, count in tags.items():
        nodes.append({
            'id': f'tag_{tag_name}',
            'type': 'Tag',
            'label': f'#{tag_name}',
            'color': '#FFFF00',
            'size': 20 + min(count * 3, 30),
            'properties': {
                'count': count,
                'tag': tag_name
            }
        })
    
    return jsonify({
        'nodes': nodes,
        'count': len(nodes),
        'source': 'local_db',
        'metadata': {
            'tags': len(tags),
            'people': len(people),
            'tools': len(tools)
        }
    })


def get_edges_from_local_db():
    """Get graph edges directly from SQLite/ChromaDB (no Neo4j)"""
    if not state_manager:
        return jsonify({'error': 'Database not available', 'edges': [], 'count': 0}), 503
    
    edges = []
    
    # Get all blocks for reference
    blocks = state_manager.get_all_memory_blocks()
    
    # Connect core memories to tags
    for block in blocks:
        label = block.get('label') if isinstance(block, dict) else block.label
        content = block.get('content', '') if isinstance(block, dict) else block.content
        
        # Extract hashtags
        hashtags = re.findall(r'#(\w+)', content.lower())
        for tag in set(hashtags):
            edges.append({
                'source': label,
                'target': f'tag_{tag}',
                'type': 'TAGGED_WITH',
                'color': '#FF8C00',
                'width': 2,
                'properties': {}
            })
    
    # Connect persona ↔ human
    if len(blocks) >= 2:
        persona_block = next((b for b in blocks if (b.get('label') if isinstance(b, dict) else b.label) == 'persona'), None)
        human_block = next((b for b in blocks if (b.get('label') if isinstance(b, dict) else b.label) == 'human'), None)
        if persona_block and human_block:
            edges.append({
                'source': 'persona',
                'target': 'human',
                'type': 'REFERENCES',
                'color': '#FF69B4',
                'width': 3,
                'properties': {}
            })
    
    return jsonify({
        'edges': edges,
        'count': len(edges),
        'source': 'local_db'
    })


# ============================================
# API ENDPOINTS
# ============================================

@graph_bp.route('/api/graph/nodes', methods=['GET'])
def get_nodes():
    """Get all graph nodes with optional filters"""
    # Always use local DB fallback (works without Neo4j)
    return get_nodes_from_local_db()


@graph_bp.route('/api/graph/edges', methods=['GET'])
def get_edges():
    """Get all graph relationships with optional filters"""
    # Always use local DB fallback (works without Neo4j)
    return get_edges_from_local_db()


@graph_bp.route('/api/graph/stats', methods=['GET'])
def get_graph_stats():
    """Get graph statistics"""
    stats = {'nodes': {}, 'edges': {}, 'metadata': {'source': 'local_db'}}
    
    if state_manager:
        blocks = state_manager.get_all_memory_blocks()
        stats['nodes']['CoreMemory'] = len(blocks)
        
        try:
            with state_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sessions")
                stats['nodes']['Conversation'] = cursor.fetchone()[0]
        except:
            stats['nodes']['Conversation'] = 0
    
    if memory_system:
        try:
            mem_stats = memory_system.get_stats()
            stats['nodes']['ArchivalMemory'] = mem_stats.get('total_memories', 0)
        except:
            stats['nodes']['ArchivalMemory'] = 0
    
    return jsonify(stats)


@graph_bp.route('/api/graph/rag', methods=['POST'])
def graph_rag_retrieve():
    """
    Graph RAG (Retrieval-Augmented Generation)
    
    Uses graph traversal to find relevant context.
    
    Body:
        {
            "query": "What do you know about coding?",
            "depth": 2,  // optional
            "max_length": 2000  // optional
        }
    """
    try:
        from services.graph_rag import GraphRAG
        
        body = request.get_json() or {}
        query = body.get('query', '')
        depth = body.get('depth', 2)
        max_length = body.get('max_length', 2000)
        
        if not query:
            return jsonify({'error': 'query required'}), 400
        
        # Retrieve context via graph traversal
        rag = GraphRAG()
        result = rag.retrieve(query, depth=depth, max_context_length=max_length)
        
        return jsonify({
            'context': result.content,
            'nodes': result.nodes,
            'edges': result.edges,
            'relevance_score': result.relevance_score,
            'path_description': result.path_description,
            'metadata': {
                'query': query,
                'depth': depth,
                'node_count': len(result.nodes),
                'edge_count': len(result.edges)
            }
        })
        
    except Exception as e:
        print(f"❌ Error in Graph RAG: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'fallback_context': 'Error retrieving graph context. Using fallback.'
        }), 500


# Export for use in server
__all__ = ['graph_bp']

