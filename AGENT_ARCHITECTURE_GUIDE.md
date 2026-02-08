# Agent Architecture Guide - Multi-Agent System with Tools

## Table of Contents
1. [System Overview](#system-overview)
2. [Agent Catalog](#agent-catalog)
3. [Tool Inventory](#tool-inventory)
4. [Multi-Agent Orchestration](#multi-agent-orchestration)
5. [ReAct Pattern](#react-pattern)
6. [Human-in-the-Loop](#human-in-the-loop)
7. [Interrupt Points](#interrupt-points)
8. [Voice LLM System](#voice-llm-system)
9. [State Management](#state-management)
10. [Detailed Tool Reference](#detailed-tool-reference)

---

## System Overview

### Architecture Type
**Multi-Agent System with Hierarchical Orchestration**

### Core Technologies
- **Framework:** LangGraph
- **LLM Provider:** Groq (Llama 3.3 70B)
- **Persistence:** PostgreSQL / SQLite
- **Observability:** Opik
- **Voice:** Whisper + ElevenLabs

### Design Pattern
**ReAct (Reasoning + Acting)** with human-in-the-loop checkpoints

---

## Agent Catalog

### 1. Green Sentinel (Main Agent)

**File:** `app/ai/groq_client.py`

**Type:** Conversational AI with Tool Access

**Purpose:** Primary user-facing agent that handles all general queries, routes to specialized sub-agents, and manages long-term memory.

**Capabilities:**
- General conversation and question answering
- Event creation delegation to Event Agent
- Memory management (save/retrieve user preferences)
- Community information lookup
- Web search integration
- Social media post generation
- Neighbor help requests

**State Schema:**
```python
class AgentState(TypedDict):
    messages: List[BaseMessage]
    thread_id: Optional[str]
    event_id: Optional[str]
    # ... inherits from EventAgentState
```

**Tools Available:**
- All API tools (11 tools)
- All Memory tools (3 tools)
- All Social Media tools (3 tools)
- **Total: 17+ tools**

**System Prompt:**
```
You are an AI Green Sentinel, a sustainability-focused community assistant...
```

**Tracking:**
```python
@track_agent_call(
    agent_name="Green Sentinel",
    agent_type="conversational",
    tags={"user_id": user_id}
)
```

**Graph Structure:**
```
START → agent → tools → agent → ... → END
          ↓
     event_workflow (subgraph)
```

---

### 2. Event Creation Agent (Sub-Agent)

**File:** `app/ai/event_agent.py`

**Type:** Multi-Step Form-Filling Agent with Human Feedback Loops

**Purpose:** Guides users through creating community events step-by-step, collecting all required information with validation and refinement.

**State Schema:**
```python
class EventAgentState(TypedDict):
    messages: List[BaseMessage]
    event_name: Optional[str]
    description: Optional[str]
    desc_iterations: int
    place: Optional[str]
    date: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    event_type: Optional[str]
    max_participants: Optional[str]
    guest_speakers: Optional[str]
    room_id: Optional[str]
    thread_id: Optional[str]
    trace_id: Optional[str]
    social_media_posts: Optional[Dict[str, str]]
    social_media_hashtags: Optional[list]
    social_media_feedback: Optional[list]
    suggestions: Optional[list[str]]
    format_hint: Optional[str]
```

**Workflow Stages:**
1. Entry → Parse event name from user input
2. Generate Description → AI creates 100-char description
3. Ask Feedback → User reviews description
4. Handle Feedback → Refine based on user input (iterative)
5. Ask Place → Collect event location
6. Ask Date → Collect event date
7. Ask Time → Collect start/end times
8. Ask Type → Collect event category
9. Ask Participants → Collect max participant count
10. Ask Guest Speakers → Collect speaker information
11. Social Media Generation → Auto-generate posts
12. Finalize → Create event in database

**Interrupt Points:** 8 human checkpoints (see [Interrupt Points](#interrupt-points))

**Tools Used:**
- `create_event_via_llm` (final creation)
- Social media tools (post generation)
- LLM for description generation and categorization

**Tracking:**
```python
@track_agent_call(
    agent_name="Event Entry Node",
    agent_type="analysis",
    tags={"stage": "entry"}
)
```

---

### 3. Event Manager Agent

**File:** `app/ai/event_manager_agent.py`

**Type:** Tool-Enabled Event Management Agent

**Purpose:** Handles event updates, queries, and management tasks.

**State Schema:**
```python
class EventAgentState(TypedDict):
    messages: List[BaseMessage]
    event_id: Optional[str]
    thread_id: Optional[str]
```

**Tools Available:**
```python
event_tools = [
    web_search,
    create_event_image,
    create_event_normal_image,
    create_event_image_promote_refine,
    update_event_via_llm,
    xpoz_mcp_tool
]
```

**Graph Structure:**
```
START → agent → tools → agent → ... → END
```

**Tracking:**
```python
@opik.track(name="Event Manager Agent Call")
```

---

### 4. Social Media Generation Agent (Node)

**File:** `app/ai/social_media_node.py`

**Type:** Specialized Content Generation Agent

**Purpose:** Creates platform-optimized social media posts for events.

**Capabilities:**
- Twitter post generation (280 chars)
- Instagram caption creation (150 chars + emojis)
- LinkedIn post writing (300 chars, professional tone)
- Trending hashtag fetching
- Post refinement based on feedback

**Functions:**
```python
@opik.track(name="Social Media Post Generation")
def generate_social_media_post(...)

@opik.track(name="Fetch Trending Hashtags")
def fetch_trending_hashtags(...)

@opik.track(name="Collect Post Feedback")
def collect_post_feedback(...)
```

**Integration:** Part of Event Creation Agent workflow

---

### 5. Voice Translation Agent (Node)

**File:** `app/ai/voice.py`

**Type:** Real-Time Audio Processing Agent

**Purpose:** Transcribe and translate voice messages in real-time for multi-language communication.

**Capabilities:**
- WebM audio transcription (Whisper)
- Language detection
- Real-time translation (Llama 3.3)
- Text-to-speech generation (ElevenLabs)

**Functions:**
```python
@track_agent_call(
    agent_name="Voice Transcription",
    agent_type="audio",
    tags={"language": "various"}
)
async def transcribe_audio(...)

@track_agent_call(
    agent_name="Voice Translation",
    agent_type="llm",
    tags={"type": "translation"}
)
async def translate_text(...)
```

**Tracking:**
```python
@track_agent_call(
    agent_name="Voice TTS",
    agent_type="audio",
    tags={"provider": "elevenlabs"}
)
async def generate_speech_bytes(...)
```

---

## Tool Inventory

### API Tools (11 Total)

**File:** `app/mcp/tools.py`

#### 1. `get_user_context`
- **Purpose:** Retrieve user profile and joined communities
- **Input:** None (uses runtime user_id)
- **Output:** Formatted user information string
- **Use Case:** Personalization, context building

#### 2. `get_community_context`
- **Purpose:** Get detailed community information
- **Input:** `room_id` (str)
- **Output:** Community details including facilities and staff
- **Use Case:** Answer community-specific questions

#### 3. `get_all_communities_context`
- **Purpose:** List all available communities
- **Input:** None
- **Output:** Summary of all communities
- **Use Case:** Help users discover communities

#### 4. `create_event_via_llm`
- **Purpose:** Create a new event in the database
- **Inputs:**
  - `event_name` (str)
  - `event_description` (str)
  - `event_type` (str)
  - `event_place` (str, optional)
  - `event_date` (str, optional)
  - `start_time` (str, optional)
  - `end_time` (str, optional)
  - `max_participants` (str, optional)
  - `guest_speakers` (str, optional)
  - `tag` (str, optional)
  - `event_classification` (str, optional)
  - `room_id` (str, optional)
- **Output:** Success/failure message with event ID
- **Use Case:** Finalize event creation

#### 5. `update_event_via_llm`
- **Purpose:** Update existing event details
- **Inputs:**
  - `event_id` (str, required)
  - All event fields (optional)
- **Output:** Confirmation message
- **Use Case:** Modify event information

#### 6. `start_event_creation`
- **Purpose:** Initialize event creation workflow
- **Input:** `event_name` (str)
- **Output:** Workflow initiation confirmation
- **Use Case:** Trigger Event Creation Agent

#### 7. `submit_user_response`
- **Purpose:** Submit user response to ongoing workflow
- **Input:** `thread_id` (str), `user_message` (str)
- **Output:** Next step in workflow
- **Use Case:** Continue multi-step processes

#### 8. `web_search`
- **Purpose:** Search the web for information
- **Input:** `query` (str)
- **Output:** Search results summary
- **Use Case:** Answer questions requiring external data

#### 9. `broadcast_neighbor_help`
- **Purpose:** Send help request to neighbors
- **Input:** `help_request` (str)
- **Output:** Broadcast confirmation
- **Use Case:** Community assistance requests

---

### Memory Tools (3 Total)

**File:** `app/mcp/memory.py`

#### 10. `save_memory`
- **Purpose:** Store user preferences and facts
- **Input:** `note` (str)
- **Output:** Confirmation message
- **Storage:** LangGraph PostgresStore
- **Use Case:** Remember user preferences

#### 11. `remove_memory`
- **Purpose:** Delete stored user information
- **Input:** `query` (str) - search term
- **Output:** Deletion confirmation
- **Use Case:** Forget outdated preferences

#### 12. `list_memories`
- **Purpose:** Retrieve all stored user notes
- **Input:** None
- **Output:** List of saved memories
- **Use Case:** Show user what's remembered

---

### Social Media Tools (3 Total)

**File:** `app/mcp/social_media_tools.py`

#### 13. `create_social_media_posts`
- **Purpose:** Generate platform-specific social media posts
- **Inputs:**
  - `event_name` (str)
  - `event_description` (str)
  - `event_place` (str)
  - `event_date` (str)
  - `event_type` (str)
  - `hashtags` (str, optional)
- **Output:** JSON with Twitter, Instagram, LinkedIn posts
- **Use Case:** Auto-generate event promotion content

#### 14. `get_trending_hashtags`
- **Purpose:** Fetch trending hashtags for event type
- **Inputs:**
  - `event_type` (str)
  - `event_name` (str)
- **Output:** JSON with hashtag list
- **Use Case:** Optimize social media reach

#### 15. `refine_social_media_post`
- **Purpose:** Improve post based on feedback
- **Inputs:**
  - `post_content` (str)
  - `platform` (str) - twitter/instagram/linkedin
  - `refinement_request` (str)
- **Output:** JSON with refined post
- **Use Case:** Iterate on post quality

---

### Image Generation Tools (3 Total)

**File:** `app/mcp/tools_manager.py`

#### 16. `create_event_image`
- **Purpose:** Generate event poster image
- **Input:** `description` (str)
- **Output:** Image URL
- **Provider:** Custom image generation service
- **Use Case:** Create event visuals

#### 17. `create_event_normal_image`
- **Purpose:** Generate standard image from prompt
- **Input:** `description` (str)
- **Output:** Image URL
- **Use Case:** General image creation

#### 18. `create_event_image_promote_refine`
- **Purpose:** Generate and refine promotional image
- **Input:** `description` (str)
- **Output:** Image URL
- **Use Case:** High-quality event promotion

---

### External Tools (1 Total)

**File:** `app/mcp/xpoz_mcp.py`

#### 19. `xpoz_mcp_tool`
- **Purpose:** Query external Xpoz MCP service
- **Input:** `query` (str)
- **Output:** Xpoz service response
- **Authentication:** Bearer token
- **Use Case:** Extended capabilities via external AI

---

## Multi-Agent Orchestration

### Hierarchical Structure

```
┌─────────────────────────────────────┐
│      Green Sentinel (Main)          │
│   - Conversation Management         │
│   - Tool Routing                    │
│   - Memory Integration              │
└──────────────┬──────────────────────┘
               │
               ├──► Event Creation Agent (Subgraph)
               │    - Step-by-step form
               │    - Description generation
               │    - Human feedback loops
               │    └──► Social Media Agent
               │         - Post generation
               │         - Hashtag fetching
               │
               ├──► Event Manager Agent
               │    - Event updates
               │    - Image generation
               │
               └──► Voice Translation Agent
                    - Transcription
                    - Translation
                    - TTS generation
```

### Agent Invocation Flow

**Example: Creating an Event**

1. **User:** "I want to create a tree planting event"

2. **Green Sentinel:**
   - Detects event creation intent
   - Calls `start_event_creation` tool
   - Transfers control to Event Creation Agent

3. **Event Creation Agent:**
   - Enters subgraph workflow
   - **Entry Node:** Extracts "tree planting" as event name
   - **Generate Description Node:** AI creates description
   - **Ask Feedback Node:** Presents description to user
   - **[INTERRUPT - Wait for user input]**

4. **User:** "That's perfect!"

5. **Event Creation Agent:**
   - **Handle Feedback Node:** Validates positive feedback
   - **Ask Place Node:** "Where will the event take place?"
   - **[INTERRUPT - Wait for user input]**

6. **User:** "Central Park"

7. **Event Creation Agent:**
   - Continues through all steps (date, time, type, etc.)
   - Each with interrupt for user input

8. **Social Media Agent:**
   - Generates platform posts
   - Fetches trending hashtags

9. **Event Creation Agent:**
   - **Finalize Node:** Calls `create_event_via_llm`
   - Returns success to user

10. **Green Sentinel:**
    - Receives completion notification
    - Presents final event details to user

---

## ReAct Pattern

### What is ReAct?

**ReAct = Reasoning + Acting**

A pattern where the LLM:
1. **Reasons** about what to do next (Thought)
2. **Acts** by calling a tool (Action)
3. **Observes** the result (Observation)
4. **Repeats** until task is complete

### Implementation in Green Sentinel

```python
def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"  # Execute tool
    return END  # Finished

workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")  # Loop back
```

### Example ReAct Loop

**User Query:** "What events are happening in my community?"

**Step 1 - Reason:**
```
Thought: I need to get the user's community first, then list events
Action: get_user_context
```

**Step 2 - Observe:**
```
Observation: User is in "Green Valley" community (room_id: 123)
```

**Step 3 - Reason:**
```
Thought: Now I know the community, I need to get events for room 123
Action: web_search("events in Green Valley community")
```

**Step 4 - Observe:**
```
Observation: Found 3 upcoming events...
```

**Step 5 - Respond:**
```
Here are the upcoming events in Green Valley:
1. Tree Planting - Feb 15
2. Recycling Drive - Feb 20
3. Community Cleanup - Feb 25
```

### ReAct in Event Creation

The Event Creation Agent uses ReAct within nodes:

```python
def generate_description_node(state: EventAgentState):
    # Reason: What kind of event is this?
    event_name = state["event_name"]
    
    # Act: Call LLM to generate description
    llm = get_chat_llm()
    response = llm.invoke([
        SystemMessage(content=PROMPT),
        HumanMessage(content=f"Generate for: {event_name}")
    ])
    
    # Observe: Extract description
    description = parse_response(response)
    
    # Decide: Need more info? Or continue?
    return {"description": description}
```

---

## Human-in-the-Loop

### What is Human-in-the-Loop?

A design pattern where **human input is required** at specific points in the agent workflow.

### Why Use It?

- **Quality Control:** Ensure AI output meets user expectations
- **Customization:** Allow users to refine AI-generated content
- **Trust:** Users see and approve each step
- **Learning:** Collect feedback for improvement

### Implementation in LangGraph

**Interrupt Configuration:**

```python
app = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=[
        "handle_feedback",
        "handle_place",
        "handle_date",
        # ... other nodes
    ]
)
```

### Flow Example

**Without Human-in-Loop (Dangerous):**
```
User Input → Agent → Tool Call → Database Write → Done
```

**With Human-in-Loop (Safe):**
```
User Input → Agent → Generate Output → [WAIT] → User Approval → Database Write → Done
```

### Code Pattern

**Ask Node (Present to User):**
```python
def ask_feedback_node(state):
    description = state["description"]
    return {
        "messages": [AIMessage(
            content=f"Here's the description: {description}. Good?"
        )]
    }
```

**[INTERRUPT] - Wait for user response**

**Handle Node (Process User Input):**
```python
def handle_feedback_node(state):
    user_feedback = state["messages"][-1].content
    
    if "yes" in user_feedback.lower():
        # User approved - continue
        return {"messages": [AIMessage("Great! Next step...")]}
    else:
        # User wants changes - refine
        refined = refine_description(user_feedback)
        return {
            "description": refined,
            "desc_iterations": state["desc_iterations"] + 1
        }
```

---

## Interrupt Points

### Event Creation Agent Interrupts

The Event Creation Agent has **8 interrupt points**:

#### 1. Description Feedback
- **Before Node:** `handle_feedback`
- **Purpose:** User reviews AI-generated description
- **User Choice:** Approve or request changes
- **Example:**
  ```
  AI: "Here's the description: 'Join us for eco-friendly tree planting!' Good?"
  [WAIT]
  User: "Add that it's family-friendly"
  ```

#### 2. Description Refinement Loop
- **Before Node:** `route_feedback` → `handle_feedback`
- **Purpose:** Iterative refinement (max 3 iterations)
- **Loop:** User can refine multiple times
- **Exit:** User approves or max iterations reached

#### 3. Place Input
- **Before Node:** `handle_place`
- **Purpose:** Collect event location
- **Example:**
  ```
  AI: "Where will the event take place?"
  [WAIT]
  User: "Central Park, Building A"
  ```

#### 4. Date Input
- **Before Node:** `handle_date`
- **Purpose:** Collect event date
- **Validation:** Agent validates date format
- **Example:**
  ```
  AI: "What date is the event?"
  [WAIT]
  User: "February 15, 2026"
  ```

#### 5. Time Input
- **Before Node:** `handle_time`
- **Purpose:** Collect start and end times
- **Example:**
  ```
  AI: "What time? (e.g., '10:00 AM - 2:00 PM')"
  [WAIT]
  User: "9:00 AM to 12:00 PM"
  ```

#### 6. Type Selection
- **Before Node:** `handle_type`
- **Purpose:** Categorize event
- **Options:** eco, wellness, social, networking, learning, charity, sports
- **Example:**
  ```
  AI: "What type of event? (eco, wellness, social, ...)"
  [WAIT]
  User: "eco"
  ```

#### 7. Participants Input
- **Before Node:** `handle_participants`
- **Purpose:** Set maximum participant count
- **Example:**
  ```
  AI: "Maximum number of participants?"
  [WAIT]
  User: "50"
  ```

#### 8. Guest Speakers Input
- **Before Node:** `handle_guest_speakers`
- **Purpose:** Collect speaker information
- **Optional:** Can skip with "none"
- **Example:**
  ```
  AI: "Any guest speakers? (or 'none')"
  [WAIT]
  User: "Dr. Jane Smith, Environmental Scientist"
  ```

### Interrupt Mechanics

**How Interrupts Work:**

1. **Agent reaches interrupt point**
   ```python
   # Execution pauses BEFORE this node
   interrupt_before=["handle_feedback"]
   ```

2. **State is saved to checkpointer**
   ```python
   checkpointer.put(config, state)
   ```

3. **Control returns to user**
   - API returns current state
   - User sees question/prompt

4. **User provides input**
   ```python
   new_message = HumanMessage(content="User response")
   ```

5. **Agent resumes**
   ```python
   app.invoke(
       {"messages": [new_message]},
       config={"thread_id": thread_id}
   )
   ```

### Resume Invocation

**API Pattern:**

```python
# Initial call - creates interrupt
result = app.invoke(
    {"messages": [HumanMessage("Create tree planting event")]},
    config={"configurable": {"thread_id": "abc123"}}
)
# Returns: "Here's the description... Good?"

# User approves
result = app.invoke(
    {"messages": [HumanMessage("Yes, perfect!")]},
    config={"configurable": {"thread_id": "abc123"}}
)
# Continues: "Great! Where will it take place?"

# ... continues through all interrupts
```

---

## Voice LLM System

### Architecture

**Real-Time Voice Translation System**

```
User A (English) ──┐
                   │
User B (Hindi) ────┼──► WebSocket Server ──► Transcription (Whisper)
                   │                              ↓
User C (Spanish) ──┘                         Translation (Llama 3.3)
                                                   ↓
                                              TTS (ElevenLabs)
                                                   ↓
                          ┌────────────────────────┴────────────────────────┐
                          ↓                         ↓                        ↓
                    User A (Hindi + Spanish)  User B (English + Spanish)  User C (English + Hindi)
```

### Components

**File:** `app/api/v1/endpoints/voice.py`

#### 1. WebSocket Manager

**Class:** `ConnectionManager`

**Purpose:** Manage real-time voice connections

**Methods:**
- `connect(ws, room_id, language)` - Accept new connection
- `disconnect(ws, room_id)` - Clean up on disconnect
- `broadcast_same_language(room_id, data, sender, language)` - Send audio to same-language users

**State Tracking:**
```python
rooms: Dict[str, List[WebSocket]]  # room_id → websockets
languages: Dict[WebSocket, str]    # websocket → language code
```

#### 2. Voice Processing Pipeline

**Step 1: Audio Reception**
```python
@router.websocket("/ws/{room_id}/{language}")
async def voice_ws(websocket, room_id, language):
    webm_bytes = await websocket.receive_bytes()
```

**Step 2: Transcription**
```python
@track_agent_call(agent_name="Voice Transcription")
async def transcribe_audio(webm: bytes, language: str):
    # Convert WebM to PCM
    pcm = webm_to_pcm(webm)
    
    # Convert to WAV
    wav = pcm_to_wav(pcm)
    
    # Whisper transcription
    result = client.audio.transcriptions.create(
        file=wav,
        model="whisper-large-v3",
        language=language
    )
    
    return result.text
```

**Step 3: Translation**
```python
@track_agent_call(agent_name="Voice Translation")
async def translate_text(text, from_lang, to_lang):
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "system",
            "content": "Professional translator..."
        }, {
            "role": "user",
            "content": f"Translate from {from_lang} to {to_lang}: {text}"
        }]
    )
    return completion.choices[0].message.content
```

**Step 4: Text-to-Speech**
```python
@track_agent_call(agent_name="Voice TTS")
async def generate_speech_bytes(text: str):
    audio_stream = ELEVEN_CLIENT.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_turbo_v2_5"
    )
    return b"".join(chunk for chunk in audio_stream)
```

#### 3. Broadcast Logic

**Language Filtering:**

```python
async def transcribe_and_broadcast(webm_bytes, room_id, source_language):
    text = await transcribe_audio(webm_bytes, source_language)
    
    # Group users by language
    users_by_lang = {}
    for ws in manager.rooms[room_id]:
        lang = manager.languages[ws]
        users_by_lang.setdefault(lang, []).append(ws)
    
    # Send to each language group
    for target_lang, users in users_by_lang.items():
        # Translate if needed
        if target_lang != source_language:
            final_text = await translate_text(text, source_language, target_lang)
        else:
            final_text = text
        
        # Send text
        payload = {
            "type": "text",
            "text": final_text,
            "lang_code": target_lang
        }
        for ws in users:
            await ws.send_text(json.dumps(payload))
        
        # Send audio (only for translations)
        if target_lang != source_language:
            audio_bytes = await generate_speech_bytes(final_text)
            for ws in users:
                await ws.send_bytes(audio_bytes)
```

### Voice Message Flow

**Example: 3 Users in Room**

**Setup:**
- User A: English
- User B: Hindi  
- User C: Spanish

**User A speaks:** "Hello everyone!"

**Processing:**
1. WebSocket receives WebM audio from User A
2. Transcribe (Whisper): "Hello everyone!" (English)
3. Group users by language:
   - English: [User A]
   - Hindi: [User B]
   - Spanish: [User C]

**To User A (same language):**
- ✅ Text: "Hello everyone!"
- ✅ Audio: Original (already heard)
- Action: Receives only text confirmation

**To User B (Hindi):**
- ✅ Text: "नमस्ते सभी!" (translated)
- ✅ Audio: Hindi TTS of translation
- Action: Hears Hindi audio + sees Hindi text

**To User C (Spanish):**
- ✅ Text: "¡Hola a todos!" (translated)
- ✅ Audio: Spanish TTS of translation
- Action: Hears Spanish audio + sees Spanish text

### Opik Tracking in Voice

**All voice operations are tracked:**

```python
# Transcription tracking
PerformanceMonitor.record_latency(
    operation="voice_transcription",
    latency_ms=250.5,
    success=True,
    metadata={
        "audio_duration_sec": 3.2,
        "text_length": 45,
        "language": "en"
    }
)

# Translation tracking
PerformanceMonitor.record_latency(
    operation="voice_translation",
    latency_ms=180.3,
    success=True,
    metadata={
        "from_lang": "en",
        "to_lang": "hi",
        "input_length": 45,
        "output_length": 38
    }
)

# TTS tracking
PerformanceMonitor.record_latency(
    operation="voice_tts",
    latency_ms=420.1,
    success=True,
    metadata={
        "text_length": 38,
        "audio_bytes": 15360
    }
)
```

---

## State Management

### Persistence Layer

**PostgreSQL Checkpointer:**

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver(conn)
checkpointer.setup()

app = workflow.compile(checkpointer=checkpointer)
```

**SQLite Checkpointer (Development):**

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver(conn)
checkpointer.setup()
```

### Thread Management

**Each conversation has a unique thread_id:**

```python
thread_id = str(uuid.uuid4())

config = {
    "configurable": {
        "thread_id": thread_id,
        "user_id": user_id
    }
}

result = app.invoke(input_state, config=config)
```

### State Recovery

**Resume from last checkpoint:**

```python
# Get current state
current_state = app.get_state(config)

# Continue from interrupt
app.invoke(
    {"messages": [HumanMessage("User response")]},
    config=config
)
```

### Long-Term Memory

**LangGraph Store (PostgreSQL):**

```python
from langgraph.store.postgres import PostgresStore

store = PostgresStore(conn)
store.setup()

# Save memory
store.put(
    namespace=("memories", user_id),
    key="preference_1",
    value={"data": "User prefers eco events"}
)

# Search memory
results = store.search(
    namespace=("memories", user_id),
    query="eco events"
)
```

---

## Detailed Tool Reference

### Tool Binding

**How tools are bound to agents:**

```python
from app.mcp.tools import APItools
from app.mcp.memory import MemoryTools
from app.mcp.social_media_tools import SocialMediaTools

ALL_TOOLS = APItools + MemoryTools + SocialMediaTools

model = get_chat_llm().bind_tools(ALL_TOOLS)
```

### Tool Execution Node

**LangGraph ToolNode:**

```python
from langgraph.prebuilt import ToolNode

tool_node = ToolNode(ALL_TOOLS)

workflow.add_node("tools", tool_node)
```

### Tool Call Format

**LangChain Tool Call:**

```python
# Agent decides to call tool
tool_call = {
    "name": "create_event_via_llm",
    "args": {
        "event_name": "Tree Planting",
        "event_description": "Community tree planting event",
        "event_type": "eco"
    },
    "id": "call_abc123"
}

# ToolNode executes
result = tool_node.invoke(tool_call)
```

### Runtime Context

**Tools receive runtime context:**

```python
@tool
def get_user_context(runtime: ToolRuntime) -> str:
    # Access user_id from config
    user_id = runtime.config["configurable"]["user_id"]
    
    # Access store
    memories = runtime.store.search(("memories", user_id))
    
    return f"User {user_id} with {len(memories)} memories"
```

---

## Summary

### Agent Count: 5

1. **Green Sentinel** - Main conversational agent
2. **Event Creation Agent** - Multi-step event builder
3. **Event Manager Agent** - Event updates & management
4. **Social Media Agent** - Content generation
5. **Voice Translation Agent** - Real-time multilingual voice

### Tool Count: 19

- **API Tools:** 9 (user/community/event management)
- **Memory Tools:** 3 (save/remove/list)
- **Social Media Tools:** 3 (create/hashtags/refine)
- **Image Tools:** 3 (generate/promote/refine)
- **External Tools:** 1 (Xpoz MCP)

### Key Features

✅ **Multi-Agent Orchestration** - Hierarchical agent system  
✅ **ReAct Pattern** - Reasoning + Acting loop  
✅ **Human-in-the-Loop** - 8 interrupt points in Event Creation  
✅ **Voice LLM** - Real-time transcription, translation, TTS  
✅ **Persistent State** - PostgreSQL checkpointer  
✅ **Long-Term Memory** - LangGraph store integration  
✅ **Full Observability** - Opik tracking on all operations  

### Technology Stack

- **Framework:** LangGraph
- **LLM:** Groq (Llama 3.3 70B Versatile)
- **Voice:** Whisper Large V3 + ElevenLabs Turbo V2.5
- **Database:** PostgreSQL / SQLite
- **Observability:** Opik
- **Patterns:** ReAct, Human-in-Loop, Multi-Agent
