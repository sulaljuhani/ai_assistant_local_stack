/**
 * AnythingLLM Custom Skill: Import Chat History
 * Imports chat history from other AI platforms
 */

module.exports.runtime = {
  handler: async function({ source, file_path }) {
    try {
      const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8000";

      if (!source || !["chatgpt", "claude", "gemini"].includes(source.toLowerCase())) {
        return "Please specify a valid source: chatgpt, claude, or gemini";
      }

      if (!file_path || file_path.trim() === "") {
        return "Please provide the path to the export file.";
      }

      const endpoint = `${API_URL}/api/import/${source.toLowerCase()}`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          file_path: file_path.trim()
        })
      });

      if (!response.ok) {
        const errorText = await response.text();

        if (response.status === 409) {
          return `⚠️ This file has already been imported. If you need to re-import, delete it from the imported_chats table first.`;
        }

        return `Failed to import chat history: API returned ${response.status}. ${errorText}`;
      }

      const result = await response.json();

      return `✅ Successfully imported ${result.conversations_count || 0} conversations from ${source}. All messages are now searchable in memory.`;

    } catch (error) {
      this.logger(`Error importing chat history: ${error.message}`);
      return `Error importing chat history: ${error.message}`;
    }
  }
};
