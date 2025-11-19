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
    const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8080";

    // Map source to API endpoint
    const endpoints = {
      chatgpt: `${API_URL}/api/import/chatgpt`,
      claude: `${API_URL}/api/import/claude`,
      gemini: `${API_URL}/api/import/gemini`
    };

    const endpoint = endpoints[source];
    if (!endpoint) {
      return {
        success: false,
        error: `Unknown source: ${source}. Must be one of: chatgpt, claude, gemini`
      };
    }

    try {
      // Read file from disk (Node.js environment)
      const fs = require('fs');
      const path = require('path');

      if (!fs.existsSync(file_path)) {
        throw new Error(`File not found: ${file_path}`);
      }

      // Read file content
      const fileBuffer = fs.readFileSync(file_path);
      const fileName = path.basename(file_path);

      // Create form data for multipart upload
      const FormData = require('form-data');
      const formData = new FormData();
      formData.append('file', fileBuffer, fileName);
      formData.append('user_id', process.env.USER_ID || 'anythingllm');
      formData.append('default_salience', '0.3');

      const response = await fetch(endpoint, {
        method: "POST",
        body: formData,
        headers: formData.getHeaders()
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const result = await response.json();

      if (result.success) {
        const convCount = result.conversations_imported || 0;
        const msgCount = result.messages_imported || 0;

        return {
          success: true,
          message: `✅ Successfully imported ${convCount} conversations (${msgCount} messages) from ${source}!\n\nAll messages have been stored as memories and are now searchable.`,
          conversations_imported: convCount,
          messages_imported: msgCount,
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
