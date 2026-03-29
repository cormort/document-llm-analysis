"use client";

import { Settings } from "lucide-react";

interface HeaderProps {
    title: string;
    subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
    return (
        <header className="border-b border-slate-200 bg-white/80 backdrop-blur-md px-6 py-4 sticky top-0 z-10 transition-all duration-300">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">{title}</h1>
                    {subtitle && <p className="text-sm text-slate-500 mt-1 font-medium">{subtitle}</p>}
                </div>
                <div className="flex items-center gap-4">
                    {/* Settings button placeholder */}
                    <button className="p-2.5 rounded-xl hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-all duration-200">
                        <Settings size={20} />
                    </button>
                </div>
            </div>
        </header>
    );
}
