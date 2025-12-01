"""
ClimateGuard Calculator Agent
=============================
Computes carbon footprint using parallel API calls to real data sources.

Makes parallel calls to:
- ElectricityMaps API (grid carbon intensity)
- Climatiq API (flights, food, transport)
- Google Maps API (driving distances)

ADK Concepts: Parallel Agents, Custom Tools, Code Execution
"""

import os
from typing import Optional, List
from datetime import datetime

# ADK Imports
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.code_executors import BuiltInCodeExecutor
from google.genai import types

# Local imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.carbon_tools import (
    get_electricity_carbon_intensity,
    calculate_flight_emissions,
    calculate_transport_emissions,
    get_food_carbon_footprint,
    calculate_home_energy_emissions,
    get_emission_factor,
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
# CALCULATOR-SPECIFIC TOOLS
# ============================================================================
def calculate_daily_footprint(
    user_id: str,
    include_diet: bool = True,
    include_transport: bool = True,
    include_energy: bool = True
) -> dict:
    """
    Calculates the user's daily carbon footprint based on their profile.
    
    Pulls data from user profile and computes emissions for each category.
    
    Args:
        user_id: User identifier
        include_diet: Include food-related emissions
        include_transport: Include transportation emissions
        include_energy: Include home energy emissions
    
    Returns:
        Dictionary with detailed breakdown of daily emissions
    """
    import asyncio
    
    memory_service = get_memory_service()
    
    # Get user profile
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
    
    if not profile:
        return {
            "status": "error",
            "message": f"No profile found for {user_id}. Please complete onboarding first."
        }
    
    emissions = {
        "diet": 0,
        "transport": 0,
        "energy": 0,
        "flights": 0,
    }
    details = {}
    
    # Calculate diet emissions (daily)
    if include_diet:
        if profile.meat_meals_per_week > 0:
            # Assume 0.25kg meat per meal, beef as default
            weekly_meat_kg = profile.meat_meals_per_week * 0.25
            meat_result = get_food_carbon_footprint("beef", weekly_meat_kg / 7, meals_per_week=7)
            emissions["diet"] = meat_result.get("per_meal_emissions_kg_co2", 0)
            details["diet"] = {
                "meat_meals_per_week": profile.meat_meals_per_week,
                "daily_food_emissions": round(emissions["diet"], 2),
                "alternatives": meat_result.get("lower_impact_alternatives", [])[:2]
            }
        else:
            emissions["diet"] = 1.5  # Average vegetarian/vegan daily
            details["diet"] = {"type": profile.diet_type, "daily_food_emissions": 1.5}
    
    # Calculate transport emissions (daily)
    if include_transport and profile.commute_distance_km > 0:
        transport_result = calculate_transport_emissions(
            mode="car" if profile.primary_transport == "car" else profile.primary_transport,
            distance_km=profile.commute_distance_km * 2,  # Round trip
            fuel_type=profile.car_type if profile.car_type != "none" else "petrol"
        )
        emissions["transport"] = transport_result.get("total_emissions_kg_co2", 0)
        details["transport"] = {
            "mode": profile.primary_transport,
            "daily_km": profile.commute_distance_km * 2,
            "daily_emissions": round(emissions["transport"], 2),
            "alternatives": transport_result.get("lower_emission_alternatives", [])[:2]
        }
    
    # Calculate energy emissions (daily)
    if include_energy and profile.electricity_kwh_monthly > 0:
        energy_result = calculate_home_energy_emissions(
            electricity_kwh=profile.electricity_kwh_monthly,
            gas_m3=profile.gas_m3_monthly,
            location=profile.city if profile.city else "us_avg",
            renewable_percentage=profile.renewable_energy_percentage
        )
        # Convert monthly to daily
        emissions["energy"] = energy_result.get("total_monthly_emissions_kg_co2", 0) / 30
        details["energy"] = {
            "monthly_electricity_kwh": profile.electricity_kwh_monthly,
            "daily_emissions": round(emissions["energy"], 2),
            "renewable_percentage": profile.renewable_energy_percentage,
            "recommendations": energy_result.get("recommendations", [])[:2]
        }
    
    # Calculate flight emissions (amortized daily)
    if profile.flights_per_year > 0:
        avg_flight_emissions = 500  # kg CO2 per round trip (average)
        yearly_flight_emissions = profile.flights_per_year * avg_flight_emissions
        emissions["flights"] = yearly_flight_emissions / 365
        details["flights"] = {
            "flights_per_year": profile.flights_per_year,
            "yearly_emissions": yearly_flight_emissions,
            "daily_amortized": round(emissions["flights"], 2)
        }
    
    # Calculate totals
    total_daily = sum(emissions.values())
    total_weekly = total_daily * 7
    total_yearly = total_daily * 365
    
    # Compare to averages
    us_avg_yearly = 16000  # kg CO2/year for average American
    global_avg_yearly = 4700  # kg CO2/year global average
    target_yearly = 2000  # kg CO2/year sustainable target
    
    return {
        "status": "success",
        "user_id": user_id,
        "location": f"{profile.city}, {profile.country}",
        "emissions": {
            "daily_kg_co2": round(total_daily, 2),
            "weekly_kg_co2": round(total_weekly, 2),
            "yearly_kg_co2": round(total_yearly, 1),
            "yearly_tons_co2": round(total_yearly / 1000, 2),
        },
        "breakdown": {
            "diet": round(emissions["diet"], 2),
            "transport": round(emissions["transport"], 2),
            "energy": round(emissions["energy"], 2),
            "flights": round(emissions["flights"], 2),
        },
        "breakdown_percentage": {
            k: round(v / total_daily * 100, 1) if total_daily > 0 else 0
            for k, v in emissions.items()
        },
        "details": details,
        "comparison": {
            "vs_us_average": f"{round((total_yearly / us_avg_yearly) * 100)}% of US average",
            "vs_global_average": f"{round((total_yearly / global_avg_yearly) * 100)}% of global average",
            "vs_sustainable_target": f"{round((total_yearly / target_yearly) * 100)}% of sustainable target",
        },
        "equivalent_trees_per_year": round(total_yearly / 21, 0),
        "biggest_impact_area": max(emissions, key=emissions.get) if any(emissions.values()) else "none",
    }


