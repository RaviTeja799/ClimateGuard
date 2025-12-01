"""
ClimateGuard Supervisor Agent
=============================
Main orchestrator that coordinates all sub-agents.

Routes user queries to the appropriate specialist:
- Profile Agent: Onboarding and preferences
- Calculator Agent: Footprint calculations
- Planner Agent: Weekly action plans
- Community Agent: Social features

ADK Concepts: Multi-Agent System (Supervisor Pattern), Sessions, Observability
"""

import os
import uuid
from typing import Optional, List

# ADK Imports
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from google.adk.apps.app import App, EventsCompactionConfig, ResumabilityConfig
from google.genai import types

# Local imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.profile import create_profile_agent
from agents.calculator import create_calculator_agent
from agents.planner import create_planner_agent
from agents.community import create_community_agent
from memory.memory_service import get_memory_service
from memory.compactor import ClimateGuardCompactor


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
# SUPERVISOR TOOLS
# ============================================================================
def get_user_status(user_id: str) -> dict:
    """
    Gets the current status of a user (profile, footprint history, etc.).
    
    Args:
        user_id: User identifier
    
    Returns:
        Dictionary with user status overview
    """
    import asyncio
    
    memory_service = get_memory_service()
    
    # Check for profile
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
    
    # Check footprint history
    try:
        if profile:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, memory_service.get_footprint_history(user_id))
                    history = future.result()
            else:
                history = asyncio.run(memory_service.get_footprint_history(user_id))
        else:
            history = None
    except Exception:
        history = None
    
    has_profile = profile is not None
    has_history = history is not None and history.get("records_count", 0) > 0
    
    return {
        "status": "success",
        "user_id": user_id,
        "has_profile": has_profile,
        "profile_summary": {
            "location": f"{profile.city}, {profile.country}" if has_profile else None,
            "diet": profile.diet_type if has_profile else None,
            "transport": profile.primary_transport if has_profile else None,
        } if has_profile else None,
        "has_footprint_history": has_history,
        "footprint_records": history.get("records_count", 0) if history else 0,
        "recommended_next_step": (
            "Calculate your footprint" if has_profile and not has_history
            else "Create a weekly plan" if has_profile and has_history
            else "Complete your profile first"
        ),
    }


def summarize_session(user_id: str, session_summary: str) -> dict:
    """
    Saves a summary of the current session to memory.
    
    Args:
        user_id: User identifier
        session_summary: Summary of what was discussed/accomplished
    
    Returns:
        Dictionary with save status
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
                    memory_service.add_memory(
                        user_id=user_id,
                        app_name="climateguard",
                        content=f"Session summary: {session_summary}",
                        category="conversation"
                    )
                )
                result = future.result()
        else:
            result = asyncio.run(memory_service.add_memory(
                user_id=user_id,
                app_name="climateguard",
                content=f"Session summary: {session_summary}",
                category="conversation"
            ))
    except RuntimeError:
        result = asyncio.run(memory_service.add_memory(
            user_id=user_id,
            app_name="climateguard",
            content=f"Session summary: {session_summary}",
            category="conversation"
        ))
    
    return {
        "status": "success",
        "message": "Session summary saved",
        "summary": session_summary
    }


# ============================================================================
# SUPERVISOR AGENT CLASS
# ============================================================================
class SupervisorAgent:
    """
    Main orchestrator for ClimateGuard.
    
    Coordinates:
    - Profile Agent: User onboarding
    - Calculator Agent: Footprint calculations
    - Planner Agent: Weekly plans
    - Community Agent: Social features
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        """
        Initialize the Supervisor Agent with all sub-agents.
        
        Args:
            model_name: Gemini model to use for all agents
        """
        self.model_name = model_name
        
        # Create sub-agents
        self.profile_agent = create_profile_agent(model_name)
        self.calculator_agent = create_calculator_agent(model_name)
        self.planner_agent = create_planner_agent(model_name)
        self.community_agent = create_community_agent(model_name)
        
        # Create supervisor
        self.agent = self._create_supervisor()
    
    def _create_supervisor(self) -> LlmAgent:
        """Create the supervisor agent."""
        return create_supervisor_agent(
            self.model_name,
            self.profile_agent,
            self.calculator_agent,
            self.planner_agent,
            self.community_agent
        )
    
    @property
    def llm_agent(self) -> LlmAgent:
        """Get the underlying LLM agent."""
        return self.agent


