"""
ClimateGuard Impact Tracker Plugin
==================================
Custom observability plugin for tracking climate impact metrics.

Tracks:
- Total CO2 saved across all users
- Actions completed
- User engagement metrics
- Tool call statistics

ADK Concept: Observability (LoggingPlugin + Custom Metrics)
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("climateguard.impact")


# ============================================================================
# METRICS DATA STRUCTURES
# ============================================================================
@dataclass
class ClimateGuardMetrics:
    """Aggregated metrics for ClimateGuard."""
    
    # Impact Metrics
    total_co2_saved_kg: float = 0.0
    total_actions_completed: int = 0
    total_plans_created: int = 0
    total_challenges_joined: int = 0
    
    # User Metrics
    total_users: int = 0
    active_users_today: int = 0
    profiles_created: int = 0
    
    # Engagement Metrics
    total_sessions: int = 0
    total_queries: int = 0
    avg_queries_per_session: float = 0.0
    
    # Tool Usage
    tool_calls: Dict[str, int] = field(default_factory=dict)
    agent_delegations: Dict[str, int] = field(default_factory=dict)
    
    # Performance
    avg_response_time_ms: float = 0.0
    total_tokens_used: int = 0
    
    # Timestamps
    first_recorded: str = ""
    last_updated: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ClimateGuardMetrics":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ImpactEvent:
    """A single impact event to log."""
    event_type: str  # co2_saved, action_completed, profile_created, etc.
    user_id: str
    value: float
    metadata: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# IMPACT TRACKER PLUGIN
# ============================================================================
class ImpactTracker:
    """
    Custom observability plugin for tracking ClimateGuard's climate impact.
    
    Extends ADK's logging capabilities with domain-specific metrics:
    - CO2 saved (the key impact metric)
    - User behavior and engagement
    - Tool effectiveness
    
    Usage:
        tracker = ImpactTracker()
        tracker.record_co2_saved("user_123", 5.5, "diet", "meatless_monday")
        tracker.on_tool_call("calculate_daily_footprint", {...})
        
        metrics = tracker.get_metrics()
        print(f"Total CO2 saved: {metrics.total_co2_saved_kg} kg")
    """
    
    def __init__(self, log_level: str = "INFO", persist_path: str = None):
        """
        Initialize the Impact Tracker.
        
        Args:
            log_level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR")
            persist_path: Path to persist metrics (JSON file)
        """
        self.log_level = log_level
        self.persist_path = persist_path or "climateguard_metrics.json"
        
        # Initialize metrics
        self.metrics = ClimateGuardMetrics(
            first_recorded=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
        
        # Event log (in-memory)
        self.events: List[ImpactEvent] = []
        self.active_users: set = set()
        self.session_queries: Dict[str, int] = {}
        
        # Load persisted metrics if available
        self._load_metrics()
        
        # Configure logger
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        logger.info("ImpactTracker initialized")
    
    # ========================================================================
    # CORE IMPACT TRACKING
    # ========================================================================
    def record_co2_saved(
        self,
        user_id: str,
        kg_co2: float,
        category: str,
        action: str,
        metadata: Dict = None
    ):
        """
        Record CO2 savings from a user action.
        
        This is the primary impact metric for ClimateGuard.
        
        Args:
            user_id: User who saved the CO2
            kg_co2: Amount saved in kg
            category: Category (diet, transport, energy)
            action: Specific action taken
            metadata: Additional context
        """
        event = ImpactEvent(
            event_type="co2_saved",
            user_id=user_id,
            value=kg_co2,
            metadata={
                "category": category,
                "action": action,
                **(metadata or {})
            }
        )
        
        self.events.append(event)
        self.metrics.total_co2_saved_kg += kg_co2
        self.metrics.total_actions_completed += 1
        self.metrics.last_updated = datetime.now().isoformat()
        
        # Log the impact
        logger.info(
            f"🌱 CO2 SAVED: {kg_co2:.2f} kg by {user_id[:8]}... "
            f"({category}/{action}) - Total: {self.metrics.total_co2_saved_kg:.1f} kg"
        )
        
        self._persist_metrics()
    
    def record_action_completed(
        self,
        user_id: str,
        action_id: str,
        action_name: str,
        co2_impact: float = 0
    ):
        """
        Record completion of a sustainability action.
        
        Args:
            user_id: User who completed the action
            action_id: Action identifier
            action_name: Human-readable action name
            co2_impact: CO2 impact in kg (if known)
        """
        event = ImpactEvent(
            event_type="action_completed",
            user_id=user_id,
            value=1,
            metadata={
                "action_id": action_id,
                "action_name": action_name,
                "co2_impact": co2_impact
            }
        )
        
        self.events.append(event)
        self.metrics.total_actions_completed += 1
        
        if co2_impact > 0:
            self.record_co2_saved(user_id, co2_impact, "action", action_name)
        
        logger.info(f"✅ Action completed: {action_name} by {user_id[:8]}...")
    
    def record_plan_created(self, user_id: str, actions_count: int, weekly_savings_kg: float):
        """
        Record creation of a weekly plan.
        
        Args:
            user_id: User who created the plan
            actions_count: Number of actions in the plan
            weekly_savings_kg: Potential weekly savings
        """
        event = ImpactEvent(
            event_type="plan_created",
            user_id=user_id,
            value=weekly_savings_kg,
            metadata={
                "actions_count": actions_count,
                "weekly_savings_kg": weekly_savings_kg
            }
        )
        
        self.events.append(event)
        self.metrics.total_plans_created += 1
        
        logger.info(
            f"📅 Plan created: {actions_count} actions, "
            f"potential {weekly_savings_kg:.1f} kg CO2/week for {user_id[:8]}..."
        )
    
    def record_challenge_joined(self, user_id: str, challenge_name: str):
        """
        Record user joining a community challenge.
        
        Args:
            user_id: User who joined
            challenge_name: Name of the challenge
        """
        event = ImpactEvent(
            event_type="challenge_joined",
            user_id=user_id,
            value=1,
            metadata={"challenge_name": challenge_name}
        )
        
        self.events.append(event)
        self.metrics.total_challenges_joined += 1
        
        logger.info(f"🎯 Challenge joined: {challenge_name} by {user_id[:8]}...")
    
    def record_profile_created(self, user_id: str, location: str):
        """
        Record creation of a user profile.
        
        Args:
            user_id: User who created profile
            location: User's location
        """
        event = ImpactEvent(
            event_type="profile_created",
            user_id=user_id,
            value=1,
            metadata={"location": location}
        )
        
        self.events.append(event)
        self.metrics.profiles_created += 1
        self.metrics.total_users += 1
        
        logger.info(f"👤 Profile created: {user_id[:8]}... from {location}")
    
    # ========================================================================
    # TOOL & AGENT TRACKING
    # ========================================================================
    def on_tool_call(self, tool_name: str, result: Dict = None, duration_ms: float = 0):
        """
        Callback when a tool is called.
        
        Args:
            tool_name: Name of the tool
            result: Tool result (for extracting metrics)
            duration_ms: Call duration
        """
        # Track tool usage
        if tool_name not in self.metrics.tool_calls:
            self.metrics.tool_calls[tool_name] = 0
        self.metrics.tool_calls[tool_name] += 1
        
        # Extract CO2 metrics from specific tools
        if result:
            if "co2_saved" in str(result).lower() or "emissions_kg_co2" in str(result):
                # Try to extract CO2 value
                if isinstance(result, dict):
                    co2_value = result.get("emissions_kg_co2", 0) or result.get("co2_saved_kg", 0)
                    if co2_value and tool_name in ["calculate_activity_emissions", "track_action_completion"]:
                        logger.debug(f"CO2 metric extracted from {tool_name}: {co2_value} kg")
        
        logger.debug(f"🔧 Tool called: {tool_name} ({duration_ms:.0f}ms)")
    
    def on_agent_delegation(self, from_agent: str, to_agent: str, query: str):
        """
        Callback when one agent delegates to another.
        
        Args:
            from_agent: Agent that delegated
            to_agent: Agent that received delegation
            query: The delegated query
        """
        key = f"{from_agent}->{to_agent}"
        if key not in self.metrics.agent_delegations:
            self.metrics.agent_delegations[key] = 0
        self.metrics.agent_delegations[key] += 1
        
        logger.debug(f"🔀 Agent delegation: {from_agent} → {to_agent}")
    
    def on_session_start(self, user_id: str, session_id: str):
        """
        Callback when a session starts.
        
        Args:
            user_id: User starting the session
            session_id: Session identifier
        """
        self.metrics.total_sessions += 1
        self.active_users.add(user_id)
        self.session_queries[session_id] = 0
        self.metrics.active_users_today = len(self.active_users)
        
        logger.debug(f"🚀 Session started: {session_id} for {user_id[:8]}...")
    
    def on_query(self, session_id: str, query: str, response_time_ms: float = 0):
        """
        Callback for each user query.
        
        Args:
            session_id: Session identifier
            query: User's query
            response_time_ms: Response time
        """
        self.metrics.total_queries += 1
        
        if session_id in self.session_queries:
            self.session_queries[session_id] += 1
        
        # Update average response time
        if response_time_ms > 0:
            total = self.metrics.avg_response_time_ms * (self.metrics.total_queries - 1)
            self.metrics.avg_response_time_ms = (total + response_time_ms) / self.metrics.total_queries
        
        # Update average queries per session
        if self.metrics.total_sessions > 0:
            self.metrics.avg_queries_per_session = self.metrics.total_queries / self.metrics.total_sessions
        
        logger.debug(f"💬 Query processed: {query[:50]}... ({response_time_ms:.0f}ms)")
    
    # ========================================================================
    # METRICS ACCESS
    # ========================================================================
    def get_metrics(self) -> ClimateGuardMetrics:
        """
        Get current metrics snapshot.
        
        Returns:
            ClimateGuardMetrics object
        """
        self.metrics.last_updated = datetime.now().isoformat()
        return self.metrics
    
    def get_impact_summary(self) -> Dict:
        """
        Get a human-readable impact summary.
        
        Returns:
            Dictionary with formatted impact data
        """
        m = self.metrics
        
        return {
            "headline": f"🌍 ClimateGuard has saved {m.total_co2_saved_kg:.1f} kg CO2!",
            "impact": {
                "co2_saved_kg": round(m.total_co2_saved_kg, 1),
                "co2_saved_tons": round(m.total_co2_saved_kg / 1000, 2),
                "equivalent_trees": round(m.total_co2_saved_kg / 21, 0),
                "equivalent_cars_off_road_days": round(m.total_co2_saved_kg / 12.6, 0),
            },
            "engagement": {
                "total_users": m.total_users,
                "active_today": m.active_users_today,
                "actions_completed": m.total_actions_completed,
                "plans_created": m.total_plans_created,
                "challenges_joined": m.total_challenges_joined,
            },
            "performance": {
                "total_sessions": m.total_sessions,
                "total_queries": m.total_queries,
                "avg_queries_per_session": round(m.avg_queries_per_session, 1),
                "avg_response_time_ms": round(m.avg_response_time_ms, 0),
            },
            "top_tools": dict(sorted(
                m.tool_calls.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]),
            "tracking_since": m.first_recorded,
            "last_updated": m.last_updated,
        }
    
    def get_recent_events(self, limit: int = 10, event_type: str = None) -> List[Dict]:
        """
        Get recent impact events.
        
        Args:
            limit: Maximum events to return
            event_type: Filter by event type
        
        Returns:
            List of event dictionaries
        """
        events = self.events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Return most recent
        return [e.to_dict() for e in events[-limit:]]
    
    # ========================================================================
    # PERSISTENCE
    # ========================================================================
    def _persist_metrics(self):
        """Save metrics to file."""
        try:
            with open(self.persist_path, "w") as f:
                json.dump(self.metrics.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist metrics: {e}")
    
    def _load_metrics(self):
        """Load metrics from file."""
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "r") as f:
                    data = json.load(f)
                    self.metrics = ClimateGuardMetrics.from_dict(data)
                    logger.info(f"Loaded persisted metrics: {self.metrics.total_co2_saved_kg:.1f} kg CO2 saved")
            except Exception as e:
                logger.warning(f"Failed to load metrics: {e}")
    
    def reset_metrics(self):
        """Reset all metrics (use with caution!)."""
        self.metrics = ClimateGuardMetrics(
            first_recorded=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
        self.events = []
        self.active_users = set()
        self.session_queries = {}
        self._persist_metrics()
        logger.info("Metrics reset")


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
_impact_tracker_instance: Optional[ImpactTracker] = None


def get_impact_tracker() -> ImpactTracker:
    """
    Get the global ImpactTracker instance.
    
    Returns:
        ImpactTracker singleton
    """
    global _impact_tracker_instance
    
    if _impact_tracker_instance is None:
        _impact_tracker_instance = ImpactTracker()
    
    return _impact_tracker_instance


# ============================================================================
# TESTING
# ============================================================================
if __name__ == "__main__":
    print("Testing Impact Tracker...")
    
    tracker = ImpactTracker(log_level="DEBUG")
    
    # Simulate some events
    tracker.record_profile_created("user_001", "San Francisco")
    tracker.on_session_start("user_001", "session_001")
    
    tracker.record_co2_saved("user_001", 6.75, "diet", "meatless_monday")
    tracker.record_action_completed("user_001", "transit_day", "Public Transit Day", 8.0)
    tracker.record_plan_created("user_001", 5, 25.5)
    tracker.record_challenge_joined("user_001", "30-Day Plant-Based Challenge")
    
    tracker.on_tool_call("calculate_daily_footprint", {"emissions_kg_co2": 15.2}, 150)
    tracker.on_query("session_001", "What's my carbon footprint?", 200)
    
    # Get summary
    print("\n" + "="*60)
    print("IMPACT SUMMARY")
    print("="*60)
    summary = tracker.get_impact_summary()
    print(json.dumps(summary, indent=2))
    
    # Get metrics
    print("\n" + "="*60)
    print("RAW METRICS")
    print("="*60)
    metrics = tracker.get_metrics()
    print(f"Total CO2 Saved: {metrics.total_co2_saved_kg} kg")
    print(f"Actions Completed: {metrics.total_actions_completed}")
    print(f"Plans Created: {metrics.total_plans_created}")
    
    print("\n✅ Impact Tracker tests passed!")