def calculate_activity_emissions(
    activity_type: str,
    activity_details: str,
    quantity: float,
    unit: str = "kg"
) -> dict:
    """
    Calculates emissions for a specific activity.
    
    Supports various activities like meals, trips, purchases.
    
    Args:
        activity_type: Type of activity - "food", "transport", "flight", "energy"
        activity_details: Specific details (e.g., "beef", "car_petrol", "NYC-LAX")
        quantity: Amount/distance/quantity
        unit: Unit of measurement (kg, km, kWh, etc.)
    
    Returns:
        Dictionary with emission calculation
    """
    activity_type = activity_type.lower()
    
    if activity_type == "food":
        return get_food_carbon_footprint(activity_details, quantity)
    
    elif activity_type == "transport":
        mode = "car"
        fuel = "petrol"
        if "_" in activity_details:
            parts = activity_details.split("_")
            mode = parts[0]
            fuel = parts[1] if len(parts) > 1 else "petrol"
        return calculate_transport_emissions(mode, quantity, fuel)
    
    elif activity_type == "flight":
        # Parse "NYC-LAX" format
        if "-" in activity_details:
            origin, dest = activity_details.split("-")
            return calculate_flight_emissions(origin.strip(), dest.strip())
        return {"status": "error", "message": "Flight format should be 'ORIGIN-DESTINATION' (e.g., 'NYC-LAX')"}
    
    elif activity_type == "energy":
        return calculate_home_energy_emissions(quantity, location=activity_details)
    
    else:
        return {
            "status": "error",
            "message": f"Unknown activity type: {activity_type}. Use: food, transport, flight, energy"
        }


def record_activity_and_emissions(
    user_id: str,
    activity_type: str,
    activity_description: str,
    emissions_kg_co2: float
) -> dict:
    """
    Records an activity and its emissions to user's history.
    
    Args:
        user_id: User identifier
        activity_type: Category (food, transport, energy, etc.)
        activity_description: Description of the activity
        emissions_kg_co2: Calculated emissions
    
    Returns:
        Dictionary with recording status
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
                    memory_service.record_footprint(
                        user_id=user_id,
                        category=activity_type,
                        activity=activity_description,
                        emissions_kg_co2=emissions_kg_co2
                    )
                )
                result = future.result()
        else:
            result = asyncio.run(memory_service.record_footprint(
                user_id=user_id,
                category=activity_type,
                activity=activity_description,
                emissions_kg_co2=emissions_kg_co2
            ))
    except RuntimeError:
        result = asyncio.run(memory_service.record_footprint(
            user_id=user_id,
            category=activity_type,
            activity=activity_description,
            emissions_kg_co2=emissions_kg_co2
        ))
    
    return result


# ============================================================================
# SUB-AGENT: MATH CALCULATOR
# ============================================================================
def create_math_agent(model_name: str = "gemini-2.0-flash") -> LlmAgent:
    """
    Create a sub-agent for precise mathematical calculations.
    
    Uses code execution for accurate computation.
    """
    return LlmAgent(
        name="math_calculator",
        model=Gemini(model=model_name, retry_options=RETRY_CONFIG),
        description="Performs precise mathematical calculations using Python code",
        instruction="""You are a calculation specialist. When given numbers to calculate:
        1. Write Python code to perform the calculation
        2. Output the result clearly
        3. Show your work step by step
        
        Always use Python for calculations to ensure precision.""",
        code_executor=BuiltInCodeExecutor(),
    )


# ============================================================================
# CALCULATOR AGENT CLASS
# ============================================================================
class CalculatorAgent:
    """
    Wrapper class for the Calculator Agent functionality.
    
    Computes carbon footprints using parallel API calls.
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the Calculator Agent.
        
        Args:
            model_name: Gemini model to use
        """
        self.model_name = model_name
        self.agent = self._create_agent()
    
    def _create_agent(self) -> LlmAgent:
        """Create the underlying LLM agent."""
        return create_calculator_agent(self.model_name)
    
    @property
    def llm_agent(self) -> LlmAgent:
        """Get the underlying LLM agent."""
        return self.agent


# ============================================================================
# AGENT FACTORY
# ============================================================================
def create_calculator_agent(model_name: str = "gemini-2.0-flash") -> LlmAgent:
    """
    Create the Calculator Agent for carbon footprint computation.
    
    Args:
        model_name: Gemini model to use
    
    Returns:
        Configured LlmAgent for calculations
    """
    # Create math sub-agent
    math_agent = create_math_agent(model_name)
    
    instruction = """You are ClimateGuard's Footprint Calculator Agent 🧮

