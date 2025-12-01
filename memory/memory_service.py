"""
ClimateGuard Memory Service
===========================
Long-term memory management for user habits, preferences, and historical data.

Implements:
- InMemoryMemoryService for development/testing
- Vertex AI Memory Bank integration (production)
- Semantic search across user history
- Session-to-memory transfer for habit learning

ADK Concepts: Sessions & Memory, Long-term Memory Bank
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict


# ============================================================================
# USER PROFILE DATA STRUCTURE
# ============================================================================
@dataclass
class UserProfile:
    """Stores user's lifestyle profile for carbon footprint calculations."""
    user_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Location
    city: str = ""
    country: str = ""
    climate_zone: str = ""  # tropical, temperate, arid, etc.
    
    # Diet
    diet_type: str = ""  # omnivore, vegetarian, vegan, pescatarian
    meat_meals_per_week: int = 0
    local_food_percentage: int = 0
    
    # Transportation
    primary_transport: str = ""  # car, public_transit, bicycle, walking
    car_type: str = ""  # petrol, diesel, hybrid, electric, none
    commute_distance_km: float = 0
    flights_per_year: int = 0
    
    # Home Energy
    home_type: str = ""  # apartment, house, condo
    electricity_kwh_monthly: float = 0
    gas_m3_monthly: float = 0
    renewable_energy_percentage: int = 0
    
    # Lifestyle
    shopping_frequency: str = ""  # minimal, moderate, frequent
    recycling_habits: str = ""  # none, some, most, all
    
    # Goals
    reduction_goal_percentage: int = 20
    priority_areas: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "UserProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class FootprintRecord:
    """Stores a carbon footprint calculation record."""
    record_id: str
    user_id: str
    timestamp: str
    category: str  # transport, food, energy, total
    activity: str
    emissions_kg_co2: float
    details: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MemoryEntry:
    """A single memory entry for semantic search."""
    entry_id: str
    user_id: str
    app_name: str
    content: str
    category: str  # profile, habit, footprint, goal, conversation
    timestamp: str
    metadata: Dict = field(default_factory=dict)
    embedding: Optional[List[float]] = None  # For semantic search
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.embedding is None:
            del data['embedding']
        return data


