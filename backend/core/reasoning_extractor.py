#!/usr/bin/env python3
"""
Universal Reasoning Extractor
==============================

Extracts reasoning/thinking content from LLM responses regardless of:
- API provider (OpenRouter, OpenAI, Anthropic, etc.)
- Response format (separate field, embedded, tagged, streaming)
- Model type (o1, R1, Qwen, etc.)

Works with ANY LLM API response structure!
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from core.reasoning_detector import (
    ReasoningDetector,
    ReasoningFormat,
    detect_reasoning_format,
    is_reasoning_model
)

logger = logging.getLogger(__name__)


class ReasoningExtractor:
    """
    Universal reasoning extractor.
    
    Extracts reasoning from various response formats:
    - Separate fields (reasoning_content, reasoning, etc.)
    - Embedded in content (Qwen-style)
    - Tagged content (<think> tags)
    - Streaming chunks
    """
    
    def __init__(self, detector: Optional[ReasoningDetector] = None):
        """
        Initialize extractor.
        
        Args:
            detector: Optional ReasoningDetector instance (uses global if None)
        """
        self.detector = detector or ReasoningDetector()
        logger.info("ReasoningExtractor initialized")
    
    def extract(
        self,
        response: Dict[str, Any],
        model_name: Optional[str] = None,
        content: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract reasoning from response.
        
        Args:
            response: LLM API response dict
            model_name: Model identifier (for format hints)
            content: Optional pre-extracted content string
            
        Returns:
            Tuple of (reasoning_text, clean_content)
            - reasoning_text: Extracted reasoning (None if not found)
            - clean_content: Content with reasoning removed (original if no reasoning)
        """
        if not response:
            return None, content
        
        # Detect reasoning format
        format_type, field_name = self.detector.detect_reasoning_format(response, model_name)
        
        logger.debug(f"Detected reasoning format: {format_type}, field: {field_name}")
        
        # Extract based on format
        if format_type == ReasoningFormat.SEPARATE_FIELD:
            return self._extract_from_field(response, field_name, content)
        
        elif format_type == ReasoningFormat.EMBEDDED_CONTENT:
            return self._extract_embedded(response, content)
        
        elif format_type == ReasoningFormat.TAGGED_CONTENT:
            return self._extract_tagged(response, content)
        
        elif format_type == ReasoningFormat.STREAMING_CHUNKS:
            return self._extract_from_delta(response, field_name)
        
        else:
            # Unknown format - try heuristics
            return self._extract_heuristic(response, model_name, content)
    
    def _extract_from_field(
        self,
        response: Dict,
        field_name: str,
        content: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract reasoning from separate field (reasoning_content, reasoning, etc.)
        """
        reasoning_text = None
        
        # Check in choices[0].message
        if 'choices' in response and len(response['choices']) > 0:
            message = response['choices'][0].get('message', {})
            
            if field_name in message:
                field_value = message[field_name]
                
                # Handle different field value types
                if isinstance(field_value, str):
                    reasoning_text = field_value.strip()
                elif isinstance(field_value, dict):
                    # Some models use reasoning.content
                    reasoning_text = field_value.get('content', '').strip()
                elif field_value is not None:
                    reasoning_text = str(field_value).strip()
        
        # Check at top level (fallback)
        if not reasoning_text and field_name in response:
            field_value = response[field_name]
            if isinstance(field_value, str):
                reasoning_text = field_value.strip()
            elif isinstance(field_value, dict):
                reasoning_text = field_value.get('content', '').strip()
            elif field_value is not None:
                reasoning_text = str(field_value).strip()
        
        # Validate reasoning text
        if reasoning_text and reasoning_text.lower() not in ['null', 'none', '']:
            logger.info(f"✅ Extracted reasoning from field '{field_name}': {len(reasoning_text)} chars")
            return reasoning_text, content  # Content unchanged (reasoning is separate)
        
        return None, content
    
    def _extract_embedded(
        self,
        response: Dict,
        content: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract embedded thinking from content (Qwen-style).
        
        Pattern: Long thinking paragraph(s), then short answer.
        """
        if not content:
            # Try to get content from response
            if 'choices' in response and len(response['choices']) > 0:
                message = response['choices'][0].get('message', {})
                content = message.get('content', '')
        
        if not content:
            return None, None
        
        paragraphs = content.split('\n\n')
        if len(paragraphs) < 2:
            return None, content
        
        # Check if first paragraph is much longer (thinking indicator)
        first_len = len(paragraphs[0])
        rest_len = sum(len(p) for p in paragraphs[1:])
        total_len = first_len + rest_len
        
        if total_len == 0:
            return None, content
        
        # If first paragraph is >70% of total, it's likely all thinking
        if first_len > total_len * 0.7:
            reasoning_text = paragraphs[0]
            clean_content = '\n\n'.join(paragraphs[1:]).strip()
            
            logger.info(f"✅ Extracted embedded thinking: {len(reasoning_text)} chars")
            return reasoning_text, clean_content
        
        # Check for thinking indicators in first paragraph
        thinking_indicators = [
            r'^i (need to|should|will|must|can)',
            r'^the user',
            r'^let me',
            r'^first,',
            r'^to answer',
            r'^i\'m (thinking|considering|analyzing)',
        ]
        
        first_para = paragraphs[0].strip()
        first_para_lower = first_para.lower()
        
        for pattern in thinking_indicators:
            if re.search(pattern, first_para_lower):
                # First paragraph is thinking, rest is answer
                reasoning_text = paragraphs[0]
                clean_content = '\n\n'.join(paragraphs[1:]).strip()
                
                logger.info(f"✅ Extracted embedded thinking (pattern match): {len(reasoning_text)} chars")
                return reasoning_text, clean_content
        
        return None, content
    
    def _extract_tagged(
        self,
        response: Dict,
        content: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract thinking from tagged content (<think>, <think>, etc.)
        """
        if not content:
            # Try to get content from response
            if 'choices' in response and len(response['choices']) > 0:
                message = response['choices'][0].get('message', {})
                content = message.get('content', '')
        
        if not content:
            return None, None
        
        # Try different tag formats
        tag_patterns = [
            (r'<think>(.*?)</think>', 'redacted_reasoning'),
            (r'<think>(.*?)</think>', 'think'),
            (r'<thinking>(.*?)</thinking>', 'thinking'),
            (r'<reasoning>(.*?)</reasoning>', 'reasoning'),
        ]
        
        for pattern, tag_name in tag_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                reasoning_text = match.group(1).strip()
                clean_content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE).strip()
                
                logger.info(f"✅ Extracted tagged thinking ({tag_name}): {len(reasoning_text)} chars")
                return reasoning_text, clean_content
        
        return None, content
    
    def _extract_from_delta(
        self,
        response: Dict,
        field_name: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract reasoning from streaming delta chunks.
        """
        if 'choices' not in response or len(response['choices']) == 0:
            return None, None
        
        choice = response['choices'][0]
        delta = choice.get('delta', {})
        
        if field_name in delta:
            field_value = delta[field_name]
            if isinstance(field_value, str):
                reasoning_text = field_value.strip()
            elif isinstance(field_value, dict):
                reasoning_text = field_value.get('content', '').strip()
            else:
                reasoning_text = str(field_value).strip() if field_value else None
            
            if reasoning_text and reasoning_text.lower() not in ['null', 'none', '']:
                logger.debug(f"Extracted reasoning from delta field '{field_name}'")
                return reasoning_text, None
        
        return None, None
    
    def _extract_heuristic(
        self,
        response: Dict,
        model_name: Optional[str],
        content: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Heuristic extraction when format is unknown.
        
        Tries common field names and patterns.
        """
        if not response:
            return None, content
        
        # Try common field names in various locations
        common_fields = [
            'reasoning',
            'reasoning_content',
            'thinking',
            'thinking_content',
            'internal_reasoning',
            'reasoning_text',
        ]
        
        # Check in choices[0].message
        if 'choices' in response and len(response['choices']) > 0:
            message = response['choices'][0].get('message', {})
            
            for field in common_fields:
                if field in message:
                    field_value = message[field]
                    if isinstance(field_value, str) and field_value.strip():
                        reasoning_text = field_value.strip()
                        if reasoning_text.lower() not in ['null', 'none']:
                            logger.info(f"✅ Heuristic: Found reasoning in '{field}'")
                            return reasoning_text, content
        
        # Check top level
        for field in common_fields:
            if field in response:
                field_value = response[field]
                if isinstance(field_value, str) and field_value.strip():
                    reasoning_text = field_value.strip()
                    if reasoning_text.lower() not in ['null', 'none']:
                        logger.info(f"✅ Heuristic: Found reasoning in top-level '{field}'")
                        return reasoning_text, content
        
        # Try embedded extraction as fallback
        if content:
            reasoning, clean = self._extract_embedded(response, content)
            if reasoning:
                return reasoning, clean
        
        return None, content
    
    def extract_from_stream_chunk(
        self,
        chunk: Dict[str, Any],
        model_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract reasoning from a single streaming chunk.
        
        Args:
            chunk: Single chunk from streaming response
            model_name: Model identifier
            
        Returns:
            Reasoning text if found, None otherwise
        """
        format_type, field_name = self.detector.detect_reasoning_format(chunk, model_name)
        
        if format_type == ReasoningFormat.STREAMING_CHUNKS and field_name:
            reasoning, _ = self._extract_from_delta(chunk, field_name)
            return reasoning
        
        # Check for reasoning in content delta (some models stream reasoning as content)
        if 'choices' in chunk and len(chunk['choices']) > 0:
            delta = chunk['choices'][0].get('delta', {})
            content = delta.get('content', '')
            
            if content and self._is_reasoning_chunk(content):
                return content
        
        return None
    
    def _is_reasoning_chunk(self, content: str) -> bool:
        """
        Heuristic: Is this chunk likely reasoning (not final answer)?
        
        Looks for reasoning indicators in content.
        """
        if not content or len(content) < 10:
            return False
        
        content_lower = content.lower().strip()
        
        reasoning_indicators = [
            r'^(i|the user|let me|first|to answer|i\'m)',
            r'^(thinking|considering|analyzing|reasoning)',
            r'^(need to|should|will|must)',
        ]
        
        for pattern in reasoning_indicators:
            if re.search(pattern, content_lower):
                return True
        
        return False


# Global instance
_extractor = ReasoningExtractor()


def extract_reasoning(
    response: Dict[str, Any],
    model_name: Optional[str] = None,
    content: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Quick extraction of reasoning from response.
    
    Returns:
        Tuple of (reasoning_text, clean_content)
    """
    return _extractor.extract(response, model_name, content)


def extract_from_stream_chunk(
    chunk: Dict[str, Any],
    model_name: Optional[str] = None
) -> Optional[str]:
    """Quick extraction from streaming chunk"""
    return _extractor.extract_from_stream_chunk(chunk, model_name)


if __name__ == "__main__":
    # Test
    extractor = ReasoningExtractor()
    
    # Test 1: Separate field
    response1 = {
        'choices': [{
            'message': {
                'content': 'The answer is 42.',
                'reasoning_content': 'I need to calculate...'
            }
        }]
    }
    
    reasoning, content = extractor.extract(response1, 'openai/o1')
    print(f"Test 1 - Separate field:")
    print(f"  Reasoning: {reasoning[:50] if reasoning else None}...")
    print(f"  Content: {content}")
    
    # Test 2: Embedded
    response2 = {
        'choices': [{
            'message': {
                'content': 'I need to think about this carefully. Let me analyze the problem step by step.\n\nThe answer is 42.'
            }
        }]
    }
    
    reasoning, content = extractor.extract(response2, 'qwen/qwq-32b')
    print(f"\nTest 2 - Embedded:")
    print(f"  Reasoning: {reasoning[:50] if reasoning else None}...")
    print(f"  Content: {content}")

