/**
 * AnythingLLM Custom Skill: Create Reminder
 * Creates a new reminder in the AI Stack system
 */

module.exports.runtime = {
  handler: async function({ title, remind_at, priority, category }) {
    try {
      const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8000";
      const USER_ID = process.env.USER_ID || "00000000-0000-0000-0000-000000000001";

      if (!title || title.trim() === "") {
        return "Please provide a reminder title.";
      }

      if (!remind_at) {
        return "Please specify when you want to be reminded (date and time).";
      }

      const reminderData = {
        title: title.trim(),
        remind_at: remind_at,
        priority: priority || "medium",
        category: category || "General",
        user_id: USER_ID
      };

      const response = await fetch(`${API_URL}/api/reminders/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(reminderData)
      });

      if (!response.ok) {
        const errorText = await response.text();
        return `Failed to create reminder: API returned ${response.status}. Please check that langgraph-agents service is running.`;
      }

      const result = await response.json();
      const remindTime = new Date(remind_at).toLocaleString();
      return `⏰ Reminder set: "${title}" at ${remindTime}`;

    } catch (error) {
      this.logger(`Error creating reminder: ${error.message}`);
      return `Error creating reminder: ${error.message}`;
    }
  }
};
