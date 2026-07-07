"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { getColumnData, interpretStats, DiagnosticResponse, LLMConfig } from "@/lib/api";
import { useSliceStore } from "@/stores/slice-store";
import { ExportInterpretation } from "./ExportInterpretation";
import { PieChart, Play, Bot, Loader2 } from "lucide-react";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false }) as React.ComponentType<{
    data: unknown[]; layout: unknown; useResizeHandler?: boolean; className?: string; config?: unknown;
}>;

interface ChartsTabProps {
    selectedDoc: string | null;
    config: LLMConfig;
    diagnostics: DiagnosticResponse | null;
}

type ColData = Record<string, (string | number | boolean | null)[]>;

// ponytail: 沿用舊版 15 種圖型中的 10 種；Sunburst/Sankey/Gauge/Heatmap 需階層彙總或已由其他分頁涵蓋，先略
const CHART_TYPES = [
    { id: "bar", label: "長條圖 Bar" },
    { id: "line", label: "折線圖 Line" },
    { id: "area", label: "面積圖 Area" },
    { id: "pie", label: "圓餅圖 Pie" },
    { id: "scatter", label: "散佈圖 Scatter" },
    { id: "box", label: "盒鬚圖 Box" },
    { id: "violin", label: "小提琴圖 Violin" },
    { id: "histogram", label: "直方圖 Histogram" },
    { id: "funnel", label: "漏斗圖 Funnel" },
    { id: "radar", label: "雷達圖 Radar" },
] as const;

const COLOR_SCHEMES: Record<string, string[]> = {
    "預設 (Plotly)": ["#636efa", "#ef553b", "#00cc96", "#ab63fa", "#ffa15a", "#19d3f3", "#ff6692", "#b6e880"],
    "冷色調": ["#1e3a8a", "#1d4ed8", "#3b82f6", "#60a5fa", "#93c5fd", "#0e7490", "#06b6d4", "#67e8f9"],
    "暖色調": ["#7c2d12", "#c2410c", "#ea580c", "#f97316", "#fb923c", "#b91c1c", "#ef4444", "#f87171"],
    "大地色": ["#44403c", "#78716c", "#a8a29e", "#854d0e", "#a16207", "#ca8a04", "#4d7c0f", "#65a30d"],
};

