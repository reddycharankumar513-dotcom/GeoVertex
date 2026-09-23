import React, { useEffect, useState } from 'react';
import { History, RefreshCw, AlertCircle, ShieldAlert } from 'lucide-react';
import { api } from '../../api/client';
import { AuditEvent, PaginatedResult } from '../../types';

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAuditLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<PaginatedResult<AuditEvent>>('/audit?size=50');
      setLogs(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Security & Audit Trail</h1>
          <p className="text-sm text-slate-400 mt-1">
            Tamper-evident operational events, security incidents, and administrative decisions.
          </p>
        </div>
        <button
          onClick={fetchAuditLogs}
          disabled={loading}
          className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center space-x-2 text-xs font-semibold transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Audit Logs Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-950/60 text-slate-400 text-[11px] font-mono uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-6">Timestamp</th>
                <th className="py-3.5 px-4">Action Event</th>
                <th className="py-3.5 px-4">Entity</th>
                <th className="py-3.5 px-4">Actor ID</th>
                <th className="py-3.5 px-6">Event Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200 font-mono text-xs">
              {loading && logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500 font-sans text-xs">
                    Querying audit events from PostgreSQL...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500 font-sans text-xs">
                    No audit records logged yet.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-850/40 transition-colors">
                    <td className="py-4 px-6 text-slate-400 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-4 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] bg-purple-950/60 border border-purple-800 text-purple-300">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-slate-300">
                      <span className="text-slate-400">{log.entity_type}:</span> {log.entity_id.slice(0, 8)}...
                    </td>
                    <td className="py-4 px-4 text-slate-400">
                      {log.actor_user_id ? `${log.actor_user_id.slice(0, 8)}...` : 'SYSTEM'}
                    </td>
                    <td className="py-4 px-6 text-slate-300 max-w-xs truncate">
                      {JSON.stringify(log.details)}
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
