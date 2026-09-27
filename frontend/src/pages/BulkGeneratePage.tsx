// Phase 12 — Bulk Generate Identifiers Page (Officer/Admin Only)
// DISCLAIMER: GeoVertex Technical 3D Identifiers are NOT official ULPINs or legal ownership identifiers.

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  Hash,
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  ShieldAlert,
  Layers,
  AlertOctagon,
} from 'lucide-react';
import { bulkPreview, bulkGenerate } from '../api/identifier';
import type { BulkPreview } from '../types/identifier';

export const BulkGeneratePage: React.FC = () => {
  const [buildingId, setBuildingId] = useState('');
  const [preview, setPreview] = useState<BulkPreview | null>(null);
  const [result, setResult] = useState<{
    job_id: string;
    status: string;
    total: number;
    generated: number;
  } | null>(null);

  const previewMutation = useMutation({
    mutationFn: () =>
      bulkPreview({
        entity_type: 'UNIT',
        building_id: buildingId.trim(),
      }),
    onSuccess: (data) => {
      setPreview(data);
      setResult(null);
    },
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      bulkGenerate({
        entity_type: 'UNIT',
        building_id: buildingId.trim(),
        confirmed: true,
      }),
    onSuccess: (data) => {
      setResult(data);
    },
  });

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 text-slate-100">
      {/* Back */}
      <Link
        to="/identifiers"
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-teal-400 transition"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Registry
      </Link>

      {/* Header */}
      <div className="flex items-center gap-2">
        <Layers className="w-7 h-7 text-teal-400" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Bulk Generate Identifiers</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Generate GeoVertex Technical 3D Identifiers for all units in a building
          </p>
        </div>
      </div>

      {/* WARNING banner */}
      <div className="flex items-start gap-3 p-4 bg-red-950/40 border border-red-500/40 rounded-xl">
        <AlertOctagon className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-sm font-bold text-red-300">
            ⚠ Bulk generation is irreversible. Review preview carefully.
          </p>
          <p className="text-xs text-red-400/80 leading-relaxed">
            Once generated, GeoVertex Technical 3D Identifiers are permanently recorded. They can be
            retired or revoked but NOT deleted. Ensure you have selected the correct building and verified
            the preview before confirming.
          </p>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="flex items-start gap-3 p-4 bg-slate-900 border border-amber-500/30 rounded-xl text-slate-300">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-xs leading-relaxed">
          <span className="font-semibold text-amber-300">Disclaimer: </span>
          GeoVertex Technical 3D Identifiers — NOT official ULPINs or legal ownership identifiers.
        </p>
      </div>

      {/* Input */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-200">Building UUID</h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={buildingId}
            onChange={(e) => { setBuildingId(e.target.value); setPreview(null); setResult(null); }}
            placeholder="Paste Building UUID…"
            className="flex-1 px-3 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 font-mono focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
          <button
            onClick={() => previewMutation.mutate()}
            disabled={!buildingId.trim() || previewMutation.isPending}
            className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-500 disabled:opacity-40 text-white rounded-lg text-sm font-medium transition"
          >
            {previewMutation.isPending ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Hash className="w-4 h-4" />
            )}
            {previewMutation.isPending ? 'Loading…' : 'Preview'}
          </button>
        </div>

        {previewMutation.isError && (
          <div className="flex items-center gap-2 p-3 bg-red-950/40 border border-red-500/30 rounded-lg text-red-400 text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {(previewMutation.error as Error).message}
          </div>
        )}
      </div>

      {/* Preview results */}
      {preview && !result && (
        <div className="space-y-4">
          {/* Summary stats */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {(
              [
                { label: 'Total Units', value: preview.total, color: 'text-white' },
                { label: 'Eligible', value: preview.eligible, color: 'text-emerald-400' },
                { label: 'Already Assigned', value: preview.already_assigned, color: 'text-blue-400' },
                { label: 'Blocked', value: preview.blocked, color: 'text-red-400' },
                { label: 'Collisions', value: preview.collisions, color: 'text-orange-400' },
                { label: 'Ready', value: preview.ready_to_generate, color: 'text-teal-400' },
              ] as const
            ).map(({ label, value, color }) => (
              <div key={label} className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
                <span className="text-slate-500 text-xs font-medium block">{label}</span>
                <span className={`text-xl font-bold mt-1 block ${color}`}>{value}</span>
              </div>
            ))}
          </div>

          {/* Unit preview table */}
          {preview.previews.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-800">
                <h3 className="text-sm font-semibold text-slate-300">
                  Unit Preview (showing up to {preview.previews.length})
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Unit ID</th>
                      <th className="py-3 px-4">Unit Code</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Preview Identifier</th>
                      <th className="py-3 px-4">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {preview.previews.map((u) => (
                      <tr key={u.unit_id} className="hover:bg-slate-800/30 transition">
                        <td className="py-2.5 px-4 font-mono text-slate-400">
                          {u.unit_id.slice(0, 12)}…
                        </td>
                        <td className="py-2.5 px-4 font-mono">{u.unit_code}</td>
                        <td className="py-2.5 px-4">
                          {u.already_assigned ? (
                            <span className="text-blue-400">Already Assigned</span>
                          ) : u.eligible ? (
                            <span className="text-emerald-400">Eligible</span>
                          ) : (
                            <span className="text-red-400">Blocked</span>
                          )}
                        </td>
                        <td className="py-2.5 px-4 font-mono text-teal-300">
                          {u.preview_identifier ?? '—'}
                        </td>
                        <td className="py-2.5 px-4 text-slate-500">
                          {u.errors.length > 0 ? u.errors.join(', ') : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Confirm & Generate */}
          {preview.ready_to_generate > 0 && (
            <div className="bg-slate-900 border border-red-500/30 rounded-2xl p-5 space-y-3">
              <p className="text-sm text-red-300 font-medium">
                ⚠ About to generate{' '}
                <strong>{preview.ready_to_generate} identifiers</strong> — this action is
                irreversible.
              </p>
              {generateMutation.isError && (
                <div className="flex items-center gap-2 p-3 bg-red-950/40 border border-red-500/30 rounded-lg text-red-400 text-sm">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  {(generateMutation.error as Error).message}
                </div>
              )}
              <button
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-700 hover:bg-red-600 disabled:opacity-40 text-white rounded-lg text-sm font-bold transition"
              >
                {generateMutation.isPending ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : null}
                {generateMutation.isPending
                  ? 'Generating…'
                  : `Confirm & Generate All (${preview.ready_to_generate})`}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="bg-slate-900 border border-emerald-500/30 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
            <h2 className="text-lg font-bold">Bulk Generation Submitted</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {(
              [
                { label: 'Job ID', value: result.job_id.slice(0, 12) + '…', color: 'text-slate-300' },
                { label: 'Status', value: result.status, color: 'text-emerald-400' },
                { label: 'Total', value: String(result.total), color: 'text-white' },
                { label: 'Generated', value: String(result.generated), color: 'text-teal-400' },
              ] as const
            ).map(({ label, value, color }) => (
              <div key={label} className="bg-slate-950 border border-slate-800 rounded-xl p-3">
                <span className="text-slate-500 text-xs block">{label}</span>
                <span className={`font-mono text-sm font-bold mt-1 block ${color}`}>{value}</span>
              </div>
            ))}
          </div>
          <Link
            to="/identifiers"
            className="inline-flex items-center gap-2 text-sm text-teal-400 hover:underline"
          >
            View Identifier Registry →
          </Link>
        </div>
      )}
    </div>
  );
};
