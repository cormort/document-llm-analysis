"use client";

import { useState, useEffect } from "react";
import * as XLSX from "xlsx";
import { Header } from "@/components/layout/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { FileUploader } from "@/components/file-uploader";
import { nlToSQL, NLToSQLResponse, getDiagnostic, DiagnosticResponse } from "@/lib/api";
import { useSettingsStore } from "@/stores/settings-store";
import { useDataFileStore } from "@/stores/data-file-store";
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
    Sparkles,
} from "lucide-react";

export default function QueryPage() {
    const { provider, model_name, local_url, api_key } = useSettingsStore();
    const { files, fetchFiles } = useDataFileStore();

    const [processing, setProcessing] = useState(false);
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [question, setQuestion] = useState("");
    const [result, setResult] = useState<NLToSQLResponse | null>(null);
    const [metadata, setMetadata] = useState<DiagnosticResponse | null>(null);

    useEffect(() => { fetchFiles(); }, [fetchFiles]);

    useEffect(() => {
        if (!selectedFile) { setMetadata(null); return; }
        getDiagnostic({
            file_path: selectedFile,
            config: { provider, model_name, local_url, api_key: api_key || undefined }
        }).then(setMetadata).catch(console.error);
    }, [selectedFile, api_key, local_url, model_name, provider]);

    const handleQuery = async () => {
        if (!selectedFile || !question.trim()) return;
        setProcessing(true);
        setResult(null);
        try {
            const res = await nlToSQL(selectedFile, question, {
                provider, model_name, local_url, api_key: api_key || undefined
            });
            setResult(res);
        } catch (err) {
            setResult({ sql: "", success: false, error: err instanceof Error ? err.message : "查詢失敗" });
        } finally {
            setProcessing(false);
        }
    };

    const exportCSV = (data: Record<string, unknown>[]) => {
        if (!data.length) return;
        const headers = Object.keys(data[0]);
        const csv = [
            headers.join(","),
            ...data.map(r => headers.map(h => `"${String(r[h] ?? "").replace(/"/g, '""')}"`).join(","))
        ].join("\n");
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" }));
        a.download = "查詢結果.csv";
        a.click();
    };

    const exportExcel = (data: Record<string, unknown>[]) => {
        if (!data.length) return;
        const ws = XLSX.utils.json_to_sheet(data);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "查詢結果");
        XLSX.writeFile(wb, "查詢結果.xlsx");
    };

    const exportJSON = (data: Record<string, unknown>[]) => {
        if (!data.length) return;
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
        a.download = "查詢結果.json";
        a.click();
    };

    const formatSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return (
        <div className="flex-1 flex flex-col bg-slate-50">
            <Header
                title="💡 自然語言數據查詢"
                subtitle="使用白話文查詢 Excel/CSV，AI 自動產生 SQL 並即時執行"
            />

            <div className="flex-1 flex p-6 gap-6 overflow-hidden">
                {/* Left sidebar */}
                <div className="w-80 flex flex-col gap-4">
                    <FileUploader onUploadComplete={fetchFiles} skipIndex />

                    <Card className="p-4 flex flex-col flex-1 overflow-hidden">
                        <h3 className="font-semibold text-slate-700 mb-3 flex items-center gap-2 text-sm">
                            <FileText size={16} className="text-blue-500"/> 選擇數據源
                        </h3>
                        <ScrollArea className="flex-1">
                            <div className="space-y-2">
                                {files.length === 0 && (
                                    <p className="text-xs text-slate-400 text-center py-4">尚無數據檔案，請先上傳</p>
                                )}
                                {files.map((f) => (
                                    <button
                                        key={f.file_name}
                                        onClick={() => setSelectedFile(f.file_name)}
                                        className={`w-full text-left p-3 rounded-lg border transition-all ${
                                            selectedFile === f.file_name
                                                ? "bg-blue-50 border-blue-200 shadow-sm"
                                                : "bg-white border-slate-100 hover:bg-slate-50"
                                        }`}
                                    >
                                        <div className="flex items-center gap-2 mb-1">
                                            {selectedFile === f.file_name
                                                ? <CheckCircle2 size={14} className="text-blue-600"/>
                                                : <Database size={14} className="text-slate-400"/>}
                                            <p className={`font-medium text-xs truncate flex-1 ${selectedFile === f.file_name ? "text-blue-700" : "text-slate-700"}`}>
                                                {f.file_name}
                                            </p>
                                        </div>
                                        <p className="text-[10px] text-slate-400 pl-6">{formatSize(f.size_bytes)}</p>
                                    </button>
                                ))}
                            </div>
                        </ScrollArea>
                    </Card>

                    {metadata && (
                        <Card className="p-4 flex flex-col max-h-72 overflow-hidden animate-in slide-in-from-left-2 duration-500">
                            <h3 className="font-semibold text-slate-700 flex items-center gap-2 text-sm mb-2">
                                <BarChart3 size={16} className="text-purple-500"/> 資料集概覽
                            </h3>
                            <div className="flex gap-2 mb-3">
                                <Badge variant="secondary">{metadata.quality_report.length} 個欄位</Badge>
                            </div>
                            <ScrollArea className="flex-1 pr-3">
                                <div className="space-y-2">
                                    {metadata.quality_report.map((col) => (
                                        <div key={col.column} className="p-2 bg-slate-50 rounded border border-slate-100">
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-bold text-xs text-slate-700 truncate max-w-[120px]" title={col.column}>{col.column}</span>
                                                <Badge variant="outline" className="text-[10px] scale-90">{col.dtype}</Badge>
                                            </div>
                                            <div className="text-[10px] text-slate-500">
                                                <span className="font-semibold">範例：</span>
                                                {col.sample_values.slice(0, 2).map(String).join(", ")}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </ScrollArea>
                        </Card>
                    )}
                </div>

                {/* Right main area */}
                <div className="flex-1 flex flex-col gap-6 overflow-hidden">
                    <Card className="p-6 bg-white shadow-sm">
                        <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
                            <Search size={18} className="text-blue-500"/> 您想了解什麼？
                        </h3>
                        <div className="flex gap-4">
                            <Input
                                value={question}
                                onChange={(e) => setQuestion(e.target.value)}
                                placeholder="例如：哪個行業的電子發票張數最多？"
                                className="flex-1"
                                disabled={processing || !selectedFile}
                                onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                            />
                            <Button
                                onClick={handleQuery}
                                disabled={processing || !selectedFile || !question.trim()}
                                className="bg-blue-600 hover:bg-blue-700 px-8"
                            >
                                {processing
                                    ? <><Sparkles size={16} className="mr-2 animate-pulse"/> 查詢中...</>
                                    : "查詢數據"}
                            </Button>
                        </div>
                        {!selectedFile && (
                            <p className="text-xs text-amber-600 mt-2 flex items-center gap-1.5">
                                <AlertTriangle size={12}/> 請先在左側選擇一個 CSV 或 Excel 檔案
                            </p>
                        )}
                    </Card>

                    <div className="flex-1 overflow-y-auto space-y-6 pb-6">
                        {processing && (
                            <div className="space-y-4">
                                <Skeleton className="h-16 w-full"/>
                                <Skeleton className="h-64 w-full"/>
                            </div>
                        )}

                        {!processing && result && (
                            <>
                                {/* Generated SQL */}
                                {result.sql && (
                                    <Card className="p-4 border-slate-200 bg-slate-50/50">
                                        <div className="flex items-center justify-between mb-3">
                                            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                                                <Code size={14} className="text-blue-400"/> 產生的 SQL
                                            </span>
                                            <Badge variant="outline" className="text-[10px]">DuckDB SQL</Badge>
                                        </div>
                                        <pre className="text-xs bg-slate-900 text-blue-300 p-4 rounded-lg overflow-x-auto shadow-inner">
                                            <code>{result.sql}</code>
                                        </pre>
                                    </Card>
                                )}

                                {/* Result table */}
                                <Card className="overflow-hidden border-slate-200 shadow-sm">
                                    <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between flex-wrap gap-2">
                                        <h3 className="font-semibold text-slate-700 flex items-center gap-2">
                                            <BarChart3 size={18} className="text-emerald-500"/> 執行結果
                                            {result.summary && <span className="text-xs text-slate-500 font-normal">{result.summary}</span>}
                                        </h3>
                                        {result.success && result.data && result.data.length > 0 && (
                                            <div className="flex gap-2">
                                                <button onClick={() => exportCSV(result.data as Record<string, unknown>[])} className="text-xs font-bold px-3 py-1.5 rounded-lg bg-amber-500 text-white hover:bg-amber-600 transition-colors">CSV</button>
                                                <button onClick={() => exportExcel(result.data as Record<string, unknown>[])} className="text-xs font-bold px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors">Excel</button>
                                                <button onClick={() => exportJSON(result.data as Record<string, unknown>[])} className="text-xs font-bold px-3 py-1.5 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors">JSON</button>
                                            </div>
                                        )}
                                    </div>
                                    {result.success && result.data ? (
                                        <div className="overflow-x-auto">
                                            <table className="min-w-full divide-y divide-slate-200">
                                                <thead className="bg-slate-50">
                                                    <tr>
                                                        {result.data.length > 0 && Object.keys(result.data[0]).map((key) => (
                                                            <th key={key} className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">{key}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody className="bg-white divide-y divide-slate-200">
                                                    {result.data.map((row, idx) => (
                                                        <tr key={idx} className="hover:bg-slate-50 transition-colors">
                                                            {Object.values(row).map((val, vIdx) => (
                                                                <td key={vIdx} className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{String(val ?? "")}</td>
                                                            ))}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : (
                                        <div className="p-10 text-center bg-red-50/50">
                                            <XCircle className="mx-auto text-red-500 mb-3" size={40}/>
                                            <p className="text-red-600 font-medium font-mono text-sm">{result.error}</p>
                                        </div>
                                    )}
                                </Card>

                                {/* AI interpretation */}
                                {result.interpretation && (
                                    <Card className="p-6 border-blue-100 bg-blue-50/30">
                                        <h3 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
                                            <Bot size={20} className="text-blue-600"/> 智慧解讀
                                        </h3>
                                        <div className="text-slate-700 leading-relaxed">
                                            <MarkdownRenderer content={result.interpretation}/>
                                        </div>
                                    </Card>
                                )}
                            </>
                        )}

                        {!processing && !result && (
                            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center opacity-40">
                                <Rocket size={64} className="mb-4 text-slate-300"/>
                                <h3 className="text-xl font-bold text-slate-400">準備就緒</h3>
                                <p className="text-slate-400 mt-2 max-w-sm">選擇數據文件並輸入問題，AI 將自動產生 SQL 並執行。</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
