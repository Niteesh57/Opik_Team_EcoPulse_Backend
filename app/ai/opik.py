"""
Opik Framework Integration - Comprehensive AI Observability & Evaluation
=========================================================================
This module provides enterprise-grade LLM observability including:
- Full trace capture for all AI interactions
- User feedback scoring and analysis
- Cost tracking and token usage monitoring
- Custom evaluation metrics
- Experiment tracking for A/B testing
- Real-time performance monitoring
"""

import opik
from opik import Opik, track
from opik.integrations.langchain import OpikTracer
from opik import opik_context
from opik.evaluation import evaluate
from opik.evaluation.metrics import Hallucination, AnswerRelevance, ContextPrecision
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from functools import wraps

# =============================================================================
# OPIK CLIENT CONFIGURATION
# =============================================================================

# Initialize Opik client with project configuration
opik_client = Opik(
    project_name="EcoPulse-AI-Platform",
)

# Global tracer instance with project binding
opik_tracer = OpikTracer(
    project_name="EcoPulse-AI-Platform",
    tags=["production", "langgraph", "multi-agent"]
)


# =============================================================================
# CUSTOM EVALUATION METRICS
# =============================================================================

class SustainabilityRelevance:
    """Custom metric to evaluate if AI responses align with sustainability goals."""
    
    name = "sustainability_relevance"
    
    def score(self, output: str, context: Optional[str] = None) -> float:
        """Score how relevant the response is to sustainability topics."""
        sustainability_keywords = [
            "eco", "green", "sustainable", "recycle", "compost", "energy",
            "solar", "renewable", "carbon", "environment", "conservation",
            "reduce", "reuse", "organic", "biodegradable", "climate"
        ]
        output_lower = output.lower()
        matches = sum(1 for kw in sustainability_keywords if kw in output_lower)
        return min(1.0, matches / 5)  # Normalize to 0-1


class CommunityEngagement:
    """Custom metric to evaluate community engagement potential."""
    
    name = "community_engagement"
    
    def score(self, output: str, context: Optional[str] = None) -> float:
        """Score the community engagement potential of a response."""
        engagement_signals = [
            "join", "participate", "together", "community", "neighbor",
            "event", "group", "share", "help", "collaborate", "team"
        ]
        output_lower = output.lower()
        matches = sum(1 for signal in engagement_signals if signal in output_lower)
        return min(1.0, matches / 4)


class ResponseQuality:
    """Composite metric for overall response quality."""
    
    name = "response_quality"
    
    def score(
        self, 
        output: str, 
        expected: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, float]:
        """Calculate multiple quality dimensions."""
        # Length appropriateness (50-500 chars is ideal)
        length = len(output)
        length_score = 1.0 if 50 <= length <= 500 else max(0, 1 - abs(length - 275) / 500)
        
        # Actionability (contains action verbs)
        action_verbs = ["can", "should", "will", "try", "use", "visit", "contact", "check"]
        actionability = min(1.0, sum(1 for v in action_verbs if v in output.lower()) / 3)
        
        # Politeness
        polite_words = ["please", "thank", "happy", "glad", "welcome", "appreciate"]
        politeness = min(1.0, sum(1 for w in polite_words if w in output.lower()) / 2)
        
        return {
            "length_appropriateness": length_score,
            "actionability": actionability,
            "politeness": politeness,
            "overall": (length_score + actionability + politeness) / 3
        }


# =============================================================================
# TRACE DECORATORS WITH RICH METADATA
# =============================================================================

def track_agent_call(
    agent_name: str,
    agent_type: str = "conversational",
    capture_input: bool = True,
    capture_output: bool = True
):
    """
    Decorator for tracking agent calls with comprehensive metadata.
    
    Args:
        agent_name: Name of the agent (e.g., "Green Sentinel", "Event Manager")
        agent_type: Type of agent (conversational, task, workflow)
        capture_input: Whether to capture input in trace
        capture_output: Whether to capture output in trace
    """
    def decorator(func):
        @wraps(func)
        @track(name=f"Agent: {agent_name}")
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            # Update trace with agent metadata
            try:
                opik_context.update_current_trace(
                    metadata={
                        "agent_name": agent_name,
                        "agent_type": agent_type,
                        "timestamp": start_time.isoformat(),
                        "platform": "EcoPulse"
                    },
                    tags=[agent_name.lower().replace(" ", "-"), agent_type, "agent-call"]
                )
            except Exception:
                pass
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Calculate duration
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update with performance metrics
            try:
                opik_context.update_current_span(
                    metadata={
                        "duration_ms": duration_ms,
                        "success": True
                    }
                )
            except Exception:
                pass
            
            return result
        return wrapper
    return decorator


