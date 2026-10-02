"use client";

import React, { Suspense, useState, useEffect } from "react";
import { RTLHierarchyBrowser } from "@/components/diagram/RTLHierarchyBrowser";
import { FileCode, ChevronLeft, RotateCcw, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";

export default function RTLHierarchyPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center text-slate-400">
          Loading hierarchy...
        </div>
      }
    >
      <RTLHierarchyView />
    </Suspense>
  );
}

function RTLHierarchyView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const designId = searchParams.get("designId");
  const projectId = searchParams.get("projectId");
  const [designs, setDesigns] = useState<any[]>([]);
  const [selectedDesign, setSelectedDesign] = useState<string | null>(designId || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDesigns();
  }, []);

  const fetchDesigns = async () => {
    try {
      const res = await api.listProjects();
      if (res.data.length > 0) {
        const firstProject = res.data[0];
        const projectRes = await api.getProjectSummary(firstProject.id);
        setDesigns(projectRes.data.designs || []);
      }
    } catch (err) {
      console.error("Failed to fetch designs:", err);
    }
  };

  const handleDesignChange = (id: string) => {
    setSelectedDesign(id);
    router.push(`/rtl/hierarchy?projectId=${projectId || ''}&designId=${id}`);
  };

  const handleRefresh = async () => {
    if (!selectedDesign) return;
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
    } catch (err) {
      console.error("Refresh failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleExportDiagram = async (format: "mermaid" | "graphviz" | "json") => {
    if (!selectedDesign) return;
    try {
      const res = await api.generateDiagram(selectedDesign, "mermaid");
      const blob = new Blob([res.data.diagram], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `hierarchy.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileCode className="w-6 h-6 text-blue-400" />
              <h1 className="text-xl font-bold text-white">RTL Hierarchy Browser</h1>
              <span className="px-2 py-0.5 text-xs bg-blue-900/30 text-blue-300 rounded">
                RTL Hierarchy
              </span>
            </div>
            <div className="flex items-center gap-3">
              {designs.length > 0 && (
                <select
                  value={selectedDesign || ""}
                  onChange={e => handleDesignChange(e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">Select Design...</option>
                  {designs.map(d => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              )}
              <button
                onClick={() => router.push("/rtl")}
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                title="Back to RTL Explorer"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {selectedDesign ? (
          <RTLHierarchyBrowser
            projectId={projectId || ""}
            designId={selectedDesign}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <FileCode className="w-16 h-16 text-gray-600 mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">No Design Selected</h2>
            <p className="text-gray-400 mb-6 max-w-md">
              Select a design from the dropdown or go to the RTL Explorer to upload/analyze a design first.
            </p>
            <button
              onClick={() => router.push("/rtl")}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center gap-2"
            >
              <FileCode className="w-5 h-5" />
              Go to RTL Explorer
            </button>
          </div>
        )}
      </main>
    </div>
  );
}