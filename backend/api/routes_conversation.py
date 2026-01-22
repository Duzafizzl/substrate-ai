#!/usr/bin/env python3
"""
Conversation History API Routes
PostgreSQL-ONLY - No SQLite fallbacks!
"""

from flask import Blueprint, jsonify, request
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint
conversation_bp = Blueprint('conversation', __name__)

# Global managers (will be set by init function)
_postgres_manager = None
_consciousness_loop = None


def init_conversation_routes(state_manager=None, consciousness_loop=None, postgres_manager=None):
    """Initialize conversation routes with dependencies"""
    global _postgres_manager, _consciousness_loop
    _postgres_manager = postgres_manager
    _consciousness_loop = consciousness_loop
    
    if not _postgres_manager:
        logger.warning("⚠️  PostgresManager not provided - conversation routes may fail!")


def _get_active_agent_id():
    """Get the first active agent's ID from PostgreSQL"""
    if not _postgres_manager:
        raise Exception("PostgreSQL not available")
    
    agents = _postgres_manager.get_all_agents()
    if not agents:
        raise Exception("No agents found in PostgreSQL")
    
    return agents[0].id


@conversation_bp.route('/api/conversation/<session_id>', methods=['GET'])
def get_conversation(session_id='default'):
    """
    Get full conversation history for a session.
    
    Args:
        session_id: Session ID (default: "default")
        
    Query params:
        limit: Max messages to return (default: 1000)
        offset: Skip N messages (default: 0)
        
    Returns:
        {
            "session_id": "default",
            "messages": [...],
            "total": 42
        }
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 503
        
        limit = int(request.args.get('limit', 1000))
        offset = int(request.args.get('offset', 0))
        
        # Get agent ID
        agent_id = _get_active_agent_id()
        
        # Get messages from PostgreSQL
        pg_messages = _postgres_manager.get_messages(
            agent_id=agent_id,
            session_id=session_id,
            limit=limit
        )
        
        # Convert to frontend format
        messages = []
        for msg in pg_messages:
            # Parse metadata if it's a string
            metadata = msg.metadata
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            elif metadata is None:
                metadata = {}
            
            # Parse tool_calls if it's a string
            tool_calls = msg.tool_calls
            if isinstance(tool_calls, str):
                try:
                    tool_calls = json.loads(tool_calls)
                except:
                    tool_calls = None
            
            # Ensure tool_calls is an array
            if tool_calls and not isinstance(tool_calls, list):
                if isinstance(tool_calls, dict):
                    tool_calls = [tool_calls] if tool_calls else None
                else:
                    tool_calls = None
            
            # Extract message_type from metadata
            message_type = metadata.get('message_type', 'system' if msg.role == 'system' else 'inbox')
            reasoning_time = metadata.get('reasoning_time', 0)
            
            messages.append({
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat() if msg.created_at else '',
                'message_type': message_type,
                'tool_calls': tool_calls if tool_calls else [],
                'thinking': msg.thinking,
                'reasoning_time': reasoning_time,
                'metadata': metadata
            })
        
        # Apply offset
        if offset > 0:
            messages = messages[offset:]
        
        logger.info(f"📬 GET /conversation/{session_id} → {len(messages)} messages (PostgreSQL)")
        
        return jsonify({
            'session_id': session_id,
            'messages': messages,
            'total': len(messages)
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/api/conversation/<session_id>/clear', methods=['POST'])
def clear_conversation(session_id='default'):
    """
    Clear conversation history for a session.
    
    Args:
        session_id: Session ID to clear
        
    Query params:
        backend: Whether to clear backend storage (default: true)
                 If false, only returns success for UI-only clear
        
    Returns:
        {"success": true, "cleared": N}
    """
    try:
        # Check if this is a backend clear or UI-only clear
        backend_clear = request.args.get('backend', 'true').lower() == 'true'
        
        if not backend_clear:
            # UI-only clear - just acknowledge
            logger.info(f"🧹 POST /conversation/{session_id}/clear?backend=false → UI-only clear")
            return jsonify({
                'success': True,
                'cleared': 0,
                'message': 'UI cleared (backend data preserved)'
            })
        
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 503
        
        # Get agent ID
        agent_id = _get_active_agent_id()
        
        # Count before delete
        pg_messages = _postgres_manager.get_messages(
            agent_id=agent_id,
            session_id=session_id,
            limit=100000
        )
        cleared_count = len(pg_messages)
        
        # Delete from PostgreSQL
        _postgres_manager.delete_messages(
            agent_id=agent_id,
            session_id=session_id
        )
        
        logger.warning(f"🗑️  POST /conversation/{session_id}/clear → Cleared {cleared_count} messages (PostgreSQL)")
        
        return jsonify({
            'success': True,
            'cleared': cleared_count
        })
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/api/conversation/<session_id>/summarize', methods=['POST'])
def trigger_summary(session_id='default'):
    """
    Manually trigger conversation summary generation.
    
    Args:
        session_id: Session ID to summarize
        
    Returns:
        {
            "success": true,
            "summary_id": 123,
            "message_count": 150,
            "from_timestamp": "...",
            "to_timestamp": "..."
        }
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 503
        
        if not _consciousness_loop:
            return jsonify({'error': 'Consciousness loop not initialized'}), 500
        
        logger.info(f"📝 POST /conversation/{session_id}/summarize → Manual summary trigger")
        
        # Get agent ID
        agent_id = _get_active_agent_id()
        
        # Get all messages for this session
        all_messages = _postgres_manager.get_messages(
            agent_id=agent_id,
            session_id=session_id,
            limit=100000
        )
        
        if not all_messages:
            return jsonify({
                'success': False,
                'error': 'No messages to summarize'
            }), 400
        
        # Convert to format for summary generator
        messages_to_summarize = []
        for msg in all_messages:
            messages_to_summarize.append({
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat() if msg.created_at else ''
            })
        
        logger.info(f"📝 Summarizing {len(messages_to_summarize)} messages...")
        
        # Generate summary
        from core.summary_generator import SummaryGenerator
        
        generator = SummaryGenerator(postgres_manager=_postgres_manager)
        summary_result = generator.generate_summary(
            messages=messages_to_summarize,
            session_id=session_id
        )
        
        # Add summary as system message
        import uuid
        summary_msg_id = f"msg-{uuid.uuid4()}"
        
        from_ts = datetime.fromisoformat(summary_result['from_timestamp'])
        to_ts = datetime.fromisoformat(summary_result['to_timestamp'])
        
        summary_content = f"""📝 **ZUSAMMENFASSUNG**

**Zeitraum:** {from_ts.strftime('%d.%m.%Y %H:%M')} - {to_ts.strftime('%d.%m.%Y %H:%M')}  
**Nachrichten:** {summary_result['message_count']}

{summary_result['summary']}"""
        
        _postgres_manager.add_message(
            message_id=summary_msg_id,
            agent_id=agent_id,
            session_id=session_id,
            role='system',
            content=summary_content,
            metadata={'message_type': 'system', 'is_summary': True}
        )
        
        logger.info(f"✅ Summary saved (id: {summary_msg_id})")
        
        return jsonify({
            'success': True,
            'message_id': summary_msg_id,
            'message_count': summary_result['message_count'],
            'from_timestamp': summary_result['from_timestamp'],
            'to_timestamp': summary_result['to_timestamp'],
            'token_count': summary_result.get('token_count', 0)
        })
        
    except Exception as e:
        logger.error(f"Error triggering summary: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
