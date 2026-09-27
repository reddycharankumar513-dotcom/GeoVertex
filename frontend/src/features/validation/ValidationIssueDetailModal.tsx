import React, { useState } from 'react';
import { ValidationIssue } from '../../types/validation';
import { validationApi } from '../../api/validation';
import { ValidationMapViewer } from './ValidationMapViewer';

interface ValidationIssueDetailModalProps {
  issue: ValidationIssue | null;
  isOpen: boolean;
  onClose: () => void;
  onIssueUpdated: (updated: ValidationIssue) => void;
  userRole?: string;
}

export const ValidationIssueDetailModal: React.FC<ValidationIssueDetailModalProps> = ({
  issue,
  isOpen,
  onClose,
  onIssueUpdated,
  userRole = 'GOVERNMENT_OFFICER',
}) => {
  const [actionType, setActionType] = useState<'NONE' | 'ACKNOWLEDGE' | 'RESOLVE' | 'WAIVE'>('NONE');
  const [noteOrReason, setNoteOrReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen || !issue) return null;

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-950 text-rose-300 border border-rose-800">CRITICAL</span>;
      case 'ERROR':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-red-950 text-red-300 border border-red-800">ERROR</span>;
      case 'WARNING':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">WARNING</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-950 text-blue-300 border border-blue-800">INFO</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'OPEN':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">OPEN</span>;
      case 'ACKNOWLEDGED':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">ACKNOWLEDGED</span>;
      case 'RESOLVED':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">RESOLVED</span>;
      case 'WAIVED':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/30">WAIVED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs text-slate-400">{status}</span>;
    }
  };

  const handleActionSubmit = async () => {
    if (actionType === 'NONE') return;

    if (actionType === 'RESOLVE' && !noteOrReason.trim()) {
      setErrorMessage('Please provide a resolution note detailing the technical resolution.');
      return;
    }

    if (actionType === 'WAIVE' && !noteOrReason.trim()) {
      setErrorMessage('Please provide a cadastral waiver justification.');
      return;
    }

    try {
      setSubmitting(true);
      setErrorMessage(null);
      const payload: any = { action: actionType };
      if (actionType === 'RESOLVE') payload.note = noteOrReason.trim();
      if (actionType === 'WAIVE') payload.reason = noteOrReason.trim();

      const updated = await validationApi.reviewIssue(issue.id, payload);
      onIssueUpdated(updated);
      setActionType('NONE');
      setNoteOrReason('');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to submit review action');
    } finally {
      setSubmitting(false);
    }
  };

  const canResolveOrWaive = ['ADMIN', 'GOVERNMENT_OFFICER'].includes(userRole);
  const canAcknowledge = ['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR'].includes(userRole);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center space-x-3">
            <span className="font-mono text-sm px-2.5 py-1 bg-slate-800 text-sky-400 rounded border border-slate-700">
              {issue.issue_code}
            </span>
            <h2 className="text-lg font-semibold text-white">{issue.rule_id}</h2>
            {getSeverityBadge(issue.severity)}
            {getStatusBadge(issue.status)}
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6 text-sm text-slate-300">
          {/* Summary Box */}
          <div className="p-4 bg-slate-800/60 rounded-lg border border-slate-700/80 space-y-2">
            <div className="font-medium text-white text-base">{issue.message}</div>
            <div className="text-slate-400 leading-relaxed font-mono text-xs bg-slate-950/60 p-3 rounded border border-slate-800">
              {issue.technical_explanation}
            </div>
          </div>

          {/* Quantitative Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg">
              <span className="text-xs text-slate-400 uppercase font-semibold">Observed / Measured</span>
              <div className="text-lg font-mono font-medium text-rose-400 mt-1">
                {issue.measured_value || 'N/A'}
              </div>
            </div>
            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg">
              <span className="text-xs text-slate-400 uppercase font-semibold">Expected Cadastral Value</span>
              <div className="text-lg font-mono font-medium text-emerald-400 mt-1">
                {issue.expected_value || 'Valid Boundary'}
              </div>
            </div>
            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg">
              <span className="text-xs text-slate-400 uppercase font-semibold">Applied Tolerance</span>
              <div className="text-lg font-mono font-medium text-amber-400 mt-1">
                {issue.tolerance || 'Exact Threshold'}
              </div>
            </div>
          </div>

          {/* Spatial Vector Preview */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold uppercase tracking-wider text-slate-300">Spatial Topology Inspection</span>
              <span>Entity: <strong className="text-slate-200">{issue.entity_type} ({issue.entity_id.slice(0, 8)}...)</strong></span>
            </div>
            <ValidationMapViewer
              issue={issue}
              entityWkt={issue.geometry_wkt}
              height="280px"
            />
          </div>

          {/* Repair Candidate (if available) */}
          {issue.metadata_json?.has_repair_candidate && (
            <div className="p-3 bg-sky-950/30 border border-sky-800/60 rounded-lg space-y-1">
              <div className="flex items-center space-x-2 text-sky-400 font-medium text-xs">
                <span>🔧 GEOS Geometry Repair Candidate Available</span>
              </div>
              <p className="text-xs text-slate-400">
                A non-destructive topological repair candidate was synthesized using GEOS structure polygonization. Authorized officers can apply this during cadastral remediation.
              </p>
            </div>
          )}

          {/* Resolution History Banner if Resolved or Waived */}
          {issue.status === 'RESOLVED' && (
            <div className="p-4 bg-emerald-950/40 border border-emerald-800/80 rounded-lg space-y-1 text-xs">
              <div className="text-emerald-300 font-semibold flex items-center space-x-2">
                <span>✓ Issue Resolved</span>
                {issue.resolved_at && <span className="text-slate-400">at {new Date(issue.resolved_at).toLocaleString()}</span>}
              </div>
              <div className="text-slate-300 italic">Resolution Note: "{issue.resolution_note || 'Resolved'}"</div>
            </div>
          )}

          {issue.status === 'WAIVED' && (
            <div className="p-4 bg-purple-950/40 border border-purple-800/80 rounded-lg space-y-1 text-xs">
              <div className="text-purple-300 font-semibold flex items-center space-x-2">
                <span>⚖️ Issue Waived with Justification</span>
                {issue.waived_at && <span className="text-slate-400">at {new Date(issue.waived_at).toLocaleString()}</span>}
              </div>
              <div className="text-slate-300 italic">Waiver Reason: "{issue.waiver_reason || 'Waived'}"</div>
            </div>
          )}

          {/* Human Review Action Panel */}
          {issue.status !== 'RESOLVED' && issue.status !== 'WAIVED' && (
            <div className="p-4 bg-slate-800/80 rounded-lg border border-slate-700 space-y-4">
              <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Human-in-the-Loop Issue Review
              </div>

              {errorMessage && (
                <div className="p-2.5 rounded bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
                  {errorMessage}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2">
                {issue.status === 'OPEN' && canAcknowledge && (
                  <button
                    type="button"
                    onClick={() => setActionType('ACKNOWLEDGE')}
                    className={`px-3 py-1.5 rounded text-xs font-medium border transition ${
                      actionType === 'ACKNOWLEDGE'
                        ? 'bg-blue-600 border-blue-500 text-white'
                        : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    Acknowledge Issue
                  </button>
                )}

                {canResolveOrWaive && (
                  <>
                    <button
                      type="button"
                      onClick={() => setActionType('RESOLVE')}
                      className={`px-3 py-1.5 rounded text-xs font-medium border transition ${
                        actionType === 'RESOLVE'
                          ? 'bg-emerald-600 border-emerald-500 text-white'
                          : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      Resolve Issue...
                    </button>

                    <button
                      type="button"
                      onClick={() => setActionType('WAIVE')}
                      className={`px-3 py-1.5 rounded text-xs font-medium border transition ${
                        actionType === 'WAIVE'
                          ? 'bg-purple-600 border-purple-500 text-white'
                          : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      Waive Issue...
                    </button>
                  </>
                )}
              </div>

              {/* Input for Resolve Note / Waiver Reason */}
              {actionType === 'RESOLVE' && (
                <div className="space-y-2 pt-2 border-t border-slate-700">
                  <label className="block text-xs font-medium text-slate-300">
                    Resolution Note (Required)
                  </label>
                  <textarea
                    rows={2}
                    value={noteOrReason}
                    onChange={(e) => setNoteOrReason(e.target.value)}
                    placeholder="Describe how the topology defect or geometry discrepancy was corrected..."
                    className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                  <div className="flex justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => setActionType('NONE')}
                      className="px-3 py-1 rounded text-xs text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={handleActionSubmit}
                      className="px-4 py-1.5 rounded text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-500 transition disabled:opacity-50"
                    >
                      {submitting ? 'Resolving...' : 'Confirm Resolution'}
                    </button>
                  </div>
                </div>
              )}

              {actionType === 'WAIVE' && (
                <div className="space-y-2 pt-2 border-t border-slate-700">
                  <label className="block text-xs font-medium text-slate-300">
                    Cadastral Waiver Justification (Required)
                  </label>
                  <textarea
                    rows={2}
                    value={noteOrReason}
                    onChange={(e) => setNoteOrReason(e.target.value)}
                    placeholder="Provide statutory or survey justification for waiving this technical finding (e.g. historical easement, cantilever exception)..."
                    className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-white focus:outline-none focus:border-purple-500"
                  />
                  <div className="flex justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => setActionType('NONE')}
                      className="px-3 py-1 rounded text-xs text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={handleActionSubmit}
                      className="px-4 py-1.5 rounded text-xs font-medium bg-purple-600 text-white hover:bg-purple-500 transition disabled:opacity-50"
                    >
                      {submitting ? 'Waiving...' : 'Confirm Waiver'}
                    </button>
                  </div>
                </div>
              )}

              {actionType === 'ACKNOWLEDGE' && (
                <div className="flex justify-end space-x-2 pt-2 border-t border-slate-700">
                  <button
                    type="button"
                    onClick={() => setActionType('NONE')}
                    className="px-3 py-1 rounded text-xs text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={handleActionSubmit}
                    className="px-4 py-1.5 rounded text-xs font-medium bg-blue-600 text-white hover:bg-blue-500 transition disabled:opacity-50"
                  >
                    {submitting ? 'Acknowledging...' : 'Confirm Acknowledgement'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between text-xs text-slate-400">
          <div>Run ID: <span className="font-mono text-slate-300">{issue.validation_run_id}</span></div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
