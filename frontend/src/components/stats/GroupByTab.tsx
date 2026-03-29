"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import { FolderKanban, Play } from "lucide-react";
import { DiagnosticResponse, EDAResponse } from "@/lib/api";

interface GroupByTabProps {
    selectedDoc: string | null;
    processing: boolean;
    edaResults: EDAResponse | null;
    diagnostics: DiagnosticResponse | null;
    onRunGroupBy: (params: { group_col: string; target_col: string; agg_func: string }) => void;
}

export function GroupByTab({
    selectedDoc,
    processing,
    edaResults,
    diagnostics,
    onRunGroupBy
}: GroupByTabProps) {
    const [selectedGroupCol, setSelectedGroupCol] = useState<string>("");
    const [selectedTargetCol, setSelectedTargetCol] = useState<string>("");
    const [selectedAggFunc, setSelectedAggFunc] = useState<string>("mean");

    const handleRun = () => {
        if (!selectedGroupCol || !selectedTargetCol) return;
        onRunGroupBy({
            group_col: selectedGroupCol,
            target_col: selectedTargetCol,
            agg_func: selectedAggFunc
        });
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
                <h3 className="font-bold mb-4 flex items-center gap-2"><FolderKanban className="text-slate-600 w-5 h-5"/> 分組匯總分析 (GroupBy Summary)</h3>
                <p className="text-sm text-slate-500 mb-4">依類別欄位分組，計算數值欄位的統計摘要</p>

                <div className="flex gap-4 items-end flex-wrap">
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold text-slate-500">分組欄位 (Group)</label>
                        <select
                            className="border rounded px-2 py-1 text-sm bg-white h-9 min-w-[150px]"
                            value={selectedGroupCol}
                            onChange={(e) => setSelectedGroupCol(e.target.value)}
                        >
                            <option value="">選擇分組欄位</option>
                            {diagnostics?.quality_report.map(c => (
                                <option key={c.column} value={c.column}>{c.column} ({c.dtype})</option>
                            ))}
                        </select>
                    </div>
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold text-slate-500">統計目標 (Target)</label>
                        <select
                            className="border rounded px-2 py-1 text-sm bg-white h-9 min-w-[150px]"
                            value={selectedTargetCol}
                            onChange={(e) => setSelectedTargetCol(e.target.value)}
                        >
                            <option value="">選擇統計目標</option>
                            {diagnostics?.quality_report
                                .filter(c => c.dtype.includes("int") || c.dtype.includes("float"))
                                .map(c => (
                                    <option key={c.column} value={c.column}>{c.column} ({c.dtype})</option>
                                ))
                            }
                        </select>
                    </div>
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold text-slate-500">聚合方式 (Agg)</label>
                        <select
                            className="border rounded px-2 py-1 text-sm bg-white h-9 min-w-[100px]"
                            value={selectedAggFunc}
                            onChange={(e) => setSelectedAggFunc(e.target.value)}
                        >
                            <option value="mean">平均值 (Mean)</option>
                            <option value="sum">加總 (Sum)</option>
                            <option value="median">中位數 (Median)</option>
                            <option value="count">計數 (Count)</option>
                            <option value="min">最小值 (Min)</option>
                            <option value="max">最大值 (Max)</option>
                        </select>
                    </div>
                    <Button
                        onClick={handleRun}
                        className="bg-purple-600 hover:bg-purple-700 h-9"
                        disabled={processing || !selectedGroupCol || !selectedTargetCol}
                    >
                        <Play size={14} className="mr-2"/> 執行分組彙總
                    </Button>
                </div>
            </Card>

            {processing ? (
                <Card className="p-12 h-64 animate-pulse bg-slate-100" />
            ) : edaResults && Array.isArray(edaResults.result_data) && edaResults.result_data.length > 0 ? (
                <div className="space-y-6">
                    {/* GroupBy Results */}
                    <Card className="p-6">
                        <h3 className="font-bold mb-4">分組彙總結果</h3>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                    <thead>
                                        <tr className="border-b bg-slate-50">
                                            {Object.keys(edaResults.result_data[0] || {}).map(k => (
                                                <th key={k} className="p-2 text-left">{k}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {edaResults.result_data.map((row, idx) => (
                                            <tr key={idx} className="border-b hover:bg-slate-50">
                                                {Object.values(row as Record<string, unknown>).map((v, i) => (
                                                    <td key={i} className="p-2">{typeof v === 'number' ? v.toLocaleString() : String(v)}</td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            <div className="h-64">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={edaResults.result_data}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey={Object.keys(edaResults.result_data[0] || {})[0]} fontSize={10} />
                                        <YAxis fontSize={10} />
                                        <Tooltip />
                                        <Bar dataKey={Object.keys(edaResults.result_data[0] || {})[1]} fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </Card>
                </div>
            ) : null}
        </div>
    );
}
