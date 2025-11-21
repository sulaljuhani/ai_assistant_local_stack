/**
 * AnythingLLM Custom Skill: AI Assistant (Pydantic AI Agent)
 *
 * Intelligent conversational agent that:
 * - Evaluates all user requests for completeness
 * - Asks clarifying questions when information is missing
 * - Validates data before execution
 * - Makes smart suggestions
 * - Maintains conversation context
 * - Routes to appropriate tools (LangGraph tools / database)
 *
 * This skill replaces individual skills (create-task, log-food, etc.) with
 * a unified conversational interface. The agent layer provides:
 * - Intent understanding
 * - Missing information detection
 * - Smart defaults and suggestions
 * - Multi-turn conversations
 * - Error handling and validation
 *
 * Usage:
 * - "Create a task" → Agent asks for details
 * - "Log that I ate pizza" → Agent asks for rating, time, etc.
 * - "Show me my day" → Agent provides summary and offers to adjust
 * - "Help me plan my week" → Multi-turn conversation
 */

module.exports.runtime = {
  name: "ai-assistant",
  description: "Your intelligent personal assistant. Handles tasks, reminders, food logging, daily planning, and more. Asks clarifying questions and makes smart suggestions. Use for any request - the agent will figure out what you need.",

  inputs: {
    // No specific inputs - agent handles natural language
  },

  /**
   * Main handler - routes all requests to Pydantic AI agent
   */
  handler: async function ({ message, workspaceSlug }) {
    const AGENT_URL = process.env.PYDANTIC_AGENT_URL || "http://pydantic-agent:8000/chat";

    try {
      // Generate conversation ID based on workspace
      // This maintains context across messages in the same workspace
      const conversationId = `anythingllm-${workspaceSlug}`;

      // Call the Pydantic AI agent service
      const response = await fetch(AGENT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          conversation_id: conversationId,
          user_id: process.env.DEFAULT_USER_ID || "00000000-0000-0000-0000-000000000001"
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Agent service error: ${response.status} - ${errorText}`);
        return {
          success: false,
          error: `Agent service error: ${response.status}`,
          response: "Sorry, I'm having trouble connecting to the agent service. Please check that the Pydantic AI container is running."
        };
      }

      const result = await response.json();

      return {
        success: true,
        response: result.response,
        conversation_id: result.conversation_id
      };

    } catch (error) {
      console.error('Error calling Pydantic AI agent:', error);

      // Provide helpful error message
      let errorMessage = "I encountered an error processing your request.";

      if (error.code === 'ECONNREFUSED') {
        errorMessage = "I can't connect to the agent service. Please ensure the Pydantic AI container is running and accessible at " + AGENT_URL;
      } else if (error.code === 'ETIMEDOUT') {
        errorMessage = "The agent service is taking too long to respond. Please try again.";
      }

      return {
        success: false,
        error: error.message,
        response: errorMessage
      };
    }
  }
};

/**
 * SETUP INSTRUCTIONS
 * ==================
 *
 * 1. Ensure Pydantic AI Agent container is running:
 *    docker ps | grep pydantic-agent
 *
 * 2. Test agent service health:
 *    curl http://pydantic-agent:8000/health
 *
 * 3. Set environment variable (optional):
 *    PYDANTIC_AGENT_URL=http://pydantic-agent:8000/chat
 *
 * 4. Import this skill in AnythingLLM:
 *    Settings → Agent Skills → Import Skill
 *
 * 5. Enable the skill in your workspace
 *
 * 6. (Optional) Disable old skills:
 *    - create-task.js
 *    - create-reminder.js
 *    - log-food.js
 *    These are now handled by the agent layer
 *
 * TESTING
 * =======
 *
 * Try these conversations:
 *
 * Simple request:
 *   You: "Create a task"
 *   Agent: "What task would you like to add?"
 *   You: "Call dentist"
 *   Agent: "When do you need to do this by?"
 *   ...
 *
 * Complex request:
 *   You: "Show me my day"
 *   Agent: [Shows tasks and events]
 *   You: "Move the blog task to tomorrow"
 *   Agent: [Updates task] "Done! Anything else?"
 *
 * Food logging:
 *   You: "I ate pizza"
 *   Agent: "Great! A few questions: What time? How would you rate it?"
 *   ...
 *
 * ADVANTAGES OVER INDIVIDUAL SKILLS
 * ==================================
 *
 * Individual Skills (old way):
 * - Required exact parameters
 * - No validation before execution
 * - No clarifying questions
 * - No suggestions
 * - No conversation memory
 * - Each skill is separate
 *
 * Agent Layer (new way):
 * - Natural language input
 * - Validates before executing
 * - Asks when information is missing
 * - Makes intelligent suggestions
 * - Maintains conversation context
 * - Unified interface for everything
 *
 * ARCHITECTURE
 * ============
 *
 * Flow:
 *   AnythingLLM → ai-assistant.js → Pydantic AI Agent
 *                                         ↓
 *                                   (Evaluates, clarifies)
 *                                         ↓
 *                                   Tools (LangGraph/DB)
 *                                         ↓
 *                                   PostgreSQL
 *
 * CONVERSATION MEMORY
 * ===================
 *
 * The agent maintains context within each workspace:
 *
 *   You: "Create a task to call dentist Friday"
 *   Agent: "Created! Want a reminder?"
 *   You: "Yes, day before"  ← Agent knows "reminder for dentist task"
 *   Agent: "Reminder set for Thursday"
 *
 * Conversations are isolated per workspace but persist across
 * the session. To clear conversation memory:
 *   curl -X DELETE http://pydantic-agent:8000/conversation/anythingllm-{workspace}
 *
 * TROUBLESHOOTING
 * ===============
 *
 * "Can't connect to agent service"
 *   → Check container: docker ps | grep pydantic-agent
 *   → Check network: docker network inspect ai-stack-network
 *   → Check URL: curl http://pydantic-agent:8000/health
 *
 * "Agent not asking questions"
 *   → Check Ollama model is loaded: docker exec ollama-ai-stack ollama list
 *   → Check system prompt in main.py
 *   → Check agent logs: docker logs pydantic-agent
 *
 * "Conversations not connected"
 *   → Check conversation_id is being passed correctly
 *   → View active conversations: curl http://pydantic-agent:8000/conversations
 *
 * "Agent calling wrong tools"
 *   → Check tool docstrings in main.py are clear
 *   → Review agent logs for tool selection reasoning
 *   → Adjust system prompt if needed
 */
