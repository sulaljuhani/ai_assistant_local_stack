/**
 * AI Stack - AnythingLLM Custom Skill
 * Create Task
 *
 * Allows the AI to create tasks in the AI Stack system.
 */

module.exports = {
  name: "create-task",
  description: "Creates a task with a title, description, and optional due date. Use this when the user wants to add something to their todo list.",

  parameters: {
    title: {
      type: "string",
      description: "The task title or what needs to be done",
      required: true
    },
    description: {
      type: "string",
      description: "Additional details about the task (optional)",
      required: false
    },
    status: {
      type: "string",
      description: "Task status: todo, in_progress, or done (default: todo)",
      required: false,
      enum: ["todo", "in_progress", "done"]
    },
    priority: {
      type: "string",
      description: "Priority level: low, medium, or high (default: medium)",
      required: false,
      enum: ["low", "medium", "high"]
    },
    due_date: {
      type: "string",
      description: "When the task is due in YYYY-MM-DD format (optional)",
      required: false
    },
    category: {
      type: "string",
      description: "Category name (default: General)",
      required: false
    },
    parent_task_id: {
      type: "string",
      description: "Parent task ID for subtasks (optional)",
      required: false
    }
  },

  async handler({ title, description, status = "todo", priority = "medium", due_date, category = "General", parent_task_id }) {
    const N8N_WEBHOOK = process.env.N8N_WEBHOOK || "http://n8n-ai-stack:5678/webhook/create-task";

    try {
      const response = await fetch(N8N_WEBHOOK, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          title,
          description,
          status,
          priority,
          due_date,
          category,
          parent_task_id
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        const dueStr = due_date ? ` (due: ${due_date})` : "";
        return {
          success: true,
          message: `✅ Task created: "${title}"${dueStr}`,
          task: result.task
        };
      } else {
        throw new Error(result.error || "Failed to create task");
      }

    } catch (error) {
      return {
        success: false,
        error: `Failed to create task: ${error.message}`
      };
    }
  },

  examples: [
    {
      prompt: "Add a task to fix the Docker configuration",
      call: {
        title: "Fix Docker configuration",
        description: "Update docker-compose.yml with new network settings",
        priority: "high",
        category: "DevOps"
      }
    },
    {
      prompt: "I need to finish the project report by Friday",
      call: {
        title: "Finish project report",
        due_date: "2025-11-22",
        priority: "high",
        category: "Work"
      }
    },
    {
      prompt: "Add 'Buy groceries' to my todo list",
      call: {
        title: "Buy groceries",
        priority: "medium",
        category: "Personal"
      }
    }
  ]
};
