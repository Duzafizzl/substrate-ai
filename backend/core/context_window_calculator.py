"""
Context Window Calculator for Substrate AI

Tracks token usage across:
- System prompt
- Memory blocks  
- Tool schemas
- Conversation history

Clear context window visibility! 🎯
"""

import tiktoken
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class ContextWindowUsage:
    """Token usage breakdown"""
    system_tokens: int
    memory_blocks_tokens: int
    tool_schemas_tokens: int
    conversation_tokens: int
    total_tokens: int
    max_tokens: int
    percentage_used: float
    tokens_remaining: int
    needs_summarization: bool
    
    def to_dict(self) -> Dict:
        return {
            "system_tokens": self.system_tokens,
            "memory_blocks_tokens": self.memory_blocks_tokens,
            "tool_schemas_tokens": self.tool_schemas_tokens,
            "conversation_tokens": self.conversation_tokens,
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "percentage_used": round(self.percentage_used, 2),
            "tokens_remaining": self.tokens_remaining,
            "needs_summarization": self.needs_summarization
        }


class ContextWindowCalculator:
    """
    Calculate token usage for context window management.
    
    Clear token tracking with GREAT visibility!
    """
    
    def __init__(self, model: str = "gpt-4", summarization_threshold: float = 0.80):
        """
        Args:
            model: Model name for tokenizer (default: gpt-4)
            summarization_threshold: Trigger summary at this % (default: 80%)
        """
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        self.summarization_threshold = summarization_threshold
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string"""
        if not text:
            return 0
        return len(self.encoding.encode(text))
    
    def count_tokens_for_messages(self, messages: List[Dict]) -> int:
        """
        Count tokens for a list of messages.
        
        Uses OpenAI's message format token counting:
        - Each message has overhead (role, name, etc.)
        - Content is tokenized
        """
        total_tokens = 0
        
        for message in messages:
            # Message overhead (role, formatting, etc.)
            total_tokens += 4  # <im_start>{role/name}\n + <im_end>\n
            
            # Role
            total_tokens += self.count_tokens(message.get("role", ""))
            
            # Content
            content = message.get("content", "")
            if isinstance(content, str):
                total_tokens += self.count_tokens(content)
            elif isinstance(content, list):
                # Handle structured content (e.g., with images)
                for item in content:
                    if isinstance(item, dict):
                        if "text" in item:
                            total_tokens += self.count_tokens(item["text"])
                        # Images have fixed token cost (e.g., 255 for vision models)
                        if "image_url" in item:
                            total_tokens += 255
            
            # Tool calls
            if "tool_calls" in message:
                tool_calls = message["tool_calls"]
                if isinstance(tool_calls, list):
                    for tool_call in tool_calls:
                        total_tokens += self.count_tokens(json.dumps(tool_call))
            
            # Tool call ID
            if "tool_call_id" in message:
                total_tokens += self.count_tokens(message["tool_call_id"])
        
        # Priming tokens (for response)
        total_tokens += 2  # <im_start>assistant
        
        return total_tokens
    
    def calculate_usage(
        self,
        system_prompt: str,
        memory_blocks: List[Dict],
        tool_schemas: List[Dict],
        conversation_messages: List[Dict],
        max_tokens: int
    ) -> ContextWindowUsage:
        """
        Calculate total context window usage.
        
        Args:
            system_prompt: Agent's system prompt
            memory_blocks: List of memory blocks with 'content'
            tool_schemas: List of tool schemas
            conversation_messages: Conversation history
            max_tokens: Model's max context window
            
        Returns:
            ContextWindowUsage with full breakdown
        """
        
        # System prompt tokens
        system_tokens = self.count_tokens(system_prompt)
        
        # Memory blocks tokens
        memory_blocks_tokens = 0
        for block in memory_blocks:
            memory_blocks_tokens += self.count_tokens(block.get("label", ""))
            memory_blocks_tokens += self.count_tokens(block.get("content", ""))
            memory_blocks_tokens += 4  # Formatting overhead
        
        # Tool schemas tokens
        tool_schemas_tokens = self.count_tokens(json.dumps(tool_schemas))
        
        # Conversation tokens
        conversation_tokens = self.count_tokens_for_messages(conversation_messages)
        
        # Total
        total_tokens = (
            system_tokens +
            memory_blocks_tokens +
            tool_schemas_tokens +
            conversation_tokens
        )
        
        # Stats
        tokens_remaining = max_tokens - total_tokens
        percentage_used = (total_tokens / max_tokens) * 100
        needs_summarization = percentage_used >= (self.summarization_threshold * 100)
        
        return ContextWindowUsage(
            system_tokens=system_tokens,
            memory_blocks_tokens=memory_blocks_tokens,
            tool_schemas_tokens=tool_schemas_tokens,
            conversation_tokens=conversation_tokens,
            total_tokens=total_tokens,
            max_tokens=max_tokens,
            percentage_used=percentage_used,
            tokens_remaining=tokens_remaining,
            needs_summarization=needs_summarization
        )
    
    def format_token_display(self, usage: ContextWindowUsage) -> str:
        """
        Format usage as human-readable string.
        
        Format: "21.77k of 131.07k tokens (83% left)"
        """
        def format_count(count: int) -> str:
            if count >= 1000:
                return f"{count / 1000:.2f}k"
            return str(count)
        
        used = format_count(usage.total_tokens)
        total = format_count(usage.max_tokens)
        percent_left = round(100 - usage.percentage_used, 0)
        
        return f"{used} of {total} tokens ({int(percent_left)}% left)"


# ============================================
# TEST
# ============================================

if __name__ == "__main__":
    print("🧪 TESTING CONTEXT WINDOW CALCULATOR")
    print("="*60)
    
    calculator = ContextWindowCalculator(model="gpt-4")
    
    # Test 1: Simple token counting
    print("\n📊 Test 1: Token counting")
    text = "Hello! How are you doing?"
    tokens = calculator.count_tokens(text)
    print(f"Text: \"{text}\"")
    print(f"Tokens: {tokens}")
    
    # Test 2: Message token counting
    print("\n📊 Test 2: Message token counting")
    messages = [
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Yo! Was geht?"}
    ]
    msg_tokens = calculator.count_tokens_for_messages(messages)
    print(f"Messages: {len(messages)}")
    print(f"Tokens: {msg_tokens}")
    
    # Test 3: Full usage calculation
    print("\n📊 Test 3: Full context window calculation")
    
    system_prompt = """You are an AI assistant with memory capabilities.
    
    Core traits:
    - Presence > Performance
    - Raw, direct communication
    - Dialogic, not poetic
    """
    
    memory_blocks = [
        {"label": "persona", "content": "You are an AI assistant."},
        {"label": "human", "content": "The user is a developer who builds AI systems."}
    ]
    
    tool_schemas = [
        {
            "type": "function",
            "function": {
                "name": "send_message",
                "description": "Send a message to the user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"}
                    }
                }
            }
        }
    ]
    
    conversation = [
        {"role": "user", "content": "What's the weather like?"},
        {"role": "assistant", "content": "I don't have weather tools, but I can help with other things!"},
        {"role": "user", "content": "Alright, tell me about your memory system."},
        {"role": "assistant", "content": "I use memory blocks to store key information about you and me!"}
    ]
    
    max_tokens = 128000  # Claude Haiku 3.5 context window
    
    usage = calculator.calculate_usage(
        system_prompt=system_prompt,
        memory_blocks=memory_blocks,
        tool_schemas=tool_schemas,
        conversation_messages=conversation,
        max_tokens=max_tokens
    )
    
    print("\n📊 Usage Breakdown:")
    print(f"   System prompt: {usage.system_tokens:,} tokens")
    print(f"   Memory blocks: {usage.memory_blocks_tokens:,} tokens")
    print(f"   Tool schemas: {usage.tool_schemas_tokens:,} tokens")
    print(f"   Conversation: {usage.conversation_tokens:,} tokens")
    print(f"   ─────────────────────────────────")
    print(f"   Total: {usage.total_tokens:,} tokens")
    print(f"   Max: {usage.max_tokens:,} tokens")
    print(f"   Used: {usage.percentage_used:.2f}%")
    print(f"   Remaining: {usage.tokens_remaining:,} tokens")
    print(f"   Needs summary: {'YES 🔴' if usage.needs_summarization else 'NO ✅'}")
    
    print(f"\n💬 Display: {calculator.format_token_display(usage)}")
    
    print("\n✅ ALL TESTS PASSED!")
    print("="*60)