def track_tool_usage(tool_name: str, tool_category: str = "general"):
    """
    Decorator for tracking tool invocations with usage analytics.
    
    Args:
        tool_name: Name of the tool
        tool_category: Category (mcp, api, memory, social)
    """
    def decorator(func):
        @wraps(func)
        @track(name=f"Tool: {tool_name}")
        def wrapper(*args, **kwargs):
            try:
                opik_context.update_current_span(
                    metadata={
                        "tool_name": tool_name,
                        "tool_category": tool_category,
                        "invocation_time": datetime.now().isoformat()
                    },
                    tags=[f"tool-{tool_category}", tool_name.lower().replace(" ", "-")]
                )
            except Exception:
                pass
            
            result = func(*args, **kwargs)
            
            # Log tool output size
            try:
                output_size = len(str(result)) if result else 0
                opik_context.update_current_span(
                    metadata={"output_size_bytes": output_size}
                )
            except Exception:
                pass
            
            return result
        return wrapper
    return decorator


def track_llm_generation(
    model_name: str = "groq",
    generation_type: str = "completion"
):
    """
    Decorator for tracking LLM generation with token/cost estimation.
    
    Args:
        model_name: Name of the LLM model
        generation_type: Type of generation (completion, chat, embedding)
    """
    def decorator(func):
        @wraps(func)
        @track(name=f"LLM Generation: {generation_type}")
        def wrapper(*args, **kwargs):
            try:
                opik_context.update_current_span(
                    metadata={
                        "model": model_name,
                        "generation_type": generation_type,
                        "provider": "Groq"
                    },
                    tags=["llm-call", model_name, generation_type]
                )
            except Exception:
                pass
            
            result = func(*args, **kwargs)
            
            # Estimate token usage from result
            try:
                if hasattr(result, 'content'):
                    output_text = result.content
                    # Rough token estimation (1 token ≈ 4 chars)
                    estimated_tokens = len(output_text) // 4
                    # Cost estimation for Groq (approximate)
                    estimated_cost = estimated_tokens * 0.00001  # $0.01 per 1K tokens
                    
                    opik_context.update_current_span(
                        metadata={
                            "estimated_output_tokens": estimated_tokens,
                            "estimated_cost_usd": round(estimated_cost, 6)
                        }
                    )
            except Exception:
                pass
            
            return result
        return wrapper
    return decorator


# =============================================================================
# FEEDBACK COLLECTION & SCORING
# =============================================================================

