"""
MCP Client Manager - 統一管理多個 MCP Server 連接。

提供動態註冊、連接管理、工具發現與調用功能。
支援 STDIO 和 HTTP/SSE 傳輸模式。
"""

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()

# MCP 配置檔案路徑
MCP_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "mcp_config.json",
)


class TransportType(Enum):
    """MCP 傳輸類型"""

    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


@dataclass
class MCPServerConfig:
    """MCP Server 配置"""

    name: str
    description: str
    command: str
    args: list[str]
    env: dict[str, str] | None = None
    enabled: bool = True
    transport: TransportType = TransportType.STDIO


@dataclass
class MCPConnection:
    """MCP Server 連接狀態"""

    config: MCPServerConfig
    process: subprocess.Popen | None = None
    connected: bool = False
    tools: list[dict] = None

    def __post_init__(self) -> None:
        if self.tools is None:
            self.tools = []


class MCPClientManager:
    """
    MCP Client Manager - 管理多個 MCP Server 連接

    用法:
        manager = MCPClientManager()
        await manager.initialize()
        result = await manager.call_tool("markitdown", "convert_to_markdown", {"uri": "file:///path/to/doc.pdf"})
    """

    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = config_path or MCP_CONFIG_PATH
        self.servers: dict[str, MCPServerConfig] = {}
        self.connections: dict[str, MCPConnection] = {}
        self._initialized = False

    def load_config(self) -> bool:
        """載入 MCP 配置檔案"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning("MCP config file not found", path=self.config_path)
                return False

            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)

            mcp_servers = config.get("mcpServers", {})
            for name, server_config in mcp_servers.items():
                self.servers[name] = MCPServerConfig(
                    name=name,
                    description=server_config.get("description", ""),
                    command=server_config.get("command", ""),
                    args=server_config.get("args", []),
                    env=server_config.get("env"),
                    enabled=server_config.get("enabled", True),
                )

            logger.info(
                "MCP config loaded",
                servers=len(self.servers),
                enabled=sum(1 for s in self.servers.values() if s.enabled),
            )
            return True

        except Exception as e:
            logger.error("Failed to load MCP config", error=str(e))
            return False

    async def initialize(self) -> None:
        """初始化所有已啟用的 MCP Server 連接"""
        if self._initialized:
            return

        self.load_config()

        for name, config in self.servers.items():
            if config.enabled:
                try:
                    await self._connect_server(name, config)
                except Exception as e:
                    logger.warning(
                        "Failed to connect MCP server",
                        server=name,
                        error=str(e),
                    )

        self._initialized = True

    async def _connect_server(
        self, name: str, config: MCPServerConfig
    ) -> MCPConnection:
        """連接單個 MCP Server"""
        logger.info("Connecting to MCP server", server=name, command=config.command)

        connection = MCPConnection(config=config)

        # 檢查命令是否可用
        if not self._check_command_available(config.command):
            logger.warning(
                "MCP server command not found",
                server=name,
                command=config.command,
            )
            self.connections[name] = connection
            return connection

        # 對於 STDIO 傳輸，我們不在這裡啟動 process
        # 而是在調用工具時按需啟動
        connection.connected = True
        self.connections[name] = connection

        logger.info("MCP server ready", server=name)
        return connection

    def _check_command_available(self, command: str) -> bool:
        """檢查命令是否可用"""
        import shutil

        # 特殊處理 npx
        if command == "npx":
            return shutil.which("npx") is not None

        # 特殊處理 uvx
        if command == "uvx":
            return shutil.which("uvx") is not None

        # 檢查 Python 模組型命令
        if "-" in command:
            # 嘗試作為模組檢查
            try:
                result = subprocess.run(
                    ["python", "-c", f"import {command.replace('-', '_')}"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return shutil.which(command) is not None

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """
        調用 MCP Server 工具

        Args:
            server_name: MCP Server 名稱
            tool_name: 工具名稱
            arguments: 工具參數
            timeout: 超時時間（秒）

        Returns:
            工具執行結果
        """
        if server_name not in self.connections:
            return {"success": False, "error": f"Server '{server_name}' not found"}

        connection = self.connections[server_name]
        if not connection.connected:
            return {
                "success": False,
                "error": f"Server '{server_name}' not connected",
            }

        config = connection.config

        try:
            # 構建 MCP 請求
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {},
                },
            }

            # 準備環境變數
            env = os.environ.copy()
            if config.env:
                env.update(config.env)

            # 構建完整命令
            cmd = [config.command, *config.args]

            # 執行 STDIO 通訊
            result = await self._stdio_call(cmd, request, env, timeout)
            return result

        except TimeoutError:
            return {"success": False, "error": f"Tool call timed out after {timeout}s"}
        except Exception as e:
            logger.error(
                "Tool call failed",
                server=server_name,
                tool=tool_name,
                error=str(e),
            )
            return {"success": False, "error": str(e)}

    async def _stdio_call(
        self,
        cmd: list[str],
        request: dict,
        env: dict,
        timeout: float,
    ) -> dict[str, Any]:
        """透過 STDIO 調用 MCP Server"""

        async def run_process():
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # 發送初始化請求
            init_request = {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "document-llm-analysis", "version": "1.0.0"},
                },
            }

            stdin_data = json.dumps(init_request) + "\n" + json.dumps(request) + "\n"
            stdout_data, stderr_data = await process.communicate(
                stdin_data.encode("utf-8")
            )

            if process.returncode != 0:
                error_msg = stderr_data.decode("utf-8", errors="replace")
                return {"success": False, "error": error_msg}

            # 解析回應
            lines = stdout_data.decode("utf-8").strip().split("\n")
            for line in reversed(lines):
                if line.strip():
                    try:
                        response = json.loads(line)
                        if "result" in response:
                            return {"success": True, "data": response["result"]}
                        elif "error" in response:
                            return {"success": False, "error": response["error"]}
                    except json.JSONDecodeError:
                        continue

            return {"success": False, "error": "No valid response from server"}

        return await asyncio.wait_for(run_process(), timeout=timeout)

    def get_available_servers(self) -> list[dict]:
        """取得所有可用的 MCP Server 列表"""
        result = []
        for name, config in self.servers.items():
            conn = self.connections.get(name)
            result.append(
                {
                    "name": name,
                    "description": config.description,
                    "enabled": config.enabled,
                    "connected": conn.connected if conn else False,
                    "command": config.command,
                }
            )
        return result

    async def list_tools(self, server_name: str) -> list[dict]:
        """列出指定 MCP Server 的所有工具"""
        if server_name not in self.connections:
            return []

        connection = self.connections[server_name]
        if not connection.connected:
            return []

        try:
            result = await self.call_tool(server_name, "", {"list": True})
            if result.get("success") and "tools" in result.get("data", {}):
                return result["data"]["tools"]
        except Exception as e:
            logger.warning("Failed to list tools", server=server_name, error=str(e))

        return connection.tools

    async def shutdown(self) -> None:
        """關閉所有 MCP Server 連接"""
        for name, conn in self.connections.items():
            if conn.process and conn.process.poll() is None:
                logger.info("Terminating MCP server", server=name)
                conn.process.terminate()
                try:
                    conn.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    conn.process.kill()
            conn.connected = False

        self.connections.clear()
        self._initialized = False
        logger.info("MCP Client Manager shutdown complete")


# ========== 便捷工具函數 ==========


async def convert_to_markdown(file_path: str) -> dict[str, Any]:
    """
    使用 markitdown-mcp 將檔案轉換為 Markdown

    Args:
        file_path: 檔案路徑（本地路徑或 URL）

    Returns:
        {"success": bool, "markdown": str, "error": str?}
    """
    manager = MCPClientManager()
    await manager.initialize()

    # 轉換為 file:// URI
    if os.path.exists(file_path):
        uri = f"file://{os.path.abspath(file_path)}"
    elif file_path.startswith(("http://", "https://", "file://", "data:")):
        uri = file_path
    else:
        return {"success": False, "error": f"Invalid file path: {file_path}"}

    result = await manager.call_tool("markitdown", "convert_to_markdown", {"uri": uri})

    if result.get("success"):
        content = result.get("data", {})
        if isinstance(content, dict):
            return {"success": True, "markdown": content.get("content", "")}
        return {"success": True, "markdown": str(content)}

    return result


async def web_search(query: str, engine: str = "duckduckgo") -> dict[str, Any]:
    """
    使用 open-websearch 進行網路搜索

    Args:
        query: 搜索查詢
        engine: 搜索引擎 (duckduckgo, bing, brave)

    Returns:
        {"success": bool, "results": list, "error": str?}
    """
    manager = MCPClientManager()
    await manager.initialize()

    result = await manager.call_tool(
        "open-websearch",
        "search",
        {"query": query, "engine": engine, "limit": 10},
    )

    return result


# 全域單例
_mcp_manager: MCPClientManager | None = None


def get_mcp_manager() -> MCPClientManager:
    """取得 MCP Client Manager 單例"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPClientManager()
    return _mcp_manager


