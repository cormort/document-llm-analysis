"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { generatePandasQuery, executeQuery, interpretQuery, QueryExecuteResponse, getDiagnostic, DiagnosticResponse } from "@/lib/api";
import { useSettingsStore } from "@/stores/settings-store";
import { useDocumentStore } from "@/stores/document-store";
import { 
    FileText, 
    BarChart3, 
    Search, 
    Code, 
    Bot, 
    Rocket, 
    AlertTriangle,
    CheckCircle2,
    XCircle,
    Database,
    Sparkles
} from "lucide-react";

export default function QueryPage() {
    const { provider, model_name, local_url, api_key } = useSettingsStore();
    
    // Global document store
    const { documents: allDocs, fetchDocuments } = useDocumentStore();
    const documents = allDocs.filter(d => d.file_name.match(/\.(csv|xlsx|xls)$/i));
    
    const [processing, setProcessing] = useState(false);

    const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
    const [question, setQuestion] = useState("");
    const [generatedCode, setGeneratedCode] = useState<string | null>(null);
    const [queryResult, setQueryResult] = useState<QueryExecuteResponse | null>(null);
    const [interpretation, setInterpretation] = useState<string | null>(null);
    const [metadata, setMetadata] = useState<DiagnosticResponse | null>(null);

    useEffect(() => {
        async function fetchMetadata() {
            if (!selectedDoc) {
                setMetadata(null);
                return;
            }
            try {
                const doc = documents.find(d => d.collection_name === selectedDoc);
                if (doc) {
                    const res = await getDiagnostic({
                        file_path: doc.file_name,
                        config: { provider, model_name, local_url, api_key: api_key || undefined }
                    });
                    setMetadata(res);
                }
            } catch (err) {
                console.error("Failed to fetch metadata", err);
            }
        }
        fetchMetadata();
    }, [selectedDoc, api_key, documents, local_url, model_name, provider]);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    const handleQuery = async () => {
        if (!selectedDoc || !question.trim()) return;
        setProcessing(true);
        setQueryResult(null);
        setInterpretation(null);
        setGeneratedCode(null);

        const config = {
            provider,
            model_name,
            local_url,
            api_key: api_key || undefined
        };

        try {
            // 1. Generate code
            const doc = documents.find(d => d.collection_name === selectedDoc);
            const { pandas_code } = await generatePandasQuery(doc!.file_name, question, config);
            setGeneratedCode(pandas_code);

            // 2. Execute code
            const res = await executeQuery({
                file_path: doc!.file_name,
                pandas_code
            });
            setQueryResult(res);

            // 3. Interpret if successful
            if (res.success && res.data) {
                const { interpretation: intro } = await interpretQuery(
                    question,
                    res.summary || "",
                    res.data.slice(0, 5),
                    config
                );
                setInterpretation(intro);
            }
        } catch (err) {
            console.error("Query failed", err);
        } finally {
            setProcessing(false);
        }
    };

    return (
        <div className="flex-1 flex flex-col bg-slate-50">
            <Header
                title="💡 自然語言數據查詢"
                subtitle="使用白話文查詢 Excel/CSV，AI 自動編寫 Pandas 腳本"
            />

            <div className="flex-1 flex p-6 gap-6 overflow-hidden">
                {/* Left: Settings */}
                <div className="w-80 flex flex-col gap-6">
                    <Card className="p-4 flex flex-col flex-1">
                        <h3 className="font-semibold text-slate-700 mb-3 flex items-center gap-2 text-sm">
                            <FileText size={16} className="text-blue-500"/> 1. 選擇數據源
                        </h3>
                        <ScrollArea className="flex-1">
                            <div className="space-y-2">
                                {documents.filter(d => d.file_name.match(/\.(csv|xlsx|xls)$/i)).map((doc) => (
                                    <button
                                        key={doc.collection_name}
                                        onClick={() => setSelectedDoc(doc.collection_name)}
                                        className={`w-full text-left p-3 rounded-lg border transition-all ${selectedDoc === doc.collection_name
                                            ? "bg-blue-50 border-blue-200 shadow-sm"
                                            : "bg-white border-slate-100 hover:bg-slate-50"
                                            }`}
                                    >
                                        <div className="flex items-center gap-2 mb-1">
                                            {selectedDoc === doc.collection_name ? <CheckCircle2 size={14} className="text-blue-600"/> : <Database size={14} className="text-slate-400"/>}
                                            <p className={`font-medium text-xs truncate flex-1 ${selectedDoc === doc.collection_name ? "text-blue-700" : "text-slate-700"}`}>
                                                {doc.file_name}
                                            </p>
                                        </div>
                                        <p className="text-[10px] text-slate-400 pl-6">
                                            {doc.chunk_count} chunks
                                        </p>
                                    </button>
                                ))}
                            </div>
                        </ScrollArea>
                    </Card>

                    {/* Data Dictionary Card */}
                    {metadata && (
                        <Card className="p-4 flex flex-col flex-1 overflow-hidden animate-in slide-in-from-left-2 duration-500">
                            <div className="mb-3">
                                <h3 className="font-semibold text-slate-700 flex items-center gap-2 text-sm">
                                    <BarChart3 size={16} className="text-purple-500"/> 資料集概覽
                                </h3>
                                <div className="flex gap-2 mt-2 text-xs text-slate-500">
                                    <Badge variant="secondary">{metadata.quality_report.length} 個欄位</Badge>
                                    <Badge variant="outline">{String(metadata.summary_stats.count || (metadata.quality_report[0]?.unique_count) || "0")} 筆資料</Badge>
                                </div>
                            </div>

                            <ScrollArea className="flex-1 pr-3">
                                <div className="space-y-3">
                                    {metadata.quality_report.map((col) => (
                                        <div key={col.column} className="p-2 bg-slate-50 rounded border border-slate-100">
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-bold text-xs text-slate-700 truncate max-w-[120px]" title={col.column}>
                                                    {col.column}
                                                </span>
                                                <Badge variant="outline" className="text-[10px] scale-90">{col.dtype}</Badge>
                                            </div>
                                            <div className="text-[10px] text-slate-500">
                                                <span className="font-semibold">Samples: </span>
                                                {col.sample_values.slice(0, 2).map(String).join(", ")}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </ScrollArea>
                        </Card>
                    )}
                </div>

                {/* Right: Interactive Area */}
                <div className="flex-1 flex flex-col gap-6 overflow-hidden">
                    {/* Input Box */}
                    <Card className="p-6 bg-white shadow-sm">
                        <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
                             <Search size={18} className="text-blue-500"/> 2. 您想了解什麼？
                        </h3>
                        <div className="flex gap-4">
                            <Input
                                value={question}
                                onChange={(e) => setQuestion(e.target.value)}
                                placeholder="例如：列出 113 年底人口數大於 100 萬的城市..."
                                className="flex-1"
                                disabled={processing || !selectedDoc}
                                onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                            />
                            <Button
                                onClick={handleQuery}
                                disabled={processing || !selectedDoc || !question.trim()}
                                className="bg-blue-600 hover:bg-blue-700 px-8"
                            >
                                {processing ? (
                                    <>
                                        <Sparkles size={16} className="mr-2 animate-pulse" /> 分析中...
                                    </>
                                ) : (
                                    <>
                                        查詢數據
                                    </>
                                )}
                            </Button>
                        </div>
                        {!selectedDoc && (
                            <p className="text-xs text-amber-600 mt-2 flex items-center gap-1.5">
                                <AlertTriangle size={12} /> 請先在左側選擇一個 CSV 或 Excel 檔案
                            </p>
                        )}
                    </Card>

                    {/* Results Display */}
                    <div className="flex-1 overflow-y-auto space-y-6 pb-6">
                        {processing && (
                            <div className="space-y-4">
                                <Skeleton className="h-40 w-full" />
                                <Skeleton className="h-64 w-full" />
                            </div>
                        )}

                        {!processing && generatedCode && (
                            <Card className="p-4 border-slate-200 bg-slate-50/50">
                                <div className="flex items-center justify-between mb-3">
                                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                                        <Code size={14} className="text-blue-400"/> AI 生成的 Pandas 程式碼
                                    </span>
                                    <Badge variant="outline" className="text-[10px]">Python</Badge>
                                </div>
                                <pre className="text-xs bg-slate-900 text-blue-300 p-4 rounded-lg overflow-x-auto shadow-inner">
                                    <code>{generatedCode}</code>
                                </pre>
                            </Card>
                        )}

                        {!processing && queryResult && (
                            <>
                                <Card className="overflow-hidden border-slate-200 shadow-sm">
                                    <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                                        <h3 className="font-semibold text-slate-700 flex items-center gap-2">
                                            <BarChart3 size={18} className="text-emerald-500"/> 執行結果
                                        </h3>
                                        <span className="text-xs text-slate-500">{queryResult.summary}</span>
                                    </div>

                                    {queryResult.success ? (
                                        <div className="overflow-x-auto">
                                            <table className="min-w-full divide-y divide-slate-200">
                                                <thead className="bg-slate-50">
                                                    <tr>
                                                        {queryResult.data && queryResult.data.length > 0 && Object.keys(queryResult.data[0]).map((key) => (
                                                            <th key={key} className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                                                                {key}
                                                            </th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody className="bg-white divide-y divide-slate-200">
                                                    {queryResult.data?.map((row, idx) => (
                                                        <tr key={idx} className="hover:bg-slate-50 transition-colors">
                                                            {Object.values(row as Record<string, unknown>).map((val: unknown, vIdx) => (
                                                                <td key={vIdx} className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                                                                    {String(val)}
                                                                </td>
                                                            ))}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : (
                                        <div className="p-10 text-center bg-red-50/50">
                                            <XCircle className="mx-auto text-red-500 mb-3" size={40} />
                                            <p className="text-red-600 font-medium font-mono text-sm">{queryResult.error}</p>
                                            <Button variant="outline" size="sm" className="mt-4 border-red-200 text-red-700 hover:bg-red-100">
                                                🔄 嘗試自動修復 (Feature Coming)
                                            </Button>
                                        </div>
                                    )}
                                </Card>

                                {interpretation && (
                                    <Card className="p-6 border-blue-100 bg-blue-50/30">
                                        <h3 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
                                            <Bot size={20} className="text-blue-600"/> 智慧解讀
                                        </h3>
                                        <div className="text-slate-700 leading-relaxed">
                                            <MarkdownRenderer content={interpretation} />
                                        </div>
                                    </Card>
                                )}
                            </>
                        )}

                        {!processing && !queryResult && !generatedCode && (
                            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center opacity-40">
                                <Rocket size={64} className="mb-4 text-slate-300"/>
                                <h3 className="text-xl font-bold text-slate-400">準備就緒</h3>
                                <p className="text-slate-400 mt-2 max-w-sm">
                                    選擇數據文件並輸入問題，AI 將為您完成剩下的工作。
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
