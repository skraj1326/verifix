'use client';

import { useState, useEffect } from 'react';
import { 
  TestTube, 
  Copy, 
  Play, 
  Download,
  Filter,
  Search,
  Code,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn, truncate, getConfidenceColor } from '@/lib/utils';
import { verificationApi } from '@/lib/api';

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

export default function TestsPage() {
  const [rtlContent, setRtlContent] = useState(defaultRtl);
  const [tests, setTests] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');
  const [selectedTest, setSelectedTest] = useState<any>(null);
  const [testTypeFilter, setTestTypeFilter] = useState('all');

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const result = await verificationApi.generateTests(rtlContent);
      setTests(result.tests || []);
    } catch (error) {
      console.error('Test generation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateUvm = async () => {
    setLoading(true);
    try {
      const result = await verificationApi.generateUvm(rtlContent);
      setTests(prev => [...prev, ...(result.uvm_components || [])]);
    } catch (error) {
      console.error('UVM generation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredTests = tests.filter((t: any) => {
    if (filter && !t.name.toLowerCase().includes(filter.toLowerCase()) &&
        !t.verification_objective.toLowerCase().includes(filter.toLowerCase())) {
      return false;
    }
    if (testTypeFilter !== 'all' && t.test_type !== testTypeFilter) {
      return false;
    }
    return true;
  });

  const testTypes = [...new Set(tests.map(t => t.test_type))];

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">Test Generator</h1>
            <div className="flex items-center gap-2">
              <button
                onClick={handleGenerateUvm}
                disabled={loading}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
              >
                Generate UVM
              </button>
              <button
                onClick={handleGenerate}
                disabled={loading}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {loading ? 'Generating...' : 'Generate Tests'}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Editor Panel */}
          <div className="lg:col-span-2">
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
                className="w-full h-96 p-4 font-mono text-sm resize-none bg-transparent outline-none"
                spellCheck={false}
              />
            </div>
          </div>

          {/* Tests Panel */}
          <div className="space-y-4">
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="border-b border-border px-4 py-3 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <TestTube className="w-5 h-5" />
                  <span className="font-medium">Generated Tests</span>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    placeholder="Filter tests..."
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm w-48"
                  />
                  <select
                    value={testTypeFilter}
                    onChange={(e) => setTestTypeFilter(e.target.value)}
                    className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm"
                  >
                    <option value="all">All Types</option>
                    {testTypes.map((type: string) => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="p-4">
                {loading ? (
                  <div className="text-center py-8 text-muted-foreground">Generating tests...</div>
                ) : tests.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    <TestTube className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Generate tests from RTL to see results</p>
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[600px] overflow-y-auto">
                    {filteredTests.map((test, idx) => (
                      <TestCard
                        key={idx}
                        test={test}
                        onSelect={setSelectedTest}
                        onCopy={copyToClipboard}
                        isSelected={selectedTest === test}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {selectedTest && (
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="border-b border-border px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    <span className="font-medium">Test Details</span>
                  </div>
                  <button
                    onClick={() => setSelectedTest(null)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    ✕
                  </button>
                </div>
                <div className="p-4 space-y-4">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-sm">{selectedTest.name}</span>
                    <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                      {selectedTest.test_type}
                    </span>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Verification Objective</label>
                    <p className="mt-1">{selectedTest.verification_objective}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Target Coverage</label>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {selectedTest.target_coverage.map((c: string) => (
                        <span key={c} className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Target Signals</label>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {selectedTest.target_signals.map((s: string) => (
                        <span key={s} className="px-2 py-0.5 text-xs bg-muted text-muted-foreground rounded">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Test Code</label>
                    <div className="mt-1 relative">
                      <button
                        onClick={() => copyToClipboard(selectedTest.code)}
                        className="absolute right-2 top-2 px-2 py-1 text-xs bg-secondary rounded hover:bg-secondary/80"
                      >
                        Copy
                      </button>
                      <pre className="bg-secondary/50 p-4 rounded-lg overflow-x-auto max-h-96">
                        <code className="font-mono text-sm">{selectedTest.code}</code>
                      </pre>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function TestCard({ test, onSelect, onCopy, isSelected }: any) {
  const getStatusIcon = (type: string) => {
    switch (type) {
      case 'directed': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'constrained_random': return <Zap className="w-4 h-4 text-yellow-500" />;
      case 'uvm_sequence_item':
      case 'uvm_sequence':
      case 'uvm_monitor': return <Code className="w-4 h-4 text-purple-500" />;
      default: return <TestTube className="w-4 h-4" />;
    }
  };

  return (
    <div
      className={cn(
        'border border-border rounded-lg p-4 cursor-pointer transition-colors',
        isSelected ? 'border-primary bg-primary/5' : 'hover:bg-secondary/50'
      )}
      onClick={() => onSelect(test)}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {getStatusIcon(test.test_type)}
            <span className="font-mono text-sm font-medium">{test.name}</span>
            <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
              {test.test_type}
            </span>
          </div>
          <p className="text-sm text-muted-foreground line-clamp-1">{test.verification_objective}</p>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onCopy(test.code); }}
          className="p-1.5 hover:bg-secondary rounded-lg transition-colors flex-shrink-0"
          title="Copy test code"
        >
          <Copy className="w-4 h-4" />
        </button>
      </div>
      <div className="flex flex-wrap gap-1 mb-2">
        {test.target_coverage.slice(0, 4).map((c: string) => (
          <span key={c} className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
            {c}
          </span>
        ))}
        {test.target_coverage.length > 4 && (
          <span className="px-2 py-0.5 text-xs bg-muted text-muted-foreground rounded">
            +{test.target_coverage.length - 4} more
          </span>
        )}
      </div>
      <div className="bg-secondary/50 rounded-lg p-2">
        <pre className="font-mono text-xs overflow-x-auto max-h-24">
          <code>{truncate(test.code, 300)}</code>
        </pre>
      </div>
    </div>
  );
}