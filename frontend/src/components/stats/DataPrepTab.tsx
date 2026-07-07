"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { imputeMissing, encodeVariable, transformVariable, meltData, MeltResponse, DiagnosticResponse, DataQualityItem } from "@/lib/api";
import {
    Sparkles,
    Eraser,
    Binary,
    Calculator,
    CheckCircle2,
    FlipVertical2,
    Download
} from "lucide-react";

interface DataPrepTabProps {
    selectedDoc: string | null;
    filePath: string | null;
    diagnostics: DiagnosticResponse | null;
}

export function DataPrepTab({ selectedDoc, filePath, diagnostics }: DataPrepTabProps) {
    const [processing, setProcessing] = useState(false);
    const [resultMsg, setResultMsg] = useState<string | null>(null);

    // Impute
    const [imputeConfig, setImputeConfig] = useState<{ col: string; method: string }>({ col: "", method: "mean" });
    
    // Encode
    const [encodeConfig, setEncodeConfig] = useState<{ col: string; method: string }>({ col: "", method: "label" });

    // Synthesis
    const [synthConfig, setSynthConfig] = useState({ name: "", expression: "" });

    // Melt (wide to long)
    const [meltIdVars, setMeltIdVars] = useState<string[]>([]);
    const [meltValueVars, setMeltValueVars] = useState<string[]>([]);
    const [meltResult, setMeltResult] = useState<MeltResponse | null>(null);

    const handleImpute = async () => {
        if (!filePath || !imputeConfig.col) return;
        setProcessing(true);
        try {
            const res = await imputeMissing({
                file_path: filePath,
                column: imputeConfig.col,
                method: imputeConfig.method as "mean" | "median" | "mode" | "constant"
            });
            setResultMsg(res.message);
        } catch (err: unknown) {
            console.error(err);
            setResultMsg("Error: " + (err instanceof Error ? err.message : String(err)));
        } finally {
            setProcessing(false);
        }
    };

    const handleEncode = async () => {
        if (!filePath || !encodeConfig.col) return;
        setProcessing(true);
        try {
            const res = await encodeVariable({
                file_path: filePath,
                column: encodeConfig.col,
                method: encodeConfig.method as "label" | "onehot"
            });
            setResultMsg(res.message);
        } catch (err: unknown) {
            console.error(err);
            setResultMsg("Error: " + (err instanceof Error ? err.message : String(err)));
        } finally {
            setProcessing(false);
        }
    };

    const handleSynthesize = async () => {
        if (!filePath || !synthConfig.name || !synthConfig.expression) return;
        setProcessing(true);
        try {
            const res = await transformVariable({
                file_path: filePath,
                new_column: synthConfig.name,
                expression: synthConfig.expression
            });
            if (res.success) {
                setResultMsg(`Successfully created variable: ${res.new_column}`);
            }
        } catch (err: unknown) {
             console.error(err);
             setResultMsg("Error: " + (err instanceof Error ? err.message : String(err)));
        } finally {
            setProcessing(false);
        }
    };

    const handleMelt = async () => {
        if (!filePath || meltIdVars.length === 0) return;
        setProcessing(true);
        try {
            const res = await meltData({
                file_path: filePath,
                id_vars: meltIdVars,
                value_vars: meltValueVars,
            });
            setMeltResult(res);
            setResultMsg(`Melt 完成：共 ${res.total_rows} 列（預覽前 ${res.data.length} 列）`);
        } catch (err: unknown) {
            console.error(err);
            setResultMsg("Error: " + (err instanceof Error ? err.message : String(err)));
        } finally {
            setProcessing(false);
        }
    };

    const downloadMeltCsv = () => {
        if (!meltResult || meltResult.data.length === 0) return;
        const headers = Object.keys(meltResult.data[0]);
        const csv = [
            headers.join(","),
            ...meltResult.data.map(row =>
                headers.map(h => {
                    const v = row[h];
                    const s = v === null ? "" : String(v);
                    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
                }).join(",")
            ),
        ].join("\n");
        const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "melted_data.csv";
        a.click();
        URL.revokeObjectURL(url);
    };

    if (!selectedDoc) {
        return (
            <Card className="p-12 text-center opacity-40">
                <p>請先選擇數據文件</p>
            </Card>
        );
    }

    const catCols = diagnostics?.quality_report
        .filter((c: DataQualityItem) => c.dtype.includes("object") || c.dtype.includes("str") ||  c.dtype.includes("category"))
        .map((c: DataQualityItem) => c.column) || [];

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* 1. Imputation */}
                <Card className="p-6 border-t-4 border-t-orange-400">
                    <h3 className="font-bold mb-4 flex items-center gap-2 text-slate-700">
                        <Eraser className="text-orange-500 w-5 h-5"/> 缺失值處理 (Imputation)
                    </h3>
                    <div className="space-y-4">
                        <div className="space-y-1">
                            <label className="text-xs font-semibold text-slate-500">選擇欄位</label>
                            <select 
                                className="w-full text-sm p-2 border rounded bg-white"
                                value={imputeConfig.col}
                                onChange={e => setImputeConfig({...imputeConfig, col: e.target.value})}
                            >
                                <option value="">選擇...</option>
                                {diagnostics?.quality_report.filter((c: DataQualityItem) => c.missing_count > 0).map((c: DataQualityItem) => (
                                    <option key={c.column} value={c.column}>{c.column} ({c.missing_count} missing)</option>
                                ))}
                            </select>
                            {diagnostics?.quality_report.filter((c: DataQualityItem) => c.missing_count > 0).length === 0 && (
                                <p className="text-[10px] text-green-600 flex items-center gap-1"><CheckCircle2 size={10}/> 無缺失值</p>
                            )}
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs font-semibold text-slate-500">填補方式</label>
                            <select 
                                className="w-full text-sm p-2 border rounded bg-white"
                                value={imputeConfig.method}
                                onChange={e => setImputeConfig({...imputeConfig, method: e.target.value})}
                            >
                                <option value="mean">平均值 (Mean) - 數值</option>
                                <option value="median">中位數 (Median) - 數值</option>
                                <option value="mode">眾數 (Mode) - 類別/數值</option>
                                <option value="constant">補零/Missing (Constant)</option>
                            </select>
                        </div>
                        <Button 
                            onClick={handleImpute} 
                            disabled={processing || !imputeConfig.col} 
                            className="w-full bg-orange-500 hover:bg-orange-600 text-white"
                        >
                            執行填補
                        </Button>
                    </div>
                </Card>

                {/* 2. Encoding */}
                <Card className="p-6 border-t-4 border-t-blue-400">
                    <h3 className="font-bold mb-4 flex items-center gap-2 text-slate-700">
                        <Binary className="text-blue-500 w-5 h-5"/> 變數編碼 (Encoding)
                    </h3>
                    <div className="space-y-4">
                         <div className="space-y-1">
                            <label className="text-xs font-semibold text-slate-500">選擇類別欄位</label>
                            <select 
                                className="w-full text-sm p-2 border rounded bg-white"
                                value={encodeConfig.col}
                                onChange={e => setEncodeConfig({...encodeConfig, col: e.target.value})}
                            >
                                <option value="">選擇...</option>
                                {catCols.map(c => (
                                    <option key={c} value={c}>{c}</option>
                                ))}
                            </select>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs font-semibold text-slate-500">編碼方式</label>
                            <select 
                                className="w-full text-sm p-2 border rounded bg-white"
                                value={encodeConfig.method}
                                onChange={e => setEncodeConfig({...encodeConfig, method: e.target.value})}
                            >
                                <option value="label">標籤編碼 (Label Encoding) - 0,1,2...</option>
                                <option value="onehot">獨熱編碼 (One-Hot) - 0/1 啞變數</option>
                            </select>
                        </div>
                        <Button 
                            onClick={handleEncode} 
                            disabled={processing || !encodeConfig.col} 
                            className="w-full bg-blue-500 hover:bg-blue-600 text-white"
                        >
                            執行編碼
                        </Button>
                    </div>
                </Card>

                {/* 3. Synthesis */}
                <Card className="p-6 border-t-4 border-t-purple-400">
                    <h3 className="font-bold mb-4 flex items-center gap-2 text-slate-700">
                        <Calculator className="text-purple-500 w-5 h-5"/> 變數衍生 (Derivation)
                    </h3>
                     <div className="space-y-4">
                         <div className="space-y-1">
                            <label className="text-xs font-semibold text-slate-500">新變數名稱</label>
                            <input 
                                type="text"
                                className="w-full text-sm p-2 border rounded"
                                placeholder="NewColumn"
                                value={synthConfig.name}
                                onChange={e => setSynthConfig({...synthConfig, name: e.target.value})}
                            />
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs font-semibold text-slate-500">計算公式 (支援 numpy)</label>
                            <input 
                                type="text"
                                className="w-full text-sm p-2 border rounded font-mono"
                                placeholder="ColA + ColB * 2"
                                value={synthConfig.expression}
                                onChange={e => setSynthConfig({...synthConfig, expression: e.target.value})}
                            />
                        </div>
                         <Button 
                            onClick={handleSynthesize} 
                            disabled={processing || !synthConfig.name} 
                            className="w-full bg-purple-500 hover:bg-purple-600 text-white"
                        >
                            建立變數
                        </Button>
                    </div>
                </Card>
            </div>

            {/* 4. Melt (Wide to Long) */}
            <Card className="p-6 border-t-4 border-t-teal-400">
                <h3 className="font-bold mb-2 flex items-center gap-2 text-slate-700">
                    <FlipVertical2 className="text-teal-500 w-5 h-5"/> 資料重塑：寬轉長 (Melt)
                </h3>
                <p className="text-xs text-slate-500 mb-4">將多個數值欄位融合為「變數/數值」兩欄的長表格式，適合後續分組與趨勢分析</p>
                <div className="space-y-3">
                    <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-500">識別欄位 (ID Vars，保留不動)</label>
                        <div className="flex flex-wrap gap-1.5">
                            {(diagnostics?.quality_report ?? []).map(c => (
                                <button
                                    key={c.column}
                                    onClick={() => setMeltIdVars(v => v.includes(c.column) ? v.filter(x => x !== c.column) : [...v, c.column])}
                                    className={`px-2 py-0.5 rounded-md text-xs border transition-all ${
                                        meltIdVars.includes(c.column)
                                            ? "bg-teal-100 text-teal-700 border-teal-300 font-bold"
                                            : "bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100"
                                    }`}
                                >
                                    {c.column}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-500">值欄位 (Value Vars，選填 = 其餘全部)</label>
                        <div className="flex flex-wrap gap-1.5">
                            {(diagnostics?.quality_report ?? []).filter(c => !meltIdVars.includes(c.column)).map(c => (
                                <button
                                    key={c.column}
                                    onClick={() => setMeltValueVars(v => v.includes(c.column) ? v.filter(x => x !== c.column) : [...v, c.column])}
                                    className={`px-2 py-0.5 rounded-md text-xs border transition-all ${
                                        meltValueVars.includes(c.column)
                                            ? "bg-teal-100 text-teal-700 border-teal-300 font-bold"
                                            : "bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100"
                                    }`}
                                >
                                    {c.column}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <Button
                            onClick={handleMelt}
                            disabled={processing || meltIdVars.length === 0}
                            className="bg-teal-500 hover:bg-teal-600 text-white"
                        >
                            執行寬轉長 (Melt)
                        </Button>
                        {meltResult && meltResult.data.length > 0 && (
                            <Button onClick={downloadMeltCsv} variant="secondary" className="gap-2">
                                <Download size={14}/> 下載 CSV
                            </Button>
                        )}
                    </div>
                    {meltResult && meltResult.data.length > 0 && (
                        <div className="overflow-x-auto max-h-64 overflow-y-auto border rounded">
                            <table className="w-full text-xs">
                                <thead className="sticky top-0">
                                    <tr className="border-b bg-slate-50">
                                        {Object.keys(meltResult.data[0]).map(k => (
                                            <th key={k} className="p-2 text-left whitespace-nowrap">{k}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {meltResult.data.slice(0, 100).map((row, idx) => (
                                        <tr key={idx} className="border-b hover:bg-slate-50">
                                            {Object.values(row).map((v, i) => (
                                                <td key={i} className="p-2 whitespace-nowrap">{v === null ? "-" : String(v)}</td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </Card>

            {/* Results Log */}
            {resultMsg && (
                <div className="bg-slate-800 text-green-400 p-4 rounded-lg font-mono text-xs flex items-center gap-2 animate-in slide-in-from-bottom-2">
                    <Sparkles size={14}/>
                    {resultMsg}
                </div>
            )}
        </div>
    );
}
