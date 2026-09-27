// Phase 12 — History / Lineage Page for GeoVertex Technical 3D Identifiers
// DISCLAIMER: GeoVertex Technical 3D Identifiers are NOT official ULPINs or legal ownership identifiers.

import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  History,
  AlertTriangle,
  RefreshCw,
  ArrowLeft,
  ArrowRight,
  ShieldAlert,
  GitBranch,
} from 'lucide-react';
import { fetchIdentifierHistory, fetchIdentifierLineage } from '../api/identifier';
import type { IdentifierStatus } from '../types/identifier';

function StatusBadge({ status }: { status: IdentifierStatus }) {
  const map: Record<IdentifierStatus, string> = {
    ACTIVE:     'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    SUPERSEDED: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    RETIRED:    'bg-slate-700/60 text-slate-400 border-slate-600/40',
    REVOKED:    'bg-red-500/10 text-red-400 border-red-500/20',
    DRAFT:      'bg-blue-500/10 text-blue-400 border-blue-500/20',
    SUSPENDED:  'bg-orange-500/10 text-orange-400 border-orange-500/20',
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${map[status] ?? 'bg-slate-800 text-slate-300 border-slate-700'}`}>
      {status}
    </span>
  );
}

export const IdentifierHistoryPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const {
    data: history,
    isLoading: histLoading,
    isError: histError,
    error: histErr,
  } = useQuery({
    queryKey: ['identifier-history', id],
    queryFn: () => fetchIdentifierHistory(id!),
    enabled: !!id,
  });

  const {
    data: lineage,
    isLoading: lineageLoading,
  } = useQuery({
    queryKey: ['identifier-lineage', id],
    queryFn: () => fetchIdentifierLineage(id!),
    enabled: !!id,
  });

  const isLoading = histLoading || lineageLoading;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 text-slate-100">
      {/* Back */}
      <Link
        to={`/identifiers/${id}`}
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-teal-400 transition"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Identifier Detail
      </Link>

      {/* Header */}
      <div className="flex items-center gap-2">
        <History className="w-7 h-7 text-teal-400" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Identifier History</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            All versions and lineage for this entity's GeoVertex Technical 3D Identifier
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

      {isLoading && (
        <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-teal-500" />
          <span>Loading identifier history…</span>
        </div>
      )}

      {histError && (
        <div className="p-8 text-center text-red-400">
          <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
          <p>{(histErr as Error)?.message || 'Failed to load history'}</p>
        </div>
      )}

      {/* Timeline */}
      {history && history.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Version Timeline</h2>
          <div className="relative pl-5 space-y-0">
            {history.map((item, idx) => (
              <div key={item.id} className="relative flex gap-4 pb-6 last:pb-0">
                {/* Timeline line */}
                {idx < history.length - 1 && (
                  <div className="absolute left-0 top-6 bottom-0 w-0.5 bg-slate-700" />
                )}
                {/* Dot */}
                <div
                  className={`relative z-10 w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 -ml-1 ${
                    item.status === 'ACTIVE'
                      ? 'bg-emerald-400 shadow-lg shadow-emerald-500/30'
                      : item.status === 'SUPERSEDED'
                      ? 'bg-yellow-400'
                      : item.status === 'REVOKED'
                      ? 'bg-red-400'
                      : 'bg-slate-500'
                  }`}
                />
                {/* Content */}
                <div className="flex-1 bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <Link
                      to={`/identifiers/${item.id}`}
                      className="font-mono text-teal-300 text-sm hover:underline break-all"
                    >
                      {item.identifier_value}
                    </Link>
                    <StatusBadge status={item.status} />
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                    <span>Version {item.version}</span>
                    <span>•</span>
                    <span>{item.entity_type}</span>
                    {item.issued_at && (
                      <>
                        <span>•</span>
                        <span>Issued {new Date(item.issued_at).toLocaleString()}</span>
                      </>
                    )}
                    {item.issued_by && (
                      <>
                        <span>•</span>
                        <span>By: {item.issued_by}</span>
                      </>
                    )}
                  </div>
                  {/* Supersession arrows */}
                  {item.superseded_by_identifier_id && (
                    <div className="flex items-center gap-1.5 text-xs text-yellow-400/70 pt-1">
                      <ArrowRight className="w-3 h-3" />
                      <span>Superseded by </span>
                      <Link
                        to={`/identifiers/${item.superseded_by_identifier_id}`}
                        className="font-mono hover:underline"
                      >
                        {item.superseded_by_identifier_id.slice(0, 12)}…
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {history && history.length === 0 && !histLoading && (
        <div className="p-8 text-center text-slate-500">
          <History className="w-12 h-12 mx-auto text-slate-600 mb-2 stroke-[1.5]" />
          <p>No history found for this identifier.</p>
        </div>
      )}

      {/* Lineage */}
      {lineage && lineage.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <GitBranch className="w-4 h-4 text-teal-400" />
            <h2 className="text-sm font-semibold text-slate-300">Related Lineage Records</h2>
          </div>
          <div className="space-y-2">
            {lineage.map((rec) => (
              <div
                key={rec.id}
                className="flex flex-wrap items-center gap-3 px-3 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs"
              >
                <span className="px-2 py-0.5 bg-slate-800 border border-slate-700 rounded font-mono text-slate-300">
                  {rec.relationship_type}
                </span>
                <Link
                  to={`/identifiers/${rec.source_identifier_id}`}
                  className="font-mono text-teal-400 hover:underline"
                >
                  {rec.source_identifier_id.slice(0, 10)}…
                </Link>
                <ArrowRight className="w-3 h-3 text-slate-500" />
                <Link
                  to={`/identifiers/${rec.target_identifier_id}`}
                  className="font-mono text-teal-400 hover:underline"
                >
                  {rec.target_identifier_id.slice(0, 10)}…
                </Link>
                {rec.reason && (
                  <span className="text-slate-500 italic ml-auto">"{rec.reason}"</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
