#!/usr/bin/env python3
"""
PostgreSQL Integration Routes

New API endpoints for PostgreSQL-powered features:
- Message continuity
- Memory coherence
- Daemon status
- Performance stats

These endpoints expose the new PostgreSQL magic to the frontend!
"""

from flask import Blueprint, jsonify, request
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Create blueprint
postgres_bp = Blueprint('postgres', __name__)

# Global managers (will be set by init function)
_postgres_manager = None
_message_manager = None
_memory_engine = None
_daemon = None


def init_postgres_routes(
    postgres_manager=None,
    message_manager=None,
    memory_engine=None,
    daemon=None
):
    """
    Initialize PostgreSQL routes with managers.
    
    If managers are None, routes will return 404 (PostgreSQL not enabled).
    """
    global _postgres_manager, _message_manager, _memory_engine, _daemon
    _postgres_manager = postgres_manager
    _message_manager = message_manager
    _memory_engine = memory_engine
    _daemon = daemon
    
    logger.info(f"PostgreSQL routes initialized")
    logger.info(f"   Postgres: {'✅' if postgres_manager else '❌'}")
    logger.info(f"   Messages: {'✅' if message_manager else '❌'}")
    logger.info(f"   Memory: {'✅' if memory_engine else '❌'}")
    logger.info(f"   Daemon: {'✅' if daemon else '❌'}")


@postgres_bp.route('/api/postgres/status', methods=['GET'])
def get_postgres_status():
    """
    Get PostgreSQL integration status.
    
    Returns:
        {
            "enabled": true,
            "database": "substrate_ai",
            "connection_pool": {"min": 1, "max": 10},
            "daemon_mode": true
        }
    """
    if not _postgres_manager:
        return jsonify({
            "enabled": False,
            "message": "PostgreSQL not configured"
        })
    
    try:
        stats = _postgres_manager.get_stats()
        
        return jsonify({
            "enabled": True,
            "database": _postgres_manager.database,
            "host": _postgres_manager.host,
            "stats": stats,
            "daemon_mode": _daemon is not None
        })
    except Exception as e:
        logger.error(f"Error getting PostgreSQL status: {e}")
        return jsonify({"error": str(e)}), 500


@postgres_bp.route('/api/postgres/messages/<agent_id>', methods=['GET'])
def get_agent_messages(agent_id='default'):
    """
    Get messages for an agent from PostgreSQL.
    
    Query params:
        session_id: Filter by session (optional)
        limit: Max messages (default: 50)
    
    Returns:
        {
            "messages": [...],
            "total": 42,
            "source": "postgresql"
        }
    """
    if not _message_manager:
        return jsonify({"error": "PostgreSQL not enabled"}), 404
    
    try:
        session_id = request.args.get('session_id')
        limit = int(request.args.get('limit', 50))
        
        messages = _message_manager.get_messages(
            agent_id=agent_id,
            session_id=session_id,
            limit=limit
        )
        
        # Convert to dict format
        messages_dict = [msg.to_dict() for msg in messages]
        
        return jsonify({
            "messages": messages_dict,
            "total": len(messages_dict),
            "source": "postgresql"
        })
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return jsonify({"error": str(e)}), 500


@postgres_bp.route('/api/postgres/memory/<agent_id>', methods=['GET'])
def get_agent_memory(agent_id='default'):
    """
    Get coherent memory state for an agent.
    
    Query params:
        session_id: Session ID (required)
        max_tokens: Max tokens for context (default: 100000)
    
    Returns:
        {
            "core_memory": [...],
            "recall_memory": [...],
            "archival_memory": [...],
            "total_tokens": 42000
        }
    """
    if not _memory_engine:
        return jsonify({"error": "PostgreSQL not enabled"}), 404
    
    try:
        session_id = request.args.get('session_id', 'default')
        max_tokens = int(request.args.get('max_tokens', 100000))
        
        state = _memory_engine.get_coherent_memory_state(
            agent_id=agent_id,
            session_id=session_id,
            max_tokens=max_tokens
        )
        
        return jsonify(state.to_dict())
    except Exception as e:
        logger.error(f"Error getting memory state: {e}")
        return jsonify({"error": str(e)}), 500


