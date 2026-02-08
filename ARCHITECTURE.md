# EcoPulse Backend - Complete Architecture & Implementation Guide

## 📊 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ECOPULSE BACKEND SYSTEM                            │
│                        FastAPI + LangGraph + Groq + Opik                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  REST API Clients  │  WebSocket Clients  │  Mobile/Web Frontend             │
│  (HTTP/HTTPS)      │  (WS/WSS)           │  (React, etc.)                   │
└──────────┬───────────────────┬────────────────────────┬─────────────────────┘
           │                   │                        │
           ▼                   ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY LAYER (FastAPI)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐    │
│  │  REST Endpoints │  │  WebSocket Routes│  │  Authentication (JWT)   │    │
│  ├─────────────────┤  ├──────────────────┤  ├─────────────────────────┤    │
│  │ /api/v1/users   │  │ /messages/ws/    │  │ - Token validation      │    │
│  │ /api/v1/events  │  │ /voice/ws/       │  │ - User session mgmt     │    │
│  │ /api/v1/rooms   │  │ /ws/{event_id}   │  │ - OAuth integration     │    │
│  │ /api/v1/auth    │  └──────────────────┘  └─────────────────────────┘    │
│  └─────────────────┘                                                         │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AI AGENT ORCHESTRATION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    GREEN SENTINEL AGENT (Main)                     │     │
│  │                     LangGraph + Groq LLM                           │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  Nodes:                                                            │     │
│  │  • call_model (LLM invocation + Opik tracking)                    │     │
│  │  • tools (Tool execution)                                          │     │
│  │  • event_manager (Event creation subgraph)                        │     │
│  │  • handle_feedback (User feedback collection)                     │     │
│  │                                                                    │     │
│  │  State: PostgreSQL Checkpointer + Store                           │     │
│  │  Context: User + Community pre-loaded context                     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                │                                             │
│                                ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    EVENT MANAGER SUBGRAPH                          │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  Workflow:                                                         │     │
│  │  entry → generate_description → ask_feedback → route_feedback     │     │
│  │       → ask_place → handle_place → ask_date → handle_date         │     │
│  │       → ask_time → handle_time → ask_type → handle_type           │     │
│  │       → ask_participants → handle_participants                    │     │
│  │       → ask_guest_speakers → handle_guest_speakers                │     │
│  │       → social_media_generation → finalize                         │     │
│  │                                                                    │     │
│  │  Interrupts: handle_feedback, handle_place, handle_date,          │     │
│  │              handle_type, handle_post_feedback                     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                │                                             │
│                                ▼                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │              EVENT MANAGER AI (Separate Agent)                     │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  Purpose: Handle event-specific queries in chat                    │     │
│  │  Tools: Event image generation, web search, social insights       │     │
│  │  Triggered: Via @AI mentions in event chat WebSocket              │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TOOL ECOSYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │   API TOOLS     │  │  MEMORY TOOLS    │  │  SOCIAL MEDIA TOOLS      │   │
│  ├─────────────────┤  ├──────────────────┤  ├──────────────────────────┤   │
│  │ • get_user_     │  │ • save_memory    │  │ • create_social_media_   │   │
│  │   context       │  │ • remove_memory  │  │   posts                  │   │
│  │ • get_community │  │ • list_memories  │  │ • get_trending_hashtags  │   │
│  │   _context      │  │                  │  │ • refine_social_media_   │   │
│  │ • create_event_ │  │ Store: Postgres  │  │   post                   │   │
│  │   via_llm       │  │ Namespace-based  │  │                          │   │
│  │ • update_event_ │  │ per user         │  │ Platform: Twitter,       │   │
│  │   via_llm       │  │                  │  │ Instagram, LinkedIn      │   │
│  │ • start_event_  │  └──────────────────┘  └──────────────────────────┘   │
│  │   creation      │                                                        │
│  │ • web_search    │  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ • broadcast_    │  │  EVENT MANAGER   │  │  EXTERNAL SERVICES       │   │
│  │   neighbor_help │  │  TOOLS           │  │  INTEGRATION             │   │
│  └─────────────────┘  ├──────────────────┤  ├──────────────────────────┤   │
│                       │ • create_event_  │  │ • xpoz_mcp_tool          │   │
│                       │   image          │  │   (Social insights)      │   │
│                       │ • create_event_  │  │ • web_search             │   │
│                       │   normal_image   │  │   (Tavily API)           │   │
│                       │ • create_event_  │  │ • Groq Whisper           │   │
│                       │   image_promote_ │  │   (Voice transcription)  │   │
│                       │   refine         │  │ • googletrans            │   │
│                       │ • update_event_  │  │   (Message translation)  │   │
│                       │   via_llm        │  └──────────────────────────┘   │
│                       │ • xpoz_mcp_tool  │                                  │
│                       └──────────────────┘                                  │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      REAL-TIME COMMUNICATION LAYER                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                EVENT MESSAGES WEBSOCKET                            │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  Endpoint: /api/v1/messages/ws/{event_id}                         │     │
│  │  Features:                                                         │     │
│  │  • Room-scoped message broadcasting                               │     │
│  │  • Per-user language translation (googletrans)                    │     │
│  │  • @AI trigger for Event Manager AI                               │     │
│  │  • Message persistence to database                                │     │
│  │  • JWT token authentication                                        │     │
│  │  • Event membership validation                                     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                    VOICE WEBSOCKET                                 │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  Endpoint: /api/v1/voice/ws/{room_id}/{language}                  │     │
│  │  Features:                                                         │     │
│  │  • Real-time audio streaming (WebM/Opus)                          │     │
│  │  • Server-side transcription (Groq Whisper)                       │     │
│  │  • Language-scoped transcript broadcasting                         │     │
│  │  • Audio codec: WebM (Opus) → PCM → WAV                           │     │
│  │  • Silence detection and filtering                                │     │
│  │  • Opik tracking for transcription metrics                        │     │
│  │                                                                    │     │
│  │  Pipeline:                                                         │     │
│  │  Audio bytes → webm_to_pcm → is_silence check →                   │     │
│  │  pcm_to_wav → Groq Whisper → text → broadcast to language group  │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY & ANALYTICS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                         OPIK INTEGRATION                           │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  Project: EcoPulse-AI-Platform                                    │     │
│  │                                                                    │     │
│  │  Tracing:                                                          │     │
│  │  • Every LLM call tracked with @opik.track                        │     │
│  │  • Agent calls (Green Sentinel, Event Manager, Event Manager AI)  │     │
│  │  • Tool invocations                                                │     │
│  │  • Voice transcription operations                                 │     │
│  │  • Social media generation                                         │     │
│  │                                                                    │     │
│  │  Metrics:                                                          │     │
│  │  • SustainabilityRelevance (custom metric)                        │     │
│  │  • CommunityEngagement (custom metric)                            │     │
│  │  • ResponseQuality (composite metric)                             │     │
│  │  • Latency tracking (PerformanceMonitor)                          │     │
│  │  • Token usage & cost estimation                                  │     │
│  │                                                                    │     │
│  │  Feedback:                                                         │     │
│  │  • User sentiment analysis (positive/negative/neutral)            │     │
│  │  • Multi-dimensional feedback (helpful, accurate, relevant, etc.) │     │
│  │  • Task completion scoring                                        │     │
│  │  • Conversation analytics                                          │     │
│  │  • User journey tracking                                           │     │
│  │                                                                    │     │
│  │  Optimization:                                                     │     │
│  │  • EvolutionaryOptimizer for prompt tuning                        │     │
│  │  • Dataset: Ecopulse_4 (input/expected_output)                   │     │
│  │  • Metric: LevenshteinRatio similarity                            │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA PERSISTENCE LAYER                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                      POSTGRESQL DATABASE                           │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  Models (SQLAlchemy ORM):                                         │     │
│  │                                                                    │     │
│  │  Core Entities:                                                    │     │
│  │  • User (auth, profile, lang preference)                          │     │
│  │  • Room (communities/apartments)                                  │     │
│  │  • UserRoom (membership linking)                                  │     │
│  │  • Event (community events)                                       │     │
│  │  • EventUser (event participation)                                │     │
│  │                                                                    │     │
│  │  Communication:                                                    │     │
│  │  • Message (user-to-user DMs)                                     │     │
│  │  • EventMessage (event chat messages)                             │     │
│  │  • Notification (push notifications)                              │     │
│  │                                                                    │     │
│  │  Gamification:                                                     │     │
│  │  • Champion (leaderboard)                                         │     │
│  │  • NearPeople (location-based discovery)                          │     │
│  │                                                                    │     │
│  │  LangGraph State:                                                  │     │
│  │  • Checkpoints (conversation state snapshots)                     │     │
│  │  • Store (long-term memory, namespaced)                           │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                               │
│  Connection Pool: psycopg_pool.ConnectionPool                                │
│  Max Size: 10 connections                                                    │
│  Auto-commit: Enabled                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL INTEGRATIONS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  LLM Provider:       Groq (openai/gpt-oss-20b)                              │
│  Speech-to-Text:     Groq Whisper (whisper-large-v3)                        │
│  Web Search:         Tavily API                                              │
│  Social Insights:    Xpoz MCP (Twitter, Instagram, TikTok, Reddit)          │
│  Translation:        googletrans                                             │
│  Image Generation:   Custom image service (promote/refine)                   │
│  Observability:      Opik (Comet ML)                                         │
│  LangSmith:          Prompt management                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Complete Tool Inventory

