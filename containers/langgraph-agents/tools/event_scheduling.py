"""
Scheduling helper tools for finding available time slots.

Provides smart scheduling assistance and conflict checking.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from langchain_core.tools import tool
from utils.db import get_db_pool
from utils.logging import get_logger

logger = get_logger(__name__)

USER_ID = "00000000-0000-0000-0000-000000000001"


def is_business_hours(dt: datetime, start_hour: int = 9, end_hour: int = 17) -> bool:
    """Check if datetime is within business hours."""
    return start_hour <= dt.hour < end_hour and dt.weekday() < 5  # Mon-Fri


@tool
async def find_available_slots(
    start_date: str,
    end_date: str,
    duration_minutes: int,
    user_id: str = USER_ID,
    business_hours_only: bool = True,
    business_start_hour: int = 9,
    business_end_hour: int = 17
) -> List[Dict[str, str]]:
    """
    Find available time slots in the calendar.

    Args:
        start_date: Start of search period (ISO format)
        end_date: End of search period (ISO format)
        duration_minutes: Required slot duration in minutes
        user_id: User identifier
        business_hours_only: Only search during business hours (default True)
        business_start_hour: Business day start (default 9)
        business_end_hour: Business day end (default 17)

    Returns:
        List of available time slots with start and end times
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            events = await conn.fetch(
                """
                SELECT start_time, end_time
                FROM events
                WHERE user_id = $1
                  AND start_time >= $2
                  AND start_time < $3
                  AND status != 'cancelled'
                ORDER BY start_time
                """,
                user_id, start_date, end_date
            )

        busy_slots = []
        for event in events:
            busy_slots.append({
                "start": event["start_time"],
                "end": event["end_time"]
            })

        available = []
        current = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        slot_duration = timedelta(minutes=duration_minutes)

        while current + slot_duration <= end:
            if business_hours_only and not is_business_hours(current, business_start_hour, business_end_hour):
                current += timedelta(minutes=30)
                continue

            slot_end = current + slot_duration
            is_available = True

            for busy in busy_slots:
                if not (slot_end <= busy["start"] or current >= busy["end"]):
                    is_available = False
                    break

            if is_available:
                available.append({
                    "start": current.isoformat(),
                    "end": slot_end.isoformat()
                })

            current += timedelta(minutes=30)

        logger.info(f"Found {len(available)} available slots")
        return available

    except Exception as e:
        logger.error(f"Error finding available slots: {e}")
        return []


@tool
async def suggest_meeting_times(
    duration_minutes: int,
    user_id: str = USER_ID,
    days_ahead: int = 7,
    preferred_time: str = "morning",
    max_suggestions: int = 5
) -> List[Dict[str, Any]]:
    """
    Suggest optimal meeting times based on calendar availability.

    Args:
        duration_minutes: Meeting duration in minutes
        user_id: User identifier
        days_ahead: How many days to look ahead (default 7)
        preferred_time: Preference (morning, afternoon, anytime)
        max_suggestions: Maximum suggestions to return

    Returns:
        List of suggested time slots with reasoning
    """
    start_date = datetime.now().isoformat()
    end_date = (datetime.now() + timedelta(days=days_ahead)).isoformat()

    available_slots = await find_available_slots(
        start_date=start_date,
        end_date=end_date,
        duration_minutes=duration_minutes,
        user_id=user_id,
        business_hours_only=True
    )

    if not available_slots:
        return []

    scored_slots = []

    for slot in available_slots:
        slot_start = datetime.fromisoformat(slot["start"])
        hour = slot_start.hour
        score = 0
        reasons = []

        if preferred_time == "morning" and 9 <= hour < 12:
            score += 10
            reasons.append("Morning slot as preferred")
        elif preferred_time == "afternoon" and 13 <= hour < 17:
            score += 10
            reasons.append("Afternoon slot as preferred")

        if hour < 9 or hour >= 16:
            score -= 5
            reasons.append("Outside prime hours")

        if slot_start.weekday() in [1, 2, 3]:
            score += 5
            reasons.append("Mid-week timing")

        scored_slots.append({
            "start": slot["start"],
            "end": slot["end"],
            "score": score,
            "day_of_week": slot_start.strftime("%A"),
            "time_of_day": "morning" if hour < 12 else "afternoon",
            "reasons": reasons
        })

    scored_slots.sort(key=lambda x: x["score"], reverse=True)

    logger.info(f"Generated {len(scored_slots[:max_suggestions])} meeting suggestions")
    return scored_slots[:max_suggestions]


