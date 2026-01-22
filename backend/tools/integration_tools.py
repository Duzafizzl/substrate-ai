#!/usr/bin/env python3
"""
Integration Tools for Substrate AI

These are the tools the AI uses to interact with external services!

Communication & Control:
- discord_tool (Full Discord integration - DMs, channels, tasks, etc.)
- spotify_control (Full Spotify control - search, play, queue, playlists)

Built to give the AI FULL CONTROL! 🔥
"""

import sys
import os
import json
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the actual tool implementations
from tools.discord_tool import discord_tool as _discord_tool
from tools.spotify_control import spotify_control as _spotify_control
from tools.web_search import web_search as _web_search
from tools.fetch_webpage import fetch_webpage as _fetch_webpage

# Import FREE search tools (no API key needed!)
from tools.free_web_search import get_free_search, smart_search as _smart_search
from tools.arxiv_search import get_arxiv_search, arxiv_search as _arxiv_search
from tools.deep_research import get_deep_research, init_deep_research
from tools.jina_reader import get_jina_reader, fetch_webpage as _jina_fetch
from tools.pdf_reader import get_pdf_reader, read_arxiv_paper as _read_arxiv
from tools.places_search import get_places_search, search_places as _search_places

# Import cost tracker for cost tools
from core.cost_tracker import CostTracker
from tools.cost_tools import CostTools


