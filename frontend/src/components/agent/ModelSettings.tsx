import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import VersionHistory from './VersionHistory';

interface Model {
  id: string;
  name: string;
  provider: string;
  description?: string;
  context_length?: number;
  pricing?: {
    prompt?: string;      // Cost per token (from OpenRouter API)
    completion?: string;  // Cost per token
  };
  architecture?: {
    modality?: string;          // "text", "text+image", "text+image+audio"
    tokenizer?: string;
    instruct_type?: string;
  };
  top_provider?: {
    max_completion_tokens?: number;
    is_moderated?: boolean;
  };
}

interface ModelPricing {
  inputCostPer1M: number;  // Cost per 1M input tokens
  outputCostPer1M: number; // Cost per 1M output tokens
  rating: 'free' | 'cheap' | 'moderate' | 'expensive' | 'very-expensive';
  notes?: string;
}

type ModelCapability = 'vision' | 'tools' | 'reasoning' | 'streaming' | 'long-context' | 'fast';

interface ModelCapabilities {
  capabilities: ModelCapability[];
  notes?: string;
}

type QualityTier = 'flagship' | 'premium' | 'good' | 'budget' | 'experimental';

interface ModelQuality {
  tier: QualityTier;
  stars: number;  // 1-5
  valueScore: number;  // 0-100 (quality/price ratio)
  notes?: string;
}

// 🎯 MODEL CAPABILITIES DATABASE
const MODEL_CAPABILITIES: Record<string, ModelCapabilities> = {
  // ========== GOOGLE GEMINI ==========
  'google/gemini-2.0-flash-exp:free': {
    capabilities: ['vision', 'tools', 'streaming', 'fast', 'long-context'],
    notes: 'Full-featured kostenlos model!'
  },
  'google/gemini-flash-1.5': {
    capabilities: ['vision', 'tools', 'streaming', 'fast', 'long-context']
  },
  'google/gemini-pro-1.5': {
    capabilities: ['vision', 'tools', 'streaming', 'long-context']
  },
  
  // ========== QWEN MODELS ==========
  'qwen/qwen-2.5-72b-instruct': {
    capabilities: ['tools', 'streaming', 'long-context'],
    notes: 'Tool-calling support, günstig & schnell'
  },
  'qwen/qwen3-vl-30b-a3b-thinking': {
    capabilities: ['vision', 'tools', 'reasoning', 'streaming'],
    notes: 'Native reasoning model mit Vision!'
  },
  'qwen/qwq-32b-preview': {
    capabilities: ['tools', 'reasoning', 'streaming', 'long-context'],
    notes: 'Reasoning specialist'
  },
  
  // ========== META LLAMA ==========
  'meta-llama/llama-3.3-70b-instruct': {
    capabilities: ['tools', 'streaming', 'long-context'],
    notes: 'Open-source, tool support'
  },
  'meta-llama/llama-3.1-405b-instruct': {
    capabilities: ['tools', 'streaming', 'long-context'],
    notes: 'Largest open-source model'
  },
  'meta-llama/llama-3.2-90b-vision-instruct': {
    capabilities: ['vision', 'tools', 'streaming', 'long-context'],
    notes: 'Llama mit Vision'
  },
  
  // ========== ANTHROPIC CLAUDE ==========
  'anthropic/claude-opus-4': {
    capabilities: ['vision', 'tools', 'streaming', 'long-context'],
    notes: 'Beste Qualität von Anthropic'
  },
  'anthropic/claude-opus-4.5': {
    capabilities: ['vision', 'tools', 'streaming', 'long-context'],
    notes: 'Beste Qualität von Anthropic'
  },
  'anthropic/claude-sonnet-4': {
    capabilities: ['vision', 'tools', 'streaming', 'reasoning', 'long-context'],
    notes: 'Extended Thinking support!'
  },
  'anthropic/claude-sonnet-4.5': {
    capabilities: ['vision', 'tools', 'streaming', 'reasoning', 'long-context'],
    notes: 'Extended Thinking support! Newest Sonnet.'
  },
  'anthropic/claude-3.5-sonnet': {
    capabilities: ['vision', 'tools', 'streaming', 'long-context'],
    notes: 'Bewährte Qualität'
  },
  'anthropic/claude-3.5-sonnet:beta': {
    capabilities: ['vision', 'tools', 'streaming', 'reasoning', 'long-context'],
    notes: 'Extended Thinking Beta'
  },
  'anthropic/claude-3-opus': {
    capabilities: ['vision', 'tools', 'streaming', 'long-context']
  },
  'anthropic/claude-3-sonnet': {
    capabilities: ['vision', 'tools', 'streaming', 'long-context']
  },
  'anthropic/claude-3-haiku': {
    capabilities: ['vision', 'tools', 'streaming', 'fast']
  },
  'anthropic/claude-haiku-4': {
    capabilities: ['vision', 'streaming', 'fast'],
    notes: 'Schnell aber keine Tools'
  },
  'anthropic/claude-haiku-4.5': {
    capabilities: ['vision', 'streaming', 'fast'],
    notes: 'Schnell aber KEINE TOOLS!'
  },
  
  // ========== OPENAI ==========
  'openai/gpt-4o': {
    capabilities: ['vision', 'tools', 'streaming', 'long-context'],
    notes: 'Multimodal flagship'
  },
  'openai/gpt-4o-mini': {
    capabilities: ['vision', 'tools', 'streaming', 'fast', 'long-context'],
    notes: 'Günstige GPT-4o Variante'
  },
  'openai/gpt-4-turbo': {
    capabilities: ['vision', 'tools', 'streaming', 'long-context']
  },
  'openai/gpt-3.5-turbo': {
    capabilities: ['tools', 'streaming', 'fast']
  },
  'openai/o1': {
    capabilities: ['tools', 'reasoning', 'long-context'],
    notes: 'Advanced reasoning'
  },
  'openai/o1-mini': {
    capabilities: ['tools', 'reasoning', 'fast'],
    notes: 'Faster reasoning'
  },
  'openai/o1-preview': {
    capabilities: ['tools', 'reasoning', 'long-context']
  },
  
  // ========== OPENROUTER SPECIALS ==========
  'openrouter/polaris-alpha': {
    capabilities: ['tools', 'streaming', 'long-context'],
    notes: 'GPT-5.1, 256k context window'
  },
  
  // ========== DEEPSEEK ==========
  'deepseek/deepseek-chat': {
    capabilities: ['tools', 'streaming', 'long-context', 'fast'],
    notes: 'Sehr effizient'
  },
  'deepseek/deepseek-coder': {
    capabilities: ['tools', 'streaming', 'long-context'],
    notes: 'Code specialist'
  },
  
  // ========== MISTRAL ==========
  'mistralai/mistral-large': {
    capabilities: ['tools', 'streaming', 'long-context']
  },
  'mistralai/mistral-medium': {
    capabilities: ['tools', 'streaming', 'long-context']
  },
  'mistralai/mistral-small': {
    capabilities: ['tools', 'streaming', 'fast']
  },
  'mistralai/mixtral-8x7b-instruct': {
    capabilities: ['tools', 'streaming', 'long-context', 'fast'],
    notes: 'MoE architecture'
  },
  'mistralai/mixtral-8x22b-instruct': {
    capabilities: ['tools', 'streaming', 'long-context'],
    notes: 'Larger MoE'
  },
  
  // ========== X.AI GROK ==========
  'x-ai/grok-beta': {
    capabilities: ['tools', 'streaming', 'long-context'],
    notes: 'Real-time info via X'
  },
  'x-ai/grok-vision-beta': {
    capabilities: ['vision', 'tools', 'streaming', 'long-context'],
    notes: 'Grok mit Vision'
  },
  
  // ========== PERPLEXITY ==========
  'perplexity/llama-3.1-sonar-large-128k-online': {
    capabilities: ['tools', 'streaming', 'long-context'],
    notes: 'Online search integrated'
  },
  'perplexity/llama-3.1-sonar-small-128k-online': {
    capabilities: ['tools', 'streaming', 'long-context', 'fast'],
    notes: 'Fast online search'
  }
};

