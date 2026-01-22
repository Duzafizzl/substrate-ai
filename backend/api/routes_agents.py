"""
Agent Management Routes
Endpoints for CRUD operations on agents

NOW WITH VERSION MANAGEMENT! 🎯
Every config/prompt change creates a version, allowing rollback.
"""

import os
import uuid
import logging
from flask import Blueprint, jsonify, request
from core.state_manager import StateManager
from core.version_manager import VersionManager

logger = logging.getLogger(__name__)

agents_bp = Blueprint('agents', __name__)

# Initialize state manager (will be overridden by server.py)
_state_manager = None
_version_manager = None
_postgres_manager = None

def init_agents_routes(state_manager, version_manager=None, postgres_manager=None):
    """Initialize routes with state manager, version manager, and postgres manager instances"""
    global _state_manager, _version_manager, _postgres_manager
    _state_manager = state_manager
    _postgres_manager = postgres_manager
    # VersionManager requires postgres_manager!
    if postgres_manager:
        _version_manager = version_manager or VersionManager(postgres_manager=postgres_manager)
    else:
        _version_manager = version_manager


@agents_bp.route('/api/agents', methods=['GET'])
def list_agents():
    """
    List all agents
    Returns: [{id, name, model, created_at, ...}]
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        agents = []
        
        # Check if PostgreSQL is available (multi-agent support!)
        from api.server import postgres_manager
        if postgres_manager:
            # Get agents from PostgreSQL
            with postgres_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, created_at, config
                    FROM agents
                    ORDER BY 
                        CASE WHEN id = '41dc0e38-bdb6-4563-a3b6-49aa0925ab14' THEN 0 ELSE 1 END,
                        created_at DESC
                """)
                rows = cursor.fetchall()
                
                for row in rows:
                    agent_id, name, created_at, config = row
                    # config is already a dict (psycopg2 handles JSONB)
                    model = config.get('model', 'unknown') if config else 'unknown'
                    
                    agents.append({
                        'id': agent_id,
                        'name': name,
                        'model': model,
                        'created_at': created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at),
                        'description': f'{name} - Multi-Agent',
                        'is_active': True
                    })
        
        # Fallback: Return current agent from StateManager (SQLite)
        if not agents:
            agent_state = _state_manager.get_agent_state()
            agents = [{
                'id': agent_state.get('id', 'default'),
                'name': agent_state.get('name', 'Assistant'),
                'model': agent_state.get('model', 'qwen/qwen-2.5-72b-instruct'),
                'created_at': agent_state.get('created_at', ''),
                'description': 'Substrate AI - Default Agent',
                'is_active': True
            }]
        
        return jsonify({
            'agents': agents,
            'count': len(agents)
        })
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents', methods=['POST'])
def create_agent():
    """
    Create a new agent
    Body: {name, agent_id?, model?, description?}
    
    Creates agent in PostgreSQL with:
    - Default channels
    - Default core memory blocks
    - Initial config
    
    If agent_id is provided, it will be used (must be valid UUID format).
    Otherwise, a new UUID will be generated.
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        data = request.json
        if not data or 'name' not in data:
            return jsonify({'error': 'name is required'}), 400
        
        name = data['name'].strip()
        if not name:
            return jsonify({'error': 'name cannot be empty'}), 400
        
        # Get model from request or use default
        model = data.get('model') or os.getenv('DEFAULT_MODEL', 'qwen/qwen-2.5-72b-instruct')
        description = data.get('description', '').strip()
        
        # Check if PostgreSQL is available first
        from api.server import postgres_manager
        if not postgres_manager:
            return jsonify({'error': 'PostgreSQL not available. Multi-agent requires PostgreSQL.'}), 500
        
        # Get agent_id from request or generate new UUID
        if 'agent_id' in data and data['agent_id']:
            agent_id = data['agent_id'].strip()
            # Validate UUID format
            try:
                uuid.UUID(agent_id)  # This will raise ValueError if invalid
            except ValueError:
                return jsonify({'error': 'agent_id must be a valid UUID format'}), 400
            
            # Check if agent already exists
            existing_agent = postgres_manager.get_agent(agent_id)
            if existing_agent:
                return jsonify({
                    'error': f'Agent with ID {agent_id} already exists',
                    'existing_agent': {
                        'id': existing_agent.id,
                        'name': existing_agent.name,
                        'created_at': existing_agent.created_at.isoformat() if hasattr(existing_agent.created_at, 'isoformat') else str(existing_agent.created_at)
                    }
                }), 409  # Conflict
        else:
            # Generate UUID for agent
            agent_id = str(uuid.uuid4())
        
        logger.info(f"🆕 Creating new agent: {name} (ID: {agent_id})")
        
        # Create agent config
        config = {
            'model': model,
            'temperature': 0.7,
            'max_tokens': None,
            'top_p': 1.0,
            'frequency_penalty': 0.0,
            'presence_penalty': 0.0,
            'context_window': int(os.getenv('DEFAULT_CONTEXT_WINDOW', '128000')),
            'reasoning_enabled': False,
            'max_reasoning_tokens': None
        }
        
        # Create agent in PostgreSQL
        db_agent = postgres_manager.create_agent(
            agent_id=agent_id,
            name=name,
            config=config
        )
        
        logger.info(f"✅ Agent created in PostgreSQL: {db_agent.name} ({db_agent.id})")
        
        # Initialize default core memory
        from core.memory_coherence import MemoryCoherenceEngine
        from core.message_continuity import MessageContinuityManager
        
        message_manager = MessageContinuityManager(postgres_manager)
        memory_engine = MemoryCoherenceEngine(
            postgres_manager=postgres_manager,
            message_manager=message_manager
        )
        
        memory_engine.initialize_default_core_memory(agent_id, name)
        logger.info(f"✅ Default core memory initialized for {name}")
        
        # Create default channels
        postgres_manager._create_default_channels(agent_id)
        logger.info(f"✅ Default channels created for {name}")
        
        # If agent name contains "alex" (case-insensitive), initialize Alex-specific memory
        if 'alex' in name.lower():
            try:
                memory_engine.initialize_alex_start_memory(agent_id)
                logger.info(f"✅ Alex-specific memory initialized for {name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Alex memory: {e}")
        
        logger.info(f"🎉 Agent '{name}' fully initialized and ready!")
        
        return jsonify({
            'success': True,
            'agent': {
                'id': agent_id,
                'name': name,
                'model': model,
                'description': description or f'{name} - Multi-Agent',
                'created_at': db_agent.created_at.isoformat() if hasattr(db_agent.created_at, 'isoformat') else str(db_agent.created_at),
                'is_active': True,
                'config': config
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """
    Get agent details
    Returns the REAL UUID, not 'default'!
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        # Resolve 'default' to actual agent_id
        original_agent_id = agent_id
        if agent_id == 'default':
            agent_state = _state_manager.get_agent_state()
            actual_agent_id = agent_state.get('id', 'default')
            if actual_agent_id != 'default':
                agent_id = actual_agent_id
                logger.info(f"🔄 Resolved 'default' ({original_agent_id}) to actual agent_id: {agent_id}")
        
        # Try PostgreSQL first
        from api.server import postgres_manager
        if postgres_manager:
            agent = postgres_manager.get_agent(agent_id)
            if agent:
                config = agent.config or {}
                return jsonify({
                    'id': agent.id,  # REAL UUID!
                    'name': agent.name,
                    'model': config.get('model', 'qwen/qwen-2.5-72b-instruct'),
                    'created_at': agent.created_at.isoformat() if hasattr(agent.created_at, 'isoformat') else str(agent.created_at),
                    'description': f'{agent.name} - Multi-Agent',
                    'is_active': True,
                    'config': config
                })
        
        # Fallback: Use state manager
        agent_state = _state_manager.get_agent_state()
        
        agent = {
            'id': agent_state.get('id', agent_id),  # Use real UUID from DB!
            'name': agent_state.get('name', 'Assistant'),
            'model': agent_state.get('model', 'qwen/qwen-2.5-72b-instruct'),
            'created_at': agent_state.get('created_at', ''),
            'description': 'Substrate AI - Default Agent',
            'is_active': True,
            'config': agent_state.get('config', {})
        }
        
        return jsonify(agent)
        
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>', methods=['PUT'])
def update_agent(agent_id):
    """
    Update agent name and/or description
    Body: {name?, description?}
    
    Updates agent in PostgreSQL database.
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Check if PostgreSQL is available
        from api.server import postgres_manager
        if not postgres_manager:
            return jsonify({'error': 'PostgreSQL not available. Multi-agent requires PostgreSQL.'}), 500
        
        # Validate agent exists
        existing_agent = postgres_manager.get_agent(agent_id)
        if not existing_agent:
            return jsonify({'error': f'Agent with ID {agent_id} not found'}), 404
        
        # Prepare update parameters
        update_name = None
        if 'name' in data:
            new_name = data['name'].strip()
            if not new_name:
                return jsonify({'error': 'name cannot be empty'}), 400
            if new_name != existing_agent.name:
                update_name = new_name
                logger.info(f"📝 Updating agent name: '{existing_agent.name}' → '{new_name}'")
        
        # Update agent in PostgreSQL
        updated_agent = postgres_manager.update_agent(
            agent_id=agent_id,
            name=update_name
        )
        
        if not updated_agent:
            return jsonify({'error': 'Failed to update agent'}), 500
        
        logger.info(f"✅ Agent '{updated_agent.id}' updated successfully")
        logger.info(f"   Name: {updated_agent.name}")
        
        # Get model from config for response
        config = updated_agent.config or {}
        model = config.get('model', 'unknown')
        
        return jsonify({
            'success': True,
            'agent': {
                'id': updated_agent.id,
                'name': updated_agent.name,
                'model': model,
                'created_at': updated_agent.created_at.isoformat() if hasattr(updated_agent.created_at, 'isoformat') else str(updated_agent.created_at),
                'is_active': True,
                'config': config
            }
        })
        
    except ValueError as e:
        logger.error(f"Validation error updating agent {agent_id}: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/config', methods=['GET'])
def get_agent_config(agent_id):
    """
    Get agent LLM configuration
    Returns: {model, temperature, max_tokens, ...}
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        # Get ACTUAL config from DB (not just defaults!)
        agent_state = _state_manager.get_agent_state()
        stored_config = agent_state.get('config', {})
        
        # Merge with defaults (for missing fields)
        default_config = {
            'model': os.getenv('DEFAULT_MODEL', 'qwen/qwen-2.5-72b-instruct'),
            'temperature': 0.7,
            'max_tokens': None,
            'top_p': 1.0,
            'frequency_penalty': 0.0,
            'presence_penalty': 0.0,
            'context_window': int(os.getenv('DEFAULT_CONTEXT_WINDOW', '128000')),
            # Reasoning Settings 🧠
            'reasoning_enabled': False,
            'max_reasoning_tokens': None
        }
        
        # Override defaults with stored values
        config = {**default_config, **stored_config}
        
        logger.info(f"📊 GET /config → Returning agent config for '{agent_id}'")
        logger.info(f"   Model: {config['model']} | Reasoning: {config.get('reasoning_enabled', False)}")
        
        return jsonify(config)
        
    except Exception as e:
        logger.error(f"Error getting agent config: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/config', methods=['PUT'])
def update_agent_config(agent_id):
    """
    Update agent LLM configuration
    Body: {model?, temperature?, max_tokens?, change_description?}
    
    NOW WITH AUTO-VERSIONING + .ENV SYNC! 🎯
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get current config
        agent_state = _state_manager.get_agent_state()
        current_config = agent_state.get('config', {})
        
        # Track changes for description
        changes = []
        env_updates = {}  # Track .env updates
        
        # Update fields
        allowed_fields = ['model', 'temperature', 'max_tokens', 'top_p', 
                         'frequency_penalty', 'presence_penalty', 'context_window',
                         'reasoning_enabled', 'max_reasoning_tokens']  # Reasoning settings 🧠
        
        for field in allowed_fields:
            if field in data and data[field] != current_config.get(field):
                old_val = current_config.get(field)
                new_val = data[field]
                changes.append(f"{field}: {old_val} → {new_val}")
                current_config[field] = new_val
        
                # Track .env updates for critical fields
                if field == 'model':
                    env_updates['DEFAULT_MODEL'] = new_val
                    env_updates['DEFAULT_LLM_MODEL'] = new_val
                elif field == 'context_window':
                    env_updates['DEFAULT_CONTEXT_WINDOW'] = str(new_val)
        
        # Save to DB
        agent_state['config'] = current_config
        _state_manager.update_agent_state(agent_state)
        
        # Save to .env file! (CRITICAL - prevents config loss!)
        if env_updates:
            try:
                from core.config_writer import ConfigWriter
                writer = ConfigWriter()
                writer.update_env_file(env_updates)
                logger.info(f"✅ Config synced to .env file: {list(env_updates.keys())}")
            except Exception as e:
                logger.error(f"⚠️ Failed to update .env file: {e}")
                # Continue anyway - DB is updated
        
        # CREATE VERSION! 🎯
        if _version_manager and changes:
            change_desc = data.get('change_description') or f"Updated config: {', '.join(changes)}"
            
            # Get system prompt and memory blocks for version
            system_prompt = _state_manager.get_state('agent:system_prompt', '')
            blocks = _state_manager.get_all_memory_blocks()
            memory_blocks = {block['label']: block.get('content', '') for block in blocks}
            
            version = _version_manager.create_version(
                agent_id=agent_id,
                config=current_config,
                system_prompt=system_prompt,
                memory_blocks=memory_blocks,
                change_description=change_desc
            )
            
            logger.info(f"📦 VERSION CREATED: {version.version_id}")
            logger.info(f"   Changes: {', '.join(changes)}")
        
        logger.info(f"✅ PUT /config → Agent config updated for '{agent_id}'")
        return jsonify({
            'success': True,
            'config': current_config,
            'changes': changes
        })
        
    except Exception as e:
        logger.error(f"Error updating agent config: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/memory/blocks', methods=['GET'])
def get_memory_blocks(agent_id):
    """
    Get all memory blocks for an agent
    Returns: [{label, value, limit, description, read_only, ...}]
    
    NOW READS FROM POSTGRESQL!
    
    If agent_id is 'default', resolves to actual agent UUID from StateManager.
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        # Resolve 'default' to actual agent_id
        original_agent_id = agent_id
        if agent_id == 'default':
            agent_state = _state_manager.get_agent_state()
            actual_agent_id = agent_state.get('id', 'default')
            if actual_agent_id != 'default':
                agent_id = actual_agent_id
                logger.info(f"🔄 Resolved 'default' ({original_agent_id}) to actual agent_id: {agent_id}")
            else:
                logger.warning(f"⚠️  Could not resolve 'default' - no agent_id in state manager")
        
        ui_blocks = []
        
        # Try PostgreSQL first
        from api.server import postgres_manager
        if postgres_manager:
            logger.info(f"🔍 Searching for memory blocks with agent_id: {agent_id}")
            with postgres_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT label, content, created_at, metadata
                    FROM memories
                    WHERE agent_id = %s AND memory_type = 'core'
                    ORDER BY label
                """, (agent_id,))
                
                rows = cursor.fetchall()
                
                logger.info(f"📦 Found {len(rows)} memory blocks for agent {agent_id}")
                
                # Debug: List all found blocks
                if rows:
                    for label, content, created_at, metadata in rows:
                        logger.info(f"   • {label}: {len(content or '')} chars")
                else:
                    # Check if agent exists
                    cursor.execute("SELECT id, name FROM agents WHERE id = %s", (agent_id,))
                    agent_row = cursor.fetchone()
                    if agent_row:
                        agent_name = agent_row[1]
                        logger.warning(f"⚠️  Agent {agent_id} ({agent_name}) exists but has no memory blocks!")
                        
                        # If this is ALEX, try to create Alex-specific blocks
                        if agent_name.upper() == "ALEX" or "alex" in agent_name.lower():
                            logger.info(f"   This is Alex - creating Alex-specific memory blocks...")
                            try:
                                from api.server import memory_engine
                                if memory_engine:
                                    # Check if default blocks exist first
                                    cursor.execute("""
                                        SELECT COUNT(*) FROM memories
                                        WHERE agent_id = %s AND memory_type = 'core'
                                    """, (agent_id,))
                                    block_count = cursor.fetchone()[0]
                                    
                                    if block_count == 0:
                                        # Create default blocks first
                                        memory_engine.initialize_default_core_memory(agent_id, agent_name)
                                        logger.info(f"   ✅ Created default core memory blocks")
                                    
                                    # Create Alex-specific blocks
                                    memory_engine.initialize_alex_start_memory(agent_id)
                                    logger.info(f"   ✅ Created Alex-specific memory blocks")
                                    
                                    # Reload blocks
                                    cursor.execute("""
                                        SELECT label, content, created_at, metadata
                                        FROM memories
                                        WHERE agent_id = %s AND memory_type = 'core'
                                        ORDER BY label
                                    """, (agent_id,))
                                    rows = cursor.fetchall()
                                    logger.info(f"   📦 Now found {len(rows)} memory blocks")
                            except Exception as e:
                                logger.error(f"   ❌ Failed to create Alex blocks: {e}")
                                import traceback
                                logger.error(traceback.format_exc())
                    else:
                        logger.warning(f"⚠️  Agent {agent_id} does not exist in database!")
                
                for label, content, created_at, metadata in rows:
                    # metadata is already a dict (psycopg2 handles JSONB)
                    meta = metadata if metadata else {}
                    
                    ui_blocks.append({
                        'label': label,
                        'value': content or '',
                        'limit': meta.get('limit', 2000),
                        'description': meta.get('description', ''),
                        'read_only': meta.get('read_only', False),
                        'metadata': meta,
                        'created_at': created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at),
                        'updated_at': meta.get('updated_at', '')
                    })
        
        # Fallback to SQLite (if PostgreSQL not available)
        if not ui_blocks:
            blocks = _state_manager.get_all_memory_blocks()
            for block in blocks:
                ui_blocks.append({
                    'label': block['label'],
                    'value': block.get('content', ''),
                    'limit': block.get('limit', 2000),
                    'description': block.get('description', ''),
                    'read_only': block.get('read_only', False),
                    'metadata': block.get('metadata', {}),
                    'created_at': block.get('created_at', ''),
                    'updated_at': block.get('updated_at', '')
                })
        
        logger.info(f"✅ Returning {len(ui_blocks)} memory blocks for agent {agent_id}")
        
        return jsonify({
            'blocks': ui_blocks,
            'count': len(ui_blocks)
        })
        
    except Exception as e:
        logger.error(f"Error getting memory blocks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/memory/blocks/<block_label>', methods=['GET'])
def get_memory_block(agent_id, block_label):
    """
    Get a specific memory block
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        block = _state_manager.get_memory_block(block_label)
        
        if not block:
            return jsonify({'error': f'Block "{block_label}" not found'}), 404
        
        return jsonify({
            'label': block['label'],
            'value': block.get('content', ''),  # MemoryBlock uses 'content' not 'value'
            'limit': block.get('limit', 2000),
            'description': block.get('description', ''),
            'read_only': block.get('read_only', False),
            'metadata': block.get('metadata', {}),
            'created_at': block.get('created_at', ''),
            'updated_at': block.get('updated_at', '')
        })
        
    except Exception as e:
        logger.error(f"Error getting memory block: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/memory/blocks/<block_label>', methods=['PUT'])
def update_memory_block(agent_id, block_label):
    """
    Update a memory block
    Body: {value?, description?, limit?, read_only?}
    
    NOW SAVES TO POSTGRESQL!
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Try PostgreSQL first
        from api.server import postgres_manager
        if postgres_manager:
            with postgres_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current block from PostgreSQL
                cursor.execute("""
                    SELECT content, metadata
                    FROM memories
                    WHERE agent_id = %s AND label = %s
                """, (agent_id, block_label))
                
                row = cursor.fetchone()
                if not row:
                    return jsonify({'error': f'Block "{block_label}" not found'}), 404
                
                current_content, current_metadata = row
                metadata = current_metadata if current_metadata else {}
                
                # Check if read-only
                if metadata.get('read_only') and 'value' in data:
                    return jsonify({'error': 'Cannot modify read-only block value'}), 403
                
                # Update fields
                new_content = current_content
                if 'value' in data:
                    new_content = data['value']
                
                if 'description' in data:
                    metadata['description'] = data['description']
                if 'limit' in data:
                    metadata['limit'] = data['limit']
                if 'read_only' in data:
                    metadata['read_only'] = data['read_only']
                
                # Update updated_at timestamp
                from datetime import datetime
                metadata['updated_at'] = datetime.now().isoformat()
                
                # Save to PostgreSQL
                import json
                cursor.execute("""
                    UPDATE memories
                    SET content = %s, metadata = %s::jsonb
                    WHERE agent_id = %s AND label = %s
                """, (new_content, json.dumps(metadata), agent_id, block_label))
                
                logger.info(f"✅ Updated memory block in PostgreSQL: {block_label}")
                
                return jsonify({
                    'success': True,
                    'block': {
                        'label': block_label,
                        'value': new_content,
                        'metadata': metadata
                    }
                })
        
        # Fallback to SQLite
        block = _state_manager.get_memory_block(block_label)
        if not block:
            return jsonify({'error': f'Block "{block_label}" not found'}), 404
        
        if block.get('read_only') and 'value' in data:
            return jsonify({'error': 'Cannot modify read-only block value'}), 403
        
        new_content = block.get('content', '')
        if 'value' in data:
            new_content = data['value']
        if 'description' in data:
            block['description'] = data['description']
        if 'limit' in data:
            block['limit'] = data['limit']
        if 'read_only' in data:
            block['read_only'] = data['read_only']
        
        _state_manager.update_memory_block(block_label, new_content, block)
        
        logger.info(f"Updated memory block in SQLite: {block_label}")
        return jsonify({
            'success': True,
            'block': block
        })
        
    except Exception as e:
        logger.error(f"Error updating memory block: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/memory/blocks', methods=['POST'])
def create_memory_block(agent_id):
    """
    Create a new memory block
    Body: {label, value, description?, limit?, read_only?}
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        data = request.json
        if not data or 'label' not in data or 'value' not in data:
            return jsonify({'error': 'label and value are required'}), 400
        
        label = data['label']
        value = data['value']
        description = data.get('description', '')
        limit = data.get('limit', 2000)
        read_only = data.get('read_only', False)
        
        # Check if block already exists
        existing = _state_manager.get_memory_block(label)
        if existing:
            return jsonify({'error': f'Block "{label}" already exists'}), 409
        
        # Create block
        block_data = {
            'label': label,
            'value': value,
            'description': description,
            'limit': limit,
            'read_only': read_only,
            'metadata': {}
        }
        
        _state_manager.create_memory_block(label, value, block_data)
        
        logger.info(f"Created memory block: {label}")
        return jsonify({
            'success': True,
            'block': block_data
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating memory block: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/system-prompt', methods=['GET'])
def get_system_prompt(agent_id):
    """
    Get agent system prompt
    Returns: {system_prompt: str}
    
    NOW AGENT-SPECIFIC! 🎯
    Loads system prompt from PostgreSQL agent.config['system_prompt']
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        # Resolve 'default' to actual agent_id
        original_agent_id = agent_id
        if agent_id == 'default':
            agent_state = _state_manager.get_agent_state()
            actual_agent_id = agent_state.get('id', 'default')
            if actual_agent_id != 'default':
                agent_id = actual_agent_id
                logger.info(f"🔄 Resolved 'default' ({original_agent_id}) to actual agent_id: {agent_id}")
        
        # Load agent-specific system prompt from PostgreSQL
        from api.server import postgres_manager
        if postgres_manager:
            agent = postgres_manager.get_agent(agent_id)
            if agent:
                config = agent.config or {}
                system_prompt = config.get('system_prompt', '')
                logger.info(f"📖 GET /system-prompt → Loaded for agent '{agent_id}' ({len(system_prompt)} chars)")
                return jsonify({
                    'system_prompt': system_prompt
                })
            else:
                logger.warning(f"⚠️  Agent {agent_id} not found in PostgreSQL")
                return jsonify({
                    'system_prompt': ''
                })
        
        # Fallback: Load from state manager (legacy)
        system_prompt = _state_manager.get_state('agent:system_prompt', '')
        logger.info(f"📖 GET /system-prompt → Loaded from state manager ({len(system_prompt)} chars)")
        
        return jsonify({
            'system_prompt': system_prompt
        })
        
    except Exception as e:
        logger.error(f"Error getting system prompt: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/system-prompt', methods=['PUT'])
def update_system_prompt(agent_id):
    """
    Update agent system prompt
    Body: {system_prompt: str, change_description?: str}
    
    NOW AGENT-SPECIFIC + AUTO-VERSIONING! 🎯
    Saves system prompt to PostgreSQL agent.config['system_prompt']
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        data = request.json
        if not data or 'system_prompt' not in data:
            return jsonify({'error': 'system_prompt is required'}), 400
        
        # Resolve 'default' to actual agent_id
        original_agent_id = agent_id
        if agent_id == 'default':
            agent_state = _state_manager.get_agent_state()
            actual_agent_id = agent_state.get('id', 'default')
            if actual_agent_id != 'default':
                agent_id = actual_agent_id
                logger.info(f"🔄 Resolved 'default' ({original_agent_id}) to actual agent_id: {agent_id}")
        
        new_prompt = data['system_prompt']
        
        # Get old prompt for versioning
        old_prompt = ''
        from api.server import postgres_manager
        if postgres_manager:
            agent = postgres_manager.get_agent(agent_id)
            if agent:
                config = agent.config or {}
                old_prompt = config.get('system_prompt', '')
                
                # Update agent config with new system prompt
                config['system_prompt'] = new_prompt
                postgres_manager.update_agent(
                    agent_id=agent_id,
                    config=config
                )
                
                # VERIFY it was saved!
                verified_agent = postgres_manager.get_agent(agent_id)
                verified_prompt = (verified_agent.config or {}).get('system_prompt', '')
                if verified_prompt != new_prompt:
                    logger.error(f"⚠️ System prompt verification FAILED!")
                    logger.error(f"   Expected: {len(new_prompt)} chars")
                    logger.error(f"   Got: {len(verified_prompt)} chars")
                    return jsonify({
                        'error': 'System prompt save verification failed!',
                        'expected_length': len(new_prompt),
                        'actual_length': len(verified_prompt)
                    }), 500
                
                logger.info(f"✅ System prompt verified in PostgreSQL: {len(new_prompt)} chars")
            else:
                logger.warning(f"⚠️  Agent {agent_id} not found in PostgreSQL")
                return jsonify({'error': f'Agent {agent_id} not found'}), 404
        else:
            # Fallback: Save to state manager (legacy)
            old_prompt = _state_manager.get_state('agent:system_prompt', '')
            _state_manager.set_state('agent:system_prompt', new_prompt)
            
            # VERIFY it was saved!
            verified_prompt = _state_manager.get_state('agent:system_prompt', '')
            if verified_prompt != new_prompt:
                logger.error(f"⚠️ System prompt verification FAILED!")
                return jsonify({
                    'error': 'System prompt save verification failed!',
                    'expected_length': len(new_prompt),
                    'actual_length': len(verified_prompt)
                }), 500
        
        # CREATE VERSION! 🎯
        if _version_manager and old_prompt != new_prompt:
            change_desc = data.get('change_description') or f"Updated system prompt ({len(old_prompt)} → {len(new_prompt)} chars)"
            
            # Get config and memory blocks for version
            agent_state = _state_manager.get_agent_state()
            config = agent_state.get('config', {})
            blocks = _state_manager.get_all_memory_blocks()
            memory_blocks = {block['label']: block.get('content', '') for block in blocks}
            
            version = _version_manager.create_version(
                agent_id=agent_id,
                config=config,
                system_prompt=new_prompt,
                memory_blocks=memory_blocks,
                change_description=change_desc
            )
            
            logger.info(f"📦 VERSION CREATED: {version.version_id}")
            logger.info(f"   System Prompt: {len(old_prompt)} → {len(new_prompt)} chars")
        
        logger.info(f"✅ PUT /system-prompt → System prompt updated for '{agent_id}' ({len(new_prompt)} chars)")
        return jsonify({
            'success': True,
            'system_prompt': new_prompt
        })
        
    except Exception as e:
        logger.error(f"Error updating system prompt: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/messages', methods=['DELETE'])
def clear_messages(agent_id):
    """
    Clear all conversation messages for an agent
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        # Clear messages from database
        _state_manager.clear_messages()
        
        logger.info(f"✅ Cleared all messages for agent {agent_id}")
        
        return jsonify({
            'success': True,
            'message': 'All messages cleared'
        })
    
    except Exception as e:
        logger.error(f"Error clearing messages: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/new-chat', methods=['POST'])
def new_chat_with_summary(agent_id):
    """
    Archive current chat, summarize it, and start fresh with summary
    """
    try:
        if not _state_manager:
            return jsonify({'error': 'State manager not initialized'}), 500
        
        # Get current conversation
        messages = _state_manager.get_conversation(session_id='default')
        
        if not messages or len(messages) < 2:
            # Nothing to summarize, just clear
            _state_manager.clear_messages()
            return jsonify({
                'success': True,
                'summary': None,
                'message': 'No conversation to summarize'
            })
        
        # Build conversation text for summarization
        conversation_text = ""
        for msg in messages:
            role = msg.role
            content = msg.content[:500]  # Limit per message
            conversation_text += f"{role.upper()}: {content}\n\n"
        
        # Ask LLM for summary
        from core.openrouter_client import OpenRouterClient
        from core.cost_tracker import CostTracker
        from api.server import postgres_manager as pg_manager
        
        # CostTracker now requires postgres_manager
        cost_tracker = CostTracker(postgres_manager=pg_manager) if pg_manager else None
        client = OpenRouterClient(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_model="qwen/qwen-2.5-72b-instruct",
            cost_tracker=cost_tracker
        )
        
        summary_prompt = f"""Fasse diese Konversation in 2-3 prägnanten Sätzen zusammen. 
Fokus: Was war der Kern? Was wurde erreicht?

{conversation_text[:3000]}

Zusammenfassung (kurz & klar):"""
        
        response = client.chat_completion(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "user", "content": summary_prompt}],
            stream=False
        )
        
        summary = response.get('content', 'Previous conversation archived.').strip()
        
        # Archive old messages (you could save to file here)
        logger.info(f"📦 Archived {len(messages)} messages")
        
        # Clear messages
        _state_manager.clear_messages()
        
        logger.info(f"✅ New chat started with summary for agent {agent_id}")
        
        return jsonify({
            'success': True,
            'summary': summary,
            'archived_count': len(messages)
        })
    
    except Exception as e:
        logger.error(f"Error creating new chat: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# VERSION MANAGEMENT ENDPOINTS 🎯
# ============================================

@agents_bp.route('/api/agents/<agent_id>/versions', methods=['GET'])
def list_agent_versions(agent_id):
    """
    List all versions for an agent
    Query params: limit (default: 50)
    """
    try:
        if not _version_manager:
            return jsonify({'error': 'Version manager not initialized'}), 500
        
        limit = int(request.args.get('limit', 50))
        versions = _version_manager.list_versions(agent_id, limit=limit)
        
        # Convert to JSON-serializable format
        version_list = []
        for v in versions:
            version_list.append({
                'version_id': v.version_id,
                'timestamp': v.timestamp,
                'change_description': v.change_description,
                'config': v.config,
                'system_prompt_length': len(v.system_prompt),
                'parent_version': v.parent_version
            })
        
        return jsonify({
            'versions': version_list,
            'count': len(version_list)
        })
    
    except Exception as e:
        logger.error(f"Error listing versions: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/versions/current', methods=['GET'])
def get_current_version(agent_id):
    """
    Get current active version
    """
    try:
        if not _version_manager:
            return jsonify({'error': 'Version manager not initialized'}), 500
        
        version = _version_manager.get_current_version(agent_id)
        
        if not version:
            return jsonify({'error': 'No current version found'}), 404
        
        return jsonify(version.to_dict())
    
    except Exception as e:
        logger.error(f"Error getting current version: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/versions/<version_id>', methods=['GET'])
def get_agent_version(agent_id, version_id):
    """
    Get specific version details
    """
    try:
        if not _version_manager:
            return jsonify({'error': 'Version manager not initialized'}), 500
        
        version = _version_manager.get_version(version_id)
        
        if not version:
            return jsonify({'error': f'Version {version_id} not found'}), 404
        
        return jsonify(version.to_dict())
    
    except Exception as e:
        logger.error(f"Error getting version: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/versions/<version_id>/rollback', methods=['POST'])
def rollback_to_version(agent_id, version_id):
    """
    Rollback to a specific version
    Creates a new version based on the old one and applies it to state
    """
    try:
        if not _version_manager or not _state_manager:
            return jsonify({'error': 'Managers not initialized'}), 500
        
        # Rollback creates new version
        new_version = _version_manager.rollback_to_version(version_id)
        
        # Apply to state
        _state_manager.set_state('agent:system_prompt', new_version.system_prompt)
        
        agent_state = _state_manager.get_agent_state()
        agent_state['config'] = new_version.config
        _state_manager.update_agent_state(agent_state)
        
        # Update memory blocks (bypass read-only check during rollback!)
        for label, content in new_version.memory_blocks.items():
            # Get existing block or create minimal block_data
            existing_block = _state_manager.get_memory_block(label)
            if existing_block:
                # Bypass read-only check for rollback (admin operation!)
                _state_manager.update_memory_block(label, content, existing_block, check_read_only=False)
            else:
                # Block doesn't exist, create it
                _state_manager.create_memory_block(label, content, {
                    'label': label,
                    'value': content,
                    'limit': 2000
                })
        
        logger.info(f"⏮️  POST /rollback → Rolling back to {version_id}")
        logger.info(f"📦 NEW VERSION: {new_version.version_id}")
        logger.info(f"   Restored Model: {new_version.config.get('model')}")
        logger.info(f"   Restored Prompt: {len(new_version.system_prompt)} chars")
        
        return jsonify({
            'success': True,
            'new_version': new_version.to_dict(),
            'rolled_back_to': version_id
        })
    
    except Exception as e:
        logger.error(f"Error rolling back: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/versions/compare', methods=['GET'])
def compare_versions(agent_id):
    """
    Compare two versions
    Query params: v1, v2 (version IDs)
    """
    try:
        if not _version_manager:
            return jsonify({'error': 'Version manager not initialized'}), 500
        
        v1 = request.args.get('v1')
        v2 = request.args.get('v2')
        
        if not v1 or not v2:
            return jsonify({'error': 'Both v1 and v2 version IDs required'}), 400
        
        diff = _version_manager.get_diff(v1, v2)
        
        return jsonify(diff)
    
    except Exception as e:
        logger.error(f"Error comparing versions: {e}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/api/agents/<agent_id>/export', methods=['GET'])
def export_agent_file(agent_id):
    """
    Export agent to .af file
    """
    try:
        if not _version_manager:
            return jsonify({'error': 'Version manager not initialized'}), 500
        
        import tempfile
        import os
        from flask import send_file
        
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.af', delete=False)
        _version_manager.export_to_agent_file(agent_id, temp_file.name)
        temp_file.close()
        
        # Send file
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f'substrate_ai_{agent_id}.af',
            mimetype='application/json'
        )
    
    except Exception as e:
        logger.error(f"Error exporting agent: {e}")
        return jsonify({'error': str(e)}), 500

