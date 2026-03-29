"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { indexDocument, uploadFile } from "@/lib/api";
import { UploadCloud, CheckCircle2 } from "lucide-react";

export function FileUploader({
    onUploadComplete,
    className
}: {
    onUploadComplete: () => void;
    className?: string;
}) {
    const [isUploading, setIsUploading] = useState(false);
    const [chunkingStrategy, setChunkingStrategy] = useState<"semantic" | "fixed">("semantic");
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        setError(null);
        setSuccess(null);

        try {
            // 1. Upload the file to the server
            const uploadRes = await uploadFile(file);
            if (!uploadRes.success) {
                setError(uploadRes.message || "上傳失敗");
                return;
            }

            // 2. Index the uploaded file using its server path
            const indexRes = await indexDocument(uploadRes.file_path, chunkingStrategy);
            if (indexRes.success) {
                setSuccess(`✓ ${file.name} 已成功索引 (${chunkingStrategy === "semantic" ? "語意切分" : "固定長度"})`);
                onUploadComplete();
            } else {
                setError(indexRes.message || "索引失敗");
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "處理失敗");
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <Card className={`p-4 border-dashed border-2 border-slate-200 bg-slate-50/50 ${className || ""}`}>
            <div className="flex flex-col items-center justify-center space-y-3">
                <div className="text-slate-400">
                    <UploadCloud size={32} />
                </div>
                <div className="text-center">
                    <p className="text-sm font-medium text-slate-700">點擊或拖曳檔案至此</p>
                    <p className="text-xs text-slate-500 mt-1">支援 PDF, TXT, DOCX, XLSX, CSV, JSON</p>
                </div>
                <div className="flex items-center gap-4 py-1">
                    <label className="flex items-center gap-1.5 cursor-pointer">
                        <input
                            type="radio"
                            name="strategy"
                            checked={chunkingStrategy === "semantic"}
                            onChange={() => setChunkingStrategy("semantic")}
                            disabled={isUploading}
                            className="w-3 h-3 text-blue-600"
                        />
                        <span className="text-xs font-medium text-slate-600">語意切分 (精確)</span>
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer">
                        <input
                            type="radio"
                            name="strategy"
                            checked={chunkingStrategy === "fixed"}
                            onChange={() => setChunkingStrategy("fixed")}
                            disabled={isUploading}
                            className="w-3 h-3 text-blue-600"
                        />
                        <span className="text-xs font-medium text-slate-600">固定長度</span>
                    </label>
                </div>

                <input
                    type="file"
                    id="file-upload"
                    className="hidden"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                    accept=".pdf,.txt,.docx,.xlsx,.csv,.json"
                />
                <Button
                    asChild
                    variant="outline"
                    size="sm"
                    disabled={isUploading}
                    className="cursor-pointer"
                >
                    <label htmlFor="file-upload">
                        {isUploading ? "正在索引..." : "選擇檔案並上傳"}
                    </label>
                </Button>
                {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
                {success && <p className="text-xs text-green-600 mt-2">{success}</p>}
            </div>
        </Card>
    );
}
