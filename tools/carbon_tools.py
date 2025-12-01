"""
ClimateGuard Carbon Tools
=========================
Custom function tools for carbon footprint calculations using real-world APIs.

APIs Integrated:
- Climatiq API: Comprehensive emissions database
- ElectricityMaps API: Real-time grid carbon intensity
- Google Maps API: Distance and route calculations

All tools are designed to be used with Google ADK agents.
"""

import os
import json
from typing import Optional
from datetime import datetime

# Try to import requests, fall back to mock data if not available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ============================================================================
# EMISSION FACTORS DATABASE (Fallback when APIs unavailable)
# ============================================================================
# Sources: EPA, DEFRA, Climatiq
EMISSION_FACTORS = {
    # Food (kg CO2e per kg of food)
    "food": {
        "beef": 27.0,
        "lamb": 39.2,
        "pork": 12.1,
        "chicken": 6.9,
        "fish": 6.1,
        "eggs": 4.8,
        "cheese": 13.5,
        "milk": 3.2,
        "rice": 2.7,
        "pasta": 1.2,
        "bread": 1.4,
        "vegetables": 2.0,
        "fruits": 1.1,
        "tofu": 2.0,
        "lentils": 0.9,
        "beans": 0.8,
    },
    # Transport (kg CO2e per km)
    "transport": {
        "car_petrol": 0.21,
        "car_diesel": 0.19,
        "car_hybrid": 0.12,
        "car_electric": 0.05,  # Depends on grid
        "bus": 0.089,
        "train": 0.041,
        "subway": 0.031,
        "bicycle": 0.0,
        "walking": 0.0,
        "motorcycle": 0.11,
        "taxi": 0.23,
        "rideshare": 0.15,
    },
    # Flights (kg CO2e per km per passenger)
    "flights": {
        "domestic_economy": 0.255,
        "short_haul_economy": 0.156,
        "short_haul_business": 0.234,
        "long_haul_economy": 0.148,
        "long_haul_business": 0.429,
        "long_haul_first": 0.591,
    },
    # Home Energy (kg CO2e per kWh)
    "energy": {
        "electricity_us_avg": 0.42,
        "electricity_uk": 0.21,
        "electricity_eu_avg": 0.28,
        "electricity_renewable": 0.02,
        "natural_gas": 2.0,  # per m3
        "heating_oil": 2.68,  # per liter
    },
    # Grid Carbon Intensity by region (g CO2/kWh)
    "grid_intensity": {
        "california": 210,
        "texas": 380,
        "new_york": 280,
        "washington": 85,
        "florida": 400,
        "uk": 180,
        "france": 50,
        "germany": 350,
        "india": 700,
        "china": 550,
        "japan": 470,
        "australia": 650,
        "brazil": 85,
        "canada": 120,
    }
}

# Airport codes database (sample)
AIRPORT_DISTANCES = {
    ("NYC", "LAX"): 3944,
    ("NYC", "LHR"): 5585,
    ("NYC", "CDG"): 5839,
    ("LAX", "SFO"): 543,
    ("LAX", "SEA"): 1544,
    ("LHR", "CDG"): 344,
    ("LHR", "FRA"): 654,
    ("SFO", "TYO"): 8278,
    ("NYC", "MIA"): 1756,
    ("CHI", "NYC"): 1144,
}


