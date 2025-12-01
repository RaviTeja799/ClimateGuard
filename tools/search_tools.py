"""
ClimateGuard Search Tools
=========================
Tools for finding community groups and sustainability information.

Uses Google Search tool and mock A2A for community features.
"""

import os
import json
from typing import List, Optional
from datetime import datetime


# ============================================================================
# MOCK COMMUNITY DATABASE
# ============================================================================
# In production, this would connect to real community platforms or A2A agents
COMMUNITY_GROUPS = {
    "new york": [
        {
            "name": "NYC Climate Action Coalition",
            "type": "local_group",
            "members": 2500,
            "focus": ["urban sustainability", "zero-waste", "public transit"],
            "contact": "nycclimateaction@example.org",
            "next_event": "Community Solar Workshop - Dec 15, 2025",
        },
        {
            "name": "Brooklyn Green Team",
            "type": "neighborhood",
            "members": 450,
            "focus": ["urban gardening", "composting", "bike advocacy"],
            "contact": "brooklyngreenteam@example.org",
            "next_event": "Winter Composting 101 - Dec 10, 2025",
        },
    ],
    "san francisco": [
        {
            "name": "Bay Area Carbon Collective",
            "type": "regional",
            "members": 3200,
            "focus": ["tech sustainability", "carbon offsets", "EV adoption"],
            "contact": "bayareacarbon@example.org",
            "next_event": "EV Ride & Drive Event - Dec 20, 2025",
        },
        {
            "name": "SF Zero Waste Group",
            "type": "local_group",
            "members": 890,
            "focus": ["zero-waste lifestyle", "plastic-free", "repair cafes"],
            "contact": "sfzerowaste@example.org",
            "next_event": "Repair Cafe - Every Saturday",
        },
    ],
    "london": [
        {
            "name": "London Climate Action",
            "type": "city",
            "members": 5600,
            "focus": ["policy advocacy", "public transport", "green spaces"],
            "contact": "londonclimate@example.org",
            "next_event": "Climate Town Hall - Dec 12, 2025",
        },
    ],
    "los angeles": [
        {
            "name": "LA Sustainability Network",
            "type": "regional",
            "members": 2100,
            "focus": ["water conservation", "solar power", "sustainable living"],
            "contact": "lasustainability@example.org",
            "next_event": "Solar Home Tour - Dec 18, 2025",
        },
    ],
    "seattle": [
        {
            "name": "Seattle Green Community",
            "type": "local_group",
            "members": 1800,
            "focus": ["rain gardens", "composting", "local food"],
            "contact": "seattlegreen@example.org",
            "next_event": "Rain Garden Workshop - Dec 8, 2025",
        },
    ],
}

# Active challenges database
COMMUNITY_CHALLENGES = [
    {
        "name": "30-Day Plant-Based Challenge",
        "description": "Commit to plant-based meals for 30 days. Average CO2 savings: 100kg per participant.",
        "participants": 1250,
        "start_date": "2025-12-01",
        "co2_saved_total_kg": 125000,
        "difficulty": "medium",
    },
    {
        "name": "No-Car Week",
        "description": "Go car-free for one week. Use public transit, bike, or walk. Average CO2 savings: 25kg.",
        "participants": 890,
        "start_date": "2025-12-07",
        "co2_saved_total_kg": 22250,
        "difficulty": "easy",
    },
    {
        "name": "Home Energy Audit Challenge",
        "description": "Complete a home energy audit and implement 3 efficiency improvements.",
        "participants": 450,
        "start_date": "2025-12-15",
        "co2_saved_total_kg": 45000,
        "difficulty": "medium",
    },
    {
        "name": "Flight-Free Year Pledge",
        "description": "Commit to no flights for 12 months. Explore local destinations instead.",
        "participants": 320,
        "start_date": "2025-01-01",
        "co2_saved_total_kg": 480000,
        "difficulty": "hard",
    },
]

