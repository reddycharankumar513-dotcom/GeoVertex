// Phase 12 — Detail Page for a Single GeoVertex Technical 3D Identifier
// DISCLAIMER: GeoVertex Technical 3D Identifiers are NOT official ULPINs or legal ownership identifiers.

import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Hash,
  Copy,
  Check,
  AlertTriangle,
  RefreshCw,
  ShieldAlert,
  ArrowRight,
  History,
  QrCode,
  ShieldCheck,
  ChevronDown,
  ArrowLeft,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import {
  fetchIdentifierById,
  verifyIdentifier,
  supersedeIdentifier,
  retireIdentifier,
  revokeIdentifier,
} from '../api/identifier';
import type { IdentifierStatus } from '../types/identifier';
import { QRViewModal } from '../components/identifiers/QRViewModal';

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
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border ${map[status] ?? 'bg-slate-800 text-slate-300 border-slate-700'}`}>
      {status}
    </span>
  );
}

interface ActionFormProps {
  label: string;
  onSubmit: (reason: string) => void;
  isLoading: boolean;
  colorClass: string;
}

function ActionForm({ label, onSubmit, isLoading, colorClass }: ActionFormProps) {
  const [reason, setReason] = useState('');
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition border ${colorClass}`}
      >
        {label}
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="mt-2 p-3 bg-slate-950 border border-slate-700 rounded-lg space-y-2">
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason (required)..."
            rows={2}
            className="w-full px-3 py-2 text-xs bg-slate-900 border border-slate-700 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-teal-500 resize-none"
          />
          <button
            onClick={() => { if (reason.trim()) { onSubmit(reason); setOpen(false); } }}
            disabled={!reason.trim() || isLoading}
            className="px-3 py-1.5 bg-rose-700 hover:bg-rose-600 disabled:opacity-40 text-white text-xs rounded font-medium transition"
          >
            {isLoading ? 'Processing…' : 'Confirm'}
          </button>
        </div>
      )}
    </div>
  );
}

