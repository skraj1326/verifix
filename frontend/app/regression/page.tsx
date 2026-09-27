'use client';

import { useState, useEffect } from 'react';
import { 
  RefreshCw, 
  PlayCircle, 
  CheckCircle, 
  XCircle,
  Clock,
  BarChart,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Download,
  Filter,
  Search,
  Code,
} from 'lucide-react';
import { cn, formatDuration } from '@/lib/utils';
import { regressionApi } from '@/lib/api';

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

const testFiles = [
  'tb_fifo_basic.sv',
  'tb_fifo_reset.sv',
  'tb_fifo_sweep.sv',
  'tb_fifo_fifo.sv',
  'tb_fifo_handshake.sv',
  'tb_fifo_random.sv',
];

export default function RegressionPage() {
  const [rtlContent, setRtlContent] = useState(defaultRtl);
  const [selectedTests, setSelectedTests] = useState<string[]>(testFiles);
  const [topModule, setTopModule] = useState('tb_fifo_sync');
  const [simulator, setSimulator] = useState('verilator');
  const [timeout, setTimeout] = useState(60);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  const handleRun = async () => {
    setLoading(true);
    try {
      const res = await regressionApi.run({
        rtl_files: [rtlContent],
        test_files: selectedTests,
        top_module: topModule,
        simulator,
        timeout,
      });
      setResult(res);
      setHistory(prev => [res, ...prev].slice(0, 10));
    } catch (error) {
      console.error('Regression failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTest = (test: string) => {
    setSelectedTests(prev => 
      prev.includes(test) ? prev.filter(t => t !== test) : [...prev, test]
    );
  };

  const getStatusIcon = (success: boolean) => 
    success ? <CheckCircle className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">Regression</h1>
            <button
              onClick={handleRun}
              disabled={loading || selectedTests.length === 0}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <PlayCircle className="w-4 h-4 mr-2" />
                  Run Regression ({selectedTests.length} tests)
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Config Panel */}
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
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  <span className="font-medium">Test Suite ({selectedTests.length}/{testFiles.length})</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setSelectedTests(testFiles)}
                    className="px-2 py-1 text-xs bg-green-500/20 text-green-400 rounded hover:bg-green-500/30"
                  >
                    All
                  </button>
                  <button
                    onClick={() => setSelectedTests([])}
                    className="px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded hover:bg-red-500/30"
                  >
                    None
                  </button>
                </div>
              </div>
              <div className="p-4 space-y-2 max-h-60 overflow-y-auto">
                {testFiles.map((test) => (
                  <label key={test} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedTests.includes(test)}
                      onChange={() => toggleTest(test)}
                      className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                    />
                    <span className="text-sm font-mono">{test}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-4 space-y-4">
              <div>
                <label className="text-sm text-muted-foreground block mb-1">Top Module</label>
                <input
                  type="text"
                  value={topModule}
                  onChange={(e) => setTopModule(e.target.value)}
                  className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-1">Simulator</label>
                <select
                  value={simulator}
                  onChange={(e) => setSimulator(e.target.value)}
                  className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
                >
                  <option value="verilator">Verilator</option>
                  <option value="icarus">Icarus Verilog</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-1">Timeout (s)</label>
                <input
                  type="number"
                  value={timeout}
                  onChange={(e) => setTimeout(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
                />
              </div>
            </div>
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-4">
            {result && (
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="border-b border-border px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-5 h-5" />
                    <span className="font-medium">Regression Results</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={cn('px-3 py-1 text-sm font-medium rounded-lg', 
                      result.failed === 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                    )}>
                      {result.failed === 0 ? 'PASSED' : 'FAILED'}
                    </span>
                    <Download className="w-4 h-4 text-muted-foreground hover:text-foreground cursor-pointer" />
                  </div>
                </div>

                <div className="p-4 grid grid-cols-4 gap-4 mb-4">
                  <StatCard label="Total" value={result.total} icon={PlayCircle} />
                  <StatCard label="Passed" value={result.passed} icon={CheckCircle} />
                  <StatCard label="Failed" value={result.failed} icon={XCircle} />
                  <StatCard label="Duration" value={formatDuration(result.duration_seconds)} icon={Clock} />
                </div>

                <div className="border-t border-border">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Test</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Status</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Duration</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Exit Code</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Error</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/50">
                        {Object.entries(result.results || {}).map(([name, data]: [string, any]) => (
                          <tr key={name} className="hover:bg-secondary/50">
                            <td className="px-4 py-3 font-mono text-sm">{name}</td>
                            <td className="px-4 py-3">
                              <span className="flex items-center gap-1">
                                {getStatusIcon(data.success)}
                                <span className={data.success ? 'text-green-400' : 'text-red-400'}>
                                  {data.success ? 'PASSED' : 'FAILED'}
                                </span>
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm">{data.duration ? formatDuration(data.duration) : 'N/A'}</td>
                            <td className="px-4 py-3 text-sm font-mono">{data.exit_code ?? 'N/A'}</td>
                            <td className="px-4 py-3 text-sm text-red-400 truncate max-w-xs">
                              {data.error || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {history.length > 0 && (
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="border-b border-border px-4 py-3">
                  <span className="font-medium">Recent Runs</span>
                </div>
                <div className="p-4 space-y-3">
                  {history.slice(0, 5).map((run, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-secondary/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className={cn('px-2 py-0.5 text-xs rounded font-medium',
                          run.failed === 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        )}>
                          {run.failed === 0 ? 'PASSED' : 'FAILED'}
                        </span>
                        <span className="text-sm font-mono">{run.total} tests</span>
                        <span className="text-sm text-muted-foreground">{run.passed} passed, {run.failed} failed</span>
                      </div>
                      <span className="text-sm text-muted-foreground">{formatDuration(run.duration_seconds)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!result && history.length === 0 && (
              <div className="bg-card border border-border rounded-xl p-12 text-center text-muted-foreground">
                <RefreshCw className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Configure test suite and run regression</p>
              </div>
            )}
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