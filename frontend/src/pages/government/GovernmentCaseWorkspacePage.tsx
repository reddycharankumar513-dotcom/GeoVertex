import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  Clock,
  User,
  Compass,
  FileText,
  AlertCircle,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  Send,
  MessageSquare,
  Lock,
  Layers,
  Database,
  Building,
  RefreshCw,
  Sliders,
  ExternalLink,
} from 'lucide-react';
import { workflowApi } from '../../api/workflow';
import {
  CrossPhaseCaseWorkspace,
  ServiceRequestDetail,
  CaseMessage,
  RequestStatus,
} from '../../types/workflow';
import { CommissionSurveyModal } from '../../features/workflow/CommissionSurveyModal';
import { ControlledUpdateModal } from '../../features/workflow/ControlledUpdateModal';

export const GovernmentCaseWorkspacePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [workspace, setWorkspace] = useState<CrossPhaseCaseWorkspace | null>(null);
  const [detail, setDetail] = useState<ServiceRequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tab State: GIS | DOCUMENTS | VALIDATION | UTILITIES | MESSAGES | TIMELINE
  const [activeTab, setActiveTab] = useState<
    'OVERVIEW' | 'CROSS_PHASE' | 'MESSAGES' | 'INTERNAL_NOTES' | 'TIMELINE'
  >('OVERVIEW');

  // Modals
  const [isSurveyModalOpen, setIsSurveyModalOpen] = useState(false);
  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false);

  // Decision inputs
  const [decisionReason, setDecisionReason] = useState('');
  const [isDecisionProcessing, setIsDecisionProcessing] = useState(false);

  // Messaging inputs
  const [newMsg, setNewMsg] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);
  const [internalNote, setInternalNote] = useState('');
  const [sendingNote, setSendingNote] = useState(false);

  useEffect(() => {
    if (id) {
      loadAll();
    }
  }, [id]);

  const loadAll = async () => {
    try {
      setLoading(true);
      setError(null);
      const [ws, d] = await Promise.all([
        workflowApi.getCrossPhaseWorkspace(id!),
        workflowApi.getServiceRequestDetail(id!),
      ]);
      setWorkspace(ws);
      setDetail(d);
    } catch (err: any) {
      setError(err?.message || 'Failed to load case workspace');
    } finally {
      setLoading(false);
    }
  };

  const handleTransition = async (newStatus: RequestStatus) => {
    if (['REJECTED', 'MORE_INFO_REQUESTED'].includes(newStatus) && !decisionReason.trim()) {
      alert('Mandatory reasoning is required for rejection or requesting citizen revision.');
      return;
    }

    try {
      setIsDecisionProcessing(true);
      const updated = await workflowApi.transitionServiceRequest(id!, {
        new_status: newStatus,
        reason: decisionReason.trim() || undefined,
      });
      setDetail(updated);
      setDecisionReason('');
      await loadAll();
    } catch (err: any) {
      alert(err?.message || 'Failed to update case status');
    } finally {
      setIsDecisionProcessing(false);
    }
  };

  const handlePostMessage = async (isInternal: boolean) => {
    const text = isInternal ? internalNote : newMsg;
    if (!text.trim() || !id) return;

    try {
      if (isInternal) setSendingNote(true);
      else setSendingMsg(true);

      const created = await workflowApi.postCaseMessage(id, {
        message_body: text.trim(),
        message_type: isInternal ? 'INTERNAL_NOTE' : 'PUBLIC_MESSAGE',
      });

      setDetail((prev) =>
        prev ? { ...prev, messages: [...prev.messages, created] } : prev
      );

      if (isInternal) setInternalNote('');
      else setNewMsg('');
    } catch (err: any) {
      alert(err?.message || 'Failed to post message');
    } finally {
      if (isInternal) setSendingNote(false);
      else setSendingMsg(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-gray-500">
        <div className="inline-block animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full mb-3" />
        <div>Loading integrated case workspace across cadastral GIS, AI, and survey twins...</div>
      </div>
    );
  }

  if (error || !workspace || !detail) {
    return (
      <div className="p-8 max-w-4xl mx-auto space-y-4">
        <button
          onClick={() => navigate('/government/dashboard')}
          className="flex items-center space-x-2 text-sm text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </button>
        <div className="p-6 rounded-2xl bg-red-950/40 border border-red-800 text-red-200 text-sm flex items-center space-x-3">
          <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
          <span>{error || 'Case workspace not available'}</span>
        </div>
      </div>
    );
  }

  const { service_request: req, sla } = workspace;
  const publicMessages = detail.messages.filter((m) => !m.is_internal);
  const internalNotes = detail.messages.filter((m) => m.is_internal);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Navigation & Status Bar */}
      <div className="space-y-3">
        <button
          onClick={() => navigate('/government/dashboard')}
          className="flex items-center space-x-2 text-xs text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Operations Dashboard</span>
        </button>

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 border-b border-gray-800 pb-5">
          <div>
            <div className="flex items-center space-x-3">
              <span className="font-mono text-base font-bold px-3 py-1 rounded-xl bg-purple-950/80 border border-purple-700/60 text-purple-300">
                {req.case_reference}
              </span>
              <span className="text-gray-500 font-mono text-xs">SR: {req.request_reference}</span>
              <span
                className={`px-3 py-0.5 rounded-full text-xs font-semibold border ${
                  sla.status === 'ON_TRACK'
                    ? 'text-emerald-400 bg-emerald-950/60 border-emerald-800'
                    : sla.status === 'DUE_SOON'
                    ? 'text-amber-400 bg-amber-950/60 border-amber-800'
                    : 'text-red-400 bg-red-950/60 border-red-800'
                }`}
              >
                SLA: {sla.status.replace(/_/g, ' ')} ({sla.hours_remaining}h)
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-2">{req.title}</h1>
            <p className="text-xs text-gray-400 mt-1">
              Service: <span className="text-gray-300 font-medium">{req.request_type}</span> •
              Priority: <span className="text-amber-400 font-semibold">{req.priority}</span> •
              Status: <span className="text-blue-400 font-semibold">{req.status}</span>
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setIsSurveyModalOpen(true)}
              className="px-3.5 py-2 rounded-xl bg-purple-900/40 hover:bg-purple-900/60 border border-purple-700/60 text-purple-300 text-xs font-medium transition flex items-center space-x-1.5"
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Commission Survey</span>
            </button>

            <button
              onClick={() => setIsUpdateModalOpen(true)}
              className="px-3.5 py-2 rounded-xl bg-amber-900/40 hover:bg-amber-900/60 border border-amber-700/60 text-amber-300 text-xs font-medium transition flex items-center space-x-1.5"
            >
              <Database className="w-3.5 h-3.5" />
              <span>Controlled Record Update</span>
            </button>

            <button
              onClick={loadAll}
              className="p-2 rounded-xl border border-gray-800 text-gray-400 hover:text-white hover:bg-gray-800 transition"
              title="Refresh Case"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Decision Workflow Bar */}
      <div className="p-4 rounded-2xl bg-gray-900 border border-gray-800 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
            Case Officer Decision Controls
          </span>
          <span className="text-xs text-gray-500">Authorized Officer Actions</span>
        </div>

        <div className="flex flex-col md:flex-row gap-3">
          <input
            type="text"
            value={decisionReason}
            onChange={(e) => setDecisionReason(e.target.value)}
            placeholder="Enter reason (mandatory for rejection, revisions, or escalations)..."
            className="flex-1 bg-gray-950 border border-gray-700 rounded-xl px-4 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => handleTransition('APPROVED')}
              disabled={isDecisionProcessing}
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition flex items-center space-x-1 disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Approve</span>
            </button>

            <button
              onClick={() => handleTransition('MORE_INFO_REQUESTED')}
              disabled={isDecisionProcessing}
              className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium transition flex items-center space-x-1 disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Request Revision</span>
            </button>

            <button
              onClick={() => handleTransition('REJECTED')}
              disabled={isDecisionProcessing}
              className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-medium transition flex items-center space-x-1 disabled:opacity-50"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Reject</span>
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center space-x-2 border-b border-gray-800 pb-2 text-xs">
        <button
          onClick={() => setActiveTab('OVERVIEW')}
          className={`px-3.5 py-1.5 rounded-lg font-medium transition ${
            activeTab === 'OVERVIEW'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-800'
          }`}
        >
          Case Overview
        </button>

        <button
          onClick={() => setActiveTab('CROSS_PHASE')}
          className={`px-3.5 py-1.5 rounded-lg font-medium transition flex items-center space-x-1.5 ${
            activeTab === 'CROSS_PHASE'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-800'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Cross-Phase Intelligence</span>
        </button>

        <button
          onClick={() => setActiveTab('MESSAGES')}
          className={`px-3.5 py-1.5 rounded-lg font-medium transition flex items-center space-x-1.5 ${
            activeTab === 'MESSAGES'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-800'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>Citizen Communications ({publicMessages.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('INTERNAL_NOTES')}
          className={`px-3.5 py-1.5 rounded-lg font-medium transition flex items-center space-x-1.5 ${
            activeTab === 'INTERNAL_NOTES'
              ? 'bg-amber-600 text-white'
              : 'text-amber-400 hover:text-amber-300 hover:bg-gray-800'
          }`}
        >
          <Lock className="w-3.5 h-3.5" />
          <span>Internal Officer Notes ({internalNotes.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('TIMELINE')}
          className={`px-3.5 py-1.5 rounded-lg font-medium transition ${
            activeTab === 'TIMELINE'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-800'
          }`}
        >
          Audit Timeline ({detail.events.length})
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'OVERVIEW' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 space-y-4">
              <h3 className="font-semibold text-white text-sm">Citizen Requester Description</h3>
              <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
                {req.description}
              </p>
            </div>

            {/* Cadastral Context Card */}
            <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 space-y-4">
              <h3 className="font-semibold text-white text-sm">Associated Cadastral Record</h3>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-gray-500 block">Property Reference</span>
                  <span className="text-white font-mono font-medium">
                    {workspace.property?.property_reference || req.property_id || 'Not Associated'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block">Cadastral Address</span>
                  <span className="text-white">{workspace.property?.address || '—'}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Parent Parcel</span>
                  <span className="text-white font-mono">
                    {workspace.parcel?.parcel_number || req.parcel_id || '—'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 block">Property Type / Status</span>
                  <span className="text-white">
                    {workspace.property?.property_type} / {workspace.property?.status}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {/* Workflow Tasks */}
            <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 space-y-4">
              <h3 className="font-semibold text-white text-sm">Active Review Tasks</h3>
              {detail.tasks.length === 0 ? (
                <div className="text-xs text-gray-500">No active subtasks generated.</div>
              ) : (
                <div className="space-y-2.5">
                  {detail.tasks.map((t) => (
                    <div
                      key={t.id}
                      className="p-3 rounded-xl bg-gray-950 border border-gray-800 text-xs flex items-center justify-between"
                    >
                      <div>
                        <div className="font-medium text-white">{t.title}</div>
                        <div className="text-[11px] text-gray-500">{t.task_type}</div>
                      </div>
                      <span className="px-2 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800 text-[10px]">
                        {t.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'CROSS_PHASE' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Documents */}
            <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <FileText className="w-4 h-4 text-blue-400" />
                  <span>Phase 8 Documents</span>
                </span>
                <span className="text-xs text-gray-500">{workspace.documents.length} verified</span>
              </div>
              <div className="text-xs text-gray-400 space-y-2">
                {workspace.documents.length === 0 ? (
                  <p className="text-gray-500 italic">No deeds or documents linked</p>
                ) : (
                  workspace.documents.map((d, i) => (
                    <div key={i} className="p-2.5 rounded-xl bg-gray-950 border border-gray-800">
                      <div className="font-medium text-white">{d.document_type || 'Deed'}</div>
                      <div className="text-[11px] text-gray-500">Ref: {d.document_number || d.id}</div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Surveys */}
            <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <Compass className="w-4 h-4 text-purple-400" />
                  <span>Phase 5 Field Surveys</span>
                </span>
                <span className="text-xs text-gray-500">{workspace.surveys.length} projects</span>
              </div>
              <div className="text-xs text-gray-400 space-y-2">
                {workspace.surveys.length === 0 ? (
                  <p className="text-gray-500 italic">No field surveys commissioned yet</p>
                ) : (
                  workspace.surveys.map((s, i) => (
                    <div key={i} className="p-2.5 rounded-xl bg-gray-950 border border-gray-800">
                      <div className="font-medium text-white">{s.name}</div>
                      <div className="text-[11px] text-gray-500">{s.status}</div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Topology Issues */}
            <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span>Phase 7 Topology Issues</span>
                </span>
                <span className="text-xs text-amber-400 font-semibold">
                  {workspace.topology_issues.length} detected
                </span>
              </div>
              <div className="text-xs text-gray-400 space-y-2">
                {workspace.topology_issues.length === 0 ? (
                  <p className="text-emerald-400">Zero topology violations on this parcel</p>
                ) : (
                  workspace.topology_issues.map((t, i) => (
                    <div key={i} className="p-2.5 rounded-xl bg-amber-950/20 border border-amber-800/40">
                      <div className="font-medium text-amber-200">{t.rule_code}</div>
                      <div className="text-[11px] text-gray-400">{t.description}</div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Temporal Changes */}
            <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <Clock className="w-4 h-4 text-emerald-400" />
                  <span>Phase 9 Change Candidates</span>
                </span>
                <span className="text-xs text-gray-500">{workspace.change_candidates.length} candidates</span>
              </div>
              <div className="text-xs text-gray-400 space-y-2">
                {workspace.change_candidates.length === 0 ? (
                  <p className="text-gray-500 italic">No pending temporal change detections</p>
                ) : (
                  workspace.change_candidates.map((c, i) => (
                    <div key={i} className="p-2.5 rounded-xl bg-gray-950 border border-gray-800">
                      <div className="font-medium text-white">{c.change_type}</div>
                      <div className="text-[11px] text-gray-500">Confidence: {c.confidence_score}</div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Subsurface Utilities */}
            <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <Database className="w-4 h-4 text-cyan-400" />
                  <span>Phase 10 Utility Clashes</span>
                </span>
                <span className="text-xs text-cyan-400">{workspace.utility_clashes.length} clashes</span>
              </div>
              <div className="text-xs text-gray-400 space-y-2">
                {workspace.utility_clashes.length === 0 ? (
                  <p className="text-emerald-400">Zero subsurface utility encroachments</p>
                ) : (
                  workspace.utility_clashes.map((u, i) => (
                    <div key={i} className="p-2.5 rounded-xl bg-cyan-950/20 border border-cyan-800/40">
                      <div className="font-medium text-cyan-200">{u.severity} Severity Clash</div>
                      <div className="text-[11px] text-gray-400">{u.description}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'MESSAGES' && (
        <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 flex flex-col h-[560px]">
          <div className="border-b border-gray-800 pb-3 mb-4">
            <h3 className="font-semibold text-white text-sm">Public Citizen Channel</h3>
            <p className="text-[11px] text-gray-400">
              Messages posted here are visible to the citizen requester in their Citizen Portal.
            </p>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
            {publicMessages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500">
                No public messages in this case yet.
              </div>
            ) : (
              publicMessages.map((m) => (
                <div
                  key={m.id}
                  className={`p-3.5 rounded-xl max-w-[85%] space-y-1 ${
                    m.sender_role === 'GOVERNMENT_OFFICER' || m.sender_role === 'ADMIN'
                      ? 'ml-auto bg-purple-950/60 border border-purple-800/60 text-purple-100'
                      : 'mr-auto bg-gray-800 border border-gray-700 text-gray-200'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] text-gray-400">
                    <span className="font-semibold">{m.sender_role}</span>
                    <span>{new Date(m.created_at).toLocaleString()}</span>
                  </div>
                  <p className="text-xs whitespace-pre-wrap">{m.message_body}</p>
                </div>
              ))
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handlePostMessage(false);
            }}
            className="mt-4 pt-3 border-t border-gray-800 flex items-center space-x-2"
          >
            <input
              type="text"
              value={newMsg}
              onChange={(e) => setNewMsg(e.target.value)}
              placeholder="Send message to citizen..."
              className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-3.5 py-2 text-white text-xs placeholder-gray-500 focus:outline-none focus:border-purple-500"
            />
            <button
              type="submit"
              disabled={sendingMsg || !newMsg.trim()}
              className="p-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white transition disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}

      {activeTab === 'INTERNAL_NOTES' && (
        <div className="p-6 rounded-2xl bg-amber-950/20 border border-amber-900/60 flex flex-col h-[560px]">
          <div className="border-b border-amber-900/40 pb-3 mb-4 flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-2 text-amber-300 font-semibold text-sm">
                <Lock className="w-4 h-4" />
                <span>Internal Officer Notes</span>
              </div>
              <p className="text-[11px] text-amber-200/70 mt-0.5">
                CONFIDENTIAL: These notes are strictly protected by ABAC and are never exposed to citizens.
              </p>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
            {internalNotes.length === 0 ? (
              <div className="h-full flex items-center justify-center text-amber-200/50">
                No internal officer notes logged yet.
              </div>
            ) : (
              internalNotes.map((m) => (
                <div
                  key={m.id}
                  className="p-3.5 rounded-xl bg-gray-900/90 border border-amber-800/50 text-gray-200 space-y-1"
                >
                  <div className="flex items-center justify-between text-[10px] text-amber-400/80">
                    <span className="font-semibold">{m.sender_role} (Confidential Note)</span>
                    <span>{new Date(m.created_at).toLocaleString()}</span>
                  </div>
                  <p className="text-xs whitespace-pre-wrap">{m.message_body}</p>
                </div>
              ))
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handlePostMessage(true);
            }}
            className="mt-4 pt-3 border-t border-amber-900/40 flex items-center space-x-2"
          >
            <input
              type="text"
              value={internalNote}
              onChange={(e) => setInternalNote(e.target.value)}
              placeholder="Record confidential review finding or surveyor instructions..."
              className="flex-1 bg-gray-900 border border-amber-700/60 rounded-xl px-3.5 py-2 text-white text-xs placeholder-gray-500 focus:outline-none focus:border-amber-400"
            />
            <button
              type="submit"
              disabled={sendingNote || !internalNote.trim()}
              className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium transition disabled:opacity-50 flex items-center space-x-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Log Note</span>
            </button>
          </form>
        </div>
      )}

      {activeTab === 'TIMELINE' && (
        <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 space-y-5">
          <div className="flex items-center justify-between border-b border-gray-800 pb-3">
            <h3 className="font-semibold text-white text-sm">Full Officer & System Event Audit Trail</h3>
            <span className="text-xs text-gray-500">{detail.events.length} audit entries</span>
          </div>

          <div className="space-y-6 relative pl-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-800">
            {detail.events.map((ev) => (
              <div key={ev.id} className="relative space-y-1">
                <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-purple-500 border-2 border-gray-900 ring-2 ring-gray-900" />
                <div className="flex items-center space-x-2 text-xs">
                  <span className="font-semibold text-white">
                    {ev.new_status.replace(/_/g, ' ')}
                  </span>
                  <span className="text-gray-500">•</span>
                  <span className="text-purple-300 font-mono text-[11px]">{ev.event_type}</span>
                  <span className="text-gray-500">•</span>
                  <span className="text-gray-400 capitalize">{ev.actor_role.toLowerCase()}</span>
                  <span className="text-gray-500">•</span>
                  <span className="text-gray-500">{new Date(ev.created_at).toLocaleString()}</span>
                </div>
                {ev.reason && (
                  <p className="text-xs text-amber-300/90 font-medium">Reason: {ev.reason}</p>
                )}
                {ev.comment && <p className="text-xs text-gray-400 italic">"{ev.comment}"</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modals */}
      <CommissionSurveyModal
        requestId={req.id}
        requestReference={req.case_reference}
        isOpen={isSurveyModalOpen}
        onClose={() => setIsSurveyModalOpen(false)}
        onCommissioned={() => loadAll()}
      />

      <ControlledUpdateModal
        requestId={req.id}
        property={workspace.property}
        isOpen={isUpdateModalOpen}
        onClose={() => setIsUpdateModalOpen(false)}
        onUpdated={() => loadAll()}
      />
    </div>
  );
};
