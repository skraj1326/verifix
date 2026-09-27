'use client';

import { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  Code, 
  Copy, 
  Search,
  Filter,
  AlertCircle,
  CheckCircle,
  XCircle,
  Info,
  Bug,
  Zap,
  FileText,
} from 'lucide-react';
import { cn, getConfidenceColor, truncate } from '@/lib/utils';
import { failureApi } from '@/lib/api';

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

const defaultLog = `[INFO] Starting simulation...
[INFO] Test fifo_basic started
[ERROR] Assertion failed in fifo_sync.a_no_write_when_full at fifo.sv:45
[ERROR] Assertion failed in fifo_sync.a_no_read_when_empty at fifo.sv:52
[INFO] Test fifo_basic completed`;

export default function FailuresPage() {
  const [rtlContent, setRtlContent] = useState(defaultRtl);
  const [logContent, setLogContent] = useState(defaultLog);
  const [failureInfo, setFailureInfo] = useState({
    error: 'Assertion failed in fifo_sync.a_no_write_when_full',
    location: 'fifo.sv:45',
    severity: 'ERROR',
    observed_fact: 'Assertion a_no_write_when_full failed when wr_en=1 and full=1',
  });
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'analysis' | 'log' | 'facts'>('analysis');

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const res = await failureApi.analyze({
        failure_info: failureInfo,
        rtl_content: rtlContent,
        log_analysis: { log_content: logContent },
      });
      setResult(res);
      setActiveTab('analysis');
    } catch (error) {
      console.error('Failure analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'FATAL': return 'bg-red-500/20 text-red-400';
      case 'ERROR': return 'bg-red-500/20 text-red-400';
      case 'WARNING': return 'bg-yellow-500/20 text-yellow-400';
      case 'INFO': return 'bg-blue-500/20 text-blue-400';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">Failure Analysis</h1>
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {loading ? 'Analyzing...' : 'Analyze Failure'}
            </button>
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
                  <span className="font-medium">RTL Context</span>
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
                  <AlertTriangle className="w-5 h-5" />
                  <span className="font-medium">Failure Info</span>
                </div>
              </div>
              <div className="p-4 space-y-3">
                <input
                  type="text"
                  value={failureInfo.error}
                  onChange={(e) => setFailureInfo({...failureInfo, error: e.target.value})}
                  placeholder="Error message"
                  className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
                />
                <input
                  type="text"
                  value={failureInfo.location}
                  onChange={(e) => setFailureInfo({...failureInfo, location: e.target.value})}
                  placeholder="Location (file:line)"
                  className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
                />
                <select
                  value={failureInfo.severity}
                  onChange={(e) => setFailureInfo({...failureInfo, severity: e.target.value})}
                  className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
                >
                  <option value="FATAL">FATAL</option>
                  <option value="ERROR">ERROR</option>
                  <option value="WARNING">WARNING</option>
                  <option value="INFO">INFO</option>
                </select>
                <textarea
                  value={failureInfo.observed_fact}
                  onChange={(e) => setFailureInfo({...failureInfo, observed_fact: e.target.value})}
                  placeholder="Observed fact"
                  className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm h-24"
                />
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="border-b border-border px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  <span className="font-medium">Simulation Log</span>
                </div>
              </div>
              <textarea
                value={logContent}
                onChange={(e) => setLogContent(e.target.value)}
                className="w-full h-48 p-4 font-mono text-sm resize-none bg-transparent outline-none"
                spellCheck={false}
              />
            </div>
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="border-b border-border px-4 py-3 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  <span className="font-medium">Failure Analysis</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setActiveTab('analysis')}
                    className={cn('px-3 py-1 text-sm rounded', activeTab === 'analysis' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
                  >
                    Analysis
                  </button>
                  <button
                    onClick={() => setActiveTab('log')}
                    className={cn('px-3 py-1 text-sm rounded', activeTab === 'log' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
                  >
                    Log Analysis
                  </button>
                  <button
                    onClick={() => setActiveTab('facts')}
                    className={cn('px-3 py-1 text-sm rounded', activeTab === 'facts' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
                  >
                    Facts vs Hypotheses
                  </button>
                </div>
              </div>

              {activeTab === 'analysis' && (
                <div className="p-4">
                  {result ? (
                    <>
                      <div className="mb-4 p-4 bg-secondary/50 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-mono text-sm">{result.failure_id || 'FAIL-XXXX'}</span>
                          <span className={cn('px-2 py-0.5 text-xs rounded', getSeverityColor(result.severity || 'ERROR'))}>
                            {result.severity || 'ERROR'}
                          </span>
                          <span className="px-2 py-0.5 text-xs bg-muted text-muted-foreground rounded">
                            {result.classification || 'HYPOTHESIS'}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">{result.error}</p>
                        <p className="text-xs text-muted-foreground mt-1">Location: {result.location}</p>
                      </div>

                      {result.root_cause_hypothesis && (
                        <div className="mb-4">
                          <h4 className="font-medium mb-2 flex items-center gap-2">
                            <Zap className="w-4 h-4 text-yellow-500" />
                            Root Cause Hypothesis
                          </h4>
                          <p className="text-sm">{result.root_cause_hypothesis}</p>
                          <div className="mt-2 flex items-center gap-2">
                            <span className="px-2 py-0.5 text-xs bg-yellow-500/20 text-yellow-400 rounded">
                              Confidence: {result.confidence || 'LOW'}
                            </span>
                          </div>
                        </div>
                      )}

                      {result.evidence && result.evidence.length > 0 && (
                        <div className="mb-4">
                          <h4 className="font-medium mb-2 flex items-center gap-2">
                            <Info className="w-4 h-4" />
                            Evidence
                          </h4>
                          <ul className="space-y-1">
                            {result.evidence.map((e: string, i: number) => (
                              <li key={i} className="text-sm text-muted-foreground flex items-center gap-2">
                                <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                                {e}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {result.recommended_action && (
                        <div className="mb-4 p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
                          <h4 className="font-medium mb-2 flex items-center gap-2">
                            <CheckCircle className="w-4 h-4 text-green-500" />
                            Recommended Action
                          </h4>
                          <p className="text-sm">{result.recommended_action}</p>
                        </div>
                      )}

                      {result.ai_analysis && (
                        <div className="border-t border-border pt-4">
                          <h4 className="font-medium mb-2 flex items-center gap-2">
                            <Bug className="w-4 h-4 text-purple-500" />
                            AI Analysis
                          </h4>
                          <pre className="bg-secondary/50 p-4 rounded-lg overflow-x-auto max-h-60 text-sm">
                            <code>{JSON.stringify(result.ai_analysis, null, 2)}</code>
                          </pre>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>Provide failure info and click Analyze Failure</p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'log' && (
                <div className="p-4">
                  <LogAnalysisView logContent={logContent} />
                </div>
              )}

              {activeTab === 'facts' && (
                <div className="p-4">
                  <FactsVsHypothesesView 
                    result={result} 
                    failureInfo={failureInfo}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function LogAnalysisView({ logContent }: { logContent: string }) {
  const lines = logContent.split('\n');
  const errors = lines.filter(l => l.includes('[ERROR]') || l.includes('[FATAL]'));
  const warnings = lines.filter(l => l.includes('[WARNING]'));
  const assertions = lines.filter(l => l.includes('assertion') && l.toLowerCase().includes('fail'));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Total Lines" value={lines.length} icon={FileText} />
        <StatCard label="Errors" value={errors.length} icon={AlertCircle} />
        <StatCard label="Warnings" value={warnings.length} icon={AlertTriangle} />
      </div>

      {assertions.length > 0 && (
        <div className="border border-red-500/30 bg-red-500/10 rounded-lg p-4">
          <h4 className="font-medium mb-2 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500" />
            Assertion Failures ({assertions.length})
          </h4>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {assertions.map((line, i) => (
              <div key={i} className="font-mono text-xs text-red-400 bg-secondary/50 p-2 rounded truncate">
                {line.trim()}
              </div>
            ))}
          </div>
        </div>
      )}

      {errors.length > 0 && (
        <div className="border border-red-500/30 bg-red-500/10 rounded-lg p-4">
          <h4 className="font-medium mb-2">Errors</h4>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {errors.map((line, i) => (
              <div key={i} className="font-mono text-xs text-red-400 bg-secondary/50 p-2 rounded truncate">
                {line.trim()}
              </div>
            ))}
          </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="border border-yellow-500/30 bg-yellow-500/10 rounded-lg p-4">
          <h4 className="font-medium mb-2">Warnings</h4>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {warnings.map((line, i) => (
              <div key={i} className="font-mono text-xs text-yellow-400 bg-secondary/50 p-2 rounded truncate">
                {line.trim()}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function FactsVsHypothesesView({ result, failureInfo }: any) {
  if (!result) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Info className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>Run analysis to see facts vs hypotheses separation</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="border-l-4 border-blue-500 bg-blue-500/10 p-4">
        <h4 className="font-medium mb-3 flex items-center gap-2">
          <Info className="w-4 h-4 text-blue-500" />
          Observed FACTS
        </h4>
        <ul className="space-y-2">
          <li className="text-sm flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
            {failureInfo.observed_fact}
          </li>
          <li className="text-sm flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
            Assertion a_no_write_when_full failed at fifo.sv:45
          </li>
          <li className="text-sm flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
            Simulation exit code: non-zero
          </li>
          {result.facts && result.facts.map((f: any, i: number) => (
            <li key={i} className="text-sm flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
              {f.fact} <span className="text-xs text-muted-foreground">({f.source})</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="border-l-4 border-yellow-500 bg-yellow-500/10 p-4">
        <h4 className="font-medium mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4 text-yellow-500" />
          HYPOTHESES (AI Inference)
        </h4>
        <ul className="space-y-2">
          {result.hypotheses && result.hypotheses.map((h: any, i: number) => (
            <li key={i} className="text-sm">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p>{h.hypothesis}</p>
                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    <span className={cn('px-1 py-0.5 rounded', getConfidenceColor(h.confidence))}>
                      {h.confidence}
                    </span>
                    {h.evidence && h.evidence.length > 0 && (
                      <span>Evidence: {h.evidence.join(', ')}</span>
                    )}
                  </div>
                </div>
              </div>
            </li>
          ))}
          {!result.hypotheses && result.root_cause_hypothesis && (
            <li className="text-sm flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
              <div>
                <p>{result.root_cause_hypothesis}</p>
                <div className="text-xs text-muted-foreground mt-1">
                  Confidence: {result.confidence}
                </div>
              </div>
            </li>
          )}
        </ul>
      </div>

      {result.separation_of_concerns && (
        <div className="bg-secondary/50 rounded-lg p-4">
          <h4 className="font-medium mb-2">Separation Summary</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-blue-400">Facts:</span>
              <ul className="space-y-1 mt-1">
                {result.separation_of_concerns.facts?.map((f: string, i: number) => (
                  <li key={i} className="flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-green-500" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <span className="font-medium text-yellow-400">Hypotheses:</span>
              <ul className="space-y-1 mt-1">
                {result.separation_of_concerns.hypotheses?.map((h: string, i: number) => (
                  <li key={i} className="flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3 text-yellow-500" />
                    {h}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
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