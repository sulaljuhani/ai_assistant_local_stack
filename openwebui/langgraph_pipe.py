"""
OpenWebUI Pipe Function for LangGraph Integration (FIXED for single-user)

This Pipe provides direct integration with your LangGraph multi-agent system,
with full access to chat_id for conversation continuity and all metadata.

IMPORTANT FIX: Always uses the hardcoded single-user ID instead of OpenWebUI's user_id

Installation:
1. Copy this file content
2. In OpenWebUI, go to Workspace > Functions
3. Find the existing "LangGraph" function and click Edit
4. Replace ALL the code with this updated version
5. Save and test

Usage:
- The function will appear as a model in OpenWebUI
- Select "LangGraph Agents" from the model dropdown
- Chat normally - conversation context is automatically maintained
"""

import os
import requests
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        """Configuration parameters for the LangGraph integration."""

        LANGGRAPH_CHAT_URL: str = Field(
            default="http://langgraph-agents:8000/chat",
            description="LangGraph chat endpoint URL (use Docker network name if running in containers)"
        )
        LANGGRAPH_API_KEY: str = Field(
            default="",
            description="Optional API key for LangGraph authentication"
        )
        LANGGRAPH_USER_ID: str = Field(
            default="00000000-0000-0000-0000-000000000001",
            description="Single-user ID (DO NOT CHANGE - all data is stored under this ID)"
        )
        LANGGRAPH_WORKSPACE: str = Field(
            default="default",
            description="Workspace identifier for LangGraph"
        )
        REQUEST_TIMEOUT: int = Field(
            default=90,
            description="Request timeout in seconds (increased for bulk operations)"
        )
        DEBUG_MODE: bool = Field(
            default=False,
            description="Enable debug logging"
        )

    def __init__(self):
        self.type = "manifold"
        self.id = "langgraph"
        self.name = "Sebastian: "
        self.valves = self.Valves()

    def pipes(self) -> List[dict]:
        """Return available LangGraph agents as selectable models."""
        return [
            {
                "id": "sebastian",
                "name": "Sebastian"
            }
        ]

    def pipe(
        self,
        body: dict,
        __user__: dict = None,
        __metadata__: dict = None,
        __event_emitter__=None,
    ) -> Union[str, Generator, Iterator]:
        """
        Main pipe function that forwards chat requests to LangGraph.

        Args:
            body: Chat request body with messages, model, etc.
            __user__: OpenWebUI user information (NOT USED - single-user system)
            __metadata__: Rich metadata including chat_id, session_id, etc.
            __event_emitter__: Optional event emitter for streaming (future)

        Returns:
            Response from LangGraph agent
        """
        if self.valves.DEBUG_MODE and __event_emitter__:
            __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Connecting to LangGraph...", "done": False},
                }
            )

        # Extract the last user message
        messages = body.get("messages", [])
        user_message = self._extract_user_message(messages)

        # Get chat_id from metadata for conversation continuity
        chat_id = __metadata__.get("chat_id") if __metadata__ else None
        session_id = chat_id or __metadata__.get("session_id") if __metadata__ else None

        # ALWAYS use the hardcoded single-user ID (this is a single-user system)
        # All tasks, events, and food logs are stored under this ID
        user_id = self.valves.LANGGRAPH_USER_ID

        if self.valves.DEBUG_MODE and __event_emitter__:
            __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Session: {session_id[:8] if session_id else 'new'}... | User: {user_id[:8]}...",
                        "done": False
                    },
                }
            )

        # Build LangGraph payload
        langgraph_payload = {
            "message": user_message,
            "user_id": user_id,  # Hardcoded single-user ID
            "workspace": self.valves.LANGGRAPH_WORKSPACE,
            "session_id": session_id or "default-session",
        }

        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if self.valves.LANGGRAPH_API_KEY:
            headers["Authorization"] = f"Bearer {self.valves.LANGGRAPH_API_KEY}"

        # Debug logging
        if self.valves.DEBUG_MODE:
            print(f"[LangGraph Pipe] Forwarding to {self.valves.LANGGRAPH_CHAT_URL}")
            print(f"[LangGraph Pipe] Session ID: {session_id}")
            print(f"[LangGraph Pipe] User ID: {user_id}")
            print(f"[LangGraph Pipe] User message: {user_message[:100]}...")

        try:
            # Call LangGraph API
            response = requests.post(
                self.valves.LANGGRAPH_CHAT_URL,
                json=langgraph_payload,
                headers=headers,
                timeout=self.valves.REQUEST_TIMEOUT,
            )

            if response.status_code >= 400:
                error_msg = f"LangGraph API error ({response.status_code}): {response.text}"
                print(f"[LangGraph Pipe] ERROR: {error_msg}")

                if __event_emitter__:
                    __event_emitter__(
                        {
                            "type": "status",
                            "data": {"description": "Error from LangGraph", "done": True},
                        }
                    )

                return f"Error: {error_msg}"

            # Parse response
            response_data = response.json()

            # Extract content from LangGraph's ChatResponse
            content = self._extract_content(response_data)
            agent = response_data.get("agent", "unknown")

            if self.valves.DEBUG_MODE:
                print(f"[LangGraph Pipe] Response from agent: {agent}")
                print(f"[LangGraph Pipe] Content length: {len(content)}")

            if __event_emitter__:
                __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Response from {agent}",
                            "done": True
                        },
                    }
                )

            return content

        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {self.valves.REQUEST_TIMEOUT}s"
            print(f"[LangGraph Pipe] ERROR: {error_msg}")

            if __event_emitter__:
                __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Request timeout", "done": True},
                    }
                )

            return f"Error: {error_msg}"

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"[LangGraph Pipe] ERROR: {error_msg}")

            if __event_emitter__:
                __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Unexpected error", "done": True},
                    }
                )

            return f"Error: {error_msg}"

    def _extract_user_message(self, messages: List[dict]) -> str:
        """Extract the last user message from messages array."""
        for message in reversed(messages):
            if message.get("role") == "user":
                return message.get("content", "")
        # Fallback: return the last message
        return messages[-1].get("content", "") if messages else ""

    def _extract_content(self, langgraph_response: dict) -> str:
        """Extract content from LangGraph's response."""
        # Try common keys
        for key in ("response", "reply", "content", "message", "text"):
            if key in langgraph_response and isinstance(langgraph_response[key], str):
                return langgraph_response[key]

        # Fallback: stringify the response
        return str(langgraph_response)
