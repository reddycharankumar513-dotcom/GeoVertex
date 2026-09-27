// Phase 12 — Technical 3D Property Identifier Engine: Registry / List Page
// DISCLAIMER: GeoVertex Technical 3D Identifiers are NOT official ULPINs or legal ownership identifiers.

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Hash,
  Search,
  RefreshCw,
  Plus,
  AlertTriangle,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  BarChart3,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { fetchIdentifiers, fetchIdentifierStatistics } from '../api/identifier';
import type { IdentifierStatus, IdentifierEntityType, PaginatedIdentifiers, IdentifierStatistics } from '../types/identifier';

const PAGE_SIZE = 50;

function StatusBadge({ status }: { status: IdentifierStatus }) {
  const map: Record<IdentifierStatus, string> = {
    ACTIVE:     'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    SUPERSEDED: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    RETIRED:    'bg-slate-700/60 text-slate-400 border-slate-600/40',
    REVOKED:    'bg-red-500/10 text-red-400 border-red-500/20',
    DRAFT:      'bg-blue-500/10 text-blue-400 border-blue-500/20',
    SUSPENDED:  'bg-orange-500/10 text-orange-400 border-orange-500/20',
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${map[status] ?? 'bg-slate-800 text-slate-300 border-slate-700'}`}>
      {status}
    </span>
  );
}

export const IdentifierRegistryPage: React.FC = () => {
  const { role } = useAuth();
  const navigate = useNavigate();
  const isOfficerOrAdmin = role === 'ADMIN' || role === 'GOVERNMENT_OFFICER';

  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');

  const { data: stats } = useQuery<IdentifierStatistics>({
    queryKey: ['identifier-statistics'],
    queryFn: fetchIdentifierStatistics,
    staleTime: 30_000,
  });

  const { data, isLoading, isError, error, refetch } = useQuery<PaginatedIdentifiers>({
    queryKey: ['identifiers', page, statusFilter, entityTypeFilter, search],
    queryFn: () =>
      fetchIdentifiers({
        status: statusFilter || undefined,
        entity_type: entityTypeFilter || undefined,
        search: search || undefined,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    placeholderData: (prev) => prev,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(0);
  };

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Hash className="w-7 h-7 text-teal-400" />
            <h1 className="text-2xl font-bold tracking-tight">Technical 3D Identifier Registry</h1>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            GeoVertex Phase 12 — 3D property identifier management engine
          </p>
        </div>
        {isOfficerOrAdmin && (
          <Link
            to="/identifiers/generate"
            className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-teal-600/20"
          >
            <Plus className="w-4 h-4" />
            Generate New Identifier
          </Link>
        )}
      </div>

      {/* Disclaimer banner */}
      <div className="flex items-start gap-3 p-4 bg-slate-900 border border-amber-500/30 rounded-xl text-slate-300">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-xs leading-relaxed">
          <span className="font-semibold text-amber-300">Disclaimer: </span>
          GeoVertex Technical 3D Identifiers — NOT official ULPINs or legal ownership identifiers.
          These are internal technical reference codes for the GeoVertex 3D cadastral system only.
        </p>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {(
            [
              { label: 'Total', value: stats.total, color: 'text-white' },
              { label: 'Active', value: stats.active, color: 'text-emerald-400' },
              { label: 'Superseded', value: stats.superseded, color: 'text-yellow-400' },
              { label: 'Retired', value: stats.retired, color: 'text-slate-400' },
              { label: 'Revoked', value: stats.revoked, color: 'text-red-400' },
              { label: 'Draft', value: stats.draft, color: 'text-blue-400' },
            ] as const
          ).map(({ label, value, color }) => (
            <div key={label} className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
              <span className="text-slate-500 text-xs font-medium block">{label}</span>
              <span className={`text-xl font-bold mt-1 block ${color}`}>{value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row items-center gap-3">
        <form onSubmit={handleSearch} className="relative flex-1 w-full flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search identifier value..."
              className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-sm font-medium transition"
          >
            Search
          </button>
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
            className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-teal-500"
          >
            <option value="">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="ACTIVE">Active</option>
            <option value="SUSPENDED">Suspended</option>
            <option value="SUPERSEDED">Superseded</option>
            <option value="RETIRED">Retired</option>
            <option value="REVOKED">Revoked</option>
          </select>

          <select
            value={entityTypeFilter}
            onChange={(e) => { setEntityTypeFilter(e.target.value); setPage(0); }}
            className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-teal-500"
          >
            <option value="">All Entity Types</option>
            <option value="JURISDICTION">Jurisdiction</option>
            <option value="PARCEL">Parcel</option>
            <option value="BUILDING">Building</option>
            <option value="FLOOR">Floor</option>
            <option value="UNIT">Unit</option>
          </select>

          <button
            onClick={() => refetch()}
            className="p-2 text-slate-400 hover:text-slate-200 bg-slate-950 border border-slate-800 rounded-lg transition"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
            <RefreshCw className="w-8 h-8 animate-spin text-teal-500" />
            <span>Loading identifiers...</span>
          </div>
        ) : isError ? (
          <div className="p-8 text-center text-red-400">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-80" />
            <span>{(error as Error)?.message || 'Failed to fetch identifiers'}</span>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-12 text-center text-slate-500 flex flex-col items-center gap-2">
            <BarChart3 className="w-12 h-12 text-slate-600 stroke-[1.5]" />
            <p className="text-base font-medium text-slate-400 mt-2">No identifiers found</p>
            <p className="text-xs text-slate-500">
              Try adjusting filters or generate a new GeoVertex Technical 3D Identifier.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/70 border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Identifier Value</th>
                  <th className="py-3.5 px-4 font-semibold">Entity Type</th>
                  <th className="py-3.5 px-4 font-semibold">Status</th>
                  <th className="py-3.5 px-4 font-semibold">Scheme</th>
                  <th className="py-3.5 px-4 font-semibold">Issued Date</th>
                  <th className="py-3.5 px-4 font-semibold">Entity ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {data.items.map((identifier) => (
                  <tr
                    key={identifier.id}
                    onClick={() => navigate(`/identifiers/${identifier.id}`)}
                    className="hover:bg-slate-800/40 cursor-pointer transition"
                  >
                    <td className="py-3.5 px-4">
                      <span className="font-mono text-teal-300 text-xs tracking-wide">
                        {identifier.identifier_value}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 bg-slate-800 border border-slate-700/60 rounded text-xs text-slate-300">
                        {identifier.entity_type}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={identifier.status} />
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-400 font-mono">
                      {identifier.scheme_code ?? '—'}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-400">
                      {identifier.issued_at
                        ? new Date(identifier.issued_at).toLocaleDateString()
                        : '—'}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-500 font-mono">
                      {identifier.entity_id
                        ? `${identifier.entity_id.slice(0, 8)}…`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-400">
          <span>
            Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, data.total)} of{' '}
            {data.total} identifiers
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono text-xs">
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
