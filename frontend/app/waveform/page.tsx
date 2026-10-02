'use client';

import { LayoutDashboard } from 'lucide-react';

import { WaveformViewer } from '@/components/waveform/WaveformViewer';

export default function WaveformPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex items-center gap-3">
          <LayoutDashboard className="h-6 w-6 text-blue-400" />
          <div>
            <h1 className="text-2xl font-semibold">Waveform Viewer</h1>
            <p className="text-sm text-gray-400">
              Inspect VCD dumps, review signal values around a failure time, and compare runs.
            </p>
          </div>
        </div>

        <WaveformViewer />
      </div>
    </div>
  );
}