async def init_mcp_manager() -> MCPClientManager:
    """初始化並取得 MCP Client Manager"""
    manager = get_mcp_manager()
    await manager.initialize()
    return manager


# ========== CLI 測試入口 ==========

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Client Manager")
    parser.add_argument("--test", action="store_true", help="Test MCP connections")
    parser.add_argument("--list", action="store_true", help="List available servers")
    args = parser.parse_args()

    async def main() -> None:
        manager = MCPClientManager()
        await manager.initialize()

        if args.list:
            servers = manager.get_available_servers()
            print("\n📡 Available MCP Servers:")
            for s in servers:
                status = "✅" if s["connected"] else "❌"
                enabled = "🟢" if s["enabled"] else "⚪"
                print(f"  {status} {enabled} {s['name']}: {s['description']}")

        if args.test:
            print("\n🧪 Testing MCP Connections...")

            # Test markitdown
            print("\n[markitdown] Testing convert_to_markdown...")
            result = await manager.call_tool(
                "markitdown",
                "convert_to_markdown",
                {"uri": "https://example.com"},
            )
            print(f"  Result: {result.get('success', False)}")

            # Test web search
            print("\n[open-websearch] Testing search...")
            result = await manager.call_tool(
                "open-websearch",
                "search",
                {"query": "MCP Model Context Protocol", "limit": 3},
            )
            print(f"  Result: {result.get('success', False)}")

        await manager.shutdown()

    asyncio.run(main())
