from typing import Any, Dict, List
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("travel-rules-mcp")


@mcp.tool()
def get_travel_preferences() -> Dict[str, Any]:
    """
    Return travel preferences and safety rules for the demo.
    The AI should call this before building the itinerary.
    """
    return {
        "destination": "Paris, France",
        "trip_style": "relaxed",
        "budget_style": "moderate",
        "food_preferences": [
            "vegetarian-friendly",
            "casual restaurants",
            "good coffee",
            "local bakeries"
        ],
        "transport_preferences": [
            "walking",
            "metro",
            "avoid taxis unless necessary"
        ],
        "planning_rules": {
            "max_main_activities_per_day": 4,
            "minimum_buffer_minutes_between_major_activities": 30,
            "calendar_creation_requires_user_approval": True,
            "do_not_invite_anyone": True,
            "do_not_add_video_conferencing": True,
            "timezone": "Europe/Paris"
        }
    }


@mcp.tool()
def validate_itinerary(itinerary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate an itinerary against travel preferences and safety rules.
    """
    warnings: List[str] = []
    passed_checks: List[str] = []

    days = itinerary.get("days", [])

    if not days:
        return {
            "valid": False,
            "warnings": ["No itinerary days were provided."],
            "passed_checks": [],
            "approval_required_before_calendar_creation": True,
            "message": "No itinerary found. Ask the model to create itinerary days first."
        }

    for day in days:
        date = day.get("date", "Unknown date")
        activities = day.get("activities", [])

        main_activity_types = {"sightseeing", "museum", "walk", "garden", "landmark"}
        main_activities = [
            activity for activity in activities
            if activity.get("type") in main_activity_types
        ]

        if len(main_activities) <= 4:
            passed_checks.append(f"{date}: relaxed activity count passed.")
        else:
            warnings.append(
                f"{date}: too many main activities. "
                f"Found {len(main_activities)}, max allowed is 4."
            )

        has_food_stop = any(
            activity.get("type") in {"meal", "coffee", "bakery"}
            for activity in activities
        )

        if has_food_stop:
            passed_checks.append(f"{date}: food or coffee stop included.")
        else:
            warnings.append(f"{date}: no food or coffee stop included.")

        has_buffer = any(
            activity.get("type") == "buffer"
            for activity in activities
        )

        if has_buffer:
            passed_checks.append(f"{date}: buffer time included.")
        else:
            warnings.append(f"{date}: no buffer time included.")

    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "passed_checks": passed_checks,
        "approval_required_before_calendar_creation": True,
        "message": (
            "Show this itinerary to the user and ask for explicit approval "
            "before creating Google Calendar events."
        )
    }


@mcp.tool()
def format_calendar_blocks(itinerary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert approved itinerary activities into calendar-ready event blocks.
    Only activities with create_calendar_event=true are returned.
    """
    calendar_events = []

    for day in itinerary.get("days", []):
        for activity in day.get("activities", []):
            if activity.get("create_calendar_event", False):
                calendar_events.append({
                    "title": f"Paris Trip - {activity.get('name')}",
                    "start": activity.get("start"),
                    "end": activity.get("end"),
                    "timezone": "Europe/Paris",
                    "description": activity.get("description", ""),
                    "location": activity.get("location", ""),
                    "attendees": [],
                    "add_video_conferencing": False
                })

    return {
        "calendar_events": calendar_events,
        "event_count": len(calendar_events),
        "safety_note": (
            "Create these events only after explicit user approval. "
            "Do not invite anyone. Do not add video conferencing."
        )
    }


if __name__ == "__main__":
    mcp.run()