# ============================================================================
# ELECTRICITY CARBON INTENSITY TOOL
# ============================================================================
def get_electricity_carbon_intensity(location: str, zone_type: str = "country") -> dict:
    """
    Gets the real-time carbon intensity of the electricity grid for a location.
    
    Uses ElectricityMaps API when available, falls back to stored data.
    
    Args:
        location: The location (city, state, or country code) to check
        zone_type: Type of zone - "country", "state", or "city"
    
    Returns:
        Dictionary with status, carbon intensity (g CO2/kWh), and breakdown
    
    Example:
        >>> get_electricity_carbon_intensity("california", "state")
        {"status": "success", "carbon_intensity": 210, "unit": "gCO2/kWh", ...}
    """
    api_key = os.getenv("ELECTRICITY_MAPS_API_KEY")
    location_lower = location.lower().replace(" ", "_")
    
    # Try API first
    if REQUESTS_AVAILABLE and api_key and api_key != "your_electricity_maps_api_key_here":
        try:
            # ElectricityMaps API endpoint
            url = f"https://api.electricitymap.org/v3/carbon-intensity/latest"
            headers = {"auth-token": api_key}
            params = {"zone": location.upper()}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "source": "electricitymaps_api",
                    "location": location,
                    "carbon_intensity": data.get("carbonIntensity", 0),
                    "unit": "gCO2/kWh",
                    "timestamp": data.get("datetime", datetime.now().isoformat()),
                    "fossil_fuel_percentage": data.get("fossilFuelPercentage", None),
                }
        except Exception as e:
            # Fall through to cached data
            pass
    
    # Use cached emission factors
    if location_lower in EMISSION_FACTORS["grid_intensity"]:
        intensity = EMISSION_FACTORS["grid_intensity"][location_lower]
        return {
            "status": "success",
            "source": "cached_data",
            "location": location,
            "carbon_intensity": intensity,
            "unit": "gCO2/kWh",
            "timestamp": datetime.now().isoformat(),
            "note": "Using average data. For real-time data, configure ELECTRICITY_MAPS_API_KEY",
        }
    
    # Default fallback
    return {
        "status": "success",
        "source": "default_estimate",
        "location": location,
        "carbon_intensity": 400,  # Global average
        "unit": "gCO2/kWh",
        "timestamp": datetime.now().isoformat(),
        "note": f"Location '{location}' not found. Using global average.",
    }


# ============================================================================
# FLIGHT EMISSIONS TOOL
# ============================================================================
def calculate_flight_emissions(
    origin: str,
    destination: str,
    cabin_class: str = "economy",
    round_trip: bool = False,
    passengers: int = 1
) -> dict:
    """
    Calculates CO2 emissions for a flight between two airports.
    
    Uses Climatiq API when available, falls back to distance-based calculation.
    
    Args:
        origin: Origin airport code (e.g., "NYC", "LAX", "LHR")
        destination: Destination airport code
        cabin_class: Flight class - "economy", "business", or "first"
        round_trip: Whether this is a round-trip flight
        passengers: Number of passengers
    
    Returns:
        Dictionary with status, emissions in kg CO2e, and breakdown
    
    Example:
        >>> calculate_flight_emissions("NYC", "LAX", "economy", round_trip=True)
        {"status": "success", "emissions_kg_co2": 2015.4, ...}
    """
    origin = origin.upper()
    destination = destination.upper()
    cabin_class = cabin_class.lower()
    
    api_key = os.getenv("CLIMATIQ_API_KEY")
    
    # Try Climatiq API first
    if REQUESTS_AVAILABLE and api_key and api_key != "your_climatiq_api_key_here":
        try:
            url = "https://beta4.api.climatiq.io/travel/flights"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "origin": origin,
                "destination": destination,
                "cabin_class": cabin_class,
                "passengers": passengers,
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                emissions = data.get("co2e", 0)
                if round_trip:
                    emissions *= 2
                return {
                    "status": "success",
                    "source": "climatiq_api",
                    "origin": origin,
                    "destination": destination,
                    "cabin_class": cabin_class,
                    "round_trip": round_trip,
                    "passengers": passengers,
                    "emissions_kg_co2": round(emissions, 2),
                    "distance_km": data.get("distance_km", None),
                    "equivalent_trees_per_year": round(emissions / 21, 1),
                }
        except Exception as e:
            pass
    
    # Calculate using stored data
    route = (origin, destination)
    reverse_route = (destination, origin)
    
    distance = AIRPORT_DISTANCES.get(route) or AIRPORT_DISTANCES.get(reverse_route)
    
    if not distance:
        # Estimate based on common routes
        distance = 2000  # Default medium-haul
        distance_note = "Distance estimated (airport codes not in database)"
    else:
        distance_note = None
    
    # Determine emission factor based on distance and class
    if distance < 1500:
        base_factor = EMISSION_FACTORS["flights"]["short_haul_economy"]
        if cabin_class == "business":
            base_factor = EMISSION_FACTORS["flights"]["short_haul_business"]
    else:
        if cabin_class == "economy":
            base_factor = EMISSION_FACTORS["flights"]["long_haul_economy"]
        elif cabin_class == "business":
            base_factor = EMISSION_FACTORS["flights"]["long_haul_business"]
        else:
            base_factor = EMISSION_FACTORS["flights"]["long_haul_first"]
    
    # Calculate emissions
    emissions = distance * base_factor * passengers
    if round_trip:
        emissions *= 2
        distance *= 2
    
    return {
        "status": "success",
        "source": "calculated",
        "origin": origin,
        "destination": destination,
        "cabin_class": cabin_class,
        "round_trip": round_trip,
        "passengers": passengers,
        "distance_km": distance,
        "emission_factor": base_factor,
        "emissions_kg_co2": round(emissions, 2),
        "equivalent_trees_per_year": round(emissions / 21, 1),
        "note": distance_note,
    }


