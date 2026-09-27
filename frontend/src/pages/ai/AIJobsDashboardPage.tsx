import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  Cpu,
  Filter,
  Layers,
  Play,
  RefreshCw,
  XCircle,
  FileCheck,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { aiApi } from '../../api/ai';
import { AIJob } from '../../types/ai';
import { AIJobCreateModal } from '../../features/ai/AIJobCreateModal';

export const AIJobsDashboardPage: React.FC = () => {
  const [jobs, setJobs] = useState<AIJob[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [jobTypeFilter, setJobTypeFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  const fetchJobs = async () => {
    setIsLoading(true);
    try {
      const res = await aiApi.listJobs({
        status: statusFilter || undefined,
        job_type: jobTypeFilter || undefined,
        size: 50,
      });
      setJobs(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load AI jobs:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [statusFilter, jobTypeFilter]);

  const queuedCount = jobs.filter((j) => j.status === 'QUEUED').length;
  const runningCount = jobs.filter((j) => j.status === 'RUNNING' || j.status === 'PREPROCESSING' || j.status === 'POSTPROCESSING' || j.status === 'VALIDATING').length;
  const completedCount = jobs.filter((j) => j.status === 'COMPLETED').length;
  const failedCount = jobs.filter((j) => j.status === 'FAILED').length;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800">
            <CheckCircle2 className="w-3 h-3" /> COMPLETED
          </span>
        );
      case 'RUNNING':
      case 'PREPROCESSING':
      case 'POSTPROCESSING':
      case 'VALIDATING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950/80 text-blue-300 border border-blue-800 animate-pulse">
            <RefreshCw className="w-3 h-3 animate-spin" /> {status}
          </span>
        );
      case 'QUEUED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-950/80 text-purple-300 border border-purple-800">
            <Clock className="w-3 h-3" /> QUEUED
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950/80 text-red-300 border border-red-800">
            <XCircle className="w-3 h-3" /> FAILED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
              <Cpu className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">AI Geospatial Processing</h1>
              <p className="text-sm text-slate-400">
                Candidate building & floor extraction pipeline from survey evidence
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/ai/reviews"
            className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-semibold rounded-xl border border-slate-700 transition-colors"
          >
            <FileCheck className="w-4 h-4 text-purple-400" />
            Candidate Reviews
          </Link>

          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white text-sm font-semibold rounded-xl shadow-lg shadow-purple-600/20 transition-all"
          >
            <Play className="w-4 h-4" />
            Dispatch AI Extraction
          </button>
        </div>
      </div>

      {/* KPI Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Queued Jobs</span>
            <Clock className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-2">{queuedCount}</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>In Processing</span>
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-2">{runningCount}</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Completed</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-2">{completedCount}</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Failed / Unconfigured</span>
            <AlertCircle className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-2">{failedCount}</div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/40 p-4 rounded-2xl border border-slate-800">
        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-purple-400"
          >
            <option value="">All Statuses</option>
            <option value="QUEUED">Queued</option>
            <option value="RUNNING">Running</option>
            <option value="COMPLETED">Completed</option>
            <option value="FAILED">Failed</option>
          </select>

          <select
            value={jobTypeFilter}
            onChange={(e) => setJobTypeFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-purple-400"
          >
            <option value="">All Job Types</option>
            <option value="BUILDING_EXTRACTION">Building Extraction</option>
            <option value="FLOOR_EXTRACTION">Floor Extraction</option>
            <option value="HEIGHT_ESTIMATION">Height Estimation</option>
          </select>
        </div>

        <button
          type="button"
          onClick={fetchJobs}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white px-3 py-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Jobs Table */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 uppercase font-semibold text-[11px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Job Type</th>
                <th className="py-3.5 px-4">Target Feature</th>
                <th className="py-3.5 px-4">Model & Version</th>
                <th className="py-3.5 px-4">Status & Stage</th>
                <th className="py-3.5 px-4">Progress</th>
                <th className="py-3.5 px-4">Dispatched At</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading && jobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    Loading AI extraction jobs...
                  </td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No AI jobs recorded. Dispatch a job using the button above.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-white">
                      {job.job_type.replace('_', ' ')}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-300">
                      <span className="px-1.5 py-0.5 bg-slate-800 rounded mr-1.5 text-slate-400">
                        {job.target_type}
                      </span>
                      {job.target_id.substring(0, 13)}...
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-purple-300">
                      {job.model_id} (v{job.model_version})
                    </td>
                    <td className="py-3 px-4">
                      {getStatusBadge(job.status)}
                      {job.error_code && (
                        <div className="text-[10px] text-red-400 font-mono mt-1">
                          {job.error_code}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="w-24">
                        <div className="flex justify-between text-[10px] text-slate-400 mb-0.5">
                          <span>{job.stage}</span>
                          <span>{job.progress_pct}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              job.status === 'FAILED'
                                ? 'bg-red-500'
                                : job.status === 'COMPLETED'
                                ? 'bg-emerald-500'
                                : 'bg-purple-500'
                            }`}
                            style={{ width: `${job.progress_pct}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      {new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {job.status === 'COMPLETED' ? (
                        <Link
                          to={`/ai/reviews?job_id=${job.id}`}
                          className="px-2.5 py-1 bg-purple-600/30 hover:bg-purple-600/50 text-purple-300 border border-purple-500/40 rounded-lg text-[11px] font-medium transition-colors"
                        >
                          View Results
                        </Link>
                      ) : job.status === 'FAILED' ? (
                        <span className="text-[11px] text-slate-500 italic">No output</span>
                      ) : (
                        <span className="text-[11px] text-blue-400 animate-pulse">Running...</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreateModal && (
        <AIJobCreateModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            fetchJobs();
          }}
        />
      )}
    </div>
  );
};
