"""
Memory Tool - Full Implementation with Block Creation! (PostgreSQL-ONLY)

This is the universal memory tool that agents use to manage their memories.
Supports: create, str_replace, insert, delete, rename operations.

100% PostgreSQL - NO SQLite!
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state_manager import StateManager, BlockType
from core.postgres_manager import create_postgres_manager_from_env


# Global state manager instance (initialized on first use)
_state_manager = None
_postgres_manager = None


def _get_state_manager() -> StateManager:
    """Get or create the state manager instance (PostgreSQL-only!)."""
    global _state_manager, _postgres_manager
    if _state_manager is None:
        _postgres_manager = create_postgres_manager_from_env()
        if not _postgres_manager:
            raise RuntimeError("PostgreSQL is REQUIRED! Configure .env and ensure PostgreSQL is running.")
        _state_manager = StateManager(postgres_manager=_postgres_manager)
    return _state_manager


def memory(
    command: str,
    path: str = None,
    file_text: str = None,
    description: str = None,
    old_str: str = None,
    new_str: str = None,
    insert_line: int = None,
    insert_text: str = None,
    old_path: str = None,
    new_path: str = None
) -> dict:
    """
    Memory management tool with sub-commands.
    
    Commands:
    - create: Create new memory block (path=label, file_text=content, description=desc)
    - str_replace: Replace text in memory (path=label, old_str=..., new_str=...)
    - insert: Insert text at line (path=label, insert_line=N, insert_text=...)
    - delete: Delete memory block (path=label)
    - rename: Rename memory block (old_path=..., new_path=...)
    - read: Read memory block contents (path=label)
    - list: List all memory blocks
    
    Args:
        command: Operation to perform
        path: Memory block label/path
        file_text: Content for create
        description: Description for create
        old_str: Text to find (for str_replace)
        new_str: Replacement text (for str_replace)
        insert_line: Line number (for insert)
        insert_text: Text to insert
        old_path: Old label (for rename)
        new_path: New label (for rename)
    
    Returns:
        dict: Operation result with status and message
    """
    try:
        state = _get_state_manager()
        
        if command == "create":
            # Create a new memory block
            if not path:
                return {
                    "status": "error",
                    "message": "❌ 'path' (block label) is required for create command"
                }
            
            content = file_text or ""
            desc = description or f"Memory block: {path}"
            
            # Check if block already exists
            existing = state.get_block(path)
            if existing:
                return {
                    "status": "error",
                    "message": f"❌ Memory block '{path}' already exists. Use str_replace to modify it."
                }
            
            # Create the block
            block = state.create_block(
                label=path,
                content=content,
                block_type=BlockType.CUSTOM,
                description=desc,
                limit=5000,  # Generous limit
                read_only=False
            )
            
            return {
                "status": "OK",
                "message": f"✅ Created memory block '{path}' with {len(content)} characters",
                "block": {
                    "label": block.label,
                    "content": block.content[:200] + "..." if len(block.content) > 200 else block.content,
                    "description": block.description
                }
            }
        
        elif command == "read":
            # Read a memory block
            if not path:
                return {
                    "status": "error",
                    "message": "❌ 'path' (block label) is required for read command"
                }
            
            block = state.get_block(path)
            if not block:
                return {
                    "status": "error",
                    "message": f"❌ Memory block '{path}' not found"
                }
            
            return {
                "status": "OK",
                "message": f"📖 Memory block '{path}'",
                "content": block.content,
                "description": block.description,
                "read_only": block.read_only
            }
        
        elif command == "list":
            # List all memory blocks
            blocks = state.list_blocks(include_hidden=False)
            
            block_list = [
                {
                    "label": b.label,
                    "type": b.block_type.value,
                    "size": len(b.content),
                    "description": b.description[:50] + "..." if len(b.description) > 50 else b.description
                }
                for b in blocks
            ]
            
            return {
                "status": "OK",
                "message": f"📚 Found {len(blocks)} memory blocks",
                "blocks": block_list
            }
        
        elif command == "str_replace":
            # Replace text in a memory block
            if not path:
                return {
                    "status": "error",
                    "message": "❌ 'path' (block label) is required for str_replace command"
                }
            
            if old_str is None or new_str is None:
                return {
                    "status": "error",
                    "message": "❌ Both 'old_str' and 'new_str' are required for str_replace command"
                }
            
            block = state.get_block(path)
            if not block:
                return {
                    "status": "error",
                    "message": f"❌ Memory block '{path}' not found"
                }
            
            if block.read_only:
                return {
                    "status": "error",
                    "message": f"❌ Memory block '{path}' is read-only"
                }
            
            if old_str not in block.content:
                return {
                    "status": "error",
                    "message": f"❌ Text not found in memory block '{path}'"
                }
            
            # Replace text
            new_content = block.content.replace(old_str, new_str, 1)
            state.update_block(path, new_content)
            
            return {
                "status": "OK",
                "message": f"✅ Replaced text in memory block '{path}'",
                "old_text": old_str[:50] + "..." if len(old_str) > 50 else old_str,
                "new_text": new_str[:50] + "..." if len(new_str) > 50 else new_str
            }
        
        elif command == "insert":
            # Insert text at a position
            if not path:
                return {
                    "status": "error",
                    "message": "❌ 'path' (block label) is required for insert command"
                }
            
            if insert_text is None:
                return {
                    "status": "error",
                    "message": "❌ 'insert_text' is required for insert command"
                }
            
            block = state.get_block(path)
            if not block:
                return {
                    "status": "error",
                    "message": f"❌ Memory block '{path}' not found"
                }
            
            if block.read_only:
                return {
                    "status": "error",
                    "message": f"❌ Memory block '{path}' is read-only"
                }
            
            # Insert at line (or append if no line specified)
            lines = block.content.split('\n')
            insert_at = insert_line if insert_line is not None else len(lines)
            insert_at = max(0, min(insert_at, len(lines)))
            
            lines.insert(insert_at, insert_text)
            new_content = '\n'.join(lines)
            state.update_block(path, new_content)
            
            return {
                "status": "OK",
                "message": f"✅ Inserted text at line {insert_at} in memory block '{path}'",
                "inserted_text": insert_text[:50] + "..." if len(insert_text) > 50 else insert_text
            }
        
        elif command == "delete":
            # Delete a memory block
            if not path:
                return {
                    "status": "error",
                    "message": "❌ 'path' (block label) is required for delete command"
                }
            
            block = state.get_block(path)
            if not block:
                return {
                    "status": "error",
                    "message": f"❌ Memory block '{path}' not found"
                }
            
            if block.read_only:
                return {
                    "status": "error",
                    "message": f"❌ Memory block '{path}' is read-only and cannot be deleted"
                }
            
            state.delete_block(path)
            
            return {
                "status": "OK",
                "message": f"🗑️ Deleted memory block '{path}'"
            }
        
        elif command == "rename":
            # Rename a memory block
            if not old_path or not new_path:
                return {
                    "status": "error",
                    "message": "❌ Both 'old_path' and 'new_path' are required for rename command"
                }
            
            block = state.get_block(old_path)
            if not block:
                return {
                    "status": "error",
                    "message": f"❌ Memory block '{old_path}' not found"
                }
            
            # Check if new name exists
            existing = state.get_block(new_path)
            if existing:
                return {
                    "status": "error",
                    "message": f"❌ Memory block '{new_path}' already exists"
                }
            
            # Create new block with old content
            new_block = state.create_block(
                label=new_path,
                content=block.content,
                block_type=block.block_type,
                description=description or block.description,
                limit=block.limit,
                read_only=block.read_only
            )
            
            # Delete old block
            state.delete_block(old_path)
            
            return {
                "status": "OK",
                "message": f"✅ Renamed memory block '{old_path}' → '{new_path}'"
            }
        
        else:
            return {
                "status": "error",
                "message": f"❌ Unknown command: '{command}'. Supported: create, read, list, str_replace, insert, delete, rename"
            }
    
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"❌ Memory tool error: {str(e)}",
            "traceback": traceback.format_exc()
        }
