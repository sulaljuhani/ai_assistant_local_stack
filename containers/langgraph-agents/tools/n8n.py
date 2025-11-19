"""
n8n webhook integration tools.
"""

from typing import Dict, Any, Optional
import httpx
from langchain_core.tools import tool
from config import settings
from utils.logging import get_logger

logger = get_logger(__name__)


@tool
async def trigger_n8n_workflow(
    workflow_name: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Trigger an n8n workflow via webhook.

    Args:
        workflow_name: Name of the workflow
        payload: Data to send to workflow

    Returns:
        Workflow response
    """
    url = f"{settings.n8n_base_url}{settings.n8n_webhook_path}/{workflow_name}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Triggered n8n workflow: {workflow_name}")
            return result
    except Exception as e:
        logger.error(f"Error triggering n8n workflow {workflow_name}: {e}")
        return {"error": str(e)}


@tool
async def log_food_with_embedding(
    user_id: str,
    food_name: str,
    food_type: str,
    rating: Optional[int] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log food entry and trigger embedding generation in n8n.

    This combines DB logging with vector embedding generation.

    Args:
        user_id: User identifier
        food_name: Food name/description
        food_type: Type of meal
        rating: Optional rating
        notes: Optional notes

    Returns:
        Result from n8n workflow
    """
    payload = {
        "user_id": user_id,
        "food_name": food_name,
        "food_type": food_type,
        "rating": rating,
        "notes": notes
    }

    return await trigger_n8n_workflow("log-food", payload)
