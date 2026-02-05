

import opik
from opik.evaluation import evaluate
from opik.evaluation.metrics import BaseMetric
from opik.evaluation.metrics.score_result import ScoreResult
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# Import your existing graph building blocks
from app.ai.groq_client import (
    AgentState, 
    ALL_TOOLS, 
    get_chat_llm, 
    SYSTEM_PROMPT, 
    build_event_subgraph,
    END, START
)
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

# Initialize Client
client = opik.Opik()

# =========================================================
# 1. DEFINE EVALUATION-SPECIFIC AGENT COMPILER
# =========================================================
def compile_agent_for_eval(user_id="test_user"):
    """
    A version of the agent compiler that uses MemorySaver (RAM) 
    instead of PostgresSaver (Database) for fast, safe testing.
    """
    # USE MEMORY INSTEAD OF DB
    checkpointer = MemorySaver()
    store = InMemoryStore()
    
    # --- Recreate the Graph Logic (Same as production) ---
    # We copy the graph construction logic here so it uses the memory checkpointer
    
    # 1. Bind Tools
    model = get_chat_llm().bind_tools(ALL_TOOLS)

    # 2. Define Nodes (Simplified for Eval)
    def call_model(state: AgentState):
        messages = state["messages"]
        # Inject context if needed (simplified for eval)
        if not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
        response = model.invoke(messages)
        return {"messages": [response]}

    def route_step(state: AgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            if any(tc["name"] == "start_event_creation" for tc in last.tool_calls):
                return "event_manager"
            return "tools"
        return "end"

    # 3. Build Graph
    workflow = StateGraph(AgentState)
    workflow.add_node("llm", call_model)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))
    
    # Event Subgraph (reused from production code)
    event_agent = build_event_subgraph().compile() 
    workflow.add_node("event_manager", event_agent)

    workflow.add_edge(START, "llm")
    workflow.add_conditional_edges("llm", route_step, {
        "tools": "tools",
        "event_manager": "event_manager",
        "end": END
    })
    workflow.add_edge("tools", "llm")
    workflow.add_edge("event_manager", END)

    # 4. Compile with Memory Checkpointer
    return workflow.compile(checkpointer=checkpointer, store=store)


# =========================================================
# 2. DEFINE METRICS (Same as before)
# =========================================================
class ToolComplianceMetric(BaseMetric):
    def __init__(self, name: str = "tool_compliance"):
        self.name = name

    def score(self, output: dict, expected_tool_call: str, **kwargs) -> ScoreResult:
        tool_calls = output.get("tool_calls", [])
        actual_tool = tool_calls[0]["name"] if tool_calls else "NONE"
        
        if actual_tool == expected_tool_call:
            return ScoreResult(name=self.name, value=1.0, reason="Correct tool called.")
        
        if expected_tool_call == "broadcast_neighbor_help" and actual_tool != "broadcast_neighbor_help":
            return ScoreResult(name=self.name, value=0.0, reason="CRITICAL: Failed to trigger neighbor help safety tool.")

        return ScoreResult(name=self.name, value=0.0, reason=f"Expected '{expected_tool_call}', got '{actual_tool}'")

# =========================================================
# 3. DEFINE TASK
# =========================================================
def evaluation_task(dataset_item):
    input_message = dataset_item.get("input_user_message")
    
    # USE THE MEMORY AGENT COMPILER
    agent = compile_agent_for_eval(user_id="test_user")
    
    # Create a unique config for this test run
    config = {"configurable": {"thread_id": "eval_run"}}
    
    try:
        # Run agent
        result = agent.invoke({"messages": [("user", input_message)]}, config=config)
        
        last_message = result["messages"][-1]
        tool_calls = []
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tc in last_message.tool_calls:
                tool_calls.append({"name": tc["name"], "args": tc["args"]})
                
        return {
            "output": {"tool_calls": tool_calls, "response": last_message.content},
            "expected_tool_call": dataset_item.get("expected_tool_call") 
        }
    except Exception as e:
        return {
            "output": {"error": str(e)},
            "expected_tool_call": dataset_item.get("expected_tool_call")
        }

# =========================================================
# 4. RUN
# =========================================================
if __name__ == "__main__":
    dataset = client.get_dataset(name="Ecopulse_1")
    # print(f"Loaded {dataset.get_item_count()} test cases.")
    
    evaluate(
        dataset=dataset,
        task=evaluation_task,
        scoring_metrics=[ToolComplianceMetric()],
        experiment_name="EcoPulse_Memory_Eval_Run",
        verbose=True
    )