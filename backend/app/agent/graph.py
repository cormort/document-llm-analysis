from langgraph.graph import StateGraph, END
from langgraph.prebuilt import tools_condition

from app.agent.state import AgentState
from app.agent.nodes import call_model, tool_node

# 1. Initialize Graph
workflow = StateGraph(AgentState)

# 2. Add Nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# 3. Define Edges
workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    tools_condition,
)

workflow.add_edge("tools", "agent")

# 4. Compile
graph = workflow.compile()