class FeedbackCollector:
    """Centralized feedback collection and scoring for Opik."""
    
    def __init__(self):
        self.feedback_types = {
            "helpful": {"min": 0, "max": 1, "description": "Was the response helpful?"},
            "accurate": {"min": 0, "max": 1, "description": "Was the information accurate?"},
            "relevant": {"min": 0, "max": 1, "description": "Was the response relevant?"},
            "actionable": {"min": 0, "max": 1, "description": "Could you act on this advice?"},
            "sustainability": {"min": 0, "max": 1, "description": "Did it promote sustainability?"}
        }
    
    @track(name="Record User Feedback")
    def record_feedback(
        self,
        trace_id: Optional[str],
        thread_id: Optional[str],
        feedback_type: str,
        score: float,
        reason: Optional[str] = None,
        user_id: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record user feedback with full context.
        
        Args:
            trace_id: Opik trace ID
            thread_id: Conversation thread ID
            feedback_type: Type of feedback (helpful, accurate, etc.)
            score: Score value (0-1)
            reason: Optional reason for the score
            user_id: User providing feedback
            message_id: Message being rated
        """
        # Validate feedback type
        if feedback_type not in self.feedback_types:
            feedback_type = "helpful"
        
        # Clamp score to valid range
        config = self.feedback_types[feedback_type]
        score = max(config["min"], min(config["max"], score))
        
        feedback_data = {
            "feedback_type": feedback_type,
            "score": score,
            "reason": reason,
            "user_id": user_id,
            "message_id": message_id,
            "thread_id": thread_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update Opik trace with feedback
        try:
            opik_context.update_current_trace(
                feedback_scores=[{
                    "name": feedback_type,
                    "value": score,
                    "reason": reason or f"User feedback: {feedback_type}"
                }],
                metadata={
                    "feedback_recorded": True,
                    "feedback_data": feedback_data
                }
            )
        except Exception as e:
            print(f"Error recording feedback to Opik: {e}")
        
        return feedback_data
    
    @track(name="Record Multi-Dimensional Feedback")
    def record_comprehensive_feedback(
        self,
        thread_id: str,
        scores: Dict[str, float],
        overall_comment: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record multiple feedback dimensions at once.
        
        Args:
            thread_id: Conversation thread ID
            scores: Dictionary of feedback_type -> score
            overall_comment: Overall user comment
            user_id: User providing feedback
        """
        feedback_scores = []
        for feedback_type, score in scores.items():
            if feedback_type in self.feedback_types:
                config = self.feedback_types[feedback_type]
                clamped_score = max(config["min"], min(config["max"], score))
                feedback_scores.append({
                    "name": feedback_type,
                    "value": clamped_score,
                    "reason": f"Multi-dimensional feedback: {feedback_type}"
                })
        
        try:
            opik_context.update_current_trace(
                feedback_scores=feedback_scores,
                metadata={
                    "comprehensive_feedback": True,
                    "overall_comment": overall_comment,
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "feedback_count": len(feedback_scores)
                }
            )
        except Exception as e:
            print(f"Error recording comprehensive feedback: {e}")
        
        return {
            "thread_id": thread_id,
            "scores_recorded": len(feedback_scores),
            "overall_comment": overall_comment
        }


# Global feedback collector instance
feedback_collector = FeedbackCollector()


# =============================================================================
# EXPERIMENT TRACKING
# =============================================================================

class ExperimentTracker:
    """Track A/B experiments and prompt variations."""
    
    def __init__(self):
        self.active_experiments: Dict[str, Dict] = {}
    
    def start_experiment(
        self,
        experiment_name: str,
        variants: List[str],
        description: Optional[str] = None
    ) -> str:
        """Start a new experiment."""
        experiment_id = f"exp_{experiment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.active_experiments[experiment_id] = {
            "name": experiment_name,
            "variants": variants,
            "description": description,
            "started_at": datetime.now().isoformat(),
            "results": {v: {"count": 0, "total_score": 0} for v in variants}
        }
        
        return experiment_id
    
    @track(name="Record Experiment Result")
    def record_result(
        self,
        experiment_id: str,
        variant: str,
        score: float,
        metadata: Optional[Dict] = None
    ):
        """Record a result for an experiment variant."""
        if experiment_id in self.active_experiments:
            exp = self.active_experiments[experiment_id]
            if variant in exp["results"]:
                exp["results"][variant]["count"] += 1
                exp["results"][variant]["total_score"] += score
        
        try:
            opik_context.update_current_trace(
                metadata={
                    "experiment_id": experiment_id,
                    "variant": variant,
                    "score": score,
                    **(metadata or {})
                },
                tags=["experiment", experiment_id, f"variant-{variant}"]
            )
        except Exception:
            pass
    
    def get_experiment_stats(self, experiment_id: str) -> Optional[Dict]:
        """Get statistics for an experiment."""
        if experiment_id not in self.active_experiments:
            return None
        
        exp = self.active_experiments[experiment_id]
        stats = {"name": exp["name"], "variants": {}}
        
        for variant, data in exp["results"].items():
            count = data["count"]
            avg_score = data["total_score"] / count if count > 0 else 0
            stats["variants"][variant] = {
                "count": count,
                "average_score": round(avg_score, 3)
            }
        
        return stats


# Global experiment tracker
experiment_tracker = ExperimentTracker()


# =============================================================================
# CONVERSATION ANALYTICS
# =============================================================================

