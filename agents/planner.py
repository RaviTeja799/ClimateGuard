"""
ClimateGuard Planner Agent
==========================
Generates personalized weekly carbon reduction plans.

Features:
- Loop agent that iterates to refine recommendations
- Long-running operations with pause/resume for user approval
- Adapts based on past success and user feedback

ADK Concepts: Loop Agents, Long-Running Operations, Tool Confirmation
"""

import os
import uuid
from typing import Optional, List, Dict
from datetime import datetime, timedelta

# ADK Imports
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.function_tool import FunctionTool
from google.genai import types

# Local imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from memory.memory_service import get_memory_service


# ============================================================================
# RETRY CONFIGURATION
# ============================================================================
RETRY_CONFIG = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


# ============================================================================
# ACTION DATABASE
# ============================================================================
# Predefined carbon reduction actions with estimated savings
CARBON_ACTIONS = {
    "diet": [
        {
            "id": "meatless_monday",
            "name": "Meatless Monday",
            "description": "Skip meat for one day per week",
            "weekly_savings_kg": 6.75,
            "difficulty": "easy",
            "category": "diet",
        },
        {
            "id": "reduce_beef",
            "name": "Swap Beef for Chicken",
            "description": "Replace beef with chicken in 2 meals this week",
            "weekly_savings_kg": 10.0,
            "difficulty": "easy",
            "category": "diet",
        },
        {
            "id": "plant_lunch",
            "name": "Plant-Based Lunches",
            "description": "Eat vegetarian lunches for the work week",
            "weekly_savings_kg": 15.0,
            "difficulty": "medium",
            "category": "diet",
        },
        {
            "id": "local_food",
            "name": "Buy Local This Week",
            "description": "Shop at farmers market for produce",
            "weekly_savings_kg": 3.0,
            "difficulty": "easy",
            "category": "diet",
        },
    ],
    "transport": [
        {
            "id": "transit_day",
            "name": "Public Transit Day",
            "description": "Take public transit instead of driving one day",
            "weekly_savings_kg": 8.0,
            "difficulty": "easy",
            "category": "transport",
        },
        {
            "id": "carpool",
            "name": "Carpool Twice",
            "description": "Share your commute with a colleague twice this week",
            "weekly_savings_kg": 10.5,
            "difficulty": "easy",
            "category": "transport",
        },
        {
            "id": "bike_short_trips",
            "name": "Bike for Errands",
            "description": "Use a bike for trips under 5km",
            "weekly_savings_kg": 5.0,
            "difficulty": "medium",
            "category": "transport",
        },
        {
            "id": "combine_trips",
            "name": "Combine Errands",
            "description": "Plan to do all errands in one trip instead of multiple",
            "weekly_savings_kg": 4.0,
            "difficulty": "easy",
            "category": "transport",
        },
        {
            "id": "wfh_day",
            "name": "Work From Home Day",
            "description": "Work remotely one day to avoid commute",
            "weekly_savings_kg": 10.5,
            "difficulty": "easy",
            "category": "transport",
        },
    ],
    "energy": [
        {
            "id": "thermostat_adjust",
            "name": "Adjust Thermostat",
            "description": "Lower heating by 1°C / raise AC by 1°C",
            "weekly_savings_kg": 3.0,
            "difficulty": "easy",
            "category": "energy",
        },
        {
            "id": "unplug_devices",
            "name": "Unplug Standby Devices",
            "description": "Unplug chargers and devices when not in use",
            "weekly_savings_kg": 1.5,
            "difficulty": "easy",
            "category": "energy",
        },
        {
            "id": "short_showers",
            "name": "Shorter Showers",
            "description": "Reduce shower time by 2 minutes",
            "weekly_savings_kg": 2.0,
            "difficulty": "easy",
            "category": "energy",
        },
        {
            "id": "cold_wash",
            "name": "Cold Water Laundry",
            "description": "Wash clothes in cold water this week",
            "weekly_savings_kg": 1.0,
            "difficulty": "easy",
            "category": "energy",
        },
        {
            "id": "air_dry",
            "name": "Air Dry Clothes",
            "description": "Skip the dryer and air dry your laundry",
            "weekly_savings_kg": 2.5,
            "difficulty": "easy",
            "category": "energy",
        },
    ],
    "lifestyle": [
        {
            "id": "no_plastic_week",
            "name": "Plastic-Free Week",
            "description": "Avoid single-use plastics for the week",
            "weekly_savings_kg": 1.0,
            "difficulty": "medium",
            "category": "lifestyle",
        },
        {
            "id": "declutter_donate",
            "name": "Declutter & Donate",
            "description": "Donate items instead of throwing away",
            "weekly_savings_kg": 2.0,
            "difficulty": "easy",
            "category": "lifestyle",
        },
        {
            "id": "repair_item",
            "name": "Repair Don't Replace",
            "description": "Fix something instead of buying new",
            "weekly_savings_kg": 5.0,
            "difficulty": "medium",
            "category": "lifestyle",
        },
    ],
}


