'use client';

import { useState, useEffect } from 'react';
import { 
  GitBranch, 
  FileText, 
  ShieldCheck, 
  TestTube,
  PlayCircle,
  AlertTriangle,
  BarChart,
  Search,
  Filter,
  ChevronRight,
  ChevronDown,
  Download,
  Link2,
  Database,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { specApi } from '@/lib/api';

const defaultSpec = `# Verification Requirements

## REQ-001
FIFO shall not accept writes when full.

## REQ-002
FIFO shall not allow reads when empty.

## REQ-003
FIFO pointers shall increment correctly.
`;

/**
 * Requirements returned by POST /api/v1/spec/analyze have the shape
 * { id, category, title, description, priority, source }.
 *
 * There is no backend endpoint that persists requirement -> artifact links
 * (plans, assertions, tests, simulations, failures, coverage), so those link
 * collections are always empty here and render as UNKNOWN. They are never
 * populated with invented identifiers.
 */
interface TraceabilityRequirement {
  id: string;
  category: string;
  title: string;
  description: string;
  priority: string;
  source: string;
  verification_plans: string[];
  assertions: string[];
  tests: string[];
  simulations: string[];
  failures: string[];
  coverage: string[];
}

function normalizeRequirement(raw: any): TraceabilityRequirement {
  return {
    id: raw?.id ?? "UNKNOWN",
    category: raw?.category ?? "UNKNOWN",
    title: raw?.title ?? "UNKNOWN",
    description: raw?.description ?? raw?.title ?? "UNKNOWN",
    priority: raw?.priority ?? "UNKNOWN",
    source: raw?.source ?? "UNKNOWN",
    verification_plans: [],
    assertions: [],
    tests: [],
    simulations: [],
    failures: [],
    coverage: [],
  };
}

const artifactIcons = {
  verification_plans: FileText,
  assertions: ShieldCheck,
  tests: TestTube,
  simulations: PlayCircle,
  failures: AlertTriangle,
  coverage: BarChart,
};

export default function TraceabilityPage() {
  const [specText, setSpecText] = useState(defaultSpec);
  const [requirements, setRequirements] = useState<TraceabilityRequirement[]>([]);
  const [filter, setFilter] = useState('');
  const [selectedReq, setSelectedReq] = useState<any>(null);
  const [viewMode, setViewMode] = useState<'table' | 'matrix'>('table');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analyzedFilename, setAnalyzedFilename] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!specText.trim()) {
      setError('No specification text to analyze');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await specApi.analyze(specText, 'requirements.md', 'markdown');
      const list: any[] = Array.isArray(result?.requirements) ? result.requirements : [];
      setRequirements(list.map(normalizeRequirement));
      setAnalyzedFilename(result?.filename ?? 'requirements.md');
      setSelectedReq(null);
    } catch (err: any) {
      setError(err?.message ?? 'Spec analysis failed');
      setRequirements([]);
      setAnalyzedFilename(null);
    } finally {
      setLoading(false);
    }
  };

  const filteredReqs = requirements.filter(req =>
    (req.id ?? '').toLowerCase().includes(filter.toLowerCase()) ||
    (req.title ?? '').toLowerCase().includes(filter.toLowerCase()) ||
    (req.description ?? '').toLowerCase().includes(filter.toLowerCase())
  );

  const getStatus = (req: TraceabilityRequirement) => {
    // No persisted requirement -> artifact links exist in the backend, so
    // every link column is reported as unrecorded rather than assumed.
    return {
      hasPlan: req.verification_plans.length > 0,
      hasAssertions: req.assertions.length > 0,
      hasTests: req.tests.length > 0,
      hasSims: req.simulations.length > 0,
      hasCoverage: req.coverage.length > 0,
    };
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">Traceability Matrix</h1>
            <div className="flex items-center gap-2">
              <Download className="w-4 h-4 text-muted-foreground hover:text-foreground cursor-pointer" />
              <Link2 className="w-4 h-4 text-muted-foreground hover:text-foreground cursor-pointer" />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="mb-6 border border-border rounded-lg bg-card/50 p-4">
          <label className="block text-sm font-medium mb-2" htmlFor="spec-input">
            Specification document
          </label>
          <textarea
            id="spec-input"
            value={specText}
            onChange={(e) => setSpecText(e.target.value)}
            rows={6}
            className="w-full px-3 py-2 bg-secondary border border-border rounded-lg font-mono text-sm"
            placeholder="Paste requirements here (markdown or plain text)..."
          />
          <div className="flex items-center gap-3 mt-3">
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
            >
              {loading ? 'Analyzing...' : 'Analyze specification'}
            </button>
            {analyzedFilename && (
              <span className="text-sm text-muted-foreground">
                Parsed {requirements.length} requirement(s) from {analyzedFilename}
              </span>
            )}
            {error && <span className="text-sm text-red-500">{error}</span>}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            [UNKNOWN] Requirement to artifact links (plans, assertions, tests, simulations,
            coverage) are not persisted by the backend, so those columns stay UNKNOWN until a
            traceability persistence layer exists. Nothing here is inferred or generated.
          </p>
        </div>

        {requirements.length === 0 ? (
          <div className="border border-border rounded-lg bg-card/50 p-8 text-center">
            <Database className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
            <h2 className="text-lg font-semibold mb-1">No requirements recorded</h2>
            <p className="text-sm text-muted-foreground">
              Analyze a specification above to load real requirements. No sample data is displayed.
            </p>
          </div>
        ) : (
          <>
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Filter requirements..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-sm w-64"
            />
            <div className="flex items-center gap-1 border border-border rounded-lg">
              <button
                onClick={() => setViewMode('table')}
                className={cn('px-3 py-1.5 text-sm rounded-l', viewMode === 'table' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
              >
                Table
              </button>
              <button
                onClick={() => setViewMode('matrix')}
                className={cn('px-3 py-1.5 text-sm rounded-r', viewMode === 'matrix' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground')}
              >
                Matrix
              </button>
            </div>
          </div>
        </div>

        {viewMode === 'table' ? (
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Requirement</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Description</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Plan</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Assertions</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Tests</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Simulations</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Coverage</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Status</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {filteredReqs.map((req) => {
                    const status = getStatus(req);
                    const complete = status.hasPlan && status.hasAssertions && status.hasTests && status.hasSims && status.hasCoverage;
                    return (
                      <tr key={req.id} className="hover:bg-secondary/50 cursor-pointer" onClick={() => setSelectedReq(req)}>
                        <td className="px-4 py-3 font-mono text-sm font-medium">{req.id}</td>
                        <td className="px-4 py-3 text-sm max-w-xs truncate">{req.description}</td>
                        <td className="px-4 py-3">
                          <span className={cn('px-2 py-0.5 text-xs rounded', status.hasPlan ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400')}>
                            {req.verification_plans.length}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn('px-2 py-0.5 text-xs rounded', status.hasAssertions ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400')}>
                            {req.assertions.length}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn('px-2 py-0.5 text-xs rounded', status.hasTests ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400')}>
                            {req.tests.length}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn('px-2 py-0.5 text-xs rounded', status.hasSims ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400')}>
                            {req.simulations.length}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn('px-2 py-0.5 text-xs rounded', status.hasCoverage ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400')}>
                            {req.coverage.length}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={cn('px-2 py-0.5 text-xs rounded font-medium', complete ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400')}>
                            {complete ? 'Complete' : 'Partial'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <ChevronRight className="w-4 h-4 text-muted-foreground" />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-max">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground sticky left-0 bg-card z-10 w-48">
                      Artifact Type
                    </th>
                    {filteredReqs.map((req) => (
                      <th key={req.id} className="px-4 py-3 text-center text-xs font-medium text-muted-foreground w-36">
                        {req.id}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(artifactIcons).map(([type, Icon]) => (
                    <tr key={type} className="border-b border-border/50">
                      <td className="px-4 py-3 sticky left-0 bg-card z-10">
                        <div className="flex items-center gap-2">
                          <Icon className="w-4 h-4 text-primary" />
                          <span className="font-medium capitalize">{type.replace('_', ' ')}</span>
                        </div>
                      </td>
                      {filteredReqs.map((req) => {
                        const items = req[type as keyof typeof req] as string[];
                        const hasItems = items.length > 0;
                        return (
                          <td key={req.id} className="px-4 py-3 text-center">
                            {hasItems ? (
                              <span className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded font-medium">
                                {items.length}
                              </span>
                            ) : (
                              // The backend does not persist requirement ->
                              // artifact links, so an empty cell means "not
                              // recorded", never "failed". Render it as an
                              // explicit UNKNOWN badge instead of a red dash.
                              <span
                                title="No persisted links to recorded artifacts (UNKNOWN)"
                                className="px-2 py-0.5 text-xs bg-amber-500/20 text-amber-300 rounded font-medium"
                              >
                                UNKNOWN
                              </span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {selectedReq && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/50" onClick={() => setSelectedReq(null)} />
            <div className="relative bg-card border border-border rounded-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto">
              <div className="border-b border-border px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <GitBranch className="w-5 h-5" />
                  <span className="font-medium">{selectedReq.id}</span>
                </div>
                <button onClick={() => setSelectedReq(null)} className="text-muted-foreground hover:text-foreground">
                  ✕
                </button>
              </div>
              <div className="p-6 space-y-6">
                <p className="text-muted-foreground">{selectedReq.description}</p>
                
                {Object.entries(selectedReq).filter(([k]) => !['id', 'title', 'description', 'category', 'priority', 'source'].includes(k)).map(([type, items]) => (
                  <div key={type} className="bg-secondary/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      {(() => {
                        const Icon = artifactIcons[type as keyof typeof artifactIcons];
                        return Icon ? <Icon className="w-4 h-4 text-primary" /> : null;
                      })()}
                      <span className="font-medium capitalize">{type.replace('_', ' ')}</span>
                      {(items as string[]).length > 0 ? (
                        <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                          {(items as string[]).length}
                        </span>
                      ) : (
                        <span
                          title="No persisted links to recorded artifacts (UNKNOWN)"
                          className="px-2 py-0.5 text-xs bg-amber-500/20 text-amber-300 rounded font-medium"
                        >
                          UNKNOWN
                        </span>
                      )}
                    </div>
                    {(items as string[]).length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {(items as string[]).map((item: string) => (
                        <span key={item} className="px-2 py-0.5 text-xs bg-secondary border border-border rounded font-mono">
                          {item}
                        </span>
                      ))}
                    </div>
                    ) : (
                      <p className="text-xs text-amber-300/90">
                        Not recorded by the backend. Absence of a link is not evidence that
                        verification did not happen.
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
          </>
        )}
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