class ConversationAnalytics:
    """Track and analyze conversation patterns."""
    
    @staticmethod
    @track(name="Analyze Conversation")
    def analyze_conversation(
        thread_id: str,
        messages: List[Dict],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a conversation for insights.
        
        Returns metrics like:
        - Turn count
        - Average message length
        - Tool usage patterns
        - Sentiment indicators
        """
        analysis = {
            "thread_id": thread_id,
            "total_turns": len(messages),
            "user_messages": 0,
            "ai_messages": 0,
            "avg_user_message_length": 0,
            "avg_ai_message_length": 0,
            "tools_used": [],
            "topics_detected": []
        }
        
        user_lengths = []
        ai_lengths = []
        
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            if role == "user":
                analysis["user_messages"] += 1
                user_lengths.append(len(content))
            elif role == "assistant":
                analysis["ai_messages"] += 1
                ai_lengths.append(len(content))
            
            # Detect tool calls
            if "tool_calls" in msg:
                for tc in msg["tool_calls"]:
                    if tc.get("name") not in analysis["tools_used"]:
                        analysis["tools_used"].append(tc.get("name"))
        
        if user_lengths:
            analysis["avg_user_message_length"] = sum(user_lengths) // len(user_lengths)
        if ai_lengths:
            analysis["avg_ai_message_length"] = sum(ai_lengths) // len(ai_lengths)
        
        # Update Opik with analytics
        try:
            opik_context.update_current_trace(
                metadata={
                    "conversation_analytics": analysis,
                    "analyzed_at": datetime.now().isoformat()
                }
            )
        except Exception:
            pass
        
        return analysis
    
    @staticmethod
    @track(name="Track User Journey")
    def track_user_journey(
        user_id: str,
        action: str,
        context: Optional[Dict] = None
    ):
        """Track a user action in their journey."""
        journey_event = {
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        
        try:
            opik_context.update_current_span(
                metadata={"user_journey_event": journey_event},
                tags=["user-journey", action]
            )
        except Exception:
            pass
        
        return journey_event


# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

class PerformanceMonitor:
    """Monitor and track AI system performance."""
    
    @staticmethod
    @track(name="Monitor Latency")
    def record_latency(
        operation: str,
        latency_ms: float,
        success: bool = True,
        metadata: Optional[Dict] = None
    ):
        """Record latency for an operation."""
        try:
            opik_context.update_current_span(
                metadata={
                    "operation": operation,
                    "latency_ms": latency_ms,
                    "success": success,
                    "performance_category": "fast" if latency_ms < 500 else "slow",
                    **(metadata or {})
                },
                tags=["performance", operation, "fast" if latency_ms < 500 else "slow"]
            )
        except Exception:
            pass
    
    @staticmethod
    @track(name="Monitor Token Usage")
    def record_token_usage(
        input_tokens: int,
        output_tokens: int,
        model: str,
        cost_per_1k_input: float = 0.01,
        cost_per_1k_output: float = 0.03
    ) -> Dict[str, Any]:
        """Record token usage and estimated cost."""
        total_tokens = input_tokens + output_tokens
        estimated_cost = (
            (input_tokens / 1000) * cost_per_1k_input +
            (output_tokens / 1000) * cost_per_1k_output
        )
        
        usage_data = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "model": model,
            "estimated_cost_usd": round(estimated_cost, 6)
        }
        
        try:
            opik_context.update_current_trace(
                metadata={
                    "token_usage": usage_data,
                    "cost_tracking": True
                }
            )
        except Exception:
            pass
        
        return usage_data


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_trace_url(trace_id: str) -> str:
    """Generate a URL to view a trace in Opik dashboard."""
    return f"https://app.comet.com/opik/traces/{trace_id}"


def create_span_context(
    name: str,
    span_type: str = "general",
    metadata: Optional[Dict] = None
):
    """Create a context manager for manual span creation."""
    return opik_context.span(
        name=name,
        metadata={
            "span_type": span_type,
            "created_at": datetime.now().isoformat(),
            **(metadata or {})
        }
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Core
    "opik_client",
    "opik_tracer",
    "opik_context",
    
    # Metrics
    "SustainabilityRelevance",
    "CommunityEngagement", 
    "ResponseQuality",
    
    # Decorators
    "track_agent_call",
    "track_tool_usage",
    "track_llm_generation",
    
    # Collectors
    "feedback_collector",
    "FeedbackCollector",
    
    # Experiment
    "experiment_tracker",
    "ExperimentTracker",
    
    # Analytics
    "ConversationAnalytics",
    "PerformanceMonitor",
    
    # Utilities
    "get_trace_url",
    "create_span_context",
]