// 🎨 CAPABILITY ICONS & LABELS
// Note: Labels and descriptions are now translated via i18n in the component
const CAPABILITY_CONFIG: Record<ModelCapability, { icon: string; labelKey: string; color: string; descriptionKey: string }> = {
  vision: {
    icon: '👁️',
    labelKey: 'modelInfo.capabilities.vision.label',
    color: 'text-blue-400',
    descriptionKey: 'modelInfo.capabilities.vision.description'
  },
  tools: {
    icon: '🛠️',
    labelKey: 'modelInfo.capabilities.tools.label',
    color: 'text-purple-400',
    descriptionKey: 'modelInfo.capabilities.tools.description'
  },
  reasoning: {
    icon: '🧠',
    labelKey: 'modelInfo.capabilities.reasoning.label',
    color: 'text-pink-400',
    descriptionKey: 'modelInfo.capabilities.reasoning.description'
  },
  streaming: {
    icon: '⚡',
    labelKey: 'modelInfo.capabilities.streaming.label',
    color: 'text-yellow-400',
    descriptionKey: 'modelInfo.capabilities.streaming.description'
  },
  'long-context': {
    icon: '📚',
    labelKey: 'modelInfo.capabilities.longContext.label',
    color: 'text-green-400',
    descriptionKey: 'modelInfo.capabilities.longContext.description'
  },
  fast: {
    icon: '🚀',
    labelKey: 'modelInfo.capabilities.fast.label',
    color: 'text-orange-400',
    descriptionKey: 'modelInfo.capabilities.fast.description'
  }
};

// 🎨 Helper function for filter selected state classes
function getFilterSelectedClass(colorClass: string): string {
  const colorMap: Record<string, string> = {
    'text-blue-400': 'bg-blue-500/20 border-blue-500/50',
    'text-purple-400': 'bg-purple-500/20 border-purple-500/50',
    'text-pink-400': 'bg-pink-500/20 border-pink-500/50',
    'text-yellow-400': 'bg-yellow-500/20 border-yellow-500/50',
    'text-green-400': 'bg-green-500/20 border-green-500/50',
    'text-orange-400': 'bg-orange-500/20 border-orange-500/50',
  };
  return colorMap[colorClass] || 'bg-purple-500/20 border-purple-500/50';
}