### 1. **API Tools** (`app/mcp/tools.py`)

| Tool Name | Purpose | Parameters | Returns |
|-----------|---------|------------|---------|
| `get_user_context` | Fetch user profile & joined communities | `runtime` | User profile summary |
| `get_community_context` | Get community details, facilities, staff | `room_id, runtime` | Community info |
| `get_all_communities_context` | List all available communities | `runtime` | All communities list |
| `create_event_via_llm` | Create new event in database | `event_name, description, type, place, date, time, participants, speakers, tag, classification, room_id, runtime` | Event creation status |
| `update_event_via_llm` | Update existing event | `event_id, [all event fields], runtime` | Update status |
| `start_event_creation` | Trigger event creation workflow | `event_name` | Workflow initiation |
| `web_search` | Search web using Tavily API | `query` | Search results |
| `broadcast_neighbor_help` | Send help request to neighbors | `help_request, runtime` | Broadcast status |

### 2. **Memory Tools** (`app/mcp/memory.py`)

| Tool Name | Purpose | Parameters | Returns |
|-----------|---------|------------|---------|
| `save_memory` | Save user note to long-term memory | `note, runtime` | Confirmation |
| `remove_memory` | Delete memory by search query | `query, runtime` | Deletion status |
| `list_memories` | List all saved memories | `runtime` | Memory list |