# ============================================================================
# AGENT FACTORY
# ============================================================================
def create_supervisor_agent(
    model_name: str = "gemini-2.5-flash-lite",
    profile_agent: LlmAgent = None,
    calculator_agent: LlmAgent = None,
    planner_agent: LlmAgent = None,
    community_agent: LlmAgent = None
) -> LlmAgent:
    """
    Create the Supervisor Agent that orchestrates all sub-agents.
    
    Args:
        model_name: Gemini model to use
        profile_agent: Pre-created profile agent (or creates new)
        calculator_agent: Pre-created calculator agent (or creates new)
        planner_agent: Pre-created planner agent (or creates new)
        community_agent: Pre-created community agent (or creates new)
    
    Returns:
        Configured supervisor LlmAgent
    """
    # Create sub-agents if not provided
    if profile_agent is None:
        profile_agent = create_profile_agent(model_name)
    if calculator_agent is None:
        calculator_agent = create_calculator_agent(model_name)
    if planner_agent is None:
        planner_agent = create_planner_agent(model_name)
    if community_agent is None:
        community_agent = create_community_agent(model_name)
    
    instruction = """You are ClimateGuard 🌍 - Your Personal Carbon Footprint Coach!

Welcome! I'm here to help you understand and reduce your environmental impact through personalized coaching and community support.

## YOUR CAPABILITIES

I coordinate a team of specialized agents to help you:

1. **Profile Agent** 📋 - Sets up your lifestyle profile
2. **Calculator Agent** 🧮 - Computes your carbon footprint
3. **Planner Agent** 📅 - Creates weekly reduction plans
4. **Community Agent** 🤝 - Connects you with others

## ROUTING LOGIC

Based on what the user asks, delegate to the appropriate agent:

### Profile Agent (profile_agent)
- "I'm new here" / "Get started" / "Set up my profile"
- Questions about updating preferences
- Changing location, diet, or transport info

### Calculator Agent (calculator_agent)
- "What's my carbon footprint?"
- "Calculate emissions for X"
- "How much CO2 does Y produce?"
- Specific activity calculations

### Planner Agent (planner_agent)
- "Create a plan for me"
- "What can I do to reduce my footprint?"
- "Help me lower my emissions"
- Weekly/daily action planning

### Community Agent (community_agent)
- "Find groups near me"
- "Join a challenge"
- "Connect with others"
- "Share my story"

## WORKFLOW FOR NEW USERS

1. Check status with get_user_status
2. If no profile → delegate to profile_agent
3. If profile exists but no history → suggest calculator_agent
4. If both exist → offer planner_agent or community_agent

## COMMUNICATION STYLE

- Be warm, encouraging, and never preachy
- Celebrate every win, no matter how small
- Make sustainability feel achievable
- Use emojis sparingly but effectively 🌱
- Focus on positive impact, not guilt

## EXAMPLE INTERACTIONS

**New User:**
User: "Hi, I want to reduce my carbon footprint"
You: [Check status] → No profile
You: "Welcome to ClimateGuard! 🌱 I'm excited to help you on your sustainability journey! Let's start by learning a bit about your lifestyle so I can give you personalized tips."
[Delegate to profile_agent]

**Returning User:**
User: "What's my footprint this week?"
You: [Check status] → Has profile
[Delegate to calculator_agent for footprint calculation]

**Action Request:**
User: "Give me something I can do today"
You: [Delegate to planner_agent for quick action]

## IMPORTANT RULES

1. ALWAYS check user_status first to understand context
2. Delegate to specialists - don't try to do their job
3. Summarize key learnings at end of important sessions
4. Be conversational, not robotic
5. If user seems overwhelmed, simplify and focus on ONE action

## SESSION MANAGEMENT

- Use summarize_session at the end of meaningful conversations
- Reference past interactions when relevant
- Build on previous progress

Let's make sustainability achievable, one step at a time! 🌍
"""
    
    return LlmAgent(
        name="climateguard_supervisor",
        model=Gemini(model=model_name, retry_options=RETRY_CONFIG),
        description="ClimateGuard: Personal Carbon Footprint Coach - coordinates profile, calculator, planner, and community agents",
        instruction=instruction,
        tools=[
            get_user_status,
            summarize_session,
            AgentTool(agent=profile_agent),
            AgentTool(agent=calculator_agent),
            AgentTool(agent=planner_agent),
            AgentTool(agent=community_agent),
        ],
    )