// 💰 MODEL PRICING DATABASE (Updated Nov 2024)
const MODEL_PRICING: Record<string, ModelPricing> = {
  // ========== FREE MODELS 🎉 ==========
  'google/gemini-2.0-flash-exp:free': {
    inputCostPer1M: 0,
    outputCostPer1M: 0,
    rating: 'free',
    notes: 'Kostenlos! Perfect for testing.'
  },
  'google/gemini-flash-1.5': {
    inputCostPer1M: 0.075,
    outputCostPer1M: 0.30,
    rating: 'cheap',
    notes: 'Sehr günstig & schnell'
  },
  'google/gemini-pro-1.5': {
    inputCostPer1M: 1.25,
    outputCostPer1M: 5.00,
    rating: 'moderate'
  },
  
  // ========== QWEN MODELS 💚 ==========
  'qwen/qwen-2.5-72b-instruct': {
    inputCostPer1M: 0.35,
    outputCostPer1M: 0.40,
    rating: 'cheap',
    notes: 'Sehr günstig, gute Qualität!'
  },
  'qwen/qwen3-vl-30b-a3b-thinking': {
    inputCostPer1M: 0.20,
    outputCostPer1M: 1.00,
    rating: 'cheap',
    notes: 'Native Reasoning mit Vision!'
  },
  'qwen/qwq-32b-preview': {
    inputCostPer1M: 0.20,
    outputCostPer1M: 1.00,
    rating: 'cheap',
    notes: 'Reasoning model'
  },
  
  // ========== META LLAMA MODELS 💚 ==========
  'meta-llama/llama-3.3-70b-instruct': {
    inputCostPer1M: 0.35,
    outputCostPer1M: 0.40,
    rating: 'cheap',
    notes: 'Open-source, günstig'
  },
  'meta-llama/llama-3.1-405b-instruct': {
    inputCostPer1M: 2.70,
    outputCostPer1M: 2.70,
    rating: 'moderate',
    notes: 'Größtes Llama Model'
  },
  'meta-llama/llama-3.2-90b-vision-instruct': {
    inputCostPer1M: 0.90,
    outputCostPer1M: 0.90,
    rating: 'moderate',
    notes: 'Vision support'
  },
  
  // ========== ANTHROPIC CLAUDE MODELS ==========
  'anthropic/claude-3.5-sonnet': {
    inputCostPer1M: 3.00,
    outputCostPer1M: 15.00,
    rating: 'moderate',
    notes: 'Gutes Preis-Leistungs-Verhältnis'
  },
  'anthropic/claude-3.5-sonnet:beta': {
    inputCostPer1M: 3.00,
    outputCostPer1M: 15.00,
    rating: 'moderate',
    notes: 'Extended Thinking Beta'
  },
  'anthropic/claude-3-opus': {
    inputCostPer1M: 15.00,
    outputCostPer1M: 75.00,
    rating: 'very-expensive',
    notes: 'Alte Generation, teuer'
  },
  'anthropic/claude-3-sonnet': {
    inputCostPer1M: 3.00,
    outputCostPer1M: 15.00,
    rating: 'moderate'
  },
  'anthropic/claude-3-haiku': {
    inputCostPer1M: 0.25,
    outputCostPer1M: 1.25,
    rating: 'cheap',
    notes: 'Alte Generation, günstig'
  },
  'anthropic/claude-haiku-4': {
    inputCostPer1M: 0.80,
    outputCostPer1M: 4.00,
    rating: 'moderate',
    notes: 'Schnell aber keine Tools'
  },
  'anthropic/claude-haiku-4.5': {
    inputCostPer1M: 1.00,
    outputCostPer1M: 5.00,
    rating: 'moderate',
    notes: '⚠️ Keine Tool-Unterstützung!'
  },
  'anthropic/claude-sonnet-4': {
    inputCostPer1M: 3.00,
    outputCostPer1M: 15.00,
    rating: 'expensive',
    notes: 'Extended Thinking support!'
  },
  'anthropic/claude-opus-4': {
    inputCostPer1M: 15.00,
    outputCostPer1M: 75.00,
    rating: 'very-expensive',
    notes: 'Beste Qualität, aber teuer!'
  },
  'anthropic/claude-opus-4.5': {
    inputCostPer1M: 15.00,
    outputCostPer1M: 75.00,
    rating: 'very-expensive',
    notes: 'Beste Qualität, aber teuer!'
  },
  
  // ========== OPENAI MODELS ==========
  'openai/gpt-4o': {
    inputCostPer1M: 2.50,
    outputCostPer1M: 10.00,
    rating: 'moderate',
    notes: 'Multimodal, Vision'
  },
  'openai/gpt-4o-mini': {
    inputCostPer1M: 0.15,
    outputCostPer1M: 0.60,
    rating: 'cheap',
    notes: 'Günstige GPT-4o Variante'
  },
  'openai/gpt-4-turbo': {
    inputCostPer1M: 10.00,
    outputCostPer1M: 30.00,
    rating: 'expensive',
    notes: 'Vision support'
  },
  'openai/gpt-3.5-turbo': {
    inputCostPer1M: 0.50,
    outputCostPer1M: 1.50,
    rating: 'cheap',
    notes: 'Alte Generation, günstig'
  },
  'openai/o1': {
    inputCostPer1M: 15.00,
    outputCostPer1M: 60.00,
    rating: 'very-expensive',
    notes: 'Reasoning model'
  },
  'openai/o1-mini': {
    inputCostPer1M: 3.00,
    outputCostPer1M: 12.00,
    rating: 'expensive',
    notes: 'Reasoning model, günstiger'
  },
  'openai/o1-preview': {
    inputCostPer1M: 15.00,
    outputCostPer1M: 60.00,
    rating: 'very-expensive',
    notes: 'Preview version'
  },
  
  // ========== OPENROUTER SPECIALS ==========
  'openrouter/polaris-alpha': {
    inputCostPer1M: 5.00,
    outputCostPer1M: 15.00,
    rating: 'expensive',
    notes: 'GPT-5.1, 256k Context'
  },
  
  // ========== DEEPSEEK MODELS 💚 ==========
  'deepseek/deepseek-chat': {
    inputCostPer1M: 0.14,
    outputCostPer1M: 0.28,
    rating: 'cheap',
    notes: 'Sehr günstig, gute Qualität'
  },
  'deepseek/deepseek-coder': {
    inputCostPer1M: 0.14,
    outputCostPer1M: 0.28,
    rating: 'cheap',
    notes: 'Coding spezialisiert'
  },
  
  // ========== MISTRAL MODELS ==========
  'mistralai/mistral-large': {
    inputCostPer1M: 2.00,
    outputCostPer1M: 6.00,
    rating: 'moderate'
  },
  'mistralai/mistral-medium': {
    inputCostPer1M: 2.70,
    outputCostPer1M: 8.10,
    rating: 'moderate'
  },
  'mistralai/mistral-small': {
    inputCostPer1M: 0.20,
    outputCostPer1M: 0.60,
    rating: 'cheap'
  },
  'mistralai/mixtral-8x7b-instruct': {
    inputCostPer1M: 0.24,
    outputCostPer1M: 0.24,
    rating: 'cheap',
    notes: 'Open-source MoE'
  },
  'mistralai/mixtral-8x22b-instruct': {
    inputCostPer1M: 0.65,
    outputCostPer1M: 0.65,
    rating: 'cheap',
    notes: 'Größeres MoE Model'
  },
  
  // ========== X.AI GROK ==========
  'x-ai/grok-beta': {
    inputCostPer1M: 5.00,
    outputCostPer1M: 15.00,
    rating: 'expensive',
    notes: 'Grok by xAI'
  },
  'x-ai/grok-vision-beta': {
    inputCostPer1M: 5.00,
    outputCostPer1M: 15.00,
    rating: 'expensive',
    notes: 'Grok mit Vision'
  },
  
  // ========== PERPLEXITY ==========
  'perplexity/llama-3.1-sonar-large-128k-online': {
    inputCostPer1M: 1.00,
    outputCostPer1M: 1.00,
    rating: 'moderate',
    notes: 'Online search enabled'
  },
  'perplexity/llama-3.1-sonar-small-128k-online': {
    inputCostPer1M: 0.20,
    outputCostPer1M: 0.20,
    rating: 'cheap',
    notes: 'Online search enabled'
  }
};

// 🔥 GET PRICING FROM MODEL (Live API or Fallback Database)
function getModelPricing(model: Model): ModelPricing | null {
  // 1. Try live pricing from OpenRouter API
  if (model.pricing?.prompt && model.pricing?.completion) {
    const inputCostPer1M = parseFloat(model.pricing.prompt) * 1_000_000;
    const outputCostPer1M = parseFloat(model.pricing.completion) * 1_000_000;
    
    // Auto-calculate rating based on cost
    let rating: ModelPricing['rating'];
    const avgCost = (inputCostPer1M + outputCostPer1M) / 2;
    
    if (avgCost === 0) {
      rating = 'free';
    } else if (avgCost < 0.50) {
      rating = 'cheap';
    } else if (avgCost < 5.00) {
      rating = 'moderate';
    } else if (avgCost < 20.00) {
      rating = 'expensive';
    } else {
      rating = 'very-expensive';
    }
    
    return {
      inputCostPer1M,
      outputCostPer1M,
      rating,
      notes: undefined
    };
  }
  
  // 2. Fallback to hardcoded database
  return MODEL_PRICING[model.id] || null;
}

