/**
 * AI Stack - AnythingLLM Custom Skill
 * Create Reminder
 *
 * Allows the AI to create reminders in the AI Stack system.
 */

module.exports = {
  name: "create-reminder",
  description: "Creates a reminder for a specific date and time. Use this when the user wants to be reminded about something.",

  parameters: {
    title: {
      type: "string",
      description: "The title or brief description of what to be reminded about",
      required: true
    },
    description: {
      type: "string",
      description: "Additional details about the reminder (optional)",
      required: false
    },
    remind_at: {
      type: "string",
      description: "When to trigger the reminder in ISO 8601 format (e.g., 2025-11-18T09:00:00Z)",
      required: true
    },
    priority: {
      type: "string",
      description: "Priority level: low, medium, or high (default: medium)",
      required: false,
      enum: ["low", "medium", "high"]
    },
    category: {
      type: "string",
      description: "Category name (default: General)",
      required: false
    }
  },

  async handler({ title, description, remind_at, priority = "medium", category = "General" }) {
    const N8N_WEBHOOK = process.env.N8N_WEBHOOK || "http://n8n-ai-stack:5678/webhook/create-reminder";

    try {
      const response = await fetch(N8N_WEBHOOK, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          title,
          description,
          remind_at,
          priority,
          category
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        return {
          success: true,
          message: `✅ Reminder created: "${title}" for ${remind_at}`,
          reminder: result.reminder
        };
      } else {
        throw new Error(result.error || "Failed to create reminder");
      }

    } catch (error) {
      return {
        success: false,
        error: `Failed to create reminder: ${error.message}`
      };
    }
  },

  examples: [
    {
      prompt: "Remind me to take medication at 9 AM tomorrow",
      call: {
        title: "Take medication",
        description: "Daily medication reminder",
        remind_at: "2025-11-19T09:00:00Z",
        priority: "high",
        category: "Health"
      }
    },
    {
      prompt: "Set a reminder for my dentist appointment on Friday at 2 PM",
      call: {
        title: "Dentist appointment",
        remind_at: "2025-11-22T14:00:00Z",
        priority: "medium",
        category: "Health"
      }
    }
  ]
};
