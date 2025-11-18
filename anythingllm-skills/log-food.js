/**
 * AnythingLLM Custom Skill: Log Food
 * Track daily food consumption with AI-powered recommendations
 *
 * Schema: food_name (required), location (required: home/outside), preference (required: liked/disliked/favorite)
 * Optional: restaurant_name (required if location=outside), description, meal_type, ingredients, tags, calories, notes
 */

module.exports.runtime = {
  name: "log-food",
  description: "Log food you ate today. Required: food name, location (home/outside), preference (liked/disliked/favorite). If location is 'outside', restaurant name is required. Can handle multiple foods in one entry (e.g., 'pizza and pasta').",
  inputs: {
    food_name: {
      type: "string",
      description: "Name of the food. Can be multiple items (e.g., 'pizza and pasta', 'burger and fries'). Will be stored as one entry unless you explicitly ask for separate entries.",
      required: true
    },
    location: {
      type: "string",
      description: "Where you ate: 'home' or 'outside'",
      required: true
    },
    preference: {
      type: "string",
      description: "Your preference: 'liked', 'disliked', or 'favorite'",
      required: true
    },
    restaurant_name: {
      type: "string",
      description: "Restaurant name (REQUIRED if location='outside')",
      required: false
    },
    description: {
      type: "string",
      description: "Description of the food, how it tasted, etc.",
      required: false
    },
    meal_type: {
      type: "string",
      description: "Type of meal: 'breakfast', 'lunch', 'dinner', or 'snack'",
      required: false
    },
    ingredients: {
      type: "array",
      description: "Array of ingredients (e.g., ['chicken', 'rice', 'curry'])",
      required: false
    },
    tags: {
      type: "array",
      description: "Tags for categorization (e.g., ['spicy', 'healthy', 'italian'])",
      required: false
    },
    calories: {
      type: "number",
      description: "Approximate calories (if known)",
      required: false
    },
    notes: {
      type: "string",
      description: "Additional notes or thoughts about the meal",
      required: false
    },
    consumed_at: {
      type: "string",
      description: "When you ate it (ISO timestamp, defaults to now)",
      required: false
    }
  },
  handler: async function ({ food_name, location, preference, restaurant_name, description, meal_type, ingredients, tags, calories, notes, consumed_at }) {
    try {
      // Validate required fields
      if (!food_name || !location || !preference) {
        return {
          success: false,
          message: "❌ Missing required fields. Need: food_name, location (home/outside), preference (liked/disliked/favorite)"
        };
      }

      // Validate location
      if (!['home', 'outside'].includes(location.toLowerCase())) {
        return {
          success: false,
          message: "❌ Location must be 'home' or 'outside'"
        };
      }

      // Validate preference
      const validPreferences = ['liked', 'disliked', 'favorite'];
      if (!validPreferences.includes(preference.toLowerCase())) {
        return {
          success: false,
          message: "❌ Preference must be 'liked', 'disliked', or 'favorite'"
        };
      }

      // Validate restaurant_name if location is outside
      if (location.toLowerCase() === 'outside' && !restaurant_name) {
        return {
          success: false,
          message: "❌ Restaurant name is required when location is 'outside'"
        };
      }

      const N8N_WEBHOOK = process.env.N8N_WEBHOOK || "http://n8n-ai-stack:5678/webhook";

      const response = await fetch(`${N8N_WEBHOOK}/log-food`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          food_name,
          location: location.toLowerCase(),
          preference: preference.toLowerCase(),
          restaurant_name,
          description,
          meal_type: meal_type ? meal_type.toLowerCase() : null,
          ingredients: ingredients || [],
          tags: tags || [],
          calories,
          notes,
          consumed_at
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`n8n webhook failed: ${response.status} ${errorText}`);
      }

      const result = await response.json();

      // Build response message
      const prefEmoji = preference.toLowerCase() === 'favorite' ? '⭐' : preference.toLowerCase() === 'liked' ? '👍' : '👎';
      const locEmoji = location.toLowerCase() === 'home' ? '🏠' : '🍽️';

      let message = `✅ Logged "${food_name}" successfully! ${prefEmoji} ${locEmoji}`;

      if (location.toLowerCase() === 'outside' && restaurant_name) {
        message += `\n   Restaurant: ${restaurant_name}`;
      }

      message += '\n   This has been vectorized for future recommendations.';

      return {
        success: true,
        message,
        food_id: result.food_id,
        details: {
          location,
          preference,
          restaurant_name,
          meal_type
        }
      };
    } catch (error) {
      console.error("Error logging food:", error);
      return {
        success: false,
        error: error.message,
        message: "❌ Failed to log food. Please check n8n workflow and database connection."
      };
    }
  }
};
