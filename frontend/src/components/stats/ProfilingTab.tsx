"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { 
    DiagnosticResponse, 
    getFieldAnalysis, 
    getFeatureSuggestions, 
    getDatasetAnalysis,
    LLMConfig,
    DataQualityItem
} from "@/lib/api";
import { useSettingsStore } from "@/stores/settings-store";
import { Loader2, Lightbulb, Microscope, Activity, BarChart3, Rocket, Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";

// Helper for type color
const getTypeColor = (dtype: string) => {
    if (dtype.includes("int") || dtype.includes("float")) return "bg-blue-100 text-blue-700 border-blue-200";
    if (dtype.includes("object") || dtype.includes("str")) return "bg-green-100 text-green-700 border-green-200";
    if (dtype.includes("date")) return "bg-purple-100 text-purple-700 border-purple-200";
    return "bg-slate-100 text-slate-700";
};

interface ProfilingTabProps {
    selectedDoc: string | null;
    processing: boolean;
    diagnostics: DiagnosticResponse | null;
}

export function ProfilingTab({ selectedDoc, processing, diagnostics }: ProfilingTabProps) {

    if (!selectedDoc) {
        return (
            <Card className="p-12 text-center opacity-40 border-dashed border-2 flex flex-col items-center">
                <BarChart3 size={64} className="mb-4 text-slate-300"/>
                <h3 className="text-xl font-bold">請先從左側選擇要分析的檔案</h3>
                <p className="text-sm mt-1">選定檔案後即可啟動自動化報表與診斷功能</p>
            </Card>
        );
    }

    if (processing) {
        return (
            <div className="space-y-6">
                <Card className="p-8 h-64 animate-pulse bg-slate-100" />
                <div className="grid grid-cols-2 gap-6">
                    <Card className="p-8 h-48 animate-pulse bg-slate-100" />
                    <Card className="p-8 h-48 animate-pulse bg-slate-100" />
                </div>
            </div>
        );
    }

    if (!diagnostics) {
        return (
            <div className="text-center py-20 bg-white border rounded-xl opacity-40">
                <p>點擊左側「一鍵全面分析」開始自動化診斷</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* 1. Overview Indicators */}
            <div className="grid grid-cols-4 gap-4">
                <Card className="p-4 bg-white border-none shadow-sm flex flex-col items-center justify-center">
                    <div className="text-2xl font-bold text-slate-700">
                        {String(diagnostics.summary_stats.count || diagnostics.quality_report[0].unique_count || "0")}
                    </div>
                </Card>
                <Card className="p-4 bg-white border-none shadow-sm flex flex-col items-center justify-center">
                    <div className="text-slate-400 text-xs mb-1">總欄位 (Columns)</div>
                    <div className="text-2xl font-bold text-slate-700">{diagnostics.quality_report.length}</div>
                </Card>
                <Card className="p-4 bg-white border-none shadow-sm flex flex-col items-center justify-center">
                    <div className="text-slate-400 text-xs mb-1">缺失率 &gt; 0%</div>
                    <div className="text-2xl font-bold text-orange-600">
                        {diagnostics.quality_report.filter((i: DataQualityItem) => i.missing_percentage > 0).length}
                    </div>
                </Card>
                <Card className="p-4 bg-white border-none shadow-sm flex flex-col items-center justify-center">
                    <div className="text-slate-400 text-xs mb-1">類型</div>
                    <div className="flex gap-1">
                        <Badge variant="secondary" className="text-[10px] bg-blue-50 text-blue-600">
                            {diagnostics.quality_report.filter((i: DataQualityItem) => i.dtype.includes('int') || i.dtype.includes('float')).length} Num
                        </Badge>
                        <Badge variant="secondary" className="text-[10px] bg-green-50 text-green-600">
                            {diagnostics.quality_report.filter((i: DataQualityItem) => i.dtype.includes('obj') || i.dtype.includes('str')).length} Cat
                        </Badge>
                    </div>
                </Card>
            </div>

            {/* 2. Visual Quality Report */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="p-6 border-none shadow-sm">
                    <h3 className="font-bold mb-4 text-slate-700">缺失值分佈 (Missing Values)</h3>
                    <div className="h-48 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={diagnostics.quality_report}>
                                <XAxis dataKey="column" tick={false} />
                                <YAxis />
                                <Tooltip />
                                <Bar dataKey="missing_percentage" fill="#F87171" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </Card>
                <Card className="p-6 border-none shadow-sm">
                    <h3 className="font-bold mb-4 text-slate-700">唯一值數量 (Cardinality)</h3>
                    <div className="h-48 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={diagnostics.quality_report}>
                                <XAxis dataKey="column" tick={false} />
                                <YAxis />
                                <Tooltip />
                                <Bar dataKey="unique_count" fill="#60A5FA" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </Card>
            </div>

            {/* 3. Detailed Table */}
            <Card className="p-6">
                <h3 className="font-bold mb-4 text-slate-700">欄位詳細報告</h3>
                <ScrollArea className="h-96">
                    <div className="space-y-1">
                        {diagnostics.quality_report.map((item: DataQualityItem) => (
                            <div key={item.column} className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-lg border border-transparent hover:border-slate-100 transition-all">
                                <div className="flex items-center gap-3">
                                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-xs font-mono font-bold border ${getTypeColor(item.dtype)}`}>
                                        {item.dtype.substring(0, 3)}
                                    </div>
                                    <div>
                                        <div className="font-bold text-sm text-slate-800">{item.column}</div>
                                        <div className="text-xs text-slate-400 mt-0.5 w-64 truncate">
                                            Sample: {item.sample_values.join(", ")}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-6 text-right">
                                    <div className="w-24">
                                        <div className="text-xs text-slate-400">缺失 (Missing)</div>
                                        <div className={`text-sm font-bold ${item.missing_percentage > 0 ? "text-orange-500" : "text-slate-600"}`}>
                                            {item.missing_percentage.toFixed(1)}% <span className="text-slate-300">({item.missing_count})</span>
                                        </div>
                                    </div>
                                    <div className="w-24">
                                        <div className="text-xs text-slate-400">唯一值 (Unique)</div>
                                        <div className="text-sm font-bold text-slate-600">
                                            {item.unique_count}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </ScrollArea>
            </Card>

            {/* 4. Deep Field Analysis */}
            <FieldAnalysisSection diagnostics={diagnostics} />

            {/* 5. Feature Suggestions */}
            <FeatureSuggestionsSection quality_report={diagnostics.quality_report} />

            {/* 6. Holistic Dataset Analysis */}
            <DatasetAnalysisSection diagnostics={diagnostics} />
        </div>
    );
}

// -------------------------------------------------------------
// Sub-components for Field Analysis
// -------------------------------------------------------------

function FieldAnalysisSection({ diagnostics }: { diagnostics: DiagnosticResponse }) {
    const [selectedField, setSelectedField] = useState<string>("");
    const [analysis, setAnalysis] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const { provider, model_name, local_url, api_key } = useSettingsStore();

    // Filter numeric fields
    const numericFields = diagnostics.quality_report.filter(
        (item: DataQualityItem) => item.dtype.includes('int') || item.dtype.includes('float')
    );
    
    // Get stats for selected field
    const selectedStats = diagnostics.quality_report.find((f: DataQualityItem) => f.column === selectedField);
    
    const handleAnalyze = async () => {
        if (!selectedField || !selectedStats) return;
        
        setLoading(true);
        setAnalysis("");
        
        try {
            // Find summary stats for this field if available
            const summary = (diagnostics.summary_stats?.[selectedField] as Record<string, unknown>) || {};
            
            const config: LLMConfig = {
                provider,
                model_name: model_name,
                local_url: local_url,
                api_key: api_key || undefined
            };

            const data = await getFieldAnalysis({
                field_name: selectedField,
                stats: { ...summary, ...selectedStats }, // Combine basic quality with summary
                sample_values: selectedStats.sample_values,
                config
            });
            setAnalysis(data.interpretation);
        } catch (error) {
            console.error(error);
            setAnalysis("分析失敗: " + String(error));
        } finally {
            setLoading(false);
        }
    };

    if (numericFields.length === 0) return null;

    return (
        <Card className="p-6 border-l-4 border-l-blue-500">
             <div className="flex items-center gap-2 mb-4">
                <Microscope className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-700">單一欄位深度分析 (Field Deep Dive)</h3>
             </div>
             
             <div className="flex gap-4 items-end flex-wrap">
                <div className="w-64">
                    <label className="text-xs font-medium text-slate-500 mb-1 block">選擇分析目標欄位</label>
                    <select 
                        value={selectedField} 
                        onChange={(e) => setSelectedField(e.target.value)}
                        className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        <option value="" disabled>選擇欄位...</option>
                        {numericFields.map((f: DataQualityItem) => (
                            <option key={f.column} value={f.column}>{f.column}</option>
                        ))}
                    </select>
                </div>
                
                <Button 
                    onClick={handleAnalyze} 
                    disabled={!selectedField || loading}
                    className="bg-blue-600 hover:bg-blue-700"
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <><Bot className="w-4 h-4 mr-2"/> AI 政策意涵分析</>}
                </Button>
             </div>
             
             {analysis && (
                 <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm text-slate-800 leading-relaxed">
                    <ReactMarkdown>{analysis}</ReactMarkdown>
                 </div>
             )}
        </Card>
    );
}

function FeatureSuggestionsSection({ quality_report }: { quality_report: DataQualityItem[] }) {
    const [suggestions, setSuggestions] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const { provider, model_name, local_url, api_key } = useSettingsStore();

    const handleSuggest = async () => {
        setLoading(true);
        setSuggestions("");
        
        try {
            // Build schema info string
            const schemaInfo = quality_report.slice(0, 20).map(
                col => `- ${col.column} (${col.dtype})`
            ).join("\n");
            
             const config: LLMConfig = {
                provider,
                model_name: model_name || undefined,
                local_url: local_url || undefined,
                api_key: api_key || undefined
            };
            
            const data = await getFeatureSuggestions({
                schema_info: schemaInfo,
                config
            });
            setSuggestions(data.suggestions);
        } catch (error) {
             console.error(error);
             setSuggestions("產生失敗: " + String(error));
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="p-6 border-l-4 border-l-purple-500">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Lightbulb className="w-5 h-5 text-purple-600" />
                    <div>
                        <h3 className="font-bold text-slate-700">特徵工程建議 (Attribute Suggestions)</h3>
                        <p className="text-xs text-slate-500">讓 AI 根據現有資料結構，建議更有分析價值的衍生指標。</p>
                    </div>
                </div>
                <Button 
                    variant="outline"
                    onClick={handleSuggest} 
                    disabled={loading}
                    className="border-purple-200 text-purple-700 hover:bg-purple-50"
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <><Rocket className="w-4 h-4 mr-2"/> 產生建議</>}
                </Button>
            </div>
            
            {suggestions && (
                 <div className="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 leading-relaxed">
                    <ReactMarkdown>{suggestions}</ReactMarkdown>
                 </div>
             )}
        </Card>
    );
}


function DatasetAnalysisSection({ diagnostics }: { diagnostics: DiagnosticResponse }) {
    const [analysis, setAnalysis] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const { provider, model_name, local_url, api_key } = useSettingsStore();

    const handleAnalyze = async () => {
        setLoading(true);
        setAnalysis("");
        
        try {
            // Select relevant numeric columns (up to 12)
            const numericCols = diagnostics.quality_report
                .filter((c: DataQualityItem) => c.dtype.includes('int') || c.dtype.includes('float'))
                .slice(0, 12);
            
            const columnsStats = numericCols.map((col: DataQualityItem) => ({
                name: col.column,
                ...((diagnostics.summary_stats?.[col.column] as Record<string, unknown>) || {}),
                sample_values: col.sample_values
            }));

            const config: LLMConfig = {
                provider,
                model_name: model_name || undefined,
                local_url: local_url || undefined,
                api_key: api_key || undefined
            };

            const data = await getDatasetAnalysis({
                columns_stats: columnsStats,
                config
            });
            setAnalysis(data.interpretation);
        } catch (error) {
            console.error(error);
            setAnalysis("分析失敗: " + String(error));
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="p-6 border-l-4 border-l-emerald-500">
             <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Activity className="w-5 h-5 text-emerald-600" />
                    <div>
                        <h3 className="font-bold text-slate-700">全域數據洞察 (Holistic Dataset Analysis)</h3>
                        <p className="text-xs text-slate-500">AI 將綜合分析多個關鍵欄位，找出跨變數的系統性關聯與潛在結構。</p>
                    </div>
                </div>
                <Button 
                    onClick={handleAnalyze} 
                    disabled={loading}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <><Activity className="w-4 h-4 mr-2"/> 啟動全域分析</>}
                </Button>
            </div>
             
             {analysis && (
                 <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-slate-800 leading-relaxed">
                    <ReactMarkdown>{analysis}</ReactMarkdown>
                 </div>
             )}
        </Card>
    );
}
