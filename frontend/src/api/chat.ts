import { apiClient } from './client';
import type {
  ChatRequest,
  ChatResponse,
  SessionInfo,
  HealthResponse
} from '../types/api';

export const chatApi = {
  /**
   * Send a message to the multi-agent system
   */
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const { data } = await apiClient.post<ChatResponse>('/chat', request);
    return data;
  },

  /**
   * Get session/conversation details
   */
  getSession: async (sessionId: string): Promise<SessionInfo> => {
    const { data } = await apiClient.get<SessionInfo>(`/session/${sessionId}`);
    return data;
  },

  /**
   * Delete a session/conversation
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/session/${sessionId}`);
  },

  /**
   * Check backend health
   */
  healthCheck: async (): Promise<HealthResponse> => {
    const { data } = await apiClient.get<HealthResponse>('/health');
    return data;
  },
};