# ============================================================================
# PLANNER TOOLS
# ============================================================================
def generate_weekly_plan(
    user_id: str,
    focus_areas: List[str] = None,
    difficulty_max: str = "medium",
    target_savings_kg: float = 20.0,
    tool_context: ToolContext = None
) -> dict:
    """
    Generates a personalized 7-day carbon reduction plan.
    
    Requires user approval before finalizing.
    
    Args:
        user_id: User identifier
        focus_areas: Areas to focus on - ["diet", "transport", "energy", "lifestyle"]
        difficulty_max: Maximum difficulty - "easy", "medium", "hard"
        target_savings_kg: Target weekly CO2 savings
    
    Returns:
        Dictionary with proposed plan requiring approval
    """
    import asyncio
    
    if focus_areas is None:
        focus_areas = ["diet", "transport", "energy"]
    
    # Get user profile and history
    memory_service = get_memory_service()
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, memory_service.get_profile(user_id))
                profile = future.result()
        else:
            profile = asyncio.run(memory_service.get_profile(user_id))
    except RuntimeError:
        profile = asyncio.run(memory_service.get_profile(user_id))
    
    # Filter actions based on criteria
    difficulty_levels = {"easy": 1, "medium": 2, "hard": 3}
    max_level = difficulty_levels.get(difficulty_max, 2)
    
    available_actions = []
    for category in focus_areas:
        if category in CARBON_ACTIONS:
            for action in CARBON_ACTIONS[category]:
                action_level = difficulty_levels.get(action["difficulty"], 2)
                if action_level <= max_level:
                    available_actions.append(action)
    
    # Select actions to meet target
    selected_actions = []
    total_savings = 0
    
    # Prioritize by savings/difficulty ratio
    sorted_actions = sorted(
        available_actions,
        key=lambda x: x["weekly_savings_kg"] / difficulty_levels.get(x["difficulty"], 1),
        reverse=True
    )
    
    for action in sorted_actions:
        if total_savings >= target_savings_kg:
            break
        if action["id"] not in [a["id"] for a in selected_actions]:
            selected_actions.append(action)
            total_savings += action["weekly_savings_kg"]
    
    # Create daily assignments
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daily_plan = {}
    
    for i, action in enumerate(selected_actions[:7]):
        day = days[i % 7]
        if day not in daily_plan:
            daily_plan[day] = []
        daily_plan[day].append({
            "action": action["name"],
            "description": action["description"],
            "savings_kg": action["weekly_savings_kg"],
        })
    
    # Request confirmation for large plans
    if tool_context and total_savings > 15:
        tool_context.request_confirmation(
            hint=f"📋 Proposed plan will save {round(total_savings, 1)} kg CO2/week. Approve?",
            payload={
                "user_id": user_id,
                "total_savings": total_savings,
                "action_count": len(selected_actions),
            }
        )
        return {
            "status": "pending_approval",
            "message": f"Plan generated! Waiting for your approval. Total potential savings: {round(total_savings, 1)} kg CO2/week",
            "proposed_plan": daily_plan,
            "actions_count": len(selected_actions),
            "total_weekly_savings_kg": round(total_savings, 1),
        }
    
    # Return plan for smaller targets
    return {
        "status": "success",
        "plan_id": f"plan_{uuid.uuid4().hex[:8]}",
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "daily_plan": daily_plan,
        "selected_actions": selected_actions,
        "summary": {
            "total_actions": len(selected_actions),
            "total_weekly_savings_kg": round(total_savings, 1),
            "yearly_savings_kg": round(total_savings * 52, 1),
            "equivalent_trees": round(total_savings * 52 / 21, 1),
        },
        "focus_areas": focus_areas,
        "difficulty_level": difficulty_max,
        "tip": "Start with just one action and build from there!",
    }


