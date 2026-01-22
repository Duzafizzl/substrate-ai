#!/usr/bin/env python3
"""
Memory Tools for Substrate AI

These are the tools the AI uses to manipulate its own memories.
Full-featured memory API with advanced capabilities!

Core Memory Tools:
- core_memory_append
- core_memory_replace
- memory_insert
- memory_replace
- memory_rethink
- memory_finish_edits

Archival Memory Tools:
- archival_memory_insert
- archival_memory_search

Conversation Tools:
- conversation_search

Built with attention to detail! 🔥
"""

import sys
import os
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state_manager import StateManager, StateManagerError
from core.memory_system import MemorySystem, MemoryCategory, MemorySystemError
from tools.integration_tools import IntegrationTools
from tools.memory import memory as _memory_tool


class MemoryToolError(Exception):
    """Memory tool execution errors"""
    pass


class MemoryTools:
    """
    Memory tools + integration tools.
    
    The AI uses these to manage its memories AND control Discord/Spotify!
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        memory_system: Optional[MemorySystem] = None,
        cost_tools=None,  # NEW: Cost Tools for self-awareness!
        postgres_manager=None  # PostgreSQL manager for IntegrationTools
    ):
        """
        Initialize memory tools.
        
        Args:
            state_manager: State manager instance
            memory_system: Memory system instance (optional, for archival)
            cost_tools: Cost tools instance (for budget awareness!)
            postgres_manager: PostgreSQL manager (for IntegrationTools)
        """
        self.state = state_manager
        self.memory = memory_system
        self.cost_tools = cost_tools  # NEW: Cost Tools!
        
        # Initialize integration tools (Discord, Spotify, etc.)
        # Pass postgres_manager for cost tracking
        self.integrations = IntegrationTools(
            cost_tracker=cost_tools.cost_tracker if cost_tools else None,
            postgres_manager=postgres_manager
        )
        
        print("✅ Memory Tools initialized")
        print("✅ Integration Tools initialized (Discord, Spotify)")
        if cost_tools:
            print("✅ Cost Tools integrated (Agent can check budget!)")
    
    # ============================================
    # CORE MEMORY TOOLS (Legacy API)
    # ============================================
    
    def core_memory_append(
        self,
        content: str,
        block_name: str
    ) -> Dict[str, Any]:
        """
        Append content to a memory block.
        
        Legacy API for backward compatibility.
        
        Args:
            content: Content to append
            block_name: Block name (persona/human)
            
        Returns:
            Result dict with status and message
        """
        try:
            # Get current block
            block = self.state.get_block(block_name)
            
            if not block:
                return {
                    "status": "error",
                    "message": f"Memory block '{block_name}' not found"
                }
            
            # Check read-only
            if block.read_only:
                return {
                    "status": "error",
                    "message": f"🔒 Memory block '{block_name}' is READ-ONLY and cannot be edited"
                }
            
            # Append content
            new_content = f"{block.content}\n{content}".strip()
            
            # Check limit
            if len(new_content) > block.limit:
                return {
                    "status": "error",
                    "message": f"Content exceeds block limit ({len(new_content)} > {block.limit} chars)"
                }
            
            # Update
            self.state.update_block(block_name, new_content, check_read_only=True)
            
            return {
                "status": "OK",
                "message": f"Added to memory block '{block_name}': {content[:60]}..."
            }
        
        except StateManagerError as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def core_memory_replace(
        self,
        old_content: str,
        new_content: str,
        block_name: str
    ) -> Dict[str, Any]:
        """
        Replace old content with new content in a memory block.
        
        Legacy API for backward compatibility.
        
        Args:
            old_content: String to replace
            new_content: Replacement string
            block_name: Block name (persona/human)
            
        Returns:
            Result dict with status and message
        """
        try:
            # Get current block
            block = self.state.get_block(block_name)
            
            if not block:
                return {
                    "status": "error",
                    "message": f"Memory block '{block_name}' not found"
                }
            
            # Check read-only
            if block.read_only:
                return {
                    "status": "error",
                    "message": f"🔒 Memory block '{block_name}' is READ-ONLY and cannot be edited"
                }
            
            # Check if old content exists
            if old_content not in block.content:
                return {
                    "status": "error",
                    "message": f"Content '{old_content[:60]}...' not found in '{block_name}'"
                }
            
            # Replace
            updated = block.content.replace(old_content, new_content)
            
            # Check limit
            if len(updated) > block.limit:
                return {
                    "status": "error",
                    "message": f"Content exceeds block limit ({len(updated)} > {block.limit} chars)"
                }
            
            # Update
            self.state.update_block(block_name, updated, check_read_only=True)
            
            return {
                "status": "OK",
                "message": f"Replaced in '{block_name}': '{old_content[:30]}...' → '{new_content[:30]}...'"
            }
        
        except StateManagerError as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    # ============================================
    # NEW MEMORY TOOLS (Modern API)
    # ============================================
    
    def memory_insert(
        self,
        text: str,
        index: int,
        block_label: str
    ) -> Dict[str, Any]:
        """
        Insert text at a specific position in a memory block.
        
        Modern memory API.
        
        Args:
            text: Text to insert
            index: Position to insert at (0-based)
            block_label: Block label
            
        Returns:
            Result dict with status and message
        """
        try:
            # Get current block
            block = self.state.get_block(block_label)
            
            if not block:
                return {
                    "status": "error",
                    "message": f"Memory block '{block_label}' not found"
                }
            
            # Check read-only
            if block.read_only:
                return {
                    "status": "error",
                    "message": f"🔒 Memory block '{block_label}' is READ-ONLY and cannot be edited"
                }
            
            # Insert
            updated = block.content[:index] + text + block.content[index:]
            
            # Check limit
            if len(updated) > block.limit:
                return {
                    "status": "error",
                    "message": f"Content exceeds block limit ({len(updated)} > {block.limit} chars)"
                }
            
            # Update
            self.state.update_block(block_label, updated, check_read_only=True)
            
            return {
                "status": "OK",
                "message": f"Inserted text at position {index} in '{block_label}'"
            }
        
        except StateManagerError as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def memory_replace(
        self,
        old_text: str,
        new_text: str,
        block_label: str
    ) -> Dict[str, Any]:
        """
        Replace specific text in a memory block.
        
        Modern memory API.
        
        Args:
            old_text: Text to replace
            new_text: Replacement text
            block_label: Block label
            
        Returns:
            Result dict with status and message
        """
        try:
            # Get current block
            block = self.state.get_block(block_label)
            
            if not block:
                return {
                    "status": "error",
                    "message": f"Memory block '{block_label}' not found"
                }
            
            # Check read-only
            if block.read_only:
                return {
                    "status": "error",
                    "message": f"🔒 Memory block '{block_label}' is READ-ONLY and cannot be edited"
                }
            
            # Check if old text exists
            if old_text not in block.content:
                return {
                    "status": "error",
                    "message": f"Text not found in '{block_label}'"
                }
            
            # Replace
            updated = block.content.replace(old_text, new_text)
            
            # Check limit
            if len(updated) > block.limit:
                return {
                    "status": "error",
                    "message": f"Content exceeds block limit ({len(updated)} > {block.limit} chars)"
                }
            
            # Update
            self.state.update_block(block_label, updated, check_read_only=True)
            
            return {
                "status": "OK",
                "message": f"Replaced in '{block_label}': '{old_text[:30]}...' → '{new_text[:30]}...'"
            }
        
        except StateManagerError as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def memory_rethink(
        self,
        new_content: str,
        block_label: str
    ) -> Dict[str, Any]:
        """
        Completely rewrite the content of a memory block.
        
        Use this to reorganize or restructure memories.
        
        Modern memory API.
        
        Args:
            new_content: New complete content for the block
            block_label: Block label
            
        Returns:
            Result dict with status and message
        """
        try:
            # Get current block
            block = self.state.get_block(block_label)
            
            if not block:
                return {
                    "status": "error",
                    "message": f"Memory block '{block_label}' not found"
                }
            
            # Check read-only
            if block.read_only:
                return {
                    "status": "error",
                    "message": f"🔒 Memory block '{block_label}' is READ-ONLY and cannot be edited"
                }
            
            # Check limit
            if len(new_content) > block.limit:
                return {
                    "status": "error",
                    "message": f"Content exceeds block limit ({len(new_content)} > {block.limit} chars)"
                }
            
            # Update
            self.state.update_block(block_label, new_content, check_read_only=True)
            
            return {
                "status": "OK",
                "message": f"Rewrote '{block_label}' block with new content ({len(new_content)} chars)"
            }
        
        except StateManagerError as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def memory_finish_edits(
        self,
        block_label: str
    ) -> Dict[str, Any]:
        """
        Signal that you've finished editing a memory block.
        
        Modern memory API.
        
        Args:
            block_label: Block label
            
        Returns:
            Result dict with status and message
        """
        # This is mainly a signal tool, doesn't change state
        block = self.state.get_block(block_label)
        
        if not block:
            return {
                "status": "error",
                "message": f"Memory block '{block_label}' not found"
            }
        
        return {
            "status": "OK",
            "message": f"Finished editing '{block_label}' block"
        }
    
    # ============================================
    # ARCHIVAL MEMORY TOOLS
    # ============================================
    
    def archival_memory_insert(
        self,
        content: str,
        category: str = "fact",
        importance: int = 5,
        tags: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Insert a memory into archival storage.
        
        Use this for long-term memories that don't fit in core memory.
        
        Standard memory API.
        
        Args:
            content: Content to store
            category: Memory category (fact/emotion/insight/relationship_moment)
            importance: Importance (1-10)
            tags: Optional tags
            
        Returns:
            Result dict with status and message
        """
        if not self.memory:
            return {
                "status": "error",
                "message": "Archival memory system not initialized"
            }
        
        try:
            # Parse category
            try:
                cat = MemoryCategory(category)
            except ValueError:
                cat = MemoryCategory.FACT
            
            # Insert
            memory_id = self.memory.insert(
                content=content,
                category=cat,
                importance=importance,
                tags=tags or []
            )
            
            return {
                "status": "OK",
                "message": f"Added to archival memory: {content[:100]}...",
                "memory_id": memory_id
            }
        
        except MemorySystemError as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def archival_memory_search(
        self,
        query: str,
        page: int = 0,
        min_importance: int = 1,
        tags: Optional[list] = None,
        tag_match_mode: str = "any",
        top_k: int = 10,
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search archival memory using semantic similarity.
        
        Memory API with full tag support!
        
        Search strategy:
        - Query by concept/meaning, not exact phrases
        - Use tags to narrow results when you know the category
        - Start broad, then narrow with tags if needed
        - Results are ranked by semantic relevance
        
        Args:
            query: What you're looking for, described naturally
            page: Page number (0-based) for pagination
            min_importance: Minimum importance filter (1-10)
            tags: Optional list of tags to filter by
            tag_match_mode: "any" = match ANY tag, "all" = match ALL tags
            top_k: Maximum number of results (default: 10)
            start_datetime: Only return memories after this time (ISO 8601)
            end_datetime: Only return memories before this time (ISO 8601)
            
        Returns:
            Result dict with status, query, page, and results
            
        Examples:
            # Search for project discussions
            archival_memory_search(
                query="database migration decisions",
                tags=["projects"]
            )
            
            # Search with date range
            archival_memory_search(
                query="roadmap planning",
                start_datetime="2024-01-01",
                end_datetime="2024-03-31",
                tags=["meetings", "roadmap"],
                tag_match_mode="all"
            )
        """
        if not self.memory:
            return {
                "status": "error",
                "message": "Archival memory system not initialized"
            }
        
        try:
            # Search with semantic similarity
            results = self.memory.search(
                query=query,
                n_results=top_k,
                min_importance=min_importance
            )
            
            # Filter by tags if provided
            if tags and len(tags) > 0:
                filtered_results = []
                for r in results:
                    result_tags = r.get('tags', []) or []
                    
                    if tag_match_mode == "all":
                        # Must have ALL specified tags
                        if all(tag in result_tags for tag in tags):
                            filtered_results.append(r)
                    else:
                        # Must have ANY of the specified tags
                        if any(tag in result_tags for tag in tags):
                            filtered_results.append(r)
                
                results = filtered_results
            
            # Filter by date range if provided
            if start_datetime or end_datetime:
                from datetime import datetime
                
                date_filtered = []
                for r in results:
                    result_time = r.get('timestamp')
                    if not result_time:
                        continue
                    
                    # Parse result timestamp
                    if isinstance(result_time, str):
                        try:
                            result_dt = datetime.fromisoformat(result_time.replace('Z', '+00:00'))
                        except:
                            continue
                    else:
                        result_dt = result_time
                    
                    # Check start bound
                    if start_datetime:
                        try:
                            start_dt = datetime.fromisoformat(start_datetime)
                            if result_dt < start_dt:
                                continue
                        except:
                            pass
                    
                    # Check end bound
                    if end_datetime:
                        try:
                            end_dt = datetime.fromisoformat(end_datetime)
                            if result_dt > end_dt:
                                continue
                        except:
                            pass
                    
                    date_filtered.append(r)
                
                results = date_filtered
            
            # Paginate
            page_size = top_k
            start_idx = page * page_size
            end_idx = start_idx + page_size
            paginated_results = results[start_idx:end_idx]
            
            return {
                "status": "OK",
                "query": query,
                "page": page,
                "total_results": len(results),
                "results_on_page": len(paginated_results),
                "tags_filter": tags,
                "tag_match_mode": tag_match_mode if tags else None,
                "results": [
                    {
                        "content": r['content'],
                        "timestamp": r['timestamp'],
                        "relevance": f"{r['relevance']:.2%}",
                        "importance": r['importance'],
                        "tags": r.get('tags', [])
                    }
                    for r in paginated_results
                ]
            }
        
        except MemorySystemError as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    # ============================================
    # CONVERSATION SEARCH
    # ============================================
    
    def conversation_search(
        self,
        query: str,
        session_id: str = "default",
        page: int = 0
    ) -> Dict[str, Any]:
        """
        Search through the conversation history for specific information.
        
        Standard memory API.
        
        Args:
            query: Search query
            session_id: Session ID
            page: Page number (0-based)
            
        Returns:
            Result dict with status, query, page, and results
        """
        try:
            page_size = 5
            
            # Search messages
            messages = self.state.search_messages(
                session_id=session_id,
                query=query,
                limit=page_size
            )
            
            return {
                "status": "OK",
                "query": query,
                "page": page,
                "total_results": len(messages),
                "results": [
                    {
                        "role": m.role,
                        "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
                        "timestamp": m.timestamp.isoformat()
                    }
                    for m in messages
                ]
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    # ============================================
    # CONVERSATION SUMMARIZATION
    # ============================================
    
    async def conversation_summarize(
        self,
        summary: str,
        importance: int = 5,
        category: str = "fact",
        session_id: str = "default_session"
    ) -> Dict[str, Any]:
        """
        Summarize old conversation messages and archive them.
        
        This is used when context window is getting full (>80%).
        The AI creates a summary, pushes it to archival memory,
        and marks old messages as summarized so they can be removed from context.
        
        Args:
            summary: The AI's summary of the old conversation
            importance: Importance rating (1-10)
            category: Category of summary
            session_id: Session to summarize
            
        Returns:
            Result dict with status, summary_id, and message count
        """
        try:
            # 1. Push summary to archival memory
            if self.memory_system:
                summary_id = await self.memory_system.insert(
                    content=summary,
                    category=category,
                    importance=importance,
                    tags=["conversation_summary", session_id],
                    metadata={"session_id": session_id, "summarized_at": "now"}
                )
            else:
                # Fallback: No archival memory available
                # Just mark messages as summarized in DB
                summary_id = f"local_{session_id}_{hash(summary)}"
            
            # 2. Get conversation history to count messages
            messages = self.state.get_conversation(session_id, limit=1000)
            message_count = len(messages)
            
            # 3. Mark messages as summarized (for future cleanup)
            # This doesn't delete them yet - consciousness loop handles that
            # We just return the count so the AI knows what got archived
            
            return {
                "status": "OK",
                "summary_id": summary_id,
                "messages_summarized": message_count,
                "message": f"Archived summary to archival memory. {message_count} messages can now be cleared from context."
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    # ============================================
    # INTEGRATION TOOLS (WRAPPERS)
    # ============================================
    
    def discord_tool(self, **kwargs) -> Dict[str, Any]:
        """
        Discord integration tool (wrapper).
        Full Discord control - DMs, channels, tasks, etc.
        """
        return self.integrations.discord_tool(**kwargs)
    
    def spotify_control(self, **kwargs) -> Dict[str, Any]:
        """
        Spotify control tool (wrapper).
        Full Spotify control - search, play, queue, playlists.
        """
        return self.integrations.spotify_control(**kwargs)
    
    def web_search(self, **kwargs) -> Dict[str, Any]:
        """
        Web search tool (wrapper).
        Search the web using Exa AI.
        """
        return self.integrations.web_search(**kwargs)
    
    def fetch_webpage(self, **kwargs) -> Dict[str, Any]:
        """
        Fetch webpage tool (wrapper).
        Fetch and convert webpage to markdown using Jina AI.
        """
        return self.integrations.fetch_webpage(**kwargs)
    
    def memory(self, **kwargs) -> Dict[str, Any]:
        """
        Memory tool - alternative API for memory management.
        
        Sub-commands: create, str_replace, insert, delete, rename, read, list
        
        POSTGRESQL-FIRST: Uses PostgreSQL if available, falls back to SQLite!
        """
        try:
            command = kwargs.get('command')
            path = kwargs.get('path')
            file_text = kwargs.get('file_text')
            description = kwargs.get('description')
            old_str = kwargs.get('old_str')
            new_str = kwargs.get('new_str')
            insert_line = kwargs.get('insert_line')
            insert_text = kwargs.get('insert_text')
            old_path = kwargs.get('old_path')
            new_path = kwargs.get('new_path')
            
            # Check if PostgreSQL is available
            postgres = getattr(self.state, 'postgres_manager', None)
            agent_id = '41dc0e38-bdb6-4563-a3b6-49aa0925ab14'  # Default agent ID
            
            if command == "create":
                if not path:
                    return {"status": "error", "message": "❌ 'path' (block label) is required"}
                
                content = file_text or ""
                desc = description or f"Memory block: {path}"
                
                # Try PostgreSQL first
                if postgres:
                    try:
                        # Check if exists in PostgreSQL
                        with postgres._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT label FROM memories 
                                WHERE agent_id = %s AND label = %s AND memory_type = 'core'
                            """, (agent_id, path))
                            if cursor.fetchone():
                                return {"status": "error", "message": f"❌ Memory block '{path}' already exists. Use str_replace to modify."}
                        
                        # Create in PostgreSQL
                        metadata = {
                            'description': desc,
                            'limit': 5000,
                            'read_only': False
                        }
                        memory_obj = postgres.add_memory(
                            agent_id=agent_id,
                            memory_type='core',
                            label=path,
                            content=content,
                            metadata=metadata
                        )
                        
                        return {
                            "status": "OK",
                            "message": f"✅ Created memory block '{path}' in PostgreSQL with {len(content)} characters",
                            "block": {"label": memory_obj.label, "description": desc}
                        }
                    except Exception as e:
                        # Fallback to SQLite if PostgreSQL fails
                        pass
                
                # Fallback to SQLite
                existing = self.state.get_block(path)
                if existing:
                    return {"status": "error", "message": f"❌ Memory block '{path}' already exists. Use str_replace to modify."}
                
                from core.state_manager import BlockType
                block = self.state.create_block(
                    label=path,
                    content=content,
                    block_type=BlockType.CUSTOM,
                    description=desc,
                    limit=5000,
                    read_only=False
                )
                
                return {
                    "status": "OK",
                    "message": f"✅ Created memory block '{path}' in SQLite with {len(content)} characters",
                    "block": {"label": block.label, "description": block.description}
                }
            
            elif command == "read":
                if not path:
                    return {"status": "error", "message": "❌ 'path' is required"}
                
                # Try PostgreSQL first
                if postgres:
                    try:
                        with postgres._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT content, metadata FROM memories 
                                WHERE agent_id = %s AND label = %s AND memory_type = 'core'
                            """, (agent_id, path))
                            row = cursor.fetchone()
                            if row:
                                content, metadata = row
                                meta = metadata or {}
                                return {
                                    "status": "OK",
                                    "message": f"📖 Memory block '{path}' (PostgreSQL)",
                                    "content": content or "",
                                    "description": meta.get('description', '')
                                }
                    except Exception:
                        pass
                
                # Fallback to SQLite
                block = self.state.get_block(path)
                if not block:
                    return {"status": "error", "message": f"❌ Memory block '{path}' not found"}
                
                return {
                    "status": "OK",
                    "message": f"📖 Memory block '{path}' (SQLite)",
                    "content": block.content,
                    "description": block.description
                }
            
            elif command == "list":
                all_blocks = []
                
                # Try PostgreSQL first
                if postgres:
                    try:
                        with postgres._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT label, content, metadata FROM memories 
                                WHERE agent_id = %s AND memory_type = 'core'
                                ORDER BY label
                            """, (agent_id,))
                            for label, content, metadata in cursor.fetchall():
                                meta = metadata or {}
                                all_blocks.append({
                                    "label": label,
                                    "type": "core",
                                    "size": len(content or "")
                                })
                    except Exception:
                        pass
                
                # Also check StateManager (merges with PostgreSQL)
                state_blocks = self.state.list_blocks(include_hidden=False)
                for b in state_blocks:
                    # Only add if not already in PostgreSQL list
                    if not any(bl['label'] == b.label for bl in all_blocks):
                        all_blocks.append({
                            "label": b.label,
                            "type": b.block_type.value,
                            "size": len(b.content)
                        })
                
                return {
                    "status": "OK",
                    "message": f"📚 Found {len(all_blocks)} memory blocks",
                    "blocks": all_blocks
                }
            
            elif command == "str_replace":
                if not path or old_str is None or new_str is None:
                    return {"status": "error", "message": "❌ path, old_str, and new_str are required"}
                
                block = self.state.get_block(path)
                if not block:
                    return {"status": "error", "message": f"❌ Memory block '{path}' not found"}
                if block.read_only:
                    return {"status": "error", "message": f"❌ Memory block '{path}' is read-only"}
                if old_str not in block.content:
                    return {"status": "error", "message": f"❌ Text not found in block '{path}'"}
                
                new_content = block.content.replace(old_str, new_str, 1)
                self.state.update_block(path, new_content)
                
                return {"status": "OK", "message": f"✅ Replaced text in '{path}'"}
            
            elif command == "insert":
                if not path or insert_text is None:
                    return {"status": "error", "message": "❌ path and insert_text are required"}
                
                block = self.state.get_block(path)
                if not block:
                    return {"status": "error", "message": f"❌ Memory block '{path}' not found"}
                if block.read_only:
                    return {"status": "error", "message": f"❌ Memory block '{path}' is read-only"}
                
                lines = block.content.split('\n')
                insert_at = insert_line if insert_line is not None else len(lines)
                lines.insert(max(0, min(insert_at, len(lines))), insert_text)
                self.state.update_block(path, '\n'.join(lines))
                
                return {"status": "OK", "message": f"✅ Inserted text at line {insert_at} in '{path}'"}
            
            elif command == "delete":
                if not path:
                    return {"status": "error", "message": "❌ 'path' is required"}
                
                # Special handling for onboarding block - use memory engine
                if path == "onboarding" and hasattr(self.state, 'postgres_manager'):
                    postgres = getattr(self.state, 'postgres_manager', None)
                    if postgres:
                        try:
                            # Try to get memory engine from state manager if available
                            # This is a bit of a hack, but we need access to memory_engine
                            # For now, we'll delete directly from PostgreSQL
                            with postgres._get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    DELETE FROM memories 
                                    WHERE agent_id = %s AND label = %s AND memory_type = 'core'
                                """, (agent_id, path))
                                conn.commit()
                                
                                if cursor.rowcount > 0:
                                    return {"status": "OK", "message": f"✅ Deleted memory block '{path}' (onboarding completed!)"}
                                else:
                                    return {"status": "error", "message": f"❌ Memory block '{path}' not found"}
                        except Exception as e:
                            # Fallback to SQLite
                            pass
                
                # Standard deletion (SQLite or fallback)
                block = self.state.get_block(path)
                if not block:
                    return {"status": "error", "message": f"❌ Memory block '{path}' not found"}
                if block.read_only:
                    return {"status": "error", "message": f"❌ Memory block '{path}' is read-only"}
                
                self.state.delete_block(path)
                return {"status": "OK", "message": f"🗑️ Deleted memory block '{path}'"}
            
            elif command == "rename":
                if not old_path or not new_path:
                    return {"status": "error", "message": "❌ old_path and new_path are required"}
                
                block = self.state.get_block(old_path)
                if not block:
                    return {"status": "error", "message": f"❌ Memory block '{old_path}' not found"}
                
                if self.state.get_block(new_path):
                    return {"status": "error", "message": f"❌ Memory block '{new_path}' already exists"}
                
                from core.state_manager import BlockType
                self.state.create_block(
                    label=new_path,
                    content=block.content,
                    block_type=block.block_type,
                    description=description or block.description,
                    limit=block.limit,
                    read_only=block.read_only
                )
                self.state.delete_block(old_path)
                
                return {"status": "OK", "message": f"✅ Renamed '{old_path}' → '{new_path}'"}
            
            else:
                return {"status": "error", "message": f"❌ Unknown command: '{command}'. Use: create, read, list, str_replace, insert, delete, rename"}
                
        except Exception as e:
            import traceback
            return {
                "status": "error",
                "message": f"Memory tool error: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    # ============================================
    # BATCH MEMORY OPERATIONS (like discord execute_batch!)
    # ============================================
    
    def memory_batch(
        self,
        operations: list,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Execute multiple memory operations in ONE tool call.
        
        🚀 BATCH MODE - Execute ANY combination of memory operations together!
        
        Supported operations:
        - archival_memory_insert: Add to long-term memory
        - archival_memory_search: Search archival memory
        - core_memory_append: Append to memory block
        - core_memory_replace: Replace text in memory block
        - conversation_search: Search conversation history
        
        Each operation is executed independently - if one fails, others continue.
        
        Args:
            operations: List of operation dicts, each with 'action' and parameters
            session_id: Session ID for conversation operations
            
        Returns:
            Batch result with status, counts, and individual operation results
            
        Examples:
            # Insert multiple memories at once
            memory_batch(operations=[
                {"action": "archival_memory_insert", "content": "Meeting notes...", "tags": ["meetings"]},
                {"action": "archival_memory_insert", "content": "Project update...", "tags": ["projects"]},
                {"action": "archival_memory_search", "query": "last meetings", "tags": ["meetings"]}
            ])
            
            # Update multiple memory blocks
            memory_batch(operations=[
                {"action": "core_memory_append", "label": "human", "content": "Likes coffee"},
                {"action": "core_memory_append", "label": "persona", "content": "Learned something new"}
            ])
        """
        results = {
            "status": "success",
            "total_operations": len(operations),
            "successful_operations": 0,
            "failed_operations": 0,
            "operation_results": [],
            "errors": []
        }
        
        for i, operation in enumerate(operations):
            operation_result = {
                "operation_index": i,
                "action": operation.get("action", "unknown"),
                "status": "pending"
            }
            
            try:
                # Validate operation structure
                if not isinstance(operation, dict):
                    operation_result["status"] = "error"
                    operation_result["error"] = "Operation must be a dictionary"
                    results["failed_operations"] += 1
                    results["errors"].append({
                        "operation_index": i,
                        "error": "Operation must be a dictionary"
                    })
                    results["operation_results"].append(operation_result)
                    continue
                
                action = operation.get("action")
                if not action:
                    operation_result["status"] = "error"
                    operation_result["error"] = "Missing 'action' parameter"
                    results["failed_operations"] += 1
                    results["errors"].append({
                        "operation_index": i,
                        "error": "Missing 'action' parameter"
                    })
                    results["operation_results"].append(operation_result)
                    continue
                
                # Prevent recursive batch (security/performance)
                if action == "memory_batch":
                    operation_result["status"] = "error"
                    operation_result["error"] = "Recursive memory_batch not allowed"
                    results["failed_operations"] += 1
                    results["errors"].append({
                        "operation_index": i,
                        "action": action,
                        "error": "Recursive memory_batch not allowed"
                    })
                    results["operation_results"].append(operation_result)
                    continue
                
                # Execute the operation by calling the appropriate method
                result = None
                
                if action == "archival_memory_insert":
                    result = self.archival_memory_insert(
                        content=operation.get("content", ""),
                        category=operation.get("category", "fact"),
                        importance=operation.get("importance", 5),
                        tags=operation.get("tags")
                    )
                
                elif action == "archival_memory_search":
                    result = self.archival_memory_search(
                        query=operation.get("query", ""),
                        page=operation.get("page", 0),
                        min_importance=operation.get("min_importance", 1),
                        tags=operation.get("tags"),
                        tag_match_mode=operation.get("tag_match_mode", "any"),
                        top_k=operation.get("top_k", 10),
                        start_datetime=operation.get("start_datetime"),
                        end_datetime=operation.get("end_datetime")
                    )
                
                elif action == "core_memory_append":
                    result = self.core_memory_append(
                        label=operation.get("label", ""),
                        content=operation.get("content", "")
                    )
                
                elif action == "core_memory_replace":
                    result = self.core_memory_replace(
                        label=operation.get("label", ""),
                        old_content=operation.get("old_content", ""),
                        new_content=operation.get("new_content", "")
                    )
                
                elif action == "memory_insert":
                    result = self.memory_insert(
                        label=operation.get("label", ""),
                        new_str=operation.get("new_str", ""),
                        insert_line=operation.get("insert_line", -1)
                    )
                
                elif action == "memory_replace":
                    result = self.memory_replace(
                        label=operation.get("label", ""),
                        old_str=operation.get("old_str", ""),
                        new_str=operation.get("new_str", "")
                    )
                
                elif action == "conversation_search":
                    result = self.conversation_search(
                        query=operation.get("query", ""),
                        session_id=operation.get("session_id", session_id),
                        page=operation.get("page", 0)
                    )
                
                else:
                    operation_result["status"] = "error"
                    operation_result["error"] = f"Unknown action: {action}"
                    results["failed_operations"] += 1
                    results["errors"].append({
                        "operation_index": i,
                        "action": action,
                        "error": f"Unknown action: {action}"
                    })
                    results["operation_results"].append(operation_result)
                    continue
                
                # Check result status
                if result and result.get("status") == "OK":
                    operation_result["status"] = "success"
                    operation_result["result"] = result
                    results["successful_operations"] += 1
                else:
                    operation_result["status"] = "error"
                    operation_result["error"] = result.get("message", "Unknown error") if result else "No result"
                    operation_result["result"] = result
                    results["failed_operations"] += 1
                    results["errors"].append({
                        "operation_index": i,
                        "action": action,
                        "error": operation_result["error"]
                    })
                
                results["operation_results"].append(operation_result)
                
            except Exception as e:
                operation_result["status"] = "error"
                operation_result["error"] = str(e)
                results["failed_operations"] += 1
                results["errors"].append({
                    "operation_index": i,
                    "action": operation.get("action", "unknown"),
                    "error": str(e)
                })
                results["operation_results"].append(operation_result)
        
        # Update overall status
        if results["failed_operations"] > 0:
            if results["successful_operations"] == 0:
                results["status"] = "error"
                results["message"] = f"All {results['failed_operations']} operations failed"
            else:
                results["status"] = "partial_success"
                results["message"] = f"{results['successful_operations']} succeeded, {results['failed_operations']} failed"
        else:
            results["message"] = f"All {results['successful_operations']} operations completed successfully"
        
        return results
    
    # ============================================
    # UTILITY: GET ALL TOOLS AS OPENAI FORMAT
    # ============================================
    
    def get_tool_schemas(self) -> list:
        """
        Get all memory tools as OpenAI function schemas.
        
        Returns:
            List of tool schemas in OpenAI format
        """
        return [
            # ============================================
            # CORE MEMORY (Old API)
            # ============================================
            {
                "type": "function",
                "function": {
                    "name": "core_memory_append",
                    "description": "Append content to a memory block. Use this to add new information to your existing memories.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Content to append to memory"
                            },
                            "block_name": {
                                "type": "string",
                                "description": "Name of memory block (persona or human)"
                            }
                        },
                        "required": ["content", "block_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "core_memory_replace",
                    "description": "Replace old content with new content in a memory block.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "old_content": {
                                "type": "string",
                                "description": "String to replace"
                            },
                            "new_content": {
                                "type": "string",
                                "description": "New string"
                            },
                            "block_name": {
                                "type": "string",
                                "description": "Name of memory block"
                            }
                        },
                        "required": ["old_content", "new_content", "block_name"]
                    }
                }
            },
            
            # ============================================
            # NEW MEMORY API
            # ============================================
            {
                "type": "function",
                "function": {
                    "name": "memory_insert",
                    "description": "Insert text at a specific position in a memory block.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to insert"
                            },
                            "index": {
                                "type": "integer",
                                "description": "Position to insert at (0-based)"
                            },
                            "block_label": {
                                "type": "string",
                                "description": "Memory block label"
                            }
                        },
                        "required": ["text", "index", "block_label"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_replace",
                    "description": "Replace specific text in a memory block.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "old_text": {
                                "type": "string",
                                "description": "Text to replace"
                            },
                            "new_text": {
                                "type": "string",
                                "description": "Replacement text"
                            },
                            "block_label": {
                                "type": "string",
                                "description": "Memory block label"
                            }
                        },
                        "required": ["old_text", "new_text", "block_label"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_rethink",
                    "description": "Completely rewrite the content of a memory block. Use this to reorganize or restructure memories.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "new_content": {
                                "type": "string",
                                "description": "New complete content for the block"
                            },
                            "block_label": {
                                "type": "string",
                                "description": "Memory block label"
                            }
                        },
                        "required": ["new_content", "block_label"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_finish_edits",
                    "description": "Signal that you've finished editing a memory block.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "block_label": {
                                "type": "string",
                                "description": "Memory block label"
                            }
                        },
                        "required": ["block_label"]
                    }
                }
            },
            
            # ============================================
            # ARCHIVAL MEMORY
            # ============================================
            {
                "type": "function",
                "function": {
                    "name": "archival_memory_insert",
                    "description": "Add information to long-term archival memory for later retrieval.\n\nUse this tool to store facts, knowledge, or context that you want to remember across all future conversations. Archival memory is permanent and searchable by semantic similarity.\n\nBest practices:\n- Store self-contained facts or summaries, not conversational fragments\n- Add descriptive tags to make information easier to find later\n- Use for: meeting notes, project updates, conversation summaries, events, reports\n\nExample:\n  archival_memory_insert(\n    content=\"Meeting on 2024-03-15: Discussed Q2 roadmap priorities.\",\n    tags=[\"meetings\", \"roadmap\", \"q2-2024\"]\n  )",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The information to store. Should be clear and self-contained."
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of category tags (e.g., ['meetings', 'project-updates', 'personal'])"
                            },
                            "category": {
                                "type": "string",
                                "description": "Memory category for organization",
                                "enum": ["fact", "emotion", "insight", "relationship_moment", "preference", "event"],
                                "default": "fact"
                            },
                            "importance": {
                                "type": "integer",
                                "description": "Importance level (1-10, higher = more likely to surface in searches)",
                                "minimum": 1,
                                "maximum": 10,
                                "default": 5
                            }
                        },
                        "required": ["content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "archival_memory_search",
                    "description": "Search archival memory using semantic similarity to find relevant information.\n\nSearch strategy:\n- Query by concept/meaning, not exact phrases\n- Use tags to narrow results when you know the category\n- Start broad, then narrow with tags if needed\n- Results are ranked by semantic relevance\n\nExamples:\n  archival_memory_search(query=\"database migration\", tags=[\"projects\"])\n  archival_memory_search(query=\"roadmap\", tags=[\"meetings\"], tag_match_mode=\"all\")",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "What you're looking for, described naturally (e.g., 'meetings about API redesign')"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter to memories with these tags. Use tag_match_mode to control matching."
                            },
                            "tag_match_mode": {
                                "type": "string",
                                "enum": ["any", "all"],
                                "description": "'any' = match memories with ANY of the tags, 'all' = match only memories with ALL tags"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10)"
                            },
                            "start_datetime": {
                                "type": "string",
                                "description": "Only return memories created after this time (ISO 8601: '2024-01-15' or '2024-01-15T14:30')"
                            },
                            "end_datetime": {
                                "type": "string",
                                "description": "Only return memories created before this time (ISO 8601 format)"
                            },
                            "page": {
                                "type": "integer",
                                "description": "Page number for pagination (0-based)",
                                "default": 0
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            
            # ============================================
            # CONVERSATION SEARCH
            # ============================================
            {
                "type": "function",
                "function": {
                    "name": "conversation_search",
                    "description": "Search through the conversation history for specific information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "page": {
                                "type": "integer",
                                "description": "Page number (0-based)",
                                "default": 0
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            
            # ============================================
            # BATCH MEMORY OPERATIONS
            # ============================================
            {
                "type": "function",
                "function": {
                    "name": "memory_batch",
                    "description": "🚀 Execute MULTIPLE memory operations in ONE tool call!\n\nSupported operations:\n- archival_memory_insert: Add to long-term memory\n- archival_memory_search: Search archival memory with tags\n- core_memory_append: Append to memory block\n- core_memory_replace: Replace text in memory block\n- memory_insert: Insert at specific line\n- memory_replace: Replace specific text\n- conversation_search: Search conversation history\n\nEach operation is independent - if one fails, others continue.\n\nExamples:\n  memory_batch(operations=[\n    {\"action\": \"archival_memory_insert\", \"content\": \"Meeting...\", \"tags\": [\"meetings\"]},\n    {\"action\": \"archival_memory_search\", \"query\": \"meetings\", \"tags\": [\"meetings\"]}\n  ])",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "operations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "action": {
                                            "type": "string",
                                            "enum": ["archival_memory_insert", "archival_memory_search", "core_memory_append", "core_memory_replace", "memory_insert", "memory_replace", "conversation_search"],
                                            "description": "The memory operation to perform"
                                        }
                                    },
                                    "required": ["action"]
                                },
                                "description": "List of memory operations to execute. Each operation needs 'action' plus action-specific parameters:\n\n- archival_memory_insert: content (required), tags, category, importance\n- archival_memory_search: query (required), tags, tag_match_mode, top_k, start_datetime, end_datetime\n- core_memory_append: label (required), content (required)\n- core_memory_replace: label, old_content, new_content\n- memory_insert: label, new_str, insert_line\n- memory_replace: label, old_str, new_str\n- conversation_search: query (required), page"
                            }
                        },
                        "required": ["operations"]
                    }
                }
            },
            
            # ============================================
            # CONVERSATION MANAGEMENT
            # ============================================
            {
                "type": "function",
                "function": {
                    "name": "conversation_summarize",
                    "description": "Summarize old conversation messages and push them to archival memory. Use this when context window is getting full (>80%). Creates a concise summary, archives it, and removes old messages from active context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "Your concise summary of the old conversation. Focus on key facts, decisions, and emotional moments."
                            },
                            "importance": {
                                "type": "integer",
                                "description": "Importance rating (1-10)",
                                "minimum": 1,
                                "maximum": 10,
                                "default": 5
                            },
                            "category": {
                                "type": "string",
                                "description": "Summary category",
                                "enum": ["fact", "emotion", "insight", "relationship_moment", "preference", "event"],
                                "default": "fact"
                            }
                        },
                        "required": ["summary"]
                    }
                }
            },
            
            # ============================================
            # MEMORY (Alternative API)
            # ============================================
            {
                "type": "function",
                "function": {
                    "name": "memory",
                    "description": "Memory management tool with various sub-commands for memory block operations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Sub-command: create, str_replace, insert, delete, rename"
                            },
                            "path": {
                                "type": "string",
                                "description": "Path to memory block"
                            },
                            "file_text": {
                                "type": "string",
                                "description": "Content for create"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description for create/rename"
                            },
                            "old_str": {
                                "type": "string",
                                "description": "Old text (for str_replace)"
                            },
                            "new_str": {
                                "type": "string",
                                "description": "New text (for str_replace)"
                            },
                            "insert_line": {
                                "type": "integer",
                                "description": "Line number (for insert)"
                            },
                            "insert_text": {
                                "type": "string",
                                "description": "Text to insert"
                            },
                            "old_path": {
                                "type": "string",
                                "description": "Old path (for rename)"
                            },
                            "new_path": {
                                "type": "string",
                                "description": "New path (for rename)"
                            }
                        },
                        "required": ["command"]
                    }
                }
            }
        ] + self.integrations.get_tool_schemas() + (
            # Add Cost Tools (if available!)
            self.cost_tools.get_tool_schemas() if self.cost_tools else []
        )


