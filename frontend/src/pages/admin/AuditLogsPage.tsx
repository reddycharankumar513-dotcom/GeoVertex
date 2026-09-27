import React, { useEffect, useState } from 'react';
import {
  History,
  RefreshCw,
  AlertCircle,
  Download,
  Filter,
  ChevronDown,
  ChevronRight,
  Search,
  ExternalLink,
} from 'lucide-react';
import { auditApi } from '../../api/governance';
import { AuditEventItem, AuditStatistics } from '../../types/governance';

const CATEGORIES = [
  'ALL',
  'AUTHENTICATION',
  'AUTHORIZATION',
  'PROPERTY',
  'GIS',
  'SURVEY',
  'AI',
  'VALIDATION',
  'DOCUMENT',
  'CHANGE_DETECTION',
  'UTILITY',
  'IDENTIFIER',
  'WORKFLOW',
  'NOTIFICATION',
  'GOVERNANCE',
  'ADMINISTRATION',
  'SYSTEM',
];

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditEventItem[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<AuditStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Filters
  const [category, setCategory] = useState<string>('ALL');
  const [action, setAction] = useState('');
  const [entityType, setEntityType] = useState('');
  const [severity, setSeverity] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const fetchAuditLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const [res, statsRes] = await Promise.all([
        auditApi.listEvents({
          category: category !== 'ALL' ? category : undefined,
          action: action.trim() || undefined,
          entity_type: entityType.trim() || undefined,
          severity: severity || undefined,
          page,
          size: pageSize,
        }),
        auditApi.getStatistics().catch(() => null),
      ]);
      setLogs(res.items);
      setTotal(res.total);
      if (statsRes) setStats(statsRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [category, page, severity]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchAuditLogs();
  };

  const handleExport = (format: 'csv' | 'json') => {
    const filters: Record<string, string> = {};
    if (category !== 'ALL') filters.category = category;
    if (action.trim()) filters.action = action.trim();
    if (entityType.trim()) filters.entity_type = entityType.trim();
    if (severity) filters.severity = severity;
    const url = auditApi.getExportUrl(format, filters);
    window.open(url, '_blank');
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-purple-950/60 border border-purple-800 text-purple-300">
              Immutable Cadastral Ledger
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">Audit Trail & Investigation</h1>
          <p className="text-sm text-slate-400">
            Append-only security, operational, and cadastral decision logs with before/after state diffs.
          </p>
        </div>
        <div className="flex items-center space-x-2.5 self-start sm:self-auto">
          <button
            onClick={() => handleExport('csv')}
            className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center space-x-1.5 text-xs font-semibold transition cursor-pointer"
            title="Export CSV"
          >
            <Download className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>
          <button
            onClick={() => handleExport('json')}
            className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center space-x-1.5 text-xs font-semibold transition cursor-pointer"
            title="Export JSON"
          >
            <Download className="w-3.5 h-3.5" />
            <span>JSON</span>
          </button>
          <button
            onClick={fetchAuditLogs}
            disabled={loading}
            className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center space-x-2 text-xs font-semibold transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Statistics Ribbon */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-slate-900/60 border border-slate-800 p-3.5 rounded-xl">
            <span className="text-[11px] text-slate-500 uppercase tracking-wider block font-mono">
              Total Logged Events
            </span>
            <span className="text-xl font-bold text-white mt-0.5 block">
              {stats.total_events.toLocaleString()}
            </span>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-3.5 rounded-xl">
            <span className="text-[11px] text-slate-500 uppercase tracking-wider block font-mono">
              Unique Actors
            </span>
            <span className="text-xl font-bold text-purple-400 mt-0.5 block">
              {stats.distinct_actors}
            </span>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-3.5 rounded-xl">
            <span className="text-[11px] text-slate-500 uppercase tracking-wider block font-mono">
              Warnings / Errors
            </span>
            <span className="text-xl font-bold text-amber-400 mt-0.5 block">
              {(stats.by_severity?.WARNING || 0) + (stats.by_severity?.ERROR || 0)}
            </span>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-3.5 rounded-xl">
            <span className="text-[11px] text-slate-500 uppercase tracking-wider block font-mono">
              Ledger Health
            </span>
            <span className="text-xl font-bold text-emerald-400 mt-0.5 block">
              Immutable
            </span>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <form
        onSubmit={handleSearchSubmit}
        className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 backdrop-blur space-y-3"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Category */}
          <div>
            <label className="block text-[11px] text-slate-400 font-mono mb-1">Category</label>
            <select
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-slate-700"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Action */}
          <div>
            <label className="block text-[11px] text-slate-400 font-mono mb-1">Action Name</label>
            <input
              type="text"
              placeholder="e.g. PARCEL_RESTORED"
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-slate-700"
            />
          </div>

          {/* Entity Type */}
          <div>
            <label className="block text-[11px] text-slate-400 font-mono mb-1">Entity Type</label>
            <input
              type="text"
              placeholder="e.g. PARCEL, BUILDING"
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-slate-700"
            />
          </div>

          {/* Severity */}
          <div>
            <label className="block text-[11px] text-slate-400 font-mono mb-1">Severity</label>
            <select
              value={severity}
              onChange={(e) => {
                setSeverity(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-slate-700"
            >
              <option value="">ALL SEVERITIES</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          {/* Submit */}
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full py-1.5 px-3 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition cursor-pointer"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Apply Filters</span>
            </button>
          </div>
        </div>
      </form>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Audit Logs Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950/60 text-slate-400 text-[11px] uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4 w-8"></th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Entity</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4 text-center">Severity</th>
                <th className="py-3 px-4 text-center">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {loading && logs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 font-sans text-xs">
                    Querying immutable audit ledger...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 font-sans text-xs">
                    No audit records matching the specified criteria.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const isExpanded = expandedId === log.id;
                  return (
                    <React.Fragment key={log.id}>
                      <tr
                        onClick={() => setExpandedId(isExpanded ? null : log.id)}
                        className="hover:bg-slate-850/50 transition cursor-pointer"
                      >
                        <td className="py-3 px-4 text-slate-500">
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-slate-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-slate-600" />
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                            {log.category}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-semibold text-white whitespace-nowrap">
                          {log.action}
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          <span className="text-slate-400">{log.entity_type}:</span>{' '}
                          {log.entity_id ? log.entity_id.slice(0, 8) : ''}...
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {log.actor_role ? (
                            <span className="text-purple-300">{log.actor_role}</span>
                          ) : log.actor_user_id ? (
                            log.actor_user_id.slice(0, 8) + '...'
                          ) : (
                            'SYSTEM'
                          )}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              log.severity === 'CRITICAL'
                                ? 'bg-red-950 text-red-400 border border-red-800'
                                : log.severity === 'WARNING'
                                ? 'bg-amber-950 text-amber-400 border border-amber-800'
                                : log.severity === 'ERROR'
                                ? 'bg-rose-950 text-rose-400 border border-rose-800'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {log.severity}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] ${
                              log.result === 'SUCCESS'
                                ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800'
                                : 'bg-rose-950/60 text-rose-400 border border-rose-800'
                            }`}
                          >
                            {log.result}
                          </span>
                        </td>
                      </tr>

                      {/* Expanded Details Row */}
                      {isExpanded && (
                        <tr className="bg-slate-950/70 border-b border-slate-800">
                          <td colSpan={8} className="p-4 pl-12 space-y-3 font-sans">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
                              <div>
                                <span className="text-slate-500 block">Event UUID</span>
                                <span className="text-slate-300">{log.event_id || log.id}</span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Correlation ID</span>
                                <span className="text-slate-300">{log.correlation_id || '—'}</span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Workflow ID</span>
                                <span className="text-slate-300">{log.workflow_id || '—'}</span>
                              </div>
                              {log.source_type && (
                                <div>
                                  <span className="text-slate-500 block">Source / Provenance</span>
                                  <span className="text-slate-300">
                                    {log.source_type} ({log.source_id || 'none'})
                                  </span>
                                </div>
                              )}
                              {log.reason && (
                                <div className="md:col-span-2">
                                  <span className="text-slate-500 block">Justification Reason</span>
                                  <span className="text-amber-300">{log.reason}</span>
                                </div>
                              )}
                            </div>

                            {/* Before / After Snapshots if available */}
                            {(Object.keys(log.before_snapshot || {}).length > 0 ||
                              Object.keys(log.after_snapshot || {}).length > 0) && (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                                <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                                  <span className="text-[11px] font-mono text-slate-400 block mb-1">
                                    Before Snapshot State
                                  </span>
                                  <pre className="text-[11px] text-slate-300 font-mono overflow-x-auto">
                                    {JSON.stringify(log.before_snapshot, null, 2)}
                                  </pre>
                                </div>
                                <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                                  <span className="text-[11px] font-mono text-emerald-400 block mb-1">
                                    After Snapshot State
                                  </span>
                                  <pre className="text-[11px] text-emerald-300 font-mono overflow-x-auto">
                                    {JSON.stringify(log.after_snapshot, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}

                            {/* Event Details JSON */}
                            {log.details && Object.keys(log.details).length > 0 && (
                              <div className="pt-1">
                                <span className="text-[11px] font-mono text-slate-400 block mb-1">
                                  Additional Metadata & Payload
                                </span>
                                <pre className="bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-[11px] text-slate-300 font-mono overflow-x-auto">
                                  {JSON.stringify(log.details, null, 2)}
                                </pre>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-slate-800 bg-slate-950/40 text-xs">
          <span className="text-slate-400 font-mono">
            Showing {logs.length} of {total} events (Page {page} of {totalPages})
          </span>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-white disabled:opacity-50 cursor-pointer"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-white disabled:opacity-50 cursor-pointer"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
