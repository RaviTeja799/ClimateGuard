"""
ClimateGuard Profile Agent
==========================
Handles user onboarding and lifestyle profiling.

Collects information about:
- Diet and food habits
- Transportation patterns
- Home energy usage
- Location and climate zone
- Sustainability goals

ADK Concepts: Sequential Agent, Memory (add_session_to_memory), Custom Tools
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime

# ADK Imports
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import ToolContext
from google.genai import types

# Local imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from memory.memory_service import UserProfile, get_memory_service


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
# PROFILE TOOLS
# ============================================================================
def save_user_profile(
    user_id: str,
    city: str,
    country: str,
    diet_type: str,
    meat_meals_per_week: int,
    primary_transport: str,
    car_type: str = "none",
    commute_distance_km: float = 0,
    flights_per_year: int = 0,
    electricity_kwh_monthly: float = 0,
    gas_m3_monthly: float = 0,
    renewable_energy_percentage: int = 0,
    tool_context: ToolContext = None
) -> dict:
    """
    Saves user's lifestyle profile to long-term memory.
    
    Call this after collecting all profile information from the user.
    
    Args:
        user_id: Unique identifier for the user
        city: User's city of residence
        country: User's country
        diet_type: Diet type - "omnivore", "vegetarian", "vegan", "pescatarian"
        meat_meals_per_week: Number of meals with meat per week (0-21)
        primary_transport: Main transport mode - "car", "public_transit", "bicycle", "walking"
        car_type: If drives - "petrol", "diesel", "hybrid", "electric", "none"
        commute_distance_km: Daily commute distance in kilometers
        flights_per_year: Number of round-trip flights per year
        electricity_kwh_monthly: Monthly electricity consumption in kWh
        gas_m3_monthly: Monthly natural gas consumption in m³
        renewable_energy_percentage: Percentage of energy from renewable sources (0-100)
    
    Returns:
        Dictionary with status and profile summary
    """
    import asyncio
    
    # Create profile object
    profile = UserProfile(
        user_id=user_id,
        city=city,
        country=country,
        diet_type=diet_type,
        meat_meals_per_week=meat_meals_per_week,
        primary_transport=primary_transport,
        car_type=car_type if primary_transport == "car" else "none",
        commute_distance_km=commute_distance_km,
        flights_per_year=flights_per_year,
        electricity_kwh_monthly=electricity_kwh_monthly,
        gas_m3_monthly=gas_m3_monthly,
        renewable_energy_percentage=renewable_energy_percentage,
    )
    
    # Save to memory service
    memory_service = get_memory_service()
    
    # Run async save in sync context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, memory_service.save_profile(profile))
                result = future.result()
        else:
            result = asyncio.run(memory_service.save_profile(profile))
    except RuntimeError:
        # Create new loop if needed
        result = asyncio.run(memory_service.save_profile(profile))
    
    # Calculate quick estimate
    estimate_parts = []
    
    # Diet estimate
    if meat_meals_per_week > 0:
        diet_co2 = meat_meals_per_week * 27 * 0.25 * 52  # ~27kg CO2/kg beef, 0.25kg per meal
        estimate_parts.append(f"Diet: ~{round(diet_co2)} kg CO2/year")
    
    # Transport estimate
    if primary_transport == "car" and commute_distance_km > 0:
        days_per_year = 250  # Working days
        car_factors = {"petrol": 0.21, "diesel": 0.19, "hybrid": 0.12, "electric": 0.05}
        factor = car_factors.get(car_type, 0.21)
        transport_co2 = commute_distance_km * 2 * factor * days_per_year
        estimate_parts.append(f"Commute: ~{round(transport_co2)} kg CO2/year")
    
    # Flight estimate
    if flights_per_year > 0:
        avg_flight_co2 = 500  # Average round trip
        flight_co2 = flights_per_year * avg_flight_co2
        estimate_parts.append(f"Flights: ~{round(flight_co2)} kg CO2/year")
    
    return {
        "status": "success",
        "message": f"Profile saved for {user_id}!",
        "profile_summary": {
            "location": f"{city}, {country}",
            "diet": f"{diet_type} ({meat_meals_per_week} meat meals/week)",
            "transport": f"{primary_transport}" + (f" ({car_type})" if car_type != "none" else ""),
            "flights_per_year": flights_per_year,
        },
        "quick_estimates": estimate_parts,
        "next_step": "Profile saved! Ready to calculate your full carbon footprint.",
    }


def get_user_profile(user_id: str) -> dict:
    """
    Retrieves a user's profile from memory.
    
    Args:
        user_id: User identifier
    
    Returns:
        Dictionary with profile data or error message
    """
    import asyncio
    
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
    
    if profile:
        return {
            "status": "success",
            "profile": profile.to_dict()
        }
    else:
        return {
            "status": "not_found",
            "message": f"No profile found for {user_id}. Please complete onboarding first."
        }


def update_user_preference(user_id: str, preference_key: str, preference_value: str) -> dict:
    """
    Updates a single preference in the user's profile.
    
    Args:
        user_id: User identifier
        preference_key: Which preference to update (e.g., "diet_type", "primary_transport")
        preference_value: New value for the preference
    
    Returns:
        Dictionary with status
    """
    import asyncio
    
    memory_service = get_memory_service()
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, 
                    memory_service.update_profile(user_id, {preference_key: preference_value})
                )
                result = future.result()
        else:
            result = asyncio.run(memory_service.update_profile(user_id, {preference_key: preference_value}))
    except RuntimeError:
        result = asyncio.run(memory_service.update_profile(user_id, {preference_key: preference_value}))
    
    return result


# ============================================================================
# PROFILE AGENT CLASS
# ============================================================================
class ProfileAgent:
    """
    Wrapper class for the Profile Agent functionality.
    
    Handles user onboarding through conversational profiling.
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the Profile Agent.
        
        Args:
            model_name: Gemini model to use
        """
        self.model_name = model_name
        self.agent = self._create_agent()
    
    def _create_agent(self) -> LlmAgent:
        """Create the underlying LLM agent."""
        return create_profile_agent(self.model_name)
    
    @property
    def llm_agent(self) -> LlmAgent:
        """Get the underlying LLM agent."""
        return self.agent


# ============================================================================
# AGENT FACTORY
# ============================================================================
def create_profile_agent(model_name: str = "gemini-2.0-flash") -> LlmAgent:
    """
    Create the Profile Agent for user onboarding.
    
    Args:
        model_name: Gemini model to use
    
    Returns:
        Configured LlmAgent for profiling
    """
    instruction = """You are ClimateGuard's friendly Profile Agent 🌱

