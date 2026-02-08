"""
AI Analytics & Observability Endpoints
=======================================
Powered by Opik Framework - Comprehensive LLM monitoring, evaluation, and feedback tracking.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User as UserModel
from app.ai.opik import (
    opik_client,
    feedback_collector,
    experiment_tracker,
    ConversationAnalytics,
    PerformanceMonitor,
    SustainabilityRelevance,
    CommunityEngagement,
    ResponseQuality,
    get_trace_url,
)

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class FeedbackSubmission(BaseModel):
    """User feedback submission model."""
    thread_id: str = Field(..., description="Conversation thread ID")
    message_id: Optional[int] = Field(None, description="Specific message ID")
    feedback_type: str = Field("helpful", description="Type: helpful, accurate, relevant, actionable, sustainability")
    score: float = Field(..., ge=0, le=1, description="Score between 0 and 1")
    reason: Optional[str] = Field(None, description="Optional reason for the score")


class MultiFeedbackSubmission(BaseModel):
    """Multi-dimensional feedback submission."""
    thread_id: str
    scores: Dict[str, float] = Field(..., description="Dict of feedback_type -> score")
    overall_comment: Optional[str] = None


class ExperimentCreate(BaseModel):
    """Create a new A/B experiment."""
    experiment_name: str
    variants: List[str]
    description: Optional[str] = None


class ExperimentResult(BaseModel):
    """Record an experiment result."""
    experiment_id: str
    variant: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class EvaluationRequest(BaseModel):
    """Request to evaluate a response."""
    response_text: str
    context: Optional[str] = None


class ConversationAnalysisRequest(BaseModel):
    """Request to analyze a conversation."""
    thread_id: str
    messages: List[Dict[str, Any]]


class AnalyticsSummary(BaseModel):
    """Analytics summary response."""
    total_conversations: int
    avg_satisfaction_score: float
    sustainability_score: float
    engagement_score: float
    top_feedback_categories: Dict[str, int]
    active_experiments: List[Dict]


# =============================================================================
# FEEDBACK ENDPOINTS
# =============================================================================

@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackSubmission,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Submit user feedback for a conversation or message.
    
    This feedback is tracked in Opik for:
    - Response quality improvement
    - Model fine-tuning signals
    - User satisfaction metrics
    """
    result = feedback_collector.record_feedback(
        trace_id=None,
        thread_id=payload.thread_id,
        feedback_type=payload.feedback_type,
        score=payload.score,
        reason=payload.reason,
        user_id=str(current_user.id),
        message_id=str(payload.message_id) if payload.message_id else None
    )
    
    return {
        "status": "success",
        "feedback_recorded": result,
        "trace_url": get_trace_url(payload.thread_id)
    }


