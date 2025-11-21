/**
 * AnythingLLM Custom Skill: Recommend Food
 * Gets personalized food recommendations from the LangGraph Food Agent
 */

module.exports.runtime = {
  handler: async function({ message }) {
    try {
      const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8000";
      const USER_ID = process.env.USER_ID || "00000000-0000-0000-0000-000000000001";

      const recommendMessage = message
        ? `Recommend food: ${message}`
        : "Recommend food I liked but haven't eaten recently";

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: recommendMessage,
          user_id: USER_ID,
          workspace: "anythingllm",
          session_id: `anythingllm-food-${Date.now()}`
        })
      });

      if (!response.ok) {
        return `Failed to get food recommendations: API returned ${response.status}. Please check that langgraph-agents service is running.`;
      }

      const result = await response.json();
      return `🍴 ${result.response || "Here are some food recommendations based on your history!"}`;

    } catch (error) {
      this.logger(`Error getting food recommendations: ${error.message}`);
      return `Error getting food recommendations: ${error.message}. Please ensure the LangGraph agents service is accessible.`;
    }
  }
};
