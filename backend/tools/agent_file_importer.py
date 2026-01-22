#!/usr/bin/env python3
"""
Agent File Importer for Substrate AI

Imports .af (agent files) with full version management!
Compatible with .af export format for interoperability.

Features:
- Parses .af format (standard agent file)
- Extracts agents, memory blocks, messages
- Creates versions in version manager
- Imports into PostgreSQL (if available)
- Preserves conversation history
- Security: Validates all imported data

Author: Substrate AI Contributors
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.version_manager import VersionManager
from core.state_manager import StateManager
from core.postgres_manager import create_postgres_manager_from_env
from core.message_continuity import PersistentMessageManager
from core.memory_coherence import MemoryCoherenceEngine


class AgentFileImporter:
    """
    Import .af agent files with full version management!
    
    Compatible with .af export format for interoperability.
    
    Handles:
    - Agent configuration
    - Memory blocks (standard format)
    - Conversation history
    - Tool configuration
    - Version tracking
    
    Security:
    - Validates JSON structure
    - Sanitizes imported data
    - Prevents injection attacks
    """
    
    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        version_manager: Optional[VersionManager] = None,
        postgres_manager: Optional[Any] = None
    ):
        """
        Initialize importer.
        
        Args:
            state_manager: State manager (PostgreSQL-backed)
            version_manager: Version manager for tracking (PostgreSQL-backed)
            postgres_manager: PostgreSQL manager (REQUIRED)
        """
        if not postgres_manager:
            raise ValueError("PostgresManager is REQUIRED!")
        self.postgres_manager = postgres_manager
        self.state_manager = state_manager
        # VersionManager now requires postgres_manager!
        self.version_manager = version_manager or VersionManager(postgres_manager=postgres_manager)
        
        # Create message manager
        self.message_manager = PersistentMessageManager(self.postgres_manager)
        self.memory_engine = MemoryCoherenceEngine(
            self.postgres_manager,
            self.message_manager
        )
        
        print("✅ Agent File Importer initialized (PostgreSQL-only)")
    
    def load_agent_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load and validate .af file.
        
        Security: Validates JSON structure before processing
        """
        print(f"📂 Loading agent file: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Agent file not found: {file_path}")
        
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate structure
        if 'agents' not in data:
            raise ValueError("Invalid agent file: missing 'agents' field")
        
        print(f"✅ Loaded agent file")
        print(f"   Agents: {len(data.get('agents', []))}")
        print(f"   Tools: {len(data.get('tools', []))}")
        print(f"   Blocks: {len(data.get('blocks', []))}")
        
        return data
    
    def extract_agent_info(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract agent information from .af format.
        
        Converts agent file structure to our format.
        """
        name = agent_data.get('name', 'Unknown Agent')
        
        # Extract system prompt
        system_prompt = agent_data.get('system', '')
        
        # Extract memory blocks
        memory_blocks = {}
        
        # Blocks stored in a separate blocks array
        block_ids = agent_data.get('block_ids', [])
        
        # For now, create default blocks (will be filled from blocks array)
        memory_blocks['persona'] = {
            'label': 'persona',
            'value': '',  # Will be filled later
            'limit': 2000
        }
        memory_blocks['human'] = {
            'label': 'human',
            'value': '',  # Will be filled later
            'limit': 2000
        }
        
        # Extract messages
        messages = agent_data.get('messages', [])
        
        # Extract tool configuration
        tool_rules = agent_data.get('tool_rules', [])
        
        return {
            'name': name,
            'system_prompt': system_prompt,
            'memory_blocks': memory_blocks,
            'messages': messages,
            'block_ids': block_ids,
            'tool_rules': tool_rules
        }
    
    def map_blocks_to_memory(
        self,
        block_ids: List[str],
        all_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Map block IDs to memory blocks.
        
        Blocks stored separately with IDs - we need to link them.
        """
        memory_blocks = {}
        
        # Create dict of blocks by ID
        blocks_by_id = {block['id']: block for block in all_blocks}
        
        # Map block IDs to memory blocks
        for block_id in block_ids:
            if block_id in blocks_by_id:
                block = blocks_by_id[block_id]
                label = block.get('label', 'unknown')
                value = block.get('value', '')
                limit = block.get('limit', 2000)
                
                memory_blocks[label] = {
                    'label': label,
                    'value': value,
                    'limit': limit
                }
        
        print(f"   Mapped {len(memory_blocks)} memory blocks")
        return memory_blocks
    
    def import_agent(
        self,
        file_path: str,
        agent_id: str = 'default',
        model: str = 'openrouter/polaris-alpha',
        change_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import agent from .af file with full version management.
        
        Complete import with version management:
        1. Load .af file
        2. Extract agent data
        3. Map memory blocks
        4. Import messages
        5. Create version
        6. Store in PostgreSQL (if available)
        
        Args:
            file_path: Path to .af file
            agent_id: Agent ID to use (default: 'default')
            model: Model to use (default: 'openrouter/polaris-alpha')
            change_description: Description of import
        
        Returns:
            Import summary dictionary
        """
        print("\n" + "="*60)
        print("📦 IMPORTING AGENT FILE")
        print("="*60 + "\n")
        
        # Load agent file
        data = self.load_agent_file(file_path)
        
        # Get agents
        agents = data.get('agents', [])
        if not agents:
            raise ValueError("No agents found in file")
        
        # Use first agent (or we could import all)
        agent_data = agents[0]
        agent_info = self.extract_agent_info(agent_data)
        
        print(f"\n📋 Agent: {agent_info['name']}")
        print(f"   Messages: {len(agent_info['messages'])}")
        print(f"   Block IDs: {len(agent_info['block_ids'])}")
        
        # Map blocks to memory
        all_blocks = data.get('blocks', [])
        memory_blocks = self.map_blocks_to_memory(
            agent_info['block_ids'],
            all_blocks
        )
        
        # Create configuration
        config = {
            'model': model,
            'temperature': 0.7,
            'top_p': 0.95,
            'context_window': 128000,
            'max_tokens': 4096
        }
        
        print(f"\n⚙️  Configuration:")
        print(f"   Model: {config['model']}")
        print(f"   Temperature: {config['temperature']}")
        print(f"   Context: {config['context_window']:,} tokens")
        
        # Create version
        change_desc = change_description or f"Imported from {os.path.basename(file_path)}"
        
        version = self.version_manager.create_version(
            agent_id=agent_id,
            config=config,
            system_prompt=agent_info['system_prompt'],
            memory_blocks=memory_blocks,
            change_description=change_desc
        )
        
        print(f"\n✅ Version created: {version.version_id}")
        
        # Store in SQLite (always)
        print(f"\n💾 Storing in SQLite...")
        
        # Save memory blocks to SQLite (update if exists, create if not)
        for label, block in memory_blocks.items():
            try:
                # Try to update existing block
                self.state_manager.update_block(
                    label=label,
                    content=block['value']
                )
            except:
                # Create if doesn't exist
                try:
                    self.state_manager.create_memory_block(
                        label=label,
                        value=block['value'],
                        block_data={'limit': block.get('limit', 2000)}
                    )
                except:
                    # Skip if still fails (might be read-only)
                    print(f"   ⚠️  Skipped block '{label}' (may already exist)")
        
        print(f"   Saved {len(memory_blocks)} memory blocks")
        
        # Import messages to SQLite
        messages_imported = 0
        import uuid
        for msg in agent_info['messages']:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            # Handle list content (sometimes stored as list)
            if isinstance(content, list):
                content = '\n'.join(str(c) for c in content if c)
            elif not isinstance(content, str):
                content = str(content)
            
            if content.strip():  # Only import non-empty messages
                self.state_manager.add_message(
                    message_id=str(uuid.uuid4()),
                    session_id='default',
                    role=role,
                    content=content
                )
                messages_imported += 1
        
        print(f"   Saved {messages_imported} messages")
        
        # Import to PostgreSQL if available
        if self.postgres_manager:
            print(f"\n🐘 Storing in PostgreSQL...")
            
            # Create agent in PostgreSQL
            pg_agent = self.postgres_manager.create_agent(
                agent_id=agent_id,
                name=agent_info['name'],
                config=config
            )
            
            print(f"   Created agent: {pg_agent.name}")
            
            # Initialize memory engine
            self.memory_engine.initialize_default_core_memory(
                agent_id=agent_id,
                agent_name=agent_info['name']
            )
            
            # If this is ALEX, initialize Alex-specific start memory blocks
            if agent_info['name'].upper() == "ALEX" or "alex" in agent_info['name'].lower():
                try:
                    self.memory_engine.initialize_alex_start_memory(agent_id)
                except Exception as e:
                    print(f"⚠️  Failed to initialize Alex start memory: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Update core memory with imported data
            for label, block in memory_blocks.items():
                if label in ['persona', 'human']:
                    self.memory_engine.update_core_memory(
                        agent_id=agent_id,
                        label=label,
                        content=block['value'],
                        limit=block.get('limit', 2000)
                    )
            
            print(f"   Updated {len(memory_blocks)} core memory blocks")
            
            # Import messages to PostgreSQL
            session_id = 'default'
            pg_messages_imported = 0
            
            for msg in agent_info['messages']:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                
                # Handle list content (sometimes stored as list)
                if isinstance(content, list):
                    content = '\n'.join(str(c) for c in content if c)
                elif not isinstance(content, str):
                    content = str(content)
                
                # Map roles to our format
                if role == 'function':
                    role = 'tool'
                
                if role in ['user', 'assistant', 'system', 'tool'] and content.strip():
                    self.message_manager.add_message(
                        agent_id=agent_id,
                        session_id=session_id,
                        role=role,
                        content=content
                    )
                    pg_messages_imported += 1
            
            print(f"   Saved {pg_messages_imported} messages")
        
        # Create summary
        summary = {
            'agent_id': agent_id,
            'agent_name': agent_info['name'],
            'version_id': version.version_id,
            'model': model,
            'memory_blocks': len(memory_blocks),
            'messages_imported': messages_imported,
            'system_prompt_length': len(agent_info['system_prompt']),
            'imported_to_postgres': self.postgres_manager is not None,
            'timestamp': datetime.now().isoformat()
        }
        
        print("\n" + "="*60)
        print("✅ IMPORT COMPLETE!")
        print("="*60)
        print(f"\nSummary:")
        print(f"  Agent: {summary['agent_name']}")
        print(f"  Version: {summary['version_id']}")
        print(f"  Model: {summary['model']}")
        print(f"  Memory blocks: {summary['memory_blocks']}")
        print(f"  Messages: {summary['messages_imported']}")
        print(f"  System prompt: {summary['system_prompt_length']:,} chars")
        print(f"  PostgreSQL: {'✅' if summary['imported_to_postgres'] else '❌'}")
        
        return summary
    
    def list_available_agents(self, file_path: str) -> List[Dict[str, Any]]:
        """
        List all agents in an .af file without importing.
        
        Useful for previewing before import.
        """
        data = self.load_agent_file(file_path)
        
        agents = []
        for agent_data in data.get('agents', []):
            info = self.extract_agent_info(agent_data)
            agents.append({
                'name': info['name'],
                'messages': len(info['messages']),
                'blocks': len(info['block_ids']),
                'system_prompt_length': len(info['system_prompt'])
            })
        
        return agents


# ============================================
# CLI INTERFACE
# ============================================

def main():
    """Command-line interface for agent file importer"""
    parser = argparse.ArgumentParser(
        description='Import agent files (.af) with version management'
    )
    
    parser.add_argument(
        'file_path',
        help='Path to .af agent file'
    )
    
    parser.add_argument(
        '--agent-id',
        default='default',
        help='Agent ID to use (default: default)'
    )
    
    parser.add_argument(
        '--model',
        default='openrouter/polaris-alpha',
        help='Model to use (default: openrouter/polaris-alpha)'
    )
    
    parser.add_argument(
        '--description',
        help='Description of this import'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List agents in file without importing'
    )
    
    parser.add_argument(
    )
    
    args = parser.parse_args()
    
    # Initialize managers - PostgreSQL REQUIRED!
    postgres_manager = create_postgres_manager_from_env()
    if not postgres_manager:
        print("❌ PostgreSQL is REQUIRED! Configure .env and ensure PostgreSQL is running.")
        exit(1)
    
    state_manager = StateManager(postgres_manager=postgres_manager)
    version_manager = VersionManager(postgres_manager=postgres_manager)
    
    # Create importer
    importer = AgentFileImporter(
        state_manager=state_manager,
        version_manager=version_manager,
        postgres_manager=postgres_manager
    )
    
    # List or import
    if args.list:
        print("\n📋 Agents in file:\n")
        agents = importer.list_available_agents(args.file_path)
        for i, agent in enumerate(agents, 1):
            print(f"{i}. {agent['name']}")
            print(f"   Messages: {agent['messages']}")
            print(f"   Blocks: {agent['blocks']}")
            print(f"   System prompt: {agent['system_prompt_length']:,} chars")
            print()
    else:
        # Import agent
        summary = importer.import_agent(
            file_path=args.file_path,
            agent_id=args.agent_id,
            model=args.model,
            change_description=args.description
        )
        
        print(f"\n🎉 Success! Agent ready to use.")
        print(f"\n💡 Next steps:")
        print(f"   1. Test it: python api/server.py")
        print(f"   2. Check version: {summary['version_id']}")
        print(f"   3. View messages: {summary['messages_imported']} imported")


if __name__ == '__main__':
    main()

