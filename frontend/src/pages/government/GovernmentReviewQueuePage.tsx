import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ListChecks,
  CheckCircle2,
  Clock,
  ExternalLink,
  RefreshCw,
  Search,
  Filter,
  UserCheck,
} from 'lucide-react';
import { workflowApi } from '../../api/workflow';
import { WorkflowTask } from '../../types/workflow';

export const GovernmentReviewQueuePage: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<WorkflowTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [taskTypeFilter, setTaskTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [myTasksOnly, setMyTasksOnly] = useState<boolean>(false);

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await workflowApi.listGovernmentTasks({
        task_type: taskTypeFilter || undefined,
        status: statusFilter || undefined,
        my_tasks_only: myTasksOnly,
      });
      setTasks(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load workflow review tasks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [taskTypeFilter, statusFilter, myTasksOnly]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'bg-emerald-950/60 text-emerald-400 border-emerald-800';
      case 'IN_PROGRESS':
        return 'bg-blue-950/60 text-blue-300 border-blue-800';
      case 'CANCELLED':
        return 'bg-red-950/60 text-red-400 border-red-800';
      default:
        return 'bg-gray-800 text-gray-300 border-gray-700';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-800 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-purple-900/60 text-purple-300 border border-purple-700/50">
              Officer Work Queues
            </span>
            <span className="text-gray-500 text-xs">• Cadastral Case Task Allocation</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">Review & Verification Queue</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Operational review tasks assigned to officer teams for verification, GIS inspection, and approval.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadTasks}
            disabled={loading}
            className="p-2.5 rounded-xl border border-gray-800 text-gray-300 hover:text-white hover:bg-gray-800 transition"
            title="Refresh Tasks"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-gray-900 p-4 rounded-2xl border border-gray-800">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={taskTypeFilter}
            onChange={(e) => setTaskTypeFilter(e.target.value)}
            className="bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
          >
            <option value="">All Task Types</option>
            <option value="INITIAL_REVIEW">Initial Review</option>
            <option value="DOCUMENT_VERIFICATION">Document Verification</option>
            <option value="FIELD_SURVEY_EXECUTION">Field Survey Execution</option>
            <option value="GIS_BOUNDARY_VERIFICATION">GIS Boundary Verification</option>
            <option value="FINAL_APPROVAL">Final Approval</option>
            <option value="OFFICIAL_RECORD_UPDATE">Official Record Update</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-xs text-gray-300 focus:outline-none focus:border-blue-500"
          >
            <option value="">All Task Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>

          <label className="flex items-center space-x-2 text-xs text-gray-300 cursor-pointer pl-2">
            <input
              type="checkbox"
              checked={myTasksOnly}
              onChange={(e) => setMyTasksOnly(e.target.checked)}
              className="rounded bg-gray-950 border-gray-800 text-purple-600 focus:ring-0"
            />
            <span>My Tasks Only</span>
          </label>
        </div>

        <span className="text-xs text-gray-500">{tasks.length} tasks in queue</span>
      </div>

      {/* Tasks Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-950/80 text-gray-400 text-xs uppercase tracking-wider border-b border-gray-800">
              <tr>
                <th className="px-5 py-3.5">Task Title</th>
                <th className="px-5 py-3.5">Category</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Assigned To</th>
                <th className="px-5 py-3.5">Due Date</th>
                <th className="px-5 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-gray-300">
              {tasks.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-gray-500 text-xs">
                    No review tasks found matching criteria.
                  </td>
                </tr>
              ) : (
                tasks.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => navigate(`/government/workspace/${t.service_request_id}`)}
                    className="hover:bg-gray-800/40 cursor-pointer transition"
                  >
                    <td className="px-5 py-4">
                      <div className="font-medium text-white">{t.title}</div>
                      {t.description && (
                        <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                          {t.description}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-4 text-xs font-mono text-purple-300">
                      {t.task_type.replace(/_/g, ' ')}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getStatusBadge(
                          t.status
                        )}`}
                      >
                        {t.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-xs font-mono text-gray-400">
                      {t.assigned_to ? t.assigned_to.slice(0, 8) + '...' : <span className="text-amber-400 italic">Unassigned</span>}
                    </td>
                    <td className="px-5 py-4 text-xs text-gray-400">
                      {t.due_at ? new Date(t.due_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/government/workspace/${t.service_request_id}`);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-white text-xs font-medium transition inline-flex items-center space-x-1.5"
                      >
                        <span>Open Case</span>
                        <ExternalLink className="w-3.5 h-3.5" />
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
  );
};