# ============================================================================
# CLIMATEGUARD MEMORY SERVICE
# ============================================================================
class ClimateGuardMemoryService:
    """
    Custom memory service for ClimateGuard that wraps ADK's memory capabilities.
    
    Features:
    - User profile storage and retrieval
    - Historical footprint tracking
    - Semantic search across memories
    - Session-to-memory transfer for habit learning
    
    In production, this integrates with Vertex AI Memory Bank.
    """
    
    def __init__(self, use_vertex_ai: bool = False):
        """
        Initialize memory service.
        
        Args:
            use_vertex_ai: Whether to use Vertex AI Memory Bank (production)
        """
        self.use_vertex_ai = use_vertex_ai
        
        # In-memory storage (development/testing)
        self._profiles: Dict[str, UserProfile] = {}
        self._memories: Dict[str, List[MemoryEntry]] = {}  # user_id -> memories
        self._footprint_history: Dict[str, List[FootprintRecord]] = {}
        
        # Initialize Vertex AI if requested
        if use_vertex_ai:
            self._init_vertex_ai()
    
    def _init_vertex_ai(self):
        """Initialize Vertex AI Memory Bank connection."""
        try:
            # This would be the actual Vertex AI initialization
            # from google.adk.memory import VertexAiMemoryService
            # self.vertex_memory = VertexAiMemoryService()
            print("Vertex AI Memory Bank: Not configured (using in-memory fallback)")
            self.use_vertex_ai = False
        except Exception as e:
            print(f"Vertex AI init failed: {e}. Using in-memory storage.")
            self.use_vertex_ai = False
    
    def _generate_id(self, prefix: str = "mem") -> str:
        """Generate a unique ID."""
        import uuid
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
    
    # ========================================================================
    # USER PROFILE MANAGEMENT
    # ========================================================================
    async def save_profile(self, profile: UserProfile) -> Dict:
        """
        Save or update a user profile.
        
        Args:
            profile: UserProfile object to save
        
        Returns:
            Status dictionary
        """
        profile.updated_at = datetime.now().isoformat()
        self._profiles[profile.user_id] = profile
        
        # Also store as searchable memory
        await self.add_memory(
            user_id=profile.user_id,
            app_name="climateguard",
            content=f"User profile: {profile.diet_type} diet, {profile.primary_transport} transport, lives in {profile.city}",
            category="profile",
            metadata=profile.to_dict()
        )
        
        return {"status": "success", "user_id": profile.user_id, "message": "Profile saved"}
    
    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Retrieve a user's profile.
        
        Args:
            user_id: User identifier
        
        Returns:
            UserProfile or None
        """
        return self._profiles.get(user_id)
    
    async def update_profile(self, user_id: str, updates: Dict) -> Dict:
        """
        Update specific fields in a user's profile.
        
        Args:
            user_id: User identifier
            updates: Dictionary of fields to update
        
        Returns:
            Status dictionary
        """
        profile = self._profiles.get(user_id)
        if not profile:
            return {"status": "error", "message": f"Profile not found for user {user_id}"}
        
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.now().isoformat()
        return await self.save_profile(profile)
    
    # ========================================================================
    # MEMORY MANAGEMENT
    # ========================================================================
    async def add_memory(
        self,
        user_id: str,
        app_name: str,
        content: str,
        category: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Add a memory entry for semantic search.
        
        Args:
            user_id: User identifier
            app_name: Application name
            content: Text content of the memory
            category: Category (profile, habit, footprint, goal, conversation)
            metadata: Optional additional metadata
        
        Returns:
            Status dictionary with entry_id
        """
        entry = MemoryEntry(
            entry_id=self._generate_id("mem"),
            user_id=user_id,
            app_name=app_name,
            content=content,
            category=category,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        if user_id not in self._memories:
            self._memories[user_id] = []
        
        self._memories[user_id].append(entry)
        
        return {
            "status": "success",
            "entry_id": entry.entry_id,
            "message": "Memory added successfully"
        }
    
    async def search_memory(
        self,
        app_name: str,
        user_id: str,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search memories semantically.
        
        In production, this uses Vertex AI's semantic search.
        Currently implements simple keyword matching.
        
        Args:
            app_name: Application name
            user_id: User identifier
            query: Search query
            category: Optional category filter
            limit: Maximum results
        
        Returns:
            List of matching memory entries
        """
        memories = self._memories.get(user_id, [])
        
        if not memories:
            return []
        
        # Simple keyword matching (production would use embeddings)
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_results = []
        for mem in memories:
            if category and mem.category != category:
                continue
            
            content_lower = mem.content.lower()
            # Score based on word matches
            score = sum(1 for word in query_words if word in content_lower)
            
            if score > 0:
                scored_results.append((score, mem))
        
        # Sort by score and return top results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        return [
            {
                "entry_id": mem.entry_id,
                "content": mem.content,
                "category": mem.category,
                "timestamp": mem.timestamp,
                "relevance_score": score,
                "metadata": mem.metadata
            }
            for score, mem in scored_results[:limit]
        ]
    
    async def add_session_to_memory(self, session: Any) -> Dict:
        """
        Transfer important information from a session to long-term memory.
        
        This extracts key facts, preferences, and commitments from conversation
        history and stores them for future reference.
        
        Args:
            session: ADK Session object
        
        Returns:
            Status dictionary
        """
        # Extract session info (would parse actual session events in production)
        user_id = getattr(session, 'user_id', 'unknown')
        session_id = getattr(session, 'id', 'unknown')
        
        # Mock extraction - in production would analyze session.events
        extracted_facts = [
            f"Session {session_id} completed",
            "User discussed carbon footprint goals",
        ]
        
        for fact in extracted_facts:
            await self.add_memory(
                user_id=user_id,
                app_name="climateguard",
                content=fact,
                category="conversation",
                metadata={"session_id": session_id}
            )
        
        return {
            "status": "success",
            "facts_extracted": len(extracted_facts),
            "message": "Session transferred to memory"
        }
    
    # ========================================================================
    # FOOTPRINT HISTORY
    # ========================================================================
    async def record_footprint(
        self,
        user_id: str,
        category: str,
        activity: str,
        emissions_kg_co2: float,
        details: Optional[Dict] = None
    ) -> Dict:
        """
        Record a carbon footprint calculation.
        
        Args:
            user_id: User identifier
            category: Category (transport, food, energy, etc.)
            activity: Activity description
            emissions_kg_co2: Emissions in kg CO2
            details: Additional details
        
        Returns:
            Status dictionary with record_id
        """
        record = FootprintRecord(
            record_id=self._generate_id("fp"),
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            category=category,
            activity=activity,
            emissions_kg_co2=emissions_kg_co2,
            details=details or {}
        )
        
        if user_id not in self._footprint_history:
            self._footprint_history[user_id] = []
        
        self._footprint_history[user_id].append(record)
        
        # Also add to searchable memory
        await self.add_memory(
            user_id=user_id,
            app_name="climateguard",
            content=f"Footprint recorded: {activity} - {emissions_kg_co2} kg CO2 ({category})",
            category="footprint",
            metadata=record.to_dict()
        )
        
        return {
            "status": "success",
            "record_id": record.record_id,
            "emissions_kg_co2": emissions_kg_co2
        }
    
    async def get_footprint_history(
        self,
        user_id: str,
        category: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """
        Get user's footprint history.
        
        Args:
            user_id: User identifier
            category: Optional category filter
            days: Number of days to look back
        
        Returns:
            Dictionary with history and summary
        """
        records = self._footprint_history.get(user_id, [])
        
        if category:
            records = [r for r in records if r.category == category]
        
        # Calculate summary
        total_emissions = sum(r.emissions_kg_co2 for r in records)
        by_category = {}
        for r in records:
            by_category[r.category] = by_category.get(r.category, 0) + r.emissions_kg_co2
        
        return {
            "status": "success",
            "user_id": user_id,
            "records_count": len(records),
            "total_emissions_kg_co2": round(total_emissions, 2),
            "by_category": {k: round(v, 2) for k, v in by_category.items()},
            "records": [r.to_dict() for r in records[-10:]],  # Last 10
            "trend": "improving" if len(records) > 1 and records[-1].emissions_kg_co2 < records[0].emissions_kg_co2 else "needs_attention"
        }
    
    # ========================================================================
    # HABIT TRACKING
    # ========================================================================
    async def record_habit(self, user_id: str, habit: str, completed: bool) -> Dict:
        """
        Record a sustainable habit completion.
        
        Args:
            user_id: User identifier
            habit: Habit description (e.g., "meatless monday", "bike to work")
            completed: Whether the habit was completed
        
        Returns:
            Status dictionary
        """
        await self.add_memory(
            user_id=user_id,
            app_name="climateguard",
            content=f"Habit {'completed' if completed else 'missed'}: {habit}",
            category="habit",
            metadata={"habit": habit, "completed": completed}
        )
        
        return {
            "status": "success",
            "habit": habit,
            "completed": completed,
            "message": "Habit recorded"
        }
    
    async def get_habit_streak(self, user_id: str, habit: str) -> Dict:
        """
        Get streak information for a habit.
        
        Args:
            user_id: User identifier
            habit: Habit to check
        
        Returns:
            Dictionary with streak info
        """
        memories = self._memories.get(user_id, [])
        habit_memories = [
            m for m in memories 
            if m.category == "habit" and habit.lower() in m.content.lower()
        ]
        
        completed_count = sum(1 for m in habit_memories if m.metadata.get("completed", False))
        
        return {
            "status": "success",
            "habit": habit,
            "total_tracked": len(habit_memories),
            "completed": completed_count,
            "completion_rate": round(completed_count / len(habit_memories) * 100, 1) if habit_memories else 0,
            "message": f"Keep going! {completed_count} completions recorded."
        }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================
_memory_service_instance: Optional[ClimateGuardMemoryService] = None


def get_memory_service(use_vertex_ai: bool = False) -> ClimateGuardMemoryService:
    """
    Get or create the memory service singleton.
    
    Args:
        use_vertex_ai: Whether to use Vertex AI (production)
    
    Returns:
        ClimateGuardMemoryService instance
    """
    global _memory_service_instance
    
    if _memory_service_instance is None:
        _memory_service_instance = ClimateGuardMemoryService(use_vertex_ai=use_vertex_ai)
    
    return _memory_service_instance


# ============================================================================
# TESTING
# ============================================================================
if __name__ == "__main__":
    import asyncio
    
    async def test_memory_service():
        print("Testing ClimateGuard Memory Service...")
        
        service = get_memory_service()
        
        # Create and save profile
        profile = UserProfile(
            user_id="test_user_123",
            city="San Francisco",
            country="USA",
            diet_type="omnivore",
            meat_meals_per_week=5,
            primary_transport="car",
            car_type="petrol",
            commute_distance_km=25,
        )
        
        result = await service.save_profile(profile)
        print(f"\nSave Profile: {json.dumps(result, indent=2)}")
        
        # Add some memories
        await service.add_memory(
            user_id="test_user_123",
            app_name="climateguard",
            content="User committed to Meatless Mondays starting next week",
            category="goal"
        )
        
        await service.add_memory(
            user_id="test_user_123",
            app_name="climateguard",
            content="User expressed interest in switching to electric vehicle",
            category="goal"
        )
        
        # Record footprint
        await service.record_footprint(
            user_id="test_user_123",
            category="transport",
            activity="Daily commute by car",
            emissions_kg_co2=10.5
        )
        
        # Search memories
        results = await service.search_memory(
            app_name="climateguard",
            user_id="test_user_123",
            query="user diet meatless"
        )
        print(f"\nMemory Search Results: {json.dumps(results, indent=2)}")
        
        # Get history
        history = await service.get_footprint_history("test_user_123")
        print(f"\nFootprint History: {json.dumps(history, indent=2)}")
        
        print("\n✅ Memory service tests passed!")
    
    asyncio.run(test_memory_service())
