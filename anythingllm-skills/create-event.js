/**
 * AI Stack - AnythingLLM Custom Skill
 * Create Event
 *
 * Allows the AI to create calendar events in the AI Stack system.
 */

module.exports = {
  name: "create-event",
  description: "Creates a calendar event with start and end times. Use this when the user mentions an appointment, meeting, or scheduled activity.",

  parameters: {
    title: {
      type: "string",
      description: "The event title or name",
      required: true
    },
    description: {
      type: "string",
      description: "Additional details about the event (optional)",
      required: false
    },
    start_time: {
      type: "string",
      description: "Event start time in ISO 8601 format (e.g., 2025-11-18T14:00:00Z)",
      required: true
    },
    end_time: {
      type: "string",
      description: "Event end time in ISO 8601 format (e.g., 2025-11-18T15:00:00Z)",
      required: true
    },
    location: {
      type: "string",
      description: "Event location (optional)",
      required: false
    },
    status: {
      type: "string",
      description: "Event status: scheduled, cancelled, or completed (default: scheduled)",
      required: false,
      enum: ["scheduled", "cancelled", "completed"]
    },
    category: {
      type: "string",
      description: "Category name (default: General)",
      required: false
    },
    external_calendar_id: {
      type: "string",
      description: "External calendar system ID (optional, for Google Calendar sync)",
      required: false
    }
  },

  async handler({ title, description, start_time, end_time, location, status = "scheduled", category = "General", external_calendar_id }) {
    const N8N_WEBHOOK = process.env.N8N_WEBHOOK || "http://n8n-ai-stack:5678/webhook/create-event";

    try {
      const response = await fetch(N8N_WEBHOOK, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          title,
          description,
          start_time,
          end_time,
          location,
          status,
          category,
          external_calendar_id
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        const locationStr = location ? ` at ${location}` : "";
        return {
          success: true,
          message: `📅 Event created: "${title}" from ${start_time} to ${end_time}${locationStr}`,
          event: result.event
        };
      } else {
        throw new Error(result.error || "Failed to create event");
      }

    } catch (error) {
      return {
        success: false,
        error: `Failed to create event: ${error.message}`
      };
    }
  },

  examples: [
    {
      prompt: "Schedule a team meeting tomorrow at 2 PM for 1 hour",
      call: {
        title: "Team Meeting",
        description: "Weekly team sync",
        start_time: "2025-11-19T14:00:00Z",
        end_time: "2025-11-19T15:00:00Z",
        category: "Work"
      }
    },
    {
      prompt: "I have a dentist appointment on Friday at 10 AM at Downtown Dental",
      call: {
        title: "Dentist Appointment",
        start_time: "2025-11-22T10:00:00Z",
        end_time: "2025-11-22T11:00:00Z",
        location: "Downtown Dental",
        category: "Health"
      }
    },
    {
      prompt: "Add my lunch meeting with John next Monday at noon at Cafe Roma",
      call: {
        title: "Lunch with John",
        start_time: "2025-11-25T12:00:00Z",
        end_time: "2025-11-25T13:00:00Z",
        location: "Cafe Roma",
        category: "Personal"
      }
    }
  ]
};
