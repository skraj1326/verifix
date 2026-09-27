'use client';

import { useState, useEffect } from 'react';
import { 
  PlayCircle, 
  Code, 
  Terminal, 
  Copy,
  CheckCircle,
  XCircle,
  Clock,
  RotateCcw,
  Download,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn, formatDuration } from '@/lib/utils';
import { simulationApi } from '@/lib/api';

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

const defaultTest = `module tb_fifo_sync;
    logic clk, reset, wr_en, rd_en;
    logic [31:0] din, dout;
    logic full, empty;
    logic [4:0] count;

    fifo_sync uut (
        .clk(clk),
        .reset(reset),
        .wr_en(wr_en),
        .rd_en(rd_en),
        .din(din),
        .dout(dout),
        .full(full),
        .empty(empty),
        .count(count)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    initial begin
        reset = 1; wr_en = 0; rd_en = 0; din = 0;
        #20 reset = 0;
        #10 wr_en = 1; din = 32'hAA; #10;
        wr_en = 0; #10;
        rd_en = 1; #10;
        rd_en = 0; #10;
        $finish;
    end
endmodule`;

export default function SimulationPage() {
  const [rtlContent, setRtlContent] = useState(defaultRtl);
  const [testContent, setTestContent] = useState(defaultTest);
  const [topModule, setTopModule] = useState('tb_fifo_sync');
  const [simulator, setSimulator] = useState('verilator');
  const [timeout, setTimeout] = useState(60);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'stdout' | 'stderr' | 'compile'>('stdout');

  const handleRun = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await simulationApi.run({
        rtl_content: rtlContent,
        test_code: testContent,
        top_module: topModule,
        simulator,
        timeout,
      });
      setResult(res);
    } catch (error) {
      console.error('Simulation failed:', error);
      setResult({ error: error.message, status: 'ERROR' });
    } finally {
      setLoading(false);
    }
  };

  const handleCompile = async () => {
    setLoading(true);
    try {
      const res = await simulationApi.compile({
        rtl_files: [rtlContent],
        testbench: testContent,
        top_module: topModule,
        simulator,
        timeout,
      });
      setResult({ compilation: res, status: res.success ? 'COMPILED' : 'COMPILE_FAILED' });
    } catch (error) {
      console.error('Compilation failed:', error);
      setResult({ error: error.message, status: 'ERROR' });
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PASSED': return 'bg-green-500/20 text-green-400';
      case 'FAILED': return 'bg-red-500/20 text-red-400';
      case 'COMPILED': return 'bg-blue-500/20 text-blue-400';
      case 'COMPILE_FAILED': return 'bg-red-500/20 text-red-400';
      case 'UNAVAILABLE': return 'bg-yellow-500/20 text-yellow-400';
      case 'ERROR': return 'bg-red-500/20 text-red-400';
      default: return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">Simulation</h1>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCompile}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                Compile Only
              </button>
              <button
                onClick={handleRun}
                disabled={loading}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-4 h-4 mr-2" />
                    Run Simulation
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* RTL Panel */}
          <div className="space-y-4">
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
                  <span className="font-medium">Testbench</span>
                </div>
              </div>
              <textarea
                value={testContent}
                onChange={(e) => setTestContent(e.target.value)}
                className="w-full h-64 p-4 font-mono text-sm resize-none bg-transparent outline-none"
                spellCheck={false}
              />
            </div>

            <div className="bg-card border border-border rounded-xl p-4 space-y-4">
              <div className="grid grid-cols-3 gap-4">
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
          </div>

          {/* Results Panel */}
          <div className="space-y-4">
            {result && (
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="border-b border-border px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-5 h-5" />
                    <span className="font-medium">Simulation Result</span>
                  </div>
                  <span className={cn('px-3 py-1 text-sm font-medium rounded-lg', getStatusColor(result.status || 'UNKNOWN'))}>
                    {result.status || 'UNKNOWN'}
                  </span>
                </div>
                <div className="px-4 py-3 border-b border-border flex gap-2">
                  <button
                    onClick={() => setActiveTab('stdout')}
                    className={cn('px-3 py-1 text-sm rounded', activeTab === 'stdout' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
                  >
                    Stdout
                  </button>
                  <button
                    onClick={() => setActiveTab('stderr')}
                    className={cn('px-3 py-1 text-sm rounded', activeTab === 'stderr' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
                  >
                    Stderr
                  </button>
                  <button
                    onClick={() => setActiveTab('compile')}
                    className={cn('px-3 py-1 text-sm rounded', activeTab === 'compile' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
                  >
                    Compile Log
                  </button>
                </div>
                <div className="p-4 h-96 overflow-y-auto bg-secondary/30">
                  <pre className="font-mono text-sm whitespace-pre-wrap">
                    {activeTab === 'stdout' ? result.stdout || result.simulation_log || 'No output' :
                     activeTab === 'stderr' ? result.stderr || 'No errors' :
                     result.compilation_log || result.compilation?.compilation_log || 'No compilation log'}
                  </pre>
                </div>
              </div>
            )}

            {result && (
              <div className="bg-card border border-border rounded-xl p-4 grid grid-cols-4 gap-4 text-center">
                <StatCard label="Exit Code" value={result.exit_code ?? 'N/A'} />
                <StatCard label="Duration" value={result.duration_seconds ? formatDuration(result.duration_seconds) : 'N/A'} />
                <StatCard label="Command" value={<code className="text-xs truncate block">{result.command || 'N/A'}</code>} />
                <StatCard label="Verilator" value={simulationApi ? 'Available' : 'Not Available'} />
              </div>
            )}

            {!result && (
              <div className="bg-card border border-border rounded-xl p-12 text-center text-muted-foreground">
                <PlayCircle className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Configure and run simulation to see results</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: any }) {
  return (
    <div className="bg-secondary/50 rounded-lg p-4">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-lg font-bold tabular-nums">{value}</div>
    </div>
  );
}