#!/usr/bin/env python3
"""
Generic LLM Provider Interface
===============================

Abstract interface for different LLM API providers.
Allows Substrate to work with ANY LLM API, not just OpenRouter.

Supported providers:
- OpenRouter (current)
- OpenAI (direct)
- Anthropic (Claude)
- Custom providers (via adapter)

Each provider implements the same interface, making them interchangeable.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM provider types"""
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


@dataclass
class LLMResponse:
    """Normalized LLM response structure"""
    content: str
    reasoning: Optional[str] = None
    tool_calls: List[Dict] = None
    usage: Optional[Dict] = None
    model: Optional[str] = None
    raw_response: Optional[Dict] = None  # Original API response
    
    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers must implement this interface to work with Substrate.
    """
    
    def __init__(self, api_key: str, default_model: str, **kwargs):
        """
        Initialize provider.
        
        Args:
            api_key: API key for the provider
            default_model: Default model identifier
            **kwargs: Provider-specific configuration
        """
        self.api_key = api_key
        self.default_model = default_model
        self.provider_type = self._get_provider_type()
        logger.info(f"Initialized {self.provider_type} provider with model: {default_model}")
    
    @abstractmethod
    def _get_provider_type(self) -> ProviderType:
        """Return provider type"""
        pass
    
    @abstractmethod
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
        Send chat completion request.
        
        Args:
            messages: List of message dicts
            model: Model identifier
            tools: Tool definitions
            tool_choice: Tool choice strategy
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            stream: Whether to stream
            **kwargs: Additional parameters
            
        Returns:
            Raw API response dict
        """
        pass
    
    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat completion.
        
        Yields:
            Response chunks
        """
        pass
    
    def normalize_response(
        self,
        response: Dict[str, Any],
        model: Optional[str] = None
    ) -> LLMResponse:
        """
        Normalize provider response to standard format.
        
        This is where provider-specific response formats are converted
        to the standard LLMResponse structure.
        
        Args:
            response: Raw API response
            model: Model identifier
            
        Returns:
            Normalized LLMResponse
        """
        from core.reasoning_extractor import extract_reasoning
        
        # Extract content
        content = self._extract_content(response)
        
        # Extract reasoning (provider-agnostic!)
        reasoning, clean_content = extract_reasoning(response, model, content)
        
        # Extract tool calls
        tool_calls = self._extract_tool_calls(response)
        
        # Extract usage
        usage = self._extract_usage(response)
        
        return LLMResponse(
            content=clean_content or content,
            reasoning=reasoning,
            tool_calls=tool_calls,
            usage=usage,
            model=model or self.default_model,
            raw_response=response
        )
    
    def _extract_content(self, response: Dict) -> str:
        """Extract content from response (provider-specific)"""
        # Default: OpenAI/OpenRouter format
        if 'choices' in response and len(response['choices']) > 0:
            message = response['choices'][0].get('message', {})
            return message.get('content', '').strip()
        
        # Anthropic format
        if 'content' in response:
            # Anthropic returns list of content blocks
            content_blocks = response['content']
            if isinstance(content_blocks, list):
                text_blocks = [
                    block.get('text', '') 
                    for block in content_blocks 
                    if block.get('type') == 'text'
                ]
                return ' '.join(text_blocks).strip()
            elif isinstance(content_blocks, str):
                return content_blocks.strip()
        
        return ''
    
    def _extract_tool_calls(self, response: Dict) -> List[Dict]:
        """Extract tool calls from response (provider-specific)"""
        tool_calls = []
        
        # OpenAI/OpenRouter format
        if 'choices' in response and len(response['choices']) > 0:
            message = response['choices'][0].get('message', {})
            raw_calls = message.get('tool_calls', [])
            
            for call in raw_calls:
                tool_calls.append({
                    'id': call.get('id'),
                    'name': call.get('function', {}).get('name'),
                    'arguments': call.get('function', {}).get('arguments')
                })
        
        # Anthropic format (tool_use blocks)
        elif 'content' in response:
            content_blocks = response['content']
            if isinstance(content_blocks, list):
                for block in content_blocks:
                    if block.get('type') == 'tool_use':
                        tool_calls.append({
                            'id': block.get('id'),
                            'name': block.get('name'),
                            'arguments': block.get('input', {})
                        })
        
        return tool_calls
    
    def _extract_usage(self, response: Dict) -> Optional[Dict]:
        """Extract token usage from response"""
        if 'usage' in response:
            return response['usage']
        
        # Some providers use different keys
        if 'input_tokens' in response or 'output_tokens' in response:
            return {
                'prompt_tokens': response.get('input_tokens', 0),
                'completion_tokens': response.get('output_tokens', 0),
                'total_tokens': response.get('input_tokens', 0) + response.get('output_tokens', 0)
            }
        
        return None


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider (wraps existing OpenRouterClient)"""
    
    def __init__(self, api_key: str, default_model: str, **kwargs):
        super().__init__(api_key, default_model, **kwargs)
        from core.openrouter_client import OpenRouterClient
        self.client = OpenRouterClient(
            api_key=api_key,
            default_model=default_model,
            **kwargs
        )
    
    def _get_provider_type(self) -> ProviderType:
        return ProviderType.OPENROUTER
    
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
        return await self.client.chat_completion(
            messages=messages,
            model=model,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs
        )
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        async for chunk in self.client.chat_completion_stream(
            messages=messages,
            model=model,
            tools=tools,
            **kwargs
        ):
            yield chunk


def create_provider(
    provider_type: str,
    api_key: str,
    default_model: str,
    **kwargs
) -> LLMProvider:
    """
    Factory function to create provider instances.
    
    Args:
        provider_type: 'openrouter', 'openai', 'anthropic', etc.
        api_key: API key
        default_model: Default model
        **kwargs: Provider-specific config
        
    Returns:
        LLMProvider instance
    """
    provider_type_lower = provider_type.lower()
    
    if provider_type_lower == 'openrouter':
        return OpenRouterProvider(api_key, default_model, **kwargs)
    
    elif provider_type_lower == 'openai':
        # TODO: Implement OpenAIProvider
        raise NotImplementedError("OpenAI provider not yet implemented")
    
    elif provider_type_lower == 'anthropic':
        # TODO: Implement AnthropicProvider
        raise NotImplementedError("Anthropic provider not yet implemented")
    
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


if __name__ == "__main__":
    # Test
    import asyncio
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    async def test():
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("❌ No API key found")
            return
        
        provider = create_provider(
            "openrouter",
            api_key,
            "openrouter/polaris-alpha"
        )
        
        response = await provider.chat_completion(
            messages=[{"role": "user", "content": "Say hello!"}],
            max_tokens=50
        )
        
        normalized = provider.normalize_response(response)
        print(f"Content: {normalized.content}")
        print(f"Reasoning: {normalized.reasoning}")
        print(f"Tool calls: {len(normalized.tool_calls)}")
    
    asyncio.run(test())