**Storage**: PostgreSQL Store, namespaced by `("memories", user_id)`

### 3. **Social Media Tools** (`app/mcp/social_media_tools.py`)

| Tool Name | Purpose | Parameters | Returns |
|-----------|---------|------------|---------|
| `create_social_media_posts` | Generate posts for Twitter, Instagram, LinkedIn | `event_name, description, place, date, type, hashtags` | JSON with platform-specific posts |
| `get_trending_hashtags` | Fetch trending hashtags for event type | `event_type, event_name` | JSON with hashtag list |
| `refine_social_media_post` | Improve existing post based on feedback | `post_content, platform, refinement_request` | Refined post |

### 4. **Event Manager Tools** (`app/mcp/tools_manager.py`)

| Tool Name | Purpose | Parameters | Returns |
|-----------|---------|------------|---------|
| `create_event_image` | Generate event poster image | `description` | Image URL |
| `create_event_normal_image` | Generate standard image | `description` | Image URL |
| `create_event_image_promote_refine` | Generate & refine promotional image | `description` | Image URL |
| `xpoz_mcp_tool` | Query social media insights | `query` | Social insights data |
| `web_search` | Web search for event ideas | `query` | Search results |
| `update_event_via_llm` | Update event fields | `event_id, [fields]` | Update status |

### 5. **Voice Processing** (`app/ai/voice.py`)

