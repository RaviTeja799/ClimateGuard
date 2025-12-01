"""
ClimateGuard Community Agent
============================
Connects users with local sustainability groups and challenges.

Features:
- Finds local community groups
- Manages group challenges
- A2A-ready for cross-agent communication
- Shares success stories

ADK Concepts: A2A Protocol, Google Search Tool, Remote Agents
"""

import os
import json
from typing import Optional, List
from datetime import datetime

# ADK Imports
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search
from google.genai import types

# Local imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.search_tools import (
    find_local_community_groups,
    search_sustainability_tips,
    get_community_impact,
    COMMUNITY_CHALLENGES,
)
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
# COMMUNITY TOOLS
# ============================================================================
def search_local_groups(
    city: str,
    interest: str = None,
    include_online: bool = True
) -> dict:
    """
    Searches for local sustainability and climate groups.
    
    Args:
        city: City to search in
        interest: Optional specific interest (e.g., "zero-waste", "cycling")
        include_online: Whether to include online/virtual groups
    
    Returns:
        Dictionary with local groups and joining information
    """
    result = find_local_community_groups(city, interest=interest)
    
    if include_online:
        result["online_groups"] = [
            {
                "name": "Climate Action Network (Global)",
                "type": "online",
                "members": 15000,
                "focus": ["climate policy", "advocacy", "education"],
                "url": "https://climatenetwork.org",
            },
            {
                "name": "r/ZeroWaste Community",
                "type": "online",
                "members": 500000,
                "focus": ["zero waste", "tips", "community support"],
                "url": "https://reddit.com/r/ZeroWaste",
            },
        ]
    
    return result


def get_active_challenges(
    difficulty: str = "all",
    category: str = "all"
) -> dict:
    """
    Gets currently active community challenges.
    
    Args:
        difficulty: Filter by difficulty - "easy", "medium", "hard", "all"
        category: Filter by category - "diet", "transport", "energy", "all"
    
    Returns:
        Dictionary with active challenges
    """
    challenges = COMMUNITY_CHALLENGES.copy()
    
    if difficulty != "all":
        challenges = [c for c in challenges if c.get("difficulty") == difficulty]
    
    # Calculate total impact
    total_participants = sum(c["participants"] for c in challenges)
    total_co2_saved = sum(c["co2_saved_total_kg"] for c in challenges)
    
    return {
        "status": "success",
        "active_challenges": len(challenges),
        "challenges": challenges,
        "total_participants": total_participants,
        "total_co2_saved_kg": total_co2_saved,
        "total_co2_saved_tons": round(total_co2_saved / 1000, 1),
        "call_to_action": "Join a challenge to multiply your impact!",
    }


def join_challenge(
    user_id: str,
    challenge_name: str,
    commitment_level: str = "full"
) -> dict:
    """
    Registers a user for a community challenge.
    
    Args:
        user_id: User identifier
        challenge_name: Name of the challenge to join
        commitment_level: "full" or "partial" participation
    
    Returns:
        Dictionary with registration status
    """
    import asyncio
    
    # Find the challenge
    challenge = None
    for c in COMMUNITY_CHALLENGES:
        if c["name"].lower() == challenge_name.lower():
            challenge = c
            break
    
    if not challenge:
        return {
            "status": "error",
            "message": f"Challenge '{challenge_name}' not found. Use get_active_challenges to see available options."
        }
    
    # Record to memory
    memory_service = get_memory_service()
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    memory_service.add_memory(
                        user_id=user_id,
                        app_name="climateguard",
                        content=f"Joined challenge: {challenge_name} ({commitment_level} participation)",
                        category="goal",
                        metadata={"challenge": challenge_name, "commitment": commitment_level}
                    )
                )
                result = future.result()
        else:
            result = asyncio.run(memory_service.add_memory(
                user_id=user_id,
                app_name="climateguard",
                content=f"Joined challenge: {challenge_name} ({commitment_level} participation)",
                category="goal",
                metadata={"challenge": challenge_name, "commitment": commitment_level}
            ))
    except RuntimeError:
        result = asyncio.run(memory_service.add_memory(
            user_id=user_id,
            app_name="climateguard",
            content=f"Joined challenge: {challenge_name} ({commitment_level} participation)",
            category="goal",
            metadata={"challenge": challenge_name, "commitment": commitment_level}
        ))
    
    return {
        "status": "success",
        "message": f"🎉 Welcome to '{challenge_name}'!",
        "challenge": challenge,
        "commitment_level": commitment_level,
        "start_date": challenge["start_date"],
        "participants_count": challenge["participants"] + 1,
        "potential_impact": f"If you complete this challenge, you could save approximately {challenge['co2_saved_total_kg'] // challenge['participants']} kg CO2!",
        "tips": [
            "Tell a friend to join for accountability",
            "Track your progress daily",
            "Share your wins in the community",
        ],
    }


