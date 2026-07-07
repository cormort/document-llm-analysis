"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { downloadReportDocx } from "@/lib/api";
import { Copy, Check, FileDown, FileText, Loader2 } from "lucide-react";

interface Props {
    content: string;
    title: string;
}

// 匯出 AI 解讀：複製 / Markdown / Word
export function ExportInterpretation({ content, title }: Props) {
    const [copied, setCopied] = useState(false);
    const [downloading, setDownloading] = useState(false);

    const copy = async () => {
        await navigator.clipboard.writeText(content);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    const downloadMd = () => {
        const blob = new Blob([`# ${title}\n\n${content}`], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${title}.md`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const downloadDocx = async () => {
        setDownloading(true);
        try {
            await downloadReportDocx(content, title);
        } catch (e) {
            console.error("Word 匯出失敗", e);
        } finally {
            setDownloading(false);
        }
    };

    return (
        <div className="flex items-center gap-2 justify-end">
            <Button variant="ghost" size="sm" onClick={copy} className="h-7 text-xs gap-1 opacity-70 hover:opacity-100">
                {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />} 複製
            </Button>
            <Button variant="ghost" size="sm" onClick={downloadMd} className="h-7 text-xs gap-1 opacity-70 hover:opacity-100">
                <FileDown size={12} /> Markdown
            </Button>
            <Button variant="ghost" size="sm" onClick={downloadDocx} disabled={downloading} className="h-7 text-xs gap-1 opacity-70 hover:opacity-100">
                {downloading ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />} Word
            </Button>
        </div>
    );
}