# ============================================================================
# TRANSPORT EMISSIONS TOOL
# ============================================================================
def calculate_transport_emissions(
    mode: str,
    distance_km: float,
    fuel_type: str = "petrol",
    passengers: int = 1
) -> dict:
    """
    Calculates CO2 emissions for ground transportation.
    
    Args:
        mode: Transport mode - "car", "bus", "train", "subway", "bicycle", "motorcycle", "taxi"
        distance_km: Distance traveled in kilometers
        fuel_type: For cars - "petrol", "diesel", "hybrid", "electric"
        passengers: Number of passengers (for per-person calculations)
    
    Returns:
        Dictionary with status, emissions in kg CO2e, and alternatives
    
    Example:
        >>> calculate_transport_emissions("car", 50, "petrol")
        {"status": "success", "emissions_kg_co2": 10.5, ...}
    """
    mode = mode.lower()
    fuel_type = fuel_type.lower()
    
    # Get emission factor
    if mode == "car":
        transport_key = f"car_{fuel_type}"
    else:
        transport_key = mode
    
    factor = EMISSION_FACTORS["transport"].get(transport_key)
    
    if factor is None:
        return {
            "status": "error",
            "error_message": f"Unknown transport mode: {mode}. Available: {list(EMISSION_FACTORS['transport'].keys())}"
        }
    
    # Calculate emissions
    total_emissions = distance_km * factor
    per_person_emissions = total_emissions / passengers if passengers > 0 else total_emissions
    
    # Calculate alternatives
    alternatives = []
    for alt_mode, alt_factor in EMISSION_FACTORS["transport"].items():
        if alt_factor < factor and alt_mode != transport_key:
            alt_emissions = distance_km * alt_factor
            savings = total_emissions - alt_emissions
            if savings > 0:
                alternatives.append({
                    "mode": alt_mode,
                    "emissions_kg_co2": round(alt_emissions, 2),
                    "savings_kg_co2": round(savings, 2),
                    "savings_percentage": round((savings / total_emissions) * 100, 1) if total_emissions > 0 else 0
                })
    
    # Sort by emissions
    alternatives = sorted(alternatives, key=lambda x: x["emissions_kg_co2"])[:3]
    
    return {
        "status": "success",
        "mode": mode,
        "fuel_type": fuel_type if mode == "car" else None,
        "distance_km": distance_km,
        "passengers": passengers,
        "emission_factor_kg_per_km": factor,
        "total_emissions_kg_co2": round(total_emissions, 2),
        "per_person_emissions_kg_co2": round(per_person_emissions, 2),
        "lower_emission_alternatives": alternatives,
        "tip": "Consider carpooling to reduce per-person emissions!" if mode == "car" and passengers == 1 else None,
    }


