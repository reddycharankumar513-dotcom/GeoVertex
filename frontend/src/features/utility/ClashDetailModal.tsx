import React, { useState } from 'react';
import { UtilityClash, ClashStatus } from '../../types/utility';
import { utilityApi } from '../../api/utility';
import { useAuth } from '../../auth/AuthContext';

interface ClashDetailModalProps {
  clash: UtilityClash | null;
  isOpen: boolean;
  onClose: () => void;
  onClashUpdated: () => void;
}

export const ClashDetailModal: React.FC<ClashDetailModalProps> = ({
  clash,
  isOpen,
  onClose,
  onClashUpdated,
}) => {
  const { user } = useAuth();
  const [resolutionStatus, setResolutionStatus] = useState<ClashStatus>('ACKNOWLEDGED');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !clash) return null;

  const handleReview = async (status: ClashStatus) => {
    setLoading(true);
    setError(null);
    try {
      await utilityApi.reviewClash(clash.id, {
        status,
        resolution_notes: notes.trim() || undefined,
      });
      onClashUpdated();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update clash status');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-rose-950/80 text-rose-300 border-rose-700';
      case 'MAJOR':
        return 'bg-amber-950/80 text-amber-300 border-amber-700';
      case 'MODERATE':
        return 'bg-yellow-950/80 text-yellow-300 border-yellow-700';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'DETECTED':
        return 'bg-rose-900/40 text-rose-300 border-rose-800';
      case 'ACKNOWLEDGED':
        return 'bg-amber-900/40 text-amber-300 border-amber-800';
      case 'RESOLVED':
        return 'bg-emerald-900/40 text-emerald-300 border-emerald-800';
      case 'WAIVED':
        return 'bg-purple-900/40 text-purple-300 border-purple-800';
      case 'FALSE_POSITIVE':
        return 'bg-slate-800 text-slate-400 border-slate-700';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-xl">⚠️</span>
            <div>
              <h2 className="text-base font-semibold text-white">Subsurface 3D Clash Inspection</h2>
              <p className="text-xs text-slate-400 font-mono">Clash ID: {clash.id}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition">
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs">
          {error && (
            <div className="p-3 rounded bg-rose-950/60 border border-rose-800 text-rose-300">
              {error}
            </div>
          )}

          {/* Status and Severity Badges */}
          <div className="flex flex-wrap gap-2 items-center">
            <span
              className={`px-2.5 py-1 rounded text-[11px] font-semibold border ${getSeverityBadge(
                clash.severity
              )}`}
            >
              Severity: {clash.severity}
            </span>
            <span
              className={`px-2.5 py-1 rounded text-[11px] font-semibold border ${getStatusBadge(
                clash.status
              )}`}
            >
              Status: {clash.status}
            </span>
            <span className="px-2.5 py-1 rounded text-[11px] bg-slate-800 text-slate-300 border border-slate-700 font-mono">
              Type: {clash.clash_type}
            </span>
          </div>

          {/* Clash Details */}
          <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-4 space-y-3">
            <h3 className="text-slate-200 font-semibold text-xs border-b border-slate-700/60 pb-1">
              3D Separation & Clearances
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-slate-400 block text-[11px]">Actual 3D Clearance</span>
                <span className="text-white font-mono font-medium text-sm">
                  {clash.clearance_distance_m !== undefined && clash.clearance_distance_m !== null
                    ? `${clash.clearance_distance_m.toFixed(3)} m`
                    : clash.distance_m !== undefined && clash.distance_m !== null
                    ? `${clash.distance_m.toFixed(3)} m`
                    : clash.measured_horizontal_separation_m !== undefined
                    ? `${clash.measured_horizontal_separation_m.toFixed(3)} m`
                    : 'Direct Physical Intersection (0.00 m)'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Required Standard Clearance</span>
                <span className="text-white font-mono font-medium text-sm">
                  {clash.required_clearance_m !== undefined && clash.required_clearance_m !== null
                    ? `${clash.required_clearance_m.toFixed(3)} m`
                    : clash.required_horizontal_separation_m !== undefined
                    ? `${clash.required_horizontal_separation_m.toFixed(3)} m`
                    : 'Rule Dependent'}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-slate-400 block text-[11px]">Separation Rule Code</span>
                <span className="text-sky-300 font-mono text-xs">
                  {clash.rule_code || 'SEPARATION_RULE_NOT_CONFIGURED (Physical Intersection / Standard)'}
                </span>
              </div>
            </div>
          </div>

          {/* Intersecting Assets */}
          <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-4 space-y-2">
            <h3 className="text-slate-200 font-semibold text-xs border-b border-slate-700/60 pb-1">
              Conflict Assets
            </h3>
            <div className="space-y-2 font-mono text-[11px]">
              <div className="flex justify-between items-center bg-slate-900/60 p-2 rounded">
                <span className="text-slate-400">Primary Asset:</span>
                <span className="text-sky-400">{clash.asset_1_id || clash.asset_a_id}</span>
              </div>
              <div className="flex justify-between items-center bg-slate-900/60 p-2 rounded">
                <span className="text-slate-400">Secondary Asset:</span>
                <span className="text-amber-400">{clash.asset_2_id || clash.asset_b_id}</span>
              </div>
            </div>
          </div>

          {/* Historical Resolution */}
          {clash.resolution_notes && (
            <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3 space-y-1">
              <span className="text-slate-400 font-medium block text-[11px]">Existing Notes:</span>
              <p className="text-slate-300 italic">{clash.resolution_notes}</p>
              {(clash.reviewed_by || clash.resolved_by) && (
                <p className="text-[10px] text-slate-500">
                  Reviewed by: {clash.reviewed_by || clash.resolved_by} at{' '}
                  {new Date(clash.reviewed_at || clash.resolved_at || '').toLocaleString()}
                </p>
              )}
            </div>
          )}

          {/* Review Actions */}
          <div className="space-y-3 pt-2">
            <label className="block text-slate-300 font-medium">Resolution Notes / Justification</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Provide engineering justification, separation mitigation or survey verification details..."
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />

            <div className="flex flex-wrap gap-2 pt-2">
              <button
                type="button"
                disabled={loading}
                onClick={() => handleReview('ACKNOWLEDGED')}
                className="px-3 py-1.5 bg-amber-600/80 hover:bg-amber-600 disabled:opacity-50 text-white rounded font-medium transition flex items-center space-x-1"
              >
                <span>⚠️ Acknowledge</span>
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => handleReview('RESOLVED')}
                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded font-medium transition flex items-center space-x-1"
              >
                <span>✓ Resolve Clash</span>
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => handleReview('WAIVED')}
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded font-medium transition flex items-center space-x-1"
              >
                <span>Waive (Engineering Exemption)</span>
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => handleReview('FALSE_POSITIVE')}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
              >
                False Positive
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 text-slate-300 hover:bg-slate-700 rounded font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
