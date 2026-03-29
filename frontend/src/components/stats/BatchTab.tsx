/**
 * BatchTab - Batch Analysis Tab for Stats Page
 *
 * This component provides multi-dimensional group-by analysis with AI insights.
 * Migrated from standalone /batch page to integrate with /stats.
 */

"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { analyzeBatch, BatchAnalyzeResponse, DiagnosticResponse } from "@/lib/api";
import { Package, Puzzle, BarChart3, Settings, Sparkles, Search, Loader2, Rocket, Download } from "lucide-react";
import { useSettingsStore } from "@/stores/settings-store";
import { useDocumentStore } from "@/stores/document-store";

interface BatchTabProps {
    selectedDoc: string | null;
    filePath: string | null;
    diagnostics: DiagnosticResponse | null;
}

export function BatchTab({ selectedDoc, filePath, diagnostics }: BatchTabProps) {
    const { provider, model_name, local_url, api_key } = useSettingsStore();
    const { documents } = useDocumentStore();

    const [processing, setProcessing] = useState(false);
    const [groupByCols, setGroupByCols] = useState<string[]>([]);
    const [metricCols, setMetricCols] = useState<string[]>([]);
    const [analysisMode, setAnalysisMode] = useState<"pairwise" | "consolidated">("consolidated");
    const [result, setResult] = useState<BatchAnalyzeResponse | null>(null);

    // Derive available columns from diagnostics
    const allColumns = diagnostics?.quality_report.map(c => c.column) || [];
    const numericColumns = diagnostics?.quality_report
        .filter(c => c.dtype.includes("int") || c.dtype.includes("float"))
        .map(c => c.column) || [];
    const categoricalColumns = diagnostics?.quality_report
        .filter(c => c.dtype === "object" || c.dtype === "category")
        .map(c => c.column) || [];

    // Reset selections when document changes
    useEffect(() => {
        setGroupByCols([]);
        setMetricCols([]);
        setResult(null);
    }, [selectedDoc]);

    const handleAnalyze = async () => {
        if (!filePath || groupByCols.length === 0 || metricCols.length === 0) return;
        setProcessing(true);
        setResult(null);

        try {
            const res = await analyzeBatch({
                file_path: filePath,
                group_by_cols: groupByCols,
                metric_cols: metricCols,
                analysis_mode: analysisMode,
                currency_unit: "TWD",
                config: {
                    provider,
                    model_name,
                    local_url,
                    api_key: api_key || undefined
                }
            });
            setResult(res);
        } catch (err) {
            console.error("Batch analysis failed", err);
        } finally {
            setProcessing(false);
        }
    };

    const toggleCol = (col: string, list: string[], setList: (l: string[]) => void) => {
        if (list.includes(col)) {
            setList(list.filter(c => c !== col));
        } else {
            setList([...list, col]);
        }
    };

    if (!selectedDoc) {
        return (
            <div className="flex flex-col items-center justify-center p-12 text-center opacity-50">
                <Package size={64} className="mb-4 text-slate-300"/>
                <h3 className="text-xl font-bold text-slate-400">請先選擇數據集</h3>
                <p className="text-slate-400 mt-2">在左側側邊欄選擇一個 CSV 或 Excel 檔案以開始批次分析。</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Configuration Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Group By Selection */}
                <Card className="p-4 border-l-4 border-l-blue-500">
                    <h3 className="font-semibold text-slate-700 mb-3 text-sm flex items-center gap-2">
                        <Puzzle size={16} className="text-blue-500"/> 分組維度 (Group By)
                    </h3>
                    <p className="text-xs text-slate-500 mb-3">選擇用於分組的類別型欄位</p>
                    <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                        {(categoricalColumns.length > 0 ? categoricalColumns : allColumns.slice(0, 6)).map(col => (
                            <div key={col} className="flex items-center gap-2">
                                <Checkbox
                                    id={`batch-group-${col}`}
                                    checked={groupByCols.includes(col)}
                                    onCheckedChange={() => toggleCol(col, groupByCols, setGroupByCols)}
                                />
                                <label htmlFor={`batch-group-${col}`} className="text-xs cursor-pointer truncate" title={col}>
                                    {col}
                                </label>
                            </div>
                        ))}
                    </div>
                    {groupByCols.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                            {groupByCols.map(col => (
                                <Badge key={col} variant="secondary" className="text-[10px]">{col}</Badge>
                            ))}
                        </div>
                    )}
                </Card>

                {/* Metrics Selection */}
                <Card className="p-4 border-l-4 border-l-purple-500">
                    <h3 className="font-semibold text-slate-700 mb-3 text-sm flex items-center gap-2">
                        <BarChart3 size={16} className="text-purple-500"/> 分析指標 (Metrics)
                    </h3>
                    <p className="text-xs text-slate-500 mb-3">選擇要進行聚合分析的數值欄位</p>
                    <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                        {numericColumns.map(col => (
                            <div key={col} className="flex items-center gap-2">
                                <Checkbox
                                    id={`batch-metric-${col}`}
                                    checked={metricCols.includes(col)}
                                    onCheckedChange={() => toggleCol(col, metricCols, setMetricCols)}
                                />
                                <label htmlFor={`batch-metric-${col}`} className="text-xs cursor-pointer truncate" title={col}>
                                    {col}
                                </label>
                            </div>
                        ))}
                    </div>
                    {metricCols.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                            {metricCols.map(col => (
                                <Badge key={col} variant="outline" className="text-[10px] border-purple-300">{col}</Badge>
                            ))}
                        </div>
                    )}
                </Card>
            </div>

            {/* Analysis Mode & Execute */}
            <Card className="p-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-6">
                        <div>
                            <h3 className="font-semibold text-slate-700 text-sm mb-2 flex items-center gap-1"><Settings size={14}/> 分析模式</h3>
                            <Tabs value={analysisMode} onValueChange={(v) => setAnalysisMode(v as "pairwise" | "consolidated")}>
                                <TabsList className="h-8">
                                    <TabsTrigger value="consolidated" className="text-[10px] px-3">綜合報告</TabsTrigger>
                                    <TabsTrigger value="pairwise" className="text-[10px] px-3">逐項分析</TabsTrigger>
                                </TabsList>
                            </Tabs>
                        </div>
                        <p className="text-[10px] text-slate-500 italic max-w-sm flex flex-col gap-1">
                            {analysisMode === "consolidated"
                                ? <span className="flex items-center gap-1"><Sparkles size={10}/> 綜合報告：AI 會彙總所有分組數據，找出跨組的趨勢與異常點。</span>
                                : <span className="flex items-center gap-1"><Search size={10}/> 逐項分析：AI 會針對每一個分組獨立撰寫分析報告。</span>}
                        </p>
                    </div>

                    <Button
                        onClick={handleAnalyze}
                        disabled={processing || groupByCols.length === 0 || metricCols.length === 0}
                        className="bg-blue-600 hover:bg-blue-700 font-bold px-8"
                    >
                        {processing ? <><Loader2 size={16} className="animate-spin mr-2"/> 分析中...</> : <><Rocket size={16} className="mr-2"/> 開始批次分析</>}
                    </Button>
                </div>
            </Card>

            {/* Results */}
            {processing && (
                <Card className="p-12 flex flex-col items-center justify-center">
                    <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4" />
                    <h2 className="text-lg font-bold text-slate-800">正在處理 {groupByCols.join(", ")} 的批次分析</h2>
                    <p className="text-sm text-slate-500 mt-2">這涉及數據分組聚合與多輪 AI 推理...</p>
                </Card>
            )}

            {result && !processing && (
                <Card className="overflow-hidden">
                    <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Badge variant="outline">{analysisMode === "consolidated" ? "綜合模式" : "逐項模式"}</Badge>
                            <span className="text-xs text-slate-500">耗時: {result.execution_time.toFixed(2)}s</span>
                        </div>
                        <Button variant="ghost" size="sm"><Download size={14} className="mr-1"/> 匯出分析報告</Button>
                    </div>

                    <ScrollArea className="max-h-[600px] p-8">
                        {analysisMode === "consolidated" && result.consolidated_report && (
                            <div className="max-w-4xl mx-auto">
                                <h2 className="text-2xl font-bold text-blue-900 mb-6 border-l-4 border-blue-600 pl-4">批次彙總分析報告</h2>
                                <MarkdownRenderer content={result.consolidated_report} />

                                <Separator className="my-10" />

                                <h3 className="text-lg font-bold text-slate-700 mb-4">分組數據摘要</h3>
                                <div className="grid grid-cols-2 gap-4">
                                    {result.results.map(r => (
                                        <Card key={r.group_value} className="p-4 bg-slate-50 border-slate-100">
                                            <p className="font-bold text-blue-700 text-sm mb-2">{r.group_value}</p>
                                            <pre className="text-[10px] text-slate-600 font-mono overflow-x-auto">
                                                {JSON.stringify(r.data_summary, null, 2)}
                                            </pre>
                                        </Card>
                                    ))}
                                </div>
                            </div>
                        )}

                        {analysisMode === "pairwise" && (
                            <div className="space-y-8 max-w-4xl mx-auto">
                                {result.results.map((r, idx) => (
                                    <div key={idx} className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                                        <div className="bg-slate-900 text-white px-6 py-3 flex justify-between items-center">
                                            <span className="font-bold">分組：{r.group_value}</span>
                                            <Badge className="bg-blue-500">個別分析</Badge>
                                        </div>
                                        <div className="p-6">
                                            <MarkdownRenderer content={r.analysis_text} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </ScrollArea>
                </Card>
            )}
        </div>
    );
}
