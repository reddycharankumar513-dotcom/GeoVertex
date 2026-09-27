import React, { useEffect, useState } from 'react';
import {
  ChangeCandidate,
  ChangeDetectionRun,
  TemporalMetrics,
  TimelineEntry,
  CandidateStatus,
  ChangeSignificance,
} from '../../types/temporal';
import { temporalApi } from '../../api/temporal';
import { ChangeDetailModal } from '../../features/temporal/ChangeDetailModal';
import { RunCreateModal } from '../../features/temporal/RunCreateModal';
import { useAuth } from '../../auth/AuthContext';

export const TemporalIntelligencePage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'CANDIDATES' | 'RUNS' | 'TIMELINE'>('CANDIDATES');

  // Data state
  const [runs, setRuns] = useState<ChangeDetectionRun[]>([]);
  const [candidates, setCandidates] = useState<ChangeCandidate[]>([]);
  const [metrics, setMetrics] = useState<TemporalMetrics | null>(null);
  const [loading, setLoading] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [significanceFilter, setSignificanceFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  // Timeline lookup state
  const [timelineEntityType, setTimelineEntityType] = useState('BUILDING');
  const [timelineEntityId, setTimelineEntityId] = useState('');
  const [timelineEntries, setTimelineEntries] = useState<TimelineEntry[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(false);

  // Modals
  const [selectedCandidate, setSelectedCandidate] = useState<ChangeCandidate | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);

  // Load candidates and runs
  const fetchData = async () => {
    setLoading(true);
    try {
      const [runsData, candidatesData, metricsData] = await Promise.all([
        temporalApi.listRuns({ limit: 50 }),
        temporalApi.listCandidates({
          status: (statusFilter as CandidateStatus) || undefined,
          significance: (significanceFilter as ChangeSignificance) || undefined,
          limit: 100,
        }),
        temporalApi.getMetrics(),
      ]);
      setRuns(runsData);
      setCandidates(candidatesData);
      setMetrics(metricsData);
    } catch (err) {
      console.error('Error fetching temporal intelligence data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [statusFilter, significanceFilter]);

  const handleFetchTimeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!timelineEntityId.trim()) return;
    setTimelineLoading(true);
    try {
      const entries = await temporalApi.getEntityTimeline(
        timelineEntityType,
        timelineEntityId.trim()
      );
      setTimelineEntries(entries);
    } catch (err) {
      console.error('Error fetching timeline:', err);
    } finally {
      setTimelineLoading(false);
    }
  };

  const handleCandidateClick = (candidate: ChangeCandidate) => {
    setSelectedCandidate(candidate);
    setIsDetailModalOpen(true);
  };

  const handleCandidateReviewSubmit = async (
    candidateId: string,
    payload: any
  ) => {
    const updated = await temporalApi.reviewCandidate(candidateId, payload);
    setCandidates((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    setSelectedCandidate(updated);
    fetchData();
  };

  const filteredCandidates = candidates.filter((c) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.change_type.toLowerCase().includes(q) ||
      (c.entity_id && c.entity_id.toLowerCase().includes(q)) ||
      c.detection_run_id.toLowerCase().includes(q) ||
      c.id.toLowerCase().includes(q)
    );
  });

  const getSignificanceBadge = (sig: ChangeSignificance) => {
    switch (sig) {
      case 'MAJOR':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">MAJOR</span>;
      case 'MODERATE':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">MODERATE</span>;
      case 'MINOR':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-500/20 text-blue-300 border border-blue-500/30">MINOR</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] bg-slate-700 text-slate-300">UNKNOWN</span>;
    }
  };

  const getStatusBadge = (status: CandidateStatus) => {
    switch (status) {
      case 'NEW':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-sky-500/20 text-sky-300 border border-sky-500/30">NEW</span>;
      case 'UNDER_REVIEW':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30">UNDER REVIEW</span>;
      case 'CONFIRMED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">CONFIRMED</span>;
      case 'REJECTED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-rose-500/20 text-rose-300 border border-rose-500/30">REJECTED</span>;
      case 'DISMISSED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-600/30 text-slate-400 border border-slate-600">DISMISSED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] bg-slate-700 text-slate-300">{status}</span>;
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
            <span>⏱️ AI Change Detection & Temporal Property Intelligence</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Temporal cadastral snapshots, deterministic spatial differences, multi-source evidence, and strict human verification.
          </p>
        </div>

        <div className="flex items-center space-x-3 self-start sm:self-auto">
          <button
            onClick={fetchData}
            className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition"
          >
            ↻ Refresh
          </button>
          {user?.role !== 'CITIZEN' && (
            <button
              onClick={() => setIsRunModalOpen(true)}
              className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow flex items-center space-x-2 transition"
            >
              <span>+ Dispatch Change Detection Run</span>
            </button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Runs</span>
          <div className="text-xl font-bold text-white mt-1">{metrics?.total_runs ?? runs.length}</div>
        </div>
        <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Candidates</span>
          <div className="text-xl font-bold text-white mt-1">{metrics?.total_candidates ?? candidates.length}</div>
        </div>
        <div className="p-3 bg-amber-950/40 border border-amber-900/60 rounded-lg">
          <span className="text-[10px] text-amber-300 uppercase font-semibold">Under Review</span>
          <div className="text-xl font-bold text-amber-400 mt-1">
            {metrics?.under_review ?? candidates.filter(c => c.status === 'UNDER_REVIEW' || c.status === 'NEW').length}
          </div>
        </div>
        <div className="p-3 bg-emerald-950/40 border border-emerald-900/60 rounded-lg">
          <span className="text-[10px] text-emerald-300 uppercase font-semibold">Confirmed</span>
          <div className="text-xl font-bold text-emerald-400 mt-1">
            {metrics?.confirmed ?? candidates.filter(c => c.status === 'CONFIRMED').length}
          </div>
        </div>
        <div className="p-3 bg-rose-950/40 border border-rose-900/60 rounded-lg">
          <span className="text-[10px] text-rose-300 uppercase font-semibold">Rejected</span>
          <div className="text-xl font-bold text-rose-400 mt-1">
            {metrics?.rejected ?? candidates.filter(c => c.status === 'REJECTED').length}
          </div>
        </div>
        <div className="p-3 bg-sky-950/40 border border-sky-900/60 rounded-lg">
          <span className="text-[10px] text-sky-300 uppercase font-semibold">Building Changes</span>
          <div className="text-xl font-bold text-sky-400 mt-1">
            {metrics?.building_changes ?? candidates.filter(c => c.entity_type === 'BUILDING').length}
          </div>
        </div>
        <div className="p-3 bg-purple-950/40 border border-purple-900/60 rounded-lg">
          <span className="text-[10px] text-purple-300 uppercase font-semibold">Floor/Parcel</span>
          <div className="text-xl font-bold text-purple-400 mt-1">
            {(metrics?.floor_changes ?? 0) + (metrics?.parcel_changes ?? 0)}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-6 text-xs font-medium">
        <button
          onClick={() => setActiveTab('CANDIDATES')}
          className={`pb-3 transition relative ${
            activeTab === 'CANDIDATES'
              ? 'text-sky-400 border-b-2 border-sky-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Change Candidates ({candidates.length})
        </button>
        <button
          onClick={() => setActiveTab('RUNS')}
          className={`pb-3 transition relative ${
            activeTab === 'RUNS'
              ? 'text-sky-400 border-b-2 border-sky-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Detection Runs ({runs.length})
        </button>
        <button
          onClick={() => setActiveTab('TIMELINE')}
          className={`pb-3 transition relative ${
            activeTab === 'TIMELINE'
              ? 'text-sky-400 border-b-2 border-sky-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Entity Timeline Explorer
        </button>
      </div>

      {/* Tab: Candidates */}
      {activeTab === 'CANDIDATES' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-xs">
            <div className="flex items-center space-x-3 flex-wrap gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search candidates by type or entity..."
                className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-white placeholder-slate-500 w-64 focus:outline-none focus:border-sky-500"
              />

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-slate-300 focus:outline-none focus:border-sky-500"
              >
                <option value="">All Statuses</option>
                <option value="NEW">New</option>
                <option value="UNDER_REVIEW">Under Review</option>
                <option value="CONFIRMED">Confirmed</option>
                <option value="REJECTED">Rejected</option>
                <option value="DISMISSED">Dismissed</option>
              </select>

              <select
                value={significanceFilter}
                onChange={(e) => setSignificanceFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-slate-300 focus:outline-none focus:border-sky-500"
              >
                <option value="">All Significance</option>
                <option value="MAJOR">Major</option>
                <option value="MODERATE">Moderate</option>
                <option value="MINOR">Minor</option>
              </select>
            </div>

            <div className="text-slate-400 text-[11px]">
              Showing {filteredCandidates.length} candidate(s)
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto bg-slate-900 border border-slate-800 rounded-lg">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-3">Entity</th>
                  <th className="p-3">Change Type</th>
                  <th className="p-3">Significance</th>
                  <th className="p-3">Magnitude Metrics</th>
                  <th className="p-3">Evidence Count</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {filteredCandidates.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-6 text-center text-slate-500">
                      {loading ? 'Loading candidates...' : 'No change candidates found matching filters.'}
                    </td>
                  </tr>
                ) : (
                  filteredCandidates.map((candidate) => (
                    <tr
                      key={candidate.id}
                      className="hover:bg-slate-800/30 transition cursor-pointer"
                      onClick={() => handleCandidateClick(candidate)}
                    >
                      <td className="p-3 font-sans">
                        <div className="font-semibold text-white">
                          {candidate.entity_type}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          {candidate.entity_id || 'Unmatched'}
                        </div>
                      </td>
                      <td className="p-3 font-sans">
                        <span className="font-medium text-sky-400">
                          {candidate.change_type.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="p-3">
                        {getSignificanceBadge(candidate.significance)}
                      </td>
                      <td className="p-3 text-[11px]">
                        {candidate.magnitude.area_difference_sqm !== undefined && (
                          <div>Δ Area: {candidate.magnitude.area_difference_sqm.toFixed(2)} m² ({candidate.magnitude.area_change_percentage?.toFixed(1)}%)</div>
                        )}
                        {candidate.magnitude.iou !== undefined && (
                          <div className="text-slate-400">IoU: {candidate.magnitude.iou.toFixed(3)}</div>
                        )}
                        {candidate.magnitude.height_difference_m !== undefined && (
                          <div>Δ Height: {candidate.magnitude.height_difference_m.toFixed(2)} m</div>
                        )}
                        {candidate.magnitude.floor_count_difference !== undefined && (
                          <div>Δ Floors: {candidate.magnitude.floor_count_difference}</div>
                        )}
                        {candidate.magnitude.attribute_name && (
                          <div className="text-amber-400">Attr: {candidate.magnitude.attribute_name}</div>
                        )}
                      </td>
                      <td className="p-3 font-sans">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]">
                          {candidate.evidence.length} source(s)
                        </span>
                      </td>
                      <td className="p-3">
                        {getStatusBadge(candidate.status)}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCandidateClick(candidate);
                          }}
                          className="px-2.5 py-1 rounded bg-sky-600/20 hover:bg-sky-600/40 text-sky-300 border border-sky-500/40 text-[11px] font-sans font-medium transition"
                        >
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
      )}

      {/* Tab: Detection Runs */}
      {activeTab === 'RUNS' && (
        <div className="overflow-x-auto bg-slate-900 border border-slate-800 rounded-lg">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/60 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="p-3">Run ID</th>
                <th className="p-3">Target Scope</th>
                <th className="p-3">Method</th>
                <th className="p-3">Baseline / Comparison</th>
                <th className="p-3">Status</th>
                <th className="p-3">Started / Finished</th>
                <th className="p-3">Summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-slate-500">
                    No change detection runs recorded.
                  </td>
                </tr>
              ) : (
                runs.map((run) => (
                  <tr key={run.id} className="hover:bg-slate-800/30 transition">
                    <td className="p-3 text-[11px] text-slate-400 font-mono">
                      {run.id.slice(0, 8)}...
                    </td>
                    <td className="p-3 font-sans">
                      <span className="font-semibold text-white">{run.target_type}</span>
                      {run.target_id && <div className="text-[11px] text-slate-400 font-mono">{run.target_id}</div>}
                    </td>
                    <td className="p-3 font-sans">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] border border-slate-700">
                        {run.detection_method}
                      </span>
                    </td>
                    <td className="p-3 text-[11px] font-mono">
                      <div>Base: {run.baseline_reference}</div>
                      <div>Comp: {run.comparison_reference}</div>
                    </td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          run.status === 'COMPLETED'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : run.status === 'RUNNING'
                            ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30 animate-pulse'
                            : run.status === 'FAILED'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : 'bg-slate-700 text-slate-300'
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className="p-3 text-[11px] font-sans text-slate-400">
                      <div>{run.started_at ? new Date(run.started_at).toLocaleTimeString() : '-'}</div>
                      <div>{run.completed_at ? new Date(run.completed_at).toLocaleTimeString() : '-'}</div>
                    </td>
                    <td className="p-3 font-sans text-[11px]">
                      {run.summary?.candidates_detected !== undefined ? (
                        <span className="text-sky-300">
                          {run.summary.candidates_detected} candidate(s) found
                        </span>
                      ) : (
                        <span className="text-slate-500">-</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Timeline Explorer */}
      {activeTab === 'TIMELINE' && (
        <div className="space-y-4">
          <form onSubmit={handleFetchTimeline} className="bg-slate-900 border border-slate-800 p-4 rounded-lg flex flex-wrap items-center gap-3">
            <select
              value={timelineEntityType}
              onChange={(e) => setTimelineEntityType(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white text-xs focus:outline-none focus:border-sky-500"
            >
              <option value="BUILDING">Building</option>
              <option value="PARCEL">Parcel</option>
              <option value="FLOOR">Floor</option>
              <option value="UNIT">Unit</option>
            </select>
            <input
              type="text"
              value={timelineEntityId}
              onChange={(e) => setTimelineEntityId(e.target.value)}
              placeholder="Enter Entity ID (e.g. BLD-001 or UUID)..."
              className="flex-1 min-w-[240px] bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white text-xs font-mono focus:outline-none focus:border-sky-500"
              required
            />
            <button
              type="submit"
              disabled={timelineLoading}
              className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow transition disabled:opacity-50"
            >
              {timelineLoading ? 'Loading Timeline...' : 'Fetch Timeline'}
            </button>
          </form>

          {timelineEntries.length > 0 && (
            <div className="relative border-l-2 border-slate-700 ml-4 pl-6 space-y-6">
              {timelineEntries.map((entry, idx) => (
                <div key={idx} className="relative group">
                  {/* Timeline dot */}
                  <div className="absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full bg-sky-500 border-2 border-slate-950" />
                  
                  <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg space-y-2 hover:border-slate-700 transition">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-sky-300 border border-slate-700">
                          {entry.entry_type}
                        </span>
                        <span className="font-semibold text-white">{entry.title}</span>
                      </div>
                      <span className="text-slate-400 font-mono text-[11px]">
                        {entry.date ? new Date(entry.date).toLocaleString() : 'Undated'} ({entry.date_precision})
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 font-sans">{entry.description}</p>

                    <div className="text-[11px] text-slate-400 font-mono pt-2 border-t border-slate-800/80 flex items-center justify-between">
                      <span>Source: {entry.source}</span>
                      {entry.status && <span className="text-amber-400">Status: {entry.status}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {timelineEntries.length === 0 && !timelineLoading && (
            <div className="text-center py-12 text-slate-500 text-xs">
              Enter an Entity ID above and click Fetch Timeline to reconstruct historical evolution.
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      <ChangeDetailModal
        candidate={selectedCandidate}
        isOpen={isDetailModalOpen}
        onClose={() => {
          setIsDetailModalOpen(false);
          setSelectedCandidate(null);
        }}
        onReviewSubmit={handleCandidateReviewSubmit}
      />

      <RunCreateModal
        isOpen={isRunModalOpen}
        onClose={() => setIsRunModalOpen(false)}
        onRunCreated={fetchData}
      />
    </div>
  );
};
