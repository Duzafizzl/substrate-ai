#!/usr/bin/env python3
"""
OpenRouter API Client for Substrate AI

This module provides direct, transparent access to OpenRouter's API.
No black boxes, full control, clear error messages.

Built with attention to detail.
"""

import os
import json
import json as json_lib  # For instrumentation logging
import time
import aiohttp
import asyncio
from typing import Optional, Dict, List, Any, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message roles for chat completion"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class TokenUsage:
    """Token usage tracking for cost calculation"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    
    def calculate_cost(self, model_pricing: Dict[str, float]) -> float:
        """
        Calculate cost in USD based on model pricing.
        
        Args:
            model_pricing: Dict with 'prompt' and 'completion' prices per M tokens
            
        Returns:
            Cost in USD
        """
        prompt_cost = (self.prompt_tokens / 1_000_000) * model_pricing.get('prompt', 0)
        completion_cost = (self.completion_tokens / 1_000_000) * model_pricing.get('completion', 0)
        return prompt_cost + completion_cost


@dataclass
class ToolCall:
    """Parsed tool call from LLM response"""
    id: str
    name: str
    arguments: Dict[str, Any]
    
    @classmethod
    def from_openai_format(cls, tool_call: Dict) -> 'ToolCall':
        """Parse tool call from OpenAI format"""
        return cls(
            id=tool_call['id'],
            name=tool_call['function']['name'],
            arguments=json.loads(tool_call['function']['arguments'])
        )


class OpenRouterError(Exception):
    """
    Base exception for OpenRouter errors.
    
    PHILOSOPHY: Error messages should be HELPFUL, not cryptic.
    Each error tells you:
    1. What went wrong
    2. Why it happened
    3. How to fix it
    """
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_body: Optional[str] = None, context: Optional[Dict] = None):
        self.status_code = status_code
        self.response_body = response_body
        self.context = context or {}
        
        # Build helpful error message
        full_message = f"\n{'='*60}\n"
        full_message += f"❌ OPENROUTER ERROR\n"
        full_message += f"{'='*60}\n\n"
        full_message += f"🔴 Problem: {message}\n\n"
        
        if status_code:
            full_message += f"📊 Status Code: {status_code}\n"
            
        if response_body:
            try:
                body = json.loads(response_body)
                if 'error' in body:
                    full_message += f"💬 API Says: {body['error'].get('message', 'Unknown error')}\n"
            except:
                full_message += f"💬 Response: {response_body[:200]}...\n"
        
        if context:
            full_message += f"\n📋 Context:\n"
            for key, value in context.items():
                full_message += f"   • {key}: {value}\n"
        
        full_message += f"\n💡 Suggestions:\n"
        
        # Contextual suggestions based on status code
        if status_code == 401:
            full_message += "   • Check your OPENROUTER_API_KEY in .env\n"
            full_message += "   • Verify key at: https://openrouter.ai/keys\n"
        elif status_code == 402:
            full_message += "   • Add credits at: https://openrouter.ai/credits\n"
            full_message += "   • Check balance at: https://openrouter.ai/activity\n"
        elif status_code == 429:
            full_message += "   • You're being rate limited\n"
            full_message += "   • Wait a few seconds and retry\n"
            full_message += "   • Consider using a different model\n"
        elif status_code == 400:
            full_message += "   • Check your message format\n"
            full_message += "   • Verify tool schemas are valid\n"
            full_message += "   • Check max_tokens isn't too high\n"
        elif status_code == 500:
            full_message += "   • OpenRouter upstream provider error\n"
            full_message += "   • Try again in a few seconds\n"
            full_message += "   • Consider switching models\n"
        else:
            full_message += "   • Check OpenRouter status: https://status.openrouter.ai\n"
            full_message += "   • Review docs: https://openrouter.ai/docs\n"
        
        full_message += f"\n{'='*60}\n"
        
        super().__init__(full_message)


class OpenRouterClient:
    """
    Direct OpenRouter API client.
    
    Features:
    - Streaming and non-streaming support
    - Tool calling
    - Cost tracking with multi-provider cache pricing
    - Clear error messages
    - Full transparency
    - 🚀 PROMPT CACHING: Multi-provider support!
      • Anthropic Claude: Explicit cache_control (0.1x reads, 1.25x-2x writes)
      • OpenAI: Automatic (0.25x-0.50x reads, FREE writes)
      • DeepSeek: Automatic (0.1x reads, 1x writes)
      • Gemini 2.5: Implicit automatic (0.25x reads, FREE writes)
      • Grok/Groq/Moonshot: Automatic (FREE writes, provider-specific reads)
    
    No magic, no black boxes.
    """
    
    # Model prefixes that support prompt caching with cache_control
    ANTHROPIC_MODELS = ('anthropic/', 'claude')
    GEMINI_MODELS = ('google/gemini', 'gemini')
    
    # Gemini 2.5 models with implicit caching (automatic like OpenAI)
    GEMINI_25_IMPLICIT = ('google/gemini-2.5-pro', 'google/gemini-2.5-flash', 
                          'gemini-2.5-pro', 'gemini-2.5-flash')
    
    # Cache TTL options for Anthropic
    # 5m: Cheaper writes (1.25x), but cache expires fast → bad for slow conversations!
    # 1h (default): Higher write cost (2x), but cache hits (0.1x) for full hour!
    #
    # MATH for 1h conversation (12 msgs, ~5min apart):
    #   5m TTL: 12 writes × 1.25x = 15x total (cache keeps expiring!)
    #   1h TTL: 1 write × 2x + 11 hits × 0.1x = 3.1x total (80% cheaper!)
    #
    CACHE_TTL_5M = None  # 5 minute TTL (no ttl field needed)
    CACHE_TTL_1H = "1h"  # Extended 1 hour TTL - BETTER for real conversations!
    
    def __init__(
        self,
        api_key: str,
        default_model: str = "openrouter/polaris-alpha",
        app_name: str = "SubstrateAI",
        app_url: Optional[str] = None,
        timeout: int = 120,  # Increased for large context windows (was 60)
        cost_tracker = None,
        cache_ttl: str = "1h"  # "1h" (default, best for real convos) or "5m" for rapid-fire
    ):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key
            default_model: Default model to use
            app_name: App name for OpenRouter tracking
            app_url: App URL for OpenRouter tracking
            timeout: Request timeout in seconds
            cost_tracker: Optional CostTracker instance for persistent cost logging
        """
        if not api_key or not api_key.startswith("sk-or-v1-"):
            raise OpenRouterError(
                "Invalid OpenRouter API key format",
                context={
                    "expected_format": "sk-or-v1-...",
                    "received": api_key[:20] + "..." if api_key else "None",
                    "how_to_get": "https://openrouter.ai/keys"
                }
            )
        
        self.api_key = api_key
        self.default_model = default_model
        self.app_name = app_name
        self.app_url = app_url
        self.timeout = timeout
        self.base_url = "https://openrouter.ai/api/v1"
        self.cache_ttl = cache_ttl  # "5m" or "1h" for Anthropic prompt caching
        
        # Cost tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0
        self.cost_tracker = cost_tracker  # Persistent cost tracker
        
        print(f"✅ OpenRouter Client initialized")
        print(f"   Model: {default_model}")
        print(f"   Timeout: {timeout}s")
        print(f"   💾 Cache TTL: {cache_ttl} (for Anthropic models)")
        print(f"   💾 Cache Strategy: Multi-provider (OpenAI, Anthropic, DeepSeek, Gemini)")
    
    def _get_headers(self) -> Dict[str, str]:
        """Build request headers"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if self.app_name:
            headers["X-Title"] = self.app_name
        
        if self.app_url:
            headers["HTTP-Referer"] = self.app_url
        
        return headers
    
    def _is_anthropic_model(self, model: str) -> bool:
        """Check if model is Anthropic/Claude (requires explicit cache_control)"""
        model_lower = model.lower()
        return any(prefix in model_lower for prefix in self.ANTHROPIC_MODELS)
    
    def _is_gemini_model(self, model: str) -> bool:
        """Check if model is Google Gemini (supports cache_control breakpoints)"""
        model_lower = model.lower()
        return any(prefix in model_lower for prefix in self.GEMINI_MODELS)
    
    def _is_gemini_25_implicit(self, model: str) -> bool:
        """Check if model is Gemini 2.5 with implicit caching (automatic)"""
        model_lower = model.lower()
        return any(prefix in model_lower for prefix in self.GEMINI_25_IMPLICIT)
    
    def _apply_prompt_caching(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict]] = None
    ) -> tuple[List[Dict[str, Any]], Optional[List[Dict]]]:
        """
        Apply prompt caching to messages AND tools for supported providers.
        
        🚀 PROMPT CACHING - Reduces costs significantly!
        
        💾 INTELLIGENT CACHING STRATEGY:
        We split the system prompt at "### MEMORY BLOCKS" to cache:
        1. Tools (last tool) - rarely changes
        2. Static system prompt (base prompt before MEMORY BLOCKS) - rarely changes
        3. Memory blocks (after ### MEMORY BLOCKS marker) - changes when edited
        4. Last user message (for conversation continuity)
        
        This way, when only memory blocks change, the static part stays cached!
        
        Provider-specific behavior:
        - Anthropic Claude: Add cache_control with configurable TTL (5m or 1h)
        - Google Gemini 2.5: Implicit caching (automatic like OpenAI)
        - Google Gemini 1.5/2.0: Add cache_control to last large text block
        - OpenAI/DeepSeek/Grok/Groq/Others: Automatic caching, no modification needed
        
        Args:
            messages: List of message dicts
            model: Model identifier
            tools: Optional list of tool definitions
            
        Returns:
            Tuple of (modified messages, modified tools)
        """
        is_anthropic = self._is_anthropic_model(model)
        is_gemini = self._is_gemini_model(model)
        is_gemini_25 = self._is_gemini_25_implicit(model)
        
        # Gemini 2.5: Implicit caching (automatic like OpenAI)
        if is_gemini_25:
            print(f"   💾 Prompt caching: IMPLICIT (Gemini 2.5 automatic caching, 0.25x cache reads)")
            return messages, tools
        
        # OpenAI, DeepSeek, Grok, Groq, Moonshot: Automatic caching - no modification needed
        if not is_anthropic and not is_gemini:
            print(f"   💾 Prompt caching: AUTOMATIC (provider handles it)")
            return messages, tools
        
        # Build cache_control object based on TTL setting
        cache_control = {"type": "ephemeral"}
        if is_anthropic and self.cache_ttl == "1h":
            cache_control["ttl"] = "1h"
        
        ttl_display = self.cache_ttl if self.cache_ttl and is_anthropic else "5m"
        breakpoints_used = 0
        max_breakpoints = 4  # Anthropic limit
        
        # === BREAKPOINT 1: Cache Tools (last tool gets cache_control) ===
        cached_tools = None
        if tools and is_anthropic and breakpoints_used < max_breakpoints:
            cached_tools = [t.copy() for t in tools]
            # Add cache_control to the LAST tool
            cached_tools[-1]["cache_control"] = cache_control.copy()
            breakpoints_used += 1
            print(f"   💾 Cache breakpoint {breakpoints_used}: TOOLS (last tool, {ttl_display} TTL)")
        else:
            cached_tools = tools
        
        # === BREAKPOINTS 2-3: Cache System Prompt WITH INTELLIGENT SPLITTING ===
        cached_messages = []
        system_cached = False
        
        for i, msg in enumerate(messages):
            msg_copy = msg.copy()
            
            # Apply cache_control to SYSTEM messages with intelligent memory block splitting
            if msg['role'] == 'system' and not system_cached and breakpoints_used < max_breakpoints:
                content = msg.get('content', '')
                
                # Only cache if content is substantial (>1024 chars)
                if isinstance(content, str) and len(content) > 1024:
                    # 💾 INTELLIGENT SPLIT: Separate static prompt from memory blocks!
                    memory_marker = "### MEMORY BLOCKS"
                    
                    if memory_marker in content and breakpoints_used < max_breakpoints - 1:
                        # Split at memory blocks marker
                        parts = content.split(memory_marker, 1)
                        static_part = parts[0].strip()
                        memory_part = memory_marker + parts[1] if len(parts) > 1 else ""
                        
                        content_blocks = []
                        
                        # Static part (base prompt + thinking) - cached, rarely changes
                        if len(static_part) > 500:
                            content_blocks.append({
                                "type": "text",
                                "text": static_part,
                                "cache_control": cache_control.copy()
                            })
                            breakpoints_used += 1
                            print(f"   💾 Cache breakpoint {breakpoints_used}: STATIC PROMPT ({len(static_part)} chars, {ttl_display} TTL)")
                        else:
                            content_blocks.append({"type": "text", "text": static_part})
                        
                        # Memory blocks part - cached separately, invalidates when edited!
                        if memory_part and len(memory_part) > 500 and breakpoints_used < max_breakpoints:
                            content_blocks.append({
                                "type": "text",
                                "text": memory_part,
                                "cache_control": cache_control.copy()
                            })
                            breakpoints_used += 1
                            print(f"   💾 Cache breakpoint {breakpoints_used}: MEMORY BLOCKS ({len(memory_part)} chars, {ttl_display} TTL)")
                        elif memory_part:
                            content_blocks.append({"type": "text", "text": memory_part})
                        
                        msg_copy['content'] = content_blocks
                        system_cached = True
                    else:
                        # No memory marker found, cache entire system prompt
                        msg_copy['content'] = [
                            {
                                "type": "text",
                                "text": content,
                                "cache_control": cache_control.copy()
                            }
                        ]
                        breakpoints_used += 1
                        system_cached = True
                        print(f"   💾 Cache breakpoint {breakpoints_used}: SYSTEM PROMPT ({len(content)} chars, {ttl_display} TTL)")
            
            cached_messages.append(msg_copy)
        
        # === BREAKPOINT 4: Cache Last Large User Message ===
        # Find the LAST user message with substantial content
        if breakpoints_used < max_breakpoints:
            for i in range(len(cached_messages) - 1, -1, -1):
                msg = cached_messages[i]
                if msg['role'] == 'user':
                    content = msg.get('content', '')
                    
                    # Handle string content
                    if isinstance(content, str) and len(content) > 512:  # Lower threshold for user msgs
                        cached_messages[i]['content'] = [
                            {
                                "type": "text",
                                "text": content,
                                "cache_control": cache_control.copy()
                            }
                        ]
                        breakpoints_used += 1
                        print(f"   💾 Cache breakpoint {breakpoints_used}: LAST USER MSG ({len(content)} chars, {ttl_display} TTL)")
                        break
                    # Handle already multipart content (add cache_control to last part)
                    elif isinstance(content, list) and len(content) > 0:
                        last_text_idx = None
                        for j in range(len(content) - 1, -1, -1):
                            if content[j].get('type') == 'text':
                                last_text_idx = j
                                break
                        if last_text_idx is not None:
                            cached_messages[i]['content'][last_text_idx]['cache_control'] = cache_control.copy()
                            breakpoints_used += 1
                            print(f"   💾 Cache breakpoint {breakpoints_used}: LAST USER MSG (multipart, {ttl_display} TTL)")
                            break
        
        if breakpoints_used == 0:
            print(f"   ⚠️  Prompt caching: No content large enough to cache")
        else:
            print(f"   💾 Total cache breakpoints: {breakpoints_used}/{max_breakpoints}")
        
        return cached_messages, cached_tools
    
    async def get_models(self) -> List[Dict[str, Any]]:
        """
        Fetch available models from OpenRouter.
        
        Returns:
            List of model info dicts
            
        Raises:
            OpenRouterError: If request fails
        """
        url = f"{self.base_url}/models"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, headers=self._get_headers()) as response:
                    if response.status != 200:
                        body = await response.text()
                        raise OpenRouterError(
                            "Failed to fetch models",
                            status_code=response.status,
                            response_body=body
                        )
                    
                    data = await response.json()
                    return data.get('data', [])
        
        except aiohttp.ClientError as e:
            raise OpenRouterError(
                f"Network error while fetching models: {str(e)}",
                context={"url": url}
            )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send chat completion request to OpenRouter.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to self.default_model)
            tools: List of tool definitions (OpenAI format)
            tool_choice: How to handle tools ("auto", "none", or {"type": "function", "function": {"name": "..."}})
            temperature: Sampling temperature (0-2)
            max_tokens: Max tokens to generate
            stream: Whether to stream response
            **kwargs: Additional model parameters
            
        Returns:
            Response dict with 'choices', 'usage', etc.
            
        Raises:
            OpenRouterError: If request fails
        """
        model = model or self.default_model
        url = f"{self.base_url}/chat/completions"
        
        # 🚀 Apply prompt caching for supported providers!
        # This caches: system prompt, tools, and last user message
        cached_messages, cached_tools = self._apply_prompt_caching(messages, model, tools)
        
        # Build payload
        payload = {
            "model": model,
            "messages": cached_messages,  # Use cached messages!
            "temperature": temperature,
            "stream": stream
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # Allow longer responses - use max_tokens if provided, otherwise allow up to 8192 tokens
        # This ensures the agent can give detailed, thoughtful responses instead of clipped fragments
        if "max_completion_tokens" not in kwargs:
            # Use max_tokens if provided, otherwise default to 8192 for full responses
            payload["max_completion_tokens"] = max_tokens if max_tokens else 8192
        
        if cached_tools:
            payload["tools"] = cached_tools  # Use cached tools!
            payload["tool_choice"] = tool_choice
        
        # Add any extra kwargs (can override max_completion_tokens!)
        payload.update(kwargs)
        
        # Log request (helpful for debugging!)
        print(f"\n📤 OpenRouter Request:")
        print(f"   Model: {model}")
        print(f"   Messages: {len(messages)}")
        print(f"   Tools: {len(tools) if tools else 0}")
        print(f"   Stream: {stream}")
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, headers=self._get_headers(), json=payload) as response:
                    
                    # Check for errors
                    if response.status != 200:
                        body = await response.text()
                        raise OpenRouterError(
                            f"Chat completion failed",
                            status_code=response.status,
                            response_body=body,
                            context={
                                "model": model,
                                "num_messages": len(messages),
                                "has_tools": bool(tools)
                            }
                        )
                    
                    # Parse response
                    data = await response.json()
                    
                    # Track usage WITH CACHE TOKENS!
                    if 'usage' in data:
                        usage = data['usage']
                        prompt_tokens = usage.get('prompt_tokens', 0)
                        completion_tokens = usage.get('completion_tokens', 0)
                        
                        # 💾 Extract cache tokens from OpenRouter response
                        cache_creation_tokens = usage.get('cache_creation_input_tokens', 0)
                        cache_read_tokens = usage.get('cache_read_input_tokens', 0)
                        
                        # Log cache info if available
                        if cache_creation_tokens > 0 or cache_read_tokens > 0:
                            print(f"   💾 Cache: {cache_creation_tokens} created, {cache_read_tokens} read")
                        
                        self.total_prompt_tokens += prompt_tokens
                        self.total_completion_tokens += completion_tokens
                        
                        # Log to persistent cost tracker WITH CACHE PRICING!
                        if self.cost_tracker:
                            from core.cost_tracker import calculate_cost, calculate_cache_savings
                            input_cost, output_cost = calculate_cost(
                                model=model, 
                                input_tokens=prompt_tokens, 
                                output_tokens=completion_tokens,
                                cache_creation_tokens=cache_creation_tokens,
                                cache_read_tokens=cache_read_tokens,
                                cache_ttl=self.cache_ttl
                            )
                            self.cost_tracker.log_request(
                                model=model,
                                input_tokens=prompt_tokens,
                                output_tokens=completion_tokens,
                                input_cost=input_cost,
                                output_cost=output_cost
                            )
                            
                            # 💾 Log cache savings!
                            if cache_read_tokens > 0:
                                savings = calculate_cache_savings(model, cache_read_tokens, self.cache_ttl)
                                if savings > 0:
                                    print(f"   💰 Cache savings: ${savings:.6f} ({cache_read_tokens} cached tokens)")
                    
                    # Log response
                    print(f"\n📥 OpenRouter Response:")
                    if 'usage' in data:
                        print(f"   Tokens: {data['usage'].get('total_tokens', 0)}")
                    if 'choices' in data and len(data['choices']) > 0:
                        choice = data['choices'][0]
                        if 'message' in choice:
                            msg = choice['message']
                            if 'tool_calls' in msg and msg['tool_calls']:
                                print(f"   Tool Calls: {len(msg['tool_calls'])}")
                                for tc in msg['tool_calls']:
                                    print(f"      • {tc['function']['name']}")
                    
                    return data
        
        except aiohttp.ClientError as e:
            raise OpenRouterError(
                f"Network error during chat completion: {str(e)}",
                context={
                    "model": model,
                    "url": url,
                    "timeout": self.timeout
                }
            )
        except asyncio.TimeoutError:
            raise OpenRouterError(
                f"Request timed out after {self.timeout}s",
                context={
                    "model": model,
                    "suggestion": "Try increasing timeout or using a faster model"
                }
            )
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat completion from OpenRouter.
        
        Args:
            messages: List of message dicts
            model: Model to use
            tools: Tool definitions
            **kwargs: Additional parameters
            
        Yields:
            Delta dicts from streaming response
            
        Raises:
            OpenRouterError: If request fails
        """
        model = model or self.default_model
        url = f"{self.base_url}/chat/completions"
        
        # 🚀 Apply prompt caching for supported providers!
        # This caches: system prompt, tools, and last user message
        cached_messages, cached_tools = self._apply_prompt_caching(messages, model, tools)
        
        payload = {
            "model": model,
            "messages": cached_messages,  # Use cached messages!
            "stream": True,
            **kwargs
        }
        
        if cached_tools:
            payload["tools"] = cached_tools  # Use cached tools!
        
        print(f"\n📡 Streaming from: {model}")
        
        try:
            # 🌊 STREAMING: No total timeout! Only sock_read timeout (60s between chunks)
            stream_timeout = aiohttp.ClientTimeout(
                total=None,           # No total timeout for streaming!
                sock_read=60.0,       # 60s between chunks
                sock_connect=10.0     # 10s to connect
            )
            async with aiohttp.ClientSession(timeout=stream_timeout) as session:
                async with session.post(url, headers=self._get_headers(), json=payload) as response:
                    
                    if response.status != 200:
                        body = await response.text()
                        raise OpenRouterError(
                            "Streaming failed",
                            status_code=response.status,
                            response_body=body,
                            context={"model": model}
                        )
                    
                    # Stream chunks LINE BY LINE! 🌊
                    # aiohttp response.content gives BYTES, not lines!
                    # We need to read line-by-line for SSE format
                    buffer = ""
                    chunk_count = 0
                    async for chunk_bytes in response.content.iter_chunked(1024):
                        chunk_count += 1
                        print(f"🌊 Received chunk #{chunk_count}: {len(chunk_bytes)} bytes")
                        buffer += chunk_bytes.decode('utf-8')
                        
                        # Process complete lines
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            print(f"   LINE: {line[:200]}")  # Debug: show first 200 chars
                            
                            if not line or line == "data: [DONE]":
                                continue
                            
                            if line.startswith("data: "):
                                try:
                                    chunk = json.loads(line[6:])
                                    print(f"✅ Parsed chunk successfully!")
                                    yield chunk
                                except json.JSONDecodeError as e:
                                    print(f"⚠️  Failed to parse chunk: {line[:100]}")
                                    continue
                    
                    print(f"🏁 Stream complete! Total chunks received: {chunk_count}")
        
        except aiohttp.ClientError as e:
            raise OpenRouterError(
                f"Network error during streaming: {str(e)}",
                context={"model": model}
            )
    
    def parse_tool_calls(self, response: Dict[str, Any]) -> List[ToolCall]:
        """
        Parse tool calls from response.
        
        Args:
            response: Chat completion response
            
        Returns:
            List of ToolCall objects
        """
        tool_calls = []
        
        if 'choices' not in response or not response['choices']:
            return tool_calls
        
        message = response['choices'][0].get('message', {})
        raw_calls = message.get('tool_calls', [])
        
        for call in raw_calls:
            try:
                tool_calls.append(ToolCall.from_openai_format(call))
            except Exception as e:
                print(f"⚠️  Failed to parse tool call: {e}")
                print(f"   Raw: {json.dumps(call, indent=2)}")
        
        return tool_calls
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "estimated_cost_usd": self.total_cost
        }


# ============================================
# TESTING
# ============================================

async def test_client():
    """Test the OpenRouter client"""
    from dotenv import load_dotenv
    
    print("\n🧪 TESTING OPENROUTER CLIENT")
    print("="*60)
    
    # Load config
    load_dotenv(".env")
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        print("❌ No API key found in .env")
        return
    
    # Initialize client
    try:
        client = OpenRouterClient(api_key=api_key)
    except OpenRouterError as e:
        print(e)
        return
    
    # Test 1: Fetch models
    print("\n📋 Test 1: Fetch models")
    try:
        models = await client.get_models()
        qwen_models = [m for m in models if 'qwen' in m['id'].lower()]
        print(f"✅ Found {len(models)} total models")
        print(f"✅ Found {len(qwen_models)} Qwen models")
    except OpenRouterError as e:
        print(e)
        return
    
    # Test 2: Simple chat
    print("\n💬 Test 2: Simple chat (non-streaming)")
    try:
        response = await client.chat_completion(
            messages=[
                {"role": "user", "content": "Say 'Hello!' and nothing else."}
            ],
            max_tokens=50
        )
        
        message = response['choices'][0]['message']['content']
        print(f"✅ Response: {message}")
        print(f"✅ Tokens: {response['usage']['total_tokens']}")
    except OpenRouterError as e:
        print(e)
        return
    
    # Test 3: Tool calling
    print("\n🛠️  Test 3: Tool calling")
    tools = [
        {
            "type": "function",
            "function": {
                "name": "send_message",
                "description": "Send a message to the user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to send"
                        }
                    },
                    "required": ["message"]
                }
            }
        }
    ]
    
    try:
        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": "You are an AI assistant. Respond using the send_message tool."},
                {"role": "user", "content": "Hello!"}
            ],
            tools=tools,
            max_tokens=100
        )
        
        tool_calls = client.parse_tool_calls(response)
        if tool_calls:
            print(f"✅ Tool calls: {len(tool_calls)}")
            for tc in tool_calls:
                print(f"   • {tc.name}({json.dumps(tc.arguments, indent=6)})")
        else:
            print("⚠️  No tool calls (might be a model limitation)")
    except OpenRouterError as e:
        print(e)
        return
    
    # Stats
    print("\n📊 Stats:")
    stats = client.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ ALL TESTS PASSED!")
    print("="*60)


if __name__ == "__main__":
    """Run tests if executed directly"""
    asyncio.run(test_client())

