/**
 * AnythingLLM Custom Skill: Create Event
 * Creates a new calendar event in the AI Stack system
 */

module.exports.runtime = {
  handler: async function({ title, start_time, end_time, location, category }) {
    try {
      const API_URL = process.env.LANGGRAPH_API_URL || "http://langgraph-agents:8000";
      const USER_ID = process.env.USER_ID || "00000000-0000-0000-0000-000000000001";

      if (!title || title.trim() === "") {
        return "Please provide an event title.";
      }

      if (!start_time) {
        return "Please specify when the event starts.";
      }

      if (!end_time) {
        return "Please specify when the event ends.";
      }

      const eventData = {
        title: title.trim(),
        start_time: start_time,
        end_time: end_time,
        category: category || "General",
        user_id: USER_ID
      };

      if (location) {
        eventData.location = location;
      }

      const response = await fetch(`${API_URL}/api/events/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(eventData)
      });

      if (!response.ok) {
        const errorText = await response.text();
        return `Failed to create event: API returned ${response.status}. Please check that langgraph-agents service is running.`;
      }

      const result = await response.json();
      const startDate = new Date(start_time).toLocaleString();
      const locationInfo = location ? ` at ${location}` : "";
      return `📅 Event created: "${title}" on ${startDate}${locationInfo}`;

    } catch (error) {
      this.logger(`Error creating event: ${error.message}`);
      return `Error creating event: ${error.message}`;
    }
  }
};
