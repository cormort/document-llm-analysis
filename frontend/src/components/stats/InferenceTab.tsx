"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { DiagnosticResponse, StatTestResponse, getColumnData } from "@/lib/api";
import { Settings, Bot, Lightbulb, Telescope, BarChart3, Binary, Scale, AlertTriangle } from "lucide-react";

// Dynamic import for Plotly
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false }) as React.ComponentType<{ data: unknown[]; layout: unknown; useResizeHandler?: boolean; className?: string; config?: unknown }>;

interface InferenceTabProps {
    selectedDoc: string | null;
    filePath: string | null;
    processing: boolean;
    testResults: StatTestResponse | null;
    diagnostics: DiagnosticResponse | null;
    onRunTest: (type: "ttest" | "anova" | "shapiro" | "outliers" | "chi_square" | "mann_whitney" | "kruskal" | "wilcoxon") => void;
    onInterpret: () => void;
    isInterpreting: boolean;
    selectedInferenceCols: string[];
    setSelectedInferenceCols: (cols: string[]) => void;
}

// Helper component for Bento Grid Items
function BentoItem({ title, value, subtext, icon: Icon, highlight }: { title: string; value: string | number; subtext?: string; icon?: React.ElementType; highlight?: boolean }) {
    return (
        <div className={`relative overflow-hidden rounded-2xl p-5 transition-all duration-300 ${highlight ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200 ring-4 ring-indigo-50' : 'bg-white border border-slate-100 hover:shadow-md hover:border-slate-200'}`}>
            <div className="flex justify-between items-start mb-2">
                <span className={`text-[11px] font-bold uppercase tracking-wider ${highlight ? 'text-indigo-200' : 'text-slate-400'}`}>{title}</span>
                {Icon && <Icon size={16} className={highlight ? 'text-indigo-300' : 'text-slate-300'} />}
            </div>
            <div className="flex items-baseline gap-2">
                <span className={`text-2xl font-black tracking-tight ${highlight ? 'text-white' : 'text-slate-800'}`}>
                    {typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 4 }) : value}
                </span>
                {subtext && <span className={`text-xs font-medium ${highlight ? 'text-indigo-200' : 'text-slate-400'}`}>{subtext}</span>}
            </div>
             {/* Decorative blob for highlighted items */}
            {highlight && (
                 <div className="absolute -bottom-6 -right-6 w-24 h-24 bg-white/10 rounded-full blur-2xl" />
            )}
        </div>
    );
}

// Main Grid Component
function BentoResultGrid({ results }: { results: Record<string, unknown> }) {
    if (!results) return null;

    // Extract common metrics safely
    const pValue = results.p_value ?? results.P_Value;
    const isSig = results.is_significant as boolean | undefined;
    const statName = Object.keys(results).find(k => k.includes("statistic") || k.includes("stat")) || "Statistic";
    const statValue = results[statName] as string | number | null | undefined;
    
    // Determine dynamic items based on content
    const items = [];
    
    // 1. P-Value (Key Metric)
    if (typeof pValue === 'number') {
        items.push(
            <BentoItem 
                key="p-value"
                title="P-Value (顯著性)" 
                value={pValue < 0.001 ? "< 0.001" : pValue.toFixed(4)} 
                subtext={isSig ? "Significant" : "Not Significant"}
                highlight={isSig}
                icon={AlertTriangle}
            />
        );
    }

    // 2. Test Statistic
    if (statValue !== undefined && statValue !== null) {
        items.push(
            <BentoItem 
                key="stat"
                title={statName.replace(/_/g, " ")} 
                value={statValue} 
                icon={Binary}
            />
        );
    }

    // 3. Other numerical metrics (Mean, Median, etc.)
    Object.entries(results).forEach(([key, val]) => {
        if (["p_value", "P_Value", "is_significant", "is_normal", statName].includes(key)) return;
        if (typeof val === "number") {
             items.push(
                <BentoItem 
                    key={key}
                    title={key.replace(/_/g, " ")} 
                    value={val} 
                    icon={Scale} // Generic icon
                />
            );
        } else if (typeof val === "string" && val.length < 20) {
             items.push(
                <BentoItem 
                    key={key}
                    title={key.replace(/_/g, " ")} 
                    value={val} 
                />
            );
        }
    });

    return (
        <div className="grid grid-cols-2 gap-4">
            {items}
        </div>
    );
}

