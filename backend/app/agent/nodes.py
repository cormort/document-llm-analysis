from app.agent.state import AgentState
from app.agent.tools import retrieve_documents
from app.core.config import settings
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from pydantic import SecretStr

# 1. Initialize Tools
tools = [retrieve_documents]
tool_node = ToolNode(tools)

# 2. Dynamic Model Factory
def get_model(config: RunnableConfig):
    # Extract config from 'configurable' passed via graph.invoke(..., config={...})
    configurable = config.get("configurable", {})
    model_config = configurable.get("model_config", {})
    
    # Priority: Request Config > Env Settings > Defaults
    provider = model_config.get("provider") or settings.LLM_SMART_PROVIDER
    model_name = model_config.get("model_name") or settings.LLM_SMART_MODEL
    api_key = model_config.get("api_key") or settings.GOOGLE_API_KEY
    local_url = model_config.get("local_url") or settings.LLM_SMART_URL
    
    if provider == "Gemini":
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=SecretStr(api_key) if api_key else None,
            temperature=0,
        )
    elif provider == "OpenAI":
        llm = ChatOpenAI(
            model=model_name,
            api_key=SecretStr(api_key) if api_key else None,
            temperature=0,
        )
    elif "Local" in provider:
        llm = ChatOpenAI(
            model=model_name,
            api_key=SecretStr("lm-studio"),  # Local usually ignores key or needs "lm-studio"
            base_url=local_url,
            temperature=0,
        )
    elif provider == "omlx":
        llm = ChatOpenAI(
            model=model_name,
            api_key=SecretStr("omlx"),  # omlx local server, key is a placeholder
            base_url=local_url,
            temperature=0,
        )
    else:
        # Fallback
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            google_api_key=SecretStr(api_key) if api_key else None,
            temperature=0,
        )
        
    return llm.bind_tools(tools)

# 3. Define Nodes with Config Injection
async def call_model(state: AgentState, config: RunnableConfig):
    model = get_model(config)
    messages = state["messages"]
    response = await model.ainvoke(messages)
    return {"messages": [response]}