export function ChartsTab({ selectedDoc, config, diagnostics }: ChartsTabProps) {
    const { filters } = useSliceStore();
    const [chartType, setChartType] = useState<string>("bar");
    const [xCol, setXCol] = useState("");
    const [yCols, setYCols] = useState<string[]>([]);
    const [colorCol, setColorCol] = useState("");
    const [scheme, setScheme] = useState("預設 (Plotly)");
    const [processing, setProcessing] = useState(false);
    const [plotData, setPlotData] = useState<unknown[] | null>(null);
    const [plotTitle, setPlotTitle] = useState("");
    const [rawData, setRawData] = useState<ColData | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [interpretation, setInterpretation] = useState<string | null>(null);
    const [interpreting, setInterpreting] = useState(false);

    const allCols = diagnostics?.quality_report.map(c => c.column) ?? [];
    const numCols = diagnostics?.quality_report
        .filter(c => c.dtype.includes("int") || c.dtype.includes("float"))
        .map(c => c.column) ?? [];
    const catCols = diagnostics?.quality_report
        .filter(c => c.unique_count <= 50)
        .map(c => c.column) ?? [];

    // 圖型對應的欄位需求
    const yIsMulti = ["bar", "line", "area", "scatter", "radar"].includes(chartType);
    const needsY = chartType !== "histogram";
    const xCandidates = chartType === "histogram" ? numCols : allCols;
    const yCandidates = numCols;
    const canColor = ["bar", "line", "scatter", "box", "violin", "histogram", "radar"].includes(chartType);

    const toggleY = (col: string) =>
        setYCols(yIsMulti
            ? (yCols.includes(col) ? yCols.filter(c => c !== col) : [...yCols, col])
            : [col]);

    const ready = chartType === "histogram" ? !!xCol : !!xCol && yCols.length > 0;

    const buildTraces = (data: ColData): unknown[] => {
        const colors = COLOR_SCHEMES[scheme];
        const x = data[xCol] ?? [];
        const groups = colorCol && data[colorCol]
            ? Array.from(new Set(data[colorCol].map(v => String(v))))
            : null;

        const pick = (col: string, group?: string) =>
            group
                ? (data[col] ?? []).filter((_, i) => String(data[colorCol]![i]) === group)
                : (data[col] ?? []);

        switch (chartType) {
            case "pie":
                return [{ type: "pie", labels: x, values: data[yCols[0]], marker: { colors }, hole: 0 }];
            case "funnel":
                return [{ type: "funnel", y: x, x: data[yCols[0]], marker: { color: colors[0] } }];
            case "histogram":
                return groups
                    ? groups.map((g, i) => ({ type: "histogram", x: pick(xCol, g), name: g, marker: { color: colors[i % colors.length] }, opacity: 0.7 }))
                    : [{ type: "histogram", x, marker: { color: colors[0] } }];
            case "box":
            case "violin":
                return groups
                    ? groups.map((g, i) => ({ type: chartType, y: pick(yCols[0], g), name: g, marker: { color: colors[i % colors.length] } }))
                    : [{ type: chartType, y: data[yCols[0]], x: xCol ? x : undefined, marker: { color: colors[0] } }];
            case "radar":
                return yCols.map((col, i) => ({
                    type: "scatterpolar", theta: x, r: data[col], fill: "toself", name: col,
                    line: { color: colors[i % colors.length] },
                }));
            case "scatter":
                if (groups) {
                    return groups.map((g, i) => ({
                        type: "scatter", mode: "markers", x: pick(xCol, g), y: pick(yCols[0], g), name: g,
                        marker: { color: colors[i % colors.length] },
                    }));
                }
                return yCols.map((col, i) => ({
                    type: "scatter", mode: "markers", x, y: data[col], name: col,
                    marker: { color: colors[i % colors.length] },
                }));
            case "line":
            case "area":
            case "bar":
            default:
                return yCols.map((col, i) => ({
                    type: chartType === "bar" ? "bar" : "scatter",
                    mode: chartType === "bar" ? undefined : "lines+markers",
                    fill: chartType === "area" ? "tozeroy" : undefined,
                    x, y: data[col], name: col,
                    marker: { color: colors[i % colors.length] },
                }));
        }
    };

    const draw = async () => {
        if (!selectedDoc || !ready) return;
        setProcessing(true);
        setError(null);
        setInterpretation(null);
        try {
            const cols = Array.from(new Set([xCol, ...yCols, colorCol].filter(Boolean)));
            const data = await getColumnData({ file_path: selectedDoc, columns: cols });
            setRawData(data);
            setPlotData(buildTraces(data));
            // 沿用舊版：把生效中的切片條件放進標題
            const filterSuffix = filters.length > 0
                ? ` (${filters.map(f => `${f.column}: ${f.values.slice(0, 3).join(", ")}${f.values.length > 3 ? "..." : ""}`).join(" | ")})`
                : "";
            setPlotTitle(`${CHART_TYPES.find(c => c.id === chartType)?.label ?? chartType}${filterSuffix}`);
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
            setPlotData(null);
        } finally {
            setProcessing(false);
        }
    };

    const interpret = async () => {
        if (!rawData) return;
        setInterpreting(true);
        try {
            // 給 AI 的摘要：每個數值欄的基本統計 + 前 20 筆
            const usedCols = Object.keys(rawData);
            const summaryLines = usedCols.map(col => {
                const vals = (rawData[col] ?? []).filter((v): v is number => typeof v === "number");
                if (vals.length === 0) return `${col}: 類別欄位，共 ${rawData[col]?.length ?? 0} 筆`;
                const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
                return `${col}: min=${Math.min(...vals)}, max=${Math.max(...vals)}, mean=${mean.toFixed(2)}, n=${vals.length}`;
            });
            const sample = usedCols.map(col => `${col}: [${(rawData[col] ?? []).slice(0, 20).join(", ")}]`).join("\n");

            const res = await interpretStats({
                context: "請從『計畫成本效益』與『政府財政負擔審查者』的觀點，針對此統計圖表資料提供關鍵發現、成因洞察、政策與營運建議（含財政衝擊評估）、具體後續行動方案，以及延伸分析建議與資料需求。",
                data_summary: `圖表類型: ${plotTitle}\n欄位摘要:\n${summaryLines.join("\n")}\n\n資料樣本 (前20筆):\n${sample}`.slice(0, 4000),
                test_type: "Custom Chart Analysis",
                config,
            });
            setInterpretation(res.interpretation);
        } catch (e) {
            console.error("AI 解讀失敗", e);
        } finally {
            setInterpreting(false);
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
            <Card className="p-6 space-y-4">
                <h3 className="font-bold flex items-center gap-2"><PieChart className="text-slate-600 w-5 h-5"/> 自定義圖表分析 (Chart Builder)</h3>

                <div className="flex flex-wrap gap-1.5">
                    {CHART_TYPES.map(ct => (
                        <button
                            key={ct.id}
                            onClick={() => { setChartType(ct.id); setPlotData(null); setYCols([]); setColorCol(""); }}
                            className={`px-2.5 py-1 rounded-full text-xs font-bold border transition-all ${
                                chartType === ct.id
                                    ? "bg-indigo-600 text-white border-indigo-600"
                                    : "bg-white text-slate-500 border-slate-200 hover:border-indigo-300 hover:text-indigo-600"
                            }`}
                        >
                            {ct.label}
                        </button>
                    ))}
                </div>

                <div className="flex gap-6 flex-wrap">
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold text-slate-500">
                            {chartType === "histogram" ? "數值分佈 (X)" : chartType === "pie" ? "類別標籤" : chartType === "funnel" ? "階段標籤" : chartType === "radar" ? "維度軸" : "X 軸"}
                        </label>
                        <select className="border rounded px-2 py-1 text-sm bg-white h-9 min-w-[150px]" value={xCol} onChange={e => setXCol(e.target.value)}>
                            <option value="">選擇欄位</option>
                            {xCandidates.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                    </div>
                    {needsY && (
                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-semibold text-slate-500">{yIsMulti ? "Y 軸數值（可多選）" : "數值欄位"}</label>
                            <div className="flex flex-wrap gap-1.5 max-w-[500px]">
                                {yCandidates.map(col => (
                                    <button
                                        key={col}
                                        onClick={() => toggleY(col)}
                                        className={`px-2 py-0.5 rounded-md text-xs border transition-all ${
                                            yCols.includes(col)
                                                ? "bg-indigo-100 text-indigo-700 border-indigo-300 font-bold"
                                                : "bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100"
                                        }`}
                                    >
                                        {col}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                    {canColor && (
                        <div className="flex flex-col gap-1">
                            <label className="text-xs font-semibold text-slate-500">分組/顏色（選填）</label>
                            <select className="border rounded px-2 py-1 text-sm bg-white h-9 min-w-[130px]" value={colorCol} onChange={e => setColorCol(e.target.value)}>
                                <option value="">無</option>
                                {catCols.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                    )}
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold text-slate-500">配色</label>
                        <select className="border rounded px-2 py-1 text-sm bg-white h-9 min-w-[130px]" value={scheme} onChange={e => setScheme(e.target.value)}>
                            {Object.keys(COLOR_SCHEMES).map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                    </div>
                    <div className="flex items-end">
                        <Button onClick={draw} disabled={processing || !ready} className="bg-indigo-600 hover:bg-indigo-700 h-9">
                            {processing ? <Loader2 size={14} className="mr-2 animate-spin"/> : <Play size={14} className="mr-2"/>}
                            執行繪圖
                        </Button>
                    </div>
                </div>
                {error && <p className="text-xs text-rose-500">{error}</p>}
            </Card>

            {plotData && (
                <Card className="p-6 space-y-4">
                    <Plot
                        data={plotData}
                        layout={{
                            title: { text: plotTitle },
                            autosize: true,
                            height: 480,
                            margin: { t: 60, r: 30, b: 60, l: 60 },
                            barmode: "group",
                        }}
                        useResizeHandler
                        className="w-full"
                        config={{ displaylogo: false }}
                    />
                    {!interpretation && (
                        <div className="flex justify-end">
                            <Button onClick={interpret} disabled={interpreting} className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2">
                                {interpreting ? <Loader2 size={16} className="animate-spin"/> : <Bot size={16}/>}
                                AI 智慧解讀與政策建議
                            </Button>
                        </div>
                    )}
                    {interpretation && (
                        <Card className="p-6 bg-blue-900 text-blue-50 border-none shadow-xl space-y-3">
                            <h3 className="font-bold flex items-center gap-2">
                                <span className="p-1 bg-blue-700 rounded text-xs px-2">AI 圖表解讀</span>
                            </h3>
                            <MarkdownRenderer content={interpretation} />
                            <ExportInterpretation content={interpretation} title="圖表分析報告" />
                        </Card>
                    )}
                </Card>
            )}
        </div>
    );
}