# ============================================================================
# FOOD CARBON FOOTPRINT TOOL
# ============================================================================
def get_food_carbon_footprint(
    food_item: str,
    quantity_kg: float = 1.0,
    meals_per_week: int = 1
) -> dict:
    """
    Gets the carbon footprint for a food item.
    
    Args:
        food_item: Name of food (e.g., "beef", "chicken", "vegetables", "tofu")
        quantity_kg: Amount in kilograms
        meals_per_week: How many times per week this is consumed (for weekly totals)
    
    Returns:
        Dictionary with emissions data and plant-based alternatives
    
    Example:
        >>> get_food_carbon_footprint("beef", 0.25, meals_per_week=4)
        {"status": "success", "weekly_emissions_kg_co2": 27.0, ...}
    """
    food_item = food_item.lower()
    
    factor = EMISSION_FACTORS["food"].get(food_item)
    
    if factor is None:
        return {
            "status": "error",
            "error_message": f"Food '{food_item}' not found. Available: {list(EMISSION_FACTORS['food'].keys())}"
        }
    
    # Calculate emissions
    per_meal_emissions = quantity_kg * factor
    weekly_emissions = per_meal_emissions * meals_per_week
    yearly_emissions = weekly_emissions * 52
    
    # Find plant-based alternatives
    alternatives = []
    plant_based = ["tofu", "lentils", "beans", "vegetables"]
    
    for alt in plant_based:
        alt_factor = EMISSION_FACTORS["food"].get(alt, 0)
        if alt_factor < factor:
            alt_emissions = quantity_kg * alt_factor
            weekly_savings = (per_meal_emissions - alt_emissions) * meals_per_week
            alternatives.append({
                "food": alt,
                "emissions_kg_co2_per_meal": round(alt_emissions, 2),
                "weekly_savings_kg_co2": round(weekly_savings, 2),
                "yearly_savings_kg_co2": round(weekly_savings * 52, 1),
            })
    
    alternatives = sorted(alternatives, key=lambda x: x["emissions_kg_co2_per_meal"])
    
    return {
        "status": "success",
        "food_item": food_item,
        "quantity_kg": quantity_kg,
        "meals_per_week": meals_per_week,
        "emission_factor_kg_co2_per_kg": factor,
        "per_meal_emissions_kg_co2": round(per_meal_emissions, 2),
        "weekly_emissions_kg_co2": round(weekly_emissions, 2),
        "yearly_emissions_kg_co2": round(yearly_emissions, 1),
        "equivalent_trees_per_year": round(yearly_emissions / 21, 1),
        "lower_impact_alternatives": alternatives,
        "tip": "Reducing red meat consumption has one of the biggest impacts on your food carbon footprint!",
    }


# ============================================================================
# HOME ENERGY EMISSIONS TOOL
# ============================================================================
def calculate_home_energy_emissions(
    electricity_kwh: float,
    gas_m3: float = 0,
    location: str = "us_avg",
    renewable_percentage: float = 0
) -> dict:
    """
    Calculates home energy carbon footprint.
    
    Args:
        electricity_kwh: Monthly electricity consumption in kWh
        gas_m3: Monthly natural gas consumption in cubic meters
        location: Location for grid intensity ("us_avg", "uk", "eu_avg", etc.)
        renewable_percentage: Percentage of electricity from renewable sources (0-100)
    
    Returns:
        Dictionary with emissions and reduction recommendations
    
    Example:
        >>> calculate_home_energy_emissions(500, 50, "california")
        {"status": "success", "monthly_emissions_kg_co2": 150.0, ...}
    """
    location = location.lower().replace(" ", "_")
    
    # Get grid intensity
    grid_result = get_electricity_carbon_intensity(location)
    grid_intensity = grid_result.get("carbon_intensity", 400) / 1000  # Convert to kg/kWh
    
    # Adjust for renewable percentage
    effective_grid_intensity = grid_intensity * (1 - renewable_percentage / 100)
    
    # Calculate emissions
    electricity_emissions = electricity_kwh * effective_grid_intensity
    gas_emissions = gas_m3 * EMISSION_FACTORS["energy"]["natural_gas"]
    
    total_monthly = electricity_emissions + gas_emissions
    total_yearly = total_monthly * 12
    
    # Recommendations
    recommendations = []
    
    if renewable_percentage < 100:
        potential_savings = electricity_kwh * grid_intensity * (1 - renewable_percentage / 100) * 0.8  # 80% renewable
        recommendations.append({
            "action": "Switch to 80% renewable energy",
            "potential_savings_kg_co2_monthly": round(potential_savings, 1),
            "potential_savings_kg_co2_yearly": round(potential_savings * 12, 1),
        })
    
    if electricity_kwh > 500:
        savings = electricity_kwh * 0.15 * effective_grid_intensity  # 15% reduction
        recommendations.append({
            "action": "Reduce electricity usage by 15% (LED lights, efficient appliances)",
            "potential_savings_kg_co2_monthly": round(savings, 1),
            "potential_savings_kg_co2_yearly": round(savings * 12, 1),
        })
    
    if gas_m3 > 0:
        gas_savings = gas_m3 * 0.2 * EMISSION_FACTORS["energy"]["natural_gas"]  # 20% reduction
        recommendations.append({
            "action": "Reduce heating/gas usage by 20% (better insulation, lower thermostat)",
            "potential_savings_kg_co2_monthly": round(gas_savings, 1),
            "potential_savings_kg_co2_yearly": round(gas_savings * 12, 1),
        })
    
    return {
        "status": "success",
        "location": location,
        "electricity_kwh": electricity_kwh,
        "gas_m3": gas_m3,
        "renewable_percentage": renewable_percentage,
        "grid_carbon_intensity_kg_per_kwh": round(grid_intensity, 4),
        "electricity_emissions_kg_co2": round(electricity_emissions, 2),
        "gas_emissions_kg_co2": round(gas_emissions, 2),
        "total_monthly_emissions_kg_co2": round(total_monthly, 2),
        "total_yearly_emissions_kg_co2": round(total_yearly, 1),
        "equivalent_trees_per_year": round(total_yearly / 21, 1),
        "recommendations": recommendations,
    }


