"use client";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { EDAResponse } from "@/lib/api";
import { Link, Play, Bot, ZoomIn } from "lucide-react";

interface CorrelationTabProps {
    selectedDoc: string | null;
    processing: boolean;
    edaResults: EDAResponse | null;
    onRunCorrelation: () => void;
    onInterpret: () => void;
    isInterpreting: boolean;
}

export function CorrelationTab({
    selectedDoc,
    processing,
    edaResults,
    onRunCorrelation,
    onInterpret,
    isInterpreting
}: CorrelationTabProps) {

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
                <h3 className="font-bold mb-4 flex items-center gap-2"><Link size={20} className="text-blue-500"/> 相關性矩陣分析 (Correlation Matrix)</h3>
                <p className="text-sm text-slate-500 mb-4">計算數值欄位之間的 Pearson 相關係數 (-1 ~ 1)</p>
                <Button
                    onClick={onRunCorrelation}
                    className="bg-indigo-600 hover:bg-indigo-700 h-9"
                    disabled={processing}
                >
                    <Play size={14} className="mr-2"/> 計算相關性矩陣
                </Button>
            </Card>

            {processing ? (
                <Card className="p-12 h-64 animate-pulse bg-slate-100" />
            ) : edaResults && typeof edaResults.result_data === 'object' && !Array.isArray(edaResults.result_data) ? (
                <div className="space-y-6">
                    {/* AI Interpretation Trigger */}
                    {!edaResults.interpretation && !isInterpreting && (
                        <div className="flex justify-end">
                            <Button
                                onClick={onInterpret}
                                className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2"
                            >
                                <Bot size={16}/> 開始 AI 深度解讀
                            </Button>
                        </div>
                    )}
                    
                    {edaResults.interpretation && (
                        <Card className="p-6 bg-blue-900 text-blue-50 border-none shadow-xl">
                            <h3 className="font-bold mb-4 flex items-center gap-2">
                                <span className="p-1 bg-blue-700 rounded text-xs px-2">AI 深度洞察</span>
                            </h3>
                            <MarkdownRenderer content={edaResults.interpretation} />
                        </Card>
                    )}

                    {isInterpreting && (
                         <div className="flex items-center justify-center p-2 bg-blue-50 text-blue-600 text-xs rounded border border-blue-100 animate-pulse gap-2">
                            <Bot size={14} /> <span>AI 正在撰寫解讀報告中...</span>
                        </div>
                    )}

                    {/* Correlation Matrix Table */}
                    <Card className="p-6 overflow-hidden group hover:overflow-visible transition-all duration-300 relative z-10 w-full hover:w-[150%] hover:scale-110 origin-top-left hover:shadow-2xl bg-white">
                        <h4 className="font-bold text-xs mb-2 text-slate-400 group-hover:text-slate-600 transition-colors flex items-center gap-1"><ZoomIn size={12}/> 縮放檢視 (Hover to Zoom)</h4>
                        <ScrollArea className="w-full">
                            <div className="min-w-[500px]">
                                <table className="w-full text-[10px] border-collapse group-hover:text-xs transition-all">
                                    <thead>
                                        <tr>
                                            <th className="p-2 bg-slate-50 border border-slate-200"></th>
                                            {Object.keys(edaResults.result_data as Record<string, unknown>).map(col => (
                                                <th key={col} className="p-2 bg-slate-50 border border-slate-200 truncate max-w-[80px] group-hover:max-w-none">{col}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {Object.keys(edaResults.result_data as Record<string, unknown>).map(row => (
                                            <tr key={row}>
                                                <td className="p-2 bg-slate-50 border border-slate-200 font-bold truncate max-w-[80px] group-hover:max-w-none">{row}</td>
                                                {Object.keys(edaResults.result_data as Record<string, unknown>).map(col => {
                                                    const val = (edaResults.result_data as Record<string, Record<string, number>>)[row]?.[col];
                                                    const opacity = Math.abs(val || 0);
                                                    const color = val > 0 ? `rgba(34, 197, 94, ${opacity})` : `rgba(239, 68, 68, ${opacity})`;
                                                    return (
                                                        <td
                                                            key={col}
                                                            className="p-2 border border-slate-200 text-center font-mono"
                                                            style={{ backgroundColor: color, color: opacity > 0.5 ? 'white' : 'black' }}
                                                        >
                                                            {val?.toFixed(2)}
                                                        </td>
                                                    );
                                                })}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </ScrollArea>
                    </Card>
                </div>
            ) : null}
        </div>
    );
}