// 🏆 GET QUALITY RATING FROM MODEL (Smart Heuristics)
function getModelQuality(model: Model, pricing: ModelPricing | null): ModelQuality {
  const modelLower = model.id?.toLowerCase() || '';
  
  // Determine Quality Tier based on model family
  let tier: QualityTier = 'good';
  let stars = 3;
  
  // FLAGSHIP (5 stars) - Best of the best
  if (modelLower.includes('opus-4') || 
      modelLower.includes('gpt-4o') && !modelLower.includes('mini') ||
      modelLower.includes('claude-sonnet-4') ||
      modelLower.includes('gemini-2.0') ||
      modelLower.includes('polaris-alpha')) {
    tier = 'flagship';
    stars = 5;
  }
  // PREMIUM (4 stars) - High quality, proven
  else if (modelLower.includes('claude-3.5-sonnet') ||
           modelLower.includes('gpt-4-turbo') ||
           modelLower.includes('gemini-pro-1.5') ||
           modelLower.includes('llama-3.1-405b') ||
           modelLower.includes('claude-opus') && !modelLower.includes('4') ||
           modelLower.includes('o1')) {
    tier = 'premium';
    stars = 4;
  }
  // GOOD (3 stars) - Solid performers
  else if (modelLower.includes('llama-3.3') ||
           modelLower.includes('qwen-2.5-72b') ||
           modelLower.includes('mixtral') ||
           modelLower.includes('mistral-large') ||
           modelLower.includes('claude-3-sonnet') ||
           modelLower.includes('deepseek') ||
           modelLower.includes('gpt-4o-mini')) {
    tier = 'good';
    stars = 3;
  }
  // BUDGET (2 stars) - Cheap but functional
  else if (modelLower.includes('mini') ||
           modelLower.includes('small') ||
           modelLower.includes('haiku') ||
           modelLower.includes('flash') ||
           modelLower.includes('3.5-turbo') ||
           modelLower.includes('mistral-small')) {
    tier = 'budget';
    stars = 2;
  }
  // EXPERIMENTAL (varies) - New/untested models
  else if (modelLower.includes('preview') ||
           modelLower.includes('beta') ||
           modelLower.includes('experimental')) {
    tier = 'experimental';
    stars = 3;
  }
  
  // Calculate Value Score (quality vs price)
  let valueScore = 50; // Default
  
  if (pricing) {
    const avgCost = (pricing.inputCostPer1M + pricing.outputCostPer1M) / 2;
    
    // Value = Stars / Cost (normalized to 0-100)
    if (avgCost === 0) {
      valueScore = 100; // Free = best value!
    } else if (avgCost > 0) {
      // Calculate ratio: higher stars + lower cost = higher value
      const qualityScore = stars * 20; // 1-5 stars → 20-100
      const costPenalty = Math.min(avgCost * 5, 80); // Cap at 80
      valueScore = Math.max(0, Math.min(100, qualityScore - costPenalty + 50));
    }
  }
  
  return {
    tier,
    stars,
    valueScore: Math.round(valueScore),
    notes: undefined
  };
}

// 🔥 GET CAPABILITIES FROM MODEL (Live API data!)
function getModelCapabilities(model: Model): ModelCapabilities | null {
  const detectedCaps: ModelCapability[] = [];
  const modelLower = model.id?.toLowerCase() || '';
  
  // 🎯 PRIORITY 1: Use REAL API data from OpenRouter!
  const supportedParams = (model as any).supported_parameters as string[] | undefined;
  const inputModalities = (model.architecture as any)?.input_modalities as string[] | undefined;
  
  // Vision: Check input_modalities from API
  if (inputModalities?.includes('image') || 
      model.architecture?.modality?.includes('image') ||
      modelLower.includes('vision')) {
    detectedCaps.push('vision');
  }
  
  // Tools: Check supported_parameters from API
  if (supportedParams?.includes('tools') || supportedParams?.includes('tool_choice')) {
    detectedCaps.push('tools');
  } else {
    // Fallback heuristic only if no API data
    const hasToolSupport = 
      modelLower.includes('gpt-4') ||
      modelLower.includes('gpt-3.5') ||
      modelLower.includes('claude') && !modelLower.includes('haiku') ||
      modelLower.includes('gemini') ||
      modelLower.includes('qwen') ||
      modelLower.includes('llama-3') ||
      modelLower.includes('mistral') ||
      modelLower.includes('deepseek');
    if (hasToolSupport) detectedCaps.push('tools');
  }
  
  // 🧠 Reasoning: Check supported_parameters from API!
  if (supportedParams?.includes('reasoning') || 
      supportedParams?.includes('include_reasoning')) {
    detectedCaps.push('reasoning');
    console.log(`🧠 Model ${model.id} has REASONING from API!`);
  } else if (modelLower.includes('o1') || 
             modelLower.includes('thinking') || 
             modelLower.includes('reasoning') ||
             modelLower.includes('qwq')) {
    // Fallback heuristic for reasoning
    detectedCaps.push('reasoning');
  }
  
  // Streaming: Almost all models support streaming
  detectedCaps.push('streaming');
  
  // Long Context: Check context length
  if (model.context_length && model.context_length >= 128000) {
    detectedCaps.push('long-context');
  }
  
  // Fast: Small/mini models
  if (modelLower.includes('mini') || 
      modelLower.includes('small') ||
      modelLower.includes('haiku') ||
      modelLower.includes('flash') ||
      modelLower.includes('3.5-turbo')) {
    detectedCaps.push('fast');
  }
  
  if (detectedCaps.length > 0) {
    return { capabilities: detectedCaps, notes: undefined };
  }
  
  // 2. Fallback to hardcoded database
  return MODEL_CAPABILITIES[model.id] || null;
}

interface ModelConfig {
  model: string;
  temperature: number;
  max_tokens: number | null;
  top_p: number;
  context_window: number;
  // Letta-style Reasoning Settings 🧠
  reasoning_enabled?: boolean;
  max_reasoning_tokens?: number;
}

interface SystemPromptState {
  text: string;
  loading: boolean;
  saving: boolean;
  expanded: boolean;
}

interface ModelSettingsProps {
  agentId?: string;
}

