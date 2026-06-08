# AI Travel Planner with MCP

A practical demo showing how **AI Agents** use **MCP servers** to connect to real tools, apply custom rules, and take action safely.

This demo is designed for a YouTube walkthrough.

The agent plans a relaxed 2-day Paris trip using:

1. **Google Maps MCP**  
   Finds real places, restaurants, routes, and travel time.

2. **Custom Travel Rules MCP Server**  
   A Python MCP server that applies user preferences, validates the itinerary, and formats calendar blocks.

3. **Google Calendar MCP**  
   Creates approved calendar events after user confirmation.

The goal is to show the difference between a chatbot and an AI agent.

> A chatbot gives an answer.  
> An MCP-powered agent uses tools.

---

## Demo Architecture

```
User
  ↓
AI Host / MCP Client
  ↓
Google Maps MCP
  → real places, routes, food stops, travel time
  ↓
Custom Travel Rules MCP
  → preferences, validation, approval guardrails
  ↓
AI Agent
  → creates itinerary
  ↓
Approval Gate
  → user reviews and approves
  ↓
Google Calendar MCP
  → creates calendar events
```

The safe agent pattern:

```
Read → Plan → Validate → Ask → Act
```

---

## What This Demo Proves

This demo shows how MCP can turn a chatbot into an agent.

The agent can:

* Use real-world travel context from Google Maps
* Apply custom travel rules through your own MCP server
* Validate the plan before taking action
* Ask for approval before modifying Google Calendar
* Create structured calendar events after approval

