import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  Send,
  MessageSquare,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Calendar,
  Compass,
  FileText,
  User,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { workflowApi } from '../../api/workflow';
import { ServiceRequestDetail, CaseMessage } from '../../types/workflow';

export const CitizenRequestDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [detail, setDetail] = useState<ServiceRequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Message input state
  const [newMsg, setNewMsg] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);

  // Revision state
  const [revisionComment, setRevisionComment] = useState('');
  const [submittingRevision, setSubmittingRevision] = useState(false);

  useEffect(() => {
    if (id) {
      loadDetail();
    }
  }, [id]);

  const loadDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await workflowApi.getServiceRequestDetail(id!);
      setDetail(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load request tracking details');
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMsg.trim() || !id) return;

    try {
      setSendingMsg(true);
      const msg = await workflowApi.postCaseMessage(id, {
        message_body: newMsg.trim(),
        message_type: 'PUBLIC_MESSAGE',
      });
      setDetail((prev) =>
        prev ? { ...prev, messages: [...prev.messages, msg] } : prev
      );
      setNewMsg('');
    } catch (err: any) {
      setError(err?.message || 'Failed to send message');
    } finally {
      setSendingMsg(false);
    }
  };

  const handleSubmitRevision = async () => {
    if (!revisionComment.trim() || !id) return;
    try {
      setSubmittingRevision(true);
      const updated = await workflowApi.transitionServiceRequest(id, {
        new_status: 'UNDER_REVIEW',
        comment: revisionComment.trim(),
      });
      setDetail(updated);
      setRevisionComment('');
    } catch (err: any) {
      setError(err?.message || 'Failed to submit revision');
    } finally {
      setSubmittingRevision(false);
    }
  };

  const handleCancelRequest = async () => {
    if (!window.confirm('Are you sure you want to cancel this request?')) return;
    try {
      const updated = await workflowApi.transitionServiceRequest(id!, {
        new_status: 'CANCELLED',
        reason: 'Cancelled by citizen requester',
      });
      setDetail(updated);
    } catch (err: any) {
      setError(err?.message || 'Failed to cancel request');
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-gray-500">
        <div className="inline-block animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mb-3" />
        <div>Loading request details and audit timeline...</div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="p-8 max-w-4xl mx-auto space-y-4">
        <button
          onClick={() => navigate('/citizen/dashboard')}
          className="flex items-center space-x-2 text-sm text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </button>
        <div className="p-6 rounded-2xl bg-red-950/40 border border-red-800 text-red-200 text-sm flex items-center space-x-3">
          <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
          <span>{error || 'Request not found'}</span>
        </div>
      </div>
    );
  }

  const { request, events, messages, sla } = detail;

  const getSlaBadge = (status: string) => {
    switch (status) {
      case 'ON_TRACK':
        return 'text-emerald-400 bg-emerald-950/60 border-emerald-800/60';
      case 'DUE_SOON':
        return 'text-amber-400 bg-amber-950/60 border-amber-800/60';
      case 'OVERDUE':
        return 'text-red-400 bg-red-950/60 border-red-800/60';
      default:
        return 'text-gray-400 bg-gray-800 border-gray-700';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      {/* Top Bar */}
      <div className="space-y-3">
        <button
          onClick={() => navigate('/citizen/dashboard')}
          className="flex items-center space-x-2 text-xs text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to My Requests</span>
        </button>

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-800 pb-6">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-sm px-2.5 py-0.5 rounded-lg bg-blue-950 border border-blue-800 text-blue-300 font-semibold">
                {request.request_reference}
              </span>
              <span className="text-gray-500 font-mono text-xs">Case: {request.case_reference}</span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getSlaBadge(
                  sla.status
                )}`}
              >
                SLA: {sla.status.replace(/_/g, ' ')} ({sla.hours_remaining}h)
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-2">{request.title}</h1>
            <p className="text-xs text-gray-400 mt-1">
              Category: <span className="text-gray-300 font-medium">{request.request_type.replace(/_/g, ' ')}</span> •
              Priority: <span className="text-amber-400 font-medium">{request.priority}</span>
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={loadDetail}
              className="p-2.5 rounded-xl border border-gray-800 text-gray-300 hover:text-white hover:bg-gray-800 transition"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            {['DRAFT', 'SUBMITTED'].includes(request.status) && (
              <button
                onClick={handleCancelRequest}
                className="px-4 py-2 rounded-xl bg-red-950/60 hover:bg-red-900/60 border border-red-800/80 text-red-300 text-xs font-medium transition flex items-center space-x-1.5"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>Cancel Request</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Revision Banner if More Info Requested */}
      {request.status === 'MORE_INFO_REQUESTED' && (
        <div className="p-5 rounded-2xl bg-amber-950/40 border border-amber-800/60 space-y-3">
          <div className="flex items-center space-x-2 text-amber-300 font-semibold text-sm">
            <AlertCircle className="w-5 h-5 text-amber-400" />
            <span>Action Required: Reviewing Officer Requested Additional Information</span>
          </div>
          <p className="text-xs text-amber-200/90 leading-relaxed">
            Please review the officer notes in the case timeline below, provide clarification or updated
            document information, and submit your revision to resume processing.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <input
              type="text"
              value={revisionComment}
              onChange={(e) => setRevisionComment(e.target.value)}
              placeholder="State your clarification or updated deed / boundary details..."
              className="flex-1 bg-gray-900 border border-amber-700/60 rounded-xl px-4 py-2.5 text-white placeholder-gray-500 text-xs focus:outline-none focus:border-amber-400"
            />
            <button
              onClick={handleSubmitRevision}
              disabled={submittingRevision || !revisionComment.trim()}
              className="px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs transition disabled:opacity-50"
            >
              {submittingRevision ? 'Submitting...' : 'Submit Revision & Resume Review'}
            </button>
          </div>
        </div>
      )}

      {/* Main Grid: Timeline + Messages */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Description & Case Timeline */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description Card */}
          <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 space-y-3">
            <h3 className="font-semibold text-white text-sm">Request Details</h3>
            <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
              {request.description}
            </p>
          </div>

          {/* Timeline */}
          <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 space-y-5">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="font-semibold text-white text-sm">Case Status Timeline</h3>
              <span className="text-xs text-gray-500">{events.length} events logged</span>
            </div>

            <div className="space-y-6 relative pl-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-800">
              {events.map((ev) => (
                <div key={ev.id} className="relative space-y-1">
                  <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-blue-500 border-2 border-gray-900 ring-2 ring-gray-900" />
                  <div className="flex items-center space-x-2 text-xs">
                    <span className="font-semibold text-white">
                      {ev.new_status.replace(/_/g, ' ')}
                    </span>
                    <span className="text-gray-500">•</span>
                    <span className="text-gray-400 capitalize">{ev.actor_role.toLowerCase()}</span>
                    <span className="text-gray-500">•</span>
                    <span className="text-gray-500">
                      {new Date(ev.created_at).toLocaleString()}
                    </span>
                  </div>
                  {ev.reason && (
                    <p className="text-xs text-amber-300/90 font-medium">
                      Reason: {ev.reason}
                    </p>
                  )}
                  {ev.comment && (
                    <p className="text-xs text-gray-400 italic">
                      "{ev.comment}"
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Col: Communication Center */}
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 flex flex-col h-[520px]">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3 mb-4">
              <div className="flex items-center space-x-2 text-white font-semibold text-sm">
                <MessageSquare className="w-4 h-4 text-blue-400" />
                <span>Officer Communications</span>
              </div>
              <span className="text-[11px] text-gray-500">Direct Case Channel</span>
            </div>

            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
              {messages.length === 0 ? (
                <div className="h-full flex items-center justify-center text-center text-gray-500">
                  No public messages yet. Use the message box below to ask questions or provide updates.
                </div>
              ) : (
                messages.map((m) => {
                  const isCitizen = m.sender_role === 'CITIZEN';
                  return (
                    <div
                      key={m.id}
                      className={`p-3 rounded-xl max-w-[88%] space-y-1 ${
                        isCitizen
                          ? 'ml-auto bg-blue-600/30 border border-blue-500/40 text-blue-100'
                          : 'mr-auto bg-gray-800/80 border border-gray-700/60 text-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px] text-gray-400">
                        <span className="font-semibold text-gray-300">
                          {isCitizen ? 'You' : 'Reviewing Officer'}
                        </span>
                        <span>{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <p className="text-xs leading-relaxed whitespace-pre-wrap">{m.message_body}</p>
                    </div>
                  );
                })
              )}
            </div>

            {/* Message Input */}
            <form onSubmit={handleSendMessage} className="mt-4 pt-3 border-t border-gray-800 flex items-center space-x-2">
              <input
                type="text"
                value={newMsg}
                onChange={(e) => setNewMsg(e.target.value)}
                placeholder="Type message to reviewing officer..."
                className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-3.5 py-2 text-white text-xs placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
              />
              <button
                type="submit"
                disabled={sendingMsg || !newMsg.trim()}
                className="p-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white transition disabled:opacity-50"
                title="Send Message"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
