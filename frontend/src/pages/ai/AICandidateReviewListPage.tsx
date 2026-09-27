import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  Eye,
  Filter,
  Layers,
  RefreshCw,
  ShieldCheck,
  XCircle,
  FileCheck,
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { aiApi } from '../../api/ai';
import { BuildingExtractionResult } from '../../types/ai';
import { AIReviewModal } from '../../features/ai/AIReviewModal';

export const AICandidateReviewListPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [results, setResults] = useState<BuildingExtractionResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [selectedResult, setSelectedResult] = useState<BuildingExtractionResult | null>(null);

  const fetchResults = async () => {
    setIsLoading(true);
    try {
      const res = await aiApi.listBuildingResults({
        status: statusFilter || undefined,
        size: 50,
      });
      setResults(res.items);
    } catch (err) {
      console.error('Failed to load candidate results:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, [statusFilter]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800">
            <CheckCircle2 className="w-3 h-3" /> APPROVED
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950/80 text-red-300 border border-red-800">
            <XCircle className="w-3 h-3" /> REJECTED
          </span>
        );
      case 'REVIEW_REQUIRED':
      case 'CANDIDATE':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-800 animate-pulse">
            <AlertTriangle className="w-3 h-3" /> REVIEW REQUIRED
          </span>
        );
    }
  };

  const getValidationBadge = (status: string) => {
    if (status === 'VALID') {
      return (
        <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold text-xs">
          <CheckCircle2 className="w-3.5 h-3.5" /> VALID
        </span>
      );
    }
    if (status === 'WARNING') {
      return (
        <span className="inline-flex items-center gap-1 text-amber-400 font-semibold text-xs">
          <AlertTriangle className="w-3.5 h-3.5" /> WARNING
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-red-400 font-semibold text-xs">
        <XCircle className="w-3.5 h-3.5" /> INVALID
      </span>
    );
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
            <FileCheck className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">AI Extraction Reviews</h1>
            <p className="text-sm text-slate-400">
              Human-in-the-loop review console for candidate building footprints
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={fetchResults}
          className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Results
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="flex items-center gap-3 bg-slate-900/40 p-4 rounded-2xl border border-slate-800">
        <Filter className="w-4 h-4 text-slate-400" />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-purple-400"
        >
          <option value="">All Review Statuses</option>
          <option value="REVIEW_REQUIRED">Review Required</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      {/* Results Table */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 uppercase font-semibold text-[11px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Target Feature</th>
                <th className="py-3.5 px-4">Model</th>
                <th className="py-3.5 px-4">Confidence</th>
                <th className="py-3.5 px-4">Cadastral IoU</th>
                <th className="py-3.5 px-4">Validation</th>
                <th className="py-3.5 px-4">Review Status</th>
                <th className="py-3.5 px-4 text-right">Adjudication</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading && results.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    Loading AI candidate results...
                  </td>
                </tr>
              ) : results.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No candidate results found. Enqueue an AI extraction job first.
                  </td>
                </tr>
              ) : (
                results.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4 font-mono text-[11px] text-white">
                      {r.source_target_id.substring(0, 16)}...
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px] text-purple-300">
                      {r.model_id} (v{r.model_version})
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white font-mono">
                          {Math.round(r.confidence * 100)}%
                        </span>
                        <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-purple-500 rounded-full"
                            style={{ width: `${r.confidence * 100}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-purple-300 font-semibold">
                      {r.cadastral_comparison?.iou ? r.cadastral_comparison.iou.toFixed(4) : 'N/A'}
                    </td>
                    <td className="py-3.5 px-4">{getValidationBadge(r.validation_status)}</td>
                    <td className="py-3.5 px-4">{getStatusBadge(r.status)}</td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedResult(r)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold shadow transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Inspect & Review
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedResult && (
        <AIReviewModal
          result={selectedResult}
          onClose={() => setSelectedResult(null)}
          onSuccess={() => {
            setSelectedResult(null);
            fetchResults();
          }}
        />
      )}
    </div>
  );
};
