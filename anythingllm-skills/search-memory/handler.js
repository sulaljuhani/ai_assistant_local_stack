/**
 * AnythingLLM Custom Skill: Search Memory
 * Searches stored memories using semantic vector search
 */

module.exports.runtime = {
  handler: async function({ query, limit }) {
    try {
      const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8000";
      const USER_ID = process.env.USER_ID || "00000000-0000-0000-0000-000000000001";

      if (!query || query.trim() === "") {
        return "Please provide a search query.";
      }

      const searchLimit = limit || 10;

      const response = await fetch(`${API_URL}/api/memory/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query: query.trim(),
          limit: searchLimit,
          user_id: USER_ID
        })
      });

      if (!response.ok) {
        return `Failed to search memories: API returned ${response.status}. Please check that langgraph-agents service is running.`;
      }

      const result = await response.json();

      if (!result.memories || result.memories.length === 0) {
        return `🔍 No memories found for "${query}". Try a different search term.`;
      }

      const memoryList = result.memories.map((mem, idx) => {
        const score = (mem.similarity_score * 100).toFixed(1);
        return `${idx + 1}. [${score}%] ${mem.content.substring(0, 150)}${mem.content.length > 150 ? "..." : ""}`;
      }).join("\n\n");

      return `🔍 Found ${result.memories.length} memories for "${query}":\n\n${memoryList}`;

    } catch (error) {
      this.logger(`Error searching memories: ${error.message}`);
      return `Error searching memories: ${error.message}`;
    }
  }
};
