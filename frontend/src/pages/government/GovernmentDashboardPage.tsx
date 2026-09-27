import React, { useEffect, useState } from 'react';
import {
  FolderKanban,
  UserCheck,
  AlertTriangle,
  Clock,
  Compass,
  CheckCircle,
  Percent,
  RefreshCw,
  Search,
  ExternalLink,
  Filter,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { workflowApi } from '../../api/workflow';
import { GovernmentDashboardMetrics, ServiceRequest } from '../../types/workflow';

export const GovernmentDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<GovernmentDashboardMetrics | null>(null);
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [search, setSearch] = useState<string>('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [m, r] = await Promise.all([
        workflowApi.getGovernmentDashboard(),
        workflowApi.listServiceRequests({
          status: statusFilter || undefined,
          priority: priorityFilter || undefined,
          search: search || undefined,
          limit: 20,
        }),
      ]);
      setMetrics(m);
      setRequests(r.items);
    } catch (err: any) {
      setError(err?.message || 'Failed to load government operations dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter, priorityFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
      case 'COMPLETED':
        return 'bg-emerald-900/40 text-emerald-400 border-emerald-700/50';
      case 'REJECTED':
      case 'CANCELLED':
        return 'bg-red-900/40 text-red-400 border-red-700/50';
      case 'MORE_INFO_REQUESTED':
        return 'bg-amber-900/40 text-amber-300 border-amber-700/50';
      case 'SURVEY_COMMISSIONED':
      case 'FIELD_VERIFIED':
        return 'bg-purple-900/40 text-purple-300 border-purple-700/50';
      default:
        return 'bg-blue-900/40 text-blue-300 border-blue-700/50';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-800 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-purple-900/60 text-purple-300 border border-purple-700/50">
              Government Operations
            </span>
            <span className="text-gray-500 text-xs">• Cadastre & Boundary Review Workspace</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">Operations & Case Dashboard</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Monitor real-time case queues, SLA compliance, surveyor commissions, and official cadastral updates.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate('/government/queues')}
            className="px-4 py-2.5 rounded-xl border border-gray-700 hover:border-gray-600 text-gray-200 text-sm font-medium transition hover:bg-gray-800"
          >
            Review Queues
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2.5 rounded-xl border border-gray-800 text-gray-300 hover:text-white hover:bg-gray-800 transition"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-900/30 border border-red-700/50 text-red-200 text-sm flex items-center space-x-3">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Active</span>
            <FolderKanban className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {metrics ? metrics.total_active_cases : '—'}
          </div>
          <div className="text-[11px] text-gray-500 mt-1">Total open cases</div>
        </div>

        <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Unassigned</span>
            <UserCheck className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">
            {metrics ? metrics.unassigned_cases : '—'}
          </div>
          <div className="text-[11px] text-gray-500 mt-1">Pending officer assignment</div>
        </div>

        <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Overdue</span>
            <AlertTriangle className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-2xl font-bold text-red-400">
            {metrics ? metrics.overdue_cases : '—'}
          </div>
          <div className="text-[11px] text-gray-500 mt-1">Exceeded target SLA</div>
        </div>

        <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Due Soon</span>
            <Clock className="w-4 h-4 text-amber-300" />
          </div>
          <div className="text-2xl font-bold text-white">
            {metrics ? metrics.due_soon_cases : '—'}
          </div>
          <div className="text-[11px] text-gray-500 mt-1">Within 24h deadline</div>
        </div>

        <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Surveys</span>
            <Compass className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {metrics ? metrics.surveys_commissioned : '—'}
          </div>
          <div className="text-[11px] text-gray-500 mt-1">Commissioned field teams</div>
        </div>

        <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">SLA Rate</span>
            <Percent className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {metrics ? `${metrics.sla_compliance_rate}%` : '—'}
          </div>
          <div className="text-[11px] text-gray-500 mt-1">Compliance index</div>
        </div>
      </div>

      {/* Case Management Section */}
      <div className="space-y-4">
        {/* Search & Filters */}
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
          <form onSubmit={handleSearchSubmit} className="w-full sm:w-80 relative">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search reference, title, or parcel..."
              className="w-full bg-gray-900 border border-gray-800 rounded-xl pl-9 pr-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
            />
            <Search className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
          </form>

          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="MORE_INFO_REQUESTED">More Info Requested</option>
              <option value="SURVEY_COMMISSIONED">Survey Commissioned</option>
              <option value="FIELD_VERIFIED">Field Verified</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
              <option value="COMPLETED">Completed</option>
            </select>

            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Priorities</option>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
              <option value="URGENT">Urgent</option>
            </select>
          </div>
        </div>

        {/* Case Table */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-950/80 text-gray-400 text-xs uppercase tracking-wider border-b border-gray-800">
                <tr>
                  <th className="px-5 py-3.5">Case Reference</th>
                  <th className="px-5 py-3.5">Title & Request Type</th>
                  <th className="px-5 py-3.5">Priority</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Assigned Officer</th>
                  <th className="px-5 py-3.5">Submitted</th>
                  <th className="px-5 py-3.5 text-right">Workspace</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800 text-gray-300">
                {requests.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-8 text-center text-gray-500 text-xs">
                      No cases match current filters.
                    </td>
                  </tr>
                ) : (
                  requests.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => navigate(`/government/workspace/${r.id}`)}
                      className="hover:bg-gray-800/40 cursor-pointer transition"
                    >
                      <td className="px-5 py-4 font-mono text-xs font-semibold text-purple-300">
                        {r.case_reference}
                      </td>
                      <td className="px-5 py-4">
                        <div className="font-medium text-white">{r.title}</div>
                        <div className="text-xs text-gray-500">{r.request_type.replace(/_/g, ' ')}</div>
                      </td>
                      <td className="px-5 py-4 text-xs font-semibold">
                        <span
                          className={
                            r.priority === 'URGENT'
                              ? 'text-red-400'
                              : r.priority === 'HIGH'
                              ? 'text-amber-400'
                              : 'text-gray-400'
                          }
                        >
                          {r.priority}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getStatusBadge(
                            r.status
                          )}`}
                        >
                          {r.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-xs text-gray-400 font-mono">
                        {r.assigned_to ? r.assigned_to.slice(0, 8) + '...' : <span className="text-amber-400 italic">Unassigned</span>}
                      </td>
                      <td className="px-5 py-4 text-xs text-gray-400">
                        {new Date(r.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/government/workspace/${r.id}`);
                          }}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition"
                          title="Open Case Workspace"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
