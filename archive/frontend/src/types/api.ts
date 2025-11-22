/**
 * Backend API request/response types
 * Match FastAPI Pydantic models exactly
 */

// ============================================================================
// Chat Endpoints
// ============================================================================

export interface ChatRequest {
  message: string;
  user_id: string;
  workspace: string;
  session_id: string;
}

export interface ChatResponse {
  response: string;
  agent: string;
  session_id: string;
  turn_count: number;
  timestamp: string;
}

// ============================================================================
// Session Endpoints
// ============================================================================

export interface SessionInfo {
  session_id: string;
  user_id: string;
  workspace: string;
  current_agent: string;
  turn_count: number;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Health Endpoint
// ============================================================================

export interface HealthResponse {
  status: string;
  timestamp: string;
  llm_provider: string;
}
