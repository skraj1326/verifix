"use client";

import React, { Suspense, useState, useEffect } from "react";
import {
  FileText,
  ChevronLeft,
  Download,
  Printer,
  Share2,
  Settings,
  Loader2,
  CheckCircle,
  XCircle,
  AlertCircle,
  FileCheck,
  ScrollText,
  Table,
  BarChart2,
  List,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";

interface ReportSection {
  id: string;
  title: string;
  content: string;
  order: number;
  type: string;
}

interface Report {
  id: string;
  project_id: string;
  title: string;
  generated_at: string;
  format: string;
  sections: ReportSection[];
  metadata: Record<string, any>;
}

// useSearchParams() opts a route out of static prerendering unless it is read
// inside a Suspense boundary, so the page wraps its content below.
export default function ReportsPage() {
  return (
    <Suspense fallback={<PageFallback label="Loading reports" />}>
      <ReportsContent />
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

function ReportsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = searchParams.get("projectId");
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<string | null>(projectId || null);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [format, setFormat] = useState<"html" | "pdf" | "json">("html");
  const [template, setTemplate] = useState<"standard" | "executive" | "detailed">("standard");
  const [includeSections, setIncludeSections] = useState<string[]>([
    "executive_summary",
    "design_overview",
    "verification_plan",
    "assertions",
    "tests",
    "coverage",
    "failures",
    "traceability",
    "conclusions",
    "appendices",
  ]);
  const [error, setError] = useState<string | null>(null);

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
    setReport(null);
  };

  const handleSectionToggle = (section: string) => {
    setIncludeSections(prev =>
      prev.includes(section)
        ? prev.filter(s => s !== section)
        : [...prev, section]
    );
  };

  const generateReport = async () => {
    if (!selectedProject) {
      toast.error("Select a project first");
      return;
    }

    setGenerating(true);
    setError(null);
    try {
      const res = await api.generateReport(selectedProject, {
        format,
        include_sections: includeSections,
        template,
      });
      setReport(res.data);
      toast.success("Report generated successfully");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to generate report");
      toast.error("Failed to generate report");
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async (exportFormat: "html" | "pdf" | "json") => {
    if (!report) return;
    if (exportFormat === "pdf") {
      toast.error("PDF export is not implemented yet. Use HTML or JSON.");
      return;
    }
    try {
      const res = await api.exportReport(report.project_id, {
        format: exportFormat,
        simulation_id: report.metadata?.simulation_id ?? undefined,
        include_sections: includeSections.length ? includeSections : undefined,
        template,
      });

      const blob = new Blob([res.data], {
        type: exportFormat === "json" ? "application/json" : "text/html",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${report.id}.${exportFormat}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      toast.success(`Report downloaded as ${exportFormat.toUpperCase()}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Export failed");
    }
  };

  const allSections = [
    { id: "executive_summary", label: "Executive Summary", desc: "High-level verification summary" },
    { id: "design_overview", label: "Design Overview", desc: "Module hierarchy and structure" },
    { id: "verification_plan", label: "Verification Plan", desc: "Auto-generated verification plan" },
    { id: "assertions", label: "Assertions", desc: "All assertions and their status" },
    { id: "tests", label: "Tests", desc: "Generated tests and results" },
    { id: "coverage", label: "Coverage Analysis", desc: "Coverage metrics and gaps" },
    { id: "failures", label: "Failures & Issues", desc: "Recorded failures and investigations" },
    { id: "traceability", label: "Traceability Matrix", desc: "Requirement to test mapping" },
    { id: "conclusions", label: "Conclusions", desc: "Findings and recommendations" },
    { id: "appendices", label: "Appendices", desc: "Raw data and supplementary info" },
  ];

  if (!selectedProject) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="w-16 h-16 text-gray-600 mb-4">
          <svg className="w-full h-full" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2h6m0 0a2 2 0 012 2h2a2 2 0 002-2V7h2a2 2 0 012 2v12a2 2 0 002 2h2a2 2 0 002-2v-2m-4-4h.586a1 1 0 01.707.293l3.414 3.414a1 1 0 00.707.293H18a2 2 0 002-2V7a2 2 0 00-2-2H8a2 2 0 01-2-2V5a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2h2a2 2 0 002-2V7z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">No Project Selected</h2>
        <p className="text-gray-400 mb-6 max-w-md">
          Select a project from the dropdown to generate a verification report.
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
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2h2a2 2 0 002-2V7z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Verification Reports</h1>
                <p className="text-sm text-gray-400">Generate professional verification reports</p>
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
                <ChevronLeft className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-auto p-6">
        <div className="max-w-7xl mx-auto">
          {/* Configuration Panel */}
          <div className="mb-6 bg-gray-900/50 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-purple-400" />
              Report Configuration
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Format</label>
                <select
                  value={format}
                  onChange={e => setFormat(e.target.value as "html" | "pdf" | "json")}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="html">HTML</option>
                  <option value="pdf">PDF</option>
                  <option value="json">JSON</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Template</label>
                <select
                  value={template}
                  onChange={e => setTemplate(e.target.value as "standard" | "executive" | "detailed")}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="standard">Standard</option>
                  <option value="executive">Executive Summary</option>
                  <option value="detailed">Detailed Technical</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Include Sections</label>
                <div className="relative">
                  <button
                    onClick={() => setIncludeSections(allSections.map(s => s.id))}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-white hover:bg-gray-700"
                  >
                    Select All ({includeSections.length}/{allSections.length})
                  </button>
                </div>
              </div>
            </div>

            {/* Section Selection */}
            <div className="bg-gray-800/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-300">Select Sections ({includeSections.length}/{allSections.length})</h4>
                <div className="flex gap-2">
                  <button
                    onClick={() => setIncludeSections(allSections.map(s => s.id))}
                    className="px-3 py-1 text-xs bg-green-900/30 text-green-300 rounded hover:bg-green-900/50"
                  >
                    Select All
                  </button>
                  <button
                    onClick={() => setIncludeSections([])}
                    className="px-3 py-1 text-xs bg-red-900/30 text-red-300 rounded hover:bg-red-900/50"
                  >
                    Clear All
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                {allSections.map(section => (
                  <label
                    key={section.id}
                    className={cn(
                      "flex items-center gap-3 p-3 rounded-lg border transition-colors cursor-pointer",
                      includeSections.includes(section.id)
                        ? "bg-purple-900/20 border-purple-700/50"
                        : "bg-gray-800/50 border-gray-700 hover:border-gray-600"
                    )}
                    onClick={() => handleSectionToggle(section.id)}
                  >
                    <input
                      type="checkbox"
                      checked={includeSections.includes(section.id)}
                      readOnly
                      className="w-4 h-4 text-purple-600 border-gray-600 rounded focus:ring-purple-500 pointer-events-none"
                    />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-white truncate block">{section.label}</span>
                      <span className="text-xs text-gray-500 truncate block">{section.desc}</span>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setIncludeSections(allSections.map(s => s.id))}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg"
              >
                Select All
              </button>
              <button
                onClick={generateReport}
                disabled={generating}
                className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium flex items-center gap-2"
              >
                <Loader2 className={cn("w-4 h-4", generating && "animate-spin")} />
                {generating ? "Generating..." : "Generate Report"}
              </button>
            </div>
          </div>

          {/* Report Preview */}
          {report && (
            <div className="mt-6 bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
              <div className="bg-gray-800/50 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-white">{report.title}</h2>
                  <p className="text-sm text-gray-400">
                    Generated: {new Date(report.generated_at).toLocaleString()} • {report.sections.length} sections
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleExport("html")}
                    className="px-4 py-2 bg-blue-900/30 text-blue-300 rounded-lg hover:bg-blue-900/50 flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    HTML
                  </button>
                  <button
                    onClick={() => handleExport("pdf")}
                    className="px-4 py-2 bg-red-900/30 text-red-300 rounded-lg hover:bg-red-900/50 flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4" />
                    PDF
                  </button>
                  <button
                    onClick={() => handleExport("json")}
                    className="px-4 py-2 bg-green-900/30 text-green-300 rounded-lg hover:bg-green-900/50 flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4" />
                    JSON
                  </button>
                  <button
                    onClick={() => handleExport("html")}
                    className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg flex items-center gap-2"
                  >
                    <Eye className="w-4 h-4" />
                    View
                  </button>
                </div>
              </div>

              <div className="p-6 max-h-[60vh] overflow-auto">
                <div className="prose prose-invert max-w-none">
                  {report.sections.map((section: any) => (
                    <section key={section.id} className="mb-8">
                      <h2 className="text-2xl font-bold text-white mb-4 pb-2 border-b border-gray-700">
                        {section.title}
                      </h2>
                      <div className="prose prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: section.content }} />
                    </section>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}