export function InferenceTab({
    selectedDoc,
    filePath,
    processing,
    testResults,
    diagnostics,
    onRunTest,
    onInterpret,
    isInterpreting,
    selectedInferenceCols,
    setSelectedInferenceCols
}: InferenceTabProps) {
    // ... (State logic same as before)
    const [activeCategory, setActiveCategory] = useState("parametric");
    const [plotData, setPlotData] = useState<Record<string, unknown>[]>([]);
    const [loadingPlot, setLoadingPlot] = useState(false);

    // Auto-fetch data for plotting when test results change & suggest comparison
    useEffect(() => {
        const fetchPlotData = async () => {
            if (!selectedDoc || !testResults || selectedInferenceCols.length < 1) return;
            
            // Only plot for comparison tests
             // Determine current test type from results structure context is hard without passing it back
             // We can infer or just plot if columns > 0
             
            // Simple heuristic: If we have multiple numeric cols, plot distribution
            setLoadingPlot(true);
            try {
                const dataMap = await getColumnData({
                    file_path: filePath || "", 
                    columns: selectedInferenceCols
                });
                
                // Transform for Plotly Boxplot
                const traces = selectedInferenceCols.map(col => ({
                    y: dataMap[col],
                    type: "box",
                    name: col,
                    boxpoints: "outliers",
                    jitter: 0.3,
                    pointpos: -1.8,
                    marker: { color: '#6366f1' }, // Indigo-500
                    fillcolor: 'rgba(99, 102, 241, 0.1)',
                    line: { width: 1.5 }
                }));
                setPlotData(traces);
            } catch (e) {
                console.error("Failed to fetch plot data", e);
            } finally {
                setLoadingPlot(false);
            }
        };

        if (testResults) {
            fetchPlotData();
        }
    }, [testResults, selectedDoc, selectedInferenceCols, filePath]); // Dependency on results triggers plot update

    if (!selectedDoc) {
        return (
            <Card className="p-12 text-center opacity-40">
                <p>請先選擇數據文件</p>
            </Card>
        );
    }

    // Filter columns based on active category intent
    const getAvailableColumns = () => {
        if (!diagnostics) return [];
        if (activeCategory === "categorical") {
            // Show Low Cardinality Categorical or Strings (Assuming categorical if dtype is object or unique < 50)
            return diagnostics.quality_report.filter(c => c.dtype === "object" || c.unique_count < 20);
        }
        // Default to Numeric
        return diagnostics.quality_report.filter(c => c.dtype.includes("int") || c.dtype.includes("float"));
    };

    const availableCols = getAvailableColumns();

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <Card className="p-0 overflow-hidden border-slate-200">
                <div className="p-4 bg-slate-50 border-b flex justify-between items-center">
                    <h3 className="font-bold text-slate-700 flex items-center gap-2">
                        <Scale className="w-5 h-5 text-blue-600" />
                        推論統計檢定 (Inferential Statistics)
                    </h3>
                </div>

                <div className="p-6">
                    <Tabs value={activeCategory} onValueChange={setActiveCategory} className="mb-6">
                        <TabsList className="grid w-full grid-cols-4 bg-slate-100 p-1">
                            <TabsTrigger value="parametric" className="text-xs">參數檢定 (Parametric)</TabsTrigger>
                            <TabsTrigger value="nonparametric" className="text-xs">無母數檢定 (Rank)</TabsTrigger>
                            <TabsTrigger value="categorical" className="text-xs">類別檢定 (Chi-Square)</TabsTrigger>
                            <TabsTrigger value="normality" className="text-xs">常態與異常 (Normality)</TabsTrigger>
                        </TabsList>
                        
                        <div className="mt-4 p-4 bg-slate-50 rounded-lg border border-slate-100">
                             <div className="mb-4">
                                <h4 className="text-xs font-bold text-slate-500 mb-2 flex items-center gap-2">
                                    <Binary size={12}/> 
                                    1. 選擇分析變數 ({activeCategory === 'categorical' ? '類別型' : '數值型'})
                                </h4>
                                <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
                                    {availableCols.length > 0 ? availableCols.map(c => (
                                        <label key={c.column} className={`flex items-center gap-1 text-xs px-2 py-1.5 rounded border cursor-pointer transition-all ${selectedInferenceCols.includes(c.column) ? 'bg-blue-100 border-blue-300 text-blue-700 font-medium' : 'bg-white border-slate-200 hover:bg-slate-50'}`}>
                                            <input
                                                type="checkbox"
                                                className="hidden"
                                                checked={selectedInferenceCols.includes(c.column)}
                                                onChange={(e) => {
                                                    if (e.target.checked) {
                                                        setSelectedInferenceCols([...selectedInferenceCols, c.column]);
                                                    } else {
                                                        setSelectedInferenceCols(selectedInferenceCols.filter(col => col !== c.column));
                                                    }
                                                }}
                                            />
                                            {selectedInferenceCols.includes(c.column) && <span className="text-blue-500">✓</span>}
                                            {c.column}
                                        </label>
                                    )) : (
                                        <p className="text-xs text-slate-400 italic">無符合此類型的欄位</p>
                                    )}
                                </div>
                            </div>

                            <div>
                                <h4 className="text-xs font-bold text-slate-500 mb-2 flex items-center gap-2">
                                    <Telescope size={12}/> 
                                    2. 選擇檢定方法
                                </h4>
                                <div className="flex flex-wrap gap-2">
                                    {activeCategory === "parametric" && (
                                        <>
                                            <Button variant="outline" size="sm" onClick={() => onRunTest("ttest")} disabled={selectedInferenceCols.length !== 2}>T-Test (雙樣本)</Button>
                                            <Button variant="outline" size="sm" onClick={() => onRunTest("anova")} disabled={selectedInferenceCols.length < 2}>ANOVA (多組)</Button>
                                        </>
                                    )}
                                    {activeCategory === "nonparametric" && (
                                        <>
                                            <Button variant="outline" size="sm" onClick={() => onRunTest("mann_whitney")} disabled={selectedInferenceCols.length !== 2}>Mann-Whitney U</Button>
                                            <Button variant="outline" size="sm" onClick={() => onRunTest("wilcoxon")} disabled={selectedInferenceCols.length !== 2}>Wilcoxon (Paired)</Button>
                                            <Button variant="outline" size="sm" onClick={() => onRunTest("kruskal")} disabled={selectedInferenceCols.length < 2}>Kruskal-Wallis</Button>
                                        </>
                                    )}
                                    {activeCategory === "categorical" && (
                                        <>
                                            <Button variant="outline" size="sm" onClick={() => onRunTest("chi_square")} disabled={selectedInferenceCols.length !== 2}>Chi-Square 獨立性檢定</Button>
                                        </>
                                    )}
                                    {activeCategory === "normality" && (
                                        <>
                                            <Button variant="outline" size="sm" onClick={() => onRunTest("shapiro")} disabled={selectedInferenceCols.length === 0}>Shapiro-Wilk 常態檢定</Button>
                                            <Button variant="outline" size="sm" onClick={() => onRunTest("outliers")} disabled={selectedInferenceCols.length === 0}>IQR 異常值偵測</Button>
                                        </>
                                    )}
                                </div>
                            </div>
                        </div>
                    </Tabs>

                    
                    {/* Results Section */}
                    {processing ? (
                        <div className="p-12 text-center animate-pulse flex flex-col items-center">
                            <Settings className="w-10 h-10 mb-2 animate-spin text-slate-400"/>
                            <p className="text-sm text-slate-500">正在進行統計檢定運算...</p>
                        </div>
                    ) : testResults ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in slide-in-from-bottom-4">
                            {/* Left: Visualization */}
                            <div className="space-y-4">
                                <Card className="p-4 h-full min-h-[350px] flex flex-col shadow-sm border-slate-200">
                                    <h4 className="font-bold text-xs text-slate-500 mb-4 flex items-center gap-2">
                                        <BarChart3 size={14} className="text-indigo-500"/> 數據分佈可視化 (Interactive)
                                    </h4>
                                    <div className="flex-1 w-full bg-slate-50/50 rounded-xl border border-slate-100 flex items-center justify-center overflow-hidden">
                                        {loadingPlot ? (
                                            <div className="text-xs text-slate-400 flex items-center gap-2"><Settings className="animate-spin" size={12}/> 載入圖表中...</div>
                                        ) : plotData.length > 0 ? (
                                            <Plot
                                                data={plotData}
                                                layout={{ 
                                                    autosize: true, 
                                                    margin: { t: 20, r: 20, l: 40, b: 30 },
                                                    showlegend: false,
                                                    paper_bgcolor: 'rgba(0,0,0,0)',
                                                    plot_bgcolor: 'rgba(0,0,0,0)',
                                                    height: 300,
                                                    font: { size: 10, color: '#64748b' }
                                                }}
                                                useResizeHandler
                                                className="w-full h-full"
                                                config={{displayModeBar: false}}
                                            />
                                        ) : (
                                            <p className="text-xs text-slate-300">無可用圖表數據</p>
                                        )}
                                    </div>
                                </Card>
                            </div>

                            {/* Right: Stats & AI */}
                            <div className="space-y-6">
                                {/* Bento Grid for Stats */}
                                <div className="space-y-2">
                                     <div className="flex justify-between items-center mb-1">
                                         <h4 className="font-bold text-xs text-slate-600 flex items-center gap-2"><Binary size={14} className="text-indigo-500"/> 檢定結果指標</h4>
                                         {!testResults.interpretation && !isInterpreting && (
                                            <Button onClick={onInterpret} size="sm" className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 rounded-full px-3 shadow-indigo-100 shadow-md">
                                                <Bot size={12} className="mr-1"/> AI 智能解讀
                                            </Button>
                                        )}
                                     </div>
                                     <BentoResultGrid results={testResults.test_results} />
                                </div>
                                
                                <div className="space-y-3">
                                    {isInterpreting && (
                                        <div className="p-4 bg-white/80 backdrop-blur border border-indigo-100 rounded-2xl shadow-lg shadow-indigo-50 animate-pulse flex items-center gap-3">
                                            <div className="p-2 bg-indigo-100 text-indigo-600 rounded-full">
                                                <Bot size={16} className="animate-bounce" />
                                            </div>
                                            <span className="text-xs font-bold text-indigo-600">AI 正在深度分析數據分佈與顯著性...</span>
                                        </div>
                                    )}
                                    
                                    {testResults.interpretation && (
                                        <Card className="p-5 bg-gradient-to-br from-indigo-50/50 via-white to-purple-50/50 border-indigo-100 shadow-xl shadow-indigo-50/50 rounded-2xl">
                                            <div className="flex items-center gap-2 mb-3 text-indigo-800">
                                                <div className="p-1.5 bg-amber-100 text-amber-600 rounded-lg">
                                                    <Lightbulb size={14} />
                                                </div>
                                                <span className="font-black text-sm tracking-tight">AI 深度洞察</span>
                                            </div>
                                            <div className="text-xs text-slate-600 leading-relaxed max-h-60 overflow-y-auto pr-2 custom-scrollbar">
                                                <MarkdownRenderer content={testResults.interpretation} />
                                            </div>
                                        </Card>
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-24 border-2 border-dashed border-slate-100 rounded-2xl bg-slate-50/50 m-4 hover:bg-slate-50 transition-colors">
                            <div className="p-4 bg-white rounded-full shadow-sm mb-4">
                                <Telescope className="w-8 h-8 text-slate-300"/>
                            </div>
                            <p className="text-slate-900 font-bold text-sm">統計檢定準備就緒</p>
                            <p className="text-xs text-slate-400 mt-1 max-w-xs text-center">請從上方選擇數據變數與檢定方法，AI 將自動協助您進行分析與解讀</p>
                        </div>
                    )}
                </div>
            </Card>
        </div>
    );
}
