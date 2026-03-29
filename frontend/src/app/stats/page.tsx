"use client";

import { useState, useEffect } from "react";
import { ProfilingTab } from "@/components/stats/ProfilingTab";
import { DataPrepTab } from "@/components/stats/DataPrepTab";
import { ExploratoryTab } from "@/components/stats/ExploratoryTab";
import { InferenceTab } from "@/components/stats/InferenceTab";
import { MultivariateTab } from "@/components/stats/MultivariateTab";
import { ModelingTab } from "@/components/stats/ModelingTab";
import { CommandCenter } from "@/components/ui/command-center";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileUploader } from "@/components/file-uploader";
import {
    getDiagnostic,
    performEDA,
    performStatTest,
    interpretStats,
    DiagnosticResponse,
    EDAResponse,
    StatTestResponse
} from "@/lib/api";
import { 
    BarChart3, 
    Microscope, 
    TrendingUp, 
    Rocket, 
    Loader2, 
    CheckCircle2, 
    Clock,
    Network,
    Compass,
    Wrench,
    LayoutGrid
} from "lucide-react";

import { useSettingsStore } from "@/stores/settings-store";
import { useDocumentStore } from "@/stores/document-store";

export default function StatisticsPage() {
    const { provider, model_name, local_url, api_key } = useSettingsStore();
    const config = { provider, model_name, local_url, api_key };

    // Global document store
    const { documents: allDocs, loading: loadingDocs, fetchDocuments } = useDocumentStore();
    const documents = allDocs.filter(d => d.file_name.match(/\.(csv|xlsx|xls|json)$/i));
    const [selectedDoc, setSelectedDoc] = useState<string | null>(null);

    const [activeTab, setActiveTab] = useState("profiling");
    const [diagnostics, setDiagnostics] = useState<DiagnosticResponse | null>(null);
    const [edaResults, setEdaResults] = useState<EDAResponse | null>(null);
    const [testResults, setTestResults] = useState<StatTestResponse | null>(null);

    const [processing, setProcessing] = useState(false);
    const [isInterpreting, setIsInterpreting] = useState(false);

    // Progress Tracking for Full Analysis
    const [analysisProgress, setAnalysisProgress] = useState<{
        profiling: "idle" | "running" | "done" | "error";
        correlation: "idle" | "running" | "done" | "error";
        inference: "idle" | "running" | "done" | "error";
    }>({ profiling: "idle", correlation: "idle", inference: "idle" });
    const [isFullAnalysis, setIsFullAnalysis] = useState(false);

    // Manual Inference Column Selection
    const [selectedInferenceCols, setSelectedInferenceCols] = useState<string[]>([]);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    const handleUploadComplete = () => {
        fetchDocuments();
    };

    const handleSelectDoc = async (collectionName: string) => {
        setSelectedDoc(collectionName);
        setDiagnostics(null);
        setEdaResults(null);
        setTestResults(null);
        setAnalysisProgress({ profiling: "idle", correlation: "idle", inference: "idle" });
        setIsFullAnalysis(false);
        setSelectedInferenceCols([]);

        // Auto-run diagnostic
        const doc = documents.find(d => d.collection_name === collectionName);
        if (doc) {
            setProcessing(true);
            try {
                const res = await getDiagnostic({
                    file_path: doc.file_name,
                    config: config
                });
                setDiagnostics(res);
                setAnalysisProgress(p => ({ ...p, profiling: "done" }));
            } catch (err) {
                console.error(err);
                setAnalysisProgress(p => ({ ...p, profiling: "error" }));
            } finally {
                setProcessing(false);
            }
        }
    };

    const handleFullAnalysis = async () => {
        if (!selectedDoc) return;
        const doc = documents.find(d => d.collection_name === selectedDoc);
        if (!doc) return;

        setIsFullAnalysis(true);
        setAnalysisProgress({ profiling: "running", correlation: "idle", inference: "idle" });

        try {
            // Step 1: Profiling
            const profilingRes = await getDiagnostic({
                file_path: doc.file_name,
                config: config
            });
            setDiagnostics(profilingRes);
            setAnalysisProgress(p => ({ ...p, profiling: "done", correlation: "running" }));

            // Step 2: Correlation
            const corrRes = await performEDA({
                file_path: doc.file_name,
                analysis_type: "correlation",
                params: {},
                config: config,
                skip_interpretation: true
            });
            setEdaResults(corrRes);
            setAnalysisProgress(p => ({ ...p, correlation: "done", inference: "running" }));

            // Step 3: Quick Inference (Shapiro on first numeric column)
            const numCols = profilingRes.quality_report
                .filter(c => c.dtype.includes("int") || c.dtype.includes("float"))
                .map(c => c.column);

            if (numCols.length > 0) {
                const targetCols = numCols.slice(0, 1);
                const testRes = await performStatTest({
                    file_path: doc.file_name,
                    test_type: "shapiro",
                    target_columns: targetCols,
                    config: config
                });
                setTestResults(testRes);
                setSelectedInferenceCols(targetCols);
            }
            setAnalysisProgress(p => ({ ...p, inference: "done" }));

        } catch (err) {
            console.error("Full analysis failed", err);
        }
    };

    const handleRunEDA = async (type: "correlation" | "groupby", manualParams?: Record<string, unknown>) => {
        if (!selectedDoc) return;
        setProcessing(true);
        if (type === "correlation") setEdaResults(null);
        else if (type === "groupby") setEdaResults(null);
        
        try {
            const doc = documents.find(d => d.collection_name === selectedDoc);
            const res = await performEDA({
                file_path: doc!.file_name,
                analysis_type: type,
                params: manualParams || {},
                config: config
            });
            setEdaResults(res);
        } catch (err) {
            console.error("EDA failed", err);
        } finally {
            setProcessing(false);
        }
    };

    const handleRunStatTest = async (type: "ttest" | "anova" | "shapiro" | "outliers" | "chi_square" | "mann_whitney" | "kruskal" | "wilcoxon") => {
        if (!selectedDoc) return;
        if (selectedInferenceCols.length === 0) {
            alert("請先選擇至少一個欄位");
            return;
        }

        setProcessing(true);
        setTestResults(null);
        try {
            const doc = documents.find(d => d.collection_name === selectedDoc);
            const res = await performStatTest({
                file_path: doc!.file_name,
                test_type: type,
                target_columns: selectedInferenceCols,
                config: config
            });
            setTestResults(res);
        } catch (err) {
            console.error("Stat test failed", err);
        } finally {
            setProcessing(false);
        }
    };
    
    const handleInterpretStats = async (contextType: "eda" | "inference" ) => {
        setIsInterpreting(true);
        try {
            let context = "";
            let summary = "";
            let type = "";

            if (contextType === "eda" && edaResults) {
                context = "這是相關性分析的結果。";
                summary = JSON.stringify(edaResults.result_data).slice(0, 2000); 
                type = "Exploratory Data Analysis";
            } else if (contextType === "inference" && testResults) {
                context = "這是統計檢定 (T-test, ANOVA, Shapiro, Outliers) 的結果。";
                summary = JSON.stringify(testResults.test_results);
                type = "Statistical Inference";
            }

            const res = await interpretStats({
                context,
                data_summary: summary,
                test_type: type,
                config: config
            });

            if (contextType === "eda" && edaResults) {
                setEdaResults({ ...edaResults, interpretation: res.interpretation });
            } else if (contextType === "inference" && testResults) {
                setTestResults({ ...testResults, interpretation: res.interpretation });
            }

        } catch (err) {
            console.error("Interpret failed", err);
        } finally {
            setIsInterpreting(false);
        }
    };


    // Derived props
    const currentFilePath = selectedDoc ? documents.find(d => d.collection_name === selectedDoc)?.file_name || null : null;

    return (
        <div className="flex h-screen bg-slate-50/50 overflow-hidden font-sans">
            {/* Standardized Sidebar (Glassmorphism + Clean Borders) */}
            <div className="w-[280px] bg-white/70 backdrop-blur-xl border-r border-slate-200/60 flex flex-col shrink-0 z-20 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
                <div className="p-6 border-b border-slate-100/50">
                    <h2 className="font-black text-xl flex items-center gap-3 text-slate-800 tracking-tight">
                        <div className="p-2 bg-indigo-600 rounded-lg shadow-indigo-200 shadow-lg">
                             <BarChart3 className="text-white w-5 h-5" /> 
                        </div>
                        統計分析
                    </h2>
                    <p className="text-xs font-bold text-slate-400 mt-2 tracking-widest uppercase pl-1">Statistics Lab</p>
                </div>
                
                <div className="p-6 pb-2 border-b border-slate-100/50">
                     <FileUploader onUploadComplete={handleUploadComplete} />
                     <p className="text-[10px] text-slate-400 mt-3 text-center font-medium">支援 CSV, Excel, JSON</p>
                </div>

                <ScrollArea className="flex-1">
                    <div className="p-4 space-y-2">
                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 px-2">Data Source</h3>
                        {loadingDocs ? (
                            <div className="space-y-3 px-2">
                                {[1, 2, 3].map(i => <div key={i} className="h-12 bg-slate-100 rounded-xl animate-pulse" />)}
                            </div>
                        ) : documents.length === 0 ? (
                            <div className="text-center py-8 border-2 border-dashed border-slate-100 rounded-xl m-2">
                                <p className="text-sm text-slate-400 font-medium">尚無數據文件</p>
                            </div>
                        ) : (
                            documents.map(doc => (
                                <button
                                    key={doc.collection_name}
                                    onClick={() => handleSelectDoc(doc.collection_name)}
                                    className={`w-full text-left p-3 rounded-xl text-sm transition-all duration-300 group ${
                                        selectedDoc === doc.collection_name
                                            ? "bg-indigo-50/80 border border-indigo-200 text-indigo-700 shadow-sm ring-1 ring-indigo-100"
                                            : "hover:bg-white hover:shadow-md border border-transparent text-slate-600 hover:text-slate-900"
                                    }`}
                                >
                                    <div className="font-bold truncate flex items-center gap-2">
                                        {selectedDoc === doc.collection_name ? <CheckCircle2 size={14} className="text-indigo-500"/> : <LayoutGrid size={14} className="text-slate-300 group-hover:text-slate-500"/>}
                                        {doc.file_name}
                                    </div>
                                    <div className="text-[10px] text-slate-400 mt-1.5 flex items-center gap-1.5 pl-6 font-mono opacity-70">
                                        <Clock size={10} /> <span>{doc.indexed_at.slice(0, 10)}</span>
                                    </div>
                                </button>
                            ))
                        )}
                    </div>
                </ScrollArea>
                
                {selectedDoc && (
                    <div className="p-6 border-t border-slate-100 bg-white/50 backdrop-blur-sm space-y-3">
                         <Button 
                            onClick={handleFullAnalysis}
                            disabled={isFullAnalysis}
                            className={`w-full h-10 text-xs font-bold rounded-xl gap-2 transition-all duration-300 ${isFullAnalysis ? 'bg-slate-100 text-slate-400' : 'bg-slate-900 hover:bg-black text-white shadow-lg hover:shadow-xl hover:-translate-y-0.5'}`}
                        >
                            {isFullAnalysis ? (
                                <>
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                    分析執行中...
                                </>
                            ) : (
                                <><Rocket size={14} /> 一鍵全面分析</>
                            )}
                        </Button>

                         {isFullAnalysis && (
                            <div className="space-y-2 bg-white/80 backdrop-blur p-3 rounded-xl border border-indigo-100 text-xs shadow-sm">
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-500 font-bold">1. 數據診斷</span>
                                    {analysisProgress.profiling === "running" && <Loader2 size={12} className="text-indigo-500 animate-spin" />}
                                    {analysisProgress.profiling === "done" && <CheckCircle2 size={12} className="text-emerald-500" />}
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-500 font-bold">2. 相關性分析</span>
                                    {analysisProgress.correlation === "running" && <Loader2 size={12} className="text-indigo-500 animate-spin" />}
                                    {analysisProgress.correlation === "done" && <CheckCircle2 size={12} className="text-emerald-500" />}
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-500 font-bold">3. 基礎檢定</span>
                                    {analysisProgress.inference === "running" && <Loader2 size={12} className="text-indigo-500 animate-spin" />}
                                    {analysisProgress.inference === "done" && <CheckCircle2 size={12} className="text-emerald-500" />}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col h-screen overflow-hidden relative bg-slate-50/30">
                <Header title="統計分析實驗室" subtitle="Statistics Lab" />
                
                <div className="flex-1 overflow-y-auto scroll-smooth">
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col min-h-screen">
                        
                        {/* Unified Sticky Header Layer */}
                        <div className="sticky top-0 z-30 bg-slate-50/95 backdrop-blur-md border-b border-slate-200/50 shadow-sm transition-all duration-300">
                            <div className="max-w-[1600px] mx-auto px-8 pt-6 pb-4 space-y-6">
                                {/* 1. Command Center */}
                                <div className="pointer-events-auto relative z-20">
                                    <CommandCenter filePath={currentFilePath} className="shadow-xl ring-1 ring-slate-900/5" />
                                </div>

                                {/* 2. Navigation Pills */}
                                <div className="flex items-center justify-center relative z-10 w-full overflow-x-auto no-scrollbar">
                                    <TabsList className="bg-slate-100/50 p-1 gap-1 h-auto rounded-full border border-slate-200/50 inline-flex">
                                        <TabsTrigger value="profiling" className="rounded-full px-4 py-1.5 text-xs font-bold data-[state=active]:bg-white data-[state=active]:text-indigo-600 data-[state=active]:shadow-sm transition-all text-slate-500 hover:text-slate-900"><BarChart3 size={14} className="mr-2"/> 概況</TabsTrigger>
                                        <TabsTrigger value="dataprep" className="rounded-full px-4 py-1.5 text-xs font-bold data-[state=active]:bg-white data-[state=active]:text-indigo-600 data-[state=active]:shadow-sm transition-all text-slate-500 hover:text-slate-900"><Wrench size={14} className="mr-2"/> 準備</TabsTrigger>
                                        <TabsTrigger value="exploratory" className="rounded-full px-4 py-1.5 text-xs font-bold data-[state=active]:bg-white data-[state=active]:text-indigo-600 data-[state=active]:shadow-sm transition-all text-slate-500 hover:text-slate-900"><Compass size={14} className="mr-2"/> 探索</TabsTrigger>
                                        <TabsTrigger value="inference" className="rounded-full px-4 py-1.5 text-xs font-bold data-[state=active]:bg-white data-[state=active]:text-indigo-600 data-[state=active]:shadow-sm transition-all text-slate-500 hover:text-slate-900"><Microscope size={14} className="mr-2"/> 推論</TabsTrigger>
                                        <TabsTrigger value="multivariate" className="rounded-full px-4 py-1.5 text-xs font-bold data-[state=active]:bg-white data-[state=active]:text-indigo-600 data-[state=active]:shadow-sm transition-all text-slate-500 hover:text-slate-900"><Network size={14} className="mr-2"/> 多變量</TabsTrigger>
                                        <TabsTrigger value="modeling" className="rounded-full px-4 py-1.5 text-xs font-bold data-[state=active]:bg-white data-[state=active]:text-indigo-600 data-[state=active]:shadow-sm transition-all text-slate-500 hover:text-slate-900"><TrendingUp size={14} className="mr-2"/> 建模</TabsTrigger>
                                    </TabsList>
                                </div>
                            </div>
                        </div>

                        {/* Content Area */}
                        <div className="flex-1 p-8 max-w-[1600px] mx-auto w-full">
                            <TabsContent value="profiling" className="mt-0 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <ProfilingTab 
                                    selectedDoc={selectedDoc} 
                                    processing={processing}
                                    diagnostics={diagnostics}
                                />
                            </TabsContent>

                            <TabsContent value="dataprep" className="mt-0 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <DataPrepTab 
                                    selectedDoc={selectedDoc}
                                    filePath={currentFilePath}
                                    diagnostics={diagnostics}
                                />
                            </TabsContent>

                            <TabsContent value="exploratory" className="mt-0 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <ExploratoryTab 
                                    selectedDoc={selectedDoc}
                                    filePath={currentFilePath}
                                    config={config}
                                    processing={processing}
                                    diagnostics={diagnostics}
                                    edaResults={edaResults}
                                    onRunEDA={handleRunEDA}
                                    onInterpret={handleInterpretStats}
                                    isInterpreting={isInterpreting}
                                />
                            </TabsContent>

                            <TabsContent value="inference" className="mt-0 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <InferenceTab 
                                    selectedDoc={selectedDoc}
                                    filePath={currentFilePath}
                                    processing={processing}
                                    testResults={testResults}
                                    diagnostics={diagnostics}
                                    onRunTest={handleRunStatTest}
                                    onInterpret={() => handleInterpretStats("inference")}
                                    isInterpreting={isInterpreting}
                                    selectedInferenceCols={selectedInferenceCols}
                                    setSelectedInferenceCols={setSelectedInferenceCols}
                                />
                            </TabsContent>

                            <TabsContent value="multivariate" className="mt-0 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <MultivariateTab 
                                    selectedDoc={selectedDoc}
                                    filePath={currentFilePath}
                                    config={config}
                                    diagnostics={diagnostics}
                                />
                            </TabsContent>

                            <TabsContent value="modeling" className="mt-0 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <ModelingTab 
                                    selectedDoc={selectedDoc}
                                    filePath={currentFilePath}
                                    config={config}
                                    diagnostics={diagnostics}
                                />
                            </TabsContent>
                        </div>
                    </Tabs>
                </div>
            </div>
        </div>
    );
}

