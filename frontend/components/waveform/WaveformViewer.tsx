"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Upload, Search, GitCompare, Loader2, AlertTriangle, X } from "lucide-react";
import toast from "react-hot-toast";

import { api, waveformApi } from "@/lib/api";

interface Transition {
  time: number;
  value: string;
}

interface Signal {
  name: string;
  transitions: Transition[];
  width: number;
  type: string;
  min_value: string;
  max_value: string;
  toggle_count: number;
  x_count: number;
  z_count: number;
}

interface WaveformUpload {
  waveform_id: string;
  filename: string;
  format: string;
  signals_count: number;
  time_range: { min: number; max: number };
  timescale: string;
  date: string;
}

interface WaveformAnalysis {
  waveform_id: string;
  filename: string;
  format: string;
  timescale: string;
  time_range: { min: number; max: number };
  total_signals: number;
  signals: Signal[];
}

interface SignalContext {
  failure_time: number;
  window: number;
  signals: Record<
    string,
    {
      value_at_failure: string;
      transitions_near_failure: { time: number; value: string }[];
      total_transitions_in_window: number;
    }
  >;
}

const ROW_HEIGHT = 28;
const LABEL_WIDTH = 200;
const MAX_ROWS = 60;

function formatTime(time: number, timescale: string) {
  return `${time} ${timescale}`;
}

/** Render a VCD value as a short human-readable label. */
function valueLabel(value: string, width: number) {
  if (/[xz]/i.test(value)) return value.toUpperCase();
  if (width === 1) return value;
  return value.replace(/^0+/, "") || "0";
}