def share_success_story(
    user_id: str,
    story_title: str,
    story_content: str,
    co2_saved_kg: float,
    category: str
) -> dict:
    """
    Shares a user's success story with the community.
    
    Args:
        user_id: User identifier
        story_title: Title of the success story
        story_content: The story content
        co2_saved_kg: Amount of CO2 saved
        category: Category of the achievement
    
    Returns:
        Dictionary with sharing status
    """
    import asyncio
    
    memory_service = get_memory_service()
    
    story = {
        "title": story_title,
        "content": story_content,
        "co2_saved_kg": co2_saved_kg,
        "category": category,
        "shared_at": datetime.now().isoformat(),
        "user_id": user_id[:8] + "...",  # Partial ID for privacy
    }
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    memory_service.add_memory(
                        user_id=user_id,
                        app_name="climateguard",
                        content=f"Shared success story: {story_title} - {co2_saved_kg} kg CO2 saved",
                        category="habit",
                        metadata=story
                    )
                )
                result = future.result()
        else:
            result = asyncio.run(memory_service.add_memory(
                user_id=user_id,
                app_name="climateguard",
                content=f"Shared success story: {story_title} - {co2_saved_kg} kg CO2 saved",
                category="habit",
                metadata=story
            ))
    except RuntimeError:
        result = asyncio.run(memory_service.add_memory(
            user_id=user_id,
            app_name="climateguard",
            content=f"Shared success story: {story_title} - {co2_saved_kg} kg CO2 saved",
            category="habit",
            metadata=story
        ))
    
    return {
        "status": "success",
        "message": "🌟 Your success story has been shared!",
        "story": story,
        "encouragement": "Your story could inspire others to take action. Thank you for sharing!",
        "impact_note": f"{co2_saved_kg} kg CO2 saved is equivalent to planting {round(co2_saved_kg/21, 1)} trees!",
    }


def get_community_leaderboard(
    scope: str = "global",
    timeframe: str = "week"
) -> dict:
    """
    Gets the community impact leaderboard.
    
    Args:
        scope: "global", "city", or "challenge"
        timeframe: "day", "week", "month", "all"
    
    Returns:
        Dictionary with leaderboard data
    """
    # Mock leaderboard data
    leaderboard = {
        "status": "success",
        "scope": scope,
        "timeframe": timeframe,
        "last_updated": datetime.now().isoformat(),
        "top_users": [
            {"rank": 1, "user": "green_warrior_42", "co2_saved_kg": 125, "actions_completed": 28},
            {"rank": 2, "user": "eco_champion_sf", "co2_saved_kg": 98, "actions_completed": 22},
            {"rank": 3, "user": "planet_protector", "co2_saved_kg": 87, "actions_completed": 19},
            {"rank": 4, "user": "climate_hero_nyc", "co2_saved_kg": 76, "actions_completed": 17},
            {"rank": 5, "user": "sustainable_sam", "co2_saved_kg": 65, "actions_completed": 15},
        ],
        "top_cities": [
            {"rank": 1, "city": "San Francisco", "participants": 450, "total_co2_saved_kg": 8500},
            {"rank": 2, "city": "New York", "participants": 380, "total_co2_saved_kg": 7200},
            {"rank": 3, "city": "Seattle", "participants": 290, "total_co2_saved_kg": 5800},
        ],
        "community_total": {
            "total_participants": 15000,
            "total_co2_saved_kg": 125000,
            "total_co2_saved_tons": 125,
            "equivalent_trees": 5952,
            "equivalent_cars_off_road": 27,
        },
        "motivation": "Together, we're making a real difference! 🌍",
    }
    
    return leaderboard


# ============================================================================
# COMMUNITY AGENT CLASS
# ============================================================================
class CommunityAgent:
    """
    Wrapper class for the Community Agent functionality.
    
    Connects users with sustainability communities and challenges.
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the Community Agent.
        
        Args:
            model_name: Gemini model to use
        """
        self.model_name = model_name
        self.agent = self._create_agent()
    
    def _create_agent(self) -> LlmAgent:
        """Create the underlying LLM agent."""
        return create_community_agent(self.model_name)
    
    @property
    def llm_agent(self) -> LlmAgent:
        """Get the underlying LLM agent."""
        return self.agent


