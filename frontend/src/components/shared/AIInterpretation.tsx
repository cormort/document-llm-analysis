/**
 * AIInterpretation - Unified AI Interpretation Component
 *
 * A reusable component for displaying AI-generated interpretations across
 * different parts of the application (Profiling, Correlation, Inference, etc.)
 */

"use client";

import { useState, ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import ReactMarkdown from "react-markdown";
import { Loader2 } from "lucide-react";

interface AIInterpretationProps {
    /** Title displayed in the header */
    title: string;
    /** Description shown below the title */
    description?: string;
    /** Async function that returns the AI interpretation text */
    onRequest: () => Promise<string>;
    /** Custom button text (default: "AI 解讀") */
    buttonText?: string;
    /** Icon to display next to the title */
    icon?: ReactNode;
    /** Border color class (default: blue) */
    borderColor?: string;
    /** Background color class */
    bgColor?: string;
    /** Whether the component is initially collapsed */
    defaultCollapsed?: boolean;
}

export function AIInterpretation({
    title,
    description,
    onRequest,
    buttonText = "🤖 AI 解讀",
    icon,
    borderColor = "border-l-blue-500",
    bgColor = "bg-blue-50",
}: AIInterpretationProps) {
    const [result, setResult] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleRequest = async () => {
        setLoading(true);
        setError(null);
        setResult("");

        try {
            const interpretation = await onRequest();
            setResult(interpretation);
        } catch (err) {
            console.error("AI interpretation failed:", err);
            setError(err instanceof Error ? err.message : "解讀失敗，請稍後再試");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className={`p-6 border-l-4 ${borderColor}`}>
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    {icon}
                    <div>
                        <h3 className="font-bold text-slate-700">{title}</h3>
                        {description && (
                            <p className="text-xs text-slate-500">{description}</p>
                        )}
                    </div>
                </div>
                <Button
                    onClick={handleRequest}
                    disabled={loading}
                    variant="outline"
                    size="sm"
                    className="gap-2"
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            分析中...
                        </>
                    ) : (
                        buttonText
                    )}
                </Button>
            </div>

            {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                    ❌ {error}
                </div>
            )}

            {result && !error && (
                <div className={`mt-4 p-4 ${bgColor} border rounded-lg text-sm text-slate-800 leading-relaxed prose prose-sm max-w-none`}>
                    <ReactMarkdown>{result}</ReactMarkdown>
                </div>
            )}
        </Card>
    );
}

/**
 * Lightweight inline version for smaller spaces
 */
interface AIInterpretationInlineProps {
    onRequest: () => Promise<string>;
    buttonText?: string;
}

export function AIInterpretationInline({
    onRequest,
    buttonText = "🤖 AI 解讀",
}: AIInterpretationInlineProps) {
    const [result, setResult] = useState<string>("");
    const [loading, setLoading] = useState(false);

    const handleRequest = async () => {
        setLoading(true);
        setResult("");
        try {
            const interpretation = await onRequest();
            setResult(interpretation);
        } catch (err) {
            console.error(err);
            setResult("解讀失敗");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-3">
            <Button
                onClick={handleRequest}
                disabled={loading}
                variant="ghost"
                size="sm"
                className="text-blue-600 hover:text-blue-700 gap-1"
            >
                {loading ? (
                    <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        分析中...
                    </>
                ) : (
                    buttonText
                )}
            </Button>
            {result && (
                <div className="p-3 bg-blue-50 rounded-lg text-sm text-slate-700 leading-relaxed">
                    <ReactMarkdown>{result}</ReactMarkdown>
                </div>
            )}
        </div>
    );
}
