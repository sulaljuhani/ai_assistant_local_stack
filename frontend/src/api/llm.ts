/**
 * Direct LLM API integration
 *
 * This module provides direct integration with LLM providers (Ollama, OpenAI)
 * based on user-configured API settings.
 *
 * Note: Currently, all chat requests go through the LangGraph backend.
 * This module is prepared for future direct API integration if needed.
 */

import axios from 'axios';
import { loadApiSettings } from '../utils/storage';

/**
 * Chat completion request
 */
export interface ChatCompletionRequest {
  messages: Array<{
    role: 'system' | 'user' | 'assistant';
    content: string;
  }>;
  temperature?: number;
  max_tokens?: number;
}

/**
 * Chat completion response
 */
export interface ChatCompletionResponse {
  content: string;
  model: string;
  finishReason?: string;
}

/**
 * Call Ollama API directly
 */
export const callOllama = async (
  request: ChatCompletionRequest
): Promise<ChatCompletionResponse> => {
  const settings = loadApiSettings();

  if (settings.provider !== 'ollama') {
    throw new Error('Ollama provider not configured');
  }

  const response = await axios.post(
    `${settings.ollamaUrl}/api/chat`,
    {
      model: settings.ollamaModel,
      messages: request.messages,
      stream: false,
      options: {
        temperature: request.temperature ?? 0.7,
        num_predict: request.max_tokens ?? 2000,
      },
    },
    {
      timeout: 60000, // 60 seconds
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  return {
    content: response.data.message.content,
    model: settings.ollamaModel,
    finishReason: response.data.done ? 'stop' : 'length',
  };
};

/**
 * Call OpenAI API directly
 */
export const callOpenAI = async (
  request: ChatCompletionRequest
): Promise<ChatCompletionResponse> => {
  const settings = loadApiSettings();

  if (settings.provider !== 'openai') {
    throw new Error('OpenAI provider not configured');
  }

  if (!settings.openaiApiKey) {
    throw new Error('OpenAI API key not configured');
  }

  const response = await axios.post(
    `${settings.openaiBaseUrl}/chat/completions`,
    {
      model: settings.openaiModel,
      messages: request.messages,
      temperature: request.temperature ?? 0.7,
      max_tokens: request.max_tokens ?? 2000,
    },
    {
      timeout: 60000, // 60 seconds
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${settings.openaiApiKey}`,
      },
    }
  );

  const choice = response.data.choices[0];

  return {
    content: choice.message.content,
    model: settings.openaiModel,
    finishReason: choice.finish_reason,
  };
};

/**
 * Call configured LLM provider
 * Routes to Ollama or OpenAI based on settings
 */
export const callLLM = async (
  request: ChatCompletionRequest
): Promise<ChatCompletionResponse> => {
  const settings = loadApiSettings();

  if (settings.provider === 'ollama') {
    return callOllama(request);
  } else if (settings.provider === 'openai') {
    return callOpenAI(request);
  } else {
    throw new Error(`Unsupported provider: ${settings.provider}`);
  }
};

/**
 * Test connection to configured provider
 */
export const testConnection = async (): Promise<{
  success: boolean;
  message: string;
}> => {
  const settings = loadApiSettings();

  try {
    if (settings.provider === 'ollama') {
      // Test Ollama connection
      const response = await axios.get(`${settings.ollamaUrl}/api/tags`, {
        timeout: 5000,
      });

      const models = response.data.models || [];
      const hasModel = models.some((m: any) => m.name === settings.ollamaModel);

      if (!hasModel) {
        return {
          success: false,
          message: `Model "${settings.ollamaModel}" not found. Available models: ${models.map((m: any) => m.name).join(', ')}`,
        };
      }

      return {
        success: true,
        message: `Connected to Ollama. Model "${settings.ollamaModel}" is available.`,
      };
    } else if (settings.provider === 'openai') {
      // Test OpenAI connection with a minimal request
      await axios.get(`${settings.openaiBaseUrl}/models`, {
        timeout: 5000,
        headers: {
          'Authorization': `Bearer ${settings.openaiApiKey}`,
        },
      });

      return {
        success: true,
        message: 'Connected to OpenAI API successfully.',
      };
    }

    return {
      success: false,
      message: 'Unknown provider',
    };
  } catch (error: any) {
    console.error('Connection test failed:', error);

    if (error.code === 'ECONNREFUSED') {
      return {
        success: false,
        message: `Cannot connect to ${settings.provider}. Make sure the service is running.`,
      };
    } else if (error.response?.status === 401) {
      return {
        success: false,
        message: 'Authentication failed. Check your API key.',
      };
    } else {
      return {
        success: false,
        message: error.message || 'Connection failed',
      };
    }
  }
};