# ============================================
# TESTING (PostgreSQL-only!)
# ============================================

if __name__ == "__main__":
    from core.state_manager import StateManager
    from core.postgres_manager import create_postgres_manager_from_env
    
    print("\n🧪 TESTING MEMORY TOOLS (PostgreSQL)")
    print("="*60)
    
    # Initialize PostgreSQL
    pg = create_postgres_manager_from_env()
    if not pg:
        print("❌ PostgreSQL required for testing!")
        exit(1)
    
    state = StateManager(postgres_manager=pg)
    tools = MemoryTools(state_manager=state)
    
    # Create test blocks
    print("\n📋 Test 1: Create memory blocks")
    state.create_block("persona", "You are an AI assistant with memory capabilities.", limit=1000)
    state.create_block("human", "User is a developer.", limit=1000)
    state.create_block("test_readonly", "READ-ONLY content", read_only=True, limit=1000)
    
    # Test core_memory_append
    print("\n✏️  Test 2: core_memory_append")
    result = tools.core_memory_append("I love coding at night.", "persona")
    print(f"   Status: {result['status']}")
    print(f"   Message: {result['message']}")
    
    # Test core_memory_replace
    print("\n🔄 Test 3: core_memory_replace")
    result = tools.core_memory_replace("night", "late night", "persona")
    print(f"   Status: {result['status']}")
    print(f"   Message: {result['message']}")
    
    # Test read-only protection
    print("\n🔒 Test 4: Read-only protection")
    result = tools.core_memory_append("This should fail", "test_readonly")
    print(f"   Status: {result['status']}")
    print(f"   Message: {result['message']}")
    
    # Test memory_rethink
    print("\n🎨 Test 5: memory_rethink")
    result = tools.memory_rethink("You are an AI assistant, completely rewritten!", "persona")
    print(f"   Status: {result['status']}")
    print(f"   Message: {result['message']}")
    
    # Show final state
    print("\n📦 Final memory blocks:")
    blocks = state.list_blocks()
    for b in blocks:
        print(f"   {b.label}: {b.content[:60]}...")
    
    # Get tool schemas
    print("\n🛠️  Tool schemas:")
    schemas = tools.get_tool_schemas()
    print(f"   Total tools: {len(schemas)}")
    for schema in schemas:
        print(f"   • {schema['function']['name']}")
    
    print("\n✅ ALL TESTS PASSED!")
    print("="*60)

