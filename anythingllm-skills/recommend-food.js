/**
 * AnythingLLM Custom Skill: Get Food Recommendations
 * Get AI-powered food recommendations based on your history
 */

module.exports.runtime = {
  name: "recommend-food",
  description: "Get personalized food recommendations based on what you've eaten and liked/favorited. The AI will suggest foods you enjoyed but haven't eaten recently.",
  inputs: {
    query: {
      type: "string",
      description: "Optional search query to refine recommendations (e.g., 'something spicy', 'healthy lunch', 'comfort food')",
      required: false
    }
  },
  handler: async function ({ query }) {
    try {
      const N8N_WEBHOOK = process.env.N8N_WEBHOOK || "http://n8n-ai-stack:5678/webhook";

      const response = await fetch(`${N8N_WEBHOOK}/recommend-food`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query || "What should I eat that I liked but haven't had in a while?"
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`n8n webhook failed: ${response.status} ${errorText}`);
      }

      const result = await response.json();

      if (!result.recommendations || result.recommendations.length === 0) {
        return {
          success: true,
          message: "No recommendations found. Try logging more food entries first!",
          recommendations: []
        };
      }

      // Format recommendations nicely
      const formattedRecommendations = result.recommendations.map((food, index) => {
        const prefEmoji = food.preference === 'favorite' ? '⭐' : '👍';
        const locEmoji = food.location === 'home' ? '🏠' : '🍽️';

        const parts = [
          `${index + 1}. **${food.food_name}** ${prefEmoji} ${locEmoji}`,
          food.days_since_eaten ? `Last eaten: ${food.days_since_eaten} days ago` : null,
          food.restaurant_name ? `Restaurant: ${food.restaurant_name}` : null,
          food.description ? `\n   ${food.description}` : null,
          food.notes ? `\n   💭 ${food.notes}` : null
        ];
        return parts.filter(Boolean).join(' ');
      });

      return {
        success: true,
        message: `🍽️ Here are ${result.recommendations.length} recommendations based on foods you liked:\n\n${formattedRecommendations.join('\n\n')}`,
        recommendations: result.recommendations,
        count: result.recommendations.length
      };
    } catch (error) {
      console.error("Error getting food recommendations:", error);
      return {
        success: false,
        error: error.message,
        message: "❌ Failed to get recommendations. Please check n8n workflow and database connection."
      };
    }
  }
};
