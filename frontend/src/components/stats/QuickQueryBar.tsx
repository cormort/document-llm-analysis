/**
 * QuickQueryBar - Inline Natural Language Query for Stats Page
 *
 * A lightweight query interface that allows users to ask questions about their data
 * directly within the Stats page without switching to the dedicated Query page.
 */

"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { generatePandasQuery, executeQuery, interpretQuery, QueryExecuteResponse } from "@/lib/api";
import { useSettingsStore } from "@/stores/settings-store";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { Loader2, ChevronDown, ChevronUp, Sparkles, Search, Bot, XCircle } from "lucide-react";

interface QuickQueryBarProps {
    filePath: string | null;
}

export function QuickQueryBar({ filePath }: QuickQueryBarProps) {
    const { provider, model_name, local_url, api_key } = useSettingsStore();

    const [expanded, setExpanded] = useState(false);
    const [question, setQuestion] = useState("");
    const [processing, setProcessing] = useState(false);
    const [generatedCode, setGeneratedCode] = useState<string | null>(null);
    const [queryResult, setQueryResult] = useState<QueryExecuteResponse | null>(null);
    const [interpretation, setInterpretation] = useState<string | null>(null);

    const handleQuery = async () => {
        if (!filePath || !question.trim()) return;

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
            const { pandas_code } = await generatePandasQuery(filePath, question, config);
            setGeneratedCode(pandas_code);

            // 2. Execute code
            const res = await executeQuery({
                file_path: filePath,
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

    if (!filePath) return null;

    return (
        <Card className="border-l-4 border-l-amber-500 overflow-hidden">
            {/* Collapsed Header */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full p-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-amber-500" />
                    <span className="font-bold text-slate-700">快速查詢 (Quick Query)</span>
                    <span className="text-xs text-slate-400">用自然語言提問</span>
                </div>
                {expanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                )}
            </button>

            {/* Expanded Content */}
            {expanded && (
                <div className="p-4 pt-0 space-y-4 animate-in slide-in-from-top-2 duration-200">
                    <div className="flex gap-3">
                        <Input
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            placeholder="例如：找出營收最高的前 5 個產品..."
                            className="flex-1"
                            disabled={processing}
                            onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                        />
                        <Button
                            onClick={handleQuery}
                            disabled={processing || !question.trim()}
                            className="bg-amber-500 hover:bg-amber-600 text-white px-6"
                        >
                            {processing ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                    查詢中...
                                </>
                            ) : (
                                <>
                                    <Search className="w-4 h-4 mr-2" /> 查詢
                                </>
                            )}
                        </Button>
                    </div>

                    {/* Generated Code */}
                    {generatedCode && (
                        <div className="p-3 bg-slate-900 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-[10px] font-bold text-slate-400 uppercase">AI 生成的 Pandas 程式碼</span>
                                <Badge variant="outline" className="text-[10px] border-slate-600 text-slate-400">Python</Badge>
                            </div>
                            <pre className="text-xs text-blue-300 overflow-x-auto">
                                <code>{generatedCode}</code>
                            </pre>
                        </div>
                    )}

                    {/* Results */}
                    {queryResult && (
                        <div className="space-y-3">
                            {queryResult.success ? (
                                <>
                                    <div className="rounded-lg border overflow-hidden">
                                        <div className="p-2 bg-slate-50 border-b flex items-center justify-between">
                                            <span className="text-xs font-bold text-slate-600">查詢結果</span>
                                            <span className="text-[10px] text-slate-400">{queryResult.summary}</span>
                                        </div>
                                        <div className="overflow-x-auto max-h-48">
                                            <table className="min-w-full divide-y divide-slate-200 text-xs">
                                                <thead className="bg-slate-50">
                                                    <tr>
                                                        {queryResult.data && queryResult.data.length > 0 && Object.keys(queryResult.data[0]).map((key) => (
                                                            <th key={key} className="px-3 py-2 text-left font-medium text-slate-500">
                                                                {key}
                                                            </th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody className="bg-white divide-y divide-slate-200">
                                                    {queryResult.data?.slice(0, 10).map((row, idx) => (
                                                        <tr key={idx}>
                                                            {Object.values(row).map((val: unknown, vIdx) => (
                                                                <td key={vIdx} className="px-3 py-2 whitespace-nowrap text-slate-600">
                                                                    {String(val)}
                                                                </td>
                                                            ))}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>

                                    {interpretation && (
                                        <div className="p-4 bg-amber-50 rounded-lg border border-amber-100">
                                            <h4 className="font-bold text-amber-800 mb-2 text-sm flex items-center gap-2">
                                                <Bot className="w-5 h-5 text-amber-600"/> 智慧解讀
                                            </h4>
                                            <div className="text-sm text-slate-700">
                                                <MarkdownRenderer content={interpretation} />
                                            </div>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div className="p-4 bg-red-50 rounded-lg border border-red-100 text-center">
                                    <XCircle className="w-8 h-8 mx-auto text-red-500 mb-2" />
                                    <p className="text-red-600 text-sm font-mono">{queryResult.error}</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </Card>
    );
}
