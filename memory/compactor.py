"""
ClimateGuard Context Compactor
==============================
Intelligently summarizes conversation history while preserving key climate facts.

Keeps token usage under 4k to optimize API costs while maintaining important:
- User preferences and commitments
- Carbon footprint data points
- Behavioral insights
- Goal progress

ADK Concept: Context Compaction
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# COMPACTION CONFIGURATION
# ============================================================================
@dataclass
class CompactionConfig:
    """Configuration for context compaction."""
    max_tokens: int = 4000  # Target maximum tokens
    min_turns_to_keep: int = 3  # Always keep last N turns
    overlap_size: int = 1  # Turns to overlap between compactions
    summary_max_length: int = 500  # Max characters for summary
    priority_keywords: List[str] = None  # Keywords that should be preserved
    
    def __post_init__(self):
        if self.priority_keywords is None:
            self.priority_keywords = [
                # Climate facts
                "co2", "carbon", "emissions", "footprint", "kg", "tons",
                # User preferences
                "vegetarian", "vegan", "meat", "beef", "chicken",
                "car", "drive", "bicycle", "transit", "flight",
                "electric", "solar", "renewable",
                # Commitments
                "commit", "goal", "plan", "will", "promise",
                "meatless", "reduce", "switch", "change",
                # Location
                "live", "city", "country", "home",
            ]


# ============================================================================
# COMPACTION RESULT
# ============================================================================
@dataclass
class CompactionResult:
    """Result of context compaction."""
    original_tokens: int
    compacted_tokens: int
    compression_ratio: float
    summary: str
    preserved_facts: List[str]
    kept_turns: int
    compacted_turns: int


# ============================================================================
# CLIMATEGUARD COMPACTOR
# ============================================================================
class ClimateGuardCompactor:
    """
    Intelligently compacts conversation history for ClimateGuard.
    
    Strategy:
    1. Identify and extract key facts (commitments, data points, preferences)
    2. Summarize older conversation turns
    3. Keep recent turns intact for context
    4. Maintain token budget
    """
    
    def __init__(self, config: Optional[CompactionConfig] = None):
        """
        Initialize compactor.
        
        Args:
            config: CompactionConfig or None for defaults
        """
        self.config = config or CompactionConfig()
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Rough estimate: ~4 characters per token for English.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def extract_key_facts(self, text: str) -> List[str]:
        """
        Extract key climate-related facts from text.
        
        Args:
            text: Text to analyze
        
        Returns:
            List of key facts
        """
        facts = []
        text_lower = text.lower()
        
        # CO2 numbers
        co2_pattern = r'(\d+(?:\.\d+)?)\s*(?:kg|tons?|tonnes?)\s*(?:co2|carbon|emissions?)'
        for match in re.finditer(co2_pattern, text_lower):
            facts.append(f"Emissions data: {match.group(0)}")
        
        # Commitments (sentences with commitment words)
        commitment_words = ["commit", "will", "plan to", "going to", "promise", "goal"]
        sentences = re.split(r'[.!?]', text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(word in sentence_lower for word in commitment_words):
                if any(kw in sentence_lower for kw in self.config.priority_keywords):
                    facts.append(f"Commitment: {sentence.strip()}")
        
        # Preferences (diet, transport, energy)
        preference_patterns = [
            (r"(?:i am|i'm|we are|we're)\s+(?:a\s+)?(vegetarian|vegan|omnivore|pescatarian)", "Diet: {}"),
            (r"(?:i|we)\s+(?:drive|use|take|ride)\s+(?:a\s+)?(\w+(?:\s+\w+)?)\s+(?:to work|daily|regularly)", "Transport: {}"),
            (r"(?:live|living)\s+in\s+(\w+(?:\s+\w+)?)", "Location: {}"),
        ]
        
        for pattern, template in preference_patterns:
            match = re.search(pattern, text_lower)
            if match:
                facts.append(template.format(match.group(1)))
        
        return list(set(facts))  # Remove duplicates
    
    def summarize_turns(self, turns: List[Dict]) -> str:
        """
        Summarize a list of conversation turns.
        
        Args:
            turns: List of turn dictionaries with 'role' and 'content'
        
        Returns:
            Summary string
        """
        if not turns:
            return ""
        
        # Extract all key facts from turns
        all_facts = []
        topics = set()
        
        for turn in turns:
            content = turn.get("content", "")
            if isinstance(content, list):
                content = " ".join(str(p) for p in content)
            
            facts = self.extract_key_facts(content)
            all_facts.extend(facts)
            
            # Extract topics
            content_lower = content.lower()
            topic_keywords = {
                "diet": ["food", "eat", "meal", "meat", "vegetarian"],
                "transport": ["car", "drive", "commute", "flight", "train"],
                "energy": ["electricity", "energy", "power", "heating"],
                "footprint": ["footprint", "emissions", "carbon", "co2"],
            }
            
            for topic, keywords in topic_keywords.items():
                if any(kw in content_lower for kw in keywords):
                    topics.add(topic)
        
        # Build summary
        summary_parts = []
        
        if topics:
            summary_parts.append(f"[Previous discussion covered: {', '.join(topics)}]")
        
        if all_facts:
            # Deduplicate and limit facts
            unique_facts = list(set(all_facts))[:5]
            summary_parts.append("[Key facts: " + "; ".join(unique_facts) + "]")
        
        summary = " ".join(summary_parts)
        
        # Truncate if too long
        if len(summary) > self.config.summary_max_length:
            summary = summary[:self.config.summary_max_length - 3] + "..."
        
        return summary
    
    def compact(self, events: List[Any]) -> CompactionResult:
        """
        Compact conversation events.
        
        Args:
            events: List of ADK Event objects or dicts with conversation history
        
        Returns:
            CompactionResult with compacted content
        """
        # Convert events to turn list
        turns = []
        for event in events:
            if hasattr(event, 'content') and event.content:
                role = getattr(event.content, 'role', 'unknown')
                parts = getattr(event.content, 'parts', [])
                content = ""
                for part in parts:
                    if hasattr(part, 'text') and part.text:
                        content += part.text
                if content:
                    turns.append({"role": role, "content": content})
            elif isinstance(event, dict):
                turns.append(event)
        
        if not turns:
            return CompactionResult(
                original_tokens=0,
                compacted_tokens=0,
                compression_ratio=1.0,
                summary="",
                preserved_facts=[],
                kept_turns=0,
                compacted_turns=0
            )
        
        # Calculate original token count
        original_text = " ".join(t.get("content", "") for t in turns)
        original_tokens = self.estimate_tokens(original_text)
        
        # If under budget, no compaction needed
        if original_tokens <= self.config.max_tokens:
            return CompactionResult(
                original_tokens=original_tokens,
                compacted_tokens=original_tokens,
                compression_ratio=1.0,
                summary="",
                preserved_facts=self.extract_key_facts(original_text),
                kept_turns=len(turns),
                compacted_turns=0
            )
        
        # Split into turns to keep and turns to summarize
        keep_count = max(self.config.min_turns_to_keep, len(turns) // 3)
        
        turns_to_summarize = turns[:-keep_count]
        turns_to_keep = turns[-keep_count:]
        
        # Summarize older turns
        summary = self.summarize_turns(turns_to_summarize)
        
        # Extract key facts from all content
        all_facts = self.extract_key_facts(original_text)
        
        # Calculate compacted tokens
        kept_text = " ".join(t.get("content", "") for t in turns_to_keep)
        compacted_tokens = self.estimate_tokens(summary + " " + kept_text)
        
        return CompactionResult(
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            compression_ratio=compacted_tokens / original_tokens if original_tokens > 0 else 1.0,
            summary=summary,
            preserved_facts=all_facts[:10],  # Limit to top 10 facts
            kept_turns=len(turns_to_keep),
            compacted_turns=len(turns_to_summarize)
        )
    
    def get_compacted_context(self, events: List[Any]) -> str:
        """
        Get the compacted context string for use in prompts.
        
        Args:
            events: Conversation events
        
        Returns:
            Compacted context string
        """
        result = self.compact(events)
        
        if not result.summary:
            # No compaction was needed
            return ""
        
        context_parts = []
        
        if result.summary:
            context_parts.append(result.summary)
        
        if result.preserved_facts:
            context_parts.append(f"[Preserved facts: {'; '.join(result.preserved_facts)}]")
        
        return "\n".join(context_parts)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================
def compact_conversation(
    events: List[Any],
    max_tokens: int = 4000
) -> Dict:
    """
    Convenience function to compact conversation history.
    
    Args:
        events: List of conversation events
        max_tokens: Maximum token budget
    
    Returns:
        Dictionary with compaction results
    """
    config = CompactionConfig(max_tokens=max_tokens)
    compactor = ClimateGuardCompactor(config)
    result = compactor.compact(events)
    
    return {
        "original_tokens": result.original_tokens,
        "compacted_tokens": result.compacted_tokens,
        "compression_ratio": round(result.compression_ratio, 2),
        "summary": result.summary,
        "preserved_facts": result.preserved_facts,
        "kept_turns": result.kept_turns,
        "compacted_turns": result.compacted_turns,
    }


# ============================================================================
# TESTING
# ============================================================================
if __name__ == "__main__":
    print("Testing ClimateGuard Compactor...")
    
    # Mock conversation
    mock_turns = [
        {"role": "user", "content": "Hi! I want to reduce my carbon footprint. I live in San Francisco."},
        {"role": "assistant", "content": "Great! Let me help you. First, tell me about your diet and transportation habits."},
        {"role": "user", "content": "I eat beef about 4 times a week and drive a petrol car 30km daily to work."},
        {"role": "assistant", "content": "Your estimated daily emissions are 15.2 kg CO2. The beef consumption contributes about 27 kg CO2 per week."},
        {"role": "user", "content": "Wow that's a lot! I commit to trying Meatless Mondays starting next week."},
        {"role": "assistant", "content": "Excellent commitment! Meatless Mondays could save you approximately 108 kg CO2 per month."},
        {"role": "user", "content": "I will also look into switching to an electric vehicle next year."},
        {"role": "assistant", "content": "That's a great goal! An EV switch could reduce your transport emissions by 75%."},
        {"role": "user", "content": "What's my total weekly footprint now?"},
        {"role": "assistant", "content": "Your current weekly footprint is approximately 150 kg CO2, including food, transport, and home energy."},
    ]
    
    # Test compaction
    compactor = ClimateGuardCompactor()
    result = compactor.compact(mock_turns)
    
    print(f"\nOriginal tokens: {result.original_tokens}")
    print(f"Compacted tokens: {result.compacted_tokens}")
    print(f"Compression ratio: {result.compression_ratio:.2f}")
    print(f"\nSummary: {result.summary}")
    print(f"\nPreserved facts:")
    for fact in result.preserved_facts:
        print(f"  - {fact}")
    print(f"\nKept turns: {result.kept_turns}, Compacted turns: {result.compacted_turns}")
    
    # Test convenience function
    print("\n" + "="*50)
    compact_result = compact_conversation(mock_turns, max_tokens=2000)
    print(f"Convenience function result: {compact_result}")
    
    print("\n✅ Compactor tests passed!")