export default function ModelSettings({ agentId = 'default' }: ModelSettingsProps) {
  const { t } = useTranslation();
  const [models, setModels] = useState<Model[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [config, setConfig] = useState<ModelConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [sortBy, setSortBy] = useState<'quality' | 'value' | 'price-low' | 'price-high' | 'name'>('quality');
  const [selectedFilters, setSelectedFilters] = useState<Set<ModelCapability>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [systemPrompt, setSystemPrompt] = useState<SystemPromptState>({
    text: '',
    loading: true,
    saving: false,
    expanded: false
  });
  // 🔥 Use agentId directly (it's already the correct ID from URL!)
  // No need to fetch "real" ID - agentId from URL is the correct one
  const displayAgentId = agentId || 'default';

  useEffect(() => {
    fetchModels();
    fetchConfig();
    fetchSystemPrompt();
  }, [agentId]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchModels = async () => {
    try {
      const response = await fetch('http://localhost:8284/api/models/all');
      const data = await response.json();
      setModels(data.models || []);
    } catch (error) {
      console.error('Failed to fetch models:', error);
    }
  };

  const fetchConfig = async () => {
    try {
      const response = await fetch(`http://localhost:8284/api/agents/${agentId}/config`);
      const data = await response.json();
      setConfig(data);
    } catch (error) {
      console.error('Failed to fetch config:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSystemPrompt = async () => {
    try {
      const response = await fetch(`http://localhost:8284/api/agents/${agentId}/system-prompt`);
      const data = await response.json();
      setSystemPrompt(prev => ({ ...prev, text: data.system_prompt || '', loading: false }));
    } catch (error) {
      console.error('Failed to fetch system prompt:', error);
      setSystemPrompt(prev => ({ ...prev, loading: false }));
    }
  };

  const saveConfig = async () => {
    if (!config) return;

    setSaving(true);
    try {
      await fetch(`http://localhost:8284/api/agents/${agentId}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
    } catch (error) {
      console.error('Failed to save config:', error);
    } finally {
      setSaving(false);
    }
  };

  const saveSystemPrompt = async () => {
    setSystemPrompt(prev => ({ ...prev, saving: true }));
    try {
      await fetch(`http://localhost:8284/api/agents/${agentId}/system-prompt`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ system_prompt: systemPrompt.text })
      });
    } catch (error) {
      console.error('Failed to save system prompt:', error);
    } finally {
      setSystemPrompt(prev => ({ ...prev, saving: false }));
    }
  };

  const updateConfig = (field: keyof ModelConfig, value: any) => {
    if (!config) return;
    setConfig({ ...config, [field]: value });
  };

  const selectModel = (modelId: string) => {
    // Find the model to check capabilities
    const selectedModel = models.find(m => m.id === modelId);
    
    // If it's an Ollama model, add the ollama: prefix
    const finalModelId = selectedModel?.provider === 'ollama' 
      ? `ollama:${modelId}` 
      : modelId;
    
    // 🧠 AUTO-ENABLE REASONING: If model has reasoning capability, turn it on!
    const capabilities = selectedModel ? getModelCapabilities(selectedModel) : null;
    const hasReasoning = capabilities?.capabilities.includes('reasoning') || false;
    
    // Update model AND reasoning_enabled together
    setConfig(prev => prev ? {
      ...prev,
      model: finalModelId,
      reasoning_enabled: hasReasoning  // Auto-enable if model supports it!
    } : prev);
    
    if (hasReasoning) {
      console.log(`🧠 Auto-enabled reasoning for ${finalModelId}`);
    }
    
    setShowDropdown(false);
    setSearchQuery('');
  };

  // Filter and Sort models
  const filteredAndSortedModels = models
    .filter(m => {
      // Search filter
      const matchesSearch = 
        m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.id.toLowerCase().includes(searchQuery.toLowerCase());
      
      if (!matchesSearch) return false;
      
      // Capability filters (multi-select: model must have ALL selected capabilities)
      if (selectedFilters.size > 0) {
        const capabilities = getModelCapabilities(m);
        if (!capabilities || capabilities.capabilities.length === 0) {
          return false;
        }
        
        // Check if model has ALL selected capabilities
        for (const filter of selectedFilters) {
          if (!capabilities.capabilities.includes(filter)) {
            return false;
          }
        }
      }
      
      return true;
    })
    .sort((a, b) => {
      const pricingA = getModelPricing(a);
      const pricingB = getModelPricing(b);
      const qualityA = getModelQuality(a, pricingA);
      const qualityB = getModelQuality(b, pricingB);
      
      switch (sortBy) {
        case 'quality':
          // Sort by stars (descending), then by value score
          if (qualityA.stars !== qualityB.stars) {
            return qualityB.stars - qualityA.stars;
          }
          return qualityB.valueScore - qualityA.valueScore;
        
        case 'value':
          // Sort by value score (descending)
          return qualityB.valueScore - qualityA.valueScore;
        
        case 'price-low':
          // Sort by average price (ascending)
          if (!pricingA || !pricingB) return 0;
          const avgA = (pricingA.inputCostPer1M + pricingA.outputCostPer1M) / 2;
          const avgB = (pricingB.inputCostPer1M + pricingB.outputCostPer1M) / 2;
          return avgA - avgB;
        
        case 'price-high':
          // Sort by average price (descending)
          if (!pricingA || !pricingB) return 0;
          const avgA2 = (pricingA.inputCostPer1M + pricingA.outputCostPer1M) / 2;
          const avgB2 = (pricingB.inputCostPer1M + pricingB.outputCostPer1M) / 2;
          return avgB2 - avgA2;
        
        case 'name':
          // Sort alphabetically by name
          return a.name.localeCompare(b.name);
        
        default:
          return 0;
      }
    });

  const currentModel = models.find(m => m.id === config?.model);

  if (loading || !config) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-gray-900 border-r border-gray-800">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <h2 className="text-sm font-semibold text-gray-300">Agent Settings</h2>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        {/* Agent ID (copy button) */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-400">Agent ID</label>
          <div className="flex items-center gap-2">
            <code className="text-xs text-gray-500 font-mono truncate flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg">
              {displayAgentId}
            </code>
            <button
              onClick={() => {
                navigator.clipboard.writeText(displayAgentId);
                // Visual feedback
                const btn = document.activeElement as HTMLButtonElement;
                if (btn) {
                  const originalText = btn.innerHTML;
                  btn.innerHTML = '<svg class="w-3 h-3 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>';
                  setTimeout(() => {
                    btn.innerHTML = originalText;
                  }, 1000);
                }
              }}
              className="p-2 hover:bg-gray-800 rounded transition-colors border border-gray-700"
              title="Copy Agent ID"
            >
              <svg className="w-3 h-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Model Selector */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-400 flex items-center gap-2">
            Model
            <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </label>

          <div className="relative" ref={dropdownRef}>
            {/* Selected Model Display */}
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-left hover:border-gray-600 transition-colors flex items-center justify-between"
            >
              <div className="flex-1 min-w-0">
                <div className="text-gray-200 truncate">{currentModel?.name || config.model}</div>
                <div className="text-xs text-gray-500 truncate mt-0.5">{config.model}</div>
              </div>
              <svg className={`w-4 h-4 text-gray-400 transition-transform ml-2 flex-shrink-0 ${showDropdown ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Dropdown */}
            {showDropdown && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute z-50 w-full mt-2 bg-gray-800 border border-gray-700 rounded-lg shadow-xl overflow-hidden"
              >
                {/* Search + Sort + Filters */}
                <div className="p-3 border-b border-gray-700 space-y-2">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search models..."
                    className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
                    autoFocus
                  />
                  
                  {/* Sort + Filter Toggle */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">Sort:</span>
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as any)}
                      className="flex-1 px-2 py-1.5 bg-gray-900 border border-gray-700 rounded-lg text-xs text-gray-200 focus:outline-none focus:border-purple-500"
                    >
                      <option value="quality">🏆 Best Quality</option>
                      <option value="value">💎 Best Value</option>
                      <option value="price-low">💚 Cheapest First</option>
                      <option value="price-high">🔴 Most Expensive</option>
                      <option value="name">🔤 Name (A-Z)</option>
                    </select>
                    
                    {/* Filter Toggle Button */}
                    <button
                      onClick={() => setShowFilters(!showFilters)}
                      className={`px-2 py-1.5 text-xs rounded-lg border transition-colors ${
                        selectedFilters.size > 0
                          ? 'bg-purple-500/20 border-purple-500/50 text-purple-400'
                          : 'bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-600'
                      }`}
                      title="Filter by capabilities"
                    >
                      🔍 Filter {selectedFilters.size > 0 && `(${selectedFilters.size})`}
                    </button>
                  </div>
                  
                  {/* Capability Filters */}
                  {showFilters && (
                    <div className="pt-2 border-t border-gray-700">
                      <div className="text-xs text-gray-500 mb-2">Filter by capabilities (multi-select):</div>
                      <div className="grid grid-cols-2 gap-2">
                        {(Object.keys(CAPABILITY_CONFIG) as ModelCapability[]).map((cap) => {
                          const capConfig = CAPABILITY_CONFIG[cap];
                          const isSelected = selectedFilters.has(cap);
                          return (
                            <label
                              key={cap}
                              className={`
                                flex items-center gap-2 px-2 py-1.5 rounded-lg border cursor-pointer transition-colors
                                ${isSelected
                                  ? getFilterSelectedClass(capConfig.color)
                                  : 'bg-gray-900 border-gray-700 hover:border-gray-600'
                                }
                              `}
                            >
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={(e) => {
                                  const newFilters = new Set(selectedFilters);
                                  if (e.target.checked) {
                                    newFilters.add(cap);
                                  } else {
                                    newFilters.delete(cap);
                                  }
                                  setSelectedFilters(newFilters);
                                }}
                                className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-purple-500 focus:ring-purple-500 focus:ring-offset-gray-900"
                              />
                              <span className={`text-xs ${isSelected ? capConfig.color : 'text-gray-400'}`}>
                                {capConfig.icon} {t(capConfig.labelKey)}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                      {selectedFilters.size > 0 && (
                        <button
                          onClick={() => setSelectedFilters(new Set())}
                          className="mt-2 text-xs text-gray-400 hover:text-gray-300 underline"
                        >
                          Clear filters
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Model List */}
                <div className="max-h-96 overflow-y-auto">
                  {filteredAndSortedModels.length === 0 ? (
                    <div className="px-3 py-6 text-center text-sm text-gray-500">
                      No models found
                    </div>
                  ) : (
                    filteredAndSortedModels.map((model) => {
                      const pricing = getModelPricing(model);  // 🔥 Live or Fallback
                      const capabilities = getModelCapabilities(model);  // 🔥 Live detection!
                      const priceIcon = pricing ? (
                        pricing.rating === 'free' ? '🎉' :
                        pricing.rating === 'cheap' ? '💚' :
                        pricing.rating === 'moderate' ? '💛' :
                        pricing.rating === 'expensive' ? '🧡' : '🔴'
                      ) : null;

                      return (
                        <button
                          key={model.id}
                          onClick={() => selectModel(model.id)}
                          className={`
                            w-full px-3 py-2.5 text-left hover:bg-gray-700 transition-colors
                            ${model.id === config.model ? 'bg-gray-700' : ''}
                          `}
                        >
                          <div className="flex items-start gap-2">
                            {/* Provider Badge */}
                            <span className={`
                              px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0 mt-0.5
                              ${model.provider === 'openrouter' ? 'bg-purple-500/10 text-purple-400' : 'bg-blue-500/10 text-blue-400'}
                            `}>
                              {model.provider}
                            </span>

                            {/* Model Info */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5">
                                <div className="text-sm text-gray-200 font-medium truncate">{model.name}</div>
                                {priceIcon && <span className="text-sm">{priceIcon}</span>}
                              </div>
                              <div className="text-xs text-gray-500 truncate mt-0.5">{model.id}</div>
                              
                              {/* 🎯 CAPABILITIES */}
                              {capabilities && capabilities.capabilities.length > 0 && (
                                <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                                  {capabilities.capabilities.map((cap) => {
                                    const capConfig = CAPABILITY_CONFIG[cap];
                                    return (
                                      <span
                                        key={cap}
                                        className="group relative"
                                        title={t(capConfig.descriptionKey)}
                                      >
                                        <span className={`text-xs ${capConfig.color} cursor-help`}>
                                          {capConfig.icon}
                                        </span>
                                        {/* Tooltip on hover */}
                                        <span className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-1 px-2 py-1 bg-gray-900 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                                          {t(capConfig.labelKey)}: {t(capConfig.descriptionKey)}
                                        </span>
                                      </span>
                                    );
                                  })}
                                </div>
                              )}
                              
                              {pricing && (
                                <div className="text-xs text-gray-600 mt-1">
                                  ${pricing.inputCostPer1M.toFixed(2)}/${pricing.outputCostPer1M.toFixed(2)} per 1M
                                </div>
                              )}
                              {model.description && (
                                <p className="text-xs text-gray-600 mt-1 line-clamp-2">{model.description}</p>
                              )}
                            </div>

                            {/* Checkmark */}
                            {model.id === config.model && (
                              <svg className="w-4 h-4 text-purple-400 flex-shrink-0 mt-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </motion.div>
            )}
          </div>

          {/* Model ID (copy button) */}
          <div className="flex items-center gap-2 mt-1">
            <code className="text-xs text-gray-500 font-mono truncate flex-1">{config.model}</code>
            <button
              onClick={() => navigator.clipboard.writeText(config.model)}
              className="p-1 hover:bg-gray-800 rounded transition-colors"
              title="Copy model ID"
            >
              <svg className="w-3 h-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          </div>

          {/* 💰 PRICING INFO + CAPABILITIES + QUALITY RATING */}
          {(() => {
            // Find current model to get live pricing & capabilities
            const currentModelData = models.find(m => m.id === config.model);
            const pricing = currentModelData ? getModelPricing(currentModelData) : MODEL_PRICING[config.model];
            const capabilities = currentModelData ? getModelCapabilities(currentModelData) : MODEL_CAPABILITIES[config.model];
            const quality = currentModelData ? getModelQuality(currentModelData, pricing) : null;
            if (!pricing) return null;

            const ratingConfig = {
              'free': {
                bg: 'bg-green-500/10',
                text: 'text-green-400',
                border: 'border-green-500/20',
                labelKey: 'modelInfo.pricing.free',
                icon: '🎉'
              },
              'cheap': {
                bg: 'bg-emerald-500/10',
                text: 'text-emerald-400',
                border: 'border-emerald-500/20',
                labelKey: 'modelInfo.pricing.cheap',
                icon: '💚'
              },
              'moderate': {
                bg: 'bg-yellow-500/10',
                text: 'text-yellow-400',
                border: 'border-yellow-500/20',
                labelKey: 'modelInfo.pricing.moderate',
                icon: '💛'
              },
              'expensive': {
                bg: 'bg-orange-500/10',
                text: 'text-orange-400',
                border: 'border-orange-500/20',
                labelKey: 'modelInfo.pricing.expensive',
                icon: '🧡'
              },
              'very-expensive': {
                bg: 'bg-red-500/10',
                text: 'text-red-400',
                border: 'border-red-500/20',
                labelKey: 'modelInfo.pricing.veryExpensive',
                icon: '🔴'
              }
            };

            const ratingCfg = ratingConfig[pricing.rating];

            // Quality tier config (colors only, labels via i18n)
            const tierConfig = {
              flagship: { color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
              premium: { color: 'text-purple-400', bg: 'bg-purple-500/10' },
              good: { color: 'text-blue-400', bg: 'bg-blue-500/10' },
              budget: { color: 'text-green-400', bg: 'bg-green-500/10' },
              experimental: { color: 'text-orange-400', bg: 'bg-orange-500/10' }
            };

            return (
              <div className={`mt-3 p-3 rounded-lg border ${ratingCfg.border} ${ratingCfg.bg}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    {/* QUALITY RATING (Stars + Tier) */}
                    {quality && (
                      <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-700/50">
                        {/* Stars */}
                        <div className="flex items-center gap-0.5" title={`${quality.stars}/5 Quality Rating`}>
                          {[...Array(5)].map((_, i) => (
                            <span key={i} className={`text-sm ${i < quality.stars ? 'text-yellow-400' : 'text-gray-700'}`}>
                              ⭐
                            </span>
                          ))}
                        </div>
                        {/* Tier Label */}
                        <span className={`text-xs font-bold ${tierConfig[quality.tier].color}`}>
                          {t(`modelInfo.quality.tier.${quality.tier}`)}
                        </span>
                        {/* Value Score */}
                        <div className="ml-auto flex items-center gap-1" title={t('modelInfo.quality.valueScoreTooltip', { score: quality.valueScore })}>
                          <span className="text-xs text-gray-500">{t('modelInfo.quality.value')}:</span>
                          <span className={`text-xs font-bold ${
                            quality.valueScore >= 80 ? 'text-green-400' :
                            quality.valueScore >= 60 ? 'text-blue-400' :
                            quality.valueScore >= 40 ? 'text-yellow-400' : 'text-orange-400'
                          }`}>
                            {quality.valueScore}/100
                          </span>
                        </div>
                      </div>
                    )}
                    
                    {/* PRICE RATING */}
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-bold ${ratingCfg.text}`}>
                        {ratingCfg.icon} {t(ratingCfg.labelKey)}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 space-y-0.5">
                      <div>{t('modelInfo.pricing.input')}: ${pricing.inputCostPer1M.toFixed(2)} / 1M tokens</div>
                      <div>{t('modelInfo.pricing.output')}: ${pricing.outputCostPer1M.toFixed(2)} / 1M tokens</div>
                      {/* 📚 CONTEXT WINDOW */}
                      {currentModelData?.context_length && (
                        <div className="flex items-center gap-1 mt-1">
                          <span className="text-purple-400">📚</span>
                          <span>{t('modelInfo.pricing.context')}: {(currentModelData.context_length / 1000).toFixed(0)}K tokens</span>
                        </div>
                      )}
                      {pricing.notes && (
                        <div className={`mt-1.5 ${ratingCfg.text} font-medium`}>
                          {pricing.notes}
                        </div>
                      )}
                    </div>
                    
                    {/* 🎯 CAPABILITIES */}
                    {capabilities && capabilities.capabilities.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-700/50">
                        <div className="text-xs font-medium text-gray-400 mb-1.5">{t('modelInfo.capabilities.title')}:</div>
                        <div className="flex flex-wrap gap-2">
                          {capabilities.capabilities.map((cap) => {
                            const capConfig = CAPABILITY_CONFIG[cap];
                            return (
                              <div
                                key={cap}
                                className="group relative flex items-center gap-1 px-2 py-1 bg-gray-800/50 rounded-md border border-gray-700/50"
                                title={t(capConfig.descriptionKey)}
                              >
                                <span className="text-xs">{capConfig.icon}</span>
                                <span className={`text-xs ${capConfig.color} font-medium`}>
                                  {t(capConfig.labelKey)}
                                </span>
                                {/* Tooltip on hover */}
                                <span className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-lg">
                                  {t(capConfig.descriptionKey)}
                                  <span className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-900"></span>
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="text-2xl">💰</div>
                </div>
              </div>
            );
          })()}
          
        </div>

        {/* 🔥 PROMINENT SAVE BUTTON - Saves Model, Context Window, Temperature, Top P, etc. */}
        <div className="sticky top-0 z-10 bg-gray-900/95 backdrop-blur-sm pb-3 -mx-4 px-4 border-b border-gray-800 mb-4">
          <button
            onClick={async () => {
              setSaving(true);
              try {
                const targetAgentId = agentId || 'default';
                console.log(`💾 Saving all config for agent: ${targetAgentId}`);
                
                const response = await fetch(`http://localhost:8284/api/agents/${targetAgentId}/config`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(config)
                });
                
                const result = await response.json();
                
                if (result.success) {
                  // Dispatch custom event to notify AgentSelector and Token Counter
                  window.dispatchEvent(new CustomEvent('agentModelUpdated', {
                    detail: { model: config.model, agentId: targetAgentId }
                  }));
                  
                  // Show success feedback
                  alert('✅ All changes saved!\n\n• Model: ' + config.model + '\n• Context Window: ' + (config.context_window ?? 128000).toLocaleString() + '\n• Temperature: ' + (config.temperature ?? 0.7).toFixed(2) + '\n• Top P: ' + (config.top_p ?? 1.0).toFixed(2));
                  
                  // Refresh the config to show updated values
                  await fetchConfig();
                } else {
                  throw new Error('Save failed');
                }
              } catch (error) {
                console.error('Failed to save config:', error);
                alert('❌ Failed to save changes!');
              } finally {
                setSaving(false);
              }
            }}
            disabled={saving}
            className="w-full px-4 py-3 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 disabled:from-gray-700 disabled:to-gray-800 text-white rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2 shadow-lg shadow-purple-500/20 hover:shadow-purple-500/30 disabled:shadow-none"
          >
            {saving ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Saving Changes...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>💾 Save All Changes</span>
              </>
            )}
          </button>
        </div>

        {/* Temperature */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-400 flex items-center justify-between">
            <span>Temperature</span>
            <span className="text-purple-400">{(config.temperature ?? 0.7).toFixed(2)}</span>
          </label>
          <input
            type="range"
            min="0"
            max="2"
            step="0.01"
            value={config.temperature ?? 0.7}
            onChange={(e) => updateConfig('temperature', parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
          />
          <div className="flex justify-between text-xs text-gray-600">
            <span>Precise</span>
            <span>Balanced</span>
            <span>Creative</span>
          </div>
        </div>

        {/* Context Window - Slider with Model Max Limit */}
        {(() => {
          // Get current model to determine max context window
          const currentModelData = models.find(m => m.id === config.model);
          const maxContextWindow = currentModelData?.context_length || 128000; // Fallback to 128k if not found
          const currentContextWindow = config.context_window ?? maxContextWindow;
          
          // Format number for display (e.g., "128K" instead of "128,000")
          const formatContextWindow = (value: number): string => {
            if (value >= 1000000) {
              return `${(value / 1000000).toFixed(1)}M`;
            } else if (value >= 1000) {
              return `${(value / 1000).toFixed(0)}K`;
            }
            return value.toString();
          };
          
          return (
            <div className="space-y-2">
              <label className="text-xs font-medium text-gray-400 flex items-center justify-between">
                <span>{t('modelSettings.contextWindow')}</span>
                <span className="text-purple-400">{formatContextWindow(currentContextWindow)} {t('modelSettings.tokens')}</span>
              </label>
              <input
                type="range"
                min="1000"
                max={maxContextWindow}
                step="1000"
                value={currentContextWindow}
                onChange={(e) => updateConfig('context_window', parseInt(e.target.value))}
                className="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
              />
              <div className="flex justify-between text-xs text-gray-600">
                <span>1K</span>
                <span className="text-purple-400">{t('modelSettings.max')}: {formatContextWindow(maxContextWindow)}</span>
              </div>
              <p className="text-xs text-gray-600">
                💡 {t('modelSettings.contextWindowHint', { modelName: currentModelData?.name || config.model, maxTokens: formatContextWindow(maxContextWindow) })}
              </p>
            </div>
          );
        })()}

        {/* Top P */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-400 flex items-center justify-between">
            <span>Top P</span>
            <span className="text-purple-400">{(config.top_p ?? 1.0).toFixed(2)}</span>
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={config.top_p ?? 1.0}
            onChange={(e) => updateConfig('top_p', parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
          />
        </div>

        {/* Max Tokens */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-400">Max Tokens</label>
          <input
            type="number"
            value={config.max_tokens || ''}
            onChange={(e) => updateConfig('max_tokens', e.target.value ? parseInt(e.target.value) : null)}
            placeholder="Auto"
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
          />
          <p className="text-xs text-gray-600">Leave empty for automatic</p>
        </div>

        {/* Letta-Style: Reasoning Settings 🧠 */}
        <div className="space-y-3 border-t border-gray-800 pt-6">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-gray-400 flex items-center gap-2">
              <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Reasoning
            </label>
            <button
              onClick={() => updateConfig('reasoning_enabled', !config.reasoning_enabled)}
              className={`
                px-3 py-1 rounded text-xs font-medium transition-all
                ${config.reasoning_enabled 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-gray-800 text-gray-400 border border-gray-700'
                }
              `}
            >
              {config.reasoning_enabled ? 'ON' : 'OFF'}
            </button>
          </div>

          {config.reasoning_enabled && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-2 pl-6"
            >
              <label className="text-xs font-medium text-gray-400 flex items-center justify-between">
                <span>Max Reasoning Tokens</span>
                <span className="text-purple-400">{config.max_reasoning_tokens || 'Auto'}</span>
              </label>
              <input
                type="number"
                value={config.max_reasoning_tokens || ''}
                onChange={(e) => updateConfig('max_reasoning_tokens', e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="Auto"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500"
              />
              <p className="text-xs text-gray-600">
                💡 For native reasoning models (o1, DeepSeek R1). Polaris uses system prompt instead.
              </p>
            </motion.div>
          )}
        </div>

        {/* System Prompt - Collapsible */}
        <div className="space-y-2 border-t border-gray-800 pt-6">
          <button
            onClick={() => setSystemPrompt(prev => ({ ...prev, expanded: !prev.expanded }))}
            className="w-full flex items-center justify-between text-xs font-medium text-gray-400 hover:text-gray-300 transition-colors"
          >
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              <span>System Prompt</span>
              {systemPrompt.text && (
                <span className="text-purple-400">({systemPrompt.text.length.toLocaleString()} chars)</span>
              )}
            </div>
            <svg 
              className={`w-4 h-4 transition-transform ${systemPrompt.expanded ? 'rotate-180' : ''}`} 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {systemPrompt.expanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-2"
            >
              {systemPrompt.loading ? (
                <div className="w-full h-64 flex items-center justify-center bg-gray-800 rounded-lg border border-gray-700">
                  <div className="w-6 h-6 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
                </div>
              ) : (
                <>
                  <textarea
                    value={systemPrompt.text}
                    onChange={(e) => setSystemPrompt(prev => ({ ...prev, text: e.target.value }))}
                    placeholder="Enter system prompt..."
                    className="w-full h-64 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500 font-mono resize-y"
                  />
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-gray-600">
                      {systemPrompt.text.length.toLocaleString()} characters
                    </p>
                    <button
                      onClick={saveSystemPrompt}
                      disabled={systemPrompt.saving}
                      className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white rounded text-xs font-medium transition-colors flex items-center gap-1.5"
                    >
                      {systemPrompt.saving ? (
                        <>
                          <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Save Prompt
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </motion.div>
          )}
        </div>

        {/* Version History */}
        <VersionHistory agentId={agentId} />
      </div>

      {/* Save Button - Fixed at bottom like chatbar */}
      <div className="px-4 py-3 border-t border-gray-800 flex-shrink-0 bg-gray-900">
        <button
          onClick={saveConfig}
          disabled={saving}
          className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
        >
          {saving ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Save Changes
            </>
          )}
        </button>
      </div>
    </div>
  );
}

