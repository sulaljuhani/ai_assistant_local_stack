/**
 * AnythingLLM Custom Skill: Get Food Recommendations
 * Get AI-powered food recommendations from the LangGraph food agent (Python backend).
 */

module.exports.runtime = {
  name: "recommend-food",
  description: "Get personalized food recommendations based on what you've eaten and liked/favorited. Uses the LangGraph food agent (Python backend).",
  inputs: {
    query: {
      type: "string",
      description: "Optional search query to refine recommendations (e.g., 'something spicy', 'healthy lunch', 'comfort food')",
      required: false
    }
  },
  handler: async function ({ query, workspaceSlug = "default" }) {
    try {
      const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8080";
      const userId = process.env.USER_ID || "anythingllm";
      const sessionId = `food-${workspaceSlug || "default"}`;

      const prompt = query
        ? `Give me food recommendations based on my history. Preferences: ${query}`
        : "Give me food recommendations based on my history. Suggest things I liked or favorited but haven't had in a while.";

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: prompt,
          user_id: userId,
          workspace: workspaceSlug || "default",
          session_id: sessionId
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Food agent call failed: ${response.status} ${errorText}`);
      }

      const result = await response.json();

      return {
        success: true,
        message: result.response || "Here are some ideas based on your food history.",
        agent: result.agent,
        session_id: result.session_id,
        raw: result
      };
    } catch (error) {
      console.error("Error getting food recommendations:", error);
      return {
        success: false,
        error: error.message,
        message: "❌ Failed to get recommendations via LangGraph. Please check the langgraph-agents service."
      };
    }
  }
};
