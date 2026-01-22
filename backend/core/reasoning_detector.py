#!/usr/bin/env python3
"""
Universal Reasoning Model Detector
==================================

Automatically detects reasoning/thinking models regardless of API provider.

Uses multiple strategies:
1. Model name patterns (thinking, reasoning, o1, r1, etc.)
2. Response structure analysis (checks for reasoning fields)
3. Content pattern analysis (embedded thinking detection)
4. Configurable model registry

Works with ANY LLM API, not just OpenRouter!
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ReasoningFormat(str, Enum):
    """Different formats reasoning can come in"""
    SEPARATE_FIELD = "separate_field"  # reasoning_content, reasoning, etc.
    EMBEDDED_CONTENT = "embedded_content"  # Thinking in content, then answer
    TAGGED_CONTENT = "tagged_content"  # <think> tags
    STREAMING_CHUNKS = "streaming_chunks"  # Separate reasoning chunks in stream
    UNKNOWN = "unknown"


class ReasoningDetector:
    """
    Universal reasoning model detector.
    
    Detects reasoning models through:
    - Model name patterns
    - Response structure analysis
    - Content pattern analysis
    - Configurable registry
    """
    
    # Model name patterns that indicate reasoning capability
    REASONING_PATTERNS = [
        r'thinking',           # Any model with "thinking" in name
        r'reasoning',          # Any model with "reasoning" in name
        r'/o1',                # OpenAI o1 series
        r'/r1',                # DeepSeek R1 series
        r'/qwq',               # Qwen QWQ series
        r'k2-thinking',        # Kimi K2 thinking
        r'gemini.*thinking',   # Google Gemini thinking
        r'polaris',            # Some reasoning models use this
    ]
    
    # Known reasoning models (can be extended via config)
    KNOWN_REASONING_MODELS: Set[str] = {
        # OpenAI
        'openai/o1',
        'openai/o1-preview',
        'openai/o1-mini',
        
        # DeepSeek
        'deepseek/deepseek-r1',
        'deepseek/deepseek-reasoner',
        'deepseek/deepseek-r1-distill-qwen-32b',
        'deepseek/deepseek-r1-distill-llama-70b',
        
        # Qwen
        'qwen/qwq-32b-preview',
        'qwen/qwen3-vl-235b-a22b-thinking',
        'qwen/qwen3-vl-30b-a3b-thinking',
        
        # Moonshot
        'moonshotai/kimi-k2-thinking',
        'moonshotai/moonshot-v1-thinking',
        
        # Google
        'google/gemini-2.0-flash-thinking-exp',
        'google/gemini-2.0-flash-thinking-exp:free',
    }
    
    def __init__(self, custom_models: Optional[List[str]] = None):
        """
        Initialize detector.
        
        Args:
            custom_models: Additional model names to treat as reasoning models
        """
        self.custom_models = set(custom_models or [])
        logger.info(f"ReasoningDetector initialized with {len(self.custom_models)} custom models")
    
    def is_reasoning_model(self, model_name: str) -> bool:
        """
        Check if a model has reasoning capabilities.
        
        Uses multiple detection strategies:
        1. Exact match in known models
        2. Pattern matching on model name
        3. Custom model registry
        
        Args:
            model_name: Model identifier (e.g., "openai/o1", "anthropic/claude-3.5-sonnet")
            
        Returns:
            True if model likely has reasoning capabilities
        """
        if not model_name:
            return False
        
        model_lower = model_name.lower()
        
        # 1. Check known models (exact match)
        if model_lower in self.KNOWN_REASONING_MODELS:
            logger.debug(f"Model {model_name} matched known reasoning model")
            return True
        
        # 2. Check custom models
        if model_lower in self.custom_models:
            logger.debug(f"Model {model_name} matched custom reasoning model")
            return True
        
        # 3. Pattern matching
        for pattern in self.REASONING_PATTERNS:
            if re.search(pattern, model_lower):
                logger.debug(f"Model {model_name} matched reasoning pattern: {pattern}")
                return True
        
        return False
    
    def detect_reasoning_format(
        self, 
        response: Dict, 
        model_name: Optional[str] = None
    ) -> Tuple[ReasoningFormat, Optional[str]]:
        """
        Detect reasoning format from response structure.
        
        Analyzes the response to determine:
        - How reasoning is structured
        - Where to find reasoning content
        
        Args:
            response: LLM API response dict
            model_name: Optional model name for format hints
            
        Returns:
            Tuple of (format_type, field_name)
            field_name is the key where reasoning can be found (if applicable)
        """
        if not response:
            return ReasoningFormat.UNKNOWN, None
        
        # Check for separate reasoning fields
        reasoning_fields = [
            'reasoning',
            'reasoning_content',
            'thinking',
            'thinking_content',
            'internal_reasoning',
        ]
        
        # Check in choices[0].message
        if 'choices' in response and len(response['choices']) > 0:
            message = response['choices'][0].get('message', {})
            
            for field in reasoning_fields:
                if field in message:
                    value = message[field]
                    if value and str(value).strip() and str(value).lower() != 'null':
                        logger.debug(f"Found reasoning in field: {field}")
                        return ReasoningFormat.SEPARATE_FIELD, field
            
            # Check for reasoning in delta (streaming)
            if 'delta' in response['choices'][0]:
                delta = response['choices'][0]['delta']
                for field in reasoning_fields:
                    if field in delta:
                        logger.debug(f"Found reasoning in delta field: {field}")
                        return ReasoningFormat.STREAMING_CHUNKS, field
        
        # Check at top level
        for field in reasoning_fields:
            if field in response:
                value = response[field]
                if value and str(value).strip() and str(value).lower() != 'null':
                    logger.debug(f"Found reasoning in top-level field: {field}")
                    return ReasoningFormat.SEPARATE_FIELD, field
        
        # Check for embedded thinking in content
        if 'choices' in response and len(response['choices']) > 0:
            message = response['choices'][0].get('message', {})
            content = message.get('content', '')
            
            if content and self._has_embedded_thinking(content):
                logger.debug("Detected embedded thinking in content")
                return ReasoningFormat.EMBEDDED_CONTENT, 'content'
        
        # Check for tagged thinking
        if 'choices' in response and len(response['choices']) > 0:
            message = response['choices'][0].get('message', {})
            content = message.get('content', '')
            
            if content and self._has_tagged_thinking(content):
                logger.debug("Detected tagged thinking in content")
                return ReasoningFormat.TAGGED_CONTENT, 'content'
        
        return ReasoningFormat.UNKNOWN, None
    
    def _has_embedded_thinking(self, content: str) -> bool:
        """
        Check if content has embedded thinking (Qwen-style).
        
        Pattern: Long thinking paragraph, then short answer.
        """
        if not content or len(content) < 100:
            return False
        
        paragraphs = content.split('\n\n')
        if len(paragraphs) < 2:
            return False
        
        # Check if first paragraph is much longer than others
        first_len = len(paragraphs[0])
        rest_len = sum(len(p) for p in paragraphs[1:])
        
        # If first paragraph is >70% of total, likely all thinking
        if first_len > (first_len + rest_len) * 0.7:
            return True
        
        # Check for thinking indicators in first paragraph
        thinking_indicators = [
            r'^i (need to|should|will|must|can)',
            r'^the user',
            r'^let me',
            r'^first,',
            r'^to answer',
            r'^i\'m (thinking|considering|analyzing)',
        ]
        
        first_para_lower = paragraphs[0].lower().strip()
        for pattern in thinking_indicators:
            if re.search(pattern, first_para_lower):
                return True
        
        return False
    
    def _has_tagged_thinking(self, content: str) -> bool:
        """Check if content has <think> tags"""
        if not content:
            return False
        
        pattern = r'<think>.*?</think>'
        return bool(re.search(pattern, content, re.DOTALL | re.IGNORECASE))
    
    def add_custom_model(self, model_name: str):
        """Add a custom model to the reasoning registry"""
        self.custom_models.add(model_name.lower())
        logger.info(f"Added custom reasoning model: {model_name}")
    
    def get_detection_info(self, model_name: str) -> Dict:
        """
        Get detection information for a model.
        
        Returns:
            Dict with detection details
        """
        is_reasoning = self.is_reasoning_model(model_name)
        
        info = {
            'model_name': model_name,
            'is_reasoning_model': is_reasoning,
            'detection_method': None,
            'matched_pattern': None,
        }
        
        if is_reasoning:
            model_lower = model_name.lower()
            
            # Check which method matched
            if model_lower in self.KNOWN_REASONING_MODELS:
                info['detection_method'] = 'known_registry'
            elif model_lower in self.custom_models:
                info['detection_method'] = 'custom_registry'
            else:
                # Find which pattern matched
                for pattern in self.REASONING_PATTERNS:
                    if re.search(pattern, model_lower):
                        info['detection_method'] = 'pattern_match'
                        info['matched_pattern'] = pattern
                        break
        
        return info


# Global instance (can be configured)
_detector = ReasoningDetector()


def is_reasoning_model(model_name: str) -> bool:
    """Quick check if model has reasoning capabilities"""
    return _detector.is_reasoning_model(model_name)


def detect_reasoning_format(response: Dict, model_name: Optional[str] = None) -> Tuple[ReasoningFormat, Optional[str]]:
    """Quick detection of reasoning format"""
    return _detector.detect_reasoning_format(response, model_name)


def add_custom_reasoning_model(model_name: str):
    """Add custom reasoning model to global registry"""
    _detector.add_custom_model(model_name)


if __name__ == "__main__":
    # Test
    detector = ReasoningDetector()
    
    test_models = [
        "openai/o1-preview",
        "deepseek/deepseek-r1",
        "qwen/qwq-32b-preview",
        "moonshotai/kimi-k2-thinking",
        "openai/gpt-4",
        "anthropic/claude-3.5-sonnet",
        "custom-provider/reasoning-model-v2",
    ]
    
    print("🧠 Reasoning Model Detection Test")
    print("=" * 60)
    
    for model in test_models:
        is_reasoning = detector.is_reasoning_model(model)
        info = detector.get_detection_info(model)
        print(f"\n{model}:")
        print(f"  Reasoning: {'✅ YES' if is_reasoning else '❌ NO'}")
        if info['detection_method']:
            print(f"  Method: {info['detection_method']}")
            if info['matched_pattern']:
                print(f"  Pattern: {info['matched_pattern']}")