| Function | Purpose | Parameters | Returns |
|----------|---------|------------|---------|
| `webm_to_pcm` | Convert WebM audio to PCM | `webm: bytes` | `np.ndarray` (PCM) |
| `is_silence` | Detect if audio is silent | `pcm: np.ndarray` | `bool` |
| `pcm_to_wav` | Convert PCM to WAV format | `pcm: np.ndarray` | `io.BytesIO` (WAV) |
| `transcribe_audio` | Transcribe audio using Groq Whisper | `webm: bytes, language: str` | `str | None` (transcript) |

**Opik Integration**: Tracks latency, audio metadata, success/failure

---

## 🔄 Data Flow Diagrams

### Event Creation Flow

```
User Request
    │
    ▼
Green Sentinel Agent
    │
    ├─ Detects "create event" intent
    │
    ▼
start_event_creation tool
    │
    ▼
Event Manager Subgraph
    │
    ├─ entry_node (track user journey)
    ├─ generate_description_node (LLM + Opik tracking)
    ├─ ask_feedback_node
    ├─ INTERRUPT → route_feedback (up to 4 iterations)
    ├─ ask_place_node
    ├─ INTERRUPT → handle_place
    ├─ ask_date_node
    ├─ INTERRUPT → handle_date
    ├─ ask_time_node
    ├─ handle_time
    ├─ ask_type_node
    ├─ INTERRUPT → handle_type
    ├─ ask_participants_node
    ├─ handle_participants
    ├─ ask_guest_speakers_node
    ├─ handle_guest_speakers
    ├─ social_media_generation_node
    │   ├─ fetch_trending_hashtags (xpoz_mcp_tool)
    │   ├─ generate_social_media_post (LLM)
    │   └─ Return posts (Twitter, Instagram, LinkedIn)
    ├─ INTERRUPT → handle_post_feedback
    └─ finalize_node
        ├─ Categorize event (LLM)
        ├─ Extract TAG/CLASS
        ├─ create_event_via_llm tool
        └─ Save to PostgreSQL
```

### Voice Call Flow

```
User (Browser)
    │
    │ MediaRecorder (WebM/Opus)
    │
    ▼
WebSocket Connection
/api/v1/voice/ws/{room_id}/{language}
    │
    ├─ Store connection + language
    │
    ▼
Audio Bytes Received
    │
    ├─ broadcast_bytes (to all except sender)
    │
    └─ Background Task: transcribe_and_broadcast
        │
        ▼
    transcribe_audio(webm, language)
        │
        ├─ webm_to_pcm (PyAV decode/resample)
        ├─ is_silence check
        ├─ pcm_to_wav
        ├─ Groq Whisper API call
        ├─ Opik tracking (latency, metadata)
        │
        ▼
    Transcript text
        │
        ▼
    broadcast_text(room_id, {type: "text", text, language}, language)
        │
        └─ Send only to connections with matching language
```

### Event Chat with AI Flow

```
User sends message in event chat
    │
    ▼
WebSocket /api/v1/messages/ws/{event_id}
    │
    ├─ Validate JWT token
    ├─ Check event membership
    │
    ▼
Message received
    │
    ├─ Save to database (EventMessage)
    │
    ├─ Check if starts with "@AI"
    │   │
    │   ├─ YES → handle_ai_request(background task)
    │   │   │
    │   │   ├─ Get Event Manager AI agent
    │   │   ├─ Invoke with user prompt
    │   │   ├─ Get AI response
    │   │   ├─ Save as EventMessage (username="ai", full_name="Event Manager AI")
    │   │   └─ Broadcast to all event participants
    │   │
    │   └─ NO → Continue
    │
    ▼
broadcast(message, event_id)
    │
    └─ For each connected user:
        ├─ Get user.lang (default: "en")
        ├─ Translate message if user.lang != "en" (googletrans)
        └─ Send translated message via WebSocket
```

---

## 🏗️ Component Details

### 1. **Green Sentinel Agent** (Main Conversational AI)

**File**: `app/ai/groq_client.py`

**State**: 
- Inherits from `EventAgentState`
- Contains `messages`, `thread_id`, and all event fields