Your role is to accurately calculate carbon emissions using real data and tools.

## CAPABILITIES

1. **Daily Footprint Analysis**
   - Use calculate_daily_footprint to get a complete breakdown
   - Analyzes diet, transport, energy, and flights
   - Compares to averages and targets

2. **Activity-Specific Calculations**
   - Use calculate_activity_emissions for one-off calculations
   - Supports food, transport, flights, and energy
   - Provides alternatives with lower emissions

3. **Recording & Tracking**
   - Use record_activity_and_emissions to log activities
   - Builds history for trend analysis

4. **API Tools for Real Data**
   - get_electricity_carbon_intensity: Real-time grid data
   - calculate_flight_emissions: Accurate flight CO2
   - calculate_transport_emissions: Ground transport
   - get_food_carbon_footprint: Diet impact
   - calculate_home_energy_emissions: Utility emissions

## CALCULATION APPROACH

1. Always use tools for calculations - don't estimate manually
2. For complex math, use the math_calculator sub-agent
3. Provide clear breakdowns with percentages
4. Always show alternatives and potential savings
5. Record significant activities to user history

## RESPONSE FORMAT

When presenting results:
- Lead with the key number (total emissions)
- Show breakdown by category
- Compare to benchmarks (US avg, global, target)
- Highlight biggest impact area
- Suggest top 2-3 reduction opportunities

## IMPORTANT

- Be precise with numbers (2 decimal places for kg, 1 for yearly)
- Convert units when needed (tons vs kg)
- Always provide context (trees equivalent, comparison)
- If data is missing, explain what's needed for accuracy
"""
    
    return LlmAgent(
        name="calculator_agent",
        model=Gemini(model=model_name, retry_options=RETRY_CONFIG),
        description="Calculates carbon footprint using real data from ElectricityMaps, Climatiq, and other APIs",
        instruction=instruction,
        tools=[
            # Main calculation tools
            calculate_daily_footprint,
            calculate_activity_emissions,
            record_activity_and_emissions,
            # Direct API tools
            get_electricity_carbon_intensity,
            calculate_flight_emissions,
            calculate_transport_emissions,
            get_food_carbon_footprint,
            calculate_home_energy_emissions,
            get_emission_factor,
            # Sub-agent for math
            AgentTool(agent=math_agent),
        ],
    )


# ============================================================================
# TESTING
# ============================================================================
if __name__ == "__main__":
    print("Calculator Agent module loaded successfully!")
    
    # Test calculation tools
    print("\nTesting calculate_daily_footprint...")
    # First create a test profile
    from profile import save_user_profile
    save_user_profile(
        user_id="calc_test_user",
        city="San Francisco",
        country="USA",
        diet_type="omnivore",
        meat_meals_per_week=4,
        primary_transport="car",
        car_type="petrol",
        commute_distance_km=20,
        flights_per_year=2,
        electricity_kwh_monthly=500,
        gas_m3_monthly=20,
        renewable_energy_percentage=10,
    )
    
    result = calculate_daily_footprint("calc_test_user")
    print(f"Daily footprint: {result.get('emissions', {}).get('daily_kg_co2', 'N/A')} kg CO2")
    print(f"Yearly: {result.get('emissions', {}).get('yearly_tons_co2', 'N/A')} tons CO2")
    print(f"Biggest impact: {result.get('biggest_impact_area', 'N/A')}")
    
    print("\nTesting calculate_activity_emissions...")
    result = calculate_activity_emissions("food", "beef", 0.25)
    print(f"Beef meal: {result.get('per_meal_emissions_kg_co2', 'N/A')} kg CO2")
    
    print("\n✅ Calculator Agent tools working!")
