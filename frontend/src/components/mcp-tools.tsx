"use client";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// API Base URL
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

interface MCPServer {
    name: string;
    description: string;
    enabled: boolean;
    connected: boolean;
    command: string;
}

interface SearchResult {
    title: string;
    url: string;
    snippet: string;
}

export function MCPToolsPanel({ className }: { className?: string }) {
    const [servers, setServers] = useState<MCPServer[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<"servers" | "search" | "convert">("servers");

    // Web Search States
    const [searchQuery, setSearchQuery] = useState("");
    const [searchEngine, setSearchEngine] = useState("duckduckgo");
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);

    // Markdown Convert States
    const [convertUrl, setConvertUrl] = useState("");
    const [markdownResult, setMarkdownResult] = useState("");
    const [isConverting, setIsConverting] = useState(false);

    // Fetch available MCP servers
    const fetchServers = async () => {
        setIsLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/mcp/servers`);
            const data = await res.json();
            if (data.success) {
                setServers(data.servers || []);
            }
        } catch (error) {
            console.error("Failed to fetch MCP servers:", error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchServers();
    }, []);

    // Web Search
    const handleWebSearch = async () => {
        if (!searchQuery.trim()) return;
        setIsSearching(true);
        setSearchResults([]);

        try {
            const res = await fetch(`${API_BASE}/api/mcp/web-search`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: searchQuery,
                    engine: searchEngine,
                    limit: 10,
                }),
            });
            const data = await res.json();
            if (data.success && data.results) {
                setSearchResults(data.results);
            }
        } catch (error) {
            console.error("Search failed:", error);
        } finally {
            setIsSearching(false);
        }
    };

    // Convert to Markdown
    const handleConvert = async () => {
        if (!convertUrl.trim()) return;
        setIsConverting(true);
        setMarkdownResult("");

        try {
            const res = await fetch(`${API_BASE}/api/mcp/convert-to-markdown`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ uri: convertUrl }),
            });
            const data = await res.json();
            if (data.success && data.markdown) {
                setMarkdownResult(data.markdown);
            } else {
                setMarkdownResult(`Error: ${data.error || "Conversion failed"}`);
            }
        } catch (error) {
            console.error("Convert failed:", error);
            setMarkdownResult("Error: Conversion failed");
        } finally {
            setIsConverting(false);
        }
    };

    return (
        <Card className={`${className || ""}`}>
            <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                    <span className="text-lg">🔌</span>
                    MCP 工具
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Tabs */}
                <div className="flex gap-1 bg-slate-100 rounded-lg p-1">
                    {[
                        { key: "servers", label: "📡 伺服器" },
                        { key: "search", label: "🔍 網路搜索" },
                        { key: "convert", label: "📄 轉 Markdown" },
                    ].map((tab) => (
                        <button
                            key={tab.key}
                            onClick={() => setActiveTab(tab.key as typeof activeTab)}
                            className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                                activeTab === tab.key
                                    ? "bg-white text-slate-900 shadow-sm"
                                    : "text-slate-600 hover:text-slate-900"
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Servers Tab */}
                {activeTab === "servers" && (
                    <div className="space-y-2">
                        {isLoading ? (
                            <p className="text-sm text-slate-500 text-center py-4">載入中...</p>
                        ) : servers.length === 0 ? (
                            <p className="text-sm text-slate-500 text-center py-4">無可用的 MCP Server</p>
                        ) : (
                            servers.map((server) => (
                                <div
                                    key={server.name}
                                    className="flex items-center justify-between p-2 bg-slate-50 rounded-lg"
                                >
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`w-2 h-2 rounded-full ${
                                                server.connected
                                                    ? "bg-green-500"
                                                    : server.enabled
                                                    ? "bg-yellow-500"
                                                    : "bg-slate-300"
                                            }`}
                                        />
                                        <div>
                                            <p className="text-xs font-medium text-slate-700">{server.name}</p>
                                            <p className="text-[10px] text-slate-500 truncate max-w-[180px]">
                                                {server.description}
                                            </p>
                                        </div>
                                    </div>
                                    <span className="text-[10px] text-slate-400">{server.command}</span>
                                </div>
                            ))
                        )}
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={fetchServers}
                            disabled={isLoading}
                            className="w-full mt-2"
                        >
                            重新整理
                        </Button>
                    </div>
                )}

                {/* Web Search Tab */}
                {activeTab === "search" && (
                    <div className="space-y-3">
                        <div className="flex gap-2">
                            <Input
                                type="text"
                                placeholder="輸入搜索查詢..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                onKeyDown={(e) => e.key === "Enter" && handleWebSearch()}
                                className="text-sm"
                            />
                            <select
                                value={searchEngine}
                                onChange={(e) => setSearchEngine(e.target.value)}
                                className="text-xs px-2 py-1 border rounded-md bg-white"
                            >
                                <option value="duckduckgo">DuckDuckGo</option>
                                <option value="bing">Bing</option>
                                <option value="brave">Brave</option>
                            </select>
                        </div>
                        <Button
                            onClick={handleWebSearch}
                            disabled={isSearching || !searchQuery.trim()}
                            size="sm"
                            className="w-full"
                        >
                            {isSearching ? "搜索中..." : "🔍 搜索"}
                        </Button>

                        {searchResults.length > 0 && (
                            <div className="space-y-2 max-h-60 overflow-y-auto">
                                {searchResults.map((result, idx) => (
                                    <a
                                        key={idx}
                                        href={result.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block p-2 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                                    >
                                        <p className="text-xs font-medium text-blue-600 truncate">{result.title}</p>
                                        <p className="text-[10px] text-slate-500 line-clamp-2">{result.snippet}</p>
                                    </a>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Convert to Markdown Tab */}
                {activeTab === "convert" && (
                    <div className="space-y-3">
                        <Input
                            type="text"
                            placeholder="輸入 URL 或 file:// 路徑..."
                            value={convertUrl}
                            onChange={(e) => setConvertUrl(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleConvert()}
                            className="text-sm"
                        />
                        <Button
                            onClick={handleConvert}
                            disabled={isConverting || !convertUrl.trim()}
                            size="sm"
                            className="w-full"
                        >
                            {isConverting ? "轉換中..." : "📄 轉換為 Markdown"}
                        </Button>

                        {markdownResult && (
                            <div className="bg-slate-50 rounded-lg p-2 max-h-60 overflow-y-auto">
                                <pre className="text-[10px] text-slate-700 whitespace-pre-wrap font-mono">
                                    {markdownResult.slice(0, 2000)}
                                    {markdownResult.length > 2000 && "\n... (truncated)"}
                                </pre>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
