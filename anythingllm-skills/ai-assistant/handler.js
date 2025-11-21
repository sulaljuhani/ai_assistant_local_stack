/**
 * AnythingLLM Custom Skill: AI Assistant
 * Intelligent conversational agent using Pydantic AI
 */

module.exports.runtime = {
  handler: async function({ message }) {
    try {
      const AGENT_URL = process.env.PYDANTIC_AGENT_URL || "http://pydantic-agent:8000/chat";
      const USER_ID = process.env.DEFAULT_USER_ID || "00000000-0000-0000-0000-000000000001";

      if (!message || message.trim() === "") {
        return "How can I assist you today?";
      }

      // Generate conversation ID (you can customize this)
      const conversationId = `anythingllm-assistant-${Date.now()}`;

      const response = await fetch(AGENT_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: message,
          conversation_id: conversationId,
          user_id: USER_ID
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        return `I'm having trouble connecting to the assistant service (status ${response.status}). Please check that the Pydantic AI container is running.`;
      }

      const result = await response.json();
      return result.response || "I processed your request but got no response.";

    } catch (error) {
      this.logger(`Error calling AI assistant: ${error.message}`);

      if (error.code === "ECONNREFUSED") {
        return "I can't connect to the assistant service. Please ensure the Pydantic AI container is running.";
      } else if (error.code === "ETIMEDOUT") {
        return "The assistant service is taking too long to respond. Please try again.";
      }

      return `Error: ${error.message}`;
    }
  }
};