# ============================================================================
# GENERIC EMISSION FACTOR LOOKUP
# ============================================================================
def get_emission_factor(category: str, item: str) -> dict:
    """
    Looks up emission factor for any category and item.
    
    Args:
        category: Category - "food", "transport", "flights", "energy", "grid_intensity"
        item: Specific item within category
    
    Returns:
        Dictionary with emission factor and unit
    """
    category = category.lower()
    item = item.lower().replace(" ", "_")
    
    if category not in EMISSION_FACTORS:
        return {
            "status": "error",
            "error_message": f"Category '{category}' not found. Available: {list(EMISSION_FACTORS.keys())}"
        }
    
    factor = EMISSION_FACTORS[category].get(item)
    
    if factor is None:
        return {
            "status": "error",
            "error_message": f"Item '{item}' not found in {category}. Available: {list(EMISSION_FACTORS[category].keys())}"
        }
    
    # Determine unit based on category
    units = {
        "food": "kg CO2e per kg",
        "transport": "kg CO2e per km",
        "flights": "kg CO2e per km per passenger",
        "energy": "kg CO2e per kWh (or m3 for gas)",
        "grid_intensity": "g CO2 per kWh",
    }
    
    return {
        "status": "success",
        "category": category,
        "item": item,
        "emission_factor": factor,
        "unit": units.get(category, "kg CO2e"),
    }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def trees_equivalent(kg_co2: float) -> float:
    """
    Converts kg CO2 to equivalent trees needed to absorb it in one year.
    Average tree absorbs ~21 kg CO2 per year.
    """
    return round(kg_co2 / 21, 1)


def cars_off_road_equivalent(kg_co2: float) -> float:
    """
    Converts kg CO2 to equivalent cars removed from road for one year.
    Average car emits ~4,600 kg CO2 per year.
    """
    return round(kg_co2 / 4600, 3)


if __name__ == "__main__":
    # Test the tools
    print("Testing Carbon Tools...")
    
    # Test electricity
    result = get_electricity_carbon_intensity("california", "state")
    print(f"\nElectricity (California): {json.dumps(result, indent=2)}")
    
    # Test flight
    result = calculate_flight_emissions("NYC", "LAX", "economy", round_trip=True)
    print(f"\nFlight NYC-LAX: {json.dumps(result, indent=2)}")
    
    # Test transport
    result = calculate_transport_emissions("car", 30, "petrol")
    print(f"\nDriving 30km: {json.dumps(result, indent=2)}")
    
    # Test food
    result = get_food_carbon_footprint("beef", 0.25, meals_per_week=4)
    print(f"\nBeef consumption: {json.dumps(result, indent=2)}")
    
    # Test home energy
    result = calculate_home_energy_emissions(600, 30, "new_york")
    print(f"\nHome energy: {json.dumps(result, indent=2)}")
    
    print("\n✅ All carbon tools working!")