@postgres_bp.route('/api/postgres/context-window/<agent_id>', methods=['GET'])
def get_context_window(agent_id='default'):
    """
    Get optimized context window for agent.
    
    Query params:
        session_id: Session ID (required)
        max_tokens: Max tokens (default: 100000)
    
    Returns:
        {
            "messages": [...],
            "total_tokens": 12000,
            "truncated": false,
            "summary_used": false
        }
    """
    if not _message_manager:
        return jsonify({"error": "PostgreSQL not enabled"}), 404
    
    try:
        session_id = request.args.get('session_id', 'default')
        max_tokens = int(request.args.get('max_tokens', 100000))
        
        context = _message_manager.get_context_window(
            agent_id=agent_id,
            session_id=session_id,
            max_tokens=max_tokens
        )
        
        return jsonify(context.to_dict())
    except Exception as e:
        logger.error(f"Error getting context window: {e}")
        return jsonify({"error": str(e)}), 500


@postgres_bp.route('/api/postgres/sessions/<agent_id>', methods=['GET'])
def get_agent_sessions(agent_id='default'):
    """
    Get active sessions for agent.
    
    Query params:
        limit: Max sessions (default: 10)
    
    Returns:
        {
            "sessions": [
                {"id": "...", "created_at": "...", "message_count": 42},
                ...
            ]
        }
    """
    if not _message_manager:
        return jsonify({"error": "PostgreSQL not enabled"}), 404
    
    try:
        limit = int(request.args.get('limit', 10))
        
        sessions = _message_manager.get_active_sessions(
            agent_id=agent_id,
            limit=limit
        )
        
        return jsonify({
            "sessions": sessions,
            "total": len(sessions)
        })
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return jsonify({"error": str(e)}), 500


@postgres_bp.route('/api/postgres/daemon/status', methods=['GET'])
def get_daemon_status():
    """
    Get daemon status (if daemon mode enabled).
    
    Returns:
        {
            "running": true,
            "agents_loaded": 3,
            "max_agents": 100,
            "heartbeat_interval": 60,
            "agents": [...]
        }
    """
    if not _daemon:
        return jsonify({
            "enabled": False,
            "message": "Daemon mode not enabled"
        })
    
    try:
        status = _daemon.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting daemon status: {e}")
        return jsonify({"error": str(e)}), 500


@postgres_bp.route('/api/postgres/performance', methods=['GET'])
def get_performance_stats():
    """
    Get performance statistics.
    
    Tests:
    - Message retrieval speed
    - Memory loading speed
    - Cache hit rates
    
    Returns:
        {
            "message_retrieval_ms": 2.5,
            "memory_loading_ms": 15.3,
            "postgres_stats": {...}
        }
    """
    if not _postgres_manager or not _message_manager:
        return jsonify({"error": "PostgreSQL not enabled"}), 404
    
    try:
        # Test message retrieval speed
        start = time.time()
        messages = _message_manager.get_messages('default', 'default', limit=50)
        message_time = (time.time() - start) * 1000  # ms
        
        # Test memory loading speed (if available)
        memory_time = None
        if _memory_engine:
            start = time.time()
            state = _memory_engine.get_coherent_memory_state('default', 'default')
            memory_time = (time.time() - start) * 1000  # ms
        
        # Get database stats
        stats = _postgres_manager.get_stats()
        
        return jsonify({
            "message_retrieval_ms": round(message_time, 2),
            "memory_loading_ms": round(memory_time, 2) if memory_time else None,
            "postgres_stats": stats,
            "timestamp": time.time()
        })
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        return jsonify({"error": str(e)}), 500


@postgres_bp.route('/api/postgres/health', methods=['GET'])
def postgres_health():
    """
    Quick health check for PostgreSQL integration.
    
    Returns:
        {
            "status": "healthy",
            "database_connected": true,
            "managers_loaded": true
        }
    """
    if not _postgres_manager:
        return jsonify({
            "status": "disabled",
            "database_connected": False,
            "managers_loaded": False,
            "message": "PostgreSQL not configured"
        })
    
    try:
        # Quick database check
        stats = _postgres_manager.get_stats()
        
        return jsonify({
            "status": "healthy",
            "database_connected": True,
            "managers_loaded": True,
            "total_messages": stats.get('messages', 0),
            "total_memories": stats.get('memories', 0)
        })
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "database_connected": False,
            "error": str(e)
        }), 500

