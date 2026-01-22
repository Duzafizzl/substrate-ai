"""
Cost Tracker for OpenRouter API Usage (PostgreSQL-ONLY)
Tracks and persists token usage and costs across server restarts

100% PostgreSQL - NO SQLite!
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .postgres_manager import PostgresManager

logger = logging.getLogger(__name__)


class CostTracker:
    """
    Persistent cost tracking for OpenRouter API usage.
    
    100% PostgreSQL backend!
    
    Stores:
    - Timestamp
    - Model ID
    - Input tokens
    - Output tokens
    - Input cost
    - Output cost
    - Total cost
    - Agent ID (optional)
    - Session ID (optional)
    """
    
    def __init__(self, postgres_manager: 'PostgresManager'):
        """
        Initialize cost tracker with PostgreSQL manager.
        
        Args:
            postgres_manager: PostgresManager instance (REQUIRED!)
        """
        if not postgres_manager:
            raise ValueError("CostTracker requires PostgresManager! No SQLite fallback.")
        
        self.pg = postgres_manager
        logger.info("✅ Cost Tracker initialized (PostgreSQL-only)")
    
    def log_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        input_cost: float,
        output_cost: float,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> float:
        """
        Log a single API request cost to PostgreSQL.
        
        Args:
            model: Model ID (e.g., "qwen/qwen-2.5-72b-instruct")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            input_cost: Cost of input tokens in USD
            output_cost: Cost of output tokens in USD
            agent_id: Optional agent ID
            session_id: Optional session ID
            metadata: Optional metadata dict
        
        Returns:
            Total cost of this request
        """
        import json
        total_cost = input_cost + output_cost
        
        with self.pg._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO costs (
                    timestamp, model, input_tokens, output_tokens,
                    input_cost, output_cost, total_cost,
                    agent_id, session_id, metadata
                ) VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                model, input_tokens, output_tokens,
                input_cost, output_cost, total_cost,
                agent_id, session_id, json.dumps(metadata or {})
            ))
            
            cursor.close()
        
        logger.info(
            f"💰 Cost logged: {model} | "
            f"In: {input_tokens}tok (${input_cost:.6f}) | "
            f"Out: {output_tokens}tok (${output_cost:.6f}) | "
            f"Total: ${total_cost:.6f}"
        )
        
        return total_cost
    
    def get_total_cost(self, since: Optional[str] = None) -> float:
        """
        Get total cost across all requests.
        
        Args:
            since: ISO timestamp to filter from (e.g., "2025-11-09T00:00:00")
        
        Returns:
            Total cost in USD
        """
        with self.pg._get_connection() as conn:
            cursor = conn.cursor()
            
            if since:
                cursor.execute("""
                    SELECT COALESCE(SUM(total_cost), 0) FROM costs
                    WHERE timestamp >= %s
                """, (since,))
            else:
                cursor.execute("SELECT COALESCE(SUM(total_cost), 0) FROM costs")
            
            result = cursor.fetchone()[0]
            cursor.close()
            
        return float(result) if result else 0.0
    
    def get_statistics(self) -> Dict:
        """
        Get detailed cost statistics from PostgreSQL.
        
        Returns:
            {
                'total_cost': float,
                'total_tokens': int,
                'total_requests': int,
                'by_model': [{model, requests, tokens, cost}, ...],
                'today': float,
                'this_week': float,
                'this_month': float
            }
        """
        with self.pg._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total cost
            cursor.execute("SELECT COALESCE(SUM(total_cost), 0) FROM costs")
            total_cost = float(cursor.fetchone()[0] or 0)
            
            # Total tokens
            cursor.execute("""
                SELECT COALESCE(SUM(input_tokens + output_tokens), 0) FROM costs
            """)
            total_tokens = int(cursor.fetchone()[0] or 0)
            
            # Total requests
            cursor.execute("SELECT COUNT(*) FROM costs")
            total_requests = int(cursor.fetchone()[0] or 0)
            
            # By model
            cursor.execute("""
                SELECT 
                    model,
                    COUNT(*) as requests,
                    SUM(input_tokens + output_tokens) as tokens,
                    SUM(total_cost) as cost
                FROM costs
                GROUP BY model
                ORDER BY cost DESC
            """)
            by_model = []
            for row in cursor.fetchall():
                by_model.append({
                    'model': row[0],
                    'requests': int(row[1]),
                    'tokens': int(row[2]) if row[2] else 0,
                    'cost': float(row[3]) if row[3] else 0.0
                })
            
            # Today (UTC)
            cursor.execute("""
                SELECT COALESCE(SUM(total_cost), 0) FROM costs
                WHERE timestamp >= CURRENT_DATE
            """)
            today_cost = float(cursor.fetchone()[0] or 0)
            
            # This week
            cursor.execute("""
                SELECT COALESCE(SUM(total_cost), 0) FROM costs
                WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
            """)
            week_cost = float(cursor.fetchone()[0] or 0)
            
            # This month
            cursor.execute("""
                SELECT COALESCE(SUM(total_cost), 0) FROM costs
                WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE)
            """)
            month_cost = float(cursor.fetchone()[0] or 0)
            
            cursor.close()
        
        return {
            'total_cost': total_cost,
            'total_tokens': total_tokens,
            'total_requests': total_requests,
            'by_model': by_model,
            'today': today_cost,
            'this_week': week_cost,
            'this_month': month_cost
        }
    
    def get_recent_requests(self, limit: int = 10) -> List[Dict]:
        """
        Get recent API requests from PostgreSQL.
        
        Args:
            limit: Maximum number of requests to return
        
        Returns:
            List of request dicts with all fields
        """
        with self.pg._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    timestamp, model, input_tokens, output_tokens,
                    input_cost, output_cost, total_cost, agent_id, session_id
                FROM costs
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
            
            requests = []
            for row in cursor.fetchall():
                requests.append({
                    'timestamp': row[0].isoformat() if row[0] else '',
                    'model': row[1],
                    'input_tokens': int(row[2]),
                    'output_tokens': int(row[3]),
                    'input_cost': float(row[4]),
                    'output_cost': float(row[5]),
                    'total_cost': float(row[6]),
                    'agent_id': row[7],
                    'session_id': row[8]
                })
            
            cursor.close()
        
        return requests
    
    def clear_all_costs(self) -> int:
        """
        Clear all cost records from PostgreSQL.
        
        Returns:
            Number of records deleted
        """
        with self.pg._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM costs")
            count = cursor.fetchone()[0]
            
            cursor.execute("DELETE FROM costs")
            cursor.close()
        
        logger.warning(f"🗑️ Cleared {count} cost records from PostgreSQL")
        return count


# OpenRouter Pricing (as of Jan 2026)
# Prices per 1M tokens in USD
# 💾 PROMPT CACHING: Multi-provider cache pricing!
#
# Provider strategies:
# - Anthropic: cache_write_5m (1.25x), cache_write_1h (2x), cache_read (0.1x)
# - OpenAI: cache_write (FREE!), cache_read (0.25x-0.50x depending on model)
# - DeepSeek: cache_write (1x input), cache_read (0.1x)
# - Gemini 2.5: implicit caching, cache_write (FREE!), cache_read (0.25x)
# - Grok/Groq/Moonshot: cache_write (FREE!), cache_read varies by provider
OPENROUTER_PRICING = {
    # Qwen models (automatic caching, no special pricing yet)
    'qwen/qwen-2.5-72b-instruct': {
        'input': 0.35,
        'output': 0.40
    },
    'qwen/qwen-2.5-7b-instruct': {
        'input': 0.05,
        'output': 0.10
    },
    'qwen/qwen3-vl-235b-a22b-thinking': {
        'input': 5.00,
        'output': 10.00
    },
    'qwen/qwen3-vl-30b-a3b-instruct': {
        'input': 0.80,
        'output': 1.50
    },
    'qwen/qwen3-vl-30b-a3b-thinking': {
        'input': 0.20,
        'output': 1.00
    },
    'openrouter/polaris-alpha': {
        'input': 0.00,
        'output': 0.00
    },
    
    # Mistral models (automatic caching, no special pricing yet)
    'mistralai/mistral-large-2411': {
        'input': 2.00,
        'output': 6.00
    },
    'mistralai/mistral-small-2501': {
        'input': 0.20,
        'output': 0.60
    },
    
    # 💾 Claude models WITH CACHE PRICING
    # Claude Opus 4.5
    'anthropic/claude-opus-4.5': {
        'input': 5.00,
        'output': 25.00,
        'cache_write_5m': 6.25,    # 1.25x
        'cache_write_1h': 10.00,   # 2x
        'cache_read': 0.50         # 0.1x (90% savings!)
    },
    # Claude Sonnet 4.5 
    'anthropic/claude-sonnet-4.5': {
        'input': 3.00,
        'output': 15.00,
        'cache_write_5m': 3.75,
        'cache_write_1h': 6.00,
        'cache_read': 0.30
    },
    # Claude Sonnet 4
    'anthropic/claude-sonnet-4': {
        'input': 3.00,
        'output': 15.00,
        'cache_write_5m': 3.75,
        'cache_write_1h': 6.00,
        'cache_read': 0.30
    },
    # Claude 3.5 Sonnet (legacy name)
    'anthropic/claude-3.5-sonnet': {
        'input': 3.00,
        'output': 15.00,
        'cache_write_5m': 3.75,
        'cache_write_1h': 6.00,
        'cache_read': 0.30
    },
    # Claude Haiku 4.5
    'anthropic/claude-haiku-4.5': {
        'input': 1.00,
        'output': 5.00,
        'cache_write_5m': 1.25,
        'cache_write_1h': 2.00,
        'cache_read': 0.10
    },
    # Claude 3.5 Haiku (legacy name)
    'anthropic/claude-3.5-haiku': {
        'input': 0.80,
        'output': 4.00,
        'cache_write_5m': 1.00,
        'cache_write_1h': 1.60,
        'cache_read': 0.08
    },
    # Claude 3 Haiku
    'anthropic/claude-3-haiku': {
        'input': 0.25,
        'output': 1.25,
        'cache_write_5m': 0.30,
        'cache_write_1h': 0.50,
        'cache_read': 0.03
    },
    
    # 💾 OpenAI models WITH AUTOMATIC CACHE PRICING
    # Cache writes: FREE! Cache reads: 0.50x (GPT-4) or 0.25x (GPT-4o)
    # Min 1024 tokens for caching
    'openai/gpt-4-turbo': {
        'input': 10.00,
        'output': 30.00,
        'cache_read': 5.00  # 0.50x
    },
    'openai/gpt-4o': {
        'input': 2.50,
        'output': 10.00,
        'cache_read': 1.25  # 0.50x
    },
    'openai/gpt-4o-mini': {
        'input': 0.15,
        'output': 0.60,
        'cache_read': 0.0375  # 0.25x
    },
    'openai/gpt-3.5-turbo': {
        'input': 0.50,
        'output': 1.50,
        'cache_read': 0.125  # 0.25x
    },
    'openai/o1': {
        'input': 15.00,
        'output': 60.00,
        'cache_read': 7.50  # 0.50x
    },
    'openai/o1-mini': {
        'input': 3.00,
        'output': 12.00,
        'cache_read': 1.50  # 0.50x
    },
    
    # 💾 Gemini models WITH CACHE PRICING
    # Gemini 2.5: Implicit caching (automatic!), cache writes FREE, cache reads 0.25x
    # Gemini 1.5/2.0: Explicit cache_control, 5m TTL, min 4096 tokens
    'google/gemini-2.5-pro': {
        'input': 1.25,
        'output': 5.00,
        'cache_read': 0.3125  # 0.25x (implicit caching!)
    },
    'google/gemini-2.5-flash': {
        'input': 0.10,
        'output': 0.40,
        'cache_read': 0.025  # 0.25x (implicit caching!)
    },
    'google/gemini-1.5-pro': {
        'input': 1.25,
        'output': 5.00,
        'cache_read': 0.3125  # 0.25x
    },
    'google/gemini-2.0-flash': {
        'input': 0.10,
        'output': 0.40,
        'cache_read': 0.025  # 0.25x
    },
    
    # 💾 DeepSeek WITH AUTOMATIC CACHE PRICING
    # Cache writes: 1x input cost, Cache reads: 0.1x (90% savings!)
    'deepseek/deepseek-chat': {
        'input': 0.14,
        'output': 0.28,
        'cache_write': 0.14,  # 1x (same as input)
        'cache_read': 0.014   # 0.1x
    },
    'deepseek/deepseek-v3': {
        'input': 0.14,
        'output': 0.28,
        'cache_write': 0.14,  # 1x (same as input)
        'cache_read': 0.014   # 0.1x
    },
    'deepseek/deepseek-reasoner': {
        'input': 0.55,
        'output': 2.19,
        'cache_write': 0.55,  # 1x (same as input)
        'cache_read': 0.055   # 0.1x
    },
    
    # Default pricing for unknown models
    'default': {
        'input': 1.00,
        'output': 3.00
    }
}


def calculate_cost(
    model: str, 
    input_tokens: int, 
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_ttl: str = "1h"
) -> tuple[float, float]:
    """
    Calculate cost for a model request WITH PROMPT CACHING support!
    
    💾 Multi-Provider Cache Pricing:
    - Anthropic: cache_write_5m (1.25x), cache_write_1h (2x), cache_read (0.1x)
    - OpenAI: cache_write FREE, cache_read (0.25x-0.50x)
    - DeepSeek: cache_write (1x input), cache_read (0.1x)
    - Gemini 2.5: cache_write FREE, cache_read (0.25x)
    - Others: Automatic caching (provider handles it)
    
    Args:
        model: Model ID
        input_tokens: Number of regular input tokens
        output_tokens: Number of output tokens
        cache_creation_tokens: Tokens written to cache
        cache_read_tokens: Tokens read from cache (cheap!)
        cache_ttl: Cache TTL used ("5m" or "1h", for Anthropic)
    
    Returns:
        (input_cost, output_cost) in USD
    """
    pricing = OPENROUTER_PRICING.get(model, OPENROUTER_PRICING['default'])
    
    # 1. Regular input tokens (not cached)
    regular_input_tokens = input_tokens - cache_creation_tokens - cache_read_tokens
    regular_input_tokens = max(0, regular_input_tokens)  # Ensure non-negative
    regular_input_cost = (regular_input_tokens / 1_000_000) * pricing['input']
    
    # 2. Cache WRITE cost (varies by provider!)
    cache_write_cost = 0.0
    if cache_creation_tokens > 0:
        # Priority 1: Anthropic TTL-based pricing (5m or 1h)
        if cache_ttl == "5m" and 'cache_write_5m' in pricing:
            cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing['cache_write_5m']
        elif cache_ttl == "1h" and 'cache_write_1h' in pricing:
            cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing['cache_write_1h']
        # Priority 2: Generic cache_write (e.g., DeepSeek = 1x input)
        elif 'cache_write' in pricing:
            cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing['cache_write']
        # Priority 3: Fallback to regular input price (conservative estimate)
        else:
            # OpenAI/Gemini 2.5: cache_write is FREE (0 cost)
            # But we don't have a way to distinguish, so use 0 if no cache_write key
            cache_write_cost = 0.0
    
    # 3. Cache READ cost (cheap! 0.1x-0.5x depending on provider)
    cache_read_cost = 0.0
    if cache_read_tokens > 0:
        if 'cache_read' in pricing:
            cache_read_cost = (cache_read_tokens / 1_000_000) * pricing['cache_read']
        else:
            # Fallback: Use regular input price if no cache pricing
            cache_read_cost = (cache_read_tokens / 1_000_000) * pricing['input']
    
    # 4. Output cost (unchanged)
    output_cost = (output_tokens / 1_000_000) * pricing['output']
    
    # Total input cost = regular + cache write + cache read
    total_input_cost = regular_input_cost + cache_write_cost + cache_read_cost
    
    return (total_input_cost, output_cost)


def calculate_cache_savings(
    model: str,
    cache_read_tokens: int,
    cache_ttl: str = "1h"
) -> float:
    """
    Calculate how much you SAVED by using prompt caching!
    
    💰 Savings by Provider:
    - Anthropic: 90% savings (0.1x vs 1x)
    - OpenAI: 50-75% savings (0.25x-0.50x vs 1x)
    - DeepSeek: 90% savings (0.1x vs 1x)
    - Gemini 2.5: 75% savings (0.25x vs 1x)
    
    Args:
        model: Model ID
        cache_read_tokens: Tokens read from cache
        cache_ttl: Cache TTL used (for display only, not used in calculation)
    
    Returns:
        Amount saved in USD
    """
    if cache_read_tokens == 0:
        return 0.0
    
    pricing = OPENROUTER_PRICING.get(model, OPENROUTER_PRICING['default'])
    
    # What it WOULD have cost without caching
    full_price = (cache_read_tokens / 1_000_000) * pricing['input']
    
    # What it actually cost with caching
    cache_price = 0.0
    if 'cache_read' in pricing:
        cache_price = (cache_read_tokens / 1_000_000) * pricing['cache_read']
    else:
        cache_price = full_price  # No savings if no cache pricing
    
    return full_price - cache_price
