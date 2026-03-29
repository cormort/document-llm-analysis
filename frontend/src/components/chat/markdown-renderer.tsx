"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
    content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
    return (
        <div className="markdown-renderer prose prose-slate max-w-none prose-sm">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    code({ node, className, children, ...props }) {
                        return (
                            <code className="bg-slate-200 px-1 rounded text-pink-600 font-mono text-xs" {...props}>
                                {children}
                            </code>
                        );
                    },
                    pre({ node, ...props }) {
                        return (
                            <pre className="not-prose bg-slate-800 text-slate-100 p-3 rounded-lg my-2 overflow-x-auto text-xs" {...props} />
                        );
                    },
                    table({ node, ...props }) {
                        return (
                            <div className="overflow-x-auto my-4">
                                <table className="min-w-full divide-y divide-slate-300 border border-slate-300 rounded-lg" {...props} />
                            </div>
                        );
                    },
                    th({ node, ...props }) {
                        return (
                            <th className="px-3 py-2 bg-slate-100 text-left font-semibold text-slate-900" {...props} />
                        );
                    },
                    td({ node, ...props }) {
                        return (
                            <td className="px-3 py-2 border-t border-slate-200" {...props} />
                        );
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
