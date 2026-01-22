"""
Model Context Window Helper

Gets the MAXIMUM context window size for a given model.
Always uses the maximum available, not a default!
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# Cache for OpenRouter model lookups (to avoid repeated API calls)
_openrouter_model_cache: dict[str, int] = {}

# Known model context windows (from OpenRouter)
# These are the MAXIMUM sizes - we always use the max!
MODEL_CONTEXT_WINDOWS = {
    # Polaris
    "openrouter/polaris-alpha": 256000,  # MAXIMUM: 256k tokens!
    
    # OpenAI
    "openai/gpt-4": 8192,
    "openai/gpt-4-turbo": 128000,
    "openai/gpt-4o": 128000,
    "openai/o1": 200000,
    "openai/o1-preview": 200000,
    "openai/o1-mini": 128000,
    
    # Anthropic
    "anthropic/claude-3-opus": 200000,
    "anthropic/claude-3-sonnet": 200000,
    "anthropic/claude-3-haiku": 200000,
    "anthropic/claude-3.5-sonnet": 200000,
    "anthropic/claude-opus-4-1-20250805": 200000,
    
    # Qwen
    "qwen/qwen-2.5-72b-instruct": 128000,
    "qwen/qwen-2.5-32b-instruct": 128000,
    
    # DeepSeek
    "deepseek/deepseek-r1": 64000,
    "deepseek/deepseek-reasoner": 64000,
    
    # Kimi
    "moonshotai/kimi-k2-thinking": 200000,
    
    # Mistral
    "mistralai/mistral-large-2": 128000,
    
    # Llama
    "meta-llama/llama-3.1-70b-instruct": 128000,
    "meta-llama/llama-3.1-8b-instruct": 128000,
}

# Default fallback (if model not in list)
DEFAULT_MAX_CONTEXT = 128000


def get_max_context_window(model_id: str) -> int:
    """
    Get the MAXIMUM context window size for a model.
    
    Always returns the MAXIMUM available, not a default!
    
    Priority:
    1. Direct match in MODEL_CONTEXT_WINDOWS
    2. OpenRouter API (if not in cache)
    3. Cached value from OpenRouter
    4. Heuristic matching (fallback)
    5. Default fallback
    
    Args:
        model_id: Model identifier (e.g., "openrouter/polaris-alpha")
        
    Returns:
        Maximum context window size in tokens
    """
    # 1. Direct match in hardcoded database
    if model_id in MODEL_CONTEXT_WINDOWS:
        logger.debug("Using hardcoded context window", {
            "model_id": model_id,
            "context_length": MODEL_CONTEXT_WINDOWS[model_id],
            "source": "hardcoded_db"
        })
        return MODEL_CONTEXT_WINDOWS[model_id]
    
    # 2. Try to fetch from OpenRouter API FIRST (before heuristics!)
    # This ensures we get the REAL value from OpenRouter if available
    if model_id not in _openrouter_model_cache:
        context_length = _fetch_context_window_from_openrouter(model_id)
        if context_length and context_length > 0:
            _openrouter_model_cache[model_id] = context_length
            logger.info("Fetched context window from OpenRouter", {
                "model_id": model_id,
                "context_length": context_length,
                "source": "openrouter_api"
            })
            return context_length
    
    # 3. Use cached value from OpenRouter if available
    if model_id in _openrouter_model_cache:
        logger.debug("Using cached context window from OpenRouter", {
            "model_id": model_id,
            "context_length": _openrouter_model_cache[model_id],
            "source": "openrouter_cache"
        })
        return _openrouter_model_cache[model_id]
    
    # 4. Heuristic matching (fallback if API not available)
    model_lower = model_id.lower()
    
    # Check for common patterns
    if "o1" in model_lower:
        logger.debug("Using heuristic for o1 model", {
            "model_id": model_id,
            "context_length": 200000,
            "source": "heuristic"
        })
        return 200000  # o1 models have huge context
    if "claude" in model_lower or "opus" in model_lower:
        logger.debug("Using heuristic for Claude model", {
            "model_id": model_id,
            "context_length": 200000,
            "source": "heuristic"
        })
        return 200000  # Claude models have 200k
    if "gpt-4" in model_lower and "turbo" in model_lower:
        logger.debug("Using heuristic for GPT-4 Turbo", {
            "model_id": model_id,
            "context_length": 128000,
            "source": "heuristic"
        })
        return 128000  # GPT-4 Turbo
    if "gpt-4" in model_lower:
        logger.debug("Using heuristic for GPT-4", {
            "model_id": model_id,
            "context_length": 8192,
            "source": "heuristic"
        })
        return 8192  # GPT-4 base
    if "kimi" in model_lower or "k2" in model_lower:
        logger.debug("Using heuristic for Kimi model", {
            "model_id": model_id,
            "context_length": 200000,
            "source": "heuristic"
        })
        return 200000  # Kimi K2
    if "deepseek" in model_lower:
        logger.debug("Using heuristic for DeepSeek model", {
            "model_id": model_id,
            "context_length": 64000,
            "source": "heuristic"
        })
        return 64000  # DeepSeek R1
    if "qwen" in model_lower:
        logger.debug("Using heuristic for Qwen model", {
            "model_id": model_id,
            "context_length": 128000,
            "source": "heuristic"
        })
        return 128000  # Qwen models
    if "llama" in model_lower:
        logger.debug("Using heuristic for Llama model", {
            "model_id": model_id,
            "context_length": 128000,
            "source": "heuristic"
        })
        return 128000  # Llama models
    if "mistral" in model_lower:
        logger.debug("Using heuristic for Mistral model", {
            "model_id": model_id,
            "context_length": 128000,
            "source": "heuristic"
        })
        return 128000  # Mistral models
    
    # 5. Fallback to default
    logger.warning("Unknown model context window, using default", {
        "model_id": model_id,
        "default_context": DEFAULT_MAX_CONTEXT,
        "source": "fallback"
    })
    return DEFAULT_MAX_CONTEXT


def _fetch_context_window_from_openrouter(model_id: str) -> Optional[int]:
    """
    Fetch context window size from OpenRouter API for unknown models.
    
    Args:
        model_id: Model identifier
        
    Returns:
        Context window size in tokens, or None if not found/error
    """
    try:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.debug("OpenRouter API key not configured, skipping lookup", {
                "model_id": model_id,
                "action": "fetch_context_window"
            })
            return None
        
        # Fetch from OpenRouter API
        logger.debug("Fetching context window from OpenRouter", {
            "model_id": model_id,
            "action": "api_request"
        })
        
        response = requests.get(
            'https://openrouter.ai/api/v1/models',
            headers={
                'Authorization': f'Bearer {api_key}',
                'HTTP-Referer': 'https://substrate-ai.local',
                'X-Title': 'Substrate AI'
            },
            timeout=5  # Quick timeout for lookups
        )
        
        if response.status_code != 200:
            logger.debug("OpenRouter API error", {
                "model_id": model_id,
                "status_code": response.status_code,
                "action": "fetch_context_window"
            })
            return None
        
        data = response.json()
        models = data.get('data', [])
        
        # Find matching model
        for model in models:
            if model.get('id') == model_id:
                context_length = model.get('context_length', 0)
                if context_length and context_length > 0:
                    logger.debug("Found model in OpenRouter", {
                        "model_id": model_id,
                        "context_length": context_length
                    })
                    return context_length
        
        logger.debug("Model not found in OpenRouter models list", {
            "model_id": model_id,
            "action": "fetch_context_window"
        })
        return None
        
    except requests.exceptions.Timeout:
        logger.debug("OpenRouter API timeout", {
            "model_id": model_id,
            "action": "fetch_context_window",
            "error_type": "Timeout"
        })
        return None
    except Exception as e:
        import traceback
        logger.debug("Error fetching context window from OpenRouter", {
            "model_id": model_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "stack_trace": traceback.format_exc(),
            "action": "fetch_context_window"
        })
        return None


def ensure_max_context_in_config(state_manager, model_id: str) -> int:
    """
    Ensure the config has the MAXIMUM context window for this model.
    
    Updates the config if it's lower than the model's maximum.
    
    Args:
        state_manager: StateManager instance
        model_id: Model identifier
        
    Returns:
        Maximum context window size (now in config)
    """
    max_context = get_max_context_window(model_id)
    
    # Get current config
    agent_state = state_manager.get_agent_state()
    config = agent_state.get('config', {})
    current_context = config.get('context_window', DEFAULT_MAX_CONTEXT)
    
    # If current is lower than max, update it!
    if current_context < max_context:
        print(f"📊 Updating context window: {current_context:,} → {max_context:,} (model maximum)")
        config['context_window'] = max_context
        state_manager.update_agent_state({'config': config})
    else:
        print(f"📊 Context window OK: {current_context:,} (model max: {max_context:,})")
    
    return max_context

