"""
ClimateGuard Test Suite
Unit tests for the multi-agent carbon footprint coach
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass

# Test fixtures and mocks for ADK components
# These tests validate the logic without requiring actual API calls


class TestCarbonTools:
    """Tests for carbon calculation tools"""
    
    def test_transport_emissions_car(self):
        """Test car emission calculations"""
        from tools.carbon_tools import calculate_transport_emissions
        
        result = calculate_transport_emissions("car", 100)  # 100 km
        
        assert "co2_kg" in result
        assert result["co2_kg"] > 0
        assert result["transport_type"] == "car"
        assert "tip" in result
    
    def test_transport_emissions_bike(self):
        """Test bike emission calculations (should be zero)"""
        from tools.carbon_tools import calculate_transport_emissions
        
        result = calculate_transport_emissions("bike", 50)
        
        assert result["co2_kg"] == 0
        assert "tip" in result
    
    def test_transport_emissions_electric_car(self):
        """Test electric car emissions are lower than regular car"""
        from tools.carbon_tools import calculate_transport_emissions
        
        car_result = calculate_transport_emissions("car", 100)
        ev_result = calculate_transport_emissions("electric_car", 100)
        
        assert ev_result["co2_kg"] < car_result["co2_kg"]
    
    def test_food_emissions_meat(self):
        """Test meat-heavy diet emissions"""
        from tools.carbon_tools import calculate_food_emissions
        
        result = calculate_food_emissions("meat_heavy")
        
        assert result["co2_kg_per_day"] > 0
        assert result["diet_type"] == "meat_heavy"
    
    def test_food_emissions_vegan(self):
        """Test vegan diet is lower than meat diet"""
        from tools.carbon_tools import calculate_food_emissions
        
        meat_result = calculate_food_emissions("meat_heavy")
        vegan_result = calculate_food_emissions("vegan")
        
        assert vegan_result["co2_kg_per_day"] < meat_result["co2_kg_per_day"]
    
    def test_energy_emissions(self):
        """Test home energy emissions calculation"""
        from tools.carbon_tools import calculate_energy_emissions
        
        result = calculate_energy_emissions(
            electricity_kwh=500,
            natural_gas_therms=30,
            country_code="US"
        )
        
        assert "electricity_co2_kg" in result
        assert "gas_co2_kg" in result
        assert "total_monthly_co2_kg" in result
        assert result["total_monthly_co2_kg"] > 0
    
    def test_carbon_offset_options(self):
        """Test offset options are returned"""
        from tools.carbon_tools import get_carbon_offset_options
        
        result = get_carbon_offset_options(1000)  # 1000 kg to offset
        
        assert "options" in result
        assert len(result["options"]) > 0
        assert all("project" in opt for opt in result["options"])


class TestSearchTools:
    """Tests for community search tools"""
    
    def test_search_community_groups(self):
        """Test community group search"""
        from tools.search_tools import search_community_groups
        
        result = search_community_groups("San Francisco", "general")
        
        assert "groups" in result
        assert isinstance(result["groups"], list)
    
    def test_get_community_challenges(self):
        """Test community challenges retrieval"""
        from tools.search_tools import get_community_challenges
        
        result = get_community_challenges()
        
        assert "challenges" in result
        assert isinstance(result["challenges"], list)


class TestMemoryService:
    """Tests for memory service"""
    
    def test_store_and_retrieve_profile(self):
        """Test storing and retrieving user profile"""
        from memory.memory_service import ClimateGuardMemoryService
        
        service = ClimateGuardMemoryService()
        
        # Store profile
        service.store_user_profile("test_user", {
            "diet": "vegetarian",
            "commute_miles": 20,
            "home_size": "apartment"
        })
        
        # Retrieve profile
        profile = service.get_user_profile("test_user")
        
        assert profile is not None
        assert profile["diet"] == "vegetarian"
    
    def test_footprint_history(self):
        """Test footprint history storage"""
        from memory.memory_service import ClimateGuardMemoryService
        
        service = ClimateGuardMemoryService()
        
        # Store multiple entries
        service.store_footprint_history("test_user", {
            "date": "2025-01-01",
            "total_co2_kg": 15.5
        })
        service.store_footprint_history("test_user", {
            "date": "2025-01-02",
            "total_co2_kg": 14.2
        })
        
        # Check history length
        history = service.get_footprint_history("test_user")
        assert len(history) == 2


class TestContextCompactor:
    """Tests for context compaction"""
    
    def test_compaction_reduces_tokens(self):
        """Test that compaction reduces event count"""
        from memory.compactor import ClimateGuardCompactor
        
        compactor = ClimateGuardCompactor(max_tokens=100)
        
        # Create mock events (long conversation)
        events = [
            {"type": "user", "content": f"Message {i}" * 10}
            for i in range(20)
        ]
        
        compacted = compactor.compact_events(events)
        
        # Compacted should have fewer events
        assert len(compacted) < len(events)
    
    def test_compaction_preserves_recent(self):
        """Test that compaction preserves recent events"""
        from memory.compactor import ClimateGuardCompactor
        
        compactor = ClimateGuardCompactor(max_tokens=100, overlap_size=3)
        
        events = [
            {"type": "user", "content": f"Message {i}"}
            for i in range(10)
        ]
        
        compacted = compactor.compact_events(events)
        
        # Last few events should be preserved
        assert events[-1]["content"] in str(compacted)


class TestAgentCreation:
    """Tests for agent creation functions"""
    
    def test_create_profile_agent(self):
        """Test profile agent creation"""
        from agents.profile import create_profile_agent
        
        agent = create_profile_agent()
        
        assert agent is not None
        assert agent.name == "profile_agent"
    
    def test_create_calculator_agent(self):
        """Test calculator agent creation"""
        from agents.calculator import create_calculator_agent
        
        agent = create_calculator_agent()
        
        assert agent is not None
        assert agent.name == "calculator_agent"
    
    def test_create_planner_agent(self):
        """Test planner agent creation"""
        from agents.planner import create_planner_agent
        
        agent = create_planner_agent()
        
        assert agent is not None
        assert agent.name == "planner_agent"
    
    def test_create_community_agent(self):
        """Test community agent creation"""
        from agents.community import create_community_agent
        
        agent = create_community_agent()
        
        assert agent is not None
        assert agent.name == "community_agent"
    
    def test_create_supervisor_agent(self):
        """Test supervisor agent creation with sub-agents"""
        from agents.supervisor import create_supervisor_agent
        
        agent = create_supervisor_agent()
        
        assert agent is not None
        assert agent.name == "climateguard_supervisor"


class TestImpactTracker:
    """Tests for the observability plugin"""
    
    def test_metrics_tracking(self):
        """Test that metrics are tracked correctly"""
        from plugins.impact_tracker import ImpactTracker, ClimateGuardMetrics
        
        tracker = ImpactTracker()
        
        # Simulate tool calls
        tracker.on_tool_call("calculate_transport_emissions", {"result": {"co2_kg": 10.5}})
        tracker.on_tool_call("calculate_food_emissions", {"result": {"co2_kg_per_day": 3.2}})
        
        metrics = tracker.get_metrics()
        
        assert metrics.total_calculations >= 2
        assert metrics.total_co2_calculated > 0
    
    def test_session_summary(self):
        """Test session summary generation"""
        from plugins.impact_tracker import ImpactTracker
        
        tracker = ImpactTracker()
        
        # Simulate some activity
        tracker.on_tool_call("calculate_transport_emissions", {"result": {"co2_kg": 10.5}})
        
        summary = tracker.get_session_summary()
        
        assert "calculations" in summary.lower() or "CO2" in summary


class TestIntegration:
    """Integration tests for the full system"""
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test a complete conversation flow"""
        # This would test the full system with mocked LLM responses
        # For actual testing, you'd use the ADK's testing utilities
        pass
    
    @pytest.mark.asyncio
    async def test_memory_persistence_across_sessions(self):
        """Test that memory persists across sessions"""
        # Test that user data is preserved
        pass


# Fixtures

@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response"""
    return {
        "candidates": [{
            "content": {
                "parts": [{"text": "Based on your profile, your carbon footprint is approximately 15 kg CO2 per day."}]
            }
        }]
    }


@pytest.fixture
def sample_user_profile():
    """Sample user profile for testing"""
    return {
        "user_id": "test_user_123",
        "diet": "vegetarian",
        "commute_type": "car",
        "commute_distance_km": 40,
        "home_type": "house",
        "home_size_sqft": 1500,
        "electricity_kwh": 600,
        "natural_gas_therms": 40
    }


@pytest.fixture
def sample_footprint():
    """Sample carbon footprint calculation"""
    return {
        "transport_co2_kg": 9.2,
        "food_co2_kg": 2.5,
        "energy_co2_kg": 3.8,
        "total_daily_co2_kg": 15.5,
        "breakdown": {
            "transport": 59,
            "food": 16,
            "energy": 25
        }
    }


# Run tests with: pytest tests/test_agents.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
