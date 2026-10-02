"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
  PieChart,
  Pie,
} from "recharts";
import {
  BarChart2,
  TrendingUp,
  TrendingDown,
  Target,
  AlertTriangle,
  Search,
  Download,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Eye,
  ArrowLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";

interface CoverageSummary {
  overall: number;
  line: number;
  branch: number;
  toggle: number;
  fsm: number;
  functional: number;
  assertion: number;
}

interface Covergroup {
  name: string;
  module: string;
  coverage: number;
  covered_bins: number;
  total_bins: number;
  coverpoints: Coverpoint[];
}

interface Coverpoint {
  name: string;
  coverage: number;
  bins: number;
}

interface TrendPoint {
  timestamp: string;
  overall: number;
  line: number;
  branch: number;
  functional: number;
}

interface Gap {
  gap_type: string;
  coverage_type: string;
  description: string;
  rtl_location: { module: string; line: number };
  conditions: string[];
  coverage_before: number;
  estimated_impact: number;
  suggested_test: string;
}

import React, { useState, useEffect, useCallback } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
  PieChart,
  Pie,
} from "recharts";
import {
  BarChart2,
  TrendingUp,
  TrendingDown,
  Target,
  AlertTriangle,
  Search,
  Download,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Eye,
  ArrowLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";

const formatCoverage = (val: number) => `${val.toFixed(1)}%`;

const getCoverageColor = (val: number) => {
  if (val >= 95) return "text-green-400 bg-green-900/30";
  if (val >= 85) return "text-yellow-400 bg-yellow-900/30";
  if (val >= 70) return "text-orange-400 bg-orange-900/30";
  return "text-red-400 bg-red-900/30";
};

const getTrendIcon = (before: number, after: number) => {
  if (after > before) return <TrendingUp className="w-4 h-4 text-green-400" />;
  if (after < before) return <TrendingDown className="w-4 h-4 text-red-400" />;
  return null;
};

const build_mock_bins = (coverpointName: string) => {
  const binsMap: Record<string, any[]> = {
    count_cp: [
      { name: "count_0", covered: true, hits: 45, expression: "count == 0" },
      { name: "count_1_to_7", covered: true, hits: 12, expression: "count in [1:7]" },
      { name: "count_8_to_14", covered: false, hits: 0, expression: "count in [8:14]" },
      { name: "count_15", covered: true, hits: 3, expression: "count == 15 (DEPTH)" },
    ],
    wr_ptr_cp: [
      ...Array.from({ length: 16 }, (_, i) => ({
        name: `wr_ptr_${i}`,
        covered: i < 15,
        hits: i < 15 ? 5 : 0,
        expression: `wr_ptr == ${i}`,
      })),
    ],
    simultaneous_rw_cp: [
      { name: "simul_write_read", covered: true, hits: 8, expression: "wr_en && rd_en" },
      { name: "simul_write_read_full", covered: false, hits: 0, expression: "wr_en && rd_en && full" },
      { name: "simul_write_read_empty", covered: false, hits: 0, expression: "wr_en && rd_en && empty" },
    ],
  };
  return binsMap[coverpointName] || [
    { name: "bin_0", covered: true, hits: 10, expression: "default" },
    { name: "bin_1", covered: false, hits: 0, expression: "other" },
  ];
};

export function CoverageDashboard({ projectId, simulationId }: { projectId: string; simulationId?: string }) {
  const [dashboard, setDashboard] = useState<any>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [selectedCovergroup, setSelectedCovergroup] = useState<string | null>(null);
  const [selectedCoverpoint, setSelectedCoverpoint] = useState<string | null>(null);
  const [selectedBin, setSelectedBin] = useState<any | null>(null);
  const [viewMode, setViewMode] = useState<"overview" | "covergroups" | "coverpoints" | "bins" | "trends">("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drilldown, setDrilldown] = useState<"covergroups" | "coverpoints" | "bins" | null>(null);

  const fetchDashboard = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getCoverageDashboard(projectId);
      setDashboard(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch coverage dashboard");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const fetchTrends = useCallback(async () => {
    if (!projectId) return;
    try {
      const res = await api.getCoverageTrends(projectId, 30);
      setTrends(res.data.trends || []);
    } catch (err) {
      console.error("Failed to fetch trends:", err);
    }
  }, [projectId]);

  useEffect(() => {
    fetchDashboard();
    fetchTrends();
  }, [fetchDashboard, fetchTrends]);

  const formatCoverage = (val: number) => `${val.toFixed(1)}%`;

  const getCoverageColor = (val: number) => {
    if (val >= 95) return "text-green-400 bg-green-900/30";
    if (val >= 85) return "text-yellow-400 bg-yellow-900/30";
    if (val >= 70) return "text-orange-400 bg-orange-900/30";
    return "text-red-400 bg-red-900/30";
  };

  const getTrendIcon = (before: number, after: number) => {
    if (after > before) return <TrendingUp className="w-4 h-4 text-green-400" />;
    if (after < before) return <TrendingDown className="w-4 h-4 text-red-400" />;
    return null;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-400">
        <div className="text-center">
          <p className="mb-2">Failed to load coverage dashboard</p>
          <p className="text-sm text-gray-500">{error}</p>
          <button
            onClick={fetchDashboard}
            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="w-16 h-16 text-gray-600 mb-4">📊</div>
        <h2 className="text-xl font-semibold text-white mb-2">No Coverage Data</h2>
        <p className="text-gray-400 mb-6 max-w-md">
          Run a simulation with coverage enabled to see coverage analytics.
        </p>
      </div>
    );
  }

  const summary = dashboard.summary || {};
  const covergroups = dashboard.covergroups || [];
  const gaps = dashboard.gaps || [];

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Target className="w-6 h-6 text-blue-400" />
              <h1 className="text-xl font-bold text-white">Coverage Dashboard</h1>
              <span className="px-2 py-0.5 text-xs bg-blue-900/30 text-blue-300 rounded">
                Coverage Analytics
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <span>Overall:</span>
                <span className={cn("font-mono font-bold", getCoverageColor(summary.overall || 0).replace("text-", "").replace("bg-", ""))}>
                  {formatCoverage(summary.overall || 0)}
                </span>
              </div>
              <button
                onClick={fetchDashboard}
                disabled={loading}
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                title="Refresh"
              >
                <RefreshCw className={cn("w-5 h-5", loading && "animate-spin")} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Summary Cards */}
      <div className="px-4 py-4 border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {[
            { label: "Overall", value: summary.overall, icon: Target },
            { label: "Line", value: summary.line, icon: BarChart2 },
            { label: "Branch", value: summary.branch, icon: GitBranch },
            { label: "Toggle", value: summary.toggle, icon: TrendingUp },
            { label: "FSM", value: summary.fsm, icon: GitBranch },
            { label: "Functional", value: summary.functional, icon: Target },
            { label: "Assertion", value: summary.assertion, icon: AlertTriangle },
          ].map((item) => (
            <div
              key={item.label}
              className={cn(
                "p-3 rounded-lg border transition-colors",
                "bg-gray-800/50 border-gray-700 hover:border-gray-600"
              )}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400">{item.label}</span>
                <item.icon className="w-4 h-4 text-gray-500" />
              </div>
              <div className="flex items-baseline gap-1">
                <span className={cn("text-2xl font-bold font-mono", getCoverageColor(item.value || 0))}>
                  {formatCoverage(item.value || 0)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Gap Summary */}
      {dashboard.gaps && dashboard.gaps.length > 0 && (
        <div className="px-4 py-3 border-b border-gray-800 bg-red-900/10 border-red-900/20">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2 text-red-300">
              <AlertTriangle className="w-5 h-5" />
              <span className="font-medium">{dashboard.total_gaps} Coverage Gaps</span>
              <span className="px-2 py-0.5 text-xs bg-red-900/30 text-red-300 rounded">
                {dashboard.gaps_by_type?.reachable_untested || 0} Reachable
              </span>
              <span className="px-2 py-0.5 text-xs bg-yellow-900/30 text-yellow-300 rounded">
                {dashboard.gaps_by_type?.potentially_unreachable || 0} Unreachable?
              </span>
            </div>
            <button
              onClick={() => setViewMode("overview")}
              className="px-3 py-1.5 text-sm bg-red-900/30 text-red-300 rounded hover:bg-red-900/50"
            >
              View All Gaps
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-auto p-4">
        {/* Overview View */}
        {viewMode === "overview" && (
          <div className="space-y-6">
            {/* Covergroups Grid */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white">Covergroups</h2>
                <button
                  onClick={() => setViewMode("covergroups")}
                  className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded"
                >
                  View All
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {covergroups.slice(0, 6).map((cg: any) => (
                  <div
                    key={cg.name}
                    onClick={() => {
                      setSelectedCovergroup(cg.name);
                      setDrilldown("coverpoints");
                    }}
                    className={cn(
                      "p-4 rounded-lg border cursor-pointer transition-all",
                      "bg-gray-800/50 border-gray-700 hover:border-blue-500 hover:bg-blue-900/10"
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold text-white">{cg.name}</h4>
                      <span className={cn("px-2 py-0.5 text-xs rounded font-mono", getCoverageColor(cg.coverage))}>
                        {formatCoverage(cg.coverage)}
                      </span>
                    </div>
                    <div className="text-sm text-gray-400 mb-2">
                      {cg.module} • {cg.covered_bins}/{cg.total_bins} bins
                    </div>
                    <div className="h-2 bg-gray-700 rounded overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-300"
                        style={{ width: `${cg.coverage}%` }}
                      />
                    </div>
                    <div className="mt-2 flex gap-1 text-xs text-gray-500">
                      {cg.coverpoints?.slice(0, 4).map((cp: any) => (
                        <span
                          key={cp.name}
                          className={cn(
                            "px-1.5 py-0.5 rounded text-xs",
                            cp.coverage >= 95 ? "bg-green-900/30 text-green-300" :
                            cp.coverage >= 85 ? "bg-yellow-900/30 text-yellow-300" :
                            "bg-red-900/30 text-red-300"
                          )}
                        >
                          {cp.name}: {formatCoverage(cp.coverage)}
                        </span>
                      ))}
                      {cg.coverpoints.length > 4 && (
                        <span className="text-gray-500">+{cg.coverpoints.length - 4} more</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Trends Chart */}
            {trends.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-400" />
                  Coverage Trends (30 days)
                </h2>
                <div className="h-64 bg-gray-800/50 rounded-lg border border-gray-700 p-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trends}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis
                        dataKey="timestamp"
                        tickFormatter={(val) => new Date(val).toLocaleDateString()}
                        stroke="#6b7280"
                        fontSize={10}
                      />
                      <YAxis
                        domain={[0, 100]}
                        stroke="#6b7280"
                        fontSize={10}
                        tickFormatter={(val) => `${val}%`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#1e293b",
                          border: "1px solid #374151",
                          borderRadius: "8px"
                        }}
                        labelFormatter={(val) => new Date(val).toLocaleDateString()}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="overall"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={false}
                        name="Overall"
                      />
                      <Line
                        type="monotone"
                        dataKey="line"
                        stroke="#22c55e"
                        strokeWidth={1.5}
                        strokeDasharray="5 5"
                        dot={false}
                        name="Line"
                      />
                      <Line
                        type="monotone"
                        dataKey="branch"
                        stroke="#f59e0b"
                        strokeWidth={1.5}
                        strokeDasharray="5 5"
                        dot={false}
                        name="Branch"
                      />
                      <Line
                        type="monotone"
                        dataKey="functional"
                        stroke="#ef4444"
                        strokeWidth={1.5}
                        strokeDasharray="5 5"
                        dot={false}
                        name="Functional"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Top Gaps */}
            {dashboard.gaps && dashboard.gaps.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  Top Coverage Gaps
                </h2>
                <div className="space-y-2 max-h-64 overflow-auto">
                  {dashboard.gaps.slice(0, 10).map((gap: any, i: number) => (
                    <div
                      key={i}
                      className="p-3 bg-gray-800/50 border border-gray-700 rounded-lg hover:border-red-500 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={cn(
                              "px-1.5 py-0.5 rounded text-xs font-mono",
                              gap.gap_type === "reachable_untested" && "bg-red-900/30 text-red-300",
                              gap.gap_type === "potentially_unreachable" && "bg-yellow-900/30 text-yellow-300",
                              "bg-gray-700 text-gray-300"
                            )}>
                              {gap.gap_type.replace("_", " ")}
                            </span>
                            <span className="text-sm text-gray-400 font-mono">
                              {gap.rtl_location?.module}:{gap.rtl_location?.line}
                            </span>
                          </div>
                          <p className="text-sm text-gray-300 truncate">{gap.description}</p>
                          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                            <span>Impact: ~{gap.estimated_impact?.toFixed(1)}%</span>
                            <span className="text-gray-500">Coverage: {formatCoverage(gap.coverage_before)}</span>
                          </div>
                        </div>
                        <button
                          className="px-2 py-1 text-xs bg-blue-900/30 text-blue-300 rounded hover:bg-blue-900/50 whitespace-nowrap"
                          title="Generate targeted test"
                        >
                          Generate Test
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Covergroups View */}
        {viewMode === "covergroups" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">All Covergroups</h2>
              <button
                onClick={() => setViewMode("overview")}
                className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 text-white rounded"
              >
                Back to Overview
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-gray-400 text-left">
                    <th className="p-3 font-medium">Covergroup</th>
                    <th className="p-3 font-medium">Module</th>
                    <th className="p-3 font-medium text-right">Coverage</th>
                    <th className="p-3 font-medium text-right">Bins</th>
                    <th className="p-3 font-medium">Coverpoints</th>
                    <th className="p-3 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {covergroups.map((cg: any) => (
                    <tr
                      key={cg.name}
                      className="border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer"
                      onClick={() => { setSelectedCovergroup(cg.name); setDrilldown("coverpoints"); }}
                    >
                      <td className="p-3 font-mono text-white">{cg.name}</td>
                      <td className="p-3 text-gray-300">{cg.module}</td>
                      <td className="p-3 text-right">
                        <span className={cn("font-mono font-medium", getCoverageColor(cg.coverage))}>
                          {formatCoverage(cg.coverage)}
                        </span>
                      </td>
                      <td className="p-3 text-right text-gray-400 font-mono">
                        {cg.covered_bins}/{cg.total_bins}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-1 flex-wrap">
                          {cg.coverpoints?.map((cp: any) => (
                            <span
                              key={cp.name}
                              className={cn(
                                "px-1.5 py-0.5 rounded text-xs",
                                cp.coverage >= 95 ? "bg-green-900/30 text-green-300" :
                                cp.coverage >= 85 ? "bg-yellow-900/30 text-yellow-300" :
                                "bg-red-900/30 text-red-300"
                              )}
                            >
                              {cp.name}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="p-3 text-center">
                        <button
                          onClick={(e) => { e.stopPropagation(); setSelectedCovergroup(cg.name); setDrilldown("coverpoints"); }}
                          className="px-2 py-1 text-xs bg-blue-900/30 text-blue-300 rounded hover:bg-blue-900/50"
                        >
                          Drill Down
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Coverpoints Drill-down */}
        {selectedCovergroup && drilldown === "coverpoints" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <button onClick={() => { setSelectedCovergroup(null); setDrilldown(null); }} className="p-2 hover:bg-gray-800 rounded">
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <h2 className="text-lg font-semibold text-white">{selectedCovergroup}</h2>
                <span className="px-2 py-0.5 text-xs bg-blue-900/30 text-blue-300 rounded">Coverpoints</span>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-gray-400 text-left">
                    <th className="p-3 font-medium">Coverpoint</th>
                    <th className="p-3 font-medium text-right">Coverage</th>
                    <th className="p-3 font-medium text-right">Bins</th>
                    <th className="p-3 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {covergroups.find((cg: any) => cg.name === selectedCovergroup)?.coverpoints?.map((cp: any) => (
                    <tr
                      key={cp.name}
                      className="border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer"
                      onClick={() => { setSelectedCoverpoint(cp.name); setDrilldown("bins"); }}
                    >
                      <td className="p-3 font-mono text-white">{cp.name}</td>
                      <td className="p-3 text-right">
                        <span className={cn("font-mono font-medium", getCoverageColor(cp.coverage))}>
                          {formatCoverage(cp.coverage)}
                        </span>
                      </td>
                      <td className="p-3 text-right text-gray-400 font-mono">{cp.bins} bins</td>
                      <td className="p-3 text-center">
                        <button className="px-2 py-1 text-xs bg-blue-900/30 text-blue-300 rounded hover:bg-blue-900/50">
                          View Bins
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Bins Drill-down */}
        {selectedCoverpoint && drilldown === "bins" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <button onClick={() => { setSelectedCoverpoint(null); setDrilldown("coverpoints"); }} className="p-2 hover:bg-gray-800 rounded">
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <h2 className="text-lg font-semibold text-white">{selectedCoverpoint}</h2>
                <span className="px-2 py-0.5 text-xs bg-green-900/30 text-green-300 rounded">Bins</span>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-gray-400 text-left">
                    <th className="p-3 font-medium">Bin</th>
                    <th className="p-3 font-medium">Expression</th>
                    <th className="p-3 font-medium text-right">Hits</th>
                    <th className="p-3 font-medium text-right">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {build_mock_bins(selectedCoverpoint).map((bin: any) => (
                    <tr key={bin.name} className="border-b border-gray-800 hover:bg-gray-800/50">
                      <td className="p-3 font-mono text-white">{bin.name}</td>
                      <td className="p-3 text-gray-300 font-mono text-sm">{bin.expression}</td>
                      <td className="p-3 text-right font-mono text-gray-300">{bin.hits}</td>
                      <td className="p-3 text-right">
                        <span className={cn(
                          "px-2 py-0.5 rounded text-xs font-medium",
                          bin.covered ? "bg-green-900/30 text-green-300" : "bg-red-900/30 text-red-300"
                        )}>
                          {bin.covered ? "COVERED" : "NOT COVERED"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Gaps View */}
        {viewMode === "overview" && dashboard.gaps && dashboard.gaps.length > 0 && (
          <div className="mt-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              All Gaps ({dashboard.total_gaps})
            </h2>
            <div className="space-y-2 max-h-96 overflow-auto">
              {dashboard.gaps.map((gap: any, i: number) => (
                <div
                  key={i}
                  className="p-4 bg-gray-800/50 border border-gray-700 rounded-lg hover:border-red-500 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn(
                          "px-1.5 py-0.5 rounded text-xs font-mono",
                          gap.gap_type === "reachable_untested" && "bg-red-900/30 text-red-300",
                          gap.gap_type === "potentially_unreachable" && "bg-yellow-900/30 text-yellow-300",
                          "bg-gray-700 text-gray-300"
                        )}>
                          {gap.gap_type.replace("_", " ")}
                        </span>
                        <span className="text-sm text-gray-400 font-mono">
                          {gap.rtl_location?.module}:{gap.rtl_location?.line}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300 mb-2">{gap.description}</p>
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span>Impact: ~{gap.estimated_impact?.toFixed(1)}%</span>
                        <span>Coverage: {formatCoverage(gap.coverage_before)}</span>
                        <span className="font-mono">{gap.coverage_type}</span>
                      </div>
                    </div>
                    <button className="px-3 py-1.5 text-sm bg-blue-900/30 text-blue-300 rounded hover:bg-blue-900/50 whitespace-nowrap">
                      Generate Test
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default CoverageDashboard;