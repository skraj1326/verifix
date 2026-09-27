'use client';

import { useState, useEffect } from 'react';
import { 
  BarChart, 
  AlertTriangle, 
  Download,
  Filter,
  Search,
  Code,
  Zap,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import { cn, truncate } from '@/lib/utils';
import { coverageApi } from '@/lib/api';

const defaultRtl = `module fifo_sync #(
    parameter int DEPTH = 16,
    parameter int DATA_WIDTH = 32
) (
    input  logic                  clk,
    input  logic                  reset,
    input  logic                  wr_en,
    input  logic                  rd_en,
    input  logic [DATA_WIDTH-1:0] din,
    output logic [DATA_WIDTH-1:0] dout,
    output logic                  full,
    output logic                  empty,
    output logic [$clog2(DEPTH):0] count
);

    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    logic [$clog2(DEPTH):0] wr_ptr, rd_ptr;

    always_ff @(posedge clk) begin
        if (reset) begin
            wr_ptr <= 0;
            rd_ptr <= 0;
        end else begin
            if (wr_en && !full) wr_ptr <= wr_ptr + 1;
            if (rd_en && !empty) rd_ptr <= rd_ptr + 1;
        end
    end

endmodule`;

const defaultCoverage = `Lines     150/200 (75.00%)
Branches  80/100 (80.00%)
Toggles   200/300 (66.67%)`;

export default function CoveragePage() {
  const [rtlContent, setRtlContent] = useState(defaultRtl);
  const [coverageReport, setCoverageReport] = useState(defaultCoverage);
  const [moduleName, setModuleName] = useState('fifo_sync');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'report' | 'gaps' | 'compare'>('report');
  const [compareBefore, setCompareBefore] = useState('');
  const [compareAfter, setCompareAfter] = useState('');

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const res = await coverageApi.analyze({
        coverage_report: coverageReport,
        rtl_content: rtlContent,
        module_name: moduleName,
      });
      setResult(res);
      setActiveTab('report');
    } catch (error) {
      console.error('Coverage analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateTests = async () => {
    setLoading(true);
    try {
      const res = await coverageApi.generateTargetedTests({
        coverage_report: coverageReport,
        rtl_content: rtlContent,
        module_name: moduleName,
      });
      console.log('Targeted tests generated:', res);
    } catch (error) {
      console.error('Test generation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    setLoading(true);
    try {
      const res = await coverageApi.compare({
        coverage_before: JSON.parse(compareBefore || '{}'),
        coverage_after: JSON.parse(compareAfter || '{}'),
      });
      setResult({ comparison: res });
      setActiveTab('compare');
    } catch (error) {
      console.error('Comparison failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const getGapColor = (type: string) => {
    switch (type) {
      case 'reachable_untested': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'potentially_unreachable': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'unreachable': return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">Coverage Analysis</h1>
            <div className="flex items-center gap-2">
              <button
                onClick={handleGenerateTests}
                disabled={loading || !result?.gaps?.length}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                Generate Targeted Tests
              </button>
              <button
                onClick={handleAnalyze}
                disabled={loading}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {loading ? 'Analyzing...' : 'Analyze Coverage'}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="border-b border-border px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code className="w-5 h-5" />
                  <span className="font-medium">RTL Source</span>
                </div>
              </div>
              <textarea
                value={rtlContent}
                onChange={(e) => setRtlContent(e.target.value)}
                className="w-full h-64 p-4 font-mono text-sm resize-none bg-transparent outline-none"
                spellCheck={false}
              />
            </div>

            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="border-b border-border px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  <span className="font-medium">Coverage Report</span>
                </div>
              </div>
              <textarea
                value={coverageReport}
                onChange={(e) => setCoverageReport(e.target.value)}
                className="w-full h-48 p-4 font-mono text-sm resize-none bg-transparent outline-none"
                spellCheck={false}
                placeholder="Paste Verilator coverage output..."
              />
            </div>

            <div className="bg-card border border-border rounded-xl p-4 space-y-3">
              <input
                type="text"
                value={moduleName}
                onChange={(e) => setModuleName(e.target.value)}
                placeholder="Module name"
                className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
              />
            </div>
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="border-b border-border px-4 py-3 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <BarChart className="w-5 h-5" />
                  <span className="font-medium">Coverage Report</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveTab('report')}
                    className={cn('px-3 py-1 text-sm rounded', activeTab === 'report' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
                  >
                    Report
                  </button>
                  <button
                    onClick={() => setActiveTab('gaps')}
                    className={cn('px-3 py-1 text-sm rounded', activeTab === 'gaps' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
                  >
                    Gaps ({result?.gaps?.length || 0})
                  </button>
                  <button
                    onClick={() => setActiveTab('compare')}
                    className={cn('px-3 py-1 text-sm rounded', activeTab === 'compare' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
                  >
                    Compare
                  </button>
                </div>
              </div>

              {activeTab === 'report' && (
                <div className="p-4">
                  {result?.report ? (
                    <>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <StatCard
                          label="Overall"
                          value={`${result.report.overall_coverage.toFixed(1)}%`}
                          icon={TrendingUp}
                        />
                        <StatCard
                          label="Line"
                          value={`${result.coverage?.line?.overall?.toFixed(1) || 0}%`}
                        />
                        <StatCard
                          label="Branch"
                          value={`${result.coverage?.branch?.overall?.toFixed(1) || 0}%`}
                        />
                        <StatCard
                          label="Toggle"
                          value={`${result.coverage?.toggle?.overall?.toFixed(1) || 0}%`}
                        />
                      </div>

                      <div className="space-y-4">
                        {Object.entries(result.coverage || {}).map(([type, data]: [string, any]) => (
                          <div key={type} className="bg-secondary/50 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium capitalize">{type} Coverage</span>
                              <span className="text-lg font-bold">{data.overall?.toFixed(1)}%</span>
                            </div>
                            <div className="h-4 bg-secondary rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary rounded-full transition-all"
                                style={{ width: `${data.overall || 0}%` }}
                              />
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">
                              {data.covered}/{data.total} covered
                            </div>
                          </div>
                        ))}
                      </div>

                      {result.report?.closure_estimate && (
                        <div className="mt-6 p-4 bg-primary/10 rounded-lg border border-primary/20">
                          <h4 className="font-medium mb-2">Closure Estimate</h4>
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-muted-foreground">Achievable Coverage</span>
                              <div className="font-bold">{result.report.closure_estimate.achievable_coverage.toFixed(1)}%</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Tests Needed</span>
                              <div className="font-bold">{result.report.closure_estimate.tests_needed}</div>
                            </div>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <BarChart className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>Analyze coverage to see report</p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'gaps' && (
                <div className="p-4">
                  {result?.gaps && result.gaps.length > 0 ? (
                    <>
                      <div className="grid grid-cols-3 gap-4 mb-6">
                        <StatCard
                          label="Reachable"
                          value={result.report?.gap_summary?.reachable_untested || 0}
                          icon={AlertCircle}
                        />
                        <StatCard
                          label="Potentially Unreachable"
                          value={result.report?.gap_summary?.potentially_unreachable || 0}
                          icon={AlertTriangle}
                        />
                        <StatCard
                          label="Unreachable"
                          value={result.report?.gap_summary?.unreachable || 0}
                          icon={XCircle}
                        />
                      </div>
                      <div className="space-y-3 max-h-[500px] overflow-y-auto">
                        {result.gaps.map((gap: any, idx: number) => (
                          <div
                            key={idx}
                            className={cn(
                              'border rounded-lg p-4',
                              getGapColor(gap.gap_type)
                            )}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-mono text-sm">{gap.coverage_type}</span>
                                  <span className="px-2 py-0.5 text-xs rounded">
                                    {gap.gap_type.replace('_', ' ')}
                                  </span>
                                </div>
                                <p className="text-sm text-muted-foreground">{gap.description}</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                  {gap.rtl_location?.module}:{gap.rtl_location?.line}
                                </p>
                              </div>
                              <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                                Priority: {gap.priority}
                              </span>
                            </div>
                            {gap.suggested_test && (
                              <div className="mt-2 p-2 bg-secondary/50 rounded text-sm">
                                <span className="font-medium">Suggested Test:</span> {gap.suggested_test}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No gaps found or analyze coverage first</p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'compare' && (
                <div className="p-4 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-muted-foreground block mb-1">Before (JSON)</label>
                      <textarea
                        value={compareBefore}
                        onChange={(e) => setCompareBefore(e.target.value)}
                        className="w-full h-48 p-4 font-mono text-sm resize-none bg-secondary border border-border rounded-lg"
                        placeholder='{"line": {"overall": 70, "covered": 70, "total": 100}, "branch": {"overall": 60, "covered": 60, "total": 100}}'
                      />
                    </div>
                    <div>
                      <label className="text-sm text-muted-foreground block mb-1">After (JSON)</label>
                      <textarea
                        value={compareAfter}
                        onChange={(e) => setCompareAfter(e.target.value)}
                        className="w-full h-48 p-4 font-mono text-sm resize-none bg-secondary border border-border rounded-lg"
                        placeholder='{"line": {"overall": 80, "covered": 80, "total": 100}, "branch": {"overall": 65, "covered": 65, "total": 100}}'
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleCompare}
                    disabled={loading}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
                  >
                    Compare Coverage
                  </button>
                  {result?.comparison && (
                    <div className="space-y-2">
                      {Object.entries(result.comparison).map(([type, data]: [string, any]) => (
                        <div key={type} className="bg-secondary/50 rounded-lg p-4">
                          <div className="flex items-center justify-between">
                            <span className="font-medium capitalize">{type}</span>
                            <span className={cn('font-bold', data.improved ? 'text-green-400' : 'text-red-400')}>
                              {data.delta > 0 ? '+' : ''}{data.delta.toFixed(1)}%
                            </span>
                          </div>
                          <div className="text-sm text-muted-foreground mt-1">
                            {data.before.toFixed(1)}% → {data.after.toFixed(1)}%
                            ({data.before_covered}/{data.total} → {data.after_covered}/{data.total})
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value, icon: Icon }: { label: string; value: any; icon?: any }) {
  return (
    <div className="bg-secondary/50 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-1">
        {Icon && <Icon className="w-4 h-4 text-muted-foreground" />}
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <div className="text-xl font-bold tabular-nums">{value}</div>
    </div>
  );
}