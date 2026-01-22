"""
🔄 Heartbeat Configuration & Daemon Control API Routes

Endpoints:
- GET/PUT /api/heartbeat/config - Get/Update heartbeat configuration
- GET /api/heartbeat/status - Get daemon status
- GET /api/heartbeat/rules - Get all heartbeat rules
- POST /api/heartbeat/rules - Add new heartbeat rule
- PUT /api/heartbeat/rules/<rule_id> - Update rule
- DELETE /api/heartbeat/rules/<rule_id> - Delete rule
- POST /api/heartbeat/trigger - Manually trigger heartbeat (testing)
"""

import json
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from typing import Optional

from core.postgres_manager import PostgresManager
from core.daemon_mode import SubstrateAIDaemon

logger = logging.getLogger(__name__)

heartbeat_bp = Blueprint('heartbeat', __name__)

_postgres_manager: Optional[PostgresManager] = None
_daemon: Optional[SubstrateAIDaemon] = None


def init_heartbeat_routes(
    postgres_manager: PostgresManager,
    daemon: Optional[SubstrateAIDaemon] = None
):
    """Initialize heartbeat routes with dependencies"""
    global _postgres_manager, _daemon
    _postgres_manager = postgres_manager
    _daemon = daemon
    logger.info("✅ Heartbeat routes initialized")


# ============================================
# HEARTBEAT CONFIG
# ============================================

