"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { transformVariable, getColumnData } from "@/lib/api";
import dynamic from "next/dynamic";
import { Wand2, Sparkles, Box, BarChart3 } from "lucide-react";

// Plotly component (client-side only)
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false, loading: () => <div className="p-10 text-center text-slate-400">Loading Plotly...</div> }) as React.ComponentType<{ data: unknown[]; layout: unknown; useResizeHandler?: boolean; className?: string; config?: unknown }>;

interface AdvancedTabProps {
    selectedDoc: string | null;
    filePath: string | null;
    numericColumns: string[];
    allColumns: string[];
}

export function AdvancedTab({ selectedDoc, filePath, numericColumns, allColumns }: AdvancedTabProps) {
    const [processing, setProcessing] = useState(false);
    
    // Synthesis State
    const [synthConfig, setSynthConfig] = useState({ name: "", expression: "" });
    const [synthHistory, setSynthHistory] = useState<string[]>([]);
    const [synthesizedCols, setSynthesizedCols] = useState<string[]>([]); // Track new columns

    // Plot State
    const [plotConfig, setPlotConfig] = useState<{ x: string; y: string; z: string; color: string }>({ x: "", y: "", z: "", color: "" });
    const [plotData, setPlotData] = useState<{ data: unknown[]; layout: unknown } | null>(null);

    // Helpers
    const getNumericCols = () => [...numericColumns, ...synthesizedCols];
    const getAllCols = () => [...allColumns, ...synthesizedCols];

    // Handlers
    const handleSynthesize = async () => {
        if (!selectedDoc || !filePath || !synthConfig.name || !synthConfig.expression) return;
        setProcessing(true);
        try {
            const res = await transformVariable({
                file_path: filePath,
                new_column: synthConfig.name,
                expression: synthConfig.expression
            });

            if (res.success) {
                setSynthesizedCols(prev => {
                    if (prev.includes(res.new_column)) return prev;
                    return [...prev, res.new_column];
                });
                setSynthHistory(prev => [...prev, `${synthConfig.name} = ${synthConfig.expression}`]);
                setSynthConfig({ name: "", expression: "" }); 
            }
        } catch (err) {
            console.error("Synthesis failed", err);
        } finally {
            setProcessing(false);
        }
    };

    const handlePlot3D = async () => {
        if (!selectedDoc || !filePath || !plotConfig.x || !plotConfig.y || !plotConfig.z) return;
        setProcessing(true);
        try {
            const rCols = [plotConfig.x, plotConfig.y, plotConfig.z];
            if (plotConfig.color) rCols.unshift(plotConfig.color); 

            const res = await getColumnData({
                file_path: filePath,
                columns: rCols
            });

            // Format for Plotly 3D Scatter
            if (res[plotConfig.x] && res[plotConfig.y] && res[plotConfig.z]) {
                 const trace = {
                    x: res[plotConfig.x],
                    y: res[plotConfig.y],
                    z: res[plotConfig.z],
                    mode: 'markers',
                    marker: {
                        size: 5,
                        color: plotConfig.color ? res[plotConfig.color] : '#1f77b4',
                        colorscale: 'Viridis',
                        opacity: 0.8,
                        showscale: true
                    },
                    type: 'scatter3d',
                    text: plotConfig.color ? res[plotConfig.color] : undefined,
                    name: 'Data Points'
                };
                
                const layout = {
                    scene: {
                        xaxis: { title: plotConfig.x },
                        yaxis: { title: plotConfig.y },
                        zaxis: { title: plotConfig.z },
                    },
                    margin: { l: 0, r: 0, b: 0, t: 0 },
                    height: 500,
                    width: '100%' 
                };

                setPlotData({ data: [trace], layout: layout });
            }
        } catch (err) {
            console.error("Plot 3D failed", err);
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

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Variable Synthesis Section */}
            <Card className="p-6">
                <h3 className="font-bold mb-4 flex items-center gap-2">
                    <Wand2 className="text-violet-600 w-5 h-5"/> 變數合成 (Variable Synthesis)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-xs font-medium">新變數名稱 (New Variable Name)</label>
                            <input 
                                type="text" 
                                className="w-full text-sm p-2 border rounded"
                                placeholder="e.g. Ratio, Sum"
                                value={synthConfig.name}
                                onChange={e => setSynthConfig({...synthConfig, name: e.target.value})}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-medium">運算公式 (Formula)</label>
                            <input 
                                type="text" 
                                className="w-full text-sm p-2 border rounded font-mono"
                                placeholder="e.g. ColA / ColB"
                                value={synthConfig.expression}
                                onChange={e => setSynthConfig({...synthConfig, expression: e.target.value})}
                            />
                            <p className="text-[10px] text-slate-400">支援基本運算 (+, -, *, /) 與 numpy 函數 (如 log, exp)。請使用欄位原始名稱。</p>
                        </div>
                        <Button onClick={handleSynthesize} disabled={processing} className="w-full bg-violet-600 hover:bg-violet-700">
                            <Sparkles size={16} className="mr-2"/> 建立新變數
                        </Button>
                    </div>
                    <div className="bg-slate-50 p-4 rounded-lg border">
                        <h4 className="text-xs font-bold mb-2">已建立的變數</h4>
                        {synthesizedCols.length === 0 ? (
                            <p className="text-xs text-slate-400">尚無合成變數</p>
                        ) : (
                            <ul className="text-xs space-y-1">
                                {synthHistory.map((h, i) => (
                                    <li key={i} className="font-mono text-slate-600">• {h}</li>
                                ))}
                            </ul>
                        )}
                    </div>
                </div>
            </Card>

            {/* 3D Plotting Section */}
            <Card className="p-6">
                <h3 className="font-bold mb-4 flex items-center gap-2">
                    <Box className="text-blue-600 w-5 h-5"/> 3D 視覺化 (Interactive 3D Plot)
                </h3>
                <div className="flex flex-col md:flex-row gap-6">
                    <div className="w-full md:w-1/4 space-y-4">
                        <div className="space-y-2">
                            <label className="text-xs font-medium">X 軸</label>
                            <select 
                                className="w-full text-xs p-2 border rounded"
                                value={plotConfig.x}
                                onChange={e => setPlotConfig({...plotConfig, x: e.target.value})}
                            >
                                <option value="">選擇欄位...</option>
                                {getNumericCols().map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-medium">Y 軸</label>
                            <select 
                                className="w-full text-xs p-2 border rounded"
                                value={plotConfig.y}
                                onChange={e => setPlotConfig({...plotConfig, y: e.target.value})}
                            >
                                <option value="">選擇欄位...</option>
                                {getNumericCols().map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-medium">Z 軸</label>
                            <select 
                                className="w-full text-xs p-2 border rounded"
                                value={plotConfig.z}
                                onChange={e => setPlotConfig({...plotConfig, z: e.target.value})}
                            >
                                <option value="">選擇欄位...</option>
                                {getNumericCols().map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-medium">顏色 (Color)</label>
                            <select 
                                className="w-full text-xs p-2 border rounded"
                                value={plotConfig.color}
                                onChange={e => setPlotConfig({...plotConfig, color: e.target.value})}
                            >
                                <option value="">無</option>
                                {getAllCols().map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                        <Button onClick={handlePlot3D} disabled={processing} className="w-full bg-blue-600 hover:bg-blue-700">
                            <BarChart3 size={16} className="mr-2"/> 繪製 3D 圖
                        </Button>
                    </div>

                    <div className="w-full md:w-3/4 min-h-[500px] border rounded bg-white flex items-center justify-center">
                        {plotData ? (
                            <Plot
                                data={plotData.data}
                                layout={plotData.layout}
                                useResizeHandler
                                className="w-full h-full"
                            />
                        ) : (
                            <div className="text-slate-300 text-center flex flex-col items-center">
                                <Box size={48} className="mb-2"/>
                                <p>請設定軸並點擊繪製</p>
                            </div>
                        )}
                    </div>
                </div>
            </Card>
        </div>
    );
}
