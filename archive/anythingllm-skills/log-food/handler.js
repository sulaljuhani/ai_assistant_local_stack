/**
 * AnythingLLM Custom Skill: Log Food
 * Logs food consumption using the LangGraph Food Agent
 */

module.exports.runtime = {
  handler: async function({ message }) {
    try {
      const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8000";
      const USER_ID = process.env.USER_ID || "00000000-0000-0000-0000-000000000001";

      if (!message || message.trim() === "") {
        return "Please provide a description of what you ate.";
      }

      // Prepend context to help route to Food Agent
      const foodMessage = `Log food: ${message}`;

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: foodMessage,
          user_id: USER_ID,
          workspace: "anythingllm",
          session_id: `anythingllm-food-${Date.now()}`
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        return `Failed to log food: API returned ${response.status}. Please check that langgraph-agents service is running.`;
      }

      const result = await response.json();
      return `🍽️ ${result.response || "Food logged successfully!"}`;

    } catch (error) {
      this.logger(`Error logging food: ${error.message}`);
      return `Error logging food: ${error.message}. Please ensure the LangGraph agents service is accessible.`;
    }
  }
};