class IntegrationTools:
    """
    Integration tools for external services.
    
    The AI uses these to control Discord and Spotify!
    """
    
    def __init__(self, cost_tracker: CostTracker = None, postgres_manager=None):
        """Initialize integration tools."""
        # Initialize cost tools
        if cost_tracker:
            self.cost_tools = CostTools(cost_tracker)
        elif postgres_manager:
            # Create CostTracker with postgres_manager
            self.cost_tools = CostTools(CostTracker(postgres_manager=postgres_manager))
        else:
            # No cost tracking available without PostgreSQL
            self.cost_tools = None
            print("⚠️ Cost tools disabled - PostgreSQL required")
        
        # Initialize FREE search tools (no API key!)
        try:
            self.free_search = get_free_search()
            print("✅ Free Web Search initialized (DuckDuckGo + Wikipedia)")
        except Exception as e:
            print(f"⚠️ Free Web Search init failed: {e}")
            self.free_search = None
        
        try:
            self.arxiv_search = get_arxiv_search()
            print("✅ ArXiv Search initialized (Academic Papers)")
        except Exception as e:
            print(f"⚠️ ArXiv Search init failed: {e}")
            self.arxiv_search = None
        
        try:
            self.deep_research = init_deep_research()
            print("✅ Deep Research initialized (Multi-Step Research)")
        except Exception as e:
            print(f"⚠️ Deep Research init failed: {e}")
            self.deep_research = None
        
        try:
            self.jina_reader = get_jina_reader()
            print("✅ Jina AI Reader initialized (FREE Webpage Fetcher)")
        except Exception as e:
            print(f"⚠️ Jina Reader init failed: {e}")
            self.jina_reader = None
        
        try:
            self.pdf_reader = get_pdf_reader()
            print("✅ PDF Reader initialized (ArXiv LaTeX + PyMuPDF)")
        except Exception as e:
            print(f"⚠️ PDF Reader init failed: {e}")
            self.pdf_reader = None
        
        try:
            self.places_search = get_places_search()
            print("✅ Places Search initialized (OpenStreetMap FREE!)")
        except Exception as e:
            print(f"⚠️ Places Search init failed: {e}")
            self.places_search = None
        
        print("✅ Integration Tools initialized")
    
    # ============================================
    # DISCORD TOOL
    # ============================================
    
    def discord_tool(self, **kwargs) -> Dict[str, Any]:
        """
        Unified Discord integration tool.
        
        Actions:
        - send_message: Send DM or channel message
        - read_messages: Read message history with time filters
        - list_guilds: List all Discord servers
        - list_channels: List channels in a server
        - create_task: Schedule a task
        - delete_task: Delete a scheduled task
        - list_tasks: List all scheduled tasks
        - download_file: Download file from message
        
        Returns:
            Dict with status and result
        """
        try:
            result = _discord_tool(**kwargs)
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"Discord tool error: {str(e)}"
            }
    
    # ============================================
    # SPOTIFY CONTROL
    # ============================================
    
    def spotify_control(self, **kwargs) -> Dict[str, Any]:
        """
        Control Spotify playback and manage playlists.
        
        Actions:
        - search: Search for tracks/albums/artists
        - play: Play a track/album/playlist
        - queue: Add tracks to queue
        - skip: Skip current track
        - pause: Pause playback
        - resume: Resume playback
        - get_current: Get currently playing track
        - create_playlist: Create new playlist
        - add_to_playlist: Add tracks to playlist
        
        Returns:
            Dict with status and result
        """
        try:
            result = _spotify_control(**kwargs)
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"Spotify control error: {str(e)}"
            }
    
    # ============================================
    # WEB SEARCH (FREE - DuckDuckGo!)
    # ============================================
    
    def web_search(self, query: str, max_results: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Search the web using DuckDuckGo (FREE!).
        
        Args:
            query: Search query
            max_results: Max results to return (default: 10)
        
        Returns:
            {
                'status': 'OK' or 'error',
                'query': str,
                'results': List[Dict],  # Search results
                'total_results': int
            }
        """
        if not self.free_search:
            return {
                "status": "error",
                "message": "Free web search not available"
            }
        
        try:
            result = self.free_search.search(query, max_results=max_results, **kwargs)
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"Web search error: {str(e)}"
            }
    
    # ============================================
    # ARXIV SEARCH (FREE - Academic Papers!)
    # ============================================
    
    def arxiv_search(self, query: str, max_results: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Search ArXiv for academic papers (FREE!).
        
        Args:
            query: Search query
            max_results: Max results to return (default: 10)
        
        Returns:
            {
                'status': 'OK' or 'error',
                'query': str,
                'results': List[Dict],  # Papers
                'total_results': int
            }
        """
        if not self.arxiv_search:
            return {
                "status": "error",
                "message": "ArXiv search not available"
            }
        
        try:
            result = _arxiv_search(query, max_results=max_results, **kwargs)
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"ArXiv search error: {str(e)}"
            }
    
    # ============================================
    # DEEP RESEARCH (FREE - Multi-Step!)
    # ============================================
    
    def deep_research(self, query: str, depth: int = 2, **kwargs) -> Dict[str, Any]:
        """
        Perform deep multi-step research (FREE!).
        
        Combines:
        - DuckDuckGo web search
        - Wikipedia for factual knowledge
        - ArXiv for academic papers
        - Multi-step analysis
        
        Args:
            query: Research question
            depth: Number of sub-questions (1-5)
        
        Returns:
            {
                'status': 'OK' or 'error',
                'query': str,
                'sub_questions': List[str],
                'sources': List[Dict],
                'report': str,  # Markdown report
                'total_sources': int
            }
        """
        if not self.deep_research:
            return {
                "status": "error",
                "message": "Deep research not available"
            }
        
        try:
            result = self.deep_research.research(query, depth=depth, **kwargs)
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"Deep research error: {str(e)}"
            }
    
    # ============================================
    # FETCH WEBPAGE (FREE - Jina AI Reader!)
    # ============================================
    
    def fetch_webpage(self, url: str, max_chars: int = 10000, **kwargs) -> Dict[str, Any]:
        """
        Fetch webpage and convert to Markdown using Jina AI (FREE!).
        
        Args:
            url: URL to fetch
            max_chars: Max characters to return (default: 10000 to save context)
        
        Returns:
            {
                'status': 'OK' or 'error',
                'url': str,
                'markdown': str,  # Clean Markdown content
                'title': str,
                'length': int
            }
        """
        if not self.jina_reader:
            return {
                "status": "error",
                "message": "Jina Reader not available"
            }
        
        try:
            result = self.jina_reader.fetch(url, max_chars=max_chars, **kwargs)
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"Fetch webpage error: {str(e)}"
            }
    
    # ============================================
    # PDF READER (FREE - ArXiv LaTeX + PyMuPDF!)
    # ============================================
    
    def read_pdf(self, arxiv_id: str = None, file_path: str = None, max_chars: int = 20000, **kwargs) -> Dict[str, Any]:
        """
        Read PDF or ArXiv paper (LaTeX preferred!).
        
        Args:
            arxiv_id: ArXiv ID (e.g., "1706.03762") - uses LaTeX source if available
            file_path: Local PDF file path
            max_chars: Max characters (default: 20000)
        
        Returns:
            {
                'status': 'OK' or 'error',
                'text': str,  # Extracted text
                'source': 'latex' or 'pdf',
                'length': int
            }
        """
        if not self.pdf_reader:
            return {"status": "error", "message": "PDF Reader not available"}
        
        try:
            if arxiv_id:
                result = self.pdf_reader.read_arxiv_paper(arxiv_id, max_chars=max_chars)
            elif file_path:
                result = self.pdf_reader.read_pdf_file(file_path, max_chars=max_chars)
            else:
                return {"status": "error", "message": "Must provide arxiv_id or file_path"}
            
            return result
        except Exception as e:
            return {"status": "error", "message": f"PDF read error: {str(e)}"}
    
    # ============================================
    # PLACES SEARCH (FREE - OpenStreetMap!)
    # ============================================
    
    def search_places(self, query: str, location: str = None, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Search for places (restaurants, shops, POIs) using OpenStreetMap (FREE!).
        
        Args:
            query: Search query (e.g., "pizza restaurant", "coffee shop", "supermarket")
            location: Location to search near (e.g., "Berlin", "New York")
            limit: Max results (default: 10)
        
        Returns:
            {
                'status': 'OK' or 'error',
                'query': str,
                'results': [
                    {
                        'name': str,
                        'type': str,
                        'address': str,
                        'lat': float,
                        'lon': float,
                        'details': Dict  # opening_hours, phone, website, etc.
                    },
                    ...
                ],
                'total_results': int
            }
        """
        if not self.places_search:
            return {"status": "error", "message": "Places Search not available"}
        
        try:
            result = self.places_search.search(query, location=location, limit=limit)
            return result
        except Exception as e:
            return {"status": "error", "message": f"Places search error: {str(e)}"}
    
    # ============================================
    # TOOL SCHEMAS
    # ============================================
    
    def get_tool_schemas(self) -> list:
        """
        Get all integration tool schemas in OpenAI format.
        
        Returns:
            List of tool schemas
        """
        # Load schemas from JSON files
        schemas = []
        
        tool_names = [
            'discord_tool',
            'spotify_control'
        ]
        
        for tool_name in tool_names:
            schema_file = os.path.join(
                os.path.dirname(__file__),
                f'{tool_name}_schema.json'
            )
            
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                    schemas.append({
                        "type": "function",
                        "function": schema
                    })
            except Exception as e:
                print(f"⚠️  Could not load schema for {tool_name}: {e}")
        
        # Add cost tools (self-awareness! 💰)
        cost_schemas = self.cost_tools.get_tool_schemas()
        schemas.extend(cost_schemas)
        
        # Add FREE tools (no API key! 🦆)
        free_tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "fetch_webpage",
                    "description": "Fetch any webpage and convert to clean Markdown using Jina AI (FREE!). Removes ads, navigation, etc. Perfect for reading articles, documentation, or any web content. ⚠️ Returns up to 10KB by default to save context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to fetch (can include https:// or not)"
                            },
                            "max_chars": {
                                "type": "integer",
                                "description": "Maximum characters to return (default: 10000, RECOMMENDED: 5000-10000 to save context!)",
                                "minimum": 1000,
                                "maximum": 50000
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web using DuckDuckGo (FREE! No API key needed). Returns web search results with titles, URLs, and snippets. ⚠️ Use sparingly - max 10 results recommended to preserve context window!",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10, RECOMMENDED MAX: 10 to save context!)",
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "arxiv_search",
                    "description": "Search ArXiv for academic papers (FREE! 2M+ papers). Returns papers with titles, authors, abstracts, and PDF links. Perfect for scientific/technical research. ⚠️ Papers have long abstracts - max 5 recommended!",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (keywords, topics, authors)"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of papers to return (default: 5, RECOMMENDED MAX: 5 due to long abstracts!)",
                                "minimum": 1,
                                "maximum": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "deep_research",
                    "description": "Perform deep multi-step research (FREE!). Combines DuckDuckGo web search, Wikipedia, and ArXiv academic papers. Generates comprehensive Markdown reports with multiple sources. ⚠️ WARNING: VERY CONTEXT-HEAVY! Use only for critical research tasks. Generates 5-20KB of text. Consider using simple web_search first!",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Research question or topic"
                            },
                            "depth": {
                                "type": "integer",
                                "description": "Number of sub-questions to explore (1-3, default: 2, RECOMMENDED MAX: 2 to save context!)",
                                "minimum": 1,
                                "maximum": 3
                            },
                            "max_sources": {
                                "type": "integer",
                                "description": "Maximum sources per sub-question (default: 5, RECOMMENDED MAX: 5 to save context!)",
                                "minimum": 1,
                                "maximum": 5
                            },
                            "include_academic": {
                                "type": "boolean",
                                "description": "Include ArXiv academic papers (default: true)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_pdf",
                    "description": "Read PDF or ArXiv paper (FREE!). For ArXiv papers, extracts LaTeX source (cleaner, formulas preserved!). For other PDFs, uses PyMuPDF. ⚠️ Returns up to 20KB to save context. Use when user asks to read a paper in detail or provides a PDF.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "arxiv_id": {
                                "type": "string",
                                "description": "ArXiv ID (e.g., '1706.03762', '2103.14030')"
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Local PDF file path (if not ArXiv paper)"
                            },
                            "max_chars": {
                                "type": "integer",
                                "description": "Maximum characters to return (default: 20000, RECOMMENDED: 10000-20000)",
                                "minimum": 5000,
                                "maximum": 50000
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_places",
                    "description": "Search for places, restaurants, shops, POIs using OpenStreetMap (FREE!). Great for finding nearby businesses, attractions, addresses. Returns location details, coordinates, opening hours (if available). ⚠️ Use sparingly - max 10 results recommended.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'pizza restaurant', 'coffee shop', 'supermarket', 'hotel')"
                            },
                            "location": {
                                "type": "string",
                                "description": "Location to search near (e.g., 'Berlin', 'New York', 'London')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 10, RECOMMENDED MAX: 10)",
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        schemas.extend(free_tool_schemas)
        
        return schemas


# ============================================
# STANDALONE TEST
# ============================================

if __name__ == "__main__":
    print("="*60)
    print("🧪 INTEGRATION TOOLS TEST")
    print("="*60)
    
    tools = IntegrationTools()
    
    # Test schema loading
    print("\n📋 Tool Schemas:")
    schemas = tools.get_tool_schemas()
    print(f"   Total: {len(schemas)}")
    for schema in schemas:
        name = schema['function']['name']
        desc = schema['function'].get('description', '')[:60]
        print(f"   • {name}: {desc}...")
    
    print("\n✅ Integration Tools ready!")
    print("="*60)