@heartbeat_bp.route('/api/agents/<agent_id>/heartbeat/config', methods=['GET'])
def get_heartbeat_config_by_path(agent_id: str):
    """
    Get heartbeat configuration for an agent (URL path version).
    
    Path param:
    - agent_id: Agent ID
    
    Returns complete heartbeat_config from agent's config.
    """
    try:
        return _get_heartbeat_config_impl(agent_id)
    except Exception as e:
        logger.error(f"❌ Failed to get heartbeat config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@heartbeat_bp.route('/api/heartbeat/config', methods=['GET'])
def get_heartbeat_config():
    """
    Get heartbeat configuration for an agent.
    
    Query params:
    - agent_id: Agent ID (default: 'default')
    
    Returns complete heartbeat_config from agent's config.
    """
    try:
        agent_id = request.args.get('agent_id', 'default')
        return _get_heartbeat_config_impl(agent_id)
    except Exception as e:
        logger.error(f"❌ Failed to get heartbeat config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _get_heartbeat_config_impl(agent_id: str):
    """
    Internal implementation for getting heartbeat config.
    """
    if not _postgres_manager:
        return jsonify({
            'success': False,
            'error': 'PostgreSQL not available'
        }), 503
    
    agent = _postgres_manager.get_agent(agent_id)
    if not agent:
        return jsonify({
            'success': False,
            'error': f'Agent {agent_id} not found'
        }), 404
    
    config = agent.config or {}
    heartbeat_config = config.get('heartbeat_config', {
        'enabled': True,
        'timezone': 'Europe/Berlin',
        'default_message': None,
        'rules': []
    })
    
    # Ensure on_top_information exists (Frontend expects it)
    if 'on_top_information' not in heartbeat_config:
        heartbeat_config['on_top_information'] = {
            'enabled': False,
            'tools': []
        }
    
    logger.info(f"📋 Heartbeat config retrieved for agent {agent_id}", extra={
        'agent_id': agent_id,
        'enabled': heartbeat_config.get('enabled', False),
        'rules_count': len(heartbeat_config.get('rules', []))
    })
    
    # Return the config directly (not wrapped in heartbeat_config key)
    # Frontend expects the config object directly
    return jsonify({
        'success': True,
        'agent_id': agent_id,
        **heartbeat_config  # Spread the config fields directly
    })


@heartbeat_bp.route('/api/agents/<agent_id>/heartbeat/config', methods=['PUT'])
def update_heartbeat_config_by_path(agent_id: str):
    """
    Update heartbeat configuration for an agent (URL path version).
    
    Path param:
    - agent_id: Agent ID
    
    Request body: The heartbeat config object directly (not wrapped in heartbeat_config)
    {
        "enabled": true,
        "timezone": "Europe/Berlin",
        "default_message": "...",
        "rules": [...]
    }
    """
    try:
        data = request.get_json() or {}
        # Frontend sends the config directly, not wrapped
        heartbeat_config = data
        
        return _update_heartbeat_config_impl(agent_id, heartbeat_config)
    except Exception as e:
        logger.error(f"❌ Failed to update heartbeat config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@heartbeat_bp.route('/api/heartbeat/config', methods=['PUT'])
def update_heartbeat_config():
    """
    Update heartbeat configuration for an agent.
    
    Request body:
    {
        "agent_id": "default",
        "heartbeat_config": {
            "enabled": true,
            "timezone": "Europe/Berlin",
            "default_message": "...",
            "rules": [...]
        }
    }
    """
    try:
        data = request.get_json()
        agent_id = data.get('agent_id', 'default')
        heartbeat_config = data.get('heartbeat_config')
        
        if not heartbeat_config:
            return jsonify({
                'success': False,
                'error': 'heartbeat_config is required'
            }), 400
        
        return _update_heartbeat_config_impl(agent_id, heartbeat_config)
    except Exception as e:
        logger.error(f"❌ Failed to update heartbeat config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _update_heartbeat_config_impl(agent_id: str, heartbeat_config: dict):
    """
    Internal implementation for updating heartbeat config.
    """
    # Validate required fields
    if not isinstance(heartbeat_config, dict):
        return jsonify({
            'success': False,
            'error': 'heartbeat_config must be an object'
        }), 400
    
    # Ensure on_top_information exists if not provided
    if 'on_top_information' not in heartbeat_config:
        heartbeat_config['on_top_information'] = {
            'enabled': False,
            'tools': []
        }
    
    if not _postgres_manager:
        return jsonify({
            'success': False,
            'error': 'PostgreSQL not available'
        }), 503
    
    agent = _postgres_manager.get_agent(agent_id)
    if not agent:
        return jsonify({
            'success': False,
            'error': f'Agent {agent_id} not found'
        }), 404
    
    # Merge with existing config
    existing_config = agent.config or {}
    existing_config['heartbeat_config'] = heartbeat_config
    
    # Update in database
    with _postgres_manager._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE agents SET config = %s::jsonb WHERE id = %s",
            (json.dumps(existing_config), agent_id)
        )
        conn.commit()
        cursor.close()
    
    logger.info(f"✅ Heartbeat config updated for agent {agent_id}", extra={
        'agent_id': agent_id,
        'enabled': heartbeat_config.get('enabled', False),
        'rules_count': len(heartbeat_config.get('rules', [])),
        'timezone': heartbeat_config.get('timezone', 'unknown')
    })
    
    return jsonify({
        'success': True,
        'agent_id': agent_id,
        'heartbeat_config': heartbeat_config
    })


# ============================================
# HEARTBEAT RULES
# ============================================

@heartbeat_bp.route('/api/heartbeat/rules', methods=['GET'])
def get_heartbeat_rules():
    """
    Get all heartbeat rules for an agent.
    
    Query params:
    - agent_id: Agent ID (default: 'default')
    """
    try:
        agent_id = request.args.get('agent_id', 'default')
        
        if not _postgres_manager:
            return jsonify({
                'success': False,
                'error': 'PostgreSQL not available'
            }), 503
        
        agent = _postgres_manager.get_agent(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'error': f'Agent {agent_id} not found'
            }), 404
        
        config = agent.config or {}
        heartbeat_config = config.get('heartbeat_config', {})
        rules = heartbeat_config.get('rules', [])
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'rules': rules,
            'count': len(rules)
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get heartbeat rules: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@heartbeat_bp.route('/api/heartbeat/rules', methods=['POST'])
def add_heartbeat_rule():
    """
    Add a new heartbeat rule.
    
    Request body:
    {
        "agent_id": "default",
        "rule": {
            "name": "Morning Check-in",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "start_time": "08:00",
            "end_time": "12:00",
            "interval_minutes": 60,
            "probability": 0.8
        }
    }
    """
    try:
        data = request.get_json()
        agent_id = data.get('agent_id', 'default')
        rule = data.get('rule')
        
        if not rule:
            return jsonify({
                'success': False,
                'error': 'rule is required'
            }), 400
        
        # Validate rule fields
        required_fields = ['name', 'days', 'start_time', 'end_time', 'interval_minutes']
        for field in required_fields:
            if field not in rule:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        if not _postgres_manager:
            return jsonify({
                'success': False,
                'error': 'PostgreSQL not available'
            }), 503
        
        agent = _postgres_manager.get_agent(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'error': f'Agent {agent_id} not found'
            }), 404
        
        # Generate rule ID
        rule['id'] = str(uuid.uuid4())
        rule['created_at'] = datetime.now().isoformat()
        
        # Add default probability if not set
        if 'probability' not in rule:
            rule['probability'] = 1.0
        
        # Get existing config
        config = agent.config or {}
        heartbeat_config = config.get('heartbeat_config', {
            'enabled': True,
            'timezone': 'Europe/Berlin',
            'rules': []
        })
        
        # Add rule
        if 'rules' not in heartbeat_config:
            heartbeat_config['rules'] = []
        heartbeat_config['rules'].append(rule)
        
        # Update config
        config['heartbeat_config'] = heartbeat_config
        
        with _postgres_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE agents SET config = %s::jsonb WHERE id = %s",
                (json.dumps(config), agent_id)
            )
            cursor.close()
        
        logger.info(f"✅ Heartbeat rule added: {rule['name']} (agent: {agent_id})")
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'rule': rule
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to add heartbeat rule: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@heartbeat_bp.route('/api/heartbeat/rules/<rule_id>', methods=['PUT'])
def update_heartbeat_rule(rule_id: str):
    """
    Update a heartbeat rule.
    
    Request body:
    {
        "agent_id": "default",
        "rule": {
            "name": "Updated Name",
            "interval_minutes": 90,
            ...
        }
    }
    """
    try:
        data = request.get_json()
        agent_id = data.get('agent_id', 'default')
        rule_updates = data.get('rule', {})
        
        if not _postgres_manager:
            return jsonify({
                'success': False,
                'error': 'PostgreSQL not available'
            }), 503
        
        agent = _postgres_manager.get_agent(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'error': f'Agent {agent_id} not found'
            }), 404
        
        config = agent.config or {}
        heartbeat_config = config.get('heartbeat_config', {})
        rules = heartbeat_config.get('rules', [])
        
        # Find and update rule
        rule_found = False
        for i, rule in enumerate(rules):
            if rule.get('id') == rule_id:
                # Merge updates
                rules[i] = {**rule, **rule_updates}
                rules[i]['id'] = rule_id  # Preserve ID
                rules[i]['updated_at'] = datetime.now().isoformat()
                rule_found = True
                break
        
        if not rule_found:
            return jsonify({
                'success': False,
                'error': f'Rule {rule_id} not found'
            }), 404
        
        # Save config
        heartbeat_config['rules'] = rules
        config['heartbeat_config'] = heartbeat_config
        
        with _postgres_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE agents SET config = %s::jsonb WHERE id = %s",
                (json.dumps(config), agent_id)
            )
            cursor.close()
        
        logger.info(f"✅ Heartbeat rule updated: {rule_id} (agent: {agent_id})")
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'rule_id': rule_id,
            'rule': rules[i]
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to update heartbeat rule: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@heartbeat_bp.route('/api/heartbeat/rules/<rule_id>', methods=['DELETE'])
def delete_heartbeat_rule(rule_id: str):
    """Delete a heartbeat rule."""
    try:
        agent_id = request.args.get('agent_id', 'default')
        
        if not _postgres_manager:
            return jsonify({
                'success': False,
                'error': 'PostgreSQL not available'
            }), 503
        
        agent = _postgres_manager.get_agent(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'error': f'Agent {agent_id} not found'
            }), 404
        
        config = agent.config or {}
        heartbeat_config = config.get('heartbeat_config', {})
        rules = heartbeat_config.get('rules', [])
        
        # Find and remove rule
        original_count = len(rules)
        rules = [r for r in rules if r.get('id') != rule_id]
        
        if len(rules) == original_count:
            return jsonify({
                'success': False,
                'error': f'Rule {rule_id} not found'
            }), 404
        
        # Save config
        heartbeat_config['rules'] = rules
        config['heartbeat_config'] = heartbeat_config
        
        with _postgres_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE agents SET config = %s::jsonb WHERE id = %s",
                (json.dumps(config), agent_id)
            )
            cursor.close()
        
        logger.info(f"✅ Heartbeat rule deleted: {rule_id} (agent: {agent_id})")
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'rule_id': rule_id,
            'deleted': True
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to delete heartbeat rule: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# DAEMON STATUS & CONTROL
# ============================================