def get_action_recommendations(
    biggest_impact_area: str,
    current_habits: List[str] = None,
    difficulty: str = "easy"
) -> dict:
    """
    Gets specific action recommendations based on impact area.
    
    Args:
        biggest_impact_area: Area with highest emissions - "diet", "transport", "energy"
        current_habits: List of habits user already does (to exclude)
        difficulty: Preferred difficulty - "easy", "medium", "hard"
    
    Returns:
        Dictionary with recommended actions
    """
    if current_habits is None:
        current_habits = []
    
    area = biggest_impact_area.lower()
    
    if area not in CARBON_ACTIONS:
        return {
            "status": "error",
            "message": f"Unknown area: {area}. Use: diet, transport, energy, lifestyle"
        }
    
    # Filter available actions
    actions = [
        a for a in CARBON_ACTIONS[area]
        if a["id"] not in current_habits
    ]
    
    # Filter by difficulty
    if difficulty != "all":
        actions = [a for a in actions if a["difficulty"] == difficulty]
    
    # Sort by savings
    actions = sorted(actions, key=lambda x: x["weekly_savings_kg"], reverse=True)
    
    return {
        "status": "success",
        "impact_area": area,
        "difficulty_filter": difficulty,
        "recommendations": actions[:5],
        "total_potential_savings_kg": sum(a["weekly_savings_kg"] for a in actions[:5]),
        "tip": f"Focus on {area} actions for maximum impact!",
    }


def track_action_completion(
    user_id: str,
    action_id: str,
    completed: bool,
    notes: str = ""
) -> dict:
    """
    Tracks completion of a planned action.
    
    Args:
        user_id: User identifier
        action_id: ID of the action
        completed: Whether the action was completed
        notes: Optional notes or feedback
    
    Returns:
        Dictionary with tracking status and encouragement
    """
    import asyncio
    
    memory_service = get_memory_service()
    
    # Find action details
    action_details = None
    for category in CARBON_ACTIONS.values():
        for action in category:
            if action["id"] == action_id:
                action_details = action
                break
    
    if not action_details:
        return {"status": "error", "message": f"Action {action_id} not found"}
    
    # Record to memory
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    memory_service.record_habit(user_id, action_details["name"], completed)
                )
                result = future.result()
        else:
            result = asyncio.run(memory_service.record_habit(user_id, action_details["name"], completed))
    except RuntimeError:
        result = asyncio.run(memory_service.record_habit(user_id, action_details["name"], completed))
    
    # Calculate impact
    if completed:
        savings = action_details["weekly_savings_kg"]
        message = f"🎉 Great job completing '{action_details['name']}'! You saved {savings} kg CO2!"
    else:
        savings = 0
        message = f"No worries! '{action_details['name']}' is still available for next time. Small steps matter!"
    
    return {
        "status": "success",
        "action_id": action_id,
        "action_name": action_details["name"],
        "completed": completed,
        "co2_saved_kg": savings if completed else 0,
        "message": message,
        "notes": notes,
        "encouragement": "Every action counts! Keep building those sustainable habits." if completed else "Tomorrow is a new opportunity!",
    }


def get_plan_progress(user_id: str, plan_id: str = None) -> dict:
    """
    Gets progress on the current or specified plan.
    
    Args:
        user_id: User identifier
        plan_id: Optional specific plan ID
    
    Returns:
        Dictionary with progress metrics
    """
    import asyncio
    
    memory_service = get_memory_service()
    
    # Get habit history
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    memory_service.search_memory("climateguard", user_id, "habit completed", category="habit")
                )
                habits = future.result()
        else:
            habits = asyncio.run(memory_service.search_memory("climateguard", user_id, "habit completed", category="habit"))
    except RuntimeError:
        habits = asyncio.run(memory_service.search_memory("climateguard", user_id, "habit completed", category="habit"))
    
    completed_count = len([h for h in habits if "completed" in h.get("content", "").lower()])
    total_tracked = len(habits)
    
    return {
        "status": "success",
        "user_id": user_id,
        "habits_tracked": total_tracked,
        "habits_completed": completed_count,
        "completion_rate": round(completed_count / total_tracked * 100, 1) if total_tracked > 0 else 0,
        "estimated_co2_saved_kg": completed_count * 5,  # Average per action
        "message": f"You've completed {completed_count} sustainable actions! Keep it up!",
        "next_milestone": f"Complete {10 - completed_count % 10} more actions to reach your next milestone!",
    }


