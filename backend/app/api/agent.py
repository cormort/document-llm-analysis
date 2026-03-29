from collections.abc import AsyncGenerator
from typing import Any

from app.agent.graph import graph
from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

class AgentChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    llm_config: dict[str, Any] | None = None
    
async def stream_agent_generator(
    message: str, thread_id: str, llm_config: dict[str, Any] | None = None
) -> AsyncGenerator[dict[str, str], None]:
    """Stream agent events from LangGraph."""
    
    # 1. Prepare State
    input_state = {"messages": [HumanMessage(content=message)], "sender": "user"}
    
    # 2. Config for thread persistence (MemorySaver needed for real persistence)
    # For now, we just run it stateless or simple
    run_config = RunnableConfig(
        configurable={
            "thread_id": thread_id,
            "model_config": llm_config or {},
        }
    )
    
    try:
        # 3. Stream from Graph
        # Using astream to get events. 
        # stream_mode="values" returns the full state at each step, 
        # stream_mode="messages" returns new messages.
        async for event in graph.astream(
            input_state, config=run_config, stream_mode="messages"
        ):
            # event is a wrapper, usually { 'messages': [...] } or message chunk
            # If stream_mode="messages", it yields chunks or message objects

            # Simple handling: yield content if it's an AI message
            if isinstance(event, tuple):
                # (chunk, metadata)
                chunk = event[0]
                content = getattr(chunk, "content", None)
                if content:
                    yield {"event": "message", "data": str(content)}
            else:
                content = getattr(event, "content", None)
                if content:
                    yield {"event": "message", "data": str(content)}
                 
        yield {"event": "done", "data": "[DONE]"}
        
    except Exception as e:
        yield {"event": "error", "data": str(e)}

@router.post("/chat", response_class=EventSourceResponse)
async def chat_agent(request: AgentChatRequest):
    """Chat with the agent via SSE."""
    return EventSourceResponse(stream_agent_generator(request.message, request.thread_id or "default", request.llm_config))
