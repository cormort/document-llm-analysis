"""
MCP Tools API - 暴露 MCP Server 工具給前端使用。

提供文件轉換、網路搜索等 MCP 工具的 REST API 端點。
"""

import os
from typing import Any

import structlog
from app.services.mcp_client_manager import (
    init_mcp_manager,
)
from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field

logger = structlog.get_logger()
router = APIRouter(prefix="/mcp", tags=["MCP Tools"])

# 臨時檔案目錄
TEMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "temp",
)
os.makedirs(TEMP_DIR, exist_ok=True)


# ========== Request/Response Models ==========


class ConvertToMarkdownRequest(BaseModel):
    """文件轉 Markdown 請求"""

    uri: str = Field(
        ...,
        description="檔案 URI (file://, http://, https://, data:)",
    )


class ConvertToMarkdownResponse(BaseModel):
    """文件轉 Markdown 回應"""

    success: bool
    markdown: str | None = None
    error: str | None = None


class WebSearchRequest(BaseModel):
    """網路搜索請求"""

    query: str = Field(..., description="搜索查詢")
    engine: str = Field(
        default="duckduckgo",
        description="搜索引擎 (duckduckgo, bing, brave)",
    )
    limit: int = Field(default=10, ge=1, le=50, description="結果數量限制")


class WebSearchResponse(BaseModel):
    """網路搜索回應"""

    success: bool
    results: list[dict[str, Any]] | None = None
    error: str | None = None


class ChromaQueryRequest(BaseModel):
    """ChromaDB 查詢請求"""

    collection_name: str = Field(..., description="Collection 名稱")
    query: str = Field(..., description="查詢文字")
    n_results: int = Field(default=5, ge=1, le=50, description="結果數量")


class MCPToolCallRequest(BaseModel):
    """通用 MCP 工具調用請求"""

    server_name: str = Field(..., description="MCP Server 名稱")
    tool_name: str = Field(..., description="工具名稱")
    arguments: dict[str, Any] = Field(default_factory=dict, description="工具參數")


class MCPToolCallResponse(BaseModel):
    """通用 MCP 工具調用回應"""

    success: bool
    data: Any | None = None
    error: str | None = None


# ========== API Endpoints ==========


@router.get("/servers")
async def list_mcp_servers() -> dict[str, Any]:
    """
    列出所有可用的 MCP Servers

    Returns:
        可用的 MCP Servers 列表及其狀態
    """
    try:
        manager = await init_mcp_manager()
        servers = manager.get_available_servers()
        return {
            "success": True,
            "servers": servers,
            "total": len(servers),
            "connected": sum(1 for s in servers if s.get("connected")),
        }
    except Exception as e:
        logger.error("Failed to list MCP servers", error=str(e))
        return {"success": False, "error": str(e), "servers": []}


@router.get("/tools/{server_name}")
async def list_server_tools(server_name: str) -> dict[str, Any]:
    """
    列出指定 MCP Server 的所有工具

    Args:
        server_name: MCP Server 名稱
    """
    try:
        manager = await init_mcp_manager()
        tools = await manager.list_tools(server_name)
        return {
            "success": True,
            "server": server_name,
            "tools": tools,
            "count": len(tools),
        }
    except Exception as e:
        logger.error("Failed to list tools", server=server_name, error=str(e))
        return {"success": False, "error": str(e), "tools": []}


@router.post("/call", response_model=MCPToolCallResponse)
async def call_mcp_tool(request: MCPToolCallRequest) -> MCPToolCallResponse:
    """
    通用 MCP 工具調用端點

    可調用任意已連接的 MCP Server 工具。
    """
    try:
        manager = await init_mcp_manager()
        result = await manager.call_tool(
            request.server_name,
            request.tool_name,
            request.arguments,
        )

        if result.get("success"):
            return MCPToolCallResponse(
                success=True,
                data=result.get("data"),
            )
        else:
            return MCPToolCallResponse(
                success=False,
                error=result.get("error", "Unknown error"),
            )

    except Exception as e:
        logger.error(
            "MCP tool call failed",
            server=request.server_name,
            tool=request.tool_name,
            error=str(e),
        )
        return MCPToolCallResponse(success=False, error=str(e))


@router.post("/convert-to-markdown", response_model=ConvertToMarkdownResponse)
async def convert_to_markdown(request: ConvertToMarkdownRequest) -> ConvertToMarkdownResponse:
    """
    使用 markitdown-mcp 將檔案轉換為 Markdown

    支援的格式：PDF, DOCX, XLSX, PPTX, HTML, 圖片等。
    """
    try:
        manager = await init_mcp_manager()
        result = await manager.call_tool(
            "markitdown",
            "convert_to_markdown",
            {"uri": request.uri},
        )

        if result.get("success"):
            data = result.get("data", {})
            markdown = data.get("content", "") if isinstance(data, dict) else str(data)
            return ConvertToMarkdownResponse(success=True, markdown=markdown)
        else:
            return ConvertToMarkdownResponse(
                success=False,
                error=result.get("error", "Conversion failed"),
            )

    except Exception as e:
        logger.error("Convert to markdown failed", uri=request.uri, error=str(e))
        return ConvertToMarkdownResponse(success=False, error=str(e))


