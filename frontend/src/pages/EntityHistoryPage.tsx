import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  History,
  GitBranch,
  ArrowLeft,
  RefreshCw,
  AlertCircle,
  RotateCcw,
  CheckCircle,
  Eye,
  GitCompare,
  Layers,
  Calendar,
  User as UserIcon,
} from 'lucide-react';
import { versionApi } from '../api/governance';
import { useAuth } from '../auth/AuthContext';
import { EntityLineage, EntityVersion } from '../types/governance';

export const EntityHistoryPage: React.FC = () => {
  const { entityType = 'PARCEL', entityId = '' } = useParams<{ entityType: string; entityId: string }>();
  const navigate = useNavigate();
  const { role } = useAuth();
  const isOfficerOrAdmin = role === 'ADMIN' || role === 'GOVERNMENT_OFFICER';

  const [versions, setVersions] = useState<EntityVersion[]>([]);
  const [lineages, setLineages] = useState<EntityLineage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Compare selection
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);

  // Restoration modal
  const [restoringVersion, setRestoringVersion] = useState<EntityVersion | null>(null);
  const [restorationReason, setRestorationReason] = useState('');
  const [restoringLoading, setRestoringLoading] = useState(false);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  const fetchHistory = async () => {
    if (!entityId) return;
    setLoading(true);
    setError(null);
    try {
      const [vRes, lRes] = await Promise.all([
        versionApi.listVersions(entityType, entityId, 1, 50),
        versionApi.getLineage(entityType, entityId).catch(() => []),
      ]);
      setVersions(vRes.items);
      setLineages(lRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load entity version history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [entityType, entityId]);

  const toggleSelectForCompare = (versionId: string) => {
    if (selectedForCompare.includes(versionId)) {
      setSelectedForCompare(selectedForCompare.filter((id) => id !== versionId));
    } else {
      if (selectedForCompare.length >= 2) {
        setSelectedForCompare([selectedForCompare[1], versionId]);
      } else {
        setSelectedForCompare([...selectedForCompare, versionId]);
      }
    }
  };

  const handleLaunchCompare = () => {
    if (selectedForCompare.length === 2) {
      navigate(`/versions/compare?vA=${selectedForCompare[0]}&vB=${selectedForCompare[1]}`);
    }
  };

  const handleExecuteRestoration = async () => {
    if (!restoringVersion) return;
    if (!restorationReason || restorationReason.trim().length < 5) {
      setRestoreError('A valid justification reason of at least 5 characters is required.');
      return;
    }

    setRestoringLoading(true);
    setRestoreError(null);
    try {
      await versionApi.restoreVersion(entityType, entityId, {
        target_version_number: restoringVersion.version_number,
        reason: restorationReason.trim(),
      });
      setRestoringVersion(null);
      setRestorationReason('');
      fetchHistory();
    } catch (err: any) {
      setRestoreError(err.message || 'Restoration failed.');
    } finally {
      setRestoringLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-white mb-2 transition cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back</span>
          </button>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-teal-950/60 border border-teal-800 text-teal-300">
              {entityType} History
            </span>
            <span className="text-xs text-slate-500 font-mono">{entityId}</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">Entity Version Timeline</h1>
          <p className="text-sm text-slate-400">
            Immutable version timeline, provenance tracking, and controlled rollback.
          </p>
        </div>

        <div className="flex items-center space-x-3 self-start sm:self-auto">
          {selectedForCompare.length === 2 && (
            <button
              onClick={handleLaunchCompare}
              className="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white flex items-center space-x-2 text-xs font-semibold transition cursor-pointer shadow-lg shadow-teal-950"
            >
              <GitCompare className="w-4 h-4" />
              <span>Compare Selected (2)</span>
            </button>
          )}
          <button
            onClick={fetchHistory}
            disabled={loading}
            className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center space-x-2 text-xs font-semibold transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Compare Helper Notice */}
      <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300">
        <div className="flex items-center space-x-2">
          <GitCompare className="w-4 h-4 text-teal-400" />
          <span>
            Select any 2 versions using checkboxes to launch side-by-side scalar & geometric comparison.
          </span>
        </div>
        <span className="font-mono text-teal-400 font-semibold">
          {selectedForCompare.length}/2 Selected
        </span>
      </div>

      {/* Timeline Section */}
      <div className="space-y-4">
        {loading && versions.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm">
            Loading entity version timeline...
          </div>
        ) : versions.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm bg-slate-900/40 rounded-2xl border border-slate-800">
            No version history recorded for this entity yet.
          </div>
        ) : (
          versions.map((ver, idx) => {
            const isSelected = selectedForCompare.includes(ver.id);
            const isCurrent = ver.version_status === 'CURRENT';

            return (
              <div
                key={ver.id}
                className={`bg-slate-900/60 border rounded-2xl p-5 backdrop-blur transition ${
                  isSelected
                    ? 'border-teal-500 ring-1 ring-teal-500/50'
                    : isCurrent
                    ? 'border-emerald-500/50 shadow-lg shadow-emerald-950/20'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start space-x-3.5">
                    {/* Checkbox for compare */}
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelectForCompare(ver.id)}
                      className="mt-1 h-4 w-4 rounded border-slate-700 text-teal-600 focus:ring-teal-500 bg-slate-950 cursor-pointer"
                    />

                    <div>
                      <div className="flex items-center space-x-2.5">
                        <span className="text-base font-bold text-white font-mono">
                          v{ver.version_number}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold font-mono ${
                            isCurrent
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {ver.version_status}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] bg-purple-950/60 text-purple-300 border border-purple-800 font-mono">
                          {ver.change_type}
                        </span>
                      </div>

                      {/* Change reason */}
                      <p className="text-xs text-slate-200 mt-2 font-medium">
                        {ver.change_reason || 'No change reason specified.'}
                      </p>

                      {/* Metadata badges */}
                      <div className="flex flex-wrap items-center gap-3 mt-3 text-[11px] text-slate-400 font-mono">
                        <span className="flex items-center space-x-1">
                          <Calendar className="w-3 h-3 text-slate-500" />
                          <span>{new Date(ver.effective_from || ver.created_at).toLocaleString()}</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <UserIcon className="w-3 h-3 text-slate-500" />
                          <span>Source: {ver.source_type} {ver.source_id ? `(${ver.source_id})` : ''}</span>
                        </span>
                        {ver.geometry_metrics?.area && (
                          <span className="text-teal-300">
                            Area: {ver.geometry_metrics.area} sqm
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2 self-end sm:self-start">
                    {isOfficerOrAdmin && !isCurrent && (
                      <button
                        onClick={() => {
                          setRestoringVersion(ver);
                          setRestorationReason('');
                          setRestoreError(null);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-amber-950/60 hover:bg-amber-900 border border-amber-800 text-amber-300 text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer"
                        title="Controlled rollback: restores state into a new version"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Restore</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Scalar Attributes Summary */}
                {ver.snapshot_data && Object.keys(ver.snapshot_data).length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                    {Object.entries(ver.snapshot_data)
                      .slice(0, 4)
                      .map(([k, v]) => (
                        <div key={k} className="bg-slate-950/40 p-2 rounded-lg">
                          <span className="text-slate-500 block text-[10px] uppercase">{k}</span>
                          <span className="text-slate-300 truncate block">
                            {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                          </span>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Restoration Modal */}
      {restoringVersion && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center space-x-2.5 text-amber-400">
              <RotateCcw className="w-5 h-5" />
              <h2 className="text-base font-bold text-white">
                Controlled Rollback to Version {restoringVersion.version_number}
              </h2>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Restoration will <span className="font-semibold text-white">NEVER overwrite history</span>.
              A new version (v{versions[0]?.version_number + 1 || 'N+1'}) will be created with the snapshot data of v{restoringVersion.version_number}.
              An immutable <span className="font-mono text-amber-300">RESTORATION</span> audit event will be recorded.
            </p>

            {restoreError && (
              <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
                {restoreError}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Mandatory Justification Reason <span className="text-rose-400">*</span>
              </label>
              <textarea
                rows={3}
                placeholder="Provide authoritative rationale for rolling back to this version..."
                value={restorationReason}
                onChange={(e) => setRestorationReason(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
              />
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setRestoringVersion(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteRestoration}
                disabled={restoringLoading || !restorationReason.trim()}
                className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold transition disabled:opacity-50 cursor-pointer"
              >
                {restoringLoading ? 'Executing Restoration...' : 'Confirm & Restore'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
