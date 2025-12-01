# ClimateGuard Tools Package
# Custom tools for carbon footprint calculation and community features

from .carbon_tools import (
    get_electricity_carbon_intensity,
    calculate_flight_emissions,
    calculate_transport_emissions,
    get_food_carbon_footprint,
    calculate_home_energy_emissions,
    get_emission_factor,
)

from .search_tools import (
    find_local_community_groups,
    search_sustainability_tips,
)

__all__ = [
    # Carbon Tools
    "get_electricity_carbon_intensity",
    "calculate_flight_emissions",
    "calculate_transport_emissions",
    "get_food_carbon_footprint",
    "calculate_home_energy_emissions",
    "get_emission_factor",
    # Search Tools
    "find_local_community_groups",
    "search_sustainability_tips",
]