@router.post("/feedback/comprehensive", status_code=status.HTTP_201_CREATED)
async def submit_comprehensive_feedback(
    payload: MultiFeedbackSubmission,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Submit multi-dimensional feedback for detailed analysis.
    
    Score categories:
    - helpful: Was the response helpful?
    - accurate: Was the information accurate?
    - relevant: Was the response relevant to the query?
    - actionable: Could the user act on the advice?
    - sustainability: Did it promote sustainability?
    """
    result = feedback_collector.record_comprehensive_feedback(
        thread_id=payload.thread_id,
        scores=payload.scores,
        overall_comment=payload.overall_comment,
        user_id=str(current_user.id)
    )
    
    return {
        "status": "success",
        "scores_recorded": result["scores_recorded"],
        "thread_id": payload.thread_id,
        "trace_url": get_trace_url(payload.thread_id)
    }


# =============================================================================
# EVALUATION ENDPOINTS
# =============================================================================

@router.post("/evaluate")
async def evaluate_response(
    payload: EvaluationRequest,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Evaluate an AI response using custom metrics.
    
    Returns scores for:
    - Sustainability relevance
    - Community engagement potential
    - Overall response quality
    """
    sustainability_metric = SustainabilityRelevance()
    engagement_metric = CommunityEngagement()
    quality_metric = ResponseQuality()
    
    sustainability_score = sustainability_metric.score(payload.response_text, payload.context)
    engagement_score = engagement_metric.score(payload.response_text, payload.context)
    quality_scores = quality_metric.score(payload.response_text, context=payload.context)
    
    # Track this evaluation in Opik
    PerformanceMonitor.record_latency(
        operation="manual_evaluation",
        latency_ms=0,
        success=True,
        metadata={
            "evaluator_id": str(current_user.id),
            "response_length": len(payload.response_text)
        }
    )
    
    return {
        "evaluation": {
            "sustainability_relevance": round(sustainability_score, 3),
            "community_engagement": round(engagement_score, 3),
            "quality": {
                "length_appropriateness": round(quality_scores["length_appropriateness"], 3),
                "actionability": round(quality_scores["actionability"], 3),
                "politeness": round(quality_scores["politeness"], 3),
                "overall": round(quality_scores["overall"], 3)
            }
        },
        "recommendations": _generate_recommendations(
            sustainability_score, 
            engagement_score, 
            quality_scores
        )
    }


def _generate_recommendations(
    sustainability: float, 
    engagement: float, 
    quality: Dict[str, float]
) -> List[str]:
    """Generate improvement recommendations based on scores."""
    recommendations = []
    
    if sustainability < 0.5:
        recommendations.append("Consider adding more sustainability-focused content (eco tips, green practices)")
    
    if engagement < 0.5:
        recommendations.append("Increase community engagement by mentioning events, groups, or collaboration opportunities")
    
    if quality["actionability"] < 0.5:
        recommendations.append("Make responses more actionable with specific steps or suggestions")
    
    if quality["politeness"] < 0.5:
        recommendations.append("Add more welcoming language (please, thank you, happy to help)")
    
    if quality["length_appropriateness"] < 0.5:
        recommendations.append("Adjust response length - aim for 50-500 characters for optimal engagement")
    
    if not recommendations:
        recommendations.append("Response looks great! All metrics are above threshold.")
    
    return recommendations


# =============================================================================
# EXPERIMENT ENDPOINTS
# =============================================================================

@router.post("/experiments", status_code=status.HTTP_201_CREATED)
async def create_experiment(
    payload: ExperimentCreate,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Create a new A/B experiment for testing prompt variations.
    
    Use this to compare different:
    - System prompts
    - Response styles
    - Tool configurations
    """
    experiment_id = experiment_tracker.start_experiment(
        experiment_name=payload.experiment_name,
        variants=payload.variants,
        description=payload.description
    )
    
    return {
        "status": "created",
        "experiment_id": experiment_id,
        "variants": payload.variants,
        "message": f"Experiment '{payload.experiment_name}' started with {len(payload.variants)} variants"
    }


@router.post("/experiments/result")
async def record_experiment_result(
    payload: ExperimentResult,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Record a result for an experiment variant."""
    experiment_tracker.record_result(
        experiment_id=payload.experiment_id,
        variant=payload.variant,
        score=payload.score,
        metadata=payload.metadata
    )
    
    return {
        "status": "recorded",
        "experiment_id": payload.experiment_id,
        "variant": payload.variant,
        "score": payload.score
    }


@router.get("/experiments/{experiment_id}/stats")
async def get_experiment_stats(
    experiment_id: str,
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get statistics for an experiment."""
    stats = experiment_tracker.get_experiment_stats(experiment_id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found"
        )
    
    return stats


@router.get("/experiments")
async def list_experiments(
    current_user: UserModel = Depends(get_current_active_user),
):
    """List all active experiments."""
    experiments = []
    for exp_id, exp_data in experiment_tracker.active_experiments.items():
        experiments.append({
            "id": exp_id,
            "name": exp_data["name"],
            "variants": exp_data["variants"],
            "started_at": exp_data["started_at"],
            "total_results": sum(v["count"] for v in exp_data["results"].values())
        })
    
    return {"experiments": experiments}


# =============================================================================
# CONVERSATION ANALYTICS
# =============================================================================

@router.post("/conversations/analyze")
async def analyze_conversation(
    payload: ConversationAnalysisRequest,
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Analyze a conversation for insights.
    
    Returns:
    - Turn count and message distribution
    - Average message lengths
    - Tools used
    - Topics detected
    """
    analysis = ConversationAnalytics.analyze_conversation(
        thread_id=payload.thread_id,
        messages=payload.messages,
        user_id=str(current_user.id)
    )
    
    return {
        "thread_id": payload.thread_id,
        "analysis": analysis,
        "trace_url": get_trace_url(payload.thread_id)
    }


# =============================================================================
# DASHBOARD & SUMMARY
# =============================================================================

@router.get("/dashboard")
async def get_analytics_dashboard(
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Get comprehensive analytics dashboard.
    
    Provides overview of:
    - AI system performance
    - User satisfaction metrics
    - Active experiments
    - Feedback summary
    """
    # Get active experiments summary
    active_experiments = []
    for exp_id, exp_data in experiment_tracker.active_experiments.items():
        active_experiments.append({
            "id": exp_id,
            "name": exp_data["name"],
            "variants_count": len(exp_data["variants"]),
            "total_results": sum(v["count"] for v in exp_data["results"].values())
        })
    
    return {
        "platform": "EcoPulse AI Analytics",
        "powered_by": "Opik Framework",
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "feedback_types_available": list(feedback_collector.feedback_types.keys()),
            "active_experiments": len(active_experiments),
            "experiments_detail": active_experiments
        },
        "capabilities": {
            "tracing": "Full LLM call tracing with metadata",
            "evaluation": "Custom metrics for sustainability, engagement, quality",
            "feedback": "Multi-dimensional user feedback collection",
            "experiments": "A/B testing for prompt optimization",
            "analytics": "Conversation analysis and user journey tracking"
        },
        "opik_features_used": [
            "OpikTracer - LangChain/LangGraph integration",
            "track() decorator - Function-level tracing",
            "opik_context - Span and trace metadata",
            "Custom evaluation metrics",
            "Feedback scoring with reasons",
            "Experiment tracking",
            "Performance monitoring",
            "Cost estimation"
        ]
    }


@router.get("/health")
async def opik_health_check():
    """Check Opik integration health."""
    return {
        "status": "healthy",
        "opik_client": "connected",
        "project": opik_client.project_name,
        "features": {
            "tracing": True,
            "feedback": True,
            "experiments": True,
            "evaluation": True
        },
        "timestamp": datetime.now().isoformat()
    }
