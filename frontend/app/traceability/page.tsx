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
import { traceabilityApi } from '@/lib/api';

const mockTraceability = {
  requirements: [
    {
      requirement_id: 'REQ-001',
      description: 'FIFO shall not accept writes when full',
      verification_plans: ['VP-fifo_sync-FIFO-001'],
      assertions: ['fifo_sync_no_write_when_full', 'fifo_sync_no_write_when_full'],
      tests: ['tb_fifo_sync_fifo', 'tb_fifo_sync_basic'],
      simulations: ['sim_001', 'sim_002'],
      failures: [],
      coverage: ['cov_001'],
    },
    {
      requirement_id: 'REQ-002',
      description: 'FIFO shall not allow reads when empty',
      verification_plans: ['VP-fifo_sync-FIFO-001'],
      assertions: ['fifo_sync_no_read_when_empty'],
      tests: ['tb_fifo_sync_fifo'],
      simulations: ['sim_001'],
      failures: [],
      coverage: ['cov_001'],
    },
    {
      requirement_id: 'REQ-003',
      description: 'FIFO pointers shall increment correctly',
      verification_plans: ['VP-fifo_sync-FIFO-002', 'VP-fifo_sync-FIFO-003'],
      assertions: ['fifo_sync_wr_ptr_progress', 'fifo_sync_rd_ptr_progress', 'fifo_sync_count_tracking'],
      tests: ['tb_fifo_sync_fifo', 'tb_fifo_sync_basic'],
      simulations: ['sim_001', 'sim_002'],
      failures: [],
      coverage: ['cov_001', 'cov_002'],
    },
    {
      requirement_id: 'REQ-004',
      description: 'FIFO full and empty flags shall be mutually exclusive',
      verification_plans: ['VP-fifo_sync-FIFO-004'],
      assertions: ['fifo_sync_full_empty_mutex'],
      tests: ['tb_fifo_sync_fifo'],
      simulations: ['sim_001'],
      failures: [],
      coverage: ['cov_001'],
    },
    {
      requirement_id: 'REQ-005',
      description: 'Reset shall clear all registers and pointers',
      verification_plans: ['VP-fifo_sync-RST-001'],
      assertions: ['fifo_sync_reset_clears_registers'],
      tests: ['tb_fifo_sync_reset'],
      simulations: ['sim_001'],
      failures: [],
      coverage: ['cov_001'],
    },
  ],
};

const artifactIcons = {
  verification_plans: FileText,
  assertions: ShieldCheck,
  tests: TestTube,
  simulations: PlayCircle,
  failures: AlertTriangle,
  coverage: BarChart,
};

export default function TraceabilityPage() {
  const [requirements, setRequirements] = useState(mockTraceability.requirements);
  const [filter, setFilter] = useState('');
  const [selectedReq, setSelectedReq] = useState<any>(null);
  const [viewMode, setViewMode] = useState<'table' | 'matrix'>('table');

  const filteredReqs = requirements.filter(req => 
    req.requirement_id.toLowerCase().includes(filter.toLowerCase()) ||
    req.description.toLowerCase().includes(filter.toLowerCase())
  );

  const getStatus = (req: any) => {
    const hasPlan = req.verification_plans.length > 0;
    const hasAssertions = req.assertions.length > 0;
    const hasTests = req.tests.length > 0;
    const hasSims = req.simulations.length > 0;
    const hasCoverage = req.coverage.length > 0;
    return { hasPlan, hasAssertions, hasTests, hasSims, hasCoverage };
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
                      <tr key={req.requirement_id} className="hover:bg-secondary/50 cursor-pointer" onClick={() => setSelectedReq(req)}>
                        <td className="px-4 py-3 font-mono text-sm font-medium">{req.requirement_id}</td>
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
                      <th key={req.requirement_id} className="px-4 py-3 text-center text-xs font-medium text-muted-foreground w-36">
                        {req.requirement_id}
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
                          <td key={req.requirement_id} className="px-4 py-3 text-center">
                            {hasItems ? (
                              <span className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded font-medium">
                                {items.length}
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 text-xs bg-red-500/20 text-red-400 rounded">
                                —
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
                  <span className="font-medium">{selectedReq.requirement_id}</span>
                </div>
                <button onClick={() => setSelectedReq(null)} className="text-muted-foreground hover:text-foreground">
                  ✕
                </button>
              </div>
              <div className="p-6 space-y-6">
                <p className="text-muted-foreground">{selectedReq.description}</p>
                
                {Object.entries(selectedReq).filter(([k]) => k !== 'requirement_id' && k !== 'description').map(([type, items]) => (
                  <div key={type} className="bg-secondary/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <artifactIcons[type as keyof typeof artifactIcons] className="w-4 h-4 text-primary" />
                      <span className="font-medium capitalize">{type.replace('_', ' ')}</span>
                      <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                        {(items as string[]).length}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {(items as string[]).map((item: string) => (
                        <span key={item} className="px-2 py-0.5 text-xs bg-secondary border border-border rounded font-mono">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
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