The official MCP Python SDK supports building MCP servers with `FastMCP`, including tools that can be exposed to MCP-compatible clients. ([GitHub](https://github.com/modelcontextprotocol/python-sdk))

---

## Project Structure

```
mcp-travel-agent-demo/
  custom-travel-rules-mcp/
    travel_rules_server.py
    requirements.txt
  prompts/
    01-plan-trip.txt
    02-approve-calendar.txt
    03-cleanup-events.txt
  .vscode/
    mcp.json
  README.md
```

---

## Prerequisites

Install:

```bash
python3 --version
node --version
npm --version
gcloud --version
```

Recommended versions:

```
Python 3.10+
Node.js 18+
npm
Google Cloud CLI
An MCP-compatible client
```

You also need an MCP-compatible AI client such as:

* Claude Desktop / Claude.ai with MCP connectors
* VS Code with MCP configuration
* Google Antigravity
* Another client that supports local stdio MCP servers and remote HTTP MCP servers

Google Maps Grounding Lite exposes an MCP endpoint at:

```
https://mapstools.googleapis.com/mcp
```

Google's Maps MCP reference lists tools such as `search_places`, `lookup_weather`, `compute_routes`, and `resolve_names`.

Google Calendar MCP uses:

```
https://calendarmcp.googleapis.com/mcp/v1
```

Calendar MCP may require Google Workspace Developer Preview access, Google Cloud API enablement, and OAuth setup.

---

## 1. Clone or Create the Project

```bash
mkdir mcp-travel-agent-demo
cd mcp-travel-agent-demo
mkdir custom-travel-rules-mcp
mkdir prompts
mkdir -p .vscode
```

---

## 2. Build the Custom MCP Server

Go into the custom MCP server folder:

```bash
cd custom-travel-rules-mcp
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install "mcp[cli]"
```

Create `requirements.txt`:

```bash
cat > requirements.txt << 'EOF'
mcp[cli]
EOF
```

Create the server file:

```bash
touch travel_rules_server.py
```

Paste this code into `travel_rules_server.py`:

```python
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
```

---

## 3. Test the Custom MCP Server

Run:

```bash
python travel_rules_server.py
```

The process may appear to hang. That is normal.

This MCP server runs over stdio and waits for an MCP client to call it.

Stop it with:

```bash
CTRL + C
```

Return to the project root:

```bash
cd ..
```

Get your absolute path:

```bash
pwd
```

Example:

```
/Users/sourabh/mcp-travel-agent-demo
```

You will need this path in the MCP config.

---

## 4. Configure MCP Servers

Create the MCP config file:

```bash
touch .vscode/mcp.json
```

Open it:

```bash
code .vscode/mcp.json
```

Paste this example:

```json
{
  "servers": {
    "travel-rules": {
      "command": "/ABSOLUTE/PATH/mcp-travel-agent-demo/custom-travel-rules-mcp/.venv/bin/python",
      "args": [
        "/ABSOLUTE/PATH/mcp-travel-agent-demo/custom-travel-rules-mcp/travel_rules_server.py"
      ]
    },
    "google-maps": {
      "type": "http",
      "url": "https://mapstools.googleapis.com/mcp"
    },
    "google-calendar": {
      "type": "http",
      "url": "https://calendarmcp.googleapis.com/mcp/v1"
    }
  }
}
```

Replace:

```
/ABSOLUTE/PATH/
```

with your real local path.

Example for macOS:

```json
{
  "servers": {
    "travel-rules": {
      "command": "/Users/sourabh/mcp-travel-agent-demo/custom-travel-rules-mcp/.venv/bin/python",
      "args": [
        "/Users/sourabh/mcp-travel-agent-demo/custom-travel-rules-mcp/travel_rules_server.py"
      ]
    },
    "google-maps": {
      "type": "http",
      "url": "https://mapstools.googleapis.com/mcp"
    },
    "google-calendar": {
      "type": "http",
      "url": "https://calendarmcp.googleapis.com/mcp/v1"
    }
  }
}
```

> Note: MCP config format can differ slightly across clients. VS Code uses `.vscode/mcp.json` with a `servers` object. Some other clients may use `mcpServers`.

---

## 5. Google Calendar MCP Setup

Google Calendar MCP may require:

* Google Cloud project
* Calendar API enabled
* Calendar MCP API enabled
* OAuth consent screen
* OAuth client ID and secret
* MCP-compatible client that supports remote OAuth MCP servers

Set your Google Cloud project:

```bash
gcloud init
gcloud config set project YOUR_PROJECT_ID
```

Enable Google Calendar API:

```bash
gcloud services enable calendar-json.googleapis.com --project=YOUR_PROJECT_ID
```

Enable Google Calendar MCP API:

```bash
gcloud services enable calendarmcp.googleapis.com --project=YOUR_PROJECT_ID
```

Then configure OAuth in Google Cloud Console:

```
Google Auth Platform
  → Branding
  → Get Started
```

Create an OAuth client:

```
Google Auth Platform
  → Clients
  → Create Client
```

For Claude custom connector setup, Google's Calendar MCP guide lists this redirect URI:

```
https://claude.ai/api/mcp/auth_callback
```

Keep your OAuth client secret private. Do not commit secrets to GitHub.

---

## 6. Test Each MCP Server

### Test Custom Travel Rules MCP

Ask your AI client:

```
Use the travel-rules MCP server.

Call get_travel_preferences and summarize my travel rules.
```

Expected output:

```
Your travel style is relaxed.
You prefer vegetarian-friendly casual food.
You prefer walking and metro.
You want no more than 4 main activities per day.
Calendar creation requires approval.
Timezone is Europe/Paris.
```

---

### Test Google Maps MCP

Ask:

```
Use Google Maps MCP.

Search for:
1. Eiffel Tower in Paris
2. Louvre Museum in Paris
3. Vegetarian-friendly casual restaurants near Le Marais, Paris
```

Then ask:

```
Use Google Maps MCP.

Compute a walking route from Eiffel Tower, Paris to Luxembourg Gardens, Paris.
```

---

### Test Google Calendar MCP

Ask:

```
Use Google Calendar MCP.

List my events for tomorrow.
```

Do not create events yet. Start with read-only testing.

---

## 7. Demo Prompts

Create prompt files in the `prompts/` directory:

```bash
touch prompts/01-plan-trip.txt
touch prompts/02-approve-calendar.txt
touch prompts/03-cleanup-events.txt
```

---

### `prompts/01-plan-trip.txt`

```
You are my AI travel planner.

Use these MCP servers:
1. Google Maps MCP for real places, routes, food stops, and travel time.
2. travel-rules MCP for my travel preferences, itinerary validation, and calendar block formatting.

Plan a relaxed 2-day Paris weekend trip.

Trip details:
- Destination: Paris, France
- Trip dates: July 18 to July 20, 2026
- Arrival: Friday, July 18 at 7:00 PM
- Departure: Sunday, July 20 at 6:00 PM
- Food: vegetarian-friendly, casual restaurants, good coffee
- Pace: relaxed, not rushed
- Activities: 3 to 4 main activities per day
- Transport: prefer walking and metro, avoid taxis

Use Google Maps MCP to:
- find real attractions
- group attractions by area
- suggest vegetarian-friendly food stops
- estimate walking or route time between key places

Use travel-rules MCP to:
- get my travel preferences
- validate the itinerary
- prepare calendar-ready blocks

Important:
Do not create Google Calendar events yet.

First show me:
1. The itinerary
2. Why you grouped places this way
3. Travel time between major stops
4. Food suggestions
5. Validation result from travel-rules MCP
6. The calendar blocks you plan to create

Then ask for my approval.
```

---

### `prompts/02-approve-calendar.txt`

```
Approved.

Use travel-rules MCP to format the final calendar blocks.

Then use Google Calendar MCP to create the approved events.

Calendar rules:
- Use Europe/Paris timezone.
- Use the title format: Paris Trip - [Activity Name]
- Do not invite anyone.
- Do not add video conferencing.
- Add a short description to each event.
- Create events only for main activities, meal breaks, and travel buffers.

After creating the events, summarize:
1. Event title
2. Date
3. Start and end time
4. Location
```

---

### `prompts/03-cleanup-events.txt`

```
Use Google Calendar MCP.

Find all calendar events with titles starting with "Paris Trip -" between July 18, 2026 and July 20, 2026.

Show me the list first.

Do not delete anything until I approve.
```

After the AI lists the events:

```
Approved. Delete those demo events.
```

---

## 8. Expected Demo Output

The agent should produce an itinerary similar to:

```
Saturday:
9:30 AM - Montmartre Morning Walk
11:00 AM - Coffee Stop
12:00 PM - Travel Buffer
12:30 PM - Lunch
2:30 PM - Louvre Museum
5:30 PM - Seine River Walk
7:30 PM - Dinner near Le Marais

Sunday:
9:30 AM - Eiffel Tower Area
11:30 AM - Luxembourg Gardens
1:00 PM - Lunch
2:30 PM - Le Marais Walk
4:00 PM - Departure Buffer
6:00 PM - Departure
```

It should also show:

```
Validation result:
- Relaxed activity count passed
- Food or coffee stop included
- Buffer time included
- Approval required before calendar creation
```

After approval, it should create calendar events such as:

```
Paris Trip - Montmartre Morning
Paris Trip - Louvre Museum
Paris Trip - Seine River Walk
Paris Trip - Eiffel Tower Area
Paris Trip - Luxembourg Gardens
Paris Trip - Le Marais Walk
Paris Trip - Departure Buffer
```

---

## 9. Recording Flow

Use this sequence for the video:

### Scene 1: Explain the Architecture

```
Google Maps MCP gives real-world context.
Custom Travel Rules MCP gives policy and guardrails.
Google Calendar MCP performs the final action.
```

### Scene 2: Show the Custom MCP Server Code

Explain the three tools:

```
get_travel_preferences()
validate_itinerary()
format_calendar_blocks()
```

### Scene 3: Show MCP Config

Show how the AI client connects to:

```
travel-rules
google-maps
google-calendar
```

### Scene 4: Test Custom MCP

Ask the agent to call:

```
get_travel_preferences
```

### Scene 5: Run the Planning Prompt

Paste:

```
prompts/01-plan-trip.txt
```

### Scene 6: Show Approval Gate

Point out:

```
The agent has not created calendar events yet.
It is waiting for approval.
```

### Scene 7: Approve Calendar Creation

Paste:

```
prompts/02-approve-calendar.txt
```

### Scene 8: Show Calendar Events

Open Google Calendar and show the created blocks.

### Scene 9: Cleanup

Use:

```
prompts/03-cleanup-events.txt
```

---

## 10. Troubleshooting

### Custom MCP server does not start

Check that the virtual environment exists:

```bash
ls custom-travel-rules-mcp/.venv/bin/python
```

Check that the server runs:

```bash
cd custom-travel-rules-mcp
source .venv/bin/activate
python travel_rules_server.py
```

If it waits without output, that is normal. It is waiting for an MCP client.

---

### MCP client cannot find the server

Use absolute paths. Do not use `~`.

Bad:

```json
"command": "~/mcp-travel-agent-demo/.venv/bin/python"
```

Good:

```json
"command": "/Users/sourabh/mcp-travel-agent-demo/custom-travel-rules-mcp/.venv/bin/python"
```

---

### Agent ignores the custom MCP server

Use a stricter prompt:

```
Before creating the itinerary, call get_travel_preferences from travel-rules MCP.

After creating the itinerary, call validate_itinerary from travel-rules MCP.

Do not proceed to Google Calendar unless validate_itinerary says approval is required and I approve.
```

---

### Agent creates calendar events too early

Add this to the prompt:

```
Calendar creation is forbidden until I explicitly say: Approved.
```

---

### Google Calendar MCP does not connect

Possible causes:

```
Calendar MCP API not enabled
OAuth consent screen not configured
OAuth redirect URI wrong
Client ID or secret wrong
MCP client does not support remote OAuth MCP servers
Developer Preview access not enabled
```

Fallback:

```
Use Google Maps MCP + custom travel-rules MCP live.
Show Calendar MCP setup as the final step.
Or replace Calendar MCP with a local mock calendar MCP server.
```

---

## 11. Safety Notes

This demo uses an approval gate. That matters.

The agent should not create calendar events immediately.

Safe MCP workflow:

```
Read first.
Plan second.
Validate third.
Ask for approval.
Act only after approval.
```

Do not give agents broad access by default.

Use:

* Least privilege
* Approval gates
* OAuth scopes
* Audit logs
* Read-only testing first
* No secrets committed to GitHub

---

## 12. Key Takeaway

MCP is not just a tool-calling feature.

It is a connection layer for AI agents.

In this demo:

```
Google Maps MCP = real-world context
Custom MCP server = business logic and guardrails
Google Calendar MCP = controlled action
```

The pattern is:

```
Context → Policy → Action
```

That is how MCP turns a chatbot into an AI agent.

---

## References

* [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — The official Python implementation of MCP, including `FastMCP`.
* [Google Maps Grounding Lite MCP](https://www.google.com/) — Managed MCP endpoint for Maps tools such as places, weather, and routes.
* Google Calendar MCP — Remote MCP server for calendar tools such as listing and creating events. Check Google's latest Calendar MCP docs before recording because preview access and setup requirements may change.