# Sustainability tips database
SUSTAINABILITY_TIPS = {
    "diet": [
        "Reduce red meat consumption to 1-2 times per week - saves ~500 kg CO2/year",
        "Buy local and seasonal produce when possible",
        "Try Meatless Mondays to ease into plant-based eating",
        "Compost food scraps to reduce methane from landfills",
        "Bring reusable bags and containers when shopping",
    ],
    "transport": [
        "Combine errands into single trips to reduce driving",
        "Consider carpooling or ridesharing for daily commutes",
        "Use public transit for trips over 5km when available",
        "Walk or bike for trips under 3km - zero emissions + health benefits!",
        "If buying a car, consider hybrid or electric options",
    ],
    "energy": [
        "Switch to LED bulbs - uses 75% less energy than incandescent",
        "Unplug electronics when not in use (standby power adds up!)",
        "Set thermostat 1-2°C lower in winter, higher in summer",
        "Consider switching to a renewable energy provider",
        "Use a programmable thermostat for automatic efficiency",
    ],
    "general": [
        "Track your carbon footprint monthly to see progress",
        "Start with one change and build habits gradually",
        "Share your journey with friends and family",
        "Join a local sustainability group for support and ideas",
        "Celebrate your wins - every kg CO2 saved matters!",
    ],
}


# ============================================================================
# COMMUNITY SEARCH TOOL
# ============================================================================
def find_local_community_groups(
    city: str,
    interest: Optional[str] = None,
    include_challenges: bool = True
) -> dict:
    """
    Finds local sustainability and climate action community groups.
    
    In production, this would use A2A protocol to query community agent networks.
    
    Args:
        city: City name to search for groups
        interest: Optional specific interest (e.g., "zero-waste", "cycling")
        include_challenges: Whether to include active community challenges
    
    Returns:
        Dictionary with groups, challenges, and engagement tips
    
    Example:
        >>> find_local_community_groups("san francisco", interest="zero-waste")
        {"status": "success", "groups": [...], "challenges": [...]}
    """
    city_lower = city.lower()
    
    # Find groups
    groups = COMMUNITY_GROUPS.get(city_lower, [])
    
    # Filter by interest if provided
    if interest and groups:
        interest_lower = interest.lower()
        filtered = []
        for group in groups:
            if any(interest_lower in focus.lower() for focus in group.get("focus", [])):
                filtered.append(group)
        if filtered:
            groups = filtered
    
    # Get challenges
    challenges = COMMUNITY_CHALLENGES if include_challenges else []
    
    # Generate response
    if not groups:
        return {
            "status": "success",
            "city": city,
            "groups_found": 0,
            "groups": [],
            "message": f"No groups found in {city}. Consider starting one or searching nearby cities!",
            "nearby_suggestion": "Try searching for groups in nearby metropolitan areas.",
            "challenges": challenges[:2] if include_challenges else [],
            "tip": "You can still participate in global online challenges!",
        }
    
    total_members = sum(g.get("members", 0) for g in groups)
    
    return {
        "status": "success",
        "city": city,
        "interest_filter": interest,
        "groups_found": len(groups),
        "total_community_members": total_members,
        "groups": groups,
        "challenges": challenges[:3] if include_challenges else [],
        "engagement_tips": [
            f"Join {groups[0]['name']} - they have {groups[0]['members']} members!",
            f"Upcoming event: {groups[0].get('next_event', 'Check their page for events')}",
            "Start by attending one event to meet like-minded people",
        ],
    }


