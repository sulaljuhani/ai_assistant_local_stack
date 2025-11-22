/**
 * AnythingLLM Custom Skill: Create Task
 * Creates a new task in the AI Stack system
 */

module.exports.runtime = {
  handler: async function({ title, priority, category, due_date }) {
    try {
      const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8000";
      const USER_ID = process.env.USER_ID || "00000000-0000-0000-0000-000000000001";

      if (!title || title.trim() === "") {
        return "Please provide a task title.";
      }

      const taskData = {
        title: title.trim(),
        priority: priority || "medium",
        category: category || "General",
        user_id: USER_ID
      };

      if (due_date) {
        taskData.due_date = due_date;
      }

      const response = await fetch(`${API_URL}/api/tasks/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(taskData)
      });

      if (!response.ok) {
        const errorText = await response.text();
        return `Failed to create task: API returned ${response.status}. Please check that langgraph-agents service is running.`;
      }

      const result = await response.json();
      const dueInfo = due_date ? ` (due: ${new Date(due_date).toLocaleDateString()})` : "";
      return `✅ Task created: "${title}"${dueInfo}`;

    } catch (error) {
      this.logger(`Error creating task: ${error.message}`);
      return `Error creating task: ${error.message}`;
    }
  }
};
