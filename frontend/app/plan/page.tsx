'use client';

import { useState, useEffect } from 'react';
import { 
  FileText, 
  Search, 
  Filter, 
  Download,
  ChevronRight,
  AlertCircle,
  ShieldCheck,
  BarChart,
  Zap,
  Settings,
  Plus,
  Eye,
  Copy,
} from 'lucide-react';
import { cn, formatDate, getConfidenceColor } from '@/lib/utils';
import { verificationApi, projectsApi } from '@/lib/api';
import { api } from '@/lib/api';

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

    property p_no_write_when_full;
        @(posedge clk) disable iff (reset) full |-> !wr_en;
    endproperty
    a_no_write_when_full: assert property (p_no_write_when_full);

endmodule`;

export default function PlanPage() {
  const [rtlContent, setRtlContent] = useState(defaultRtl);
  const [plan, setPlan] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [specification, setSpecification] = useState('');

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const result = await verificationApi.generatePlan(rtlContent, specification);
      setPlan(result);
    } catch (error) {
      console.error('Plan generation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredItems = plan?.plan?.items?.filter((item: any) => {
    if (filter && !item.title.toLowerCase().includes(filter.toLowerCase()) &&
        !item.requirement.toLowerCase().includes(filter.toLowerCase())) {
      return false;
    }
    if (selectedCategory !== 'all' && !item.id.includes(selectedCategory.toUpperCase())) {
      return false;
    }
    return true;
  }) || [];

  const categories = [...new Set(plan?.plan?.items?.map((item: any) => 
    item.id.split('-')[1] || 'OTHER'
  ))] || [];

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">Verification Plan</h1>
            <div className="flex items-center gap-2">
              <button
                onClick={handleGenerate}
                disabled={loading}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {loading ? 'Generating...' : 'Generate Plan'}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Editor Panel */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="border-b border-border px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
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

            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="border-b border-border px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  <span className="font-medium">Specification (Optional)</span>
                </div>
              </div>
              <textarea
                value={specification}
                onChange={(e) => setSpecification(e.target.value)}
                className="w-full h-32 p-4 font-mono text-sm resize-none bg-transparent outline-none"
                placeholder="Enter specification requirements..."
              />
            </div>
          </div>

          {/* Plan Panel */}
          <div className="space-y-4">
            {plan && (
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="border-b border-border px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    <span className="font-medium">Plan Summary</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Download className="w-4 h-4" />
                    <span className="text-sm text-muted-foreground">{plan.plan?.items?.length || 0} items</span>
                  </div>
                </div>
                <div className="p-4 grid grid-cols-2 gap-4">
                  <StatCard label="Total Items" value={plan.summary?.total_items || 0} />
                  <StatCard label="Modules" value={plan.summary?.modules_analyzed || 0} />
                  <StatCard label="FSMs" value={plan.summary?.total_fsm || 0} />
                  <StatCard label="Assertions" value={plan.summary?.total_assertions || 0} />
                  <div className="col-span-2">
                    <h4 className="font-medium mb-2">Categories</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(plan.summary?.categories || {}).map(([cat, count]) => (
                        <span key={cat} className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                          {cat}: {count}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="col-span-2">
                    <h4 className="font-medium mb-2">Sources</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(plan.summary?.source_breakdown || {}).map(([src, count]) => (
                        <span key={src} className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded">
                          {src}: {count}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="border-b border-border px-4 py-3 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  <span className="font-medium">Verification Items</span>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    placeholder="Filter items..."
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm w-48"
                  />
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm"
                  >
                    <option value="all">All Categories</option>
                    {categories.map((cat: string) => (
                      <option key={cat} value={cat.toLowerCase()}>{cat}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">ID</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Feature</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Priority</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Source</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {filteredItems.map((item: any) => (
                      <tr key={item.id} className="hover:bg-secondary/50 cursor-pointer">
                        <td className="px-4 py-3 font-mono text-sm">{item.id}</td>
                        <td className="px-4 py-3 text-sm max-w-xs truncate">{item.feature}</td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                            {item.priority}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded">
                            {item.source_type}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn('px-2 py-0.5 text-xs rounded', getConfidenceColor(item.confidence))}>
                            {item.confidence}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {filteredItems.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                          No items match the filter
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {plan && plan.plan?.items && (
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="border-b border-border px-4 py-3">
                  <span className="font-medium">Item Details (click row above)</span>
                </div>
                <div className="p-4">
                  <p className="text-sm text-muted-foreground">Select an item from the table to view details</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-secondary/50 rounded-lg p-4">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-2xl font-bold tabular-nums">{value}</div>
    </div>
  );
}