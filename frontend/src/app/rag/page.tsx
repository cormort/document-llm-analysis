"use client";

import { useState, useEffect } from "react";
import { 
    MessageSquare, 
    Database, 
    FileText, 
    RefreshCw, 
    Trash2, 
    AlertTriangle, 
    Inbox, 
    Check, 
    Settings, 
    Zap,
    CheckCircle2,
    Loader2
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatInterface } from "@/components/chat/chat-interface";
import { FileUploader } from "@/components/file-uploader";
import {
    deleteDocument,
    reindexDocument,
    reindexAllDocuments,
    ReindexAllResult,
} from "@/lib/api";
import { useChatStore } from "@/stores/chat-store";
import { useDocumentStore } from "@/stores/document-store";

type TabType = "chat" | "data";

export default function RAGPage() {
    // Global document store
    const { documents, loading, error, fetchDocuments } = useDocumentStore();
    
    const [activeTab, setActiveTab] = useState<TabType>("chat");
    const [reindexing, setReindexing] = useState<Set<string>>(new Set());
    const [reindexAllLoading, setReindexAllLoading] = useState(false);
    const [reindexAllResult, setReindexAllResult] = useState<ReindexAllResult | null>(null);
    const [reindexResults, setReindexResults] = useState<
        { name: string; success: boolean; tags?: string[] }[]
    >([]);
    
    // RAG Optimization Settings
    const [useHybrid, setUseHybrid] = useState(true);
    const [useQueryExpansion, setUseQueryExpansion] = useState(false);
    const [useCompression, setUseCompression] = useState(false);
    
    const { selectedDocuments, setSelectedDocuments, clearMessages } =
        useChatStore();

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    const toggleDocument = (collectionName: string) => {
        if (selectedDocuments.includes(collectionName)) {
            setSelectedDocuments(
                selectedDocuments.filter((d) => d !== collectionName)
            );
        } else {
            setSelectedDocuments([...selectedDocuments, collectionName]);
        }
    };

    const handleDelete = async (collectionName: string) => {
        if (!confirm("確定要刪除此文件索引嗎？")) return;
        try {
            await deleteDocument(collectionName);
            await fetchDocuments();
        } catch (err) {
            alert(err instanceof Error ? err.message : "刪除失敗");
        }
    };

    const handleReindex = async (collectionName: string) => {
        setReindexing((prev) => new Set([...prev, collectionName]));
        try {
            const result = await reindexDocument(collectionName);
            const doc = documents.find(
                (d) => d.collection_name === collectionName
            );
            setReindexResults((prev) => [
                ...prev,
                {
                    name: doc?.file_name || collectionName,
                    success: result.success,
                    tags: result.extracted_tags,
                },
            ]);
            if (result.success) {
                await fetchDocuments();
            }
        } catch {
            setReindexResults((prev) => [
                ...prev,
                {
                    name: collectionName,
                    success: false,
                },
            ]);
        } finally {
            setReindexing((prev) => {
                const next = new Set(prev);
                next.delete(collectionName);
                return next;
            });
        }
    };

    const handleReindexAll = async () => {
        setReindexResults([]);
        for (const doc of documents) {
            await handleReindex(doc.collection_name);
        }
    };

    // 🆕 Quick embedding-only reindex (for model switching)
    const handleQuickReindexAll = async () => {
        if (!confirm("確定要重建所有文件的向量嗎？\\n\\n這將使用新的 Embedding 模型重新計算所有向量，但不會重新讀取原始檔案。")) return;
        
        setReindexAllLoading(true);
        setReindexAllResult(null);
        
        try {
            const result = await reindexAllDocuments();
            setReindexAllResult(result);
            if (result.success) {
                await fetchDocuments();
            }
        } catch (err) {
            setReindexAllResult({
                success: false,
                error: err instanceof Error ? err.message : "重建失敗"
            });
        } finally {
            setReindexAllLoading(false);
        }
    };

    return (
        <div className="flex-1 flex flex-col bg-slate-50/50">
            <Header
                title="RAG 智能問答"
                subtitle="基於文件內容的精確問答系統"
            />

            {/* Tab Navigation */}
            <div className="px-8 pt-6">
                <div className="flex gap-1 border-b border-slate-200">
                    <button
                        onClick={() => setActiveTab("chat")}
                        className={`px-4 py-3 text-sm font-medium transition-all flex items-center gap-2 border-b-2 ${
                            activeTab === "chat"
                                ? "text-blue-600 border-blue-600 bg-blue-50/50"
                                : "text-slate-500 hover:text-slate-700 border-transparent hover:bg-slate-50"
                        }`}
                    >
                        <MessageSquare size={16} />
                        智能問答
                    </button>
                    <button
                        onClick={() => setActiveTab("data")}
                        className={`px-4 py-3 text-sm font-medium transition-all flex items-center gap-2 border-b-2 ${
                            activeTab === "data"
                                ? "text-blue-600 border-blue-600 bg-blue-50/50"
                                : "text-slate-500 hover:text-slate-700 border-transparent hover:bg-slate-50"
                        }`}
                    >
                        <Database size={16} />
                        資料中心
                    </button>
                </div>
            </div>

            {/* Tab Content */}
            {activeTab === "chat" ? (
                <div className="flex-1 flex p-6 gap-6 h-[calc(100vh-140px)]">
                    {/* Document Selector */}
                    <Card className="w-80 flex flex-col h-full border-slate-200/60 shadow-lg bg-white/70 backdrop-blur-sm">
                        <div className="p-4 border-b border-slate-100 flex items-center gap-2">
                             <FileText className="text-slate-400" size={18} />
                             <div>
                                <h2 className="font-semibold text-slate-700 text-sm">
                                    選擇文件
                                </h2>
                                <p className="text-[10px] text-slate-400">
                                    選擇要查詢的文件範圍
                                </p>
                             </div>
                        </div>

                        <div className="p-4 border-b border-slate-100 bg-slate-50/50">
                            <FileUploader onUploadComplete={fetchDocuments} />
                        </div>

                        <ScrollArea className="flex-1 p-3">
                            {loading ? (
                                <div className="space-y-3">
                                    {[1, 2, 3].map((i) => (
                                        <div key={i} className="space-y-2">
                                            <Skeleton className="h-8 w-full rounded-lg" />
                                            <Skeleton className="h-3 w-1/2" />
                                        </div>
                                    ))}
                                </div>
                            ) : error ? (
                                <div className="text-center py-8">
                                    <AlertTriangle className="mx-auto text-red-400 mb-2" size={32} />
                                    <p className="text-xs text-red-500 mb-2">
                                        {error}
                                    </p>
                                    <button
                                        onClick={() => window.location.reload()}
                                        className="text-xs text-blue-600 hover:underline flex items-center justify-center gap-1 mx-auto"
                                    >
                                        <RefreshCw size={10} /> 重試
                                    </button>
                                </div>
                            ) : documents.length === 0 ? (
                                <div className="text-center py-12">
                                    <Inbox className="mx-auto text-slate-300 mb-3" size={40} />
                                    <p className="text-sm text-slate-500 font-medium">
                                        尚無已索引的文件
                                    </p>
                                </div>
                            ) : (
                                <div className="space-y-1.5">
                                    {documents.map((doc) => {
                                        const isSelected =
                                            selectedDocuments.includes(
                                                doc.collection_name
                                            );
                                        return (
                                            <button
                                                key={doc.collection_name}
                                                onClick={() =>
                                                    toggleDocument(
                                                        doc.collection_name
                                                    )
                                                }
                                                className={`w-full text-left p-2.5 rounded-lg border transition-all flex items-start gap-3 group ${
                                                    isSelected
                                                        ? "bg-blue-50 border-blue-200 shadow-sm"
                                                        : "bg-white border-transparent hover:bg-slate-50"
                                                }`}
                                            >
                                                <div className={`mt-0.5 transition-colors ${isSelected ? "text-blue-600" : "text-slate-300 group-hover:text-slate-400"}`}>
                                                    {isSelected ? <CheckCircle2 size={18} /> : <FileText size={18} />}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p className={`font-medium text-sm truncate ${isSelected ? "text-blue-700" : "text-slate-600"}`}>
                                                        {doc.file_name}
                                                    </p>
                                                    <p className="text-[10px] text-slate-400 mt-0.5 flex items-center gap-1">
                                                        <span className="bg-slate-100 px-1.5 py-0.5 rounded text-slate-500 font-mono">
                                                            {doc.chunk_count}
                                                        </span> 
                                                        chunks
                                                    </p>
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </ScrollArea>

                        {selectedDocuments.length > 0 && (
                            <div className="p-3 border-t border-slate-200 bg-slate-50/80 backdrop-blur-sm">
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-slate-600 font-medium ml-1">
                                        已選 {selectedDocuments.length} 個文件
                                    </span>
                                    <button
                                        onClick={() => {
                                            setSelectedDocuments([]);
                                            clearMessages();
                                        }}
                                        className="text-slate-400 hover:text-red-500 transition-colors p-1"
                                        title="清除選擇"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>
                        )}
                        
                        {/* Optimization Settings */}
                        <div className="p-4 border-t border-slate-200 bg-blue-50/50">
                            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                                <Settings size={10} /> 搜尋優化
                            </h3>
                            <div className="space-y-2.5">
                                <label className="flex items-center gap-2 text-xs cursor-pointer group">
                                    <input
                                        type="checkbox"
                                        checked={useHybrid}
                                        onChange={(e) => setUseHybrid(e.target.checked)}
                                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    <span className="text-slate-600 group-hover:text-slate-900 transition-colors">混合搜尋 (Vector + Keyword)</span>
                                </label>
                                <label className="flex items-center gap-2 text-xs cursor-pointer group">
                                    <input
                                        type="checkbox"
                                        checked={useQueryExpansion}
                                        onChange={(e) => setUseQueryExpansion(e.target.checked)}
                                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    <span className="text-slate-600 group-hover:text-slate-900 transition-colors">查詢擴展 (AI 改寫)</span>
                                </label>
                                <label className="flex items-center gap-2 text-xs cursor-pointer group">
                                    <input
                                        type="checkbox"
                                        checked={useCompression}
                                        onChange={(e) => setUseCompression(e.target.checked)}
                                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    <span className="text-slate-600 group-hover:text-slate-900 transition-colors">Context 壓縮 (Smart)</span>
                                </label>
                            </div>
                        </div>
                    </Card>

                    {/* Chat Area */}
                    <div className="flex-1 min-w-0">
                        <ChatInterface 
                            selectedDocuments={selectedDocuments}
                        />
                    </div>
                </div>
            ) : (
                <div className="flex-1 p-8">
                    <Card className="h-full flex flex-col max-w-5xl mx-auto border-slate-200/60 shadow-xl bg-white/80 backdrop-blur-sm">
                        <div className="p-6 border-b border-slate-100">
                            <h2 className="font-bold text-xl text-slate-800 flex items-center gap-2">
                                <Database className="text-blue-500" />
                                文件庫管理中心
                            </h2>
                            <p className="text-sm text-slate-500 mt-1 pl-8">
                                管理已索引的文件，或使用 LangExtract 重建索引以獲取更佳的結構化數據
                            </p>
                        </div>

                        {/* Upload Section */}
                        <div className="p-6 border-b border-slate-100 bg-slate-50/50">
                            <FileUploader onUploadComplete={fetchDocuments} />
                        </div>

                        {/* Batch Reindex Section */}
                        <div className="p-6 border-b border-slate-100">
                            <div className="flex items-center justify-between mb-4">
                                <div>
                                    <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                                        <RefreshCw size={18} className="text-indigo-500" />
                                        批次重建索引 (LangExtract 增強)
                                    </h3>
                                    <p className="text-xs text-slate-500 mt-1 pl-6">
                                        重建後可獲得自動標籤和更精確的實體識別
                                    </p>
                                </div>
                                <button
                                    onClick={handleReindexAll}
                                    disabled={
                                        documents.length === 0 ||
                                        reindexing.size > 0
                                    }
                                    className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg transition-all flex items-center gap-2"
                                >
                                    {reindexing.size > 0 ? (
                                        <>
                                            <RefreshCw className="animate-spin" size={16} />
                                            重建中 ({reindexing.size}/{documents.length})
                                        </>
                                    ) : (
                                        <>
                                            <RefreshCw size={16} />
                                            重建全部
                                        </>
                                    )}
                                </button>
                            </div>

                            {/* Reindex Results */}
                            {reindexResults.length > 0 && (
                                <div className="mt-4 p-4 bg-slate-900 rounded-xl max-h-40 overflow-y-auto custom-scrollbar">
                                    {reindexResults.map((r, i) => (
                                        <div
                                            key={i}
                                            className="text-xs text-slate-300 py-1.5 flex items-center gap-2 border-b border-slate-800 last:border-0"
                                        >
                                            {r.success ? <Check size={14} className="text-green-400" /> : <AlertTriangle size={14} className="text-red-400" />} 
                                            <span className="font-mono text-slate-400">{r.name}</span>
                                            {r.tags && r.tags.length > 0 && (
                                                <span className="text-blue-400 ml-auto bg-blue-500/10 px-2 py-0.5 rounded-full text-[10px]">
                                                    {r.tags.join(", ")}
                                                </span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                            
                            {/* Quick Embedding Reindex (for model switching) */}
                            <div className="mt-6 p-5 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl border border-purple-100/50">
                                <div className="flex items-center justify-between mb-2">
                                    <div>
                                        <h3 className="font-semibold text-purple-700 flex items-center gap-2">
                                            <Zap size={18} className="text-purple-600" />
                                            快速向量重建
                                            <span className="text-[10px] bg-purple-200 text-purple-700 px-2 py-0.5 rounded-full font-bold tracking-wide">切換模型專用</span>
                                        </h3>
                                        <p className="text-xs text-purple-600/70 mt-1 pl-7">
                                            不需原始檔案，只重建 Embeddings 向量 (速度約快 10 倍)
                                        </p>
                                    </div>
                                    <button
                                        onClick={handleQuickReindexAll}
                                        disabled={documents.length === 0 || reindexAllLoading}
                                        className="px-5 py-2.5 bg-purple-600 text-white text-sm font-medium rounded-xl hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-md hover:shadow-lg transition-all"
                                    >
                                        {reindexAllLoading ? (
                                            <>
                                                <Loader2 className="animate-spin" size={16} />
                                                重建中...
                                            </>
                                        ) : (
                                            <>
                                                <Zap size={16} />
                                                一鍵重建
                                            </>
                                        )}
                                    </button>
                                </div>
                                
                                {/* Quick Reindex Result */}
                                {reindexAllResult && (
                                    <div className={`mt-4 p-4 rounded-xl text-sm border ${
                                        reindexAllResult.success 
                                            ? 'bg-green-50 border-green-200 text-green-800'
                                            : 'bg-red-50 border-red-200 text-red-800'
                                    }`}>
                                        {reindexAllResult.success ? (
                                            <div>
                                                <p className="font-bold flex items-center gap-2">
                                                    <CheckCircle2 size={18} />
                                                    成功重建 {reindexAllResult.reindexed}/{reindexAllResult.total} 個文件
                                                </p>
                                                {reindexAllResult.details && (
                                                    <div className="mt-3 text-xs space-y-1 max-h-32 overflow-y-auto custom-scrollbar bg-white/50 p-2 rounded-lg">
                                                        {reindexAllResult.details.map((d, i) => (
                                                            <div key={i} className="flex items-center gap-2 py-0.5">
                                                                {d.status === 'success' && <><Check size={12} className="text-green-600" /> <span className="flex-1">{d.file_name || d.collection}</span> <span className="text-slate-400">{d.chunks} chunks</span></>}
                                                                {d.status === 'skipped' && <><span className="text-slate-400">⏭️</span> <span className="text-slate-400">{d.collection}: 跳過</span></>}
                                                                {d.status === 'error' && <><AlertTriangle size={12} className="text-red-500" /> <span className="text-red-600">{d.collection}: {d.error}</span></>}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <p className="flex items-center gap-2 font-bold">
                                                <AlertTriangle size={18} />
                                                重建失敗: {reindexAllResult.error}
                                            </p>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Document List */}
                        <ScrollArea className="flex-1 p-6">
                            {loading ? (
                                <div className="space-y-4">
                                    {[1, 2, 3].map((i) => (
                                        <Skeleton
                                            key={i}
                                            className="h-20 w-full rounded-xl"
                                        />
                                    ))}
                                </div>
                            ) : documents.length === 0 ? (
                                <div className="text-center py-16">
                                    <div className="w-24 h-24 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
                                        <Inbox className="text-slate-300" size={48} />
                                    </div>
                                    <p className="text-slate-500 font-medium">
                                        文件庫目前是空的
                                    </p>
                                    <p className="text-xs text-slate-400 mt-2">
                                        請點擊上方的上傳區域開始建立您的知識庫
                                    </p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {documents.map((doc) => (
                                        <div
                                            key={doc.collection_name}
                                            className="flex items-center justify-between p-4 bg-white rounded-xl border border-slate-200 hover:border-blue-200 hover:shadow-md transition-all group"
                                        >
                                            <div className="flex items-center gap-4">
                                                <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                                                    <FileText size={24} />
                                                </div>
                                                <div>
                                                    <p className="font-semibold text-slate-800 text-base">
                                                        {doc.file_name}
                                                    </p>
                                                    <p className="text-xs text-slate-500 mt-1 flex items-center gap-2">
                                                        <span className="bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                                                            {doc.chunk_count} chunks
                                                        </span>
                                                        <span>
                                                            · 索引於 {doc.indexed_at?.slice(0, 10) || "未知"}
                                                        </span>
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() =>
                                                        handleReindex(
                                                            doc.collection_name
                                                        )
                                                    }
                                                    disabled={reindexing.has(
                                                        doc.collection_name
                                                    )}
                                                    className="p-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors disabled:opacity-50"
                                                    title="重建此文件索引"
                                                >
                                                    <RefreshCw size={18} className={reindexing.has(doc.collection_name) ? "animate-spin" : ""} />
                                                </button>
                                                <button
                                                    onClick={() =>
                                                        handleDelete(
                                                            doc.collection_name
                                                        )
                                                    }
                                                    className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                                    title="刪除此文件"
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </ScrollArea>
                    </Card>
                </div>
            )}
        </div>
    );
}
