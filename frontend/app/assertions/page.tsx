'use client';

import { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Copy, 
  Check,
  AlertCircle,
  Download,
  Filter,
  Search,
  Code,
  Zap,
  AlertTriangle,
  Info,
} from 'lucide-react';
import { cn, getConfidenceColor, truncate } from '@/lib/utils';
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

export default function AssertionsPage() {
  const [rtlContent, setRtlContent] = useState(defaultRtl);
  const [assertions, setAssertions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');
  const [selectedAssertion, setSelectedAssertion] = useState<any>(null);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const result = await verificationApi.generateAssertions(rtlContent);
      setAssertions(result.assertions || []);
    } catch (error) {
      console.error('Assertion generation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredAssertions = assertions.filter((a: any) => {
    if (!filter) return true;
    const search = filter.toLowerCase();
    return a.name.toLowerCase().includes(search) ||
           a.description.toLowerCase().includes(search) ||
           a.sva_code.toLowerCase().includes(search);
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">SVA Assertions</h1>
            <div className="flex items-center gap-2">
              <button
                onClick={handleGenerate}
                disabled={loading}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {loading ? 'Generating...' : 'Generate Assertions'}
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

          {/* Assertions Panel */}
          <div className="space-y-4">
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="border-b border-border px-4 py-3 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5" />
                  <span className="font-medium">Generated Assertions</span>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    placeholder="Filter assertions..."
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm w-48"
                  />
                  {assertions.length > 0 && (
                    <button className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm hover:bg-secondary/80">
                      <Download className="w-4 h-4 mr-1" />
                      Export
                    </button>
                  )}
                </div>
              </div>
              <div className="p-4">
                {loading ? (
                  <div className="text-center py-8 text-muted-foreground">Generating assertions...</div>
                ) : assertions.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    <ShieldCheck className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Generate assertions from RTL to see results</p>
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[600px] overflow-y-auto">
                    {filteredAssertions.map((assertion, idx) => (
                      <AssertionCard
                        key={idx}
                        assertion={assertion}
                        onSelect={setSelectedAssertion}
                        onCopy={copyToClipboard}
                        isSelected={selectedAssertion === assertion}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {selectedAssertion && (
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="border-b border-border px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Info className="w-5 h-5" />
                    <span className="font-medium">Assertion Details</span>
                  </div>
                  <button
                    onClick={() => setSelectedAssertion(null)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    ✕
                  </button>
                </div>
                <div className="p-4 space-y-4">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm">{selectedAssertion.name}</span>
                    <span className={cn('px-2 py-0.5 text-xs rounded', getConfidenceColor(selectedAssertion.confidence))}>
                      {selectedAssertion.confidence}
                    </span>
                    <span className="px-2 py-0.5 text-xs bg-muted text-muted-foreground rounded">
                      {selectedAssertion.validation_status}
                    </span>
                    <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                      {selectedAssertion.classification}
                    </span>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Description</label>
                    <p className="mt-1">{selectedAssertion.description}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Evidence</label>
                    <p className="mt-1 text-sm">{selectedAssertion.evidence}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Assumptions</label>
                    <p className="mt-1 text-sm">{selectedAssertion.assumptions}</p>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">SVA Code</label>
                    <div className="mt-1 relative">
                      <button
                        onClick={() => copyToClipboard(selectedAssertion.sva_code)}
                        className="absolute right-2 top-2 px-2 py-1 text-xs bg-secondary rounded hover:bg-secondary/80"
                      >
                        Copy
                      </button>
                      <pre className="bg-secondary/50 p-4 rounded-lg overflow-x-auto max-h-60">
                        <code className="font-mono text-sm">{selectedAssertion.sva_code}</code>
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

function AssertionCard({ assertion, onSelect, onCopy, isSelected }: any) {
  return (
    <div
      className={cn(
        'border border-border rounded-lg p-4 cursor-pointer transition-colors',
        isSelected ? 'border-primary bg-primary/5' : 'hover:bg-secondary/50'
      )}
      onClick={() => onSelect(assertion)}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-sm font-medium">{assertion.name}</span>
            <span className={cn('px-2 py-0.5 text-xs rounded', getConfidenceColor(assertion.confidence))}>
              {assertion.confidence}
            </span>
            <span className="px-2 py-0.5 text-xs bg-muted text-muted-foreground rounded">
              {assertion.assertion_type}
            </span>
          </div>
          <p className="text-sm text-muted-foreground line-clamp-1">{assertion.description}</p>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onCopy(assertion.sva_code); }}
          className="p-1.5 hover:bg-secondary rounded-lg transition-colors flex-shrink-0"
          title="Copy SVA code"
        >
          <Copy className="w-4 h-4" />
        </button>
      </div>
      <div className="bg-secondary/50 rounded-lg p-2">
        <pre className="font-mono text-xs overflow-x-auto max-h-24">
          <code>{truncate(assertion.sva_code, 300)}</code>
        </pre>
      </div>
    </div>
  );
}