export function WaveformViewer() {
  const [uploaded, setUploaded] = useState<WaveformUpload | null>(null);
  const [analysis, setAnalysis] = useState<WaveformAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [context, setContext] = useState<SignalContext | null>(null);
  const [failureTime, setFailureTime] = useState<string>("");
  const [compareId, setCompareId] = useState("");
  const [comparison, setComparison] = useState<any>(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadWaveform = useCallback(async (waveformId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/waveform/${waveformId}`);
      setAnalysis(response.data);
      setSelected([]);
      setContext(null);
      setComparison(null);
    } catch (err: any) {
      const message = err?.response?.data?.detail || "Failed to load waveform";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleFile = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      try {
        // Drag-and-drop bypasses the file input's `accept` filter, so reject
        // unsupported formats explicitly instead of surfacing a backend error.
        if (!file.name.toLowerCase().endsWith(".vcd")) {
          const message = `.fst is not supported yet. Only .vcd files can be parsed (UNKNOWN for .fst).`;
          setError(message);
          toast.error(message);
          return;
        }
        const uploaded = await waveformApi.upload(file);
        setUploaded(uploaded);
        await loadWaveform(uploaded.waveform_id);
        toast.success(
          `Loaded ${uploaded.signals_count} signals from ${uploaded.filename}`
        );
      } catch (err: any) {
        const message = err?.response?.data?.detail || "Upload failed";
        setError(message);
        toast.error(message);
      } finally {
        setLoading(false);
      }
    },
    [loadWaveform]
  );

  const visibleSignals = useMemo(() => {
    if (!analysis) return [];
    const matched = filter
      ? analysis.signals.filter((s) => s.name.toLowerCase().includes(filter.toLowerCase()))
      : analysis.signals;
    return matched.slice(0, MAX_ROWS);
  }, [analysis, filter]);

  const toggleSignal = (name: string) => {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  const loadContext = async () => {
    if (!uploaded) return;
    const time = Number(failureTime);
    if (!Number.isFinite(time)) {
      toast.error("Enter a numeric time to inspect");
      return;
    }
    try {
      const response = await api.getWaveformSignalContext(uploaded.waveform_id, time, 50);
      setContext(response.data);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Signal context failed");
    }
  };

  const runComparison = async () => {
    if (!uploaded || !compareId) return;
    try {
      const response = await api.post("/waveform/compare", {
        waveform_id_1: uploaded.waveform_id,
        waveform_id_2: compareId,
        tolerance: 0,
      });
      setComparison(response.data);
      toast.success("Comparison complete");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Comparison failed");
    }
  };

  const timeSpan = analysis
    ? Math.max(analysis.time_range.max - analysis.time_range.min, 1)
    : 1;

  if (!uploaded) {
    return (
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        className={`flex min-h-[24rem] flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
          dragging ? "border-blue-500 bg-blue-950/20" : "border-gray-700"
        }`}
      >
        <Upload className="h-10 w-10 text-gray-500" />
        <div>
          <p className="text-lg font-medium">Drop a VCD waveform here</p>
          <p className="mt-1 text-sm text-gray-400">
            VCD dumps are uploaded and parsed by the backend. FST is not yet
            supported.
          </p>
        </div>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Choose file
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".vcd"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-700 bg-gray-800/40 p-3">
        <div className="text-sm">
          <span className="font-medium">{uploaded.filename}</span>
          <span className="ml-2 text-gray-400">
            {uploaded.format} - {uploaded.signals_count} signals -{" "}
            {formatTime(uploaded.time_range.max, uploaded.timescale)}
          </span>
        </div>
        <button
          onClick={() => {
            setUploaded(null);
            setAnalysis(null);
            setError(null);
          }}
          className="ml-auto rounded border border-gray-600 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700"
        >
          Clear
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[12rem]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter signals"
            className="w-full rounded-lg border border-gray-700 bg-gray-900 py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
          />
        </div>
        <button
          onClick={() =>
            setSelected(
              selected.length === visibleSignals.length
                ? []
                : visibleSignals.map((s) => s.name)
            )
          }
          className="rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-700"
        >
          {selected.length === visibleSignals.length ? "Clear selection" : "Select all"}
        </button>
      </div>

      <div className="flex flex-wrap items-end gap-2 rounded-lg border border-gray-700 bg-gray-800/40 p-3">
        <label className="text-sm text-gray-300">
          <span className="mb-1 block text-xs text-gray-400">Inspect at time</span>
          <input
            value={failureTime}
            onChange={(e) => setFailureTime(e.target.value)}
            placeholder="e.g. 20"
            className="w-28 rounded border border-gray-700 bg-gray-900 px-2 py-1 text-sm outline-none focus:border-blue-500"
          />
        </label>
        <button
          onClick={loadContext}
          className="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
        >
          Show context
        </button>
        <label className="text-sm text-gray-300">
          <span className="mb-1 block text-xs text-gray-400">Compare with id</span>
          <input
            value={compareId}
            onChange={(e) => setCompareId(e.target.value.trim())}
            placeholder="wave_2_..."
            className="w-44 rounded border border-gray-700 bg-gray-900 px-2 py-1 text-sm outline-none focus:border-blue-500"
          />
        </label>
        <button
          onClick={runComparison}
          disabled={!compareId}
          className="flex items-center gap-1 rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-40"
        >
          <GitCompare className="h-4 w-4" />
          Compare
        </button>
      </div>

      {comparison && (
        <div className="rounded-lg border border-gray-700 bg-gray-800/40 p-3 text-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Comparison result</h3>
            <button onClick={() => setComparison(null)} aria-label="Dismiss comparison">
              <X className="h-4 w-4 text-gray-400 hover:text-white" />
            </button>
          </div>
          <p className="mt-2 text-gray-300">
            Matching: {comparison.matching_signals.length} | Different:{" "}
            {comparison.different_signals.length} | Only in current: {comparison.only_in_1.length}{" "}
            | Only in other: {comparison.only_in_2.length}
          </p>
          {comparison.different_signals.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-gray-400">
              {comparison.different_signals.map((d: any) => (
                <li key={d.signal}>
                  <span className="font-mono text-gray-200">{d.signal}</span>:{" "}
                  {d.differences.length} difference(s)
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading waveform...
        </div>
      )}

      {analysis && (
        <div className="overflow-x-auto rounded-lg border border-gray-700">
          <div className="min-w-[40rem]">
            <div className="flex border-b border-gray-700 bg-gray-800/60 text-xs text-gray-400">
              <div className="shrink-0 px-3 py-2" style={{ width: LABEL_WIDTH }}>
                Signal
              </div>
              <div className="flex-1 px-3 py-2">
                {formatTime(analysis.time_range.min, analysis.timescale)} to{" "}
                {formatTime(analysis.time_range.max, analysis.timescale)}
              </div>
            </div>
            {visibleSignals.map((signal) => {
              const isSelected = selected.includes(signal.name);
              return (
                <div
                  key={signal.name}
                  className={`flex border-b border-gray-800 text-xs ${
                    isSelected ? "bg-blue-950/30" : ""
                  }`}
                  style={{ height: ROW_HEIGHT }}
                >
                  <button
                    onClick={() => toggleSignal(signal.name)}
                    className="flex shrink-0 items-center gap-2 px-3 text-left hover:bg-gray-700/40"
                    style={{ width: LABEL_WIDTH }}
                  >
                    <span
                      className={`h-2 w-2 rounded-full ${
                        isSelected ? "bg-blue-400" : "bg-gray-600"
                      }`}
                    />
                    <span className="truncate font-mono text-gray-200">{signal.name}</span>
                    <span className="ml-auto text-gray-500">{signal.width}b</span>
                  </button>
                  <div className="relative flex-1">
                    <svg
                      className="h-full w-full"
                      preserveAspectRatio="none"
                      viewBox={`0 0 ${Math.max(timeSpan, 1)} 10`}
                    >
                      {signal.transitions.map((t, index) => {
                        const previous = signal.transitions[index - 1];
                        const x = t.time - analysis.time_range.min;
                        const prevX = previous
                          ? previous.time - analysis.time_range.min
                          : x;
                        const isHot =
                          context &&
                          Math.abs(t.time - context.failure_time) <= 50;
                        return (
                          <g key={`${t.time}-${index}`}>
                            {previous && (
                              <line
                                x1={prevX}
                                x2={x}
                                y1={5}
                                y2={5}
                                stroke={isHot ? "#f87171" : "#38bdf8"}
                                strokeWidth={0.18}
                                vectorEffect="non-scaling-stroke"
                              />
                            )}
                            <line
                              x1={x}
                              x2={x}
                              y1={isHot ? 1 : 2.5}
                              y2={isHot ? 9 : 7.5}
                              stroke={isHot ? "#f87171" : "#38bdf8"}
                              strokeWidth={0.18}
                              vectorEffect="non-scaling-stroke"
                            />
                            <text
                              x={x + 0.15}
                              y={8.6}
                              fontSize={2.4}
                              fill={isHot ? "#fca5a5" : "#93c5fd"}
                            >
                              {valueLabel(t.value, signal.width)}
                            </text>
                          </g>
                        );
                      })}
                    </svg>
                    {context && (
                      <div
                        className="absolute inset-y-0 w-px bg-red-500/70"
                        style={{
                          left: `${Math.min(
                            Math.max(
                              ((context.failure_time - analysis.time_range.min) / timeSpan) * 100,
                              0
                            ),
                            100
                          )}%`,
                        }}
                      />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          {analysis.total_signals > visibleSignals.length && (
            <p className="border-t border-gray-800 px-3 py-2 text-xs text-gray-500">
              Showing {visibleSignals.length} of {analysis.total_signals} signals. Refine the
              filter to narrow the list.
            </p>
          )}
        </div>
      )}

      {context && (
        <div className="rounded-lg border border-gray-700 bg-gray-800/40 p-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">
              Signal context at {context.failure_time} (window {context.window})
            </h3>
            <button onClick={() => setContext(null)} aria-label="Dismiss context">
              <X className="h-4 w-4 text-gray-400 hover:text-white" />
            </button>
          </div>
          <table className="mt-2 w-full text-left text-xs">
            <thead className="text-gray-500">
              <tr>
                <th className="py-1 pr-3 font-normal">Signal</th>
                <th className="py-1 pr-3 font-normal">Value at time</th>
                <th className="py-1 font-normal">Transitions in window</th>
              </tr>
            </thead>
            <tbody className="font-mono text-gray-300">
              {Object.entries(context.signals)
                .filter(([name]) => selected.length === 0 || selected.includes(name))
                .map(([name, data]) => (
                  <tr key={name} className="border-t border-gray-800">
                    <td className="py-1 pr-3">{name}</td>
                    <td className="py-1 pr-3">{valueLabel(data.value_at_failure, 32)}</td>
                    <td className="py-1">{data.total_transitions_in_window}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default WaveformViewer;