import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  GitCompare,
  ArrowLeft,
  AlertTriangle,
  ShieldAlert,
  Layers,
  ArrowRight,
  TrendingUp,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { versionApi } from '../api/governance';
import { VersionComparison } from '../types/governance';

export const VersionComparePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const vA = searchParams.get('vA') || '';
  const vB = searchParams.get('vB') || '';

  const [comparison, setComparison] = useState<VersionComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchComparison = async () => {
    if (!vA || !vB) {
      setError('Please provide two valid version IDs (vA and vB) to compare.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await versionApi.compareVersions(vA, vB);
      setComparison(res);
    } catch (err: any) {
      setError(err.message || 'Failed to compare entity versions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComparison();
  }, [vA, vB]);

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate(-1)}
          className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-white mb-2 transition cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Timeline</span>
        </button>
        <div className="flex items-center space-x-2">
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-teal-950/60 border border-teal-800 text-teal-300">
            Version Comparison Engine
          </span>
        </div>
        <h1 className="text-2xl font-bold text-white mt-1">Side-by-Side Version Comparison</h1>
        <p className="text-sm text-slate-400">
          Deterministic attribute variance and spatial geometric delta inspection.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Cadastral / Legal Disclaimer */}
      {comparison && (
        <div className="flex items-start gap-3 p-4 bg-slate-900/80 border border-amber-500/30 rounded-2xl text-slate-300">
          <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-xs leading-relaxed">
            <span className="font-semibold text-amber-300">Legal & Cadastral Notice: </span>
            {comparison.disclaimer}
          </p>
        </div>
      )}

      {loading ? (
        <div className="py-20 text-center text-slate-500 text-sm">
          Computing attribute differences and geometric variance...
        </div>
      ) : !comparison ? null : (
        <div className="space-y-6">
          {/* Version Header Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Version A */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400 uppercase">Baseline Version</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700 font-mono">
                  {comparison.version_a.version_status}
                </span>
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                v{comparison.version_a.version_number}
              </div>
              <div className="text-xs text-slate-400 font-mono space-y-0.5">
                <div>Change Type: <span className="text-purple-300">{comparison.version_a.change_type}</span></div>
                <div>Source: <span className="text-slate-300">{comparison.version_a.source_type}</span></div>
                <div>Date: {comparison.version_a.created_at ? new Date(comparison.version_a.created_at).toLocaleString() : '—'}</div>
              </div>
            </div>

            {/* Version B */}
            <div className="bg-slate-900/60 border border-teal-500/40 rounded-2xl p-5 backdrop-blur space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-teal-400 uppercase">Target Version</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
                  {comparison.version_b.version_status}
                </span>
              </div>
              <div className="text-2xl font-bold text-teal-300 font-mono">
                v{comparison.version_b.version_number}
              </div>
              <div className="text-xs text-slate-400 font-mono space-y-0.5">
                <div>Change Type: <span className="text-purple-300">{comparison.version_b.change_type}</span></div>
                <div>Source: <span className="text-slate-300">{comparison.version_b.source_type}</span></div>
                <div>Date: {comparison.version_b.created_at ? new Date(comparison.version_b.created_at).toLocaleString() : '—'}</div>
              </div>
            </div>
          </div>

          {/* Geometric Variance Panel */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur space-y-4">
            <h2 className="text-base font-semibold text-white flex items-center space-x-2">
              <Layers className="w-4 h-4 text-teal-400" />
              <span>Spatial & Geometric Variance</span>
            </h2>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-slate-950/60 border border-slate-800 p-3.5 rounded-xl">
                <span className="text-[11px] font-mono text-slate-500 uppercase block">Area Delta</span>
                <span className="text-lg font-bold text-white font-mono block mt-1">
                  {comparison.geometry_diff.area_delta > 0 ? `+${comparison.geometry_diff.area_delta}` : comparison.geometry_diff.area_delta} sqm
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  ({comparison.geometry_diff.area_pct_change}%)
                </span>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-3.5 rounded-xl">
                <span className="text-[11px] font-mono text-slate-500 uppercase block">Perimeter Delta</span>
                <span className="text-lg font-bold text-white font-mono block mt-1">
                  {comparison.geometry_diff.perimeter_delta > 0 ? `+${comparison.geometry_diff.perimeter_delta}` : comparison.geometry_diff.perimeter_delta} m
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  Length variation
                </span>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-3.5 rounded-xl">
                <span className="text-[11px] font-mono text-slate-500 uppercase block">Centroid Shift</span>
                <span className="text-lg font-bold text-white font-mono block mt-1">
                  {comparison.geometry_diff.centroid_movement_units}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  Spatial offset
                </span>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-3.5 rounded-xl">
                <span className="text-[11px] font-mono text-slate-500 uppercase block">Geometry Hash</span>
                <span className="text-xs font-bold font-mono block mt-2">
                  {comparison.geometry_diff.geometry_changed ? (
                    <span className="text-amber-400">CHANGED</span>
                  ) : (
                    <span className="text-emerald-400">IDENTICAL</span>
                  )}
                </span>
              </div>
            </div>
          </div>

          {/* Scalar Field Differences Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur space-y-4">
            <h2 className="text-base font-semibold text-white flex items-center space-x-2">
              <GitCompare className="w-4 h-4 text-purple-400" />
              <span>Attribute Modifications ({Object.keys(comparison.modified_fields).length})</span>
            </h2>

            {Object.keys(comparison.modified_fields).length === 0 ? (
              <p className="text-xs text-slate-400 font-mono py-4 text-center">
                No scalar attributes were modified between these two versions.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="text-[11px] text-slate-500 uppercase border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Field Name</th>
                      <th className="py-2.5 px-3">Baseline (v{comparison.version_a.version_number})</th>
                      <th className="py-2.5 px-3">Target (v{comparison.version_b.version_number})</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-200">
                    {Object.entries(comparison.modified_fields).map(([fieldName, diff]: [string, any]) => (
                      <tr key={fieldName} className="hover:bg-slate-850/40">
                        <td className="py-3 px-3 font-semibold text-white">{fieldName}</td>
                        <td className="py-3 px-3 text-rose-300 bg-rose-950/20">
                          {typeof diff.before === 'object' ? JSON.stringify(diff.before) : String(diff.before)}
                        </td>
                        <td className="py-3 px-3 text-emerald-300 bg-emerald-950/20">
                          {typeof diff.after === 'object' ? JSON.stringify(diff.after) : String(diff.after)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
