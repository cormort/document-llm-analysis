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
import { generatePandasQuery, executeQuery, interpretQuery, QueryExecuteResponse, getDiagnostic, DiagnosticResponse } from "@/lib/api";
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
    Sparkles
} from "lucide-react";

export default function QueryPage() {
    const { provider, model_name, local_url, api_key } = useSettingsStore();
    const { files, fetchFiles } = useDataFileStore();

    const [processing, setProcessing] = useState(false);
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [question, setQuestion] = useState("");
    const [generatedCode, setGeneratedCode] = useState<string | null>(null);
    const [queryResult, setQueryResult] = useState<QueryExecuteResponse | null>(null);
    const [interpretation, setInterpretation] = useState<string | null>(null);
    const [metadata, setMetadata] = useState<DiagnosticResponse | null>(null);

    useEffect(() => {
        fetchFiles();
    }, [fetchFiles]);

    useEffect(() => {
        async function fetchMetadata() {
            if (!selectedFile) {
                setMetadata(null);
                return;
            }
            try {
                const res = await getDiagnostic({
                    file_path: selectedFile,
                    config: { provider, model_name, local_url, api_key: api_key || undefined }
                });
                setMetadata(res);
            } catch (err) {
                console.error("Failed to fetch metadata", err);
            }
        }
        fetchMetadata();
    }, [selectedFile, api_key, local_url, model_name, provider]);

    const handleQuery = async () => {
        if (!selectedFile || !question.trim()) return;
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
            const { pandas_code } = await generatePandasQuery(selectedFile, question, config);
            setGeneratedCode(pandas_code);

            const res = await executeQuery({ file_path: selectedFile, pandas_code });
            setQueryResult(res);

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
                subtitle="使用白話文查詢 Excel/CSV，AI 自動編寫 Pandas 腳本"
            />

            <div className="flex-1 flex p-6 gap-6 overflow-hidden">
                {/* Left: Settings */}
                <div className="w-80 flex flex-col gap-4">
                    {/* Uploader */}
                    <FileUploader onUploadComplete={fetchFiles} skipIndex />

                    {/* File List */}
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
                                        className={`w-full text-left p-3 rounded-lg border transition-all ${selectedFile === f.file_name
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

                    {/* Data Dictionary */}
                    {metadata && (
                        <Card className="p-4 flex flex-col flex-1 overflow-hidden animate-in slide-in-from-left-2 duration-500">
                            <div className="mb-3">
                                <h3 className="font-semibold text-slate-700 flex items-center gap-2 text-sm">
                                    <BarChart3 size={16} className="text-purple-500"/> 資料集概覽
                                </h3>
                                <div className="flex gap-2 mt-2 text-xs text-slate-500">
                                    <Badge variant="secondary">{metadata.quality_report.length} 個欄位</Badge>
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

                {/* Right: Interactive Area */}
                <div className="flex-1 flex flex-col gap-6 overflow-hidden">
                    <Card className="p-6 bg-white shadow-sm">
                        <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
                             <Search size={18} className="text-blue-500"/> 您想了解什麼？
                        </h3>
                        <div className="flex gap-4">
                            <Input
                                value={question}
                                onChange={(e) => setQuestion(e.target.value)}
                                placeholder="例如：列出 113 年底人口數大於 100 萬的城市..."
                                className="flex-1"
                                disabled={processing || !selectedFile}
                                onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                            />
                            <Button
                                onClick={handleQuery}
                                disabled={processing || !selectedFile || !question.trim()}
                                className="bg-blue-600 hover:bg-blue-700 px-8"
                            >
                                {processing ? (
                                    <><Sparkles size={16} className="mr-2 animate-pulse"/> 分析中...</>
                                ) : "查詢數據"}
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
                                <Skeleton className="h-40 w-full"/>
                                <Skeleton className="h-64 w-full"/>
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
                                    <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between flex-wrap gap-2">
                                        <h3 className="font-semibold text-slate-700 flex items-center gap-2">
                                            <BarChart3 size={18} className="text-emerald-500"/> 執行結果
                                            {queryResult.summary && <span className="text-xs text-slate-500 font-normal">{queryResult.summary}</span>}
                                        </h3>
                                        {queryResult.success && queryResult.data && queryResult.data.length > 0 && (
                                            <div className="flex gap-2">
                                                <button onClick={() => exportCSV(queryResult.data as Record<string, unknown>[])} className="text-xs font-bold px-3 py-1.5 rounded-lg bg-amber-500 text-white hover:bg-amber-600 transition-colors">CSV</button>
                                                <button onClick={() => exportExcel(queryResult.data as Record<string, unknown>[])} className="text-xs font-bold px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors">Excel</button>
                                                <button onClick={() => exportJSON(queryResult.data as Record<string, unknown>[])} className="text-xs font-bold px-3 py-1.5 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors">JSON</button>
                                            </div>
                                        )}
                                    </div>
                                    {queryResult.success ? (
                                        <div className="overflow-x-auto">
                                            <table className="min-w-full divide-y divide-slate-200">
                                                <thead className="bg-slate-50">
                                                    <tr>
                                                        {queryResult.data && queryResult.data.length > 0 && Object.keys(queryResult.data[0]).map((key) => (
                                                            <th key={key} className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">{key}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody className="bg-white divide-y divide-slate-200">
                                                    {queryResult.data?.map((row, idx) => (
                                                        <tr key={idx} className="hover:bg-slate-50 transition-colors">
                                                            {Object.values(row as Record<string, unknown>).map((val, vIdx) => (
                                                                <td key={vIdx} className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{String(val)}</td>
                                                            ))}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : (
                                        <div className="p-10 text-center bg-red-50/50">
                                            <XCircle className="mx-auto text-red-500 mb-3" size={40}/>
                                            <p className="text-red-600 font-medium font-mono text-sm">{queryResult.error}</p>
                                        </div>
                                    )}
                                </Card>

                                {interpretation && (
                                    <Card className="p-6 border-blue-100 bg-blue-50/30">
                                        <h3 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
                                            <Bot size={20} className="text-blue-600"/> 智慧解讀
                                        </h3>
                                        <div className="text-slate-700 leading-relaxed">
                                            <MarkdownRenderer content={interpretation}/>
                                        </div>
                                    </Card>
                                )}
                            </>
                        )}

                        {!processing && !queryResult && !generatedCode && (
                            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center opacity-40">
                                <Rocket size={64} className="mb-4 text-slate-300"/>
                                <h3 className="text-xl font-bold text-slate-400">準備就緒</h3>
                                <p className="text-slate-400 mt-2 max-w-sm">選擇數據文件並輸入問題，AI 將為您完成剩下的工作。</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
