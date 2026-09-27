import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  History,
  Bell,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  FileText,
  GitBranch,
  Layers,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';
import { governanceApi } from '../../api/governance';
import { DataIntegrityReport, GovernanceDashboard } from '../../types/governance';

export const GovernanceDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<GovernanceDashboard | null>(null);
  const [integrity, setIntegrity] = useState<DataIntegrityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkingIntegrity, setCheckingIntegrity] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashRes, integRes] = await Promise.all([
        governanceApi.getDashboard(),
        governanceApi.checkIntegrity(),
      ]);
      setData(dashRes);
      setIntegrity(integRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load governance metrics');
    } finally {
      setLoading(false);
    }
  };

  const handleRunIntegrityCheck = async () => {
    setCheckingIntegrity(true);
    try {
      const res = await governanceApi.checkIntegrity();
      setIntegrity(res);
    } catch (err: any) {
      console.error('Integrity check error', err);
    } finally {
      setCheckingIntegrity(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-emerald-950/60 border border-emerald-800 text-emerald-400">
              Phase 13 Governance
            </span>
            <span className="text-xs text-slate-500 font-mono">Immutable Provenance & Assurance</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">Platform Governance Dashboard</h1>
          <p className="text-sm text-slate-400">
            Append-only audit verification, deterministic version lineage, and system health assurance.
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center space-x-2 text-xs font-semibold transition-colors cursor-pointer self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Audit Events */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Immutable Audit Events
            </span>
            <div className="p-2 rounded-lg bg-purple-950/50 border border-purple-800/50 text-purple-400">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">
              {data ? data.audit.total_events.toLocaleString() : '—'}
            </span>
            <span className="text-xs text-purple-400 font-mono">Append-Only</span>
          </div>
          <div className="mt-2 text-xs text-slate-500">
            Across {data ? data.audit.distinct_actors : 0} distinct authenticated actors
          </div>
        </div>

        {/* Card 2: Versioned Entities */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Versioned Entities
            </span>
            <div className="p-2 rounded-lg bg-teal-950/50 border border-teal-800/50 text-teal-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">
              {data ? data.versioning.versioned_entities.toLocaleString() : '—'}
            </span>
            <span className="text-xs text-teal-400 font-mono">
              {data ? data.versioning.total_versions : 0} total snapshots
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-500">
            {data?.versioning.by_status?.CURRENT || 0} active, {data?.versioning.by_status?.SUPERSEDED || 0} superseded
          </div>
        </div>

        {/* Card 3: Notifications Health */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Notification Deliveries
            </span>
            <div className="p-2 rounded-lg bg-blue-950/50 border border-blue-800/50 text-blue-400">
              <Bell className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">
              {data ? data.notifications.total.toLocaleString() : '—'}
            </span>
            <span className="text-xs text-blue-400 font-mono">Multi-Channel</span>
          </div>
          <div className="mt-2 text-xs text-slate-500">
            {data?.notifications.by_status?.SENT || data?.notifications.by_status?.DELIVERED || 0} delivered / read
          </div>
        </div>

        {/* Card 4: Integrity Status */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Data Integrity
            </span>
            <div className="p-2 rounded-lg bg-emerald-950/50 border border-emerald-800/50 text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span
              className={`text-2xl font-bold ${
                integrity?.status === 'HEALTHY' ? 'text-emerald-400' : 'text-amber-400'
              }`}
            >
              {integrity ? integrity.status : 'CHECKING...'}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {integrity?.issues_count || 0} issues
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-500">
            Automated hash & version consistency
          </div>
        </div>
      </div>

      {/* Integrity Verification Card */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start space-x-3">
            {integrity?.status === 'HEALTHY' ? (
              <CheckCircle className="w-5 h-5 text-emerald-400 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5" />
            )}
            <div>
              <h2 className="text-base font-semibold text-white">System Data Integrity Verification</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Validates absence of orphan versions, verifies version chain consistency, and checks audit immutability.
              </p>
            </div>
          </div>
          <button
            onClick={handleRunIntegrityCheck}
            disabled={checkingIntegrity}
            className="px-3.5 py-1.5 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-300 hover:text-white hover:bg-emerald-900 text-xs font-medium transition cursor-pointer self-start sm:self-auto"
          >
            {checkingIntegrity ? 'Running Check...' : 'Run Integrity Audit'}
          </button>
        </div>

        {integrity && integrity.issues_count > 0 && (
          <div className="mt-4 space-y-2 border-t border-slate-800 pt-4">
            <span className="text-xs font-semibold text-amber-400">Detected Inconsistencies:</span>
            <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
              {integrity.issues.map((issue, idx) => (
                <li key={idx}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Quick Access & Category Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Recent Audit Trail */}
        <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white flex items-center space-x-2">
              <History className="w-4 h-4 text-purple-400" />
              <span>Recent Operational & Cadastral Events</span>
            </h2>
            <button
              onClick={() => navigate('/audit')}
              className="text-xs text-purple-400 hover:text-purple-300 flex items-center space-x-1 font-medium cursor-pointer"
            >
              <span>View Full Trail</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="text-[11px] text-slate-500 uppercase border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Entity</th>
                  <th className="py-2.5 px-3 text-right">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {loading && !data ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-500 font-sans">
                      Loading audit records...
                    </td>
                  </tr>
                ) : data?.recent_events?.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-500 font-sans">
                      No events recorded yet.
                    </td>
                  </tr>
                ) : (
                  data?.recent_events?.map((ev) => (
                    <tr key={ev.id} className="hover:bg-slate-850/40 transition">
                      <td className="py-2.5 px-3 text-slate-400 whitespace-nowrap">
                        {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '—'}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                          {ev.category}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-white whitespace-nowrap">
                        {ev.action}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">
                        {ev.entity_type}:{ev.entity_id ? ev.entity_id.slice(0, 8) : ''}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] ${
                            ev.result === 'SUCCESS'
                              ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800'
                              : 'bg-rose-950/60 text-rose-400 border border-rose-800'
                          }`}
                        >
                          {ev.result}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right 1 Col: Quick Links & Categories */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur space-y-3">
            <h2 className="text-sm font-semibold text-white font-sans">Governance Tools</h2>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/audit')}
                className="w-full text-left p-3 rounded-xl bg-slate-950/50 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs flex items-center justify-between transition cursor-pointer"
              >
                <div className="flex items-center space-x-2.5">
                  <FileText className="w-4 h-4 text-purple-400" />
                  <div>
                    <span className="font-semibold block text-white">Full Audit Investigation</span>
                    <span className="text-[11px] text-slate-500">Filter, search & compliance export</span>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500" />
              </button>

              <button
                onClick={() => navigate('/notifications')}
                className="w-full text-left p-3 rounded-xl bg-slate-950/50 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs flex items-center justify-between transition cursor-pointer"
              >
                <div className="flex items-center space-x-2.5">
                  <Bell className="w-4 h-4 text-blue-400" />
                  <div>
                    <span className="font-semibold block text-white">Notification Center</span>
                    <span className="text-[11px] text-slate-500">User alerts & channel preferences</span>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500" />
              </button>

              <button
                onClick={() => navigate('/versions/compare')}
                className="w-full text-left p-3 rounded-xl bg-slate-950/50 hover:bg-slate-800 border border-slate-800 text-slate-200 text-xs flex items-center justify-between transition cursor-pointer"
              >
                <div className="flex items-center space-x-2.5">
                  <GitBranch className="w-4 h-4 text-teal-400" />
                  <div>
                    <span className="font-semibold block text-white">Version Comparator</span>
                    <span className="text-[11px] text-slate-500">Side-by-side geometric diff analysis</span>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500" />
              </button>
            </div>
          </div>

          {/* Audit Category Distribution */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur space-y-3">
            <h2 className="text-sm font-semibold text-white font-sans">Audit Activity by Domain</h2>
            <div className="space-y-1.5">
              {data &&
                Object.entries(data.audit.by_category || {}).map(([cat, count]) => (
                  <div key={cat} className="flex items-center justify-between text-xs py-1">
                    <span className="text-slate-400 font-mono text-[11px]">{cat}</span>
                    <span className="font-semibold text-white font-mono bg-slate-800 px-2 py-0.5 rounded text-[11px]">
                      {count}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
