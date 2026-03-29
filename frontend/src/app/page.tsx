"use client";

import Link from "next/link";
import { prefetch } from "next/navigation";
import {
  Bot,
  Search,
  BarChart2,
  FileText,
  Database,
  ArrowRight
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { useEffect, useState } from "react";

const tools = [
  {
    title: "Agent Workspace",
    description: "Chat with your documents using our advanced Agentic AI flow.",
    icon: Bot,
    href: "/agent",
    color: "bg-gradient-to-br from-indigo-500 to-purple-600",
    featured: true
  },
  {
    title: "RAG Search",
    description: "Semantic search and document retrieval system.",
    icon: Search,
    href: "/rag",
    color: "bg-blue-50"
  },
  {
    title: "Statistical Analysis",
    description: "Exploratory Data Analysis (EDA) and visualization.",
    icon: BarChart2,
    href: "/stats",
    color: "bg-green-50"
  },
  {
    title: "Report Generation",
    description: "Automated report writing based on templates.",
    icon: FileText,
    href: "/reports",
    color: "bg-amber-50"
  },
  {
    title: "Data Query",
    description: "SQL-based data querying and transformation.",
    icon: Database,
    href: "/query",
    color: "bg-slate-50"
  }
];

export default function Dashboard() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50/50">
      <div className="max-w-6xl mx-auto px-6 py-12">
        <header className="mb-12">
          <h1 className="text-3xl font-bold text-slate-900">Document LLM Analysis</h1>
          <p className="text-slate-500 mt-2">Select a tool to begin your analysis workflow.</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tools.map((tool) => (
            <Link 
              key={tool.title} 
              href={tool.href} 
              className="block group h-full"
              prefetch={tool.featured}
            >
              <Card className={`h-full border-slate-200 transition-all duration-200 hover:shadow-lg hover:-translate-y-1 ${tool.featured ? 'ring-2 ring-indigo-500 shadow-md transform scale-[1.02]' : 'hover:border-slate-300'}`}>
                <div className="p-6 h-full flex flex-col">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${tool.featured ? tool.color : tool.color}`}>
                    <tool.icon className={`w-6 h-6 ${tool.featured ? 'text-white' : 'text-blue-600'}`} />
                  </div>

                  <h3 className="text-lg font-bold text-slate-800 mb-2 group-hover:text-blue-600 transition-colors">
                    {tool.title}
                  </h3>
                  <p className="text-slate-500 text-sm mb-6 flex-1">
                    {tool.description}
                  </p>

                  <div className={`flex items-center text-sm font-medium ${tool.featured ? 'text-indigo-600' : 'text-slate-400 group-hover:text-blue-600'}`}>
                    Open Tool <ArrowRight className="w-4 h-4 ml-1" />
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
