"""
Channels Management Routes
API endpoints for CRUD operations on channels/rooms.

Channels are organizational units for messages, similar to Discord channels.
Standard channels: heartbeat-log, task, reflection

CRITICAL RULE:
==============
ALL messages sent to channels MUST ALSO appear in the normal agent thread!
This ensures continuity - the agent thread always contains everything.
"""

import os
import logging
import uuid
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

channels_bp = Blueprint('channels', __name__)

# Module-level managers (initialized via init_channels_routes)
_state_manager = None
_postgres_manager = None


def init_channels_routes(state_manager, postgres_manager=None):
    """Initialize routes with state manager and postgres manager"""
    global _state_manager, _postgres_manager
    _state_manager = state_manager
    _postgres_manager = postgres_manager


# ============================================
# CHANNELS ENDPOINTS
# ============================================

@channels_bp.route('/api/channels', methods=['GET'])
def list_channels():
    """
    List all channels for an agent.
    
    Query params: 
        - agent_id (optional, defaults to current agent)
        - parent_id (optional, filter by parent channel)
        - include_children (optional, default: false)
        
    Returns: {channels: [...], count: N}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available - channels require PostgreSQL'}), 500
        
        # Get agent ID from query params or state
        agent_id = request.args.get('agent_id')
        if not agent_id or agent_id == 'default':
            if _state_manager:
                agent_state = _state_manager.get_agent_state()
                agent_id = agent_state.get('id', 'default')
            else:
                agent_id = 'default'
        
        # Get optional filters
        parent_id = request.args.get('parent_id')
        include_children = request.args.get('include_children', 'false').lower() == 'true'
        
        # Ensure default channels exist
        _ensure_default_channels(agent_id)
        
        # Get channels
        channels = _postgres_manager.list_channels(
            agent_id=agent_id,
            parent_id=parent_id,
            include_children=include_children
        )
        
        logger.info(f"📊 GET /api/channels → {len(channels)} channels for agent '{agent_id}'")
        return jsonify({
            'channels': channels,
            'count': len(channels)
        })
        
    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/api/channels', methods=['POST'])
def create_channel():
    """
    Create a new channel for an agent.
    
    Body: {
        name: string (required),
        description?: string,
        parent_id?: string,
        discord_channel_id?: string,
        discord_webhook_url?: string
    }
    
    Returns: {success: true, channel: {...}}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        data = request.json
        if not data or 'name' not in data:
            return jsonify({'error': 'name is required'}), 400
        
        # Get agent ID
        agent_id = data.get('agent_id')
        if not agent_id and _state_manager:
            agent_state = _state_manager.get_agent_state()
            agent_id = agent_state.get('id', 'default')
        
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'name cannot be empty'}), 400
        
        # Create channel
        channel = _postgres_manager.create_channel(
            agent_id=agent_id,
            name=name,
            description=data.get('description', '').strip(),
            parent_id=data.get('parent_id'),
            discord_channel_id=data.get('discord_channel_id'),
            discord_webhook_url=data.get('discord_webhook_url')
        )
        
        if channel:
            logger.info(f"✅ Created channel '{name}' for agent '{agent_id}'")
            return jsonify({
                'success': True,
                'channel': channel
            }), 201
        else:
            return jsonify({'error': 'Failed to create channel'}), 500
            
    except Exception as e:
        error_msg = str(e)
        if 'unique constraint' in error_msg.lower() or 'duplicate' in error_msg.lower():
            return jsonify({'error': f'Channel with this name already exists'}), 409
        logger.error(f"Error creating channel: {e}")
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/api/channels/<channel_id>', methods=['GET'])
def get_channel(channel_id):
    """
    Get a specific channel.
    
    Returns: {id, name, description, ...}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        # Get agent ID
        agent_id = request.args.get('agent_id', 'default')
        if agent_id == 'default' and _state_manager:
            agent_state = _state_manager.get_agent_state()
            agent_id = agent_state.get('id', 'default')
        
        channel = _postgres_manager.get_channel(channel_id, agent_id)
        
        if not channel:
            return jsonify({'error': 'Channel not found'}), 404
        
        return jsonify(channel)
        
    except Exception as e:
        logger.error(f"Error getting channel: {e}")
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/api/channels/<channel_id>', methods=['PUT'])
def update_channel(channel_id):
    """
    Update a channel.
    
    Body: {name?, description?}
    Returns: {success: true, ...}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get agent ID
        agent_id = 'default'
        if _state_manager:
            agent_state = _state_manager.get_agent_state()
            agent_id = agent_state.get('id', 'default')
        
        # Build update kwargs
        update_kwargs = {}
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'error': 'name cannot be empty'}), 400
            update_kwargs['name'] = name
        
        if 'description' in data:
            update_kwargs['description'] = data['description'].strip()
        
        if not update_kwargs:
            return jsonify({'error': 'No fields to update'}), 400
        
        updated = _postgres_manager.update_channel(channel_id, agent_id, **update_kwargs)
        
        if not updated:
            return jsonify({'error': 'Channel not found'}), 404
        
        logger.info(f"✅ Updated channel {channel_id}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error updating channel: {e}")
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/api/channels/<channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    """
    Delete a channel.
    
    Returns: {success: true}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        # Get agent ID
        agent_id = 'default'
        if _state_manager:
            agent_state = _state_manager.get_agent_state()
            agent_id = agent_state.get('id', 'default')
        
        deleted = _postgres_manager.delete_channel(channel_id, agent_id)
        
        if not deleted:
            return jsonify({'error': 'Channel not found'}), 404
        
        logger.info(f"✅ Deleted channel {channel_id}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# CHANNEL MESSAGES ENDPOINTS
# ============================================

@channels_bp.route('/api/channels/<channel_id>/messages', methods=['GET'])
def get_channel_messages(channel_id):
    """
    Get messages from a channel with optional filtering.
    
    Query params:
    - rule_id: Filter by rule ID
    - rule_name: Filter by rule name
    - date_from: Filter by date from (YYYY-MM-DD)
    - date_to: Filter by date to (YYYY-MM-DD)
    - limit: Max number of messages (default: 100)
    
    Returns: {messages: [...], count: N, filters: {...}}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        # Get agent ID
        agent_id = request.args.get('agent_id', 'default')
        if agent_id == 'default' and _state_manager:
            agent_state = _state_manager.get_agent_state()
            agent_id = agent_state.get('id', 'default')
        
        # Verify channel exists
        channel = _postgres_manager.get_channel(channel_id, agent_id)
        if not channel:
            return jsonify({'error': 'Channel not found'}), 404
        
        # Get filter parameters
        rule_id = request.args.get('rule_id')
        rule_name = request.args.get('rule_name')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        limit = int(request.args.get('limit', 100))
        
        messages = _postgres_manager.get_channel_messages(
            channel_id=channel_id,
            agent_id=agent_id,
            limit=limit,
            rule_id=rule_id,
            rule_name=rule_name,
            date_from=date_from,
            date_to=date_to
        )
        
        logger.info(f"📊 GET /api/channels/{channel_id}/messages → {len(messages)} messages")
        return jsonify({
            'messages': messages,
            'count': len(messages),
            'filters': {
                'rule_id': rule_id,
                'rule_name': rule_name,
                'date_from': date_from,
                'date_to': date_to
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting channel messages: {e}")
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/api/channels/<channel_id>/messages', methods=['POST'])
def send_channel_message(channel_id):
    """
    Send a message to a channel.
    
    CRITICAL: Message is posted to BOTH channel AND normal agent thread!
    
    Body: {
        content: string (required),
        role?: string (default: 'user'),
        metadata?: object
    }
    
    Returns: {success: true, channel_message_id, thread_message_id}
    """
    try:
        if not _postgres_manager:
            return jsonify({'error': 'PostgreSQL not available'}), 500
        
        data = request.json
        if not data or 'content' not in data:
            return jsonify({'error': 'content is required'}), 400
        
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'error': 'content cannot be empty'}), 400
        
        role = data.get('role', 'user')
        if role not in ['user', 'assistant', 'system', 'tool']:
            return jsonify({'error': f'Invalid role: {role}'}), 400
        
        metadata = data.get('metadata', {})
        
        # Get agent ID
        agent_id = 'default'
        if _state_manager:
            agent_state = _state_manager.get_agent_state()
            agent_id = agent_state.get('id', 'default')
        
        # Verify channel exists
        channel = _postgres_manager.get_channel(channel_id, agent_id)
        if not channel:
            return jsonify({'error': 'Channel not found'}), 404
        
        channel_name = channel['name']
        
        # Add channel info to metadata
        enhanced_metadata = {
            **(metadata or {}),
            'channel_id': channel_id,
            'channel_name': channel_name
        }
        
        import json as json_lib
        metadata_json = json_lib.dumps(enhanced_metadata)
        
        # Post to channel
        channel_msg = _postgres_manager.add_message(
            agent_id=agent_id,
            session_id=channel_name,
            role=role,
            content=content,
            metadata=enhanced_metadata
        )
        
        # Also post to main agent thread (for continuity)
        thread_msg = _postgres_manager.add_message(
            agent_id=agent_id,
            session_id=agent_id,
            role=role,
            content=content,
            metadata=enhanced_metadata
        )
        
        # Update channel_id on messages
        with _postgres_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE messages SET channel_id = %s WHERE id IN (%s, %s)",
                (channel_id, channel_msg.id, thread_msg.id)
            )
            cursor.close()
        
        logger.info(f"✅ Posted message to channel '{channel_name}' AND agent thread")
        
        return jsonify({
            'success': True,
            'message': 'Message sent to channel and agent thread',
            'channel_message_id': channel_msg.id,
            'thread_message_id': thread_msg.id,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'agent_id': agent_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error sending channel message: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# HELPER FUNCTIONS
# ============================================

def _ensure_default_channels(agent_id: str):
    """Ensure default channels exist for an agent"""
    try:
        if not _postgres_manager:
            return
        
        # Check if default channels exist
        channels = _postgres_manager.list_channels(agent_id)
        channel_names = [ch['name'] for ch in channels]
        
        default_channels = ['💓 heartbeat-log', '📋 task', '🧠 reflection']
        
        for ch_name in default_channels:
            if ch_name not in channel_names:
                logger.info(f"🔧 Creating default channel '{ch_name}' for agent '{agent_id}'")
                _postgres_manager._create_default_channels(agent_id)
                break  # _create_default_channels creates all of them
                
    except Exception as e:
        logger.warning(f"⚠️  Failed to ensure default channels: {e}")

