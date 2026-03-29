/**
 * CommandCenter - Premium Floating Query Interface
 * 
 * Replaces the traditional "Quick Query Bar" with a Spotlight-style
 * command center. Features glassmorphism, fluid animations, and 
 * premium typography.
 */

"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { generatePandasQuery, executeQuery, interpretQuery, QueryExecuteResponse } from "@/lib/api";
import { useSettingsStore } from "@/stores/settings-store";
import { MarkdownRenderer } from "@/components/chat/markdown-renderer";
import { 
    Loader2, 
    Sparkles, 
    Bot, 
    XCircle, 
    Command,
    Terminal
} from "lucide-react";
import { cn } from "@/lib/utils";

interface CommandCenterProps {
    filePath: string | null;
    className?: string;
}

export function CommandCenter({ filePath, className }: CommandCenterProps) {
    const { provider, model_name, local_url, api_key } = useSettingsStore();

    const [isFocused, setIsFocused] = useState(false);
    const [question, setQuestion] = useState("");
    const [processing, setProcessing] = useState(false);
    const [generatedCode, setGeneratedCode] = useState<string | null>(null);
    const [queryResult, setQueryResult] = useState<QueryExecuteResponse | null>(null);
    const [interpretation, setInterpretation] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Expand when focused or when there are results
    const isExpanded = isFocused || !!queryResult || processing || !!generatedCode || question.length > 0;

    const handleQuery = async () => {
        if (!filePath || !question.trim()) return;

        setProcessing(true);
        setQueryResult(null);
        setInterpretation(null);
        setGeneratedCode(null);

        const config = {
            provider,
            model_name,
            local_url,
            api_key: api_key || undefined
        };

        try {
            // 1. Generate code
            const { pandas_code } = await generatePandasQuery(filePath, question, config);
            setGeneratedCode(pandas_code);

            // 2. Execute code
            const res = await executeQuery({
                file_path: filePath,
                pandas_code
            });
            setQueryResult(res);

            // 3. Interpret if successful
            if (res.success && res.data) {
                const { interpretation: intro } = await interpretQuery(
                    question,
                    res.summary || "",
                    res.data.slice(0, 5),
                    config
                );
                setInterpretation(intro);
            }
        } catch (err) {
            console.error("Query failed", err);
        } finally {
            setProcessing(false);
        }
    };

    const handleClear = () => {
        setQuestion("");
        setQueryResult(null);
        setInterpretation(null);
        setGeneratedCode(null);
        setIsFocused(false);
        if (inputRef.current) inputRef.current.blur();
    };

    if (!filePath) return null;

    return (
        <div className={cn("w-full transition-all duration-500 ease-out", className)}>
            {/* Main Floating Card */}
            <div 
                className={cn(
                    "relative overflow-hidden transition-all duration-500 rounded-2xl border",
                    isExpanded 
                        ? "bg-white/90 shadow-2xl border-indigo-100 ring-4 ring-indigo-50/50 backdrop-blur-xl" 
                        : "bg-white/60 shadow-lg border-slate-200/60 backdrop-blur-md hover:bg-white/80 hover:shadow-xl hover:border-indigo-100"
                )}
            >
                {/* Search Input Area */}
                <div className="relative flex items-center p-2">
                    <div className={cn(
                        "flex items-center justify-center w-12 h-12 rounded-xl transition-all duration-500",
                        isExpanded ? "bg-indigo-600 text-white rotate-12 scale-110" : "bg-slate-100 text-slate-400"
                    )}>
                        {processing ? <Loader2 className="w-6 h-6 animate-spin" /> : <Sparkles className="w-6 h-6" />}
                    </div>
                    
                    <div className="flex-1 ml-4 mr-2">
                         <input
                            ref={inputRef}
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            onFocus={() => setIsFocused(true)}
                            onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                            placeholder="Ask your data anything (e.g., 'Show top 5 revenue sources')..."
                            className="w-full bg-transparent border-none text-lg font-medium text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-0"
                            disabled={processing}
                        />
                    </div>

                    <div className="flex items-center gap-2">
                        {isExpanded && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleClear}
                                className="text-slate-400 hover:text-slate-600 rounded-full h-10 w-10 p-0"
                            >
                                <XCircle className="w-6 h-6" />
                            </Button>
                        )}
                        <Button
                            onClick={handleQuery}
                            disabled={processing || !question.trim()}
                            className={cn(
                                "h-12 px-6 rounded-xl font-bold transition-all duration-300",
                                !question.trim() 
                                    ? "bg-slate-100 text-slate-300 pointer-events-none" 
                                    : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-200"
                            )}
                        >
                            <span className="mr-2">Run</span> <Command size={16} />
                        </Button>
                    </div>
                </div>

                {/* Expanded Result Area */}
                <div className={cn(
                    "grid transition-all duration-500 ease-in-out px-4",
                    isExpanded && (generatedCode || queryResult) ? "grid-rows-[1fr] opacity-100 pb-6 pt-2" : "grid-rows-[0fr] opacity-0"
                )}>
                    <div className="overflow-hidden min-h-0 space-y-6">
                        {/* Divider */}
                        <div className="h-px w-full bg-gradient-to-r from-transparent via-slate-200 to-transparent" />

                        {/* Generated Code */}
                        {generatedCode && (
                            <div className="p-4 bg-slate-900/95 rounded-xl border border-slate-800 shadow-inner group relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Badge variant="secondary" className="bg-slate-800 text-white border-slate-700">Python</Badge>
                                </div>
                                <div className="flex items-center gap-2 mb-3 text-slate-400">
                                    <Terminal size={14} />
                                    <span className="text-xs font-mono uppercase tracking-widest font-bold">Generated Logic</span>
                                </div>
                                <pre className="text-sm font-mono text-emerald-400 overflow-x-auto custom-scrollbar">
                                    <code>{generatedCode}</code>
                                </pre>
                            </div>
                        )}

                        {/* Results */}
                        {queryResult && (
                            <div className="space-y-4 animate-in slide-in-from-bottom-4 duration-500">
                                {queryResult.success ? (
                                    <>
                                        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                                             <div className="px-6 py-3 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Result Data</span>
                                                </div>
                                                <Badge variant="outline" className="bg-white">{queryResult.summary}</Badge>
                                            </div>
                                            <div className="overflow-x-auto max-h-[300px] custom-scrollbar">
                                                <table className="min-w-full divide-y divide-slate-100">
                                                    <thead className="bg-slate-50 underline-offset-4">
                                                        <tr>
                                                            {queryResult.data && queryResult.data.length > 0 && Object.keys(queryResult.data[0]).map((key) => (
                                                                <th key={key} className="px-6 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                                                                    {key}
                                                                </th>
                                                            ))}
                                                        </tr>
                                                    </thead>
                                                    <tbody className="bg-white divide-y divide-slate-50">
                                                        {queryResult.data?.slice(0, 10).map((row, idx) => (
                                                            <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                                                                {Object.values(row as Record<string, unknown>).map((val, vIdx) => (
                                                                    <td key={vIdx} className="px-6 py-3 whitespace-nowrap text-sm text-slate-600 font-medium font-mono">
                                                                        {String(val)}
                                                                    </td>
                                                                ))}
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                            {queryResult.data && queryResult.data.length > 10 && (
                                                <div className="bg-slate-50 px-6 py-2 text-center text-xs text-slate-400 italic">
                                                    Showing first 10 rows
                                                </div>
                                            )}
                                        </div>

                                        {interpretation && (
                                            <div className="p-6 bg-gradient-to-br from-indigo-50 to-white rounded-xl border border-indigo-100 shadow-sm relative overflow-hidden">
                                                <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-100 rounded-full blur-3xl -translate-y-16 translate-x-16 opacity-50 pointer-events-none" />
                                                <h4 className="font-bold text-indigo-900 mb-3 text-sm flex items-center gap-2 relative z-10">
                                                    <Bot className="w-5 h-5 text-indigo-600"/> Expert Insight
                                                </h4>
                                                <div className="text-slate-700 text-sm leading-relaxed relative z-10">
                                                    <MarkdownRenderer content={interpretation} />
                                                </div>
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <div className="p-6 bg-red-50 rounded-xl border border-red-100 text-center animate-in shake">
                                        <div className="w-12 h-12 bg-red-100 text-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <XCircle size={24} />
                                        </div>
                                        <h4 className="font-bold text-red-900 mb-2">Query Execution Failed</h4>
                                        <p className="text-red-600 text-sm font-mono bg-red-100/50 p-3 rounded inline-block max-w-[90%]">
                                            {queryResult.error}
                                        </p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
