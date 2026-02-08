# Opik Integration Guide - Comprehensive AI Observability

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Tracing & Monitoring](#tracing--monitoring)
5. [Custom Evaluation Metrics](#custom-evaluation-metrics)
6. [Feedback Collection](#feedback-collection)
7. [Performance Monitoring](#performance-monitoring)
8. [Experiment Tracking](#experiment-tracking)
9. [Best Practices](#best-practices)
10. [Usage Examples](#usage-examples)

---

## Overview

Opik is integrated throughout the EcoPulse AI Platform to provide enterprise-grade observability, monitoring, and evaluation for all AI interactions. This integration enables:

- **Full trace capture** for all LLM calls, agent interactions, and tool executions
- **Real-time performance monitoring** with latency tracking and cost analysis
- **Custom evaluation metrics** tailored to sustainability and community engagement
- **User feedback collection** with scoring and sentiment analysis
- **A/B testing** through experiment tracking
- **Conversation analytics** for insight into user engagement patterns

---

## Architecture

### Initialization

```python
# Global Opik client (app/ai/opik.py)
opik_client = Opik(
    project_name="EcoPulse-AI-Platform",
    workspace="default"
)

# Global tracer for LangChain/LangGraph integration
opik_tracer = OpikTracer(
    project_name="EcoPulse-AI-Platform",
    tags=["production", "langgraph", "multi-agent"]
)
```

### Integration Points

1. **LangGraph Agents** - Tracked via `OpikTracer` callbacks
2. **Function Decorators** - `@track_agent_call`, `@track_tool_usage`, `@track_llm_generation`
3. **Span Contexts** - Manual span creation for fine-grained tracking
4. **Performance Monitors** - Automated latency and success rate tracking

---

## Core Components

### 1. Opik Client (`opik_client`)

The central client instance that manages all interactions with the Opik platform.

**Configuration:**
- Project: `EcoPulse-AI-Platform`
- Workspace: Configurable via `settings.OPIK_WORKSPACE`
- Tags: `["production", "langgraph", "multi-agent"]`

**Usage:**
```python
from app.ai.opik import opik_client

# Log custom trace
trace = opik_client.trace(
    name="custom_operation",
    input={"query": "user question"},
    output={"response": "ai answer"}
)
```

### 2. Opik Tracer (`opik_tracer`)

LangChain-compatible tracer that automatically captures LLM calls, chains, and agent executions.

**Features:**
- Automatic LLM call logging
- Token usage tracking
- Cost calculation
- Error capture

**Usage:**
```python
from app.ai.opik import opik_tracer

# In LangChain invocations
response = llm.invoke(messages, config={"callbacks": [opik_tracer]})
```

### 3. Opik Context (`opik_context`)

Thread-safe context manager for accessing current trace and span.

**Usage:**
```python
from opik import opik_context

# Update current span metadata
opik_context.update_current_span(
    metadata={"custom_field": "value"}
)

# Get current trace ID
trace_id = opik_context.get_current_trace_id()
```

---

## Tracing & Monitoring

### Agent Call Tracking

**Decorator:** `@track_agent_call()`

**Purpose:** Tracks entire agent execution including input, output, latency, and errors.

**Parameters:**
- `agent_name` (str): Human-readable agent name
- `agent_type` (str): Category - "conversational", "analysis", "audio", "llm"
- `capture_input` (bool): Whether to log input data
- `capture_output` (bool): Whether to log output data
- `tags` (dict): Custom tags for filtering

**Example:**
```python
@track_agent_call(
    agent_name="Green Sentinel",
    agent_type="conversational",
    tags={"user_id": "123"}
)
async def call_model(state: AgentState):
    # Agent logic here
    return {"messages": [response]}
```

**Captured Data:**
- Function name and arguments
- Execution start/end time
- Total latency (ms)
- Success/failure status
- Input/output snapshots
- Exception details (if any)
- Custom tags and metadata

### Tool Usage Tracking

**Decorator:** `@track_tool_usage()`

**Purpose:** Monitors tool invocations and their outcomes.

**Parameters:**
- `tool_name` (str): Tool identifier
- `tool_category` (str): Type - "general", "search", "api", "database"

**Example:**
```python
@track_tool_usage(tool_name="web_search", tool_category="search")
def web_search(query: str) -> str:
    # Search logic
    return results
```

**Captured Data:**
- Tool name and category
- Input parameters
- Output results
- Execution time
- Success rate

### LLM Generation Tracking

**Decorator:** `@track_llm_generation()`

**Purpose:** Detailed logging of LLM completions with token and cost tracking.

**Parameters:**
- `model_name` (str): LLM identifier (e.g., "groq", "gpt-4")
- `generation_type` (str): "completion" or "chat"

**Example:**
```python
@track_llm_generation(model_name="groq", generation_type="completion")
async def generate_response(prompt: str):
    response = llm.invoke(prompt)
    return response
```

**Captured Data:**
- Model name and version
- Prompt and completion
- Token counts (input/output/total)
- Estimated cost
- Temperature and other parameters
- Latency

### Span Contexts

**Function:** `create_span_context()`

**Purpose:** Create custom spans for granular operation tracking.

**Parameters:**
- `name` (str): Span name
- `span_type` (str): Category - "general", "llm", "tool", "audio"
- `metadata` (dict): Additional context

**Example:**
```python
from app.ai.opik import create_span_context

with create_span_context(
    name="Voice Transcription",
    span_type="audio",
    metadata={"language": "en"}
):
    # Transcription logic
    text = transcribe(audio_bytes)
```

**Use Cases:**
- Multi-step operations
- External API calls
- Database queries
- Audio/video processing
- Custom business logic

---

## Custom Evaluation Metrics

### 1. SustainabilityRelevance

**Purpose:** Evaluates how well responses align with sustainability and environmental themes.

**Scoring:**
- 1.0 = Highly relevant to sustainability
- 0.7 = Somewhat relevant
- 0.3 = Minimal relevance
- 0.0 = Not relevant

**Keywords Tracked:**
- eco, green, sustainable, carbon
- renewable, environment, climate
- recycle, organic, conservation

**Usage:**
```python
from app.ai.opik import SustainabilityRelevance

metric = SustainabilityRelevance()
score = metric.score(
    input="How can I reduce carbon footprint?",
    output="Use renewable energy and recycle more."
)
# Returns: {"value": 1.0, "reason": "Highly relevant..."}
```

### 2. CommunityEngagement

**Purpose:** Measures response quality in promoting community participation.

**Scoring:**
- 1.0 = Strong call-to-action for community
- 0.5 = Mentions community but passive
- 0.0 = No community engagement

**Keywords Tracked:**
- join, participate, together, community
- event, meet, collaborate, neighbor

**Usage:**
```python
from app.ai.opik import CommunityEngagement

metric = CommunityEngagement()
score = metric.score(
    input="What can we do together?",
    output="Join our community cleanup event this Saturday!"
)
# Returns: {"value": 1.0, "reason": "Strong engagement..."}
```

### 3. ResponseQuality

**Purpose:** Comprehensive quality assessment of AI responses.

**Evaluation Criteria:**
- **Completeness:** Does it fully answer the question?
- **Clarity:** Is it well-structured and easy to understand?
- **Accuracy:** Is the information correct?
- **Actionability:** Does it provide next steps?

**Scoring Scale:** 0.0 to 1.0

**Usage:**
```python
from app.ai.opik import ResponseQuality

metric = ResponseQuality()
score = metric.score(
    input="How do I create an event?",
    output="To create an event: 1. Click Create Event 2. Fill details..."
)
# Returns: {"value": 0.9, "reason": "Complete, clear, actionable"}
```

---

## Feedback Collection

### FeedbackCollector Class

**Purpose:** Capture user feedback, ratings, and sentiment for continuous improvement.

### Methods

#### 1. `log_feedback()`

**Captures explicit user feedback scores.**

```python
from app.ai.opik import feedback_collector

feedback_collector.log_feedback(
    trace_id="abc123",
    score=5,
    feedback_type="thumbs_up",
    comment="Very helpful!",
    metadata={"user_id": "user_123"}
)
```

**Parameters:**
- `trace_id` (str): Opik trace identifier
- `score` (float): Rating (1-5 or 0-1)
- `feedback_type` (str): Category - "thumbs_up", "thumbs_down", "rating"
- `comment` (str, optional): User comment
- `metadata` (dict, optional): Additional context

#### 2. `analyze_sentiment()`

**Performs automatic sentiment analysis on text.**

```python
sentiment = feedback_collector.analyze_sentiment(
    text="This is amazing!",
    trace_id="abc123"
)
# Returns: "positive", "negative", or "neutral"
```

**Sentiment Rules:**
- Positive: "great", "amazing", "perfect", "excellent", "helpful"
- Negative: "bad", "terrible", "wrong", "useless", "poor"

#### 3. `get_feedback_stats()`

**Retrieves aggregated feedback metrics for a time period.**

```python
stats = feedback_collector.get_feedback_stats(
    project_name="EcoPulse-AI-Platform",
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 2, 1)
)
# Returns: {
#   "total_feedback": 150,
#   "average_score": 4.2,
#   "positive_ratio": 0.85,
#   "sentiment_breakdown": {...}
# }
```

### Integration in Agents

```python
# In human feedback node
def handle_feedback_node(state: EventAgentState):
    feedback_text = state["messages"][-1].content
    thread_id = state.get("thread_id")
    
    # Analyze sentiment
    sentiment = feedback_collector.analyze_sentiment(
        text=feedback_text,
        trace_id=thread_id
    )
    
    # Log structured feedback
    feedback_collector.log_feedback(
        trace_id=thread_id,
        score=1.0 if sentiment == "positive" else 0.5,
        feedback_type="user_refinement",
        comment=feedback_text
    )
```

---

## Performance Monitoring

### PerformanceMonitor Class

**Purpose:** Track latency, throughput, success rates, and system health.

### Methods

#### 1. `record_latency()`

**Records operation timing and success metrics.**

```python
from app.ai.opik import PerformanceMonitor

PerformanceMonitor.record_latency(
    operation="voice_transcription",
    latency_ms=250.5,
    success=True,
    metadata={
        "audio_duration": 3.2,
        "language": "en"
    }
)
```

**Parameters:**
- `operation` (str): Operation identifier
- `latency_ms` (float): Duration in milliseconds
- `success` (bool): Whether operation succeeded
- `metadata` (dict): Additional context

#### 2. `get_performance_metrics()`

**Retrieves aggregated performance data.**

```python
metrics = PerformanceMonitor.get_performance_metrics(
    operation="voice_transcription",
    time_window_hours=24
)
# Returns: {
#   "avg_latency_ms": 245.3,
#   "p95_latency_ms": 380.0,
#   "success_rate": 0.98,
#   "total_calls": 1250
# }
```

#### 3. `track_token_usage()`

**Monitors LLM token consumption and costs.**

```python
PerformanceMonitor.track_token_usage(
    model="groq-llama-3.3-70b",
    input_tokens=150,
    output_tokens=300,
    cost_usd=0.00045
)
```

### Real-World Integration Example

```python
@track_agent_call(agent_name="Voice Translation", agent_type="llm")
async def translate_text(text: str, from_lang: str, to_lang: str) -> str:
    start_time = datetime.now()
    
    try:
        # Translation logic
        result = llm.translate(text)
        
        # Record success
        PerformanceMonitor.record_latency(
            operation="voice_translation",
            latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
            success=True,
            metadata={
                "from_lang": from_lang,
                "to_lang": to_lang,
                "text_length": len(text)
            }
        )
        return result
        
    except Exception as e:
        # Record failure
        PerformanceMonitor.record_latency(
            operation="voice_translation",
            latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
            success=False,
            metadata={"error": str(e)}
        )
        raise
```

---

## Experiment Tracking

### ExperimentTracker Class

**Purpose:** Run A/B tests and compare prompt/model performance.

### Methods

#### 1. `create_experiment()`

**Initialize a new experiment.**

```python
from app.ai.opik import experiment_tracker

exp_id = experiment_tracker.create_experiment(
    name="Event Description Prompts",
    description="Testing concise vs detailed prompts",
    variants=["variant_a", "variant_b"]
)
```

#### 2. `log_variant_result()`

**Record result for a specific variant.**

```python
experiment_tracker.log_variant_result(
    experiment_id=exp_id,
    variant_name="variant_a",
    trace_id="trace_123",
    metrics={"latency_ms": 450, "user_rating": 4.5}
)
```

#### 3. `get_experiment_results()`

**Retrieve aggregated experiment metrics.**

```python
results = experiment_tracker.get_experiment_results(exp_id)
# Returns: {
#   "variant_a": {"avg_latency": 450, "avg_rating": 4.2},
#   "variant_b": {"avg_latency": 520, "avg_rating": 4.6}
# }
```

### Use Case: Prompt A/B Testing

```python
# Test two different event description prompts
variants = {
    "concise": "Generate a short 50-char event description",
    "detailed": "Generate a comprehensive 100-char description with emojis"
}

exp_id = experiment_tracker.create_experiment(
    name="Event Description Style",
    variants=list(variants.keys())
)

for variant_name, prompt in variants.items():
    result = generate_description(prompt)
    
    # Log result
    experiment_tracker.log_variant_result(
        experiment_id=exp_id,
        variant_name=variant_name,
        trace_id=current_trace_id,
        metrics={
            "user_satisfaction": get_rating(),
            "engagement_score": calculate_engagement()
        }
    )

# Analyze winner
results = experiment_tracker.get_experiment_results(exp_id)
```

---

## Best Practices

### 1. Consistent Metadata

Always include relevant context in traces:

```python
config = {
    "callbacks": [opik_tracer],
    "metadata": {
        "user_id": user_id,
        "thread_id": thread_id,
        "workflow_stage": "event_creation",
        "timestamp": datetime.now().isoformat()
    }
}
```

### 2. Error Handling

Wrap tracing code to prevent failures from breaking functionality:

```python
try:
    opik_context.update_current_span(metadata={"key": "value"})
except Exception as e:
    # Log but don't crash
    print(f"Opik logging failed: {e}")
```

### 3. Selective Logging

Don't log sensitive data (passwords, tokens, PII):

```python
@track_agent_call(
    agent_name="Auth Handler",
    capture_input=False,  # Don't log passwords
    capture_output=False
)
def authenticate_user(username, password):
    # Auth logic
    pass
```

### 4. Performance Optimization

Batch metric recording when possible:

```python
# Instead of individual calls
for item in batch:
    PerformanceMonitor.record_latency(...)  # ❌ Slow

# Use batch operations
metrics = [calculate_metric(item) for item in batch]
PerformanceMonitor.record_batch(metrics)  # ✅ Faster
```

### 5. Trace Correlation

Link related operations with thread_id:

```python
# Start of conversation
thread_id = str(uuid.uuid4())

# All subsequent traces use same thread_id
config = {"metadata": {"thread_id": thread_id}}
```

---

## Usage Examples

### Example 1: Voice Transcription with Full Observability

```python
@track_agent_call(
    agent_name="Voice Transcription",
    agent_type="audio",
    tags={"language": "various"}
)
async def transcribe_audio(webm: bytes, language: str) -> str | None:
    start_time = datetime.now()
    
    with create_span_context(
        name="Voice Transcription",
        span_type="audio",
        metadata={"language": language}
    ):
        try:
            # Convert audio
            pcm = webm_to_pcm(webm)
            
            # Record audio metadata
            opik_context.update_current_span(
                metadata={
                    "audio_duration_sec": pcm.size / SAMPLE_RATE,
                    "sample_rate": SAMPLE_RATE
                }
            )
            
            # Transcribe
            result = client.audio.transcriptions.create(...)
            
            # Record success
            PerformanceMonitor.record_latency(
                operation="voice_transcription",
                latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                success=True,
                metadata={"text_length": len(result.text)}
            )
            
            return result.text
            
        except Exception as e:
            # Record failure
            PerformanceMonitor.record_latency(
                operation="voice_transcription",
                latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                success=False,
                metadata={"error": str(e)}
            )
            return None
```

### Example 2: Event Agent with Human Feedback

```python
def handle_feedback_node(state: EventAgentState):
    feedback_text = state["messages"][-1].content
    thread_id = state.get("thread_id")
    
    # Analyze sentiment
    sentiment = feedback_collector.analyze_sentiment(
        text=feedback_text,
        trace_id=thread_id
    )
    
    # Score based on keywords
    score = 1.0 if "perfect" in feedback_text.lower() else 0.5
    
    # Log feedback
    feedback_collector.log_feedback(
        trace_id=thread_id,
        score=score,
        feedback_type="description_refinement",
        comment=feedback_text,
        metadata={
            "sentiment": sentiment,
            "iteration": state.get("desc_iterations", 0)
        }
    )
    
    return {
        "messages": [AIMessage(content="Thanks for feedback!")]
    }
```

### Example 3: Multi-Agent Workflow Tracking

```python
def build_event_subgraph():
    workflow = StateGraph(EventAgentState)
    
    # Each node is tracked
    workflow.add_node("entry", entry_node)  # @track_agent_call
    workflow.add_node("generate_desc", generate_description_node)
    workflow.add_node("social_media", social_media_generation_node)
    
    # Compile with tracer
    app = workflow.compile()
    
    # Wrap with Opik tracking
    app = track_langgraph(app, opik_tracer)
    
    return app
```

---

## Summary

Opik provides comprehensive observability across the entire EcoPulse AI Platform:

✅ **Automatic Tracing** - All LLM calls, agents, and tools are logged  
✅ **Custom Metrics** - Sustainability and engagement scoring  
✅ **User Feedback** - Sentiment analysis and rating collection  
✅ **Performance Monitoring** - Latency, success rates, token usage  
✅ **Experimentation** - A/B testing for prompts and models  
✅ **Analytics** - Conversation patterns and user insights  

This enables data-driven improvements, quality assurance, and continuous optimization of AI interactions.
