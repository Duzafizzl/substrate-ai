#!/usr/bin/env python3
"""
Agent File Import for Substrate AI (PostgreSQL-ONLY)

Upload an .af (agent file) and automatically create:
- All memory blocks (with read_only, limit, description, etc.)
- System prompt
- Tool configurations
- Agent settings

Full compatibility with .af format while adding our improvements.

100% PostgreSQL - NO SQLite!

Built with determination! 🔥
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state_manager import StateManager, MemoryBlock, BlockType
from core.postgres_manager import create_postgres_manager_from_env


class ImportError(Exception):
    """
    Import errors with helpful messages.
    """
    def __init__(self, message: str, context: Optional[Dict] = None):
        self.context = context or {}
        
        full_message = f"\n{'='*60}\n"
        full_message += f"❌ IMPORT ERROR\n"
        full_message += f"{'='*60}\n\n"
        full_message += f"🔴 Problem: {message}\n\n"
        
        if context:
            full_message += f"📋 Context:\n"
            for key, value in context.items():
                full_message += f"   • {key}: {value}\n"
        
        full_message += f"\n💡 Suggestions:\n"
        full_message += "   • Check .af file format is valid JSON\n"
        full_message += "   • Verify file was exported correctly\n"
        full_message += "   • Try exporting a fresh copy\n"
        full_message += f"\n{'='*60}\n"
        
        super().__init__(full_message)


class AgentFileImporter:
    """
    Import .af files and create agents in Substrate AI (PostgreSQL-only!).
    
    Handles:
    - Memory blocks (with full .af format compatibility)
    - System prompts
    - Tool configurations
    - Agent metadata
    """
    
    def __init__(self, state_manager: StateManager):
        """
        Initialize importer.
        
        Args:
            state_manager: State manager instance (PostgreSQL-backed)
        """
        self.state = state_manager
        
        print("✅ Agent File Importer initialized (PostgreSQL-only)")
    
    def import_from_file(self, af_file_path: str) -> Dict[str, Any]:
        """
        Import agent from .af file.
        
        Args:
            af_file_path: Path to .af file
            
        Returns:
            Dict with import results (agent config, blocks created, etc.)
            
        Raises:
            ImportError: If import fails
        """
        print(f"\n🔄 Importing agent from: {af_file_path}")
        print("="*60)
        
        # Load .af file
        try:
            with open(af_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise ImportError(
                f"File not found: {af_file_path}",
                context={"path": af_file_path}
            )
        except json.JSONDecodeError as e:
            raise ImportError(
                f"Invalid JSON in .af file: {str(e)}",
                context={"path": af_file_path, "error": str(e)}
            )
        
        # Validate structure
        if 'agents' not in data:
            raise ImportError(
                "Invalid .af file format: missing 'agents' field",
                context={"available_fields": list(data.keys())}
            )
        
        if not data['agents']:
            raise ImportError(
                "No agents found in .af file",
                context={"path": af_file_path}
            )
        
        # Import first agent (format allows multiple, we'll import the first)
        agent_data = data['agents'][0]
        agent_name = agent_data.get('name', 'Imported Agent')
        
        print(f"\n📦 Agent: {agent_name}")
        print(f"   Source: {os.path.basename(af_file_path)}")
        
        # Extract components
        blocks_data = data.get('blocks', [])
        system_prompt = agent_data.get('system', '')
        tools = agent_data.get('tools', [])
        tool_rules = agent_data.get('tool_rules', [])
        
        print(f"\n📊 Found:")
        print(f"   • Memory blocks: {len(blocks_data)}")
        print(f"   • System prompt: {len(system_prompt)} chars")
        print(f"   • Tools: {len(tools)}")
        print(f"   • Tool rules: {len(tool_rules)}")
        
        # Import memory blocks
        print(f"\n💾 Importing memory blocks...")
        imported_blocks = []
        
        for block_data in blocks_data:
            try:
                block = self._import_block(block_data)
                imported_blocks.append(block)
            except Exception as e:
                print(f"⚠️  Skipped block '{block_data.get('label', 'unknown')}': {e}")
        
        print(f"✅ Imported {len(imported_blocks)} blocks")
        
        # Store system prompt
        print(f"\n📝 Storing system prompt...")
        self.state.set_state("agent:system_prompt", system_prompt)
        self.state.set_state("agent:name", agent_name)
        print(f"✅ System prompt stored ({len(system_prompt)} chars)")
        
        # Store tool configuration
        print(f"\n🛠️  Storing tool configuration...")
        self.state.set_state("agent:tools", tools)
        self.state.set_state("agent:tool_rules", tool_rules)
        print(f"✅ Tool config stored ({len(tools)} tools)")
        
        # Store agent metadata
        self.state.set_state("agent:imported_at", datetime.utcnow().isoformat())
        self.state.set_state("agent:source_file", os.path.basename(af_file_path))
        
        print(f"\n{'='*60}")
        print(f"✅ IMPORT COMPLETE!")
        print(f"{'='*60}")
        print(f"\n🎉 Agent '{agent_name}' is ready!")
        print(f"   • {len(imported_blocks)} memory blocks loaded")
        print(f"   • System prompt configured")
        print(f"   • {len(tools)} tools registered")
        
        return {
            "agent_name": agent_name,
            "blocks_imported": len(imported_blocks),
            "blocks": [b.to_dict() for b in imported_blocks],
            "system_prompt_length": len(system_prompt),
            "tools_count": len(tools),
            "tool_rules_count": len(tool_rules)
        }
    
    def _import_block(self, block_data: Dict) -> MemoryBlock:
        """
        Import a single memory block from .af format.
        
        Args:
            block_data: Block data from .af file
            
        Returns:
            Created MemoryBlock
            
        Raises:
            Exception: If block creation fails
        """
        label = block_data.get('label', 'unknown')
        content = block_data.get('value', '')  # .af format uses 'value' not 'content'
        description = block_data.get('description', '') or ''  # Handle None
        limit = block_data.get('limit', 2000) or 2000
        read_only = block_data.get('read_only', False) or False
        metadata = block_data.get('metadata', {}) or {}
        hidden = block_data.get('hidden', False) or False  # Handle None!
        
        # Determine block type
        block_type = BlockType.CUSTOM
        label_lower = label.lower()
        if 'persona' in label_lower or label == 'persona':
            block_type = BlockType.PERSONA
        elif 'human' in label_lower or label == 'human':
            block_type = BlockType.HUMAN
        
        # Check if block already exists
        existing = self.state.get_block(label)
        if existing:
            print(f"   ⚠️  Block '{label}' already exists, skipping")
            return existing
        
        # Create block
        block = self.state.create_block(
            label=label,
            content=content,
            block_type=block_type,
            limit=limit,
            read_only=read_only,
            description=description,
            metadata=metadata,
            hidden=hidden
        )
        
        return block
    
    def list_agent_info(self) -> Dict[str, Any]:
        """
        Get current agent configuration.
        
        Returns:
            Dict with agent info
        """
        blocks = self.state.list_blocks(include_hidden=False)
        
        return {
            "name": self.state.get_state("agent:name", "No agent loaded"),
            "system_prompt": self.state.get_state("agent:system_prompt", ""),
            "memory_blocks": len(blocks),
            "blocks_detail": [
                {
                    "label": b.label,
                    "type": b.block_type.value,
                    "size": len(b.content),
                    "limit": b.limit,
                    "read_only": b.read_only,
                    "description": b.description
                }
                for b in blocks
            ],
            "tools": len(self.state.get_state("agent:tools", [])),
            "tool_rules": len(self.state.get_state("agent:tool_rules", [])),
            "imported_at": self.state.get_state("agent:imported_at", "Never"),
            "source_file": self.state.get_state("agent:source_file", "Unknown")
        }
    
    def export_blocks_as_json(self, output_path: str):
        """
        Export current blocks as JSON (for backup/inspection).
        
        Args:
            output_path: Where to save JSON file
        """
        blocks = self.state.list_blocks(include_hidden=True)
        
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "agent_name": self.state.get_state("agent:name", "Unknown"),
            "blocks": [b.to_dict() for b in blocks]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(blocks)} blocks to: {output_path}")


# ============================================
# CLI INTERFACE
# ============================================

def main():
    """Command-line interface for importing agents (PostgreSQL-only!)"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Import .af agent files into Substrate AI (PostgreSQL-only!)"
    )
    parser.add_argument(
        'af_file',
        help='Path to .af file to import'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Show current agent info instead of importing'
    )
    parser.add_argument(
        '--export',
        help='Export current blocks to JSON file'
    )
    
    args = parser.parse_args()
    
    # Initialize PostgreSQL manager (REQUIRED!)
    postgres_manager = create_postgres_manager_from_env()
    if not postgres_manager:
        print("❌ PostgreSQL is REQUIRED! Configure .env and ensure PostgreSQL is running.")
        sys.exit(1)
    
    # Initialize state manager (PostgreSQL-backed)
    state = StateManager(postgres_manager=postgres_manager)
    importer = AgentFileImporter(state)
    
    # Show info?
    if args.info:
        info = importer.list_agent_info()
        print("\n📊 CURRENT AGENT INFO")
        print("="*60)
        print(f"Name: {info['name']}")
        print(f"System prompt: {len(info['system_prompt'])} chars")
        print(f"Memory blocks: {info['memory_blocks']}")
        print(f"Tools: {info['tools']}")
        print(f"Imported: {info['imported_at']}")
        print(f"Source: {info['source_file']}")
        print(f"\n📦 Memory Blocks:")
        for b in info['blocks_detail']:
            ro = "🔒" if b['read_only'] else "✏️ "
            print(f"   {ro} {b['label']:<20} ({b['type']:<10}) {b['size']}/{b['limit']} chars")
            if b['description']:
                print(f"      ↳ {b['description'][:60]}...")
        return
    
    # Export?
    if args.export:
        importer.export_blocks_as_json(args.export)
        return
    
    # Import!
    try:
        result = importer.import_from_file(args.af_file)
        print(f"\n🎉 SUCCESS! Agent '{result['agent_name']}' imported!")
    except ImportError as e:
        print(e)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
