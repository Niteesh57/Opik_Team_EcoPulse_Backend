# 🔬 Opik Framework Integration - AI Observability & Evaluation

## 🏆 Overview for Judges

EcoPulse leverages **Opik** - an enterprise-grade LLM observability framework - to provide comprehensive monitoring, evaluation, and improvement of our AI systems. This integration demonstrates best practices in AI/ML observability for production systems.

---

## 🎯 Key Opik Features Implemented

### 1. **Full Trace Capture** 📊
Every AI interaction is fully traced with rich metadata:

```python
@track_agent_call(agent_name="Green Sentinel", agent_type="conversational")
def call_model(state: AgentState):
    # Complete trace of LLM call with:
    # - Input/output capture
    # - Token usage estimation
    # - Latency measurement
    # - Cost calculation
    # - Thread correlation
```

### 2. **Custom Evaluation Metrics** 📈

We've built domain-specific metrics for our sustainability platform:

| Metric | Purpose | Score Range |
|--------|---------|-------------|
| `SustainabilityRelevance` | Measures eco-friendly content in responses | 0-1 |
| `CommunityEngagement` | Evaluates collaboration/social signals | 0-1 |
| `ResponseQuality` | Composite metric (length, actionability, politeness) | 0-1 |

```python
class SustainabilityRelevance:
    def score(self, output: str, context: Optional[str] = None) -> float:
        sustainability_keywords = ["eco", "green", "sustainable", "recycle"...]
        matches = sum(1 for kw in sustainability_keywords if kw in output.lower())
        return min(1.0, matches / 5)
```

### 3. **Multi-Dimensional Feedback Collection** 👍

Users can rate responses across multiple dimensions:

```python
feedback_collector.record_comprehensive_feedback(
    thread_id=thread_id,
    scores={
        "helpful": 0.9,
        "accurate": 0.8,
        "relevant": 0.85,
        "actionable": 0.7,
        "sustainability": 0.95
    },
    overall_comment="Great eco-tips!",
    user_id=str(user.id)
)
```

### 4. **A/B Experiment Tracking** 🧪

Test prompt variations and measure impact:

```python
# Create experiment
experiment_id = experiment_tracker.start_experiment(
    experiment_name="system_prompt_v2",
    variants=["concise", "detailed", "friendly"],
    description="Testing different response styles"
)

# Record results
experiment_tracker.record_result(
    experiment_id=experiment_id,
    variant="friendly",
    score=0.92,
    metadata={"user_satisfaction": "high"}
)
```

### 5. **LangGraph Integration** 🔗

Full tracing for multi-agent workflows:

```python
from opik.integrations.langchain import track_langgraph, OpikTracer

# Trace the entire graph including subgraphs
opik_tracer = OpikTracer(graph=agent.get_graph(xray=True))
agent = track_langgraph(agent, opik_tracer)
```

### 6. **Real-Time Performance Monitoring** ⚡

Track latency and cost across all operations:

```python
PerformanceMonitor.record_latency(
    operation="agent_call",
    latency_ms=245.3,
    success=True,
    metadata={
        "thread_id": thread_id,
        "model": "groq/openai-gpt-oss-20b"
    }
)

PerformanceMonitor.record_token_usage(
    input_tokens=150,
    output_tokens=320,
    model="groq",
    cost_per_1k_input=0.01,
    cost_per_1k_output=0.03
)
```

### 7. **User Journey Analytics** 🛤️

Track user behavior across conversations:

```python
ConversationAnalytics.track_user_journey(
    user_id=str(user.id),
    action="event_creation_completed",
    context={
        "thread_id": thread_id,
        "event_name": "Community Garden Day",
        "creation_latency_ms": 1250
    }
)
```

---

## 🌐 API Endpoints

### Analytics Dashboard
```
GET /api/v1/analytics/dashboard
```
Returns comprehensive AI system metrics:
- Active experiments
- Feedback types available
- Feature capabilities

### Submit Feedback
```
POST /api/v1/analytics/feedback
{
    "thread_id": "abc123",
    "feedback_type": "helpful",
    "score": 0.9,
    "reason": "Very informative response"
}
```

### Multi-Dimensional Feedback
```
POST /api/v1/analytics/feedback/comprehensive
{
    "thread_id": "abc123",
    "scores": {
        "helpful": 0.9,
        "accurate": 0.85,
        "sustainability": 0.95
    },
    "overall_comment": "Loved the eco tips!"
}
```