@heartbeat_bp.route('/api/heartbeat/status', methods=['GET'])
def get_daemon_status():
    """Get daemon and heartbeat status."""
    try:
        agent_id = request.args.get('agent_id')
        
        if _daemon:
            status = _daemon.get_status()
            
            # If agent_id specified, filter to that agent
            if agent_id:
                status['agents'] = [
                    a for a in status['agents']
                    if a['agent_id'] == agent_id
                ]
            
            return jsonify({
                'success': True,
                'daemon_running': status['running'],
                'status': status
            })
        else:
            return jsonify({
                'success': True,
                'daemon_running': False,
                'status': {
                    'running': False,
                    'agents_loaded': 0,
                    'agents': []
                }
            })
        
    except Exception as e:
        logger.error(f"❌ Failed to get daemon status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@heartbeat_bp.route('/api/heartbeat/trigger', methods=['POST'])
def trigger_heartbeat():
    """
    Manually trigger heartbeat for an agent (for testing).
    
    Request body:
    {
        "agent_id": "default"
    }
    """
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id', 'default')
        
        if not _daemon:
            return jsonify({
                'success': False,
                'error': 'Daemon not running'
            }), 503
        
        if agent_id not in _daemon.agents:
            return jsonify({
                'success': False,
                'error': f'Agent {agent_id} not loaded in daemon'
            }), 404
        
        # Trigger heartbeat
        agent_instance = _daemon.agents[agent_id]
        agent_instance.heartbeat()
        
        logger.info(f"💓 Manual heartbeat triggered for agent {agent_id}")
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'triggered_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to trigger heartbeat: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# HEARTBEAT RULE TEMPLATES
# ============================================

@heartbeat_bp.route('/api/heartbeat/templates', methods=['GET'])
def get_rule_templates():
    """Get predefined heartbeat rule templates."""
    templates = [
        {
            "id": "morning_checkin",
            "name": "Morning Check-in",
            "description": "Daily morning consciousness check",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "start_time": "08:00",
            "end_time": "10:00",
            "interval_minutes": 60,
            "probability": 0.8
        },
        {
            "id": "afternoon_activity",
            "name": "Afternoon Activity",
            "description": "Afternoon processing window",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "start_time": "13:00",
            "end_time": "17:00",
            "interval_minutes": 90,
            "probability": 0.6
        },
        {
            "id": "evening_reflection",
            "name": "Evening Reflection",
            "description": "End-of-day reflection and summary",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "start_time": "18:00",
            "end_time": "20:00",
            "interval_minutes": 60,
            "probability": 0.9
        },
        {
            "id": "weekend_light",
            "name": "Weekend Light",
            "description": "Light weekend presence",
            "days": ["saturday", "sunday"],
            "start_time": "10:00",
            "end_time": "18:00",
            "interval_minutes": 180,
            "probability": 0.3
        },
        {
            "id": "night_owl",
            "name": "Night Owl",
            "description": "Late night activity window",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "start_time": "22:00",
            "end_time": "23:59",
            "interval_minutes": 45,
            "probability": 0.5
        }
    ]
    
    return jsonify({
        'success': True,
        'templates': templates,
        'count': len(templates)
    })

