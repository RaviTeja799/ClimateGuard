#!/usr/bin/env python
"""
ClimateGuard - Personal Carbon Footprint Coach
===============================================
Main entry point for the ClimateGuard multi-agent system.

Google AI Agents Intensive Capstone Project
Track: Agents for Good - Sustainability

Usage:
    python main.py                    # Interactive CLI mode
    python main.py --demo             # Run demo queries
    python main.py --web              # Start web server (A2A)
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Verify API key
if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your_gemini_api_key_here":
    print("⚠️  Warning: GOOGLE_API_KEY not set or is placeholder")
    print("   Get your free API key from: https://aistudio.google.com/app/apikey")
    print("   Then add it to your .env file")
    print()

# Import ClimateGuard components
from agents.supervisor import create_climateguard_app, run_climateguard
from plugins.impact_tracker import get_impact_tracker


# ============================================================================
# CLI INTERFACE
# ============================================================================
class ClimateGuardCLI:
    """Interactive CLI for ClimateGuard."""
    
    def __init__(self, user_id: str = None):
        """
        Initialize CLI.
        
        Args:
            user_id: User identifier (generates random if None)
        """
        import uuid
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        self.session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # Create app and services
        print("🌱 Initializing ClimateGuard...")
        self.app, self.runner, self.session_service = create_climateguard_app()
        self.tracker = get_impact_tracker()
        
        print(f"✅ Ready! User ID: {self.user_id}")
        print()
    
    async def chat(self, query: str) -> str:
        """
        Send a chat message.
        
        Args:
            query: User's message
        
        Returns:
            Agent's response
        """
        from google.genai import types
        
        # Track query
        start_time = datetime.now()
        
        # Ensure session exists
        try:
            await self.session_service.create_session(
                app_name="climateguard",
                user_id=self.user_id,
                session_id=self.session_id
            )
        except:
            pass  # Session exists
        
        # Run query
        query_content = types.Content(
            role="user",
            parts=[types.Part(text=query)]
        )
        
        response_text = None
        async for event in self.runner.run_async(
            user_id=self.user_id,
            session_id=self.session_id,
            new_message=query_content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text = part.text
        
        # Track response
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        self.tracker.on_query(self.session_id, query, duration_ms)
        
        return response_text or "I'm sorry, I couldn't process that request."
    
    async def run_interactive(self):
        """Run interactive chat loop."""
        print("="*60)
        print("🌍 ClimateGuard - Your Personal Carbon Footprint Coach")
        print("="*60)
        print()
        print("I'm here to help you understand and reduce your carbon footprint!")
        print("Type 'help' for commands, 'quit' to exit")
        print()
        
        # Track session start
        self.tracker.on_session_start(self.user_id, self.session_id)
        
        while True:
            try:
                user_input = input("You > ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n🌱 Thank you for using ClimateGuard!")
                    print("   Every action counts. Keep making sustainable choices!")
                    break
                
                if user_input.lower() == 'help':
                    self._print_help()
                    continue
                
                if user_input.lower() == 'status':
                    self._print_status()
                    continue
                
                if user_input.lower() == 'impact':
                    self._print_impact()
                    continue
                
                # Send to agent
                print()
                response = await self.chat(user_input)
                print(f"ClimateGuard > {response}")
                print()
                
            except KeyboardInterrupt:
                print("\n\n🌱 Goodbye! Keep being sustainable!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("   Try again or type 'help' for commands")
    
    def _print_help(self):
        """Print help message."""
        print("""
╔══════════════════════════════════════════════════════════╗
║                    ClimateGuard Help                     ║
╠══════════════════════════════════════════════════════════╣
║ COMMANDS                                                 ║
║   help    - Show this help message                       ║
║   status  - Show your current status                     ║
║   impact  - Show community impact metrics                ║
║   quit    - Exit ClimateGuard                            ║
║                                                          ║
║ THINGS TO TRY                                            ║
║   "I want to reduce my carbon footprint"                 ║
║   "What's my carbon footprint?"                          ║
║   "Create a weekly plan for me"                          ║
║   "Find sustainability groups near me"                   ║
║   "How much CO2 does a flight from NYC to LA produce?"   ║
║   "What can I do today to help the planet?"              ║
╚══════════════════════════════════════════════════════════╝
""")
    
    def _print_status(self):
        """Print user status."""
        from agents.supervisor import get_user_status
        status = get_user_status(self.user_id)
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                      Your Status                         ║
╠══════════════════════════════════════════════════════════╣
║  User ID: {self.user_id:<45} ║
║  Profile: {'✅ Complete' if status.get('has_profile') else '❌ Not set up':<45} ║
║  History: {str(status.get('footprint_records', 0)) + ' records':<45} ║
║  Next Step: {status.get('recommended_next_step', 'Start chatting!'):<43} ║
╚══════════════════════════════════════════════════════════╝
""")
    
    def _print_impact(self):
        """Print impact metrics."""
        summary = self.tracker.get_impact_summary()
        impact = summary.get('impact', {})
        engagement = summary.get('engagement', {})
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                   Community Impact                       ║
╠══════════════════════════════════════════════════════════╣
║  🌍 Total CO2 Saved: {impact.get('co2_saved_kg', 0):<10} kg                        ║
║  🌳 Equivalent Trees: {int(impact.get('equivalent_trees', 0)):<10}                          ║
║  👥 Total Users: {engagement.get('total_users', 0):<10}                              ║
║  ✅ Actions Completed: {engagement.get('actions_completed', 0):<10}                     ║
║  📅 Plans Created: {engagement.get('plans_created', 0):<10}                          ║
║  🎯 Challenges Joined: {engagement.get('challenges_joined', 0):<10}                     ║
╚══════════════════════════════════════════════════════════╝
""")


# ============================================================================
# DEMO MODE
# ============================================================================
async def run_demo():
    """Run a demonstration of ClimateGuard capabilities."""
    print("="*60)
    print("🎬 ClimateGuard Demo")
    print("="*60)
    print()
    
    cli = ClimateGuardCLI(user_id="demo_user")
    
    demo_queries = [
        "Hi! I want to reduce my carbon footprint. I live in San Francisco.",
        "I eat meat about 5 times a week and drive to work every day (about 20km round trip).",
        "What's my estimated carbon footprint?",
        "Give me 3 easy things I can do this week to reduce emissions.",
        "Are there any sustainability groups in San Francisco?",
    ]
    
    for query in demo_queries:
        print(f"You > {query}")
        response = await cli.chat(query)
        print(f"ClimateGuard > {response}")
        print()
        print("-"*60)
        print()
        await asyncio.sleep(1)  # Pause for readability
    
    print("🎬 Demo complete!")
    print()
    cli._print_impact()


# ============================================================================
# MAIN
# ============================================================================
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ClimateGuard - Personal Carbon Footprint Coach"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration queries"
    )
    parser.add_argument(
        "--user",
        type=str,
        default=None,
        help="User ID to use"
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start web server for A2A (not implemented yet)"
    )
    
    args = parser.parse_args()
    
    if args.web:
        print("Web server mode not yet implemented.")
        print("Use 'python main.py' for interactive mode.")
        return
    
    if args.demo:
        asyncio.run(run_demo())
    else:
        cli = ClimateGuardCLI(user_id=args.user)
        asyncio.run(cli.run_interactive())


if __name__ == "__main__":
    main()