@tool
async def bulk_check_conflicts(
    proposed_slots: List[Dict[str, str]],
    user_id: str = USER_ID
) -> List[Dict[str, Any]]:
    """
    Check multiple proposed time slots for conflicts.

    Useful for meeting polls or finding which times work.

    Args:
        proposed_slots: List of slots with start and end times
        user_id: User identifier

    Example:
        proposed_slots = [
            {"start": "2025-01-15 09:00", "end": "2025-01-15 10:00"},
            {"start": "2025-01-15 14:00", "end": "2025-01-15 15:00"},
        ]

    Returns:
        List of results showing availability and conflicts for each slot
    """
    pool = await get_db_pool()

    try:
        results = []

        async with pool.acquire() as conn:
            for idx, slot in enumerate(proposed_slots):
                start_time = slot["start"]
                end_time = slot["end"]

                conflicts = await conn.fetch(
                    """
                    SELECT id, title, start_time, end_time
                    FROM events
                    WHERE user_id = $1
                      AND status != 'cancelled'
                      AND (
                          (start_time <= $2 AND end_time > $2)
                          OR (start_time < $3 AND end_time >= $3)
                          OR (start_time >= $2 AND end_time <= $3)
                      )
                    """,
                    user_id, start_time, end_time
                )

                conflict_list = []
                for conflict in conflicts:
                    conflict_list.append({
                        "id": str(conflict["id"]),
                        "title": conflict["title"],
                        "start": conflict["start_time"].isoformat(),
                        "end": conflict["end_time"].isoformat()
                    })

                results.append({
                    "slot_index": idx,
                    "proposed_start": start_time,
                    "proposed_end": end_time,
                    "available": len(conflict_list) == 0,
                    "conflict_count": len(conflict_list),
                    "conflicts": conflict_list
                })

        available_count = sum(1 for r in results if r["available"])
        logger.info(f"Checked {len(results)} slots: {available_count} available")

        return results

    except Exception as e:
        logger.error(f"Error checking bulk conflicts: {e}")
        return []


@tool
async def get_busy_free_times(
    start_date: str,
    end_date: str,
    user_id: str = USER_ID,
    granularity_minutes: int = 30
) -> Dict[str, List[Dict[str, str]]]:
    """
    Get busy and free time blocks for a date range.

    Similar to Google Calendar's free/busy view.

    Args:
        start_date: Start of period (ISO format)
        end_date: End of period (ISO format)
        user_id: User identifier
        granularity_minutes: Time block size (default 30)

    Returns:
        Dict with 'busy' and 'free' arrays of time blocks
    """
    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            events = await conn.fetch(
                """
                SELECT start_time, end_time, title
                FROM events
                WHERE user_id = $1
                  AND start_time >= $2
                  AND end_time <= $3
                  AND status != 'cancelled'
                ORDER BY start_time
                """,
                user_id, start_date, end_date
            )

        busy_blocks = []
        for event in events:
            busy_blocks.append({
                "start": event["start_time"].isoformat(),
                "end": event["end_time"].isoformat(),
                "title": event["title"]
            })

        free_blocks = []

        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        if not busy_blocks:
            free_blocks.append({
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat()
            })
        else:
            first_event_start = datetime.fromisoformat(busy_blocks[0]["start"])
            if start_dt < first_event_start:
                free_blocks.append({
                    "start": start_dt.isoformat(),
                    "end": first_event_start.isoformat()
                })

            for i in range(len(busy_blocks) - 1):
                current_end = datetime.fromisoformat(busy_blocks[i]["end"])
                next_start = datetime.fromisoformat(busy_blocks[i + 1]["start"])

                if current_end < next_start:
                    free_blocks.append({
                        "start": current_end.isoformat(),
                        "end": next_start.isoformat()
                    })

            last_event_end = datetime.fromisoformat(busy_blocks[-1]["end"])
            if last_event_end < end_dt:
                free_blocks.append({
                    "start": last_event_end.isoformat(),
                    "end": end_dt.isoformat()
                })

        result = {
            "period": {
                "start": start_date,
                "end": end_date
            },
            "busy": busy_blocks,
            "free": free_blocks,
            "summary": {
                "total_busy_blocks": len(busy_blocks),
                "total_free_blocks": len(free_blocks)
            }
        }

        logger.info(f"Generated busy/free report: {len(busy_blocks)} busy, {len(free_blocks)} free")
        return result

    except Exception as e:
        logger.error(f"Error getting busy/free times: {e}")
        return {"error": str(e), "busy": [], "free": []}
