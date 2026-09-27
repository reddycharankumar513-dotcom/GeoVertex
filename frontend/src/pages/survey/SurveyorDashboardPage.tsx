import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { SurveyAssignment } from '../../types';
import { surveyApi } from '../../api/surveys';
import { offlineStorage } from '../../utils/offlineStorage';
import { useOnlineStatus } from '../../hooks/useOnlineStatus';
import { useAuth } from '../../auth/AuthContext';
import {
  ClipboardList,
  Wifi,
  WifiOff,
  RefreshCw,
  Search,
  Clock,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Play,
  Check,
  Building2,
  MapPin,
  Calendar,
  AlertCircle,
  FileCheck,
} from 'lucide-react';

export const SurveyorDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isOnline, isSyncing, pendingSyncCount, lastSyncError, syncNow } = useOnlineStatus();

  const [assignments, setAssignments] = useState<SurveyAssignment[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const fetchAssignments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (isOnline) {
        const result = await surveyApi.getAssignments({ size: 100 });
        setAssignments(result.items);
        await offlineStorage.cacheAssignments(result.items);
      } else {
        const local = await offlineStorage.getLocalAssignments();
        setAssignments(local);
      }
    } catch (err: any) {
      console.warn('Network fetch failed, attempting offline cache:', err);
      try {
        const local = await offlineStorage.getLocalAssignments();
        setAssignments(local);
      } catch (cacheErr) {
        setError('Failed to load survey assignments from network or local storage.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [isOnline]);

  useEffect(() => {
    fetchAssignments();
  }, [fetchAssignments]);

  const handleAcceptAssignment = async (assignmentId: string) => {
    setActionInProgress(assignmentId);
    try {
      if (isOnline) {
        await surveyApi.acceptAssignment(assignmentId);
      } else {
        // Enqueue offline sync
        await offlineStorage.enqueueSyncOperation({
          client_operation_id: `accept_${assignmentId}_${Date.now()}`,
          operation_type: 'UPDATE',
          entity_type: 'SURVEY_ASSIGNMENT',
          entity_id: assignmentId,
          payload: { status: 'ACCEPTED' },
        });
      }
      await fetchAssignments();
    } catch (err: any) {
      setError(err?.message || 'Failed to accept assignment');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleStartSurvey = async (assignmentId: string) => {
    setActionInProgress(assignmentId);
    try {
      if (isOnline) {
        await surveyApi.startSurvey(assignmentId);
      }
      navigate(`/surveyor/field/${assignmentId}`);
    } catch (err: any) {
      // Even if network start fails or offline, navigate to field view
      navigate(`/surveyor/field/${assignmentId}`);
    } finally {
      setActionInProgress(null);
    }
  };

  const filteredAssignments = assignments.filter((a) => {
    if (activeTab !== 'ALL' && a.status !== activeTab) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchProject = a.project_name?.toLowerCase().includes(q) || a.project_code?.toLowerCase().includes(q);
      const matchParcel = a.parcel_code?.toLowerCase().includes(q);
      const matchBuilding = a.building_reference?.toLowerCase().includes(q);
      const matchNotes = a.notes?.toLowerCase().includes(q);
      return matchProject || matchParcel || matchBuilding || matchNotes;
    }
    return true;
  });

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'URGENT':
        return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
      case 'HIGH':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'MEDIUM':
        return 'bg-sky-500/15 text-sky-400 border-sky-500/30';
      default:
        return 'bg-slate-700/50 text-slate-300 border-slate-600/30';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      case 'SUBMITTED':
      case 'UNDER_REVIEW':
        return 'bg-sky-500/15 text-sky-400 border-sky-500/30';
      case 'REVISION_REQUIRED':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'IN_PROGRESS':
        return 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30';
      case 'ACCEPTED':
        return 'bg-teal-500/15 text-teal-400 border-teal-500/30';
      case 'REJECTED':
        return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-sky-500/10 border border-sky-500/20 text-sky-400 rounded-xl">
              <ClipboardList className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Surveyor Field Console</h1>
              <p className="text-xs text-slate-400">
                Logged in as <span className="text-slate-200 font-semibold">{user?.full_name || 'Field Surveyor'}</span> • Offline-Ready Mobile/PWA Workflow
              </p>
            </div>
          </div>

          {/* Network & Sync Bar */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Online Status Badge */}
            <div
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full border text-xs font-mono font-medium ${
                isOnline
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
              }`}
            >
              {isOnline ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
              <span>{isOnline ? 'ONLINE' : 'OFFLINE MODE'}</span>
            </div>

            {/* Sync Queue */}
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={syncNow}
                disabled={!isOnline || isSyncing || pendingSyncCount === 0}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                  pendingSyncCount > 0
                    ? 'bg-amber-500/20 border-amber-500/40 text-amber-300 hover:bg-amber-500/30'
                    : 'bg-slate-800/80 border-slate-700 text-slate-400'
                } disabled:opacity-50 cursor-pointer`}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
                <span>
                  {isSyncing
                    ? 'Syncing...'
                    : pendingSyncCount > 0
                    ? `Sync ${pendingSyncCount} Changes`
                    : 'All Synced'}
                </span>
              </button>

              <button
                type="button"
                onClick={fetchAssignments}
                disabled={isLoading}
                className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors cursor-pointer"
                title="Refresh assignment list"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {lastSyncError && (
          <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>Sync advisory: {lastSyncError}</span>
          </div>
        )}
      </div>

      {/* Tabs and Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-1 overflow-x-auto pb-1 sm:pb-0 scrollbar-thin">
          {[
            { id: 'ALL', label: 'All Tasks' },
            { id: 'ASSIGNED', label: 'Assigned' },
            { id: 'IN_PROGRESS', label: 'In Progress' },
            { id: 'SUBMITTED', label: 'Submitted' },
            { id: 'REVISION_REQUIRED', label: 'Revisions' },
            { id: 'APPROVED', label: 'Approved' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative min-w-[240px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter assignments or parcels..."
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Assignments List */}
      {isLoading && assignments.length === 0 ? (
        <div className="py-16 text-center text-slate-500 text-xs">
          Loading assignments...
        </div>
      ) : filteredAssignments.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-12 text-center text-slate-500 space-y-2">
          <ClipboardList className="w-8 h-8 mx-auto text-slate-600" />
          <div className="text-sm font-medium text-slate-400">No field assignments found</div>
          <p className="text-xs text-slate-500">
            {activeTab !== 'ALL' ? `No assignments in '${activeTab}' state.` : 'You have no assigned surveys at this time.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAssignments.map((assignment) => {
            const isAssigned = assignment.status === 'ASSIGNED';
            const isInProgress = assignment.status === 'IN_PROGRESS' || assignment.status === 'ACCEPTED';
            const isRevision = assignment.status === 'REVISION_REQUIRED';
            const isSubmitted = assignment.status === 'SUBMITTED' || assignment.status === 'UNDER_REVIEW';
            const isApproved = assignment.status === 'APPROVED';

            return (
              <div
                key={assignment.id}
                className="bg-slate-900/90 border border-slate-800 hover:border-slate-700/80 rounded-xl p-5 shadow-lg flex flex-col justify-between transition-all"
              >
                <div>
                  {/* Card Header: Badges */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono border font-semibold ${getPriorityBadge(
                        assignment.priority
                      )}`}
                    >
                      {assignment.priority} PRIORITY
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono border font-semibold ${getStatusBadge(
                        assignment.status
                      )}`}
                    >
                      {assignment.status.replace('_', ' ')}
                    </span>
                  </div>

                  {/* Project & Title */}
                  <div className="space-y-1">
                    <div className="text-[11px] font-mono text-sky-400 uppercase tracking-wider">
                      {assignment.project_code || 'PROJECT'}
                    </div>
                    <h3 className="text-sm font-bold text-white tracking-tight line-clamp-1">
                      {assignment.project_name || 'Cadastral Survey'}
                    </h3>
                  </div>

                  {/* Target metadata */}
                  <div className="mt-3.5 space-y-1.5 text-xs text-slate-300">
                    {assignment.building_reference && (
                      <div className="flex items-center space-x-2">
                        <Building2 className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                        <span className="font-mono text-slate-200">
                          Building: {assignment.building_reference}
                        </span>
                      </div>
                    )}
                    {assignment.parcel_code && (
                      <div className="flex items-center space-x-2">
                        <MapPin className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span className="font-mono text-slate-200">
                          Parcel: {assignment.parcel_code}
                        </span>
                      </div>
                    )}
                    {assignment.jurisdiction_name && (
                      <div className="text-[11px] text-slate-400">
                        Jurisdiction: {assignment.jurisdiction_name}
                      </div>
                    )}
                    {assignment.notes && (
                      <p className="text-[11px] text-slate-400 italic line-clamp-2 mt-1">
                        "{assignment.notes}"
                      </p>
                    )}
                  </div>
                </div>

                {/* Footer and Actions */}
                <div className="mt-5 pt-4 border-t border-slate-800/80 space-y-3">
                  <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
                    <span className="flex items-center space-x-1">
                      <Calendar className="w-3 h-3" />
                      <span>{new Date(assignment.assigned_at).toLocaleDateString()}</span>
                    </span>
                    {assignment.due_at && (
                      <span className="flex items-center space-x-1 text-amber-400">
                        <Clock className="w-3 h-3" />
                        <span>Due {new Date(assignment.due_at).toLocaleDateString()}</span>
                      </span>
                    )}
                  </div>

                  {/* Buttons based on status */}
                  <div className="flex items-center space-x-2">
                    {isAssigned && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleAcceptAssignment(assignment.id)}
                          disabled={actionInProgress === assignment.id}
                          className="flex-1 py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
                        >
                          <Check className="w-3.5 h-3.5 text-teal-400" />
                          <span>Accept</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleStartSurvey(assignment.id)}
                          disabled={actionInProgress === assignment.id}
                          className="flex-1 py-2 px-3 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer shadow-lg shadow-sky-600/20"
                        >
                          <Play className="w-3.5 h-3.5" />
                          <span>Start</span>
                        </button>
                      </>
                    )}

                    {(isInProgress || isRevision) && (
                      <button
                        type="button"
                        onClick={() => navigate(`/surveyor/field/${assignment.id}`)}
                        className={`w-full py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer shadow-lg ${
                          isRevision
                            ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-amber-600/20'
                            : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20'
                        }`}
                      >
                        <Play className="w-3.5 h-3.5" />
                        <span>{isRevision ? 'Revise Survey' : 'Continue Survey'}</span>
                        <ArrowRight className="w-3.5 h-3.5 ml-1" />
                      </button>
                    )}

                    {isSubmitted && (
                      <button
                        type="button"
                        onClick={() => navigate(`/surveyor/field/${assignment.id}`)}
                        className="w-full py-2 px-3 bg-slate-800 hover:bg-slate-700 text-sky-400 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
                      >
                        <FileCheck className="w-3.5 h-3.5" />
                        <span>View Submission</span>
                      </button>
                    )}

                    {isApproved && (
                      <button
                        type="button"
                        onClick={() => navigate(`/surveyor/field/${assignment.id}`)}
                        className="w-full py-2 px-3 bg-slate-800 hover:bg-slate-700 text-emerald-400 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Approved Record</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