export const IdentifierDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { role } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const isOfficerOrAdmin = role === 'ADMIN' || role === 'GOVERNMENT_OFFICER';
  const isAdmin = role === 'ADMIN';

  const [copied, setCopied] = useState(false);
  const [qrOpen, setQrOpen] = useState(false);
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; message: string } | null>(null);

  const { data: identifier, isLoading, isError, error } = useQuery({
    queryKey: ['identifier', id],
    queryFn: () => fetchIdentifierById(id!),
    enabled: !!id,
  });

  const verifyMutation = useMutation({
    mutationFn: () => verifyIdentifier(id!),
    onSuccess: (data) => {
      setVerifyResult({ valid: data.valid, message: data.verification_message });
    },
  });

  const supersedeMutation = useMutation({
    mutationFn: (reason: string) => supersedeIdentifier(id!, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['identifier', id] });
    },
  });

  const retireMutation = useMutation({
    mutationFn: (reason: string) => retireIdentifier(id!, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['identifier', id] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (reason: string) => revokeIdentifier(id!, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['identifier', id] });
    },
  });

  const handleCopy = () => {
    if (identifier) {
      navigator.clipboard.writeText(identifier.identifier_value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
        <RefreshCw className="w-8 h-8 animate-spin text-teal-500" />
        <span>Loading identifier…</span>
      </div>
    );
  }

  if (isError || !identifier) {
    return (
      <div className="p-8 text-center text-red-400">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
        <p>{(error as Error)?.message || 'Identifier not found'}</p>
        <button onClick={() => navigate('/identifiers')} className="mt-3 text-sm text-teal-400 underline">
          Back to Registry
        </button>
      </div>
    );
  }

  const h = identifier.hierarchy;

  const mutationError =
    supersedeMutation.error || retireMutation.error || revokeMutation.error;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 text-slate-100">
      {/* Back link */}
      <Link
        to="/identifiers"
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-teal-400 transition"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Registry
      </Link>

      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Hash className="w-5 h-5 text-teal-400" />
              <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                GeoVertex Technical 3D Identifier
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-2xl text-teal-300 tracking-wide break-all">
                {identifier.identifier_value}
              </span>
              <button
                onClick={handleCopy}
                title="Copy identifier"
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-teal-300 transition shrink-0"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <StatusBadge status={identifier.status} />
        </div>
      </div>

      {/* Disclaimer */}
      <div className="flex items-start gap-3 p-4 bg-slate-900 border border-amber-500/30 rounded-xl text-slate-300">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-xs leading-relaxed">
          <span className="font-semibold text-amber-300">Important: </span>
          This is a <strong>GeoVertex Technical 3D Identifier</strong> — NOT an official ULPIN or legal
          property identifier. It is for GeoVertex system use only and carries no legal ownership significance.
        </p>
      </div>

      {/* Mutation error */}
      {mutationError && (
        <div className="flex items-center gap-2 p-3 bg-red-950/40 border border-red-500/30 rounded-lg text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {(mutationError as Error).message}
        </div>
      )}

      {/* Verify result */}
      {verifyResult && (
        <div className={`flex items-start gap-3 p-4 rounded-xl border text-sm ${verifyResult.valid ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300' : 'bg-red-950/30 border-red-500/30 text-red-300'}`}>
          <ShieldCheck className="w-5 h-5 shrink-0 mt-0.5" />
          <p><strong>{verifyResult.valid ? 'VALID' : 'INVALID'}</strong> — {verifyResult.message}</p>
        </div>
      )}

      {/* Info cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: 'Scheme', value: identifier.scheme_code ?? '—' },
          { label: 'Entity Type', value: identifier.entity_type },
          { label: 'Version', value: String(identifier.version) },
          { label: 'Entity ID', value: identifier.entity_id ? `${identifier.entity_id.slice(0, 12)}…` : '—' },
          { label: 'Issued At', value: identifier.issued_at ? new Date(identifier.issued_at).toLocaleString() : '—' },
          { label: 'Issued By', value: identifier.issued_by ?? '—' },
        ].map(({ label, value }) => (
          <div key={label} className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
            <span className="text-slate-500 text-xs font-medium block">{label}</span>
            <span className="text-sm font-mono text-slate-200 mt-1 block break-all">{value}</span>
          </div>
        ))}
      </div>

      {/* Hierarchy panel */}
      {h && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Hierarchy Components</h3>
          <div className="flex flex-col gap-1">
            {(
              [
                { label: 'Jurisdiction', component: h.jurisdiction_component, id: h.jurisdiction_id },
                { label: 'Parcel', component: h.parcel_component, id: h.parcel_id },
                { label: 'Building', component: h.building_component, id: h.building_id },
                { label: 'Floor', component: h.floor_component, id: h.floor_id },
                { label: 'Unit', component: h.unit_component, id: h.unit_id },
              ] as const
            )
              .filter(({ component }) => !!component)
              .map(({ label, component, id: eid }, idx, arr) => (
                <React.Fragment key={label}>
                  <div className="flex items-center gap-3 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg">
                    <span className="text-xs text-slate-500 w-20 shrink-0 font-medium">{label}</span>
                    <span className="font-mono text-teal-300 text-sm">{component}</span>
                    {eid && (
                      <span className="text-xs text-slate-500 font-mono ml-auto">
                        {eid.slice(0, 8)}…
                      </span>
                    )}
                  </div>
                  {idx < arr.length - 1 && (
                    <div className="flex justify-center">
                      <ArrowRight className="w-4 h-4 text-slate-700 rotate-90" />
                    </div>
                  )}
                </React.Fragment>
              ))}
          </div>
        </div>
      )}

      {/* Supersession chain */}
      {(identifier.supersedes_identifier_id || identifier.superseded_by_identifier_id) && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Supersession Chain</h3>
          <div className="space-y-2">
            {identifier.supersedes_identifier_id && (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span className="text-slate-500">Supersedes:</span>
                <Link
                  to={`/identifiers/${identifier.supersedes_identifier_id}`}
                  className="font-mono text-teal-400 hover:underline"
                >
                  {identifier.supersedes_identifier_id.slice(0, 16)}…
                </Link>
              </div>
            )}
            {identifier.superseded_by_identifier_id && (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span className="text-slate-500">Superseded by:</span>
                <Link
                  to={`/identifiers/${identifier.superseded_by_identifier_id}`}
                  className="font-mono text-teal-400 hover:underline"
                >
                  {identifier.superseded_by_identifier_id.slice(0, 16)}…
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">Actions</h3>
        <div className="flex flex-wrap gap-3">
          {/* QR Code - all roles */}
          <button
            onClick={() => setQrOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition border bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-teal-300"
          >
            <QrCode className="w-3.5 h-3.5" />
            View QR Code
          </button>

          {/* Verify - all roles */}
          <button
            onClick={() => verifyMutation.mutate()}
            disabled={verifyMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition border bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-emerald-300 disabled:opacity-50"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            {verifyMutation.isPending ? 'Verifying…' : 'Verify'}
          </button>

          {/* History - all roles */}
          <Link
            to={`/identifiers/${id}/history`}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition border bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-blue-300"
          >
            <History className="w-3.5 h-3.5" />
            View History
          </Link>

          {/* Supersede - officer/admin */}
          {isOfficerOrAdmin && identifier.status === 'ACTIVE' && (
            <ActionForm
              label="Supersede"
              onSubmit={(reason) => supersedeMutation.mutate(reason)}
              isLoading={supersedeMutation.isPending}
              colorClass="bg-slate-800 border-yellow-500/40 text-yellow-400 hover:bg-slate-700"
            />
          )}

          {/* Retire - officer/admin */}
          {isOfficerOrAdmin && identifier.status === 'ACTIVE' && (
            <ActionForm
              label="Retire"
              onSubmit={(reason) => retireMutation.mutate(reason)}
              isLoading={retireMutation.isPending}
              colorClass="bg-slate-800 border-slate-500/40 text-slate-400 hover:bg-slate-700"
            />
          )}

          {/* Revoke - admin only */}
          {isAdmin && (
            <ActionForm
              label="Revoke"
              onSubmit={(reason) => revokeMutation.mutate(reason)}
              isLoading={revokeMutation.isPending}
              colorClass="bg-slate-800 border-red-500/40 text-red-400 hover:bg-slate-700"
            />
          )}
        </div>
      </div>

      {/* QR Modal */}
      <QRViewModal
        isOpen={qrOpen}
        onClose={() => setQrOpen(false)}
        identifierId={identifier.id}
        identifierValue={identifier.identifier_value}
      />
    </div>
  );
};