**Graph Structure**:
```
START → llm → {tools | event_manager | ask_feedback | end}
            ↓           ↓                 ↓
          tools   event_manager    ask_feedback
            ↓           ↓                 ↓
          llm         END          handle_feedback
                                         ↓
                                        END
```

**Key Features**:
- Pre-loads user & community context from database
- Injects dynamic context into system prompt
- Detects explicit feedback in conversation
- Routes to tools, event subgraph, or feedback handler
- Comprehensive Opik tracking for every LLM call
- Custom metrics: sustainability, engagement, quality

**Tools Bound**: `ALL_TOOLS = APItools + MemoryTools + SocialMediaTools`

---

### 2. **Event Manager Subgraph** (Event Creation Workflow)

**File**: `app/ai/event_agent.py`

**State**: `EventAgentState` with all event fields + social media fields

**Graph Structure**:
```
entry → generate_description → route_feedback (loop up to 4x)
     → ask_place → handle_place
     → ask_date → handle_date  
     → ask_time → handle_time
     → ask_type → handle_type
     → ask_participants → handle_participants
     → ask_guest_speakers → handle_guest_speakers
     → social_media_generation
     → ask_post_feedback → handle_post_feedback
     → finalize
```

**Interrupt Points**: 
- `handle_feedback`, `handle_place`, `handle_date`, `handle_type`, `handle_post_feedback`
- User must provide input to resume workflow

**Opik Tracking**:
- Every node tracked with metadata (workflow_stage, event_name, thread_id)
- LLM generation latency, iteration count, prompt/response lengths
- Performance metrics, user journey tracking

---

### 3. **Event Manager AI** (Event-Specific Assistant)

**File**: `app/ai/event_manager_agent.py`

**Purpose**: Separate agent for handling event-related queries in chat

**Tools**:
- `create_event_image`, `create_event_normal_image`, `create_event_image_promote_refine`
- `web_search`, `xpoz_mcp_tool`, `update_event_via_llm`

**Triggered By**: `@AI` mentions in event chat WebSocket

**State**: Simple state with `messages`, `event_id`, `thread_id`

---

### 4. **WebSocket Managers**

#### Event Messages Manager
**File**: `app/api/v1/endpoints/event_messages.py`

**Connection Tracking**: `Dict[str, List[(WebSocket, User)]]` by event_id

**Features**:
- JWT authentication via query param
- Event membership validation
- Message persistence to database
- Per-user translation (googletrans)
- @AI trigger for Event Manager AI

#### Voice Manager
**File**: `app/api/v1/endpoints/voice.py`

**Connection Tracking**: 
- `rooms: Dict[str, List[WebSocket]]`
- `languages: Dict[WebSocket, str]`

**Features**:
- Room-scoped audio broadcasting
- Language-aware transcript distribution
- Server-side transcription via Groq Whisper
- Opik tracking for transcription operations

---

### 5. **Opik Integration Framework**

**File**: `app/ai/opik.py`

**Components**:

1. **Decorators**:
   - `@track_agent_call`: Track agent invocations
   - `@track_tool_usage`: Track tool calls
   - `@track_llm_generation`: Track LLM generations

2. **Metrics**:
   - `SustainabilityRelevance`: Custom metric for eco-focus
   - `CommunityEngagement`: Engagement potential scoring
   - `ResponseQuality`: Composite quality metric

3. **Collectors**:
   - `FeedbackCollector`: Multi-dimensional user feedback
   - `PerformanceMonitor`: Latency & token tracking
   - `ConversationAnalytics`: Conversation pattern analysis
   - `ExperimentTracker`: A/B test tracking

4. **Utilities**:
   - `create_span_context`: Manual span creation
   - `get_trace_url`: Generate Opik dashboard links

---

### 6. **Prompt Management**

**File**: `app/ai/prompts.py`

**Versioned Prompts** (via Opik):
- `GREEN_SENTINEL_SYSTEM_PROMPT`: Main agent instructions
- `EVENT_CREATION_SUBAGENT_PROMPT`: Event workflow rules
- `EVENT_CATEGORIZATION_PROMPT`: TAG/CLASS extraction
- `EVENT_MANAGER_SYSTEM_PROMPT`: Event-specific AI instructions
- `SOCIAL_MEDIA_POST_GENERATION_PROMPT`: Post generation template
- `SOCIAL_MEDIA_SYSTEM_PROMPT`: Social media expert persona

