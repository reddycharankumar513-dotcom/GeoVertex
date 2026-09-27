import React, { useState, useEffect, useCallback } from 'react';
import { SurveySubmission } from '../../types';
import { surveyApi } from '../../api/surveys';
import {
  Scale,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Search,
  RefreshCw,
  Building2,
  MapPin,
  Calendar,
  User,
  ShieldCheck,
  Maximize2,
  Download,
  AlertCircle,
  Send,
  MessageSquare,
} from 'lucide-react';

export const OfficerReviewPage: React.FC = () => {
  const [submissions, setSubmissions] = useState<SurveySubmission[]>([]);
  const [selectedSubmission, setSelectedSubmission] = useState<SurveySubmission | null>(null);
  const [submissionDetail, setSubmissionDetail] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('SUBMITTED');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [isProcessingAction, setIsProcessingAction] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchSubmissions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = activeTab === 'ALL' ? {} : { status: activeTab };
      const res = await surveyApi.getSubmissions({ ...params, size: 50 });
      setSubmissions(res.items);
      if (res.items.length > 0 && !selectedSubmission) {
        setSelectedSubmission(res.items[0]);
      } else if (res.items.length === 0) {
        setSelectedSubmission(null);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch survey submissions');
    } finally {
      setIsLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchSubmissions();
  }, [fetchSubmissions]);

  // Load detailed submission snapshot and validation info when selection changes
  useEffect(() => {
    if (!selectedSubmission) {
      setSubmissionDetail(null);
      return;
    }

    const loadDetail = async () => {
      setIsLoadingDetail(true);
      try {
        const fullSub = await surveyApi.getSubmission(selectedSubmission.id);
        setSubmissionDetail(fullSub);
        setReviewNotes(fullSub.review_notes || '');
      } catch (err) {
        console.warn('Failed to load full submission details:', err);
      } finally {
        setIsLoadingDetail(false);
      }
    };

    loadDetail();
  }, [selectedSubmission]);

  const handleReviewAction = async (action: 'approve' | 'request-revision' | 'reject') => {
    if (!selectedSubmission) return;

    if ((action === 'request-revision' || action === 'reject') && !reviewNotes.trim()) {
      setError(`Please provide reviewer notes explaining why this survey is being ${action === 'request-revision' ? 'returned for revision' : 'rejected'}.`);
      return;
    }

    setIsProcessingAction(true);
    setError(null);
    setActionSuccess(null);

    try {
      const updated = await surveyApi.reviewSubmission(selectedSubmission.id, action, reviewNotes.trim());
      setActionSuccess(`Survey submission successfully marked as ${updated.status}.`);
      await fetchSubmissions();
      setSelectedSubmission(updated);
    } catch (err: any) {
      setError(err?.message || `Failed to ${action} survey submission`);
    } finally {
      setIsProcessingAction(false);
    }
  };

  const snapshot = submissionDetail?.snapshot_data
    ? typeof submissionDetail.snapshot_data === 'string'
      ? JSON.parse(submissionDetail.snapshot_data)
      : submissionDetail.snapshot_data
    : null;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-xl">
              <Scale className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                Cadastral Survey Review Console
              </h1>
              <p className="text-xs text-slate-400">
                Official Municipal Review, Quality Adjudication, & Cadastral Discrepancy Verification
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={fetchSubmissions}
              disabled={isLoading}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh Queue</span>
            </button>
          </div>
        </div>

        {actionSuccess && (
          <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-300 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
        )}
        {error && (
          <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Submissions Queue (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          {/* Tabs */}
          <div className="flex items-center space-x-1 overflow-x-auto pb-1">
            {[
              { id: 'SUBMITTED', label: 'Pending Review' },
              { id: 'APPROVED', label: 'Approved' },
              { id: 'REVISION_REQUIRED', label: 'Revisions' },
              { id: 'ALL', label: 'All' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap cursor-pointer ${
                  activeTab === tab.id
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Submissions List */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-lg divide-y divide-slate-800">
            {isLoading ? (
              <div className="p-8 text-center text-xs text-slate-500">Loading submissions...</div>
            ) : submissions.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                No submissions found for selected filter.
              </div>
            ) : (
              submissions.map((sub) => {
                const isSelected = selectedSubmission?.id === sub.id;
                return (
                  <div
                    key={sub.id}
                    onClick={() => setSelectedSubmission(sub)}
                    className={`p-4 cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-indigo-950/40 border-l-4 border-indigo-500 text-white'
                        : 'hover:bg-slate-800/40 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        v{sub.version_number}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                          sub.status === 'APPROVED'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : sub.status === 'REVISION_REQUIRED'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-sky-500/20 text-sky-300'
                        }`}
                      >
                        {sub.status.replace('_', ' ')}
                      </span>
                    </div>

                    <div className="text-xs font-semibold text-slate-200 line-clamp-1">
                      Assignment: {sub.assignment_id.slice(0, 12)}...
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 font-mono">
                      <span>Submitted: {new Date(sub.submitted_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Detailed Review & Cadastre Comparison (8 cols) */}
        <div className="lg:col-span-8 space-y-5">
          {!selectedSubmission ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-16 text-center text-slate-500">
              Select a survey submission from the queue to view evidence and adjudicate.
            </div>
          ) : (
            <>
              {/* Submission Header Card */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-md">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-indigo-400 font-mono">
                        SUBMISSION v{selectedSubmission.version_number}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                          selectedSubmission.status === 'APPROVED'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : selectedSubmission.status === 'REVISION_REQUIRED'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-sky-500/20 text-sky-300'
                        }`}
                      >
                        {selectedSubmission.status.replace('_', ' ')}
                      </span>
                    </div>
                    <h2 className="text-sm font-semibold text-white mt-1">
                      Assignment ID: {selectedSubmission.assignment_id}
                    </h2>
                    <p className="text-xs text-slate-400">
                      Submitted on {new Date(selectedSubmission.submitted_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={() => surveyApi.exportAssignment(selectedSubmission.assignment_id)}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Export Snapshot</span>
                    </button>
                  </div>
                </div>

                {/* Evidence Snapshot Statistics */}
                {snapshot && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 text-xs font-mono">
                    <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                      <span className="text-slate-500 block text-[10px]">Observations</span>
                      <span className="text-sm font-bold text-sky-400">
                        {snapshot.observations?.length || 0}
                      </span>
                    </div>
                    <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                      <span className="text-slate-500 block text-[10px]">Photo Evidence</span>
                      <span className="text-sm font-bold text-emerald-400">
                        {snapshot.evidence?.length || 0}
                      </span>
                    </div>
                    <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                      <span className="text-slate-500 block text-[10px]">Validation Status</span>
                      <span className="text-sm font-bold text-slate-200">
                        {snapshot.validation_summary?.is_valid ? 'PASSED' : 'CHECK'}
                      </span>
                    </div>
                    <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
                      <span className="text-slate-500 block text-[10px]">Version</span>
                      <span className="text-sm font-bold text-indigo-400">
                        v{snapshot.version_number || selectedSubmission.version_number}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Cadastral Comparison Table (Official Record vs Field Observations) */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-md">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                  <div className="flex items-center space-x-2">
                    <Scale className="w-4 h-4 text-indigo-400" />
                    <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                      Official Cadastre vs Field Survey Observations
                    </h3>
                  </div>
                  <span className="text-[10px] text-slate-500">
                    Immutable evidence snapshot
                  </span>
                </div>

                {snapshot?.validation_summary?.comparisons &&
                snapshot.validation_summary.comparisons.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse font-mono">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                          <th className="py-2 pr-3">Attribute</th>
                          <th className="py-2 px-3">Official Record</th>
                          <th className="py-2 px-3">Field Measurement</th>
                          <th className="py-2 px-3">Difference</th>
                          <th className="py-2 pl-3">Adjudication</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-[11px]">
                        {snapshot.validation_summary.comparisons.map((c: any, i: number) => (
                          <tr key={i} className="hover:bg-slate-800/30">
                            <td className="py-2.5 pr-3 text-slate-200 font-sans font-medium">
                              {c.property}
                            </td>
                            <td className="py-2.5 px-3 text-slate-400">{c.official_value}</td>
                            <td className="py-2.5 px-3 text-sky-300 font-bold">
                              {c.survey_value}
                            </td>
                            <td className="py-2.5 px-3 text-slate-400">{c.difference}</td>
                            <td className="py-2.5 pl-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  c.status === 'MATCH'
                                    ? 'bg-emerald-500/15 text-emerald-400'
                                    : 'bg-amber-500/15 text-amber-400'
                                }`}
                              >
                                {c.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  /* Fallback display from raw observations */
                  <div className="space-y-2">
                    {snapshot?.observations?.map((obs: any) => (
                      <div
                        key={obs.id}
                        className="p-3 bg-slate-950/50 rounded-lg border border-slate-800/80 flex items-center justify-between text-xs"
                      >
                        <div>
                          <div className="font-semibold text-white">
                            {obs.observation_type.replace(/_/g, ' ')}
                          </div>
                          <div className="text-slate-400 text-[11px]">
                            Target: {obs.target_type} ({obs.target_id.slice(0, 8)})
                          </div>
                          {obs.notes && (
                            <div className="text-slate-300 italic text-[11px] mt-1">
                              "{obs.notes}"
                            </div>
                          )}
                        </div>
                        <div className="text-right font-mono">
                          <span className="text-sm font-bold text-sky-400">
                            {obs.value} {obs.unit || ''}
                          </span>
                          {obs.latitude && obs.longitude && (
                            <div className="text-[10px] text-slate-500 mt-0.5">
                              {obs.latitude.toFixed(4)}, {obs.longitude.toFixed(4)}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Photo Evidence Records */}
              {snapshot?.evidence && snapshot.evidence.length > 0 && (
                <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-md">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                    <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                      Attached Field Evidence ({snapshot.evidence.length})
                    </h3>
                    <span className="text-[11px] text-emerald-400 font-mono flex items-center space-x-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>SHA-256 Verified</span>
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {snapshot.evidence.map((ev: any) => (
                      <div
                        key={ev.id}
                        className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden flex flex-col"
                      >
                        <div className="aspect-video bg-slate-900 overflow-hidden relative">
                          <img
                            src={surveyApi.getEvidenceFileUrl(ev.id)}
                            alt={ev.description || ev.filename}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = 'none';
                            }}
                          />
                        </div>
                        <div className="p-2 text-[11px] space-y-1">
                          <div className="font-semibold text-slate-200 truncate">
                            {ev.evidence_type.replace('_', ' ')}
                          </div>
                          {ev.description && (
                            <p className="text-slate-400 text-[10px] line-clamp-1">{ev.description}</p>
                          )}
                          <div className="text-[9px] font-mono text-slate-500 truncate" title={ev.sha256_hash}>
                            Hash: {ev.sha256_hash}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Adjudication Controls & Review Notes */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-md space-y-4">
                <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
                  <MessageSquare className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                    Cadastral Adjudication & Official Decision
                  </h3>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Official Reviewer Notes / Revision Instructions
                  </label>
                  <textarea
                    rows={3}
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="Enter review findings, justification for approval, or specific instructions for revision..."
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => handleReviewAction('reject')}
                    disabled={isProcessingAction}
                    className="px-4 py-2 bg-rose-600/10 hover:bg-rose-600/20 border border-rose-500/30 text-rose-300 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4" />
                    <span>Reject Survey</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleReviewAction('request-revision')}
                    disabled={isProcessingAction}
                    className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer disabled:opacity-50 shadow-lg shadow-amber-600/20"
                  >
                    <AlertTriangle className="w-4 h-4" />
                    <span>Request Revision</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleReviewAction('approve')}
                    disabled={isProcessingAction}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer disabled:opacity-50 shadow-lg shadow-emerald-600/20"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Approve Survey</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