@router.post("/convert-to-markdown/upload", response_model=ConvertToMarkdownResponse)
async def convert_uploaded_file_to_markdown(
    file: UploadFile = File(...),
) -> ConvertToMarkdownResponse:
    """
    上傳檔案並轉換為 Markdown

    支援的格式：PDF, DOCX, XLSX, PPTX, HTML, 圖片等。
    """
    try:
        # 儲存上傳的檔案
        filename = file.filename or "uploaded_file"
        temp_path = os.path.join(TEMP_DIR, filename)
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 轉換為 file:// URI
        uri = f"file://{os.path.abspath(temp_path)}"

        manager = await init_mcp_manager()
        result = await manager.call_tool(
            "markitdown",
            "convert_to_markdown",
            {"uri": uri},
        )

        # 清理臨時檔案
        try:
            os.remove(temp_path)
        except OSError:
            pass

        if result.get("success"):
            data = result.get("data", {})
            markdown = data.get("content", "") if isinstance(data, dict) else str(data)
            return ConvertToMarkdownResponse(success=True, markdown=markdown)
        else:
            return ConvertToMarkdownResponse(
                success=False,
                error=result.get("error", "Conversion failed"),
            )

    except Exception as e:
        logger.error("Convert uploaded file failed", filename=file.filename, error=str(e))
        return ConvertToMarkdownResponse(success=False, error=str(e))


@router.post("/web-search", response_model=WebSearchResponse)
async def web_search(request: WebSearchRequest) -> WebSearchResponse:
    """
    使用 open-webSearch 進行網路搜索

    支援多個搜索引擎：DuckDuckGo, Bing, Brave 等。
    不需要 API Key。
    """
    try:
        manager = await init_mcp_manager()
        result = await manager.call_tool(
            "open-websearch",
            "search",
            {
                "query": request.query,
                "engine": request.engine,
                "limit": request.limit,
            },
        )

        if result.get("success"):
            data = result.get("data", {})
            results = data.get("results", []) if isinstance(data, dict) else []
            return WebSearchResponse(success=True, results=results)
        else:
            return WebSearchResponse(
                success=False,
                error=result.get("error", "Search failed"),
            )

    except Exception as e:
        logger.error("Web search failed", query=request.query, error=str(e))
        return WebSearchResponse(success=False, error=str(e))


@router.post("/chroma/query")
async def chroma_query(request: ChromaQueryRequest) -> dict[str, Any]:
    """
    使用 chroma-mcp 查詢 ChromaDB

    直接透過 MCP 協議操作 ChromaDB。
    """
    try:
        manager = await init_mcp_manager()
        result = await manager.call_tool(
            "chroma-mcp",
            "chroma_query_documents",
            {
                "collection_name": request.collection_name,
                "query_texts": [request.query],
                "n_results": request.n_results,
            },
        )

        return result

    except Exception as e:
        logger.error("Chroma query failed", error=str(e))
        return {"success": False, "error": str(e)}


@router.get("/chroma/collections")
async def list_chroma_collections() -> dict[str, Any]:
    """
    列出所有 ChromaDB Collections
    """
    try:
        manager = await init_mcp_manager()
        result = await manager.call_tool(
            "chroma-mcp",
            "chroma_list_collections",
            {},
        )

        return result

    except Exception as e:
        logger.error("List chroma collections failed", error=str(e))
        return {"success": False, "error": str(e)}


@router.post("/faiss/search")
async def faiss_search(query: str, n_results: int = 5) -> dict[str, Any]:
    """
    使用 local-faiss-mcp 進行向量搜索

    本地 FAISS 向量搜索，支援 Re-ranking。
    """
    try:
        manager = await init_mcp_manager()
        result = await manager.call_tool(
            "local-faiss",
            "query_rag_store",
            {
                "query": query,
                "top_k": n_results,
            },
        )

        return result

    except Exception as e:
        logger.error("FAISS search failed", error=str(e))
        return {"success": False, "error": str(e)}


@router.post("/faiss/ingest")
async def faiss_ingest_document(file_path: str) -> dict[str, Any]:
    """
    使用 local-faiss-mcp 索引文件

    將文件加入本地 FAISS 向量索引。
    """
    try:
        manager = await init_mcp_manager()
        result = await manager.call_tool(
            "local-faiss",
            "ingest_document",
            {"path": file_path},
        )

        return result

    except Exception as e:
        logger.error("FAISS ingest failed", error=str(e))
        return {"success": False, "error": str(e)}
