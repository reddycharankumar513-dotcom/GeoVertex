import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  EyeOff,
  History,
  ShieldAlert,
  Layers,
  MapPin,
  FileText,
  Clock,
  ExternalLink,
} from 'lucide-react';
import { ChangeCandidate, ChangeCandidateReviewPayload, ReviewReason } from '../../types/temporal';

interface ChangeDetailModalProps {
  candidate: ChangeCandidate | null;
  isOpen: boolean;
  onClose: () => void;
  onReviewSubmit: (candidateId: string, payload: ChangeCandidateReviewPayload) => Promise<void>;
}

export const ChangeDetailModal: React.FC<ChangeDetailModalProps> = ({
  candidate,
  isOpen,
  onClose,
  onReviewSubmit,
}) => {
  if (!isOpen || !candidate) return null;

  const [action, setAction] = useState<'CONFIRM' | 'REJECT' | 'DISMISS'>('CONFIRM');
  const [reviewReason, setReviewReason] = useState<ReviewReason>('CONFIRMED_FIELD_SURVEY');
  const [reviewNotes, setReviewNotes] = useState(candidate.review_notes || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await onReviewSubmit(candidate.id, {
        action,
        review_reason: reviewReason,
        review_notes: reviewNotes.trim() || undefined,
      });
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to submit candidate review');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getSignificanceColor = (sig: string) => {
    switch (sig) {
      case 'MAJOR':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'MODERATE':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'MINOR':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const mag = candidate.magnitude || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl max-w-3xl w-full overflow-hidden text-slate-100 my-8 animate-in fade-in zoom-in duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center gap-3">
            <History className="w-5 h-5 text-indigo-400" />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-lg">{candidate.change_type}</h3>
                <span
                  className={`px-2 py-0.5 rounded text-[11px] font-bold border ${getSignificanceColor(
                    candidate.significance
                  )}`}
                >
                  {candidate.significance}
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                  {candidate.status}
                </span>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                Entity: {candidate.entity_type} {candidate.entity_id ? `(${candidate.entity_id})` : ''}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Temporal Baseline vs Comparison Banner */}
          <div className="grid grid-cols-2 gap-4 bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-xs">
            <div>
              <span className="text-slate-500 font-medium block">Baseline Reference</span>
              <span className="font-mono text-slate-200 font-semibold mt-0.5 block">
                {candidate.baseline_snapshot_id || 'Historical Snapshot'}
              </span>
              <span className="text-slate-400 text-[11px] mt-0.5 block flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-500" />{' '}
                {candidate.baseline_date
                  ? new Date(candidate.baseline_date).toLocaleDateString()
                  : 'Historical Date'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 font-medium block">Comparison Reference</span>
              <span className="font-mono text-indigo-300 font-semibold mt-0.5 block">
                {candidate.comparison_snapshot_id || 'Current Live Record'}
              </span>
              <span className="text-slate-400 text-[11px] mt-0.5 block flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-500" />{' '}
                {candidate.comparison_date
                  ? new Date(candidate.comparison_date).toLocaleDateString()
                  : 'Current Date'}
              </span>
            </div>
          </div>

          {/* Standardized Change Magnitude Metrics */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              Calculated Magnitude & Spatial Metrics
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
              {mag.area_difference_sqm !== undefined && (
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[11px] block">Area Delta</span>
                  <span
                    className={`font-mono font-bold text-sm block mt-0.5 ${
                      mag.area_difference_sqm > 0
                        ? 'text-emerald-400'
                        : mag.area_difference_sqm < 0
                        ? 'text-red-400'
                        : 'text-slate-200'
                    }`}
                  >
                    {mag.area_difference_sqm > 0 ? `+${mag.area_difference_sqm}` : mag.area_difference_sqm} m²
                  </span>
                  {mag.area_change_percentage !== undefined && (
                    <span className="text-[10px] text-slate-400 font-mono">
                      {mag.area_change_percentage > 0 ? `+${mag.area_change_percentage}` : mag.area_change_percentage}%
                    </span>
                  )}
                </div>
              )}

              {mag.iou !== undefined && (
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[11px] block">Spatial IoU</span>
                  <span className="font-mono font-bold text-sm text-indigo-300 block mt-0.5">
                    {Math.round(mag.iou * 100)}%
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">Overlap Ratio</span>
                </div>
              )}

              {mag.boundary_displacement_m !== undefined && (
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[11px] block">Boundary Shift</span>
                  <span className="font-mono font-bold text-sm text-cyan-300 block mt-0.5">
                    {mag.boundary_displacement_m} m
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">Hausdorff metric</span>
                </div>
              )}

              {mag.height_difference_m !== undefined && (
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[11px] block">Height Delta</span>
                  <span className="font-mono font-bold text-sm text-amber-300 block mt-0.5">
                    {mag.height_difference_m > 0 ? `+${mag.height_difference_m}` : mag.height_difference_m} m
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {mag.old_value}m → {mag.new_value}m
                  </span>
                </div>
              )}

              {mag.floor_count_difference !== undefined && (
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[11px] block">Floor Count Delta</span>
                  <span className="font-mono font-bold text-sm text-purple-300 block mt-0.5">
                    {mag.floor_count_difference > 0 ? `+${mag.floor_count_difference}` : mag.floor_count_difference}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {mag.baseline_floor_count} → {mag.comparison_floor_count}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Temporal Evidence & Provenance */}
          {candidate.evidence && candidate.evidence.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                Temporal Evidence & Cross-Dataset Provenance
              </h4>
              <div className="space-y-2">
                {candidate.evidence.map((ev, i) => (
                  <div
                    key={i}
                    className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-indigo-300 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-indigo-400" />
                        {ev.source_type}
                      </span>
                      {ev.source_id && (
                        <span className="font-mono text-slate-500 text-[11px]">ID: {ev.source_id.substring(0, 8)}...</span>
                      )}
                    </div>
                    <p className="text-slate-300">{ev.description}</p>
                    {ev.date && <span className="text-[10px] text-slate-500 block">Date: {ev.date}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Phase 7 Spatial Topology Validation Findings */}
          {candidate.validation_issues && candidate.validation_issues.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-red-400 mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" /> Phase 7 Spatial Topology Findings
              </h4>
              <div className="space-y-1.5">
                {candidate.validation_issues.map((iss, i) => (
                  <div
                    key={i}
                    className="p-2.5 bg-red-950/20 border border-red-900/40 rounded-lg text-xs space-y-0.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-red-300">{iss.issue_code}</span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 uppercase">
                        {iss.severity}
                      </span>
                    </div>
                    <p className="text-slate-300 text-[11px]">{iss.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Governance Notice */}
          <div className="p-3 bg-slate-950 border border-amber-500/30 rounded-lg text-xs text-slate-300 flex items-start gap-2.5">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-amber-300">Mandatory Cadastral Governance:</span> Candidate
              changes reflect physical or record variations detected across temporal layers. Human cadastral
              officers determine whether changes are authorized, require field survey, or represent data alignment errors.
            </div>
          </div>

          {/* Human Review Decision Bar */}
          <div className="space-y-3 pt-2 border-t border-slate-800">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Cadastral Review Action
            </h4>

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => {
                  setAction('CONFIRM');
                  setReviewReason('CONFIRMED_FIELD_SURVEY');
                }}
                className={`flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border text-xs font-semibold transition ${
                  action === 'CONFIRM'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 ring-1 ring-emerald-500/40'
                    : 'bg-slate-800/40 text-slate-400 border-slate-700/60 hover:bg-slate-800'
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Confirm Change
              </button>
              <button
                type="button"
                onClick={() => {
                  setAction('REJECT');
                  setReviewReason('FALSE_POSITIVE');
                }}
                className={`flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border text-xs font-semibold transition ${
                  action === 'REJECT'
                    ? 'bg-red-500/20 text-red-300 border-red-500/50 ring-1 ring-red-500/40'
                    : 'bg-slate-800/40 text-slate-400 border-slate-700/60 hover:bg-slate-800'
                }`}
              >
                <XCircle className="w-3.5 h-3.5" /> Reject
              </button>
              <button
                type="button"
                onClick={() => {
                  setAction('DISMISS');
                  setReviewReason('TEMPORARY_STRUCTURE');
                }}
                className={`flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border text-xs font-semibold transition ${
                  action === 'DISMISS'
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 ring-1 ring-amber-500/40'
                    : 'bg-slate-800/40 text-slate-400 border-slate-700/60 hover:bg-slate-800'
                }`}
              >
                <EyeOff className="w-3.5 h-3.5" /> Dismiss
              </button>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Review Reason / Technical Justification <span className="text-red-400">*</span>
              </label>
              <select
                value={reviewReason}
                onChange={(e) => setReviewReason(e.target.value as ReviewReason)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="CONFIRMED_FIELD_SURVEY">Confirmed Against Field Survey</option>
                <option value="CONFIRMED_PERMIT_APPROVED">Confirmed via Approved Building Permit</option>
                <option value="FALSE_POSITIVE">False Positive / Image Artifact</option>
                <option value="TEMPORARY_STRUCTURE">Temporary Structure / Non-Permanent</option>
                <option value="DATA_ALIGNMENT_ERROR">Data / Imagery Alignment Error</option>
                <option value="SURVEY_CORRECTION">Correction of Prior Survey Error</option>
                <option value="DUPLICATE_DETECTION">Duplicate Detection Run</option>
                <option value="INSUFFICIENT_EVIDENCE">Insufficient Evidence</option>
                <option value="OTHER">Other Technical Justification</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Officer Audit Notes
              </label>
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                rows={2}
                placeholder="Enter justification for confirmation, rejection, or field re-survey requirement..."
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs text-slate-400 hover:text-slate-200 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition shadow-lg shadow-indigo-600/20"
            >
              {isSubmitting ? 'Saving Review...' : `Submit Decision (${action})`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