# ============================================================================
# AGENT FACTORY
# ============================================================================
def create_community_agent(model_name: str = "gemini-2.0-flash") -> LlmAgent:
    """
    Create the Community Agent for social features.
    
    Args:
        model_name: Gemini model to use
    
    Returns:
        Configured LlmAgent for community features
    """
    instruction = """You are ClimateGuard's Community Connector Agent 🤝

Your role is to help users find their climate action community and participate in collective challenges.

## YOUR MISSION

- Connect users with like-minded people in their area
- Help them join challenges for accountability
- Celebrate their wins and share success stories
- Show them the collective impact of the community

## TOOLS

- `search_local_groups`: Find sustainability groups in user's city
- `get_active_challenges`: Show current community challenges
- `join_challenge`: Register user for a challenge
- `share_success_story`: Help user share their achievements
- `get_community_leaderboard`: Show impact rankings
- `google_search`: Search for additional resources

## COMMUNITY CONNECTION APPROACH

1. **Find Their Tribe**
   - Ask about their city and interests
   - Match them with relevant local groups
   - Suggest online communities if local options are limited

2. **Challenge Them**
   - Present active challenges that match their goals
   - Explain the collective impact
   - Make joining feel exciting, not obligatory

3. **Celebrate Together**
   - Encourage sharing success stories
   - Highlight community achievements
   - Show how individual actions add up

## COMMUNICATION STYLE

- Be warm and inclusive
- Emphasize "we're in this together"
- Use community-building language
- Celebrate collective wins
- Make sustainability feel social and fun

## EXAMPLE INTERACTION

User: "I want to connect with others working on climate action"
You: "That's wonderful! 🌍 Climate action is more powerful together.

Let me find some groups near you. What city are you in?

While you share that, here's some inspiration: Our community has collectively saved 125 tons of CO2 this year - that's like taking 27 cars off the road!

You could also join one of our active challenges:
🥗 30-Day Plant-Based Challenge (1,250 participants)
🚗 No-Car Week (890 participants)

Would you like to explore local groups or jump into a challenge?"

## A2A FUTURE CAPABILITIES

In the future, this agent will connect to other community agents via A2A protocol to:
- Share challenges across platforms
- Coordinate city-wide events
- Connect users across different apps

For now, we simulate these connections with our built-in community features.
"""
    
    return LlmAgent(
        name="community_agent",
        model=Gemini(model=model_name, retry_options=RETRY_CONFIG),
        description="Connects users with local sustainability groups and community challenges via A2A-ready features",
        instruction=instruction,
        tools=[
            search_local_groups,
            get_active_challenges,
            join_challenge,
            share_success_story,
            get_community_leaderboard,
            get_community_impact,
            search_sustainability_tips,
            google_search,
        ],
    )


# ============================================================================
# A2A EXTENSION (Future)
# ============================================================================
def create_a2a_community_server():
    """
    Creates an A2A server for the community agent.
    
    This would allow other agents to:
    - Query community challenges
    - Submit users to challenges
    - Share success stories across platforms
    
    Note: This is a placeholder for future A2A integration.
    """
    # In production, this would use:
    # from google.adk.a2a.utils.agent_to_a2a import to_a2a
    # a2a_app = to_a2a(create_community_agent())
    # return a2a_app
    
    return {
        "status": "not_implemented",
        "message": "A2A server is ready for future implementation",
        "planned_endpoints": [
            "/challenges - List active challenges",
            "/join - Join a challenge",
            "/impact - Get community impact metrics",
            "/stories - Share success stories",
        ]
    }


# ============================================================================
# TESTING
# ============================================================================
if __name__ == "__main__":
    print("Community Agent module loaded successfully!")
    
    # Test community tools
    print("\nTesting search_local_groups...")
    result = search_local_groups("San Francisco", interest="zero-waste")
    print(f"Found {result.get('groups_found', 0)} groups")
    
    print("\nTesting get_active_challenges...")
    result = get_active_challenges()
    print(f"Active challenges: {result.get('active_challenges', 0)}")
    print(f"Total participants: {result.get('total_participants', 0)}")
    
    print("\nTesting join_challenge...")
    result = join_challenge("community_test_user", "30-Day Plant-Based Challenge")
    print(f"Join status: {result.get('status')}")
    
    print("\nTesting get_community_leaderboard...")
    result = get_community_leaderboard()
    print(f"Community total CO2 saved: {result.get('community_total', {}).get('total_co2_saved_tons', 0)} tons")
    
    print("\n✅ Community Agent tools working!")
