"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import {
LayoutDashboard,
Bot,
FileText,
Database,
LineChart,
ChevronLeft,
ChevronRight,
LogIn,
LogOut,
Users,
BarChart3,
User,
Settings,
Globe,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { LLMSelector } from "@/components/settings/llm-selector";
import { useAuthStore } from "@/stores/auth-store";
import { useAnalytics } from "@/hooks/useAnalytics";

const navItems = [
{ href: "/", label: "Dashboard", icon: LayoutDashboard },
{ href: "/rag", label: "RAG 問答", icon: Bot },
{ href: "/reports", label: "產生報告", icon: FileText },
{ href: "/query", label: "數據查詢", icon: Database },
{ href: "/stats", label: "統計分析", icon: LineChart },
];

const adminNavItems = [
{ href: "/admin", label: "管理首頁", icon: LayoutDashboard },
{ href: "/admin/users", label: "用戶管理", icon: Users },
{ href: "/admin/analytics", label: "行為報表", icon: BarChart3 },
{ href: "/admin/ip", label: "IP 管理", icon: Globe },
{ href: "/admin/settings", label: "系統設定", icon: Settings },
];

export function Sidebar() {
const pathname = usePathname();
const router = useRouter();
const [collapsed, setCollapsed] = useState(false);
const { user, isAuthenticated, logout } = useAuthStore();
const { trackClick } = useAnalytics();

const handleLogout = () => {
trackClick("logout_button");
logout();
router.push("/login");
};

return (
<aside
className={`${collapsed ? "w-16" : "w-64"} min-h-screen bg-slate-900/95 backdrop-blur-xl border-r border-white/5 text-white transition-all duration-300 flex flex-col z-50 shadow-2xl`}
>
{/* Header */}
<div className="p-4 border-b border-white/10 flex items-center justify-between h-16">
{!collapsed && (
<h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent animate-in fade-in duration-300">
Doc Analysis
</h1>
)}
<Button
variant="ghost"
size="icon"
onClick={() => {
trackClick("sidebar_toggle");
setCollapsed(!collapsed);
}}
className="ml-auto text-slate-400 hover:text-white hover:bg-white/10 h-8 w-8"
>
{collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
</Button>
</div>

{/* LLM Settings - Moved to top */}
<LLMSelector collapsed={collapsed} />

{/* Navigation */}
<nav className="flex-1 p-3 space-y-1 overflow-y-auto custom-scrollbar">
{navItems.map((item) => {
const isActive = pathname === item.href;
const Icon = item.icon;
return (
<Link
key={item.href}
href={item.href}
onClick={() => trackClick(`nav_${item.label}`)}
className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group relative ${
isActive
? "bg-blue-600/20 text-blue-400 ring-1 ring-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.15)]"
: "text-slate-400 hover:bg-white/5 hover:text-slate-100"
}`}
>
<Icon size={20} className={`${isActive ? "text-blue-400" : "text-slate-400 group-hover:text-slate-200"}`} />

{!collapsed && (
<span className="font-medium text-sm tracking-wide">
{item.label}
</span>
)}

{/* Tooltip for collapsed mode */}
{collapsed && (
<div className="absolute left-full ml-2 px-2 py-1 bg-slate-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none border border-white/10 shadow-xl">
{item.label}
</div>
)}
</Link>
);
})}

{/* Admin Section */}
{isAuthenticated && user?.is_admin && (
<>
{!collapsed && (
<div className="px-3 pt-4 pb-2">
<span className="text-xs text-slate-500 font-medium">管理功能</span>
</div>
)}
{adminNavItems.map((item) => {
const isActive = pathname === item.href;
const Icon = item.icon;
return (
<Link
key={item.href}
href={item.href}
onClick={() => trackClick(`nav_${item.label}`)}
className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group relative ${
isActive
? "bg-purple-600/20 text-purple-400 ring-1 ring-purple-500/30"
: "text-slate-400 hover:bg-white/5 hover:text-slate-100"
}`}
>
<Icon size={20} className={`${isActive ? "text-purple-400" : "text-slate-400 group-hover:text-slate-200"}`} />

{!collapsed && (
<span className="font-medium text-sm tracking-wide">
{item.label}
</span>
)}

{collapsed && (
<div className="absolute left-full ml-2 px-2 py-1 bg-slate-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none border border-white/10 shadow-xl">
{item.label}
</div>
)}
</Link>
);
})}
</>
)}
</nav>

{/* User Section */}
<div className="p-4 border-t border-white/10 bg-black/20">
{isAuthenticated && user ? (
<div className="space-y-2">
{!collapsed && (
<div className="flex items-center gap-2 px-2 mb-2">
<User size={16} className="text-slate-400" />
<span className="text-sm text-slate-300 truncate">{user.username}</span>
</div>
)}
<Button
variant="ghost"
size={collapsed ? "icon" : "default"}
onClick={handleLogout}
className={`w-full justify-start text-slate-400 hover:text-white hover:bg-white/10 ${
collapsed ? "px-2" : ""
}`}
>
<LogOut size={16} />
{!collapsed && <span className="ml-2">登出</span>}
</Button>
</div>
) : (
<Link href="/login">
<Button
variant="ghost"
size={collapsed ? "icon" : "default"}
onClick={() => trackClick("login_button_sidebar")}
className={`w-full justify-start text-slate-400 hover:text-white hover:bg-white/10 ${
collapsed ? "px-2" : ""
}`}
>
<LogIn size={16} />
{!collapsed && <span className="ml-2">登入</span>}
</Button>
</Link>
)}

{!collapsed && !isAuthenticated && (
<p className="text-[10px] text-slate-500 font-mono text-center mt-2">
© 2026 PRO MAX
</p>
)}
</div>
</aside>
);
}