**Prompt Class**: Wraps `opik.Prompt` for versioning and tracking

---

## 🔐 Security & Authentication

**JWT Implementation**:
- Token-based authentication
- User session management
- Scoped access to resources

**WebSocket Auth**:
- Token passed as query parameter
- Validated before connection upgrade
- User context maintained per connection

**Database Security**:
- Connection pooling with max size limits
- Auto-commit enabled
- Prepared statements via SQLAlchemy ORM

---

## 📊 Database Schema Summary

### Core Tables

**users**:
- id, username, email, full_name, hashed_password
- is_active, lang (language preference)

**rooms**:
- id, room_id (unique), name, description, location
- Facilities: doctor, shop, security, partyhall, cleaning, playground
- staff_assignments (JSON)

**user_rooms**:
- id, user_id, room_id, room_number
- Links users to communities

**events**:
- id, room_id, event_name, event_description
- event_type, event_place, event_date, start_time, end_time
- max_participants, guest_speakers
- tag, event_classification, image_url

**event_users**:
- id, event_id, user_id
- Tracks event participation

**event_messages**:
- id, event_id, user_id, content, username, full_name
- created_at, image_url

**notifications**:
- id, user_id, title, message, is_read
- created_at, image_url

**champions**:
- id, user_id, room_id, points

**near_people**:
- id, user_id, room_id, latitude, longitude
- created_at, is_active

---

## 🚀 Deployment Architecture

**Container**: Docker (Multi-stage build)

**Base Image**: Python 3.11-slim

**Dependencies**:
- Build tools: gcc, g++, make, build-essential
- Media: ffmpeg (for PyAV/voice)
- Database: libpq-dev, libpq5 (PostgreSQL client)

**Runtime**:
- Uvicorn ASGI server on port 8000
- WebSocket support via `websockets>=12.0`
- Auto-reload disabled in production

**Environment Variables**:
- `DATABASE_URL`: PostgreSQL connection string
- `GROQ_API_KEY`: Groq LLM/Whisper API key
- `OPIK_API_KEY`: Opik observability key
- `TAVILY_API_KEY`: Web search API key
- `XPOZ_API_KEY`: Social insights API key

---

## 🔄 Integration Points

### 1. LangGraph ↔ PostgreSQL
- Checkpointer: Saves conversation state snapshots
- Store: Long-term memory storage (namespaced)
- Auto-setup on agent compilation

### 2. FastAPI ↔ LangGraph Agents
- Agents compiled with connection pool
- Thread-based conversation management
- State passed via `config["configurable"]`

### 3. Opik ↔ LangChain/LangGraph
- `OpikTracer` attached to LLM invocations
- `track_langgraph()` wraps compiled graphs
- `@track` decorator on custom functions

### 4. WebSockets ↔ Background Tasks
- Transcription runs in background (`asyncio.create_task`)
- AI responses generated asynchronously
- Translation happens per-broadcast

### 5. Groq ↔ Application
- LLM: `ChatGroq` with tool binding
- Whisper: Direct API call for transcription
- Callbacks: Opik tracer attached to all calls

---

## 📈 Monitoring & Observability

### Metrics Tracked

1. **Performance**:
   - LLM latency (ms)
   - Tool execution time
   - Transcription latency
   - WebSocket connection count

2. **Quality**:
   - Sustainability relevance score (0-1)
   - Community engagement score (0-1)
   - Response quality (length, actionability, politeness)

3. **User Feedback**:
   - Helpful (0-1)
   - Accurate (0-1)
   - Relevant (0-1)
   - Actionable (0-1)
   - Satisfaction (0-1)

4. **Token Usage**:
   - Estimated input/output tokens
   - Cost estimation (USD)

### Opik Dashboard

All traces viewable at: `https://app.comet.com/opik/traces/{trace_id}`

Project: `EcoPulse-AI-Platform`

