import React, { useState, useEffect } from "react";
import { MonacoEditor } from "@/components/editor/MonacoEditor";
import { FileText, Play, Download, Upload, Search, ChevronDown, Save, Loader2, GitBranch, Code2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

const FIFO_EXAMPLE = `// FIFO Synchronous - Clean Verification Example
// VerifiX AI - V0.1 Demo RTL

module fifo_sync #(
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

    // Internal signals
    logic [DATA_WIDTH-1:0] mem [0:DEPTH-1];
    logic [$clog2(DEPTH):0] wr_ptr, rd_ptr;
    logic [$clog2(DEPTH):0] wr_ptr_next, rd_ptr_next;
    logic [$clog2(DEPTH):0] count_next;
    logic full_next, empty_next;
    logic [$clog2(DEPTH):0] occupancy;

    // Write pointer logic
    assign wr_ptr_next = wr_ptr + (wr_en && !full);
    assign rd_ptr_next = rd_ptr + (rd_en && !empty);
    assign count_next  = wr_ptr_next - rd_ptr_next;
    assign full_next   = (count_next == DEPTH);
    assign empty_next  = (count_next == 0);

    // Memory write
    always_ff @(posedge clk) begin
        if (wr_en && !full) begin
            mem[wr_ptr[$clog2(DEPTH)-1:0]] <= din;
        end
    end

    // Memory read (registered output)
    always_ff @(posedge clk) begin
        if (reset) begin
            dout <= '0;
        end else if (rd_en && !empty) begin
            dout <= mem[rd_ptr[$clog2(DEPTH)-1:0]];
        end
    end

    // State registers
    always_ff @(posedge clk) begin
        if (reset) begin
            wr_ptr  <= '0;
            rd_ptr  <= '0;
            count   <= '0;
            full    <= 1'b0;
            empty   <= 1'b1;
        end else begin
            wr_ptr  <= wr_ptr_next;
            rd_ptr  <= rd_ptr_next;
            count   <= count_next;
            full    <= full_next;
            empty   <= empty_next;
        end
    end

    // Assertions for verification
    property p_reset;
        @(posedge clk) reset |-> ##1 (!full && empty && count == 0 && wr_ptr == 0 && rd_ptr == 0);
    endproperty
    a_reset: assert property (p_reset);

    property p_no_write_when_full;
        @(posedge clk) disable iff (reset) full |-> !wr_en;
    endproperty
    a_no_write_when_full: assert property (p_no_write_when_full);

    property p_no_read_when_empty;
        @(posedge clk) disable iff (reset) empty |-> !rd_en;
    endproperty
    a_no_read_when_empty: assert property (p_no_read_when_empty);

    property p_wr_ptr_increments;
        @(posedge clk) disable iff (reset) (wr_en && !full) |=> (wr_ptr == $past(wr_ptr) + 1);
    endproperty
    a_wr_ptr_increments: assert property (p_wr_ptr_increments);

    property p_rd_ptr_increments;
        @(posedge clk) disable iff (reset) (rd_en && !empty) |=> (rd_ptr == $past(rd_ptr) + 1);
    endproperty
    a_rd_ptr_increments: assert property (p_rd_ptr_increments);

    property p_count_tracking;
        @(posedge clk) disable iff (reset) count == wr_ptr - rd_ptr;
    endproperty
    a_count_tracking: assert property (p_count_tracking);

    property p_full_empty_mutex;
        @(posedge clk) disable iff (reset) !(full && empty) || (DEPTH == 1);
    endproperty
    a_full_empty_mutex: assert property (p_full_empty_mutex);

    // Cover properties
    property p_cover_full;
        @(posedge clk) disable iff (reset) full;
    endproperty
    c_full: cover property (p_cover_full);

    property p_cover_empty;
        @(posedge clk) disable iff (reset) empty;
    endproperty
    c_empty: cover property (p_cover_empty);

    property p_cover_simultaneous_rw;
        @(posedge clk) disable iff (reset) wr_en && rd_en && !full && !empty;
    endproperty
    c_simultaneous_rw: cover property (p_cover_simultaneous_rw);

    property p_cover_wr_at_full;
        @(posedge clk) disable iff (reset) full && wr_en;
    endproperty
    c_wr_at_full: cover property (p_cover_wr_at_full);

    property p_cover_rd_at_empty;
        @(posedge clk) disable iff (reset) empty && rd_en;
    endproperty
    c_rd_at_empty: cover property (p_cover_rd_at_empty);

endmodule`;

export default function RTLEditorPage() {
  const router = useRouter();
  const [rtlContent, setRtlContent] = useState(FIFO_EXAMPLE);
  const [filename, setFilename] = useState("fifo_sync.sv");
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"editor" | "analysis" | "hierarchy" | "files">("editor");
  const [designId, setDesignId] = useState<string | null>(null);
  const [files, setFiles] = useState<{name: string, content: string}[]>([
    { name: "fifo_sync.sv", content: FIFO_EXAMPLE },
  ]);

  const handleAnalyze = async () => {
    if (!rtlContent.trim()) {
      toast.error("No RTL content to analyze");
      return;
    }

    setAnalyzing(true);
    try {
      const response = await api.post("/rtl/analyze", {
        content: rtlContent,
        filename,
      });
      setAnalysisResult(response.data);
      // Extract design ID from the first module if available
      if (response.data.modules && response.data.modules.length > 0) {
        // Use a generated design ID based on filename and timestamp
        setDesignId(`design_${Date.now()}`);
      }
      setActiveTab("analysis");
      toast.success("RTL analysis complete");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFullFlow = async () => {
    if (!rtlContent.trim()) {
      toast.error("No RTL content to process");
      return;
    }

    setAnalyzing(true);
    try {
      // Create project
      const projectRes = await api.post("/projects/", {
        name: filename.replace(".sv", "").replace("_", " ").toUpperCase(),
        description: `Auto-generated from ${filename}`,
      });
      const projectId = projectRes.data.id;

      // Upload RTL
      await api.post(`/projects/${projectId}/rtl`, {
        content: rtlContent,
        filename,
      });

      // Run full verification flow
      const flowRes = await api.post("/verification/full-flow", {
        rtl_content: rtlContent,
        specification: `Parameterized synchronous FIFO with full/empty flags, occupancy counter, and built-in assertions.`,
      });

      toast.success("Full verification flow complete!");
      router.push(`/projects/${projectId}`);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Full flow failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const content = await file.text();
    setRtlContent(content);
    setFilename(file.name);
    
    // Add to files list
    setFiles(prev => [...prev, { name: file.name, content }]);
    toast.success(`Loaded ${file.name}`);
  };

  const handleFileSelect = (file: {name: string, content: string}) => {
    setRtlContent(file.content);
    setFilename(file.name);
    setActiveTab("editor");
  };

  const handleDownload = () => {
    const blob = new Blob([rtlContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const stats = analysisResult?.summary ? (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <div className="text-2xl font-bold text-blue-400">{analysisResult.summary.num_modules}</div>
        <div className="text-xs text-gray-400">Modules</div>
      </div>
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <div className="text-2xl font-bold text-purple-400">{analysisResult.summary.total_ports}</div>
        <div className="text-xs text-gray-400">Ports</div>
      </div>
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <div className="text-2xl font-bold text-green-400">{analysisResult.summary.total_fsm_count}</div>
        <div className="text-xs text-gray-400">FSMs</div>
      </div>
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <div className="text-2xl font-bold text-orange-400">{analysisResult.summary.total_assertions}</div>
        <div className="text-xs text-gray-400">Assertions</div>
      </div>
    </div>
  ) : null;

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-gray-800 bg-gray-900/50">
        <div className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            className="bg-transparent border-none outline-none text-white font-mono text-sm w-40"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="cursor-pointer">
            <Upload className="w-5 h-5 text-gray-400 hover:text-white" />
            <input
              type="file"
              accept=".sv,.v,.svh,.vh"
              onChange={handleFileUpload}
              className="hidden"
              id="file-upload"
            />
          </label>
          <button
            onClick={handleDownload}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            title="Download RTL"
          >
            <Download className="w-5 h-5" />
          </button>
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            <Search className="w-4 h-4" />
            {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : "Analyze"}
          </button>
          <button
            onClick={handleFullFlow}
            disabled={analyzing}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            Full Flow
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800 bg-gray-900/50">
        {[
          { id: "editor", label: "Editor", icon: FileText },
          { id: "analysis", label: "Analysis", icon: Search },
          { id: "hierarchy", label: "Hierarchy", icon: GitBranch },
          { id: "files", label: "Files", icon: FileText },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors border-b-2 flex items-center gap-2",
              activeTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-gray-400 hover:text-gray-200"
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "editor" && (
          <div className="h-full p-4">
            <MonacoEditor
              value={rtlContent}
              onChange={setRtlContent}
              language="systemverilog"
              theme="vs-dark"
              height="calc(100% - 2rem)"
            />
          </div>
        )}

        {activeTab === "analysis" && analysisResult && (
          <div className="h-full p-4 overflow-auto">
            {stats}
            <div className="space-y-4">
              {analysisResult.modules.map((module: any) => (
                <div key={module.name} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold">{module.name}</h3>
                    <span className="px-2 py-1 text-xs bg-gray-700 rounded">{module.module_type}</span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div>
                      <h4 className="text-sm font-medium text-gray-400 mb-2">Ports</h4>
                      <ul className="space-y-1 text-sm">
                        {module.ports.map((p: any) => (
                          <li key={p.name} className="flex items-center gap-2">
                            <span className={cn(
                              "px-1.5 py-0.5 rounded text-xs font-mono",
                              p.direction === "input" && "bg-blue-900/50 text-blue-300",
                              p.direction === "output" && "bg-green-900/50 text-green-300",
                              p.direction === "inout" && "bg-yellow-900/50 text-yellow-300"
                            )}>
                              {p.direction}
                            </span>
                            <span>{p.name}</span>
                            {p.width && <span className="text-gray-500">[{p.width}]</span>}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium text-gray-400 mb-2">Signals</h4>
                      <ul className="space-y-1 text-sm max-h-40 overflow-auto">
                        {module.signals.slice(0, 20).map((s: any) => (
                          <li key={s.name} className="flex items-center gap-2">
                            <span className="px-1.5 py-0.5 rounded text-xs font-mono bg-purple-900/50 text-purple-300">
                              {s.type}
                            </span>
                            <span>{s.name}</span>
                            {s.width && <span className="text-gray-500">[{s.width}]</span>}
                          </li>
                        ))}
                        {module.signals.length > 20 && (
                          <li className="text-gray-500 text-xs">... and {module.signals.length - 20} more</li>
                        )}
                      </ul>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium text-gray-400 mb-2">FSMs</h4>
                      {module.fsm_info.length > 0 ? (
                        <ul className="space-y-1 text-sm">
                          {module.fsm_info.map((fsm: any) => (
                            <li key={fsm.name}>
                              <div className="font-mono">{fsm.name}</div>
                              <div className="text-gray-500 text-xs">
                                {fsm.states.length} states, {fsm.transitions.length} transitions
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-gray-500 text-sm">No FSMs detected</p>
                      )}
                    </div>
                  </div>

                  {module.metadata?.corner_cases && module.metadata.corner_cases.length > 0 && (
                    <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-800/50 rounded-lg">
                      <h4 className="text-sm font-medium text-yellow-300 mb-2">Corner Cases Detected</h4>
                      <ul className="space-y-1 text-sm">
                        {module.metadata.corner_cases.map((cc: any, i: number) => (
                          <li key={i} className="text-yellow-200">
                            <strong>{cc.type}:</strong> {cc.description}
                            <ul className="ml-4 mt-1 space-y-0.5">
                              {cc.cases.map((c: string, j: number) => (
                                <li key={j} className="text-xs text-yellow-300">• {c}</li>
                              ))}
                            </ul>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "analysis" && !analysisResult && (
          <div className="h-full flex items-center justify-center text-gray-500">
            Click "Analyze" to see RTL analysis results
          </div>
        )}

        {activeTab === "hierarchy" && (
          <div className="h-full p-4">
            <div className="h-full">
              <iframe
                src={`/rtl/hierarchy?designId=${designId}`}
                className="w-full h-full border-0"
                title="RTL Hierarchy Browser"
              />
            </div>
          </div>
        )}

        {activeTab === "files" && (
          <div className="h-full p-4 overflow-auto">
            <div className="space-y-2">
              {files.map((file, i) => (
                <button
                  key={i}
                  onClick={() => handleFileSelect(file)}
                  className={cn(
                    "w-full p-3 rounded-lg text-left border transition-colors flex items-center justify-between",
                    filename === file.name
                      ? "bg-blue-900/30 border-blue-700"
                      : "bg-gray-800/50 border-gray-700 hover:border-gray-600"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-gray-400" />
                    <span className="font-mono text-sm">{file.name}</span>
                  </div>
                  {filename === file.name && (
                    <span className="text-xs text-blue-400">Active</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}