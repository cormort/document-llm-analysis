"use client";

import { useEffect, useState } from "react";
import { getColumnData, DiagnosticResponse } from "@/lib/api";
import { useSliceStore, SliceFilter } from "@/stores/slice-store";
import { Filter, X, Loader2 } from "lucide-react";

interface Props {
    filePath: string | null;
    diagnostics: DiagnosticResponse | null;
    onFiltersChanged?: () => void;
}

// 全域資料切片：選擇欄位與值，過濾條件自動套用到所有統計分析
export function GlobalSliceBar({ filePath, diagnostics, onFiltersChanged }: Props) {
    const { filters, setFilters, clearFilters } = useSliceStore();
    const [expandedCol, setExpandedCol] = useState<string | null>(null);
    const [colValues, setColValues] = useState<Record<string, (string | number | boolean)[]>>({});
    const [loadingCol, setLoadingCol] = useState<string | null>(null);

    // 換檔案時清空切片
    useEffect(() => {
        clearFilters();
        setColValues({});
        setExpandedCol(null);
    }, [filePath, clearFilters]);

    if (!filePath || !diagnostics) return null;

    // 候選欄位：低基數的類別欄位（2~50 個唯一值）
    const candidateCols = diagnostics.quality_report
        .filter(c => c.unique_count >= 2 && c.unique_count <= 50)
        .map(c => c.column);

    if (candidateCols.length === 0) return null;

    const toggleColumn = async (col: string) => {
        if (expandedCol === col) {
            setExpandedCol(null);
            return;
        }
        setExpandedCol(col);
        if (!colValues[col]) {
            setLoadingCol(col);
            try {
                const res = await getColumnData({ file_path: filePath, columns: [col] });
                const uniq = Array.from(new Set((res[col] || []).filter(v => v !== null))) as (string | number | boolean)[];
                setColValues(prev => ({ ...prev, [col]: uniq }));
            } catch (e) {
                console.error("載入欄位值失敗", e);
            } finally {
                setLoadingCol(null);
            }
        }
    };

    const toggleValue = (col: string, val: string | number | boolean) => {
        const existing = filters.find(f => f.column === col);
        let next: SliceFilter[];
        if (!existing) {
            next = [...filters, { column: col, values: [val] }];
        } else {
            const values = existing.values.includes(val)
                ? existing.values.filter(v => v !== val)
                : [...existing.values, val];
            next = values.length === 0
                ? filters.filter(f => f.column !== col)
                : filters.map(f => f.column === col ? { ...f, values } : f);
        }
        setFilters(next);
        onFiltersChanged?.();
    };

    const isSelected = (col: string, val: string | number | boolean) =>
        filters.find(f => f.column === col)?.values.includes(val) ?? false;

    return (
        <div className="bg-white/70 backdrop-blur rounded-xl border border-slate-200/60 px-4 py-3 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
                <span className="flex items-center gap-1.5 text-xs font-bold text-slate-500 shrink-0">
                    <Filter size={13} className="text-indigo-500" /> 資料切片
                </span>
                {candidateCols.map(col => {
                    const active = filters.find(f => f.column === col);
                    return (
                        <button
                            key={col}
                            onClick={() => toggleColumn(col)}
                            className={`px-2.5 py-1 rounded-full text-xs font-bold border transition-all ${
                                active
                                    ? "bg-indigo-600 text-white border-indigo-600"
                                    : expandedCol === col
                                        ? "bg-indigo-50 text-indigo-600 border-indigo-200"
                                        : "bg-white text-slate-500 border-slate-200 hover:border-indigo-300 hover:text-indigo-600"
                            }`}
                        >
                            {col}{active ? ` (${active.values.length})` : ""}
                        </button>
                    );
                })}
                {filters.length > 0 && (
                    <button
                        onClick={() => { clearFilters(); onFiltersChanged?.(); }}
                        className="ml-auto flex items-center gap-1 text-xs font-bold text-rose-500 hover:text-rose-700 shrink-0"
                    >
                        <X size={12} /> 清除切片
                    </button>
                )}
            </div>

            {expandedCol && (
                <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-slate-100">
                    {loadingCol === expandedCol ? (
                        <span className="flex items-center gap-1.5 text-xs text-slate-400">
                            <Loader2 size={12} className="animate-spin" /> 載入 {expandedCol} 的值...
                        </span>
                    ) : (
                        (colValues[expandedCol] || []).map(val => (
                            <button
                                key={String(val)}
                                onClick={() => toggleValue(expandedCol, val)}
                                className={`px-2 py-0.5 rounded-md text-xs border transition-all ${
                                    isSelected(expandedCol, val)
                                        ? "bg-indigo-100 text-indigo-700 border-indigo-300 font-bold"
                                        : "bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100"
                                }`}
                            >
                                {String(val)}
                            </button>
                        ))
                    )}
                </div>
            )}

            {filters.length > 0 && (
                <p className="text-[10px] text-slate-400 font-medium">
                    ⚡ 切片生效中：所有分析（概況/探索/推論/多變量/建模）僅使用符合條件的資料列
                </p>
            )}
        </div>
    );
}
