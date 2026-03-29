"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, Cell, Legend
} from "recharts";
import { Network, Play, Settings, Compass, Layers, Loader2 } from "lucide-react";
import {
    performMultivariate,
    DiagnosticResponse,
    MultivariateResponse,
    MultivariateRequest
} from "@/lib/api";

interface MultivariateTabProps {
    selectedDoc: string | null;
    filePath: string | null;
    config?: any;
    diagnostics: DiagnosticResponse | null;
}

const COLORS = ['#6366f1', '#ec4899', '#14b8a6', '#f59e0b', '#8b5cf6', '#ef4444', '#10b981'];

export function MultivariateTab({ selectedDoc, filePath, config, diagnostics }: MultivariateTabProps) {
    const [analysisType, setAnalysisType] = useState<"pca" | "kmeans">("pca");
    const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
    const [nComponents, setNComponents] = useState(2);
    const [nClusters, setNClusters] = useState(3);
    const [processing, setProcessing] = useState(false);
    const [result, setResult] = useState<MultivariateResponse | null>(null);

    if (!selectedDoc || !filePath) {
        return (
            <Card className="p-12 text-center text-slate-500">
                請先從左側選擇一份文件以進行多變量分析。
            </Card>
        );
    }

    const numericCols = diagnostics?.quality_report
        .filter(c => c.dtype.includes('int') || c.dtype.includes('float'))
        .map(c => c.column) || [];

    const handleFeatureToggle = (col: string) => {
        if (selectedFeatures.includes(col)) {
            setSelectedFeatures(selectedFeatures.filter(f => f !== col));
        } else {
            setSelectedFeatures([...selectedFeatures, col]);
        }
    };

    const handleRunAnalysis = async () => {
        if (selectedFeatures.length < 2) {
            alert("多變量分析至少需要選擇 2 個特徵欄位！");
            return;
        }

        setProcessing(true);
        setResult(null);

        const req: MultivariateRequest = {
            file_path: filePath,
            analysis_type: analysisType,
            features: selectedFeatures,
            n_components: analysisType === "pca" ? nComponents : undefined,
            n_clusters: analysisType === "kmeans" ? nClusters : undefined,
            config
        };

        try {
            const res = await performMultivariate(req);
            setResult(res);
        } catch (error: any) {
            console.error("Multivariate analysis failed:", error);
            alert("分析失敗: " + error.message);
        } finally {
            setProcessing(false);
        }
    };

    // Helper functions for rendering charts
    const renderPCACharts = (data: MultivariateResponse) => {
        // Prepare variance data
        const varData = data.components_variance?.map((v, i) => ({
            name: `PC${i + 1}`,
            variance: v * 100
        })) || [];

        return (
            <div className="space-y-6">
                <div className="grid grid-cols-2 gap-6">
                    {/* PCA Scatter Plot */}
                    <Card className="p-6 bg-white shadow-sm border-slate-100 flex flex-col h-[350px]">
                        <h4 className="font-bold text-slate-700 mb-4 text-sm">主成分散佈圖 (PC1 vs PC2)</h4>
                        <div className="flex-1 min-h-0 w-full relative">
                            {data.n_components >= 2 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: -20 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                                        <XAxis type="number" dataKey="PC1" name="PC1" stroke="#94a3b8" fontSize={11} tickLine={false} />
                                        <YAxis type="number" dataKey="PC2" name="PC2" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                                        <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                                        <Scatter name="Data" data={data.data} fill="#6366f1" />
                                    </ScatterChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">
                                    此圖表需要至少 2 個主成分
                                </div>
                            )}
                        </div>
                    </Card>

                    {/* Explained Variance Bar Chart */}
                    <Card className="p-6 bg-white shadow-sm border-slate-100 flex flex-col h-[350px]">
                        <h4 className="font-bold text-slate-700 mb-4 text-sm">各成分解釋變異量 (%)</h4>
                        <div className="flex-1 min-h-0 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={varData} margin={{ top: 10, right: 10, bottom: 20, left: -20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                                    <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                                    <Tooltip formatter={(val: number) => val.toFixed(2) + '%'} />
                                    <Bar dataKey="variance" fill="#14b8a6" radius={[4, 4, 0, 0]} barSize={40} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </Card>
                </div>
                
                {data.feature_weights && (
                    <Card className="p-6 bg-white shadow-sm border-slate-100 overflow-x-auto">
                        <h4 className="font-bold text-slate-700 mb-4 text-sm">特徵組成權重 (Loadings)</h4>
                        <table className="w-full text-xs text-left">
                            <thead className="bg-slate-50 text-slate-500 uppercase font-black">
                                <tr>
                                    <th className="px-4 py-3 rounded-tl-xl border-b border-slate-200">Feature</th>
                                    {Object.keys(data.feature_weights).map(pc => (
                                        <th key={pc} className="px-4 py-3 border-b border-slate-200">{pc}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 text-slate-600 font-medium">
                                {selectedFeatures.map((feat, idx) => (
                                    <tr key={feat} className="hover:bg-slate-50/50">
                                        <td className="px-4 py-3 font-mono">{feat}</td>
                                        {Object.values(data.feature_weights!).map((weights, wIdx) => (
                                            <td key={wIdx} className="px-4 py-3">
                                                {weights[idx]?.toFixed(4)}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </Card>
                )}
            </div>
        );
    };

    const renderKMeansCharts = (data: MultivariateResponse) => {
        // Group data points by cluster for Scatter Plot Customization
        const clusters = new Set(data.data.map(d => d.cluster));
        const clusterArray = Array.from(clusters).sort();

        // Prepare data for centers Radar or Bar Chart (we will use BarChart for simplicity)
        const centerData = [];
        if (data.cluster_centers) {
            for (const feature of selectedFeatures) {
                const row: any = { feature };
                Object.keys(data.cluster_centers).forEach((clusterName, idx) => {
                    row[clusterName] = data.cluster_centers![clusterName][feature];
                });
                centerData.push(row);
            }
        }

        return (
            <div className="space-y-6">
                <div className="grid grid-cols-2 gap-6">
                    {/* KMeans Scatter Plot (PCA projected) */}
                    <Card className="p-6 bg-white shadow-sm border-slate-100 flex flex-col h-[350px]">
                        <h4 className="font-bold text-slate-700 mb-4 text-sm">集群分佈預覽 (投影至 2D 空白)</h4>
                        <div className="flex-1 min-h-0 w-full relative">
                            <ResponsiveContainer width="100%" height="100%">
                                <ScatterChart margin={{ top: 10, right: 30, bottom: 10, left: -20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                                    <XAxis type="number" dataKey="x" name="PC1/Feat1" stroke="#94a3b8" fontSize={11} tickLine={false} />
                                    <YAxis type="number" dataKey="y" name="PC2/Feat2" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                                    <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                                    <Legend iconType="circle" />
                                    {clusterArray.map((c, i) => (
                                        <Scatter 
                                            key={`cluster-${c}`} 
                                            name={`Cluster ${c}`} 
                                            data={data.data.filter(d => d.cluster === c)} 
                                            fill={COLORS[i % COLORS.length]} 
                                        />
                                    ))}
                                </ScatterChart>
                            </ResponsiveContainer>
                        </div>
                    </Card>

                    {/* Cluster Centers Profile */}
                    <Card className="p-6 bg-white shadow-sm border-slate-100 flex flex-col h-[350px]">
                        <h4 className="font-bold text-slate-700 mb-4 text-sm">群集特徵輪廓 (平均值)</h4>
                        <div className="flex-1 min-h-0 w-full relative overflow-hidden">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={centerData} margin={{ top: 10, right: 10, bottom: 20, left: -20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                                    <XAxis dataKey="feature" stroke="#94a3b8" fontSize={11} tickLine={false} />
                                    <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                                    <Tooltip />
                                    <Legend />
                                    {Object.keys(data.cluster_centers || {}).map((clusterName, idx) => (
                                        <Bar 
                                            key={clusterName} 
                                            dataKey={clusterName} 
                                            fill={COLORS[idx % COLORS.length]} 
                                            radius={[4, 4, 0, 0]} 
                                        />
                                    ))}
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </Card>
                </div>
            </div>
        );
    };

    return (
        <div className="flex gap-8 items-start relative h-full">
            {/* Left Panel: Configuration Map */}
            <div className="w-[300px] shrink-0 sticky top-8 space-y-4">
                <Card className="p-5 border-none shadow-lg bg-white/60 backdrop-blur ring-1 ring-slate-200/50">
                    <div className="flex items-center gap-2 mb-6">
                        <div className="p-1.5 bg-indigo-100 rounded text-indigo-600">
                            <Settings size={16} />
                        </div>
                        <h3 className="font-black text-sm uppercase tracking-widest text-slate-500">模型參數</h3>
                    </div>

                    <div className="space-y-6">
                        {/* Analysis Type */}
                        <div className="space-y-3">
                            <label className="text-xs font-bold text-slate-700">演算法類型</label>
                            <Tabs value={analysisType} onValueChange={(v) => { setAnalysisType(v as any); setResult(null); }} className="w-full">
                                <TabsList className="grid grid-cols-2 w-full p-1 bg-slate-100 h-auto rounded-lg">
                                    <TabsTrigger value="pca" className="text-xs py-2 rounded-md font-bold data-[state=active]:bg-white data-[state=active]:text-indigo-600"><Compass size={14} className="mr-1.5"/>PCA</TabsTrigger>
                                    <TabsTrigger value="kmeans" className="text-xs py-2 rounded-md font-bold data-[state=active]:bg-white data-[state=active]:text-indigo-600"><Layers size={14} className="mr-1.5"/>K-Means</TabsTrigger>
                                </TabsList>
                            </Tabs>
                        </div>

                        {/* Features Selection */}
                        <div className="space-y-3">
                            <label className="text-xs font-bold text-slate-700 flex justify-between items-center">
                                參與特徵
                                <span className="text-[10px] bg-slate-100 text-slate-500 py-0.5 px-2 rounded-full">{selectedFeatures.length} 選取</span>
                            </label>
                            <div className="bg-slate-50 border border-slate-100 rounded-lg p-2 max-h-[160px] overflow-y-auto space-y-1">
                                {numericCols.length === 0 ? (
                                    <div className="text-xs text-slate-400 p-2 text-center">無可用數值欄位</div>
                                ) : (
                                    numericCols.map(col => (
                                        <label key={col} className={`flex items-center gap-2 px-2 py-1.5 rounded text-xs cursor-pointer transition-colors ${selectedFeatures.includes(col) ? 'bg-indigo-50 text-indigo-700 font-bold' : 'hover:bg-slate-200/50 text-slate-600'}`}>
                                            <input 
                                                type="checkbox" 
                                                checked={selectedFeatures.includes(col)}
                                                onChange={() => handleFeatureToggle(col)}
                                                className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-600 w-3 h-3"
                                            />
                                            <span className="truncate">{col}</span>
                                        </label>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Algorithm Params */}
                        {analysisType === "pca" && (
                            <div className="space-y-3">
                                <label className="text-xs font-bold text-slate-700 flex justify-between items-center">
                                    主成分數量 (n_components)
                                    <span className="text-indigo-600">{nComponents}</span>
                                </label>
                                <input 
                                    type="range" 
                                    min="2" max={Math.max(2, selectedFeatures.length)} 
                                    value={nComponents}
                                    onChange={(e) => setNComponents(parseInt(e.target.value))}
                                    className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                                />
                                <p className="text-[10px] text-slate-400">降維後的維度數量</p>
                            </div>
                        )}

                        {analysisType === "kmeans" && (
                            <div className="space-y-3">
                                <label className="text-xs font-bold text-slate-700 flex justify-between items-center">
                                    分群數量 (k)
                                    <span className="text-indigo-600">{nClusters}</span>
                                </label>
                                <input 
                                    type="range" 
                                    min="2" max="10" 
                                    value={nClusters}
                                    onChange={(e) => setNClusters(parseInt(e.target.value))}
                                    className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                                />
                                <p className="text-[10px] text-slate-400">預期劃分的目標群集數量</p>
                            </div>
                        )}

                        <Button 
                            onClick={handleRunAnalysis}
                            disabled={processing || selectedFeatures.length < 2}
                            className={`w-full h-10 text-xs font-bold rounded-lg shadow-md transition-all ${processing ? 'bg-slate-100 text-slate-400' : 'bg-indigo-600 hover:bg-indigo-700 text-white hover:shadow-lg hover:-translate-y-0.5'}`}
                        >
                            {processing ? (
                                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> 計算中...</>
                            ) : (
                                <><Play className="mr-2 h-3.5 w-3.5" /> 執行分析</>
                            )}
                        </Button>
                    </div>
                </Card>
            </div>

            {/* Right Panel: Results View */}
            <div className="flex-1 w-full min-w-0">
                {!result && !processing && (
                    <div className="h-full flex flex-col items-center justify-center p-20 text-center opacity-60">
                        <Network size={64} className="text-slate-300 mb-6"/>
                        <h3 className="text-xl font-bold text-slate-400 mb-2">多變量分析 (Multivariate Analysis)</h3>
                        <p className="text-slate-400 max-w-sm text-sm">
                            請在左側選擇數值特徵，並調整演算法參數，最後點擊「執行分析」開始探索特徵之間的深層結構或分群輪廓。
                        </p>
                    </div>
                )}

                {processing && !result && (
                     <div className="h-full flex flex-col items-center justify-center p-20">
                        <Loader2 size={48} className="text-indigo-300 animate-spin mb-6" />
                        <h3 className="text-lg font-bold text-slate-500 mb-2">正在進行矩陣運算與 LLM 解析...</h3>
                        <p className="text-slate-400 text-sm">StandardScaler 準備中，分析模型運轉中</p>
                    </div>
                )}

                {result && (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        {analysisType === "pca" && renderPCACharts(result)}
                        {analysisType === "kmeans" && renderKMeansCharts(result)}

                        {result.interpretation && (
                            <Card className="p-8 bg-gradient-to-br from-indigo-900 via-slate-900 to-black text-white shadow-2xl border-none relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-8 opacity-5 transform translate-x-4 -translate-y-4 group-hover:scale-110 transition-transform duration-700">
                                    <Network size={120} />
                                </div>
                                <div className="relative z-10">
                                    <h4 className="flex items-center gap-2 font-black text-amber-400 mb-5 text-sm tracking-widest uppercase">
                                        <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                                        AI 深度洞察解析
                                    </h4>
                                    <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-p:text-slate-300 prose-strong:text-amber-200">
                                        {result.interpretation.split('\n').map((line, i) => (
                                            <p key={i} className="mb-2">{line}</p>
                                        ))}
                                    </div>
                                </div>
                            </Card>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
