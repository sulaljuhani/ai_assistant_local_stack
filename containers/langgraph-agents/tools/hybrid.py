"""
Hybrid tools combining database queries and vector search.
"""

from typing import List, Dict, Any
from langchain_core.tools import tool
from .database import search_food_log, get_food_by_rating
from .vector import vector_search_foods
from utils.logging import get_logger

logger = get_logger(__name__)


@tool
async def get_food_recommendations(
    user_id: str,
    preferences: str,
    days_ago: int = 30,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get intelligent food recommendations using hybrid approach.

    Combines:
    1. Structured filters (rating, recency, variety)
    2. Semantic similarity (vector search)
    3. User preferences and history

    Args:
        user_id: User identifier
        preferences: User preference description (e.g., "haven't had in a while", "healthy options")
        days_ago: Days of history to consider
        limit: Maximum recommendations

    Returns:
        Recommendations with reasoning
    """
    try:
        # Step 1: Get highly rated foods from DB (structured)
        logger.info("Fetching highly rated foods from database")
        high_rated = await get_food_by_rating(
            user_id=user_id,
            min_rating=4,
            days_ago=days_ago,
            limit=limit * 2  # Get more for filtering
        )

        # Step 2: Vector search for semantic similarity
        logger.info("Performing vector search for similar foods")
        vector_results = await vector_search_foods(
            query=preferences,
            user_id=user_id,
            limit=limit,
            score_threshold=0.7
        )

        # Step 3: Merge and rank results
        # Create a scoring system combining both approaches
        recommendations = []

        # Add highly rated items with base score
        for food in high_rated:
            recommendations.append({
                "food_name": food["food_name"],
                "food_type": food["food_type"],
                "rating": food.get("rating"),
                "last_eaten": food.get("logged_at"),
                "score": food.get("rating", 0) / 5.0,  # Normalize rating to 0-1
                "source": "database",
                "reason": f"Highly rated ({food.get('rating')}/5)"
            })

        # Add vector results with semantic scores
        for food in vector_results:
            recommendations.append({
                "food_name": food["food_name"],
                "food_type": food["food_type"],
                "rating": food.get("rating"),
                "last_eaten": food.get("logged_at"),
                "score": food["score"],  # Already 0-1
                "source": "vector",
                "reason": f"Similar to preferences (match: {food['score']:.2%})"
            })

        # Deduplicate by food_name, keeping highest score
        unique_recommendations = {}
        for rec in recommendations:
            food_name = rec["food_name"]
            if food_name not in unique_recommendations or rec["score"] > unique_recommendations[food_name]["score"]:
                unique_recommendations[food_name] = rec

        # Sort by score descending
        final_recommendations = sorted(
            unique_recommendations.values(),
            key=lambda x: x["score"],
            reverse=True
        )[:limit]

        result = {
            "recommendations": final_recommendations,
            "total_found": len(final_recommendations),
            "criteria": {
                "preferences": preferences,
                "days_considered": days_ago,
                "min_rating": 4
            }
        }

        logger.info(f"Generated {len(final_recommendations)} hybrid recommendations")
        return result

    except Exception as e:
        logger.error(f"Error getting food recommendations: {e}")
        return {
            "recommendations": [],
            "total_found": 0,
            "error": str(e)
        }
