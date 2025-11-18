/**
 * AI Stack - AnythingLLM Custom Skill
 * Store Memory
 *
 * Allows the AI to store important information as a memory for future retrieval.
 */

module.exports = {
  name: "store-memory",
  description: "Stores important information as a memory that can be retrieved later. Use this when the user shares important facts, preferences, or experiences that should be remembered.",

  parameters: {
    content: {
      type: "string",
      description: "The content to store as a memory - should be clear and descriptive",
      required: true
    },
    conversation_id: {
      type: "string",
      description: "Optional conversation identifier to group related memories",
      required: false
    },
    conversation_title: {
      type: "string",
      description: "Optional title for the conversation",
      required: false
    },
    source: {
      type: "string",
      description: "Source of the memory (default: chat)",
      required: false
    },
    salience_score: {
      type: "number",
      description: "Importance score from 0.0 to 1.0 (default: 0.5). Higher scores indicate more important memories.",
      required: false
    }
  },

  async handler({ content, conversation_id, conversation_title = "Untitled Conversation", source = "chat", salience_score = 0.5 }) {
    const N8N_WEBHOOK = process.env.N8N_WEBHOOK || "http://n8n-ai-stack:5678/webhook/store-chat-turn";

    // Validate salience score
    salience_score = Math.min(Math.max(salience_score, 0.0), 1.0);

    // Generate conversation ID if not provided
    if (!conversation_id) {
      conversation_id = `conv-${Date.now()}-${Math.random().toString(36).substring(7)}`;
    }

    try {
      const response = await fetch(N8N_WEBHOOK, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          content,
          conversation_id,
          conversation_title,
          source,
          salience_score
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        const sectors = result.sectors || [];
        return {
          success: true,
          message: `💾 Memory stored successfully!\nClassified as: ${sectors.join(", ")}\nImportance: ${(salience_score * 100).toFixed(0)}%`,
          memory_id: result.memory_id,
          sectors: sectors
        };
      } else {
        throw new Error(result.error || "Failed to store memory");
      }

    } catch (error) {
      return {
        success: false,
        error: `Failed to store memory: ${error.message}`
      };
    }
  },

  examples: [
    {
      prompt: "Remember that I prefer Python over JavaScript for backend development",
      call: {
        content: "User prefers Python over JavaScript for backend development",
        conversation_title: "Coding Preferences",
        salience_score: 0.8
      }
    },
    {
      prompt: "Store this: I fixed the Docker network issue by recreating the bridge network",
      call: {
        content: "Fixed Docker network issue by recreating the bridge network. Command used: docker network create ai-stack-network",
        conversation_title: "Docker Troubleshooting",
        salience_score: 0.7
      }
    },
    {
      prompt: "I learned that PostgreSQL connection pooling should be between 2-10 connections for this workload",
      call: {
        content: "PostgreSQL connection pooling optimal range: 2-10 connections for current AI Stack workload",
        conversation_title: "Database Optimization",
        salience_score: 0.6
      }
    },
    {
      prompt: "Remember: my morning standup is at 9:30 AM every weekday",
      call: {
        content: "Morning standup meeting scheduled at 9:30 AM every weekday",
        conversation_title: "Daily Schedule",
        salience_score: 0.7
      }
    }
  ]
};
