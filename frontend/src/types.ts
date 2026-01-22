/**
 * Common types used throughout the application
 */

// Message type for chat
export interface Message {
  id?: string;  // Unique message ID (for threads, etc.)
  role: 'user' | 'assistant' | 'system';
  content: string;
  message_type?: 'inbox' | 'system';  // inbox = normal, system = context management
  model?: string;  // Which model generated this response (for assistant messages)
  // Structured data (only for assistant messages)
  thinking?: string;
  toolCalls?: Array<{
    name: string;
    arguments: Record<string, any>;
    result: any;
  }>;
  reasoningTime?: number;
}

// A chat session stored locally
export interface ChatSession {
  id: string;
  title: string;
  createdAt: string; // ISO timestamp
  updatedAt: string; // ISO timestamp
  messages: Message[];
}