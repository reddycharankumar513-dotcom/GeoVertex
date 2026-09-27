import React, { useEffect, useState } from 'react';
import {
  ValidationIssue,
  ValidationRule,
  ValidationRun,
  ValidationSeverity,
} from '../../types/validation';
import { validationApi } from '../../api/validation';
import { ValidationIssueDetailModal } from '../../features/validation/ValidationIssueDetailModal';
import { ValidationRunCreateModal } from '../../features/validation/ValidationRunCreateModal';
import { useAuth } from '../../auth/AuthContext';

export const ValidationDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'ISSUES' | 'RUNS' | 'RULES'>('ISSUES');

  // State
  const [runs, setRuns] = useState<ValidationRun[]>([]);
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [rules, setRules] = useState<ValidationRule[]>([]);
  const [loading, setLoading] = useState(false);

  // Filters for issues
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('OPEN');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals
  const [selectedIssue, setSelectedIssue] = useState<ValidationIssue | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Load initial data
  const fetchData = async () => {
    setLoading(true);
    try {
      const [runsData, issuesData, rulesData] = await Promise.all([
        validationApi.listRuns({ limit: 50 }),
        validationApi.listIssues({
          severity: severityFilter || undefined,
          status: statusFilter || undefined,
          category: categoryFilter || undefined,
          limit: 100,
        }),
        validationApi.listRules(),
      ]);
      setRuns(runsData);
      setIssues(issuesData);
      setRules(rulesData);
    } catch (err) {
      console.error('Error fetching validation data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Polling for background job completion
    return () => clearInterval(interval);
  }, [severityFilter, statusFilter, categoryFilter]);

  // Aggregate KPI metrics
  const totalIssuesCount = issues.length;
  const criticalCount = issues.filter((i) => i.severity === 'CRITICAL').length;
  const errorCount = issues.filter((i) => i.severity === 'ERROR').length;
  const warningCount = issues.filter((i) => i.severity === 'WARNING').length;
  const infoCount = issues.filter((i) => i.severity === 'INFO').length;
  const openCount = issues.filter((i) => i.status === 'OPEN').length;
  const resolvedCount = issues.filter((i) => i.status === 'RESOLVED').length;

  const handleIssueClick = (issue: ValidationIssue) => {
    setSelectedIssue(issue);
    setIsDetailModalOpen(true);
  };

  const handleIssueUpdated = (updated: ValidationIssue) => {
    setIssues((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
    setSelectedIssue(updated);
  };

  const filteredIssues = issues.filter((i) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      i.issue_code.toLowerCase().includes(q) ||
      i.rule_id.toLowerCase().includes(q) ||
      i.message.toLowerCase().includes(q) ||
      i.entity_id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
            <span>🛡️ Topology Validation & Spatial Consistency Engine</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic spatial rules, cross-dataset discrepancies, vertical stacking checks, and human-in-the-loop review.
          </p>
        </div>

        {user?.role !== 'CITIZEN' && (
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow flex items-center space-x-2 transition self-start sm:self-auto"
          >
            <span>+ Dispatch Validation Run</span>
          </button>
        )}
      </div>

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Issues</span>
          <div className="text-xl font-bold text-white mt-1">{totalIssuesCount}</div>
        </div>
        <div className="p-3 bg-rose-950/40 border border-rose-900/60 rounded-lg">
          <span className="text-[10px] text-rose-300 uppercase font-semibold">Critical</span>
          <div className="text-xl font-bold text-rose-400 mt-1">{criticalCount}</div>
        </div>
        <div className="p-3 bg-red-950/40 border border-red-900/60 rounded-lg">
          <span className="text-[10px] text-red-300 uppercase font-semibold">Errors</span>
          <div className="text-xl font-bold text-red-400 mt-1">{errorCount}</div>
        </div>
        <div className="p-3 bg-amber-950/40 border border-amber-900/60 rounded-lg">
          <span className="text-[10px] text-amber-300 uppercase font-semibold">Warnings</span>
          <div className="text-xl font-bold text-amber-400 mt-1">{warningCount}</div>
        </div>
        <div className="p-3 bg-blue-950/40 border border-blue-900/60 rounded-lg">
          <span className="text-[10px] text-blue-300 uppercase font-semibold">Info</span>
          <div className="text-xl font-bold text-blue-400 mt-1">{infoCount}</div>
        </div>
        <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
          <span className="text-[10px] text-amber-400 uppercase font-semibold">Open Queue</span>
          <div className="text-xl font-bold text-amber-300 mt-1">{openCount}</div>
        </div>
        <div className="p-3 bg-emerald-950/40 border border-emerald-900/60 rounded-lg">
          <span className="text-[10px] text-emerald-300 uppercase font-semibold">Resolved</span>
          <div className="text-xl font-bold text-emerald-400 mt-1">{resolvedCount}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-800 flex space-x-6 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('ISSUES')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition ${
            activeTab === 'ISSUES'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Validation Issues</span>
          <span className="px-1.5 py-0.5 rounded-full bg-slate-800 text-[10px] text-slate-300">
            {issues.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('RUNS')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition ${
            activeTab === 'RUNS'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Validation Runs</span>
          <span className="px-1.5 py-0.5 rounded-full bg-slate-800 text-[10px] text-slate-300">
            {runs.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('RULES')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition ${
            activeTab === 'RULES'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Rule Catalogue</span>
          <span className="px-1.5 py-0.5 rounded-full bg-slate-800 text-[10px] text-slate-300">
            {rules.length}
          </span>
        </button>
      </div>

      {/* TAB 1: ISSUES */}
      {activeTab === 'ISSUES' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex flex-wrap items-center gap-3 text-xs">
            <input
              type="text"
              placeholder="Search by code, rule, entity ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1 text-slate-200 placeholder-slate-500 text-xs w-60 focus:outline-none focus:border-sky-500"
            />

            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1 text-slate-200 text-xs focus:outline-none focus:border-sky-500"
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="ERROR">ERROR</option>
              <option value="WARNING">WARNING</option>
              <option value="INFO">INFO</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1 text-slate-200 text-xs focus:outline-none focus:border-sky-500"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">OPEN</option>
              <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="WAIVED">WAIVED</option>
            </select>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1 text-slate-200 text-xs focus:outline-none focus:border-sky-500"
            >
              <option value="">All Categories</option>
              <option value="GEOMETRY">GEOMETRY</option>
              <option value="PARCEL">PARCEL</option>
              <option value="BUILDING">BUILDING</option>
              <option value="FLOOR">FLOOR</option>
              <option value="UNIT">UNIT</option>
              <option value="VERTICAL">VERTICAL</option>
              <option value="CROSS_DATASET">CROSS_DATASET</option>
              <option value="AI">AI</option>
              <option value="SURVEY">SURVEY</option>
              <option value="CRS">CRS</option>
            </select>

            <div className="ml-auto text-slate-500 text-[11px]">
              Showing {filteredIssues.length} of {issues.length} findings
            </div>
          </div>

          {/* Issues Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800/80 text-slate-400 font-semibold border-b border-slate-700 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="p-3">Severity</th>
                  <th className="p-3">Issue Code</th>
                  <th className="p-3">Rule / Category</th>
                  <th className="p-3">Entity Target</th>
                  <th className="p-3">Technical Finding</th>
                  <th className="p-3">Measured vs Expected</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {filteredIssues.map((issue) => (
                  <tr
                    key={issue.id}
                    onClick={() => handleIssueClick(issue)}
                    className="hover:bg-slate-800/50 cursor-pointer transition"
                  >
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          issue.severity === 'CRITICAL'
                            ? 'bg-rose-950 text-rose-300 border border-rose-800'
                            : issue.severity === 'ERROR'
                            ? 'bg-red-950 text-red-300 border border-red-800'
                            : issue.severity === 'WARNING'
                            ? 'bg-amber-950 text-amber-300 border border-amber-800'
                            : 'bg-blue-950 text-blue-300 border border-blue-800'
                        }`}
                      >
                        {issue.severity}
                      </span>
                    </td>
                    <td className="p-3 font-mono text-sky-400 font-medium">{issue.issue_code}</td>
                    <td className="p-3">
                      <div className="font-medium text-white">{issue.rule_id}</div>
                      <div className="text-[10px] text-slate-500">{issue.category}</div>
                    </td>
                    <td className="p-3 font-mono text-slate-400">
                      {issue.entity_type} ({issue.entity_id.slice(0, 8)}...)
                    </td>
                    <td className="p-3 max-w-xs truncate text-slate-300" title={issue.message}>
                      {issue.message}
                    </td>
                    <td className="p-3 font-mono text-[11px] text-slate-400">
                      {issue.measured_value ? (
                        <span>
                          <span className="text-rose-400">{issue.measured_value}</span>
                          {issue.expected_value && <span className="text-slate-500"> / {issue.expected_value}</span>}
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          issue.status === 'OPEN'
                            ? 'bg-amber-500/10 text-amber-400'
                            : issue.status === 'ACKNOWLEDGED'
                            ? 'bg-blue-500/10 text-blue-400'
                            : issue.status === 'RESOLVED'
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : 'bg-purple-500/10 text-purple-400'
                        }`}
                      >
                        {issue.status}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleIssueClick(issue);
                        }}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
                {filteredIssues.length === 0 && (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-slate-500 text-xs">
                      No topology validation issues matching selected filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: RUNS */}
      {activeTab === 'RUNS' && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/80 text-slate-400 font-semibold border-b border-slate-700 uppercase tracking-wider text-[10px]">
              <tr>
                <th className="p-3">Run ID</th>
                <th className="p-3">Scope / Target</th>
                <th className="p-3">Status / Stage</th>
                <th className="p-3">Duration</th>
                <th className="p-3">Rules Executed</th>
                <th className="p-3">Issues Discovered</th>
                <th className="p-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {runs.map((r) => (
                <tr key={r.id} className="hover:bg-slate-800/50">
                  <td className="p-3 font-mono text-sky-400 font-medium">{r.id.slice(0, 8)}...</td>
                  <td className="p-3">
                    <span className="font-semibold text-white">{r.target_type}</span>
                    {r.target_id && <span className="text-slate-400 font-mono ml-1.5">({r.target_id.slice(0, 8)}...)</span>}
                  </td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        r.status === 'COMPLETED'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                          : r.status === 'RUNNING'
                          ? 'bg-blue-950 text-blue-300 border border-blue-800 animate-pulse'
                          : r.status === 'FAILED'
                          ? 'bg-rose-950 text-rose-300 border border-rose-800'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {r.status} ({r.stage})
                    </span>
                  </td>
                  <td className="p-3 font-mono text-slate-400">{r.duration_ms ? `${r.duration_ms} ms` : '-'}</td>
                  <td className="p-3 font-mono text-slate-300">{r.summary?.rules_executed || 0}</td>
                  <td className="p-3">
                    <span className="font-bold text-rose-400">{r.summary?.total_issues || 0}</span>
                    <span className="text-slate-500 ml-1.5 text-[11px]">
                      ({r.summary?.critical || 0} crit, {r.summary?.errors || 0} err)
                    </span>
                  </td>
                  <td className="p-3 text-slate-400">{new Date(r.created_at).toLocaleTimeString()}</td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-500 text-xs">
                    No validation runs recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB 3: RULES */}
      {activeTab === 'RULES' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rules.map((rule) => (
            <div key={rule.rule_id} className="p-4 bg-slate-900 border border-slate-800 rounded-lg space-y-2">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-sky-400 font-mono">
                  {rule.category}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    rule.severity === 'CRITICAL'
                      ? 'bg-rose-950 text-rose-300 border border-rose-800'
                      : rule.severity === 'ERROR'
                      ? 'bg-red-950 text-red-300 border border-red-800'
                      : 'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}
                >
                  {rule.severity}
                </span>
              </div>
              <h3 className="font-semibold text-white text-sm">{rule.name}</h3>
              <div className="font-mono text-xs text-slate-500">{rule.rule_id} (v{rule.rule_version})</div>
              <p className="text-xs text-slate-400 leading-relaxed">{rule.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      <ValidationIssueDetailModal
        isOpen={isDetailModalOpen}
        issue={selectedIssue}
        onClose={() => setIsDetailModalOpen(false)}
        onIssueUpdated={handleIssueUpdated}
        userRole={user?.role}
      />

      {/* Create Run Modal */}
      <ValidationRunCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onRunCreated={fetchData}
      />
    </div>
  );
};
