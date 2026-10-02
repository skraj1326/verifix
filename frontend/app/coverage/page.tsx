"use client";

import React, { Suspense, useState, useEffect } from "react";
import { CoverageDashboard } from "@/components/coverage/CoverageDashboard";
import { FileCode, ChevronLeft, TrendingUp, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";

// useSearchParams() opts a route out of static prerendering unless it is read
// inside a Suspense boundary, so the page wraps its content below.
export default function CoverageDashboardPage() {
  return (
    <Suspense fallback={<PageFallback label="Loading coverage" />}>
      <CoverageDashboardContent />
    </Suspense>
  );
}

function PageFallback({ label }: { label: string }) {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
        <p className="mt-3 text-sm text-muted-foreground">{label}...</p>
      </div>
    </div>
  );
}

function CoverageDashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = searchParams.get("projectId");
  const simulationId = searchParams.get("simulationId");
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<string | null>(projectId || null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await api.listProjects();
      setProjects(res.data);
      if (res.data.length > 0 && !selectedProject) {
        setSelectedProject(res.data[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch projects:", err);
    }
  };

  const handleProjectChange = (id: string) => {
    setSelectedProject(id);
    router.push(`/coverage?projectId=${id}`);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Coverage Dashboard</h1>
                <p className="text-sm text-gray-400">Interactive coverage analytics & drill-down</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {projects.length > 0 && (
                <select
                  value={selectedProject || ""}
                  onChange={e => handleProjectChange(e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">Select Project...</option>
                  {projects.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              )}
              <button
                onClick={() => router.push("/")}
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                title="Back to Dashboard"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {selectedProject ? (
          <CoverageDashboard projectId={selectedProject} simulationId={simulationId ?? undefined} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="w-16 h-16 text-gray-600 mb-4">
              <svg className="w-full h-full" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">No Project Selected</h2>
            <p className="text-gray-400 mb-6 max-w-md">
              Select a project from the dropdown or go to the Dashboard to create a new project.
            </p>
            <button
              onClick={() => router.push("/")}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Go to Dashboard
            </button>
          </div>
        )}
      </main>
    </div>
  );
}