Your role is to conduct a warm, conversational onboarding to understand the user's lifestyle and create their carbon profile.

## ONBOARDING FLOW

1. **Welcome & Location**
   - Greet the user warmly
   - Ask where they live (city & country)

2. **Diet & Food** 
   - Ask about their diet type (omnivore, vegetarian, vegan, etc.)
   - If not vegan, ask how many meals per week include meat
   - Keep it non-judgmental!

3. **Transportation**
   - Ask about their primary way of getting around
   - If they drive, ask about car type (petrol, diesel, hybrid, electric)
   - Ask about daily commute distance (if applicable)
   - Ask about annual flight frequency

4. **Home Energy** (optional - ask if they know)
   - Monthly electricity usage (kWh)
   - Gas/heating usage
   - Any renewable energy?

5. **Save & Summarize**
   - Use save_user_profile tool with ALL collected data
   - Provide an encouraging summary

## COMMUNICATION STYLE

- Be friendly and encouraging, never preachy
- Use emojis sparingly but warmly 🌍
- Acknowledge their answers positively
- If they don't know exact numbers, help them estimate
- Keep each question focused (one topic at a time)

## IMPORTANT RULES

- Collect information conversationally, not like a survey
- ALWAYS use save_user_profile when you have enough data
- If user already has a profile, use get_user_profile first
- Make estimates for missing data based on averages
- End with excitement about helping them reduce their footprint!

## EXAMPLE FLOW

User: "Hi, I want to track my carbon footprint"
You: "Welcome to ClimateGuard! 🌱 I'm excited to help you on your sustainability journey. Let's start with the basics - which city and country do you call home?"

User: "San Francisco, USA"  
You: "San Francisco - beautiful city with great public transit options! 🌉 Now, tell me a bit about your diet. Are you omnivore, vegetarian, vegan, or somewhere in between?"

[Continue naturally through the questions]
"""
    
    return LlmAgent(
        name="profile_agent",
        model=Gemini(model=model_name, retry_options=RETRY_CONFIG),
        description="Conducts friendly user onboarding to collect lifestyle data for carbon footprint profiling",
        instruction=instruction,
        tools=[
            save_user_profile,
            get_user_profile,
            update_user_preference,
        ],
    )


# ============================================================================
# TESTING
# ============================================================================
if __name__ == "__main__":
    print("Profile Agent module loaded successfully!")
    
    # Test tool functions
    print("\nTesting save_user_profile tool...")
    result = save_user_profile(
        user_id="test_user",
        city="San Francisco",
        country="USA",
        diet_type="omnivore",
        meat_meals_per_week=5,
        primary_transport="car",
        car_type="petrol",
        commute_distance_km=25,
        flights_per_year=4,
        electricity_kwh_monthly=600,
        gas_m3_monthly=30,
        renewable_energy_percentage=0,
    )
    print(f"Save result: {result}")
    
    print("\nTesting get_user_profile tool...")
    result = get_user_profile("test_user")
    print(f"Get result: {result}")
    
    print("\n✅ Profile Agent tools working!")
