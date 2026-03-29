"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { getDescriptiveStats, interpretStats, DescriptiveStatsResponse, LLMConfig } from "@/lib/api";
import { Ruler, Play, Bot, Sparkles, Loader2 } from "lucide-react";

interface DescriptiveTabProps {
    selectedDoc: string | null;
    filePath: string | null;
    config: LLMConfig;
}

export function DescriptiveTab({ selectedDoc, filePath, config }: DescriptiveTabProps) {
    const [processing, setProcessing] = useState(false);
    const [descriptiveStats, setDescriptiveStats] = useState<DescriptiveStatsResponse | null>(null);
    const [descInterpretation, setDescInterpretation] = useState<string | null>(null);
    const [isInterpretingDesc, setIsInterpretingDesc] = useState(false);

    const handleRunDescriptive = async () => {
        if (!selectedDoc || !filePath) return;
        setProcessing(true);
        setDescriptiveStats(null);
        setDescInterpretation(null);
        try {
            const res = await getDescriptiveStats({
                file_path: filePath,
                config: config
            });
            setDescriptiveStats(res);
        } catch (err) {
            console.error("Descriptive stats failed", err);
        } finally {
            setProcessing(false);
        }
    };

    const handleInterpretDescriptive = async () => {
        if (!descriptiveStats) return;
        setIsInterpretingDesc(true);
        try {
            // Format stats for AI
            const summary = descriptiveStats.stats.map(s => 
                `${s.column}: Mean=${s.mean.toFixed(2)}, Std=${s.std.toFixed(2)}, Min=${s.min}, Max=${s.max}, Skew=${s.skewness.toFixed(2)}`
            ).join("\n");

            const res = await interpretStats({
                context: "這是數據集所有數值欄位的詳細敘述性統計結果。",
                data_summary: summary,
                test_type: "Descriptive Statistics",
                config: config
            });
            setDescInterpretation(res.interpretation);
        } catch (err) {
            console.error("Interpretation failed", err);
        } finally {
            setIsInterpretingDesc(false);
        }
    };

    if (!selectedDoc) {
        return (
            <Card className="p-12 text-center opacity-40">
                <p>請先選擇數據文件</p>
            </Card>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <Card className="p-6">
                <h3 className="font-bold mb-4 flex items-center gap-2"><Ruler size={20} className="text-teal-600"/> 敘述性統計 (Descriptive Statistics)</h3>
                <p className="text-sm text-slate-500 mb-4">計算數值欄位的詳細統計指標，包括平均值、標準差、四分位數等。</p>
                <Button
                    onClick={handleRunDescriptive}
                    className="bg-teal-600 hover:bg-teal-700 h-9"
                    disabled={processing}
                >
                    <Play size={14} className="mr-2"/> 計算敘述性統計
                </Button>
            </Card>

            {processing ? (
                <Card className="p-12 h-64 animate-pulse bg-slate-100" />
            ) : descriptiveStats ? (
                <Card className="p-6 overflow-hidden">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="font-bold">統計指標表</h3>
                        <div className="text-xs text-slate-500">
                            總筆數: {descriptiveStats.total_rows} | 數值欄位: {descriptiveStats.numeric_columns}
                        </div>
                    </div>
                    <ScrollArea className="w-full">
                        <div className="min-w-[800px]">
                            <table className="w-full text-xs border-collapse">
                                <thead>
                                    <tr className="bg-slate-50 border-b border-slate-200">
                                        <th className="p-2 text-left font-bold border-r">欄位 (Column)</th>
                                        <th className="p-2 text-right">平均 (Mean)</th>
                                        <th className="p-2 text-right">中位數 (Median)</th>
                                        <th className="p-2 text-right">標準差 (Std)</th>
                                        <th className="p-2 text-right text-slate-400">Min</th>
                                        <th className="p-2 text-right text-slate-400">25%</th>
                                        <th className="p-2 text-right text-slate-400">75%</th>
                                        <th className="p-2 text-right text-slate-400">Max</th>
                                        <th className="p-2 text-right border-l">偏態 (Skew)</th>
                                        <th className="p-2 text-right">峰度 (Kurt)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {descriptiveStats.stats.map((row) => (
                                        <tr key={row.column} className="border-b border-slate-100 hover:bg-slate-50">
                                            <td className="p-2 font-mono font-bold text-blue-700 border-r">{row.column}</td>
                                            <td className="p-2 text-right font-medium">{row.mean.toFixed(2)}</td>
                                            <td className="p-2 text-right font-medium">{row.median.toFixed(2)}</td>
                                            <td className="p-2 text-right text-slate-600">{row.std.toFixed(2)}</td>
                                            <td className="p-2 text-right text-slate-400">{row.min.toFixed(1)}</td>
                                            <td className="p-2 text-right text-slate-400">{row.q25.toFixed(1)}</td>
                                            <td className="p-2 text-right text-slate-400">{row.q75.toFixed(1)}</td>
                                            <td className="p-2 text-right text-slate-400">{row.max.toFixed(1)}</td>
                                            <td className={`p-2 text-right border-l ${Math.abs(row.skewness) > 1 ? "text-red-500 font-bold" : "text-slate-500"}`}>
                                                {row.skewness.toFixed(2)}
                                            </td>
                                            <td className="p-2 text-right text-slate-500">{row.kurtosis.toFixed(2)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </ScrollArea>
                    
                    <div className="mt-4 pt-4 border-t border-slate-100">
                        <div className="flex justify-between items-center">
                            <h4 className="font-bold text-sm flex items-center gap-2">
                                <Bot size={16} className="text-violet-600"/> AI 智能解讀 (AI Interpretation)
                            </h4>
                            <Button 
                                variant="outline" 
                                size="sm" 
                                onClick={handleInterpretDescriptive}
                                disabled={isInterpretingDesc}
                                className="text-violet-600 border-violet-200 hover:bg-violet-50"
                            >
                                {isInterpretingDesc ? <><Loader2 size={14} className="animate-spin mr-1"/> 分析中...</> : <><Sparkles size={14} className="mr-1"/> 讓 AI 分析這些數據</>}
                            </Button>
                        </div>
                        
                        {descInterpretation && (
                            <div className="mt-4 bg-slate-50 p-4 rounded-lg text-sm border border-slate-200">
                                <MarkdownRenderer content={descInterpretation} />
                            </div>
                        )}
                    </div>
                </Card>
            ) : (
                <div className="text-center py-20 bg-white border rounded-xl opacity-40">
                    <p>點擊上方按鈕開始計算與分析</p>
                </div>
            )}
        </div>
    );
}
