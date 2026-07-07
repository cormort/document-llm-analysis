"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { performEDA, DiagnosticResponse } from "@/lib/api";
import { Grid3x3, Play, Loader2 } from "lucide-react";

interface PivotTabProps {
    selectedDoc: string | null;
    diagnostics: DiagnosticResponse | null;
}

// 多維度交叉透視表（如同 Excel 樞紐分析）
export function PivotTab({ selectedDoc, diagnostics }: PivotTabProps) {
    const [indexCols, setIndexCols] = useState<string[]>([]);
    const [columnCols, setColumnCols] = useState<string[]>([]);
    const [valueCols, setValueCols] = useState<string[]>([]);
    const [aggFunc, setAggFunc] = useState("mean");
    const [processing, setProcessing] = useState(false);
    const [rows, setRows] = useState<Record<string, unknown>[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    const allCols = diagnostics?.quality_report.map(c => c.column) ?? [];
    const numCols = diagnostics?.quality_report
        .filter(c => c.dtype.includes("int") || c.dtype.includes("float"))
        .map(c => c.column) ?? [];

    const toggle = (list: string[], set: (v: string[]) => void, col: string) =>
        set(list.includes(col) ? list.filter(c => c !== col) : [...list, col]);

    const run = async () => {
        if (!selectedDoc || indexCols.length === 0 || valueCols.length === 0) return;
        setProcessing(true);
        setError(null);
        try {
            const res = await performEDA({
                file_path: selectedDoc,
                analysis_type: "pivot",
                params: { index: indexCols, columns: columnCols, values: valueCols, agg: aggFunc },
                skip_interpretation: true,
            });
            setRows(res.result_data as Record<string, unknown>[]);
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
            setRows(null);
        } finally {
            setProcessing(false);
        }
    };

    if (!selectedDoc) {
        return (
            <Card className="p-12 text-center opacity-40">
                <p>請先選擇數據文件</p>
            </Card>
        );
    }

    const ColPicker = ({ label, selected, onToggle, candidates }: {
        label: string;
        selected: string[];
        onToggle: (col: string) => void;
        candidates: string[];
    }) => (
        <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-slate-500">{label}</label>
            <div className="flex flex-wrap gap-1.5">
                {candidates.map(col => (
                    <button
                        key={col}
                        onClick={() => onToggle(col)}
                        className={`px-2 py-0.5 rounded-md text-xs border transition-all ${
                            selected.includes(col)
                                ? "bg-indigo-100 text-indigo-700 border-indigo-300 font-bold"
                                : "bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100"
                        }`}
                    >
                        {col}
                    </button>
                ))}
            </div>
        </div>
    );

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <Card className="p-6 space-y-4">
                <h3 className="font-bold flex items-center gap-2"><Grid3x3 className="text-slate-600 w-5 h-5"/> 交叉透視表 (Pivot Table)</h3>
                <p className="text-sm text-slate-500">多維度交叉分析，如同 Excel 樞紐分析表</p>

                <ColPicker label="列 (Index)" selected={indexCols} onToggle={c => toggle(indexCols, setIndexCols, c)} candidates={allCols} />
                <ColPicker label="欄 (Columns，選填)" selected={columnCols} onToggle={c => toggle(columnCols, setColumnCols, c)} candidates={allCols} />
                <ColPicker label="值 (Values)" selected={valueCols} onToggle={c => toggle(valueCols, setValueCols, c)} candidates={numCols} />

                <div className="flex gap-4 items-end">
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold text-slate-500">匯總方式</label>
                        <select
                            className="border rounded px-2 py-1 text-sm bg-white h-9 min-w-[100px]"
                            value={aggFunc}
                            onChange={(e) => setAggFunc(e.target.value)}
                        >
                            <option value="mean">平均值 (Mean)</option>
                            <option value="sum">加總 (Sum)</option>
                            <option value="count">計數 (Count)</option>
                            <option value="min">最小值 (Min)</option>
                            <option value="max">最大值 (Max)</option>
                        </select>
                    </div>
                    <Button
                        onClick={run}
                        className="bg-indigo-600 hover:bg-indigo-700 h-9"
                        disabled={processing || indexCols.length === 0 || valueCols.length === 0}
                    >
                        {processing ? <Loader2 size={14} className="mr-2 animate-spin"/> : <Play size={14} className="mr-2"/>}
                        執行透視分析
                    </Button>
                </div>
                {error && <p className="text-xs text-rose-500">{error}</p>}
            </Card>

            {rows && rows.length > 0 && (
                <Card className="p-6">
                    <h3 className="font-bold mb-4">透視結果（{rows.length} 列）</h3>
                    <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                        <table className="w-full text-xs">
                            <thead className="sticky top-0">
                                <tr className="border-b bg-slate-50">
                                    {Object.keys(rows[0]).map(k => (
                                        <th key={k} className="p-2 text-left whitespace-nowrap">{k}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((row, idx) => (
                                    <tr key={idx} className="border-b hover:bg-slate-50">
                                        {Object.values(row).map((v, i) => (
                                            <td key={i} className="p-2 whitespace-nowrap">
                                                {typeof v === "number" ? v.toLocaleString() : v === null ? "-" : String(v)}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}
        </div>
    );
}
