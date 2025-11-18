/**
 * AI Stack - AnythingLLM Custom Skill
 * Import Chat History
 *
 * Allows the AI to trigger import of chat history exports from various services.
 */

module.exports = {
  name: "import-chat-history",
  description: "Imports chat history from ChatGPT, Claude, or Gemini exports. Use this when the user wants to import their conversation history from other AI platforms.",

  parameters: {
    source: {
      type: "string",
      description: "The source platform: chatgpt, claude, or gemini",
      required: true,
      enum: ["chatgpt", "claude", "gemini"]
    },
    file_path: {
      type: "string",
      description: "Absolute path to the export file on the server",
      required: true
    }
  },

  async handler({ source, file_path }) {
    // Map source to webhook endpoint
    const webhooks = {
      chatgpt: process.env.N8N_WEBHOOK_CHATGPT || "http://n8n-ai-stack:5678/webhook/import-chatgpt",
      claude: process.env.N8N_WEBHOOK_CLAUDE || "http://n8n-ai-stack:5678/webhook/import-claude",
      gemini: process.env.N8N_WEBHOOK_GEMINI || "http://n8n-ai-stack:5678/webhook/import-gemini"
    };

    const webhook = webhooks[source];
    if (!webhook) {
      return {
        success: false,
        error: `Unknown source: ${source}. Must be one of: chatgpt, claude, gemini`
      };
    }

    try {
      const response = await fetch(webhook, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          file_path
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        const count = result.conversations || 0;
        const status = result.status;

        if (status === "duplicate") {
          return {
            success: false,
            message: `⚠️ This ${source} export has already been imported. Duplicate detected.`,
            status: "duplicate"
          };
        }

        return {
          success: true,
          message: `✅ Successfully imported ${count} conversations from ${source}!\n\nAll messages have been stored as memories and are now searchable.`,
          conversations_imported: count,
          source: source
        };

      } else {
        throw new Error(result.error || result.message || "Failed to import chat history");
      }

    } catch (error) {
      return {
        success: false,
        error: `Failed to import ${source} history: ${error.message}`
      };
    }
  },

  examples: [
    {
      prompt: "Import my ChatGPT conversations from /mnt/user/appdata/ai_stack/imports/chatgpt-export.json",
      call: {
        source: "chatgpt",
        file_path: "/mnt/user/appdata/ai_stack/imports/chatgpt-export.json"
      }
    },
    {
      prompt: "Load my Claude conversation history from the exports folder",
      call: {
        source: "claude",
        file_path: "/mnt/user/appdata/ai_stack/imports/claude-conversations.json"
      }
    },
    {
      prompt: "Import Gemini chat history from my Google Takeout",
      call: {
        source: "gemini",
        file_path: "/mnt/user/appdata/ai_stack/imports/gemini-takeout.json"
      }
    }
  ],

  notes: [
    "Export files must be uploaded to the server first (e.g., /mnt/user/appdata/ai_stack/imports/)",
    "ChatGPT exports: Download from ChatGPT Settings > Data Export > conversations.json",
    "Claude exports: Download from Claude.ai account settings (format varies)",
    "Gemini exports: Use Google Takeout to export Bard/Gemini conversations",
    "Duplicate imports are detected via file hash and will be rejected",
    "All imported messages are automatically classified into memory sectors",
    "Large imports may take several minutes to process"
  ]
};