Tags: `production`, `langgraph`, `multi-agent`

---

## 🧪 Optimization Pipeline

**File**: `app/Opik_Features/optimize_ecopulse.py`

**Optimizer**: EvolutionaryOptimizer (replacing FewShotBayesian)

**Dataset**: Ecopulse_4
- Columns: `input`, `expected_output`
- Format: CSV with 50+ samples

**Metric**: LevenshteinRatio (string similarity)

**Target**: `GREEN_SENTINEL_SYSTEM_PROMPT`

**Process**:
1. Load dataset from Opik (with CSV fallback)
2. Run baseline evaluation
3. Generate prompt variations
4. Evaluate each variant
5. Select best-performing prompt
6. Version in Opik for deployment

---

## 🔧 Key Configuration Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage container build |
| `requirements.txt` | Python dependencies (pinned versions) |
| `vercel.json` | Serverless deployment config |
| `.env` | Environment variables (API keys, DB URL) |
| `run_migration.py` | Database migration runner |

---

## 📚 Complete File Map

```
app/
├── __init__.py
├── main.py                         # FastAPI application entry
├── database.py                     # SQLAlchemy setup
├── dependencies.py                 # Dependency injection
│
├── ai/                             # AI Agent Layer
│   ├── groq_client.py             # Green Sentinel Agent
│   ├── event_agent.py             # Event Manager Subgraph
│   ├── event_manager_agent.py     # Event Manager AI
│   ├── voice.py                   # Voice transcription pipeline
│   ├── prompts.py                 # Centralized prompt management
│   ├── opik.py                    # Opik observability framework
│   └── social_media_node.py       # Social media generation
│
├── api/v1/endpoints/              # API Endpoints
│   ├── auth.py                    # Authentication
│   ├── users.py                   # User management
│   ├── rooms.py                   # Community management
│   ├── events.py                  # Event CRUD
│   ├── event_messages.py          # Event chat WebSocket
│   ├── voice.py                   # Voice WebSocket
│   ├── notifications.py           # Push notifications
│   ├── champions.py               # Leaderboard
│   ├── near_people.py             # Location-based discovery
│   └── webhooks.py                # External webhooks
│
├── mcp/                           # Tool Ecosystem
│   ├── tools.py                   # API tools
│   ├── memory.py                  # Memory tools
│   ├── social_media_tools.py      # Social media tools
│   ├── tools_manager.py           # Event Manager tools
│   └── xpoz_mcp.py                # Social insights integration
│
├── models/                        # SQLAlchemy Models
│   ├── user.py
│   ├── room.py
│   ├── user_room.py
│   ├── event.py
│   ├── event_user.py
│   ├── event_message.py
│   ├── notification.py
│   ├── champion.py
│   └── near_people.py
│
├── schemas/                       # Pydantic Schemas
│   ├── user.py
│   ├── room.py
│   ├── event.py
│   ├── token.py
│   └── ...
│
├── crud/                          # Database Operations
│   ├── user.py
│   ├── room.py
│   ├── event.py
│   └── ...
│
├── core/                          # Core Configuration
│   ├── config.py                  # Settings (Pydantic)
│   └── security.py                # JWT & password hashing
│
└── utils/
    └── image.py                   # Image generation utilities
```

---

## 🎯 Key Takeaways

1. **Multi-Agent Architecture**: Green Sentinel (main) → Event Manager (subgraph) → Event Manager AI (chat assistant)

2. **Comprehensive Tooling**: 30+ tools across API, memory, social media, and event management

3. **Real-Time Communication**: Two WebSocket systems (event chat + voice) with language-aware broadcasting

4. **Full Observability**: Every LLM call, tool invocation, and transcription tracked in Opik

5. **State Persistence**: LangGraph checkpoints + store in PostgreSQL for conversation continuity

6. **Optimization Pipeline**: Evolutionary algorithm for prompt tuning against Ecopulse dataset

7. **Production-Ready**: Docker containerization, dependency pinning, error handling, and monitoring

---

This architecture enables EcoPulse to deliver a sophisticated, AI-powered sustainability platform with real-time communication, intelligent event management, and comprehensive analytics.
