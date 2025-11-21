/**
 * AnythingLLM Custom Skill: Store Memory
 * Stores important information as a searchable memory
 */

module.exports.runtime = {
  handler: async function({ content, conversation_title }) {
    try {
      const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8000";
      const USER_ID = process.env.USER_ID || "00000000-0000-0000-0000-000000000001";

      if (!content || content.trim() === "") {
        return "Please provide content to remember.";
      }

      const memoryData = {
        content: content.trim(),
        conversation_title: conversation_title || "AnythingLLM Chat",
        salience_score: 0.8,
        user_id: USER_ID
      };

      const response = await fetch(`${API_URL}/api/memory/store`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(memoryData)
      });

      if (!response.ok) {
        return `Failed to store memory: API returned ${response.status}. Please check that langgraph-agents service is running.`;
      }

      const result = await response.json();
      const preview = content.length > 100 ? content.substring(0, 100) + "..." : content;
      return `💾 Memory stored: "${preview}"`;

    } catch (error) {
      this.logger(`Error storing memory: ${error.message}`);
      return `Error storing memory: ${error.message}`;
    }
  }
};