# ============================================================================
# APP FACTORY
# ============================================================================
def create_climateguard_app(
    model_name: str = "gemini-2.5-flash-lite",
    use_compaction: bool = True,
    use_database: bool = False,
    db_url: str = "sqlite:///climateguard.db"
) -> tuple:
    """
    Create the complete ClimateGuard application with all services.
    
    Args:
        model_name: Gemini model to use
        use_compaction: Enable context compaction
        use_database: Use database for persistent sessions
        db_url: Database URL if using database
    
    Returns:
        Tuple of (App, Runner, SessionService)
    """
    # Create supervisor with all sub-agents
    supervisor = SupervisorAgent(model_name)
    
    # Configure compaction
    compaction_config = None
    if use_compaction:
        compaction_config = EventsCompactionConfig(
            compaction_interval=5,  # Compact every 5 invocations
            overlap_size=2,  # Keep 2 turns of context
        )
    
    # Create the app
    app = App(
        name="climateguard",
        root_agent=supervisor.llm_agent,
        events_compaction_config=compaction_config,
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
    
    # Create session service
    if use_database:
        session_service = DatabaseSessionService(db_url=db_url)
    else:
        session_service = InMemorySessionService()
    
    # Create runner
    runner = Runner(
        app=app,
        session_service=session_service,
        memory_service=get_memory_service(),
    )
    
    return app, runner, session_service


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================
async def run_climateguard(
    query: str,
    user_id: str = "default_user",
    session_id: str = None,
    runner: Runner = None,
    session_service = None
):
    """
    Run a query through ClimateGuard.
    
    Args:
        query: User's query
        user_id: User identifier
        session_id: Session ID (creates new if None)
        runner: Pre-existing runner (creates new if None)
        session_service: Pre-existing session service
    
    Returns:
        Response from the agent
    """
    # Create runner if not provided
    if runner is None:
        _, runner, session_service = create_climateguard_app()
    
    # Create or get session
    if session_id is None:
        session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    try:
        await session_service.create_session(
            app_name="climateguard",
            user_id=user_id,
            session_id=session_id
        )
    except:
        pass  # Session might already exist
    
    # Run query
    query_content = types.Content(
        role="user",
        parts=[types.Part(text=query)]
    )
    
    final_response = None
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=query_content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    final_response = part.text
    
    return final_response


# ============================================================================
# TESTING
# ============================================================================
if __name__ == "__main__":
    print("Supervisor Agent module loaded successfully!")
    
    # Test supervisor tools
    print("\nTesting get_user_status...")
    result = get_user_status("supervisor_test_user")
    print(f"Status: {result}")
    
    print("\nTesting summarize_session...")
    result = summarize_session("supervisor_test_user", "User discussed diet changes and committed to Meatless Mondays")
    print(f"Summary saved: {result.get('status')}")
    
    print("\nCreating ClimateGuard App...")
    app, runner, session_service = create_climateguard_app()
    print(f"App name: {app.name}")
    print(f"Root agent: {app.root_agent.name}")
    
    print("\n✅ Supervisor Agent setup complete!")