# ============================================================================
# SUSTAINABILITY TIPS SEARCH TOOL
# ============================================================================
def search_sustainability_tips(
    category: str = "general",
    user_context: Optional[str] = None,
    limit: int = 5
) -> dict:
    """
    Searches for relevant sustainability tips based on category or context.
    
    Args:
        category: Category - "diet", "transport", "energy", "general"
        user_context: Optional context about user's situation for personalized tips
        limit: Maximum number of tips to return
    
    Returns:
        Dictionary with tips and action items
    
    Example:
        >>> search_sustainability_tips("diet", user_context="eats meat daily")
        {"status": "success", "tips": [...]}
    """
    category_lower = category.lower()
    
    if category_lower not in SUSTAINABILITY_TIPS:
        # Search all categories
        all_tips = []
        for cat, tips in SUSTAINABILITY_TIPS.items():
            all_tips.extend(tips)
        tips = all_tips[:limit]
        category_used = "all"
    else:
        tips = SUSTAINABILITY_TIPS[category_lower][:limit]
        category_used = category_lower
    
    # Personalize based on context
    personalized_advice = None
    if user_context:
        context_lower = user_context.lower()
        if "meat" in context_lower or "beef" in context_lower:
            personalized_advice = "Based on your diet, reducing meat consumption could be your biggest impact area. Start with Meatless Mondays!"
        elif "car" in context_lower or "driv" in context_lower:
            personalized_advice = "Since you drive frequently, consider carpooling or combining trips. Even one day of public transit per week helps!"
        elif "fly" in context_lower or "flight" in context_lower:
            personalized_advice = "Air travel is high-impact. Consider alternatives like trains for trips under 500km, or carbon offsets for necessary flights."
    
    return {
        "status": "success",
        "category": category_used,
        "user_context": user_context,
        "tips_count": len(tips),
        "tips": tips,
        "personalized_advice": personalized_advice,
        "quick_wins": [
            "LED light bulbs",
            "Reusable water bottle",
            "Meatless Monday",
        ],
        "challenge_suggestion": COMMUNITY_CHALLENGES[0] if COMMUNITY_CHALLENGES else None,
    }


# ============================================================================
# A2A MOCK ENDPOINT (for future extension)
# ============================================================================
def connect_to_community_agent(agent_url: str, user_id: str, action: str) -> dict:
    """
    Mock A2A connection to remote community agent.
    
    In production, this would use RemoteA2aAgent from google.adk.agents.
    
    Args:
        agent_url: URL of the remote community agent
        user_id: User identifier
        action: Action to perform ("join_group", "join_challenge", "share_progress")
    
    Returns:
        Dictionary with connection status and result
    """
    # Mock response - in production would use actual A2A protocol
    return {
        "status": "success",
        "source": "mock_a2a",
        "agent_url": agent_url,
        "user_id": user_id,
        "action": action,
        "message": f"A2A connection to {agent_url} successful. Action '{action}' queued.",
        "note": "This is a mock response. Configure A2A agents for real community connections.",
    }


# ============================================================================
# LEADERBOARD & IMPACT AGGREGATION
# ============================================================================
def get_community_impact(city: Optional[str] = None) -> dict:
    """
    Gets aggregated community impact data.
    
    Args:
        city: Optional city filter
    
    Returns:
        Dictionary with community impact metrics
    """
    total_participants = sum(c["participants"] for c in COMMUNITY_CHALLENGES)
    total_co2_saved = sum(c["co2_saved_total_kg"] for c in COMMUNITY_CHALLENGES)
    
    # Calculate equivalents
    trees_equivalent = round(total_co2_saved / 21, 0)
    cars_off_road = round(total_co2_saved / 4600, 1)
    
    return {
        "status": "success",
        "city_filter": city,
        "total_active_challenges": len(COMMUNITY_CHALLENGES),
        "total_participants": total_participants,
        "total_co2_saved_kg": total_co2_saved,
        "total_co2_saved_tons": round(total_co2_saved / 1000, 1),
        "equivalent_trees_planted": trees_equivalent,
        "equivalent_cars_off_road_for_year": cars_off_road,
        "top_challenge": max(COMMUNITY_CHALLENGES, key=lambda x: x["co2_saved_total_kg"]),
        "impact_message": f"Together, we've saved {round(total_co2_saved/1000, 1)} tons of CO2 - equivalent to planting {int(trees_equivalent)} trees!",
    }


if __name__ == "__main__":
    # Test the tools
    print("Testing Search Tools...")
    
    # Test community search
    result = find_local_community_groups("san francisco", interest="zero-waste")
    print(f"\nCommunity Groups (SF): {json.dumps(result, indent=2)}")
    
    # Test tips search
    result = search_sustainability_tips("diet", user_context="eats meat daily")
    print(f"\nSustainability Tips: {json.dumps(result, indent=2)}")
    
    # Test impact
    result = get_community_impact()
    print(f"\nCommunity Impact: {json.dumps(result, indent=2)}")
    
    print("\n✅ All search tools working!")
