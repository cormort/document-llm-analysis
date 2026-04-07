"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
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

export default function ReportsPage() {
    console.log("ReportsPage Rendering");
    const { provider, model_name, local_url, api_key, context_window } = useSettingsStore();
    
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
    // Added for option B (Reading Overlay)
    const [isOverlayOpen, setIsOverlayOpen] = useState(false);

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

    const handleTemplateSelect = (templateId: string) => {
        setSelectedTemplate(templateId);
        const template = templates.find((t) => t.id === templateId);
        if (template) {
            setSelectedSkills(template.recommended_skills);
        }
    };

    const handleSkillToggle = (skillId: string) => {
        if (selectedSkills.includes(skillId)) {
            setSelectedSkills(selectedSkills.filter(id => id !== skillId));
        } else {
            setSelectedSkills([...selectedSkills, skillId]);
        }
    };

    const handleGenerate = async () => {
        if (!selectedDoc) {
             setError("Please select a document first.");
             return;
        }
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
            setIsOverlayOpen(true); // Auto-open overlay
        } catch (err) {
            console.error("Generation failed", err);
            setError(err instanceof Error ? err.message : "Report generation failed");
        } finally {
            setGenerating(false);
        }
    };

    const handleCopyReport = () => {
        if (!report) return;
        navigator.clipboard.writeText(report.content);
        alert("Report copied to clipboard.");
    };

    const handleDownloadWord = async () => {
        if (!report) return;
        try {
            const title = templates.find(t => t.id === selectedTemplate)?.name || "Analysis Report";
            await downloadReportDocx(report.content, title);
        } catch (err) {
            console.error("Download failed", err);
            setError("Download failed");
        }
    };

    // Calculate dynamic UI elements
    const selectedTemplateObj = templates.find(t => t.id === selectedTemplate);

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center bg-surface h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <div className="flex-1 min-h-screen bg-surface font-['Inter'] relative text-on-surface w-full overflow-hidden flex flex-col">
            {/* Configuration Header (Sticky) */}
             <section className="sticky top-0 z-30 bg-surface/80 backdrop-blur-md px-10 py-6 border-b border-outline-variant/30">
                <div className="max-w-6xl mx-auto">
                    {/* Templates Row */}
                    <div className="mb-8">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-[12px] font-semibold text-on-surface-variant uppercase tracking-[0.1em]">Select Intelligence Template</h3>
                        </div>
                        <div className="flex gap-4 overflow-x-auto pb-4 no-scrollbar">
                            {templates.map(t => (
                                <div 
                                    key={t.id} 
                                    onClick={() => handleTemplateSelect(t.id)}
                                    className={`flex-shrink-0 w-72 p-6 rounded-xl editorial-shadow group cursor-pointer transition-all ${
                                        selectedTemplate === t.id 
                                        ? "bg-surface-container-lowest border-2 border-primary-container relative" 
                                        : "bg-surface-container-lowest hover:bg-primary-container border-2 border-transparent"
                                    }`}
                                >
                                    {selectedTemplate === t.id && (
                                        <div className="absolute top-4 right-4 relative flex items-center justify-center border-none" style={{pointerEvents: 'none'}}>
                                            <span className="material-symbols-outlined text-primary-container" style={{fontVariationSettings: '"FILL" 1'}}>check_circle</span>
                                        </div>
                                    )}
                                    
                                    <span className={`material-symbols-outlined mb-4 text-3xl ${selectedTemplate === t.id ? "text-primary-container" : "text-indigo-600 group-hover:text-white"}`}>
                                        analytics
                                    </span>
                                    <h4 className={`font-bold text-lg mb-2 ${selectedTemplate === t.id ? "text-on-surface" : "group-hover:text-white"}`}>
                                        {t.name}
                                    </h4>
                                    <p className={`text-sm line-clamp-2 ${selectedTemplate === t.id ? "text-on-surface-variant" : "text-on-surface-variant group-hover:text-indigo-100"}`}>
                                        {t.description}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                    
                    {/* Skills Row */}
                    <div>
                        <h3 className="text-[12px] font-semibold text-on-surface-variant uppercase tracking-[0.1em] mb-4">Expert Skills Engaged</h3>
                        <div className="flex flex-wrap gap-3">
                            {skills.map(skill => {
                                const isSelected = selectedSkills.includes(skill.id);
                                return (
                                    <button 
                                        key={skill.id}
                                        onClick={() => handleSkillToggle(skill.id)}
                                        className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all ${
                                            isSelected 
                                            ? "bg-primary-container text-white" 
                                            : "bg-secondary-container/30 text-on-secondary-container border border-secondary-container/50 hover:bg-secondary-container/50"
                                        }`}
                                    >
                                        <span className="material-symbols-outlined text-sm" style={{fontVariationSettings: isSelected ? '"FILL" 1' : '"FILL" 0'}}>
                                            {isSelected ? 'verified' : 'psychology_alt'}
                                        </span>
                                        <span className="text-sm font-semibold">{skill.name.split(" ")[1] || skill.name}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </section>

            {/* Generation Canvas */}
            <section className="px-10 py-8 pb-32 flex-1 overflow-y-auto">
                <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-10">
                    
                    {/* Left: Editor/Preview */}
                    <div className="lg:col-span-8 space-y-8">
                        {generating ? (
                             <div className="rounded-xl border-2 border-outline-variant bg-surface-container-low min-h-[600px] flex flex-col items-center justify-center p-12 text-center group transition-all editorial-shadow">
                                <div className="relative mb-6">
                                     <div className="w-20 h-20 bg-surface-container-lowest rounded-full flex items-center justify-center editorial-shadow animate-pulse">
                                         <span className="material-symbols-outlined text-4xl text-primary animate-spin">autorenew</span>
                                     </div>
                                </div>
                                <h2 className="text-2xl font-black text-on-surface mb-2 animate-pulse">Synthesizing Data Vectors</h2>
                                <p className="text-on-surface-variant max-w-sm mt-2">Architect Intelligence is currently resolving multi-hop variables and executing specialized skill chains.</p>
                             </div>
                        ) : report ? (
                             <div className="rounded-xl border border-outline-variant bg-surface-container-lowest min-h-[600px] flex flex-col items-center justify-center p-12 text-center group transition-all editorial-shadow">
                                <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mb-6">
                                    <span className="material-symbols-outlined text-4xl text-primary" style={{fontVariationSettings: '"FILL" 1'}}>task_alt</span>
                                </div>
                                <h2 className="text-2xl font-black text-on-surface mb-2">Report Successfully Generated</h2>
                                <p className="text-on-surface-variant max-w-sm mb-8">Your intelligence synthesis is ready for review.</p>
                                <button 
                                    onClick={() => setIsOverlayOpen(true)}
                                    className="flex items-center gap-3 bg-primary text-white px-8 py-4 rounded-xl font-bold editorial-shadow hover:scale-105 transition-all"
                                >
                                    <span className="material-symbols-outlined">fullscreen</span>
                                    Open Reading Mode
                                </button>
                             </div>
                        ) : (
                            <div className="rounded-xl border-2 border-dashed border-outline-variant bg-surface-container-low min-h-[600px] flex flex-col items-center justify-center p-12 text-center group transition-all">
                                <div className="w-20 h-20 bg-surface-container-lowest rounded-full flex items-center justify-center mb-6 editorial-shadow">
                                    <span className="material-symbols-outlined text-4xl text-outline-variant">description</span>
                                </div>
                                <h2 className="text-2xl font-black text-on-surface mb-2">Report Canvas Empty</h2>
                                <p className="text-on-surface-variant max-w-sm">Configure your intelligence parameters above, select a document from the right panel, and click Generate.</p>
                               
                                <div className="mt-10">
                                    <button 
                                        onClick={handleGenerate}
                                        disabled={!selectedDoc || !selectedTemplate}
                                        className={`relative flex items-center gap-3 px-10 py-5 rounded-xl font-black text-lg transition-all group ${!selectedDoc ? "bg-surface-variant text-outline cursor-not-allowed" : "bg-gradient-to-br from-primary to-primary-container text-white editorial-shadow hover:scale-[1.02] active:scale-95"}`}
                                    >
                                        <span className={`material-symbols-outlined text-2xl transition-transform ${selectedDoc ? "group-hover:rotate-12" : ""}`}>rocket_launch</span>
                                        <span>Generate Intelligence Report</span>
                                        {selectedDoc && <div className="absolute -inset-1 bg-primary/20 rounded-xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity"></div>}
                                    </button>
                                </div>
                                {error && <p className="text-error font-bold mt-4 bg-error-container px-4 py-2 rounded-lg">{error}</p>}
                            </div>
                        )}
                    </div>

                    {/* Right: Insights/Stats */}
                    <div className="lg:col-span-4 space-y-6">
                        <div className="p-8 rounded-xl bg-surface-container-lowest editorial-shadow">
                            <h3 className="text-sm font-black uppercase tracking-widest text-primary mb-6">Source Intelligence</h3>
                            <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                {documents.length === 0 ? (
                                     <p className="text-sm text-outline">No documents available.</p>
                                ) : (
                                    documents.map(doc => (
                                        <div 
                                            key={doc.collection_name} 
                                            onClick={() => setSelectedDoc(doc.collection_name)}
                                            className={`flex items-start gap-4 p-3 rounded-xl cursor-pointer transition-colors border ${selectedDoc === doc.collection_name ? "bg-indigo-50 border-primary/20 shadow-sm" : "border-transparent hover:bg-surface-container-low"}`}
                                        >
                                            <div className={`p-2 rounded-lg ${selectedDoc === doc.collection_name ? "bg-primary text-white" : "bg-indigo-50 text-indigo-600"}`}>
                                                <span className="material-symbols-outlined text-xl">picture_as_pdf</span>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <h5 className="text-sm font-bold text-on-surface truncate">{doc.file_name}</h5>
                                                <p className="text-[11px] text-on-surface-variant truncate">Indexed: {doc.indexed_at.substring(0, 10)}</p>
                                            </div>
                                            {selectedDoc === doc.collection_name && (
                                                 <span className="material-symbols-outlined text-primary text-sm mt-1">check_circle</span>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div className="p-8 rounded-xl bg-gradient-to-br from-indigo-900 to-slate-900 text-white editorial-shadow relative overflow-hidden">
                            <div className="relative z-10">
                                <h3 className="text-sm font-black uppercase tracking-widest text-indigo-200 mb-6">Processing Power</h3>
                                <div className="flex items-end gap-3 mb-2">
                                    <span className="text-4xl font-black tracking-tighter">Local</span>
                                    <span className="text-sm font-medium text-indigo-300 mb-1">{provider}</span>
                                </div>
                                <div className="w-full bg-white/10 h-1.5 rounded-full mt-4 overflow-hidden">
                                    <div className={`bg-primary h-full rounded-full transition-all duration-1000 ${generating ? "w-full animate-pulse" : "w-2/3"}`}></div>
                                </div>
                                <p className="text-xs text-indigo-200 mt-4 leading-relaxed">
                                    {generating ? "High-fidelity reasoning mode active. Synthesizing data..." : "Model ready. Awaiting request for document intelligence."}
                                    <br/><br/>
                                    <span className="opacity-70 font-mono text-[10px]">Context Window: {context_window || "Default"}</span>
                                </p>
                            </div>
                            <div className="absolute -right-4 -bottom-4 opacity-10">
                                <span className="material-symbols-outlined text-[120px]">hub</span>
                            </div>
                        </div>
                    </div>

                </div>
            </section>

            {/* Hidden Report Preview Overlay */}
            {isOverlayOpen && (
                <div className="fixed inset-0 z-[100] bg-on-surface/60 backdrop-blur-sm flex items-center justify-center p-4 md:p-10 animate-in fade-in duration-300">
                    <div className="bg-surface-container-lowest w-full max-w-5xl h-full rounded-xl flex flex-col editorial-shadow overflow-hidden">
                        
                        <div className="p-4 md:p-6 border-b border-surface-container flex items-center justify-between bg-surface-container-low shadow-sm z-10">
                            <div className="flex items-center gap-4">
                                <div className="p-2 bg-primary/10 rounded-lg">
                                    <span className="material-symbols-outlined text-primary">article</span>
                                </div>
                                <div>
                                    <h2 className="font-black text-lg md:text-xl tracking-tight text-on-surface">{selectedTemplateObj?.name || "Report"}</h2>
                                    <p className="text-xs text-on-surface-variant hidden md:block">Architect Intelligence Output</p>
                                </div>
                            </div>
                            
                            <div className="flex items-center gap-2 md:gap-3">
                                <button onClick={handleCopyReport} className="px-3 py-2 md:px-4 md:py-2 text-sm font-bold text-on-surface-variant hover:bg-white hover:shadow-sm transition-all rounded-lg flex items-center gap-2">
                                    <span className="material-symbols-outlined text-lg">content_copy</span> <span className="hidden md:inline">Copy</span>
                                </button>
                                <button onClick={handleDownloadWord} className="px-3 py-2 md:px-4 md:py-2 text-sm font-bold text-on-surface-variant hover:bg-white hover:shadow-sm transition-all rounded-lg flex items-center gap-2">
                                    <span className="material-symbols-outlined text-lg">description</span> <span className="hidden md:inline">Word</span>
                                </button>
                                {/* <button className="px-4 py-2 md:px-6 bg-primary text-white font-bold rounded-lg shadow-md hover:bg-primary-fixed-variant transition-colors text-sm">PDF</button> */}
                                <button onClick={() => setIsOverlayOpen(false)} className="p-2 ml-2 hover:bg-red-50 text-red-500 rounded-full transition-colors flex items-center justify-center">
                                    <span className="material-symbols-outlined">close</span>
                                </button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto bg-slate-100 p-4 md:p-12 relative">
                            <article className="max-w-3xl mx-auto bg-white p-8 md:p-16 shadow-[0px_10px_40px_rgba(0,0,0,0.05)] rounded-xl min-h-[1000px] prose prose-slate">
                                <header className="mb-12 border-b-4 border-primary pb-8">
                                    <p className="text-xs font-black uppercase tracking-widest text-primary mb-3">Generated Report</p>
                                    <h1 className="text-3xl md:text-4xl font-black tracking-tight text-on-surface leading-tight">
                                        {selectedTemplateObj?.name || "Intelligence Report"}
                                    </h1>
                                    <p className="text-slate-500 mt-4 text-sm font-medium italic">
                                        Source: {documents.find(d => d.collection_name === selectedDoc)?.file_name}
                                    </p>
                                </header>
                                
                                <div className="prose prose-indigo prose-headings:font-black max-w-none text-slate-800">
                                    {report ? (
                                        <MarkdownRenderer content={report.content} />
                                    ) : (
                                        <p>No content available.</p>
                                    )}
                                </div>
                            </article>
                        </div>

                    </div>
                </div>
            )}
        </div>
    );
}
