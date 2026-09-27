// Phase 12 — Scheme Management Page (Admin Only)
// DISCLAIMER: GeoVertex Technical 3D Identifiers are NOT official ULPINs or legal ownership identifiers.

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings,
  AlertTriangle,
  RefreshCw,
  Plus,
  CheckCircle2,
  XCircle,
  ToggleLeft,
  ToggleRight,
  ShieldAlert,
} from 'lucide-react';
import { fetchSchemes, createScheme, patchScheme } from '../api/identifier';
import type { IdentifierScheme } from '../types/identifier';

type CreateForm = Pick<
  IdentifierScheme,
  'scheme_code' | 'name' | 'version' | 'prefix' | 'separator'
>;

const DEFAULT_FORM: CreateForm = {
  scheme_code: '',
  name: '',
  version: 1,
  prefix: 'GV',
  separator: '-',
};

export const SchemeManagementPage: React.FC = () => {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateForm>(DEFAULT_FORM);

  const { data: schemes, isLoading, isError, error } = useQuery({
    queryKey: ['identifier-schemes'],
    queryFn: fetchSchemes,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      patchScheme(id, { active }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['identifier-schemes'] });
    },
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createScheme({
        ...form,
        jurisdiction_component: '',
        parcel_component: '',
        building_component: '',
        floor_component: '',
        unit_component: '',
        padding_rules: {},
        checksum_enabled: false,
        active: false,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['identifier-schemes'] });
      setShowCreate(false);
      setForm(DEFAULT_FORM);
    },
  });

  const activeScheme = schemes?.find((s) => s.active);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Settings className="w-7 h-7 text-teal-400" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Identifier Scheme Management</h1>
            <p className="text-slate-400 text-sm mt-0.5">
              Admin — configure GeoVertex Technical 3D Identifier encoding schemes
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowCreate((s) => !s)}
          className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-sm font-medium transition"
        >
          <Plus className="w-4 h-4" />
          {showCreate ? 'Cancel' : 'Create New Scheme'}
        </button>
      </div>

      {/* Disclaimer */}
      <div className="flex items-start gap-3 p-4 bg-slate-900 border border-amber-500/30 rounded-xl text-slate-300">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-xs leading-relaxed">
          <span className="font-semibold text-amber-300">Disclaimer: </span>
          GeoVertex Technical 3D Identifiers — NOT official ULPINs or legal ownership identifiers.
          Changing the active scheme affects all future identifier generation.
        </p>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">Create New Scheme</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {(
              [
                { key: 'scheme_code', label: 'Scheme Code', placeholder: 'e.g. GV-2026' },
                { key: 'name', label: 'Name', placeholder: 'e.g. GeoVertex Standard 2026' },
                { key: 'prefix', label: 'Prefix', placeholder: 'e.g. GV' },
                { key: 'separator', label: 'Separator', placeholder: 'e.g. -' },
              ] as const
            ).map(({ key, label, placeholder }) => (
              <div key={key} className="space-y-1">
                <label className="text-xs font-medium text-slate-400">{label}</label>
                <input
                  type="text"
                  value={form[key]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                  placeholder={placeholder}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>
            ))}
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-400">Version</label>
              <input
                type="number"
                value={form.version}
                onChange={(e) => setForm((f) => ({ ...f, version: Number(e.target.value) }))}
                min={1}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
            </div>
          </div>

          {createMutation.isError && (
            <div className="flex items-center gap-2 p-3 bg-red-950/40 border border-red-500/30 rounded-lg text-red-400 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              {(createMutation.error as Error).message}
            </div>
          )}

          <button
            onClick={() => createMutation.mutate()}
            disabled={!form.scheme_code.trim() || !form.name.trim() || createMutation.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-500 disabled:opacity-40 text-white rounded-lg text-sm font-medium transition"
          >
            {createMutation.isPending ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            {createMutation.isPending ? 'Creating…' : 'Create Scheme'}
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        {isLoading && (
          <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
            <RefreshCw className="w-8 h-8 animate-spin text-teal-500" />
            <span>Loading schemes…</span>
          </div>
        )}
        {isError && (
          <div className="p-8 text-center text-red-400">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
            <p>{(error as Error)?.message}</p>
          </div>
        )}
        {schemes && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/70 border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 px-4">Code</th>
                  <th className="py-3.5 px-4">Name</th>
                  <th className="py-3.5 px-4">Version</th>
                  <th className="py-3.5 px-4">Prefix / Sep</th>
                  <th className="py-3.5 px-4">Effective From</th>
                  <th className="py-3.5 px-4">Effective To</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Toggle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {schemes.map((scheme) => {
                  const isActive = scheme.active;
                  const isCurrent = scheme.id === activeScheme?.id;
                  return (
                    <tr
                      key={scheme.id}
                      className={`hover:bg-slate-800/30 transition ${isCurrent ? 'bg-teal-500/5 border-l-2 border-teal-500/50' : ''}`}
                    >
                      <td className="py-3.5 px-4 font-mono font-semibold text-teal-300">
                        {scheme.scheme_code}
                        {isCurrent && (
                          <span className="ml-2 text-xs bg-teal-500/10 text-teal-400 border border-teal-500/20 rounded px-1.5 py-0.5">
                            Current
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">{scheme.name}</td>
                      <td className="py-3.5 px-4 font-mono">v{scheme.version}</td>
                      <td className="py-3.5 px-4 font-mono text-slate-400">
                        {scheme.prefix}
                        <span className="text-slate-600 mx-1">|</span>
                        "{scheme.separator}"
                      </td>
                      <td className="py-3.5 px-4 text-xs text-slate-400">
                        {scheme.effective_from
                          ? new Date(scheme.effective_from).toLocaleDateString()
                          : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-xs text-slate-400">
                        {scheme.effective_to
                          ? new Date(scheme.effective_to).toLocaleDateString()
                          : '—'}
                      </td>
                      <td className="py-3.5 px-4">
                        {isActive ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            <CheckCircle2 className="w-3 h-3" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-500 border border-slate-700">
                            <XCircle className="w-3 h-3" /> Inactive
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => toggleMutation.mutate({ id: scheme.id, active: !isActive })}
                          disabled={toggleMutation.isPending}
                          title={isActive ? 'Deactivate scheme' : 'Activate scheme'}
                          className="p-1.5 rounded-lg hover:bg-slate-700 transition text-slate-400 hover:text-teal-400 disabled:opacity-40"
                        >
                          {isActive ? (
                            <ToggleRight className="w-5 h-5 text-teal-400" />
                          ) : (
                            <ToggleLeft className="w-5 h-5" />
                          )}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
