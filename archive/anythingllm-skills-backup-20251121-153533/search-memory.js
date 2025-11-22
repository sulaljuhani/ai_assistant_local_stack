/**
 * AI Stack - AnythingLLM Custom Skill
 * Search Memory
 *
 * Allows the AI to search through stored memories using vector similarity search.
 */

module.exports = {
  name: "search-memory",
  description: "Searches stored memories and past conversations using semantic search. Use this when the user asks about something they previously mentioned or discussed.",

  parameters: {
    query: {
      type: "string",
      description: "The search query - what to look for in memory",
      required: true
    },
    sector: {
      type: "string",
      description: "Optionally filter by memory sector: semantic, episodic, procedural, emotional, or reflective",
      required: false,
      enum: ["semantic", "episodic", "procedural", "emotional", "reflective"]
    },
    limit: {
      type: "number",
      description: "Maximum number of results to return (default: 10, max: 50)",
      required: false
    },
    summarize: {
      type: "boolean",
      description: "Whether to generate an AI summary of results (default: false)",
      required: false
    }
  },

  async handler({ query, sector, limit = 10, summarize = false }) {
    const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8080";
    const endpoint = `${API_URL}/api/memory/search`;

    // Ensure limit is within bounds
    limit = Math.min(Math.max(limit, 1), 50);

    // Note: Python API expects user_id field
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          user_id: process.env.USER_ID || "anythingllm",
          query,
          sector,
          limit,
          generate_summary: summarize
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        const memories = result.memories || [];

        if (memories.length === 0) {
          return {
            success: true,
            message: `No memories found matching "${query}"`,
            results_count: 0,
            memories: []
          };
        }

        let output = `🔍 Found ${result.results_count} memories matching "${query}":\n\n`;

        // Format memory results
        memories.slice(0, 5).forEach((mem, idx) => {
          output += `${idx + 1}. [${mem.sector}] ${mem.content.substring(0, 150)}... (similarity: ${(mem.similarity_score * 100).toFixed(1)}%)\n\n`;
        });

        if (memories.length > 5) {
          output += `... and ${memories.length - 5} more results\n\n`;
        }

        // Add summary if generated
        if (result.summary) {
          output += `📝 Summary:\n${result.summary}\n`;
        }

        return {
          success: true,
          message: output,
          results_count: result.results_count,
          memories: memories,
          summary: result.summary
        };

      } else {
        throw new Error(result.error || "Failed to search memories");
      }

    } catch (error) {
      return {
        success: false,
        error: `Failed to search memories: ${error.message}`
      };
    }
  },

  examples: [
    {
      prompt: "What did I say about Docker configuration?",
      call: {
        query: "Docker configuration",
        limit: 10,
        summarize: false
      }
    },
    {
      prompt: "Search my memories for anything related to project deadlines and summarize",
      call: {
        query: "project deadlines",
        limit: 15,
        summarize: true
      }
    },
    {
      prompt: "Do I have any procedural memories about setting up databases?",
      call: {
        query: "setting up databases",
        sector: "procedural",
        limit: 10
      }
    },
    {
      prompt: "What do I remember about my preferences for coding?",
      call: {
        query: "coding preferences",
        sector: "emotional",
        limit: 10,
        summarize: true
      }
    }
  ]
};