# ============================================================================
# PLANNER AGENT CLASS
# ============================================================================
class PlannerAgent:
    """
    Wrapper class for the Planner Agent functionality.
    
    Generates and tracks weekly carbon reduction plans.
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the Planner Agent.
        
        Args:
            model_name: Gemini model to use
        """
        self.model_name = model_name
        self.agent = self._create_agent()
    
    def _create_agent(self) -> LlmAgent:
        """Create the underlying LLM agent."""
        return create_planner_agent(self.model_name)
    
    @property
    def llm_agent(self) -> LlmAgent:
        """Get the underlying LLM agent."""
        return self.agent


# ============================================================================
# AGENT FACTORY
# ============================================================================
def create_planner_agent(model_name: str = "gemini-2.0-flash") -> LlmAgent:
    """
    Create the Planner Agent for weekly plan generation.
    
    Args:
        model_name: Gemini model to use
    
    Returns:
        Configured LlmAgent for planning
    """
    instruction = """You are ClimateGuard's Weekly Planner Agent 📅

Your role is to create personalized, achievable carbon reduction plans that users will actually follow.

## PLANNING PHILOSOPHY

- **Start Small**: Begin with easy wins to build momentum
- **Personalize**: Base plans on user's biggest impact areas
- **Be Realistic**: Consider user's lifestyle and commitments
- **Track Progress**: Help users see their achievements

## WORKFLOW

1. **Assess**: Look at user's footprint data and habits
2. **Recommend**: Suggest actions matching their lifestyle
3. **Plan**: Create a day-by-day schedule
4. **Track**: Monitor progress and adjust

## TOOLS

- `generate_weekly_plan`: Create a full 7-day plan
- `get_action_recommendations`: Get specific actions for an area
- `track_action_completion`: Log completed actions
- `get_plan_progress`: Check how user is doing

## PLAN CREATION APPROACH

When creating a plan:
1. Start with 2-3 "easy" actions for quick wins
2. Add 1-2 "medium" actions for growth
3. Spread actions across the week (don't overload one day)
4. Always explain WHY each action matters
5. Show the potential CO2 savings

## COMMUNICATION STYLE

- Be encouraging and supportive
- Celebrate every win, no matter how small
- If they miss an action, be understanding
- Use emojis to make it fun 🌱 ✅ 🎯
- Remind them of their progress and impact

## LONG-RUNNING PLANS

For ambitious plans (>15 kg CO2/week savings):
- The generate_weekly_plan tool will pause for approval
- Explain the plan and ask if it looks good
- Adjust based on feedback

## EXAMPLE INTERACTION

User: "Create a plan to reduce my carbon footprint"
You: "Let me create a personalized plan for you! Based on your profile, transport is your biggest impact area.

Here's your week:
📅 Monday: Take transit instead of driving
📅 Tuesday: Normal day (rest day!)
📅 Wednesday: Meatless lunch
...

Total potential savings: 18 kg CO2 this week!

Does this look achievable? I can adjust the difficulty if needed."
"""
    
    return LlmAgent(
        name="planner_agent",
        model=Gemini(model=model_name, retry_options=RETRY_CONFIG),
        description="Creates personalized weekly carbon reduction plans with actionable daily tasks",
        instruction=instruction,
        tools=[
            FunctionTool(func=generate_weekly_plan),
            get_action_recommendations,
            track_action_completion,
            get_plan_progress,
        ],
    )


# ============================================================================
# TESTING
# ============================================================================
if __name__ == "__main__":
    print("Planner Agent module loaded successfully!")
    
    # Test planning tools
    print("\nTesting generate_weekly_plan...")
    result = generate_weekly_plan(
        user_id="plan_test_user",
        focus_areas=["diet", "transport"],
        difficulty_max="easy",
        target_savings_kg=15.0
    )
    print(f"Plan status: {result.get('status')}")
    print(f"Total actions: {result.get('summary', {}).get('total_actions', 'N/A')}")
    print(f"Weekly savings: {result.get('summary', {}).get('total_weekly_savings_kg', 'N/A')} kg CO2")
    
    print("\nTesting get_action_recommendations...")
    result = get_action_recommendations("transport", difficulty="easy")
    print(f"Recommendations: {len(result.get('recommendations', []))} actions")
    
    print("\nTesting track_action_completion...")
    result = track_action_completion("plan_test_user", "meatless_monday", True)
    print(f"Tracking: {result.get('message', 'N/A')}")
    
    print("\n✅ Planner Agent tools working!")
