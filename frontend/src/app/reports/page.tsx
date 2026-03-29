"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { FileUploader } from "@/components/file-uploader";
import {
    listSkills,
    listTemplates,
    generateReport,
    downloadReportDocx,
    SkillInfo,
    TemplateInfo,
    ReportResponse,
} from "@/lib/api";
import { useSettingsStore } from "@/stores/settings-store";
import { useDocumentStore } from "@/stores/document-store";
import { 
    FileText, 
    Rocket, 
    CheckCircle2, 
    XCircle, 
    Copy, 
    Download, 
    ChevronLeft, 
    ChevronRight,
    Loader2,
    Briefcase,
    Clock
} from "lucide-react";

export default function ReportsPage() {
    console.log("ReportsPage Rendering");
    const { provider, model_name, local_url, api_key, context_window } = useSettingsStore();
    
    // Global document store
    const { documents, fetchDocuments } = useDocumentStore();
    
    const [skills, setSkills] = useState<SkillInfo[]>([]);
    const [templates, setTemplates] = useState<TemplateInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
    const [selectedTemplate, setSelectedTemplate] = useState<string>("");
    const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
    const [report, setReport] = useState<ReportResponse | null>(null);
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    useEffect(() => {
        fetchDocuments();
        async function initData() {
            try {
                const [skillList, templateList] = await Promise.all([
                    listSkills(),
                    listTemplates(),
                ]);
                setSkills(skillList);
                setTemplates(templateList);
                // 預設選擇第一個模板
                if (templateList.length > 0) {
                    setSelectedTemplate(templateList[0].id);
                    setSelectedSkills(templateList[0].recommended_skills);
                }
            } catch (err) {
                console.error("Failed to load report data", err);
            } finally {
                setLoading(false);
            }
        }
        initData();
    }, [fetchDocuments]);

    // 選擇模板時自動推薦技能
    const handleTemplateSelect = (templateId: string) => {
        setSelectedTemplate(templateId);
        const template = templates.find((t) => t.id === templateId);
        if (template) {
            setSelectedSkills(template.recommended_skills);
        }
    };

    const handleGenerate = async () => {
        if (!selectedDoc) return;
        setGenerating(true);
        setError(null);
        try {
            const res = await generateReport({
                template_name: selectedTemplate,
                selected_skills: selectedSkills,
                file_path: documents.find(d => d.collection_name === selectedDoc)?.file_name,
                config: {
                    provider,
                    model_name,
                    local_url,
                    api_key: api_key || undefined,
                    context_window,
                }
            });
            setReport(res);
        } catch (err) {
            console.error("Generation failed", err);
            setError(err instanceof Error ? err.message : "報表生成失敗，請稍後再試");
        } finally {
            setGenerating(false);
        }
    };
    
    // 複製內容
    const handleCopyReport = () => {
        if (!report) return;
        navigator.clipboard.writeText(report.content);
        alert("分析報告已複製到剪貼簿");
    };

    // 下載 Word
    const handleDownloadWord = async () => {
        if (!report) return;
        try {
            const title = templates.find(t => t.id === selectedTemplate)?.name || "分析報告";
            await downloadReportDocx(report.content, title);
        } catch (err) {
            console.error("Download failed", err);
            setError("下載失敗，請檢查網路連線或稍後再試");
        }
    };

    const categories = Array.from(new Set(skills.map(s => s.category)));

    if (loading) {
        return (
            <div className="flex-1 flex flex-col bg-slate-50/50 p-6 space-y-6 h-screen overflow-hidden">
                <Skeleton className="h-20 w-full" />
                <div className="grid grid-cols-12 gap-6 flex-1">
                    <Skeleton className="col-span-3 h-full rounded-2xl" />
                    <Skeleton className="col-span-9 h-full rounded-2xl" />
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-screen bg-slate-50/50 overflow-hidden font-sans">
            {/* 1. Sidebar (Document Selection) - Left Panel */}
            <div 
                className={`flex-shrink-0 bg-white/70 backdrop-blur-xl border-r border-slate-200/60 transition-all duration-300 flex flex-col z-20 shadow-[4px_0_24px_rgba(0,0,0,0.02)] ${isSidebarOpen ? "w-[280px]" : "w-0 overflow-hidden"}`}
            >
                <div className="p-6 border-b border-slate-100/50">
                    <h2 className="font-black text-xl flex items-center gap-3 text-slate-800 tracking-tight">
                        <div className="p-2 bg-indigo-600 rounded-lg shadow-indigo-200 shadow-lg">
                             <Briefcase className="text-white w-5 h-5" /> 
                        </div>
                        報告中心
                    </h2>
                    <p className="text-xs font-bold text-slate-400 mt-2 tracking-widest uppercase pl-1">Report Center</p>
                </div>

                <div className="p-6 pb-2 border-b border-slate-100/50">
                     <FileUploader onUploadComplete={fetchDocuments} />
                     <p className="text-[10px] text-slate-400 mt-3 text-center font-medium">支援 PDF, TXT, DOCX</p>
                </div>

                <ScrollArea className="flex-1">
                    <div className="p-4 space-y-2">
                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 px-2">Source Files</h3>
                        {documents.length === 0 ? (
                            <div className="text-center py-8 border-2 border-dashed border-slate-100 rounded-xl m-2">
                                <p className="text-sm text-slate-400 font-medium">尚無文件</p>
                            </div>
                        ) : (
                            documents.map((doc) => (
                                <button
                                    key={doc.collection_name}
                                    onClick={() => setSelectedDoc(doc.collection_name)}
                                    className={`w-full text-left p-3 rounded-xl text-sm transition-all duration-300 group ${
                                        selectedDoc === doc.collection_name
                                            ? "bg-indigo-50/80 border border-indigo-200 text-indigo-700 shadow-sm ring-1 ring-indigo-100"
                                            : "hover:bg-white hover:shadow-md border border-transparent text-slate-600 hover:text-slate-900"
                                    }`}
                                >
                                    <div className="font-bold truncate flex items-center gap-2">
                                        {selectedDoc === doc.collection_name ? <CheckCircle2 size={14} className="text-indigo-500"/> : <FileText size={14} className="text-slate-300 group-hover:text-slate-500"/>}
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
                
                {/* Generate Button in Sidebar for better Mobile Flow or consistency? No, keep main action prominent. */}
            </div>

            {/* Sidebar Toggle (Floating) */}
            <button
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                className={`absolute bottom-6 z-30 w-8 h-12 bg-white border border-slate-200 shadow-xl rounded-r-lg flex items-center justify-center text-slate-400 hover:text-indigo-600 transition-all duration-300 hover:w-10 ${isSidebarOpen ? "left-[280px]" : "left-0"}`}
            >
                {isSidebarOpen ? <ChevronLeft size={16}/> : <ChevronRight size={16}/>}
            </button>

            {/* 2. Main Content Area */}
            <div className="flex-1 flex flex-col h-screen overflow-hidden relative bg-slate-50/30">
                <Header title="產生分析報告" subtitle="Report Generation Level 3" />
                
                <div className="flex-1 overflow-y-auto scroll-smooth">
                    {/* Unified Sticky Header for Configuration */}
                    <div className="sticky top-0 z-30 bg-slate-50/95 backdrop-blur-md border-b border-slate-200/50 shadow-sm transition-all duration-300">
                        <div className="max-w-[1200px] mx-auto px-8 py-6">
                            <div className="flex gap-8 items-start">
                                {/* Configuration Columns */}
                                <div className="flex-1 flex flex-col gap-6 min-w-0">
                                    
                                    {/* Template Selection */}
                                    <div className="min-w-0">
                                        <div className="flex items-center justify-between mb-2">
                                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                                <div className="w-4 h-4 rounded bg-indigo-100 flex items-center justify-center text-indigo-600 text-[10px]">1</div> 
                                                選擇報告模板
                                            </label>
                                        </div>
                                        <div className="flex gap-3 overflow-x-auto pb-2 -mx-2 px-2 no-scrollbar">
                                            {templates.map((t) => (
                                                <button
                                                    key={t.id}
                                                    onClick={() => handleTemplateSelect(t.id)}
                                                    className={`flex-shrink-0 text-left px-4 py-3 rounded-xl border transition-all w-[200px] group ${
                                                        selectedTemplate === t.id
                                                            ? "bg-indigo-600 border-indigo-600 text-white shadow-indigo-200 shadow-md ring-2 ring-indigo-100"
                                                            : "bg-white border-slate-200 text-slate-600 hover:border-indigo-300 hover:bg-indigo-50/30"
                                                    }`}
                                                >
                                                    <div className="flex justify-between items-start mb-1">
                                                        <span className="font-bold text-sm tracking-tight">{t.name}</span>
                                                        {selectedTemplate === t.id && <CheckCircle2 size={14} className="text-indigo-300" />}
                                                    </div>
                                                    <p className={`text-[11px] leading-relaxed line-clamp-2 ${selectedTemplate === t.id ? "text-indigo-100" : "text-slate-400 group-hover:text-slate-500"}`}>
                                                        {t.description}
                                                    </p>
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Skills Selection */}
                                    <div className="min-w-0">
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 flex items-center gap-2">
                                            <div className="w-4 h-4 rounded bg-indigo-100 flex items-center justify-center text-indigo-600 text-[10px]">2</div>
                                            配置專家技能
                                        </label>
                                        <div className="bg-white/50 backdrop-blur-sm rounded-xl border border-slate-200/60 p-1 flex gap-2 overflow-x-auto no-scrollbar items-center">
                                            {categories.map(cat => (
                                                <div key={cat} className="flex-shrink-0 flex items-center gap-2 px-3 border-r last:border-r-0 border-slate-200/60 py-1">
                                                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider whitespace-nowrap">{cat}</span>
                                                    <div className="flex gap-1.5">
                                                        {skills.filter(s => s.category === cat).map(skill => (
                                                            <button
                                                                key={skill.id}
                                                                onClick={() => {
                                                                    if (selectedSkills.includes(skill.id)) setSelectedSkills(selectedSkills.filter(id => id !== skill.id));
                                                                    else setSelectedSkills([...selectedSkills, skill.id]);
                                                                }}
                                                                className={`px-3 py-1 rounded-full text-[11px] font-bold transition-all border ${selectedSkills.includes(skill.id)
                                                                    ? "bg-indigo-50 border-indigo-200 text-indigo-700 shadow-sm"
                                                                    : "bg-transparent border-transparent text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                                                                    }`}
                                                                title={skill.description}
                                                            >
                                                                {skill.name.split(" ")[1] || skill.name}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {/* Generate Button (Right Side, Big) */}
                                <div className="flex-shrink-0 pt-6">
                                    <Button
                                        onClick={handleGenerate}
                                        disabled={!selectedDoc || !selectedTemplate || generating}
                                        className={`h-28 w-40 flex flex-col items-center justify-center gap-3 rounded-2xl shadow-xl transition-all duration-300 group ${
                                            !selectedDoc 
                                                ? "bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed" 
                                                : "bg-slate-900 hover:bg-black text-white shadow-indigo-200 hover:shadow-2xl hover:-translate-y-1"
                                        }`}
                                    >
                                        {generating ? (
                                            <>
                                                <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
                                                <span className="text-xs font-bold animate-pulse">生成中...</span>
                                            </>
                                        ) : (
                                            <>
                                                <div className={`p-3 rounded-full ${!selectedDoc ? "bg-slate-200" : "bg-indigo-600 group-hover:scale-110 transition-transform duration-300"}`}>
                                                    <Rocket size={24} className="text-white" />
                                                </div>
                                                <div className="text-center">
                                                    <span className="block text-sm font-black tracking-tight">產生報告</span>
                                                    <span className="block text-[10px] opacity-60 font-mono mt-0.5">GENERATE</span>
                                                </div>
                                            </>
                                        )}
                                    </Button>
                                    {!selectedDoc && (
                                        <p className="text-[10px] text-red-500 font-bold text-center mt-2 animate-pulse">請先選擇文件</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Result Content Area */}
                    <div className="p-8 max-w-[1200px] mx-auto min-h-[500px]">
                        {generating ? (
                            <div className="flex flex-col items-center justify-center p-20 text-center bg-white rounded-3xl border border-slate-100 shadow-xl shadow-slate-200/50">
                                <div className="relative">
                                    <div className="w-24 h-24 bg-indigo-50 rounded-full flex items-center justify-center mb-8 animate-pulse">
                                        <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
                                    </div>
                                    <div className="absolute top-0 right-0 w-6 h-6 bg-emerald-400 rounded-full animate-ping" />
                                </div>
                                <h2 className="text-2xl font-black text-slate-800 tracking-tight">正在構建深度分析報告</h2>
                                <p className="text-slate-500 mt-3 text-lg font-medium">AI 正在調用專家技能進行多維度解析...</p>
                                <div className="w-full max-w-md mt-12 space-y-4">
                                    <Skeleton className="h-3 w-full rounded-full bg-slate-100" />
                                    <Skeleton className="h-3 w-5/6 rounded-full bg-slate-100" />
                                    <Skeleton className="h-3 w-4/6 rounded-full bg-slate-100" />
                                </div>
                            </div>
                        ) : report ? (
                            <div className="bg-white rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/50 overflow-hidden animate-in fade-in slide-in-from-bottom-8 duration-700">
                                <div className="px-8 py-5 border-b border-slate-100 bg-white/50 backdrop-blur-sm flex items-center justify-between sticky top-0 z-10">
                                    <div className="flex items-center gap-4">
                                        <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-600 rounded-full border border-emerald-100">
                                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                            <span className="text-xs font-bold tracking-wide uppercase">Analysis Ready</span>
                                        </div>
                                        <span className="text-sm font-medium text-slate-500">
                                            {templates.find(t => t.id === selectedTemplate)?.name}
                                        </span>
                                    </div>
                                    <div className="flex gap-3">
                                        <Button variant="outline" size="sm" className="rounded-xl font-bold border-slate-200 hover:bg-slate-50 text-slate-600" onClick={handleCopyReport}>
                                            <Copy size={14} className="mr-2"/> 複製全文
                                        </Button>
                                        <Button size="sm" className="rounded-xl font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-200 shadow-lg" onClick={handleDownloadWord}>
                                            <Download size={14} className="mr-2"/> 下載報告 (Word)
                                        </Button>
                                    </div>
                                </div>
                                <div className="p-12 min-h-[800px] bg-white">
                                    <div className="max-w-[900px] mx-auto prose prose-slate prose-headings:font-black prose-p:text-slate-600 prose-li:text-slate-600">
                                        <MarkdownRenderer content={report.content} />
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center text-center p-20 bg-white/40 border-4 border-dashed border-slate-200/60 rounded-[3rem] min-h-[600px] hover:bg-white/60 hover:border-indigo-200/60 transition-all duration-500 group">
                                <div className="w-32 h-32 bg-slate-50 rounded-full flex items-center justify-center mb-8 group-hover:scale-110 transition-transform duration-500">
                                    <FileText size={48} className="text-slate-300 group-hover:text-indigo-300 transition-colors" />
                                </div>
                                <h2 className="text-3xl font-black text-slate-300 italic uppercase tracking-widest group-hover:text-indigo-300 transition-colors">Pending Generation</h2>
                                <p className="text-slate-400 mt-4 max-w-sm text-lg font-medium">
                                    請從左側選擇文件，並配置上方參數以開始分析
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Error Display (Floating Toast) */}
            {error && (
                <div className="fixed bottom-8 right-8 p-5 bg-white border-l-4 border-rose-500 shadow-2xl rounded-xl z-50 flex items-center gap-4 animate-in slide-in-from-right duration-500">
                    <div className="p-2 bg-rose-50 rounded-full">
                        <XCircle size={24} className="text-rose-500"/>
                    </div>
                    <div>
                        <p className="font-bold text-slate-900 text-sm">生成失敗</p>
                        <p className="text-xs text-slate-500 mt-0.5 max-w-[200px]">{error}</p>
                    </div>
                    <button onClick={() => setError(null)} className="ml-4 text-slate-400 hover:text-slate-600 transition-colors">✕</button>
                </div>
            )}
        </div>
    );
}
