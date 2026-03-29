"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    LineChart, Line, ScatterChart, Scatter
} from "recharts";
import { TrendingUp, Play, Settings, Target, Binary, Activity, Layers } from "lucide-react";
import dynamic from "next/dynamic";
import {
    performRegression,
    performClassification,
    performTimeSeries,
    DiagnosticResponse,
    RegressionResponse,
    ClassificationResponse,
    TimeSeriesResponse,
    LLMConfig,
    DataQualityItem
} from "@/lib/api";

// Dynamic import for Plotly
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false }) as React.ComponentType<{ data: unknown[]; layout: unknown; useResizeHandler?: boolean; className?: string; config?: unknown }>;

interface ModelingTabProps {
    selectedDoc: string | null;
    filePath: string | null;
    config: LLMConfig;
    diagnostics: DiagnosticResponse | null;
}

export function ModelingTab({
    selectedDoc,
    filePath,
    config,
    diagnostics
}: ModelingTabProps) {

    const [activeTab, setActiveTab] = useState("regression");
    const [processing, setProcessing] = useState(false);
    
    // Regression State
    const [regressionResults, setRegressionResults] = useState<RegressionResponse | null>(null);
    const [regFeatures, setRegFeatures] = useState<string[]>([]);
    const [regTarget, setRegTarget] = useState<string>("");
    const [testSize] = useState<number>(0.2);

    // Classification State
    const [classResults, setClassResults] = useState<ClassificationResponse | null>(null);
    const [classFeatures, setClassFeatures] = useState<string[]>([]);
    const [classTarget, setClassTarget] = useState<string>("");

    // Time Series State
    const [timeSeriesResults, setTimeSeriesResults] = useState<TimeSeriesResponse | null>(null);
    const [selectedDateCol, setSelectedDateCol] = useState<string>("");
    const [selectedValueCol, setSelectedValueCol] = useState<string>("");
    const [forecastPeriods, setForecastPeriods] = useState<number>(12);

    const handleRunRegression = async () => {
        if (!selectedDoc || !filePath || regFeatures.length === 0 || !regTarget) return;
        setProcessing(true);
        setRegressionResults(null);
        try {
            const res = await performRegression({
                file_path: filePath,
                feature_cols: regFeatures,
                target_col: regTarget,
                test_size: testSize,
                config: config
            });
            setRegressionResults(res);
        } catch (err) {
            console.error("Regression failed", err);
        } finally {
            setProcessing(false);
        }
    };

    const handleRunClassification = async () => {
        if (!selectedDoc || !filePath || classFeatures.length === 0 || !classTarget) return;
        setProcessing(true);
        setClassResults(null);
        try {
            const res = await performClassification({
                file_path: filePath,
                feature_cols: classFeatures,
                target_col: classTarget,
                test_size: testSize,
                config: config
            });
            setClassResults(res);
        } catch (err) {
            console.error("Classification failed", err);
        } finally {
            setProcessing(false);
        }
    };

    const handleRunTimeSeries = async () => {
        if (!selectedDoc || !filePath || !selectedDateCol || !selectedValueCol) return;
        setProcessing(true);
        setTimeSeriesResults(null);
        try {
            const res = await performTimeSeries({
                file_path: filePath,
                date_col: selectedDateCol,
                value_col: selectedValueCol,
                forecast_periods: forecastPeriods,
                config: config
            });
            setTimeSeriesResults(res);
        } catch (err) {
            console.error(err);
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

    const numericCols = diagnostics?.quality_report.filter((c: DataQualityItem) => c.dtype.includes("int") || c.dtype.includes("float")) || [];
    const allCols = diagnostics?.quality_report || [];

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
             <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="grid w-full grid-cols-3 mb-6">
                    <TabsTrigger value="regression" className="flex items-center gap-2">
                         <TrendingUp size={14}/> 線性迴歸 (Regression)
                    </TabsTrigger>
                    <TabsTrigger value="classification" className="flex items-center gap-2">
                        <Target size={14}/> 分類預測 (Classification)
                    </TabsTrigger>
                    <TabsTrigger value="timeseries" className="flex items-center gap-2">
                        <Activity size={14}/> 時間序列 (Time Series)
                    </TabsTrigger>
                </TabsList>

                {/* --- Regression Tab --- */}
                <TabsContent value="regression" className="space-y-6">
                    <Card className="p-6 border-blue-100 bg-blue-50/30">
                         <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-3">
                                <label className="text-xs font-bold text-slate-500 flex items-center gap-1">
                                    <Target size={12}/> 預測目標 (Y) - 數值型
                                </label>
                                <select
                                    className="w-full border rounded-md p-2 text-sm bg-white shadow-sm"
                                    value={regTarget}
                                    onChange={(e) => setRegTarget(e.target.value)}
                                >
                                    <option value="">選擇目標變數...</option>
                                    {numericCols.map((c: DataQualityItem) => <option key={c.column} value={c.column}>{c.column}</option>)}
                                </select>
                            </div>
                            
                            <div className="space-y-3">
                                <label className="text-xs font-bold text-slate-500 flex items-center gap-1">
                                    <Layers size={12}/> 特徵變數 (X) - 數值型
                                </label>
                                <div className="p-3 bg-white rounded-md border text-sm h-32 overflow-y-auto shadow-sm">
                                    {numericCols.map((c: DataQualityItem) => (
                                         <label key={c.column} className="flex items-center gap-2 mb-1.5 cursor-pointer hover:bg-slate-50 p-1 rounded">
                                            <input
                                                type="checkbox"
                                                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                                checked={regFeatures.includes(c.column)}
                                                onChange={(e) => {
                                                    if (e.target.checked) setRegFeatures([...regFeatures, c.column]);
                                                    else setRegFeatures(regFeatures.filter(f => f !== c.column));
                                                }}
                                            />
                                            <span className={regFeatures.includes(c.column) ? "font-medium text-blue-700" : "text-slate-600"}>{c.column}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="flex justify-end mt-4">
                            <Button 
                                onClick={handleRunRegression} 
                                disabled={processing || !regTarget || regFeatures.length === 0}
                                className="bg-blue-600 hover:bg-blue-700 shadow-blue-200 shadow-lg"
                            >
                                {processing ? <Settings className="animate-spin mr-2" size={16}/> : <Play className="mr-2" size={16}/>}
                                執行迴歸分析
                            </Button>
                        </div>
                    </Card>

                    {regressionResults && (
                        <div className="animate-in slide-in-from-bottom-4 space-y-6">
                             {/* Metrics Grid */}
                             <div className="grid grid-cols-4 gap-4">
                                {[{ label: "R² Score", val: regressionResults.r2_score, color: "text-blue-600", bg: "bg-blue-50" },
                                  { label: "RMSE", val: regressionResults.rmse, color: "text-red-500", bg: "bg-red-50" },
                                  { label: "Intercept", val: regressionResults.intercept, color: "text-purple-600", bg: "bg-purple-50" },
                                  { label: "Samples", val: regressionResults.predictions.length, color: "text-slate-600", bg: "bg-slate-50" }]
                                  .map((m, i) => (
                                    <div key={i} className={`p-4 rounded-xl border border-slate-100 shadow-sm ${m.bg}`}>
                                        <div className="text-xs text-slate-500 font-bold uppercase">{m.label}</div>
                                        <div className={`text-2xl font-black ${m.color}`}>{typeof m.val === 'number' ? m.val.toFixed(4) : m.val}</div>
                                    </div>
                                ))}
                             </div>

                             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Coefficients */}
                                <Card className="p-4 h-[350px] flex flex-col">
                                    <h4 className="font-bold text-sm text-slate-700 mb-4">特徵重要性 (Feature Coefficients)</h4>
                                     <ResponsiveContainer width="100%" height="100%">
                                        <BarChart
                                            layout="vertical"
                                            data={Object.entries(regressionResults.coefficients)
                                                .map(([name, val]) => ({ name, value: val as number }))
                                                .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))}
                                            margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                            <XAxis type="number" fontSize={10}/>
                                            <YAxis dataKey="name" type="category" width={80} fontSize={10}/>
                                            <Tooltip />
                                            <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={20}/>
                                        </BarChart>
                                    </ResponsiveContainer>
                                </Card>
                                
                                {/* Pred vs Actual */}
                                <Card className="p-4 h-[350px] flex flex-col">
                                    <h4 className="font-bold text-sm text-slate-700 mb-4">預測值 vs 實際值</h4>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                                            <CartesianGrid strokeDasharray="3 3"/>
                                            <XAxis type="number" dataKey="actual" name="Actual" fontSize={10}>
                                            </XAxis>
                                            <YAxis type="number" dataKey="predicted" name="Predicted" fontSize={10}/>
                                            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                                            <Scatter name="Values" data={regressionResults.predictions.map((p, i) => ({ actual: regressionResults.actual[i], predicted: p }))} fill="#8884d8" />
                                        </ScatterChart>
                                    </ResponsiveContainer>
                                </Card>
                             </div>
                        </div>
                    )}
                </TabsContent>

                {/* --- Classification Tab --- */}
                <TabsContent value="classification" className="space-y-6">
                    <Card className="p-6 border-indigo-100 bg-indigo-50/30">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-3">
                                <label className="text-xs font-bold text-slate-500 flex items-center gap-1">
                                    <Target size={12}/> 分類目標 (Y) - 類別/二元
                                </label>
                                <select
                                    className="w-full border rounded-md p-2 text-sm bg-white shadow-sm"
                                    value={classTarget}
                                    onChange={(e) => setClassTarget(e.target.value)}
                                >
                                    <option value="">選擇目標變數...</option>
                                    {allCols.map((c: DataQualityItem) => <option key={c.column} value={c.column}>{c.column} ({c.dtype})</option>)}
                                </select>
                            </div>
                            
                            <div className="space-y-3">
                                <label className="text-xs font-bold text-slate-500 flex items-center gap-1">
                                    <Layers size={12}/> 特徵變數 (X) - 數值最適
                                </label>
                                <div className="p-3 bg-white rounded-md border text-sm h-32 overflow-y-auto shadow-sm">
                                    {numericCols.map((c: DataQualityItem) => (
                                         <label key={c.column} className="flex items-center gap-2 mb-1.5 cursor-pointer hover:bg-slate-50 p-1 rounded">
                                            <input
                                                type="checkbox"
                                                className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                                                checked={classFeatures.includes(c.column)}
                                                onChange={(e) => {
                                                    if (e.target.checked) setClassFeatures([...classFeatures, c.column]);
                                                    else setClassFeatures(classFeatures.filter(f => f !== c.column));
                                                }}
                                            />
                                            <span className={classFeatures.includes(c.column) ? "font-medium text-indigo-700" : "text-slate-600"}>{c.column}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="flex justify-end mt-4">
                            <Button 
                                onClick={handleRunClassification} 
                                disabled={processing || !classTarget || classFeatures.length === 0}
                                className="bg-indigo-600 hover:bg-indigo-700 shadow-indigo-200 shadow-lg"
                            >
                                {processing ? <Settings className="animate-spin mr-2" size={16}/> : <Binary className="mr-2" size={16}/>}
                                執行分類模型 (Logistic Regression)
                            </Button>
                        </div>
                    </Card>

                    {classResults && (
                        <div className="animate-in slide-in-from-bottom-4 space-y-6">
                            {/* Metrics Grid */}
                             <div className="grid grid-cols-4 gap-4">
                                {[{ label: "Accuracy", val: classResults.metrics.accuracy },
                                  { label: "Precision", val: classResults.metrics.precision },
                                  { label: "Recall", val: classResults.metrics.recall },
                                  { label: "F1 Score", val: classResults.metrics.f1 }]
                                  .map((m, i) => (
                                    <div key={i} className="p-4 rounded-xl border border-indigo-100 bg-white shadow-sm hover:shadow-md transition-shadow">
                                        <div className="text-xs text-slate-400 font-bold uppercase mb-1">{m.label}</div>
                                        <div className="text-2xl font-black text-indigo-900">{m.val.toFixed(4)}</div>
                                        <div className="w-full h-1 bg-slate-100 mt-2 rounded-full overflow-hidden">
                                            <div className="h-full bg-indigo-500" style={{width: `${m.val * 100}%`}}></div>
                                        </div>
                                    </div>
                                ))}
                             </div>

                             <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* Confusion Matrix */}
                                <Card className="p-4 min-h-[350px] flex flex-col justify-center items-center">
                                    <h4 className="font-bold text-sm text-slate-700 mb-4 w-full">混淆矩陣 (Confusion Matrix)</h4>
                                     <Plot
                                        data={[{
                                            z: classResults.confusion_matrix,
                                            x: classResults.classes.map(String),
                                            y: classResults.classes.map(String),
                                            type: 'heatmap',
                                            colorscale: 'Blues',
                                            showscale: true
                                        }]}
                                        layout={{
                                            width: 400,
                                            height: 300,
                                            title: '',
                                            xaxis: { title: 'Predicted' },
                                            yaxis: { title: 'Actual' },
                                            margin: { t: 20, r: 20, b: 40, l: 40 }
                                        }}
                                        config={{displayModeBar: false}}
                                     />
                                </Card>

                                {/* ROC Curve (if available) */}
                                {classResults.roc_curve ? (
                                    <Card className="p-4 min-h-[350px]">
                                        <h4 className="font-bold text-sm text-slate-700 mb-4">ROC Curve (AUC: {classResults.roc_curve.auc.toFixed(4)})</h4>
                                        <div className="h-[300px]">
                                             <ResponsiveContainer width="100%" height="100%">
                                                <LineChart data={classResults.roc_curve.fpr.map((f, i) => ({ fpr: f, tpr: classResults.roc_curve!.tpr[i] }))}>
                                                    <CartesianGrid strokeDasharray="3 3" />
                                                    <XAxis dataKey="fpr" type="number" label={{ value: 'False Positive Rate', position: 'insideBottom', offset: -5 }} />
                                                    <YAxis dataKey="tpr" type="number" label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft' }} />
                                                    <Tooltip />
                                                    <Line type="monotone" dataKey="tpr" stroke="#6366f1" dot={false} strokeWidth={2} />
                                                    <Line type="monotone" dataKey="fpr" stroke="#cbd5e1" dot={false} strokeDasharray="5 5" /> {/* Diagonal */}
                                                </LineChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </Card>
                                ) : (
                                    // Feature Importance for non-binary or fall-back
                                     <Card className="p-4 min-h-[350px]">
                                        <h4 className="font-bold text-sm text-slate-700 mb-4">特徵重要性</h4>
                                        <ResponsiveContainer width="100%" height="100%">
                                            <BarChart
                                                layout="vertical"
                                                data={classResults.feature_importance?.sort((a, b) => b.importance - a.importance).slice(0, 10)}
                                                margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                                            >
                                                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                                <XAxis type="number" fontSize={10}/>
                                                <YAxis dataKey="feature" type="category" width={100} fontSize={10}/>
                                                <Tooltip />
                                                <Bar dataKey="importance" fill="#818cf8" radius={[0, 4, 4, 0]} />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </Card>
                                )}
                             </div>
                        </div>
                    )}

                </TabsContent>

                {/* --- Time Series Tab --- */}
                <TabsContent value="timeseries" className="space-y-6">
                    <Card className="p-6 border-green-100 bg-green-50/30">
                        {/* Time Series Controls (Same as before but cleaner layout) */}
                         <div className="flex flex-wrap gap-4 items-end">
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500">日期欄位 (T)</label>
                                <select
                                    className="border rounded px-2 py-1.5 text-sm bg-white min-w-[200px]"
                                    value={selectedDateCol}
                                    onChange={(e) => setSelectedDateCol(e.target.value)}
                                >
                                    <option value="">選擇日期...</option>
                                    {allCols.map((c: DataQualityItem) => <option key={c.column} value={c.column}>{c.column} ({c.dtype})</option>)}
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500">數值欄位 (Y)</label>
                                <select
                                    className="border rounded px-2 py-1.5 text-sm bg-white min-w-[200px]"
                                    value={selectedValueCol}
                                    onChange={(e) => setSelectedValueCol(e.target.value)}
                                >
                                    <option value="">選擇數值...</option>
                                    {numericCols.map((c: DataQualityItem) => <option key={c.column} value={c.column}>{c.column}</option>)}
                                </select>
                            </div>
                             <div className="space-y-1">
                                <label className="text-xs font-bold text-slate-500">預測期數</label>
                                <input
                                    type="number"
                                    min="1"
                                    max="36"
                                    value={forecastPeriods}
                                    onChange={(e) => setForecastPeriods(parseInt(e.target.value) || 12)}
                                    className="border rounded px-2 py-1.5 text-sm bg-white w-24"
                                />
                            </div>
                            <Button
                                onClick={handleRunTimeSeries}
                                className="bg-green-600 hover:bg-green-700 h-9"
                                disabled={processing}
                            >
                                {processing ? <Settings className="animate-spin mr-2"/> : <Play className="mr-2" size={14}/>}
                                執行時序分析
                            </Button>
                        </div>
                    </Card>

                     {/* Time Series Results (Keep original logic but updated UI containers) */}
                    {timeSeriesResults && (
                        <div className="space-y-6 animate-in fade-in">
                             <Card className="p-4">
                                <h4 className="font-bold text-sm mb-4">原始數據與趨勢</h4>
                                <div className="h-64">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={timeSeriesResults.dates.map((d, i) => ({
                                            date: d,
                                            value: timeSeriesResults.values[i],
                                            trend: timeSeriesResults.trend[i]
                                        }))}>
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis dataKey="date" fontSize={10} tickFormatter={(v) => v.slice(0, 7)} />
                                            <YAxis fontSize={10} />
                                            <Tooltip />
                                            <Legend />
                                            <Line type="monotone" dataKey="value" stroke="#3b82f6" name="原始值" dot={false} />
                                            <Line type="monotone" dataKey="trend" stroke="#ef4444" name="趨勢" dot={false} strokeWidth={2} />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </Card>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <Card className="p-4">
                                    <h4 className="font-bold text-sm mb-4">預測結果 (Forecast)</h4>
                                     <div className="h-48">
                                         <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={[
                                                ...timeSeriesResults.dates.slice(-20).map((d, i) => ({
                                                    date: d,
                                                    actual: timeSeriesResults.values[timeSeriesResults.dates.length - 20 + i],
                                                    forecast: null
                                                })),
                                                ...timeSeriesResults.forecast_dates!.map((d, i) => ({
                                                    date: d,
                                                    actual: null,
                                                    forecast: timeSeriesResults.forecast![i]
                                                }))
                                            ]}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="date" fontSize={10} />
                                                <YAxis fontSize={10} />
                                                <Tooltip />
                                                <Legend />
                                                <Line type="monotone" dataKey="actual" stroke="#3b82f6" name="歷史" dot={false} />
                                                <Line type="monotone" dataKey="forecast" stroke="#10b981" name="預測" strokeDasharray="5 5" dot={false} strokeWidth={2} />
                                            </LineChart>
                                        </ResponsiveContainer>
                                     </div>
                                </Card>
                                <Card className="p-4">
                                    <h4 className="font-bold text-sm mb-4">季節性成分 (Seasonality)</h4>
                                    <div className="h-48">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={timeSeriesResults.dates.map((d, i) => ({
                                                date: d,
                                                seasonal: timeSeriesResults.seasonal[i]
                                            }))}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="date" fontSize={10} tickFormatter={(v) => v.slice(0, 7)} />
                                                <YAxis fontSize={10} />
                                                <Tooltip />
                                                <Line type="monotone" dataKey="seasonal" stroke="#f59e0b" name="季節性" dot={false} />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                </Card>
                            </div>
                        </div>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
}