### Evaluate Response
```
POST /api/v1/analytics/evaluate
{
    "response_text": "Consider using a compost bin for food scraps..."
}

Response:
{
    "evaluation": {
        "sustainability_relevance": 0.8,
        "community_engagement": 0.6,
        "quality": {
            "length_appropriateness": 0.9,
            "actionability": 0.85,
            "politeness": 0.7,
            "overall": 0.82
        }
    },
    "recommendations": [...]
}
```

### Create Experiment
```
POST /api/v1/analytics/experiments
{
    "experiment_name": "response_style_test",
    "variants": ["formal", "casual", "emoji"],
    "description": "Testing different response tones"
}
```

---

## 📊 Trace Metadata Structure

Every trace includes:

```json
{
    "trace_id": "tr_abc123",
    "thread_id": "conv_xyz789",
    "agent_name": "Green Sentinel",
    "agent_type": "conversational",
    "timestamp": "2026-02-03T10:30:00Z",
    "model": "groq/openai-gpt-oss-20b",
    "evaluation_metrics": {
        "sustainability_relevance": 0.75,
        "community_engagement": 0.65,
        "response_quality": {
            "overall": 0.82
        },
        "latency_ms": 245
    },
    "feedback_scores": [
        {"name": "sustainability", "value": 0.75},
        {"name": "engagement", "value": 0.65},
        {"name": "quality", "value": 0.82}
    ],
    "token_usage": {
        "input_tokens": 150,
        "output_tokens": 320,
        "estimated_cost_usd": 0.000115
    }
}
```

---

## 🔧 Custom Decorators

### `@track_agent_call`
```python
@track_agent_call(agent_name="Green Sentinel", agent_type="conversational")
def call_model(state: AgentState):
    # Automatically captures:
    # - Agent metadata
    # - Duration
    # - Success/failure
```

### `@track_tool_usage`
```python
@track_tool_usage(tool_name="create_event", tool_category="api")
def create_event_via_llm(event_name: str, ...):
    # Tracks tool invocation and output
```

### `@track_llm_generation`
```python
@track_llm_generation(model_name="groq", generation_type="completion")
def generate_description():
    # Tracks token usage and cost
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Endpoint                            │
│  ┌────────────────────────────────────────────────────┐ │
│  │  @track_agent_call                                  │ │
│  │  - Captures input/output                            │ │
│  │  - Measures latency                                 │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph Agent                             │
│  ┌────────────────────────────────────────────────────┐ │
│  │  OpikTracer                                         │ │
│  │  - Graph structure capture                          │ │
│  │  - Node-level tracing                               │ │
│  │  - Tool call monitoring                             │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Opik Dashboard                              │
│  ┌────────────────────────────────────────────────────┐ │
│  │  📊 Real-time metrics                               │ │
│  │  📈 Evaluation scores                               │ │
│  │  👍 User feedback                                   │ │
│  │  🧪 Experiment results                              │ │
│  │  💰 Cost tracking                                   │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Impact & Benefits

| Feature | Benefit |
|---------|---------|
| **Full Tracing** | Debug issues by replaying exact conversations |
| **Custom Metrics** | Domain-specific evaluation for sustainability platform |
| **Feedback Collection** | Continuous improvement from user signals |
| **A/B Testing** | Data-driven prompt optimization |
| **Cost Tracking** | Budget management and optimization |
| **Performance Monitoring** | SLA compliance and latency optimization |

---

## 📁 File Structure

```
app/ai/
├── opik.py              # Core Opik integration (600+ lines)
│   ├── OpikTracer       # LangChain/LangGraph integration
│   ├── FeedbackCollector # Multi-dimensional feedback
│   ├── ExperimentTracker # A/B testing
│   ├── Custom Metrics   # Sustainability, Engagement, Quality
│   └── Decorators       # @track_agent_call, @track_tool_usage
├── groq_client.py       # Main agent with Opik tracking
├── event_agent.py       # Event workflow with journey tracking
└── social_media_node.py # Social media with feedback collection

app/api/v1/endpoints/
└── analytics.py         # Opik-powered analytics API (350+ lines)
    ├── /feedback        # Single & multi-dimensional
    ├── /evaluate        # Custom metric evaluation
    ├── /experiments     # A/B test management
    └── /dashboard       # Comprehensive metrics
```

---

## 🚀 Why This Matters

1. **Production-Ready Observability**: Full visibility into AI behavior
2. **Continuous Improvement**: User feedback drives model optimization
3. **Cost Control**: Token and cost tracking for budget management
4. **Compliance**: Audit trail for all AI interactions
5. **Quality Assurance**: Automated evaluation with custom metrics

---

**EcoPulse** - Making AI Observability as Green as Our Mission 🌱
