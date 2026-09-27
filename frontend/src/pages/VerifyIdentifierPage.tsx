// Phase 12 — Public Verification Page for GeoVertex Technical 3D Identifiers
// Accessible at /verify/:token (public token) and /identifiers/verify (manual input)
// Works without authentication for token-based checks.

import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShieldCheck,
  ShieldAlert,
  Search,
  RefreshCw,
  AlertTriangle,
  Hash,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';
import { verifyByToken, verifyIdentifier } from '../api/identifier';
import type { VerificationResult } from '../types/identifier';

/** Determine whether `input` looks like a UUID (entity identifier) or a short token. */
function isUUID(s: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s.trim());
}

function ResultBanner({ result }: { result: VerificationResult }) {
  const status = result.status?.toUpperCase() ?? (result.valid ? 'ACTIVE' : 'UNKNOWN');

  const config: Record<
    string,
    { bg: string; border: string; text: string; icon: React.ReactNode }
  > = {
    ACTIVE: {
      bg: 'bg-emerald-950/40',
      border: 'border-emerald-500/40',
      text: 'text-emerald-300',
      icon: <CheckCircle2 className="w-8 h-8 text-emerald-400" />,
    },
    VALID: {
      bg: 'bg-emerald-950/40',
      border: 'border-emerald-500/40',
      text: 'text-emerald-300',
      icon: <CheckCircle2 className="w-8 h-8 text-emerald-400" />,
    },
    INVALID: {
      bg: 'bg-red-950/40',
      border: 'border-red-500/40',
      text: 'text-red-300',
      icon: <XCircle className="w-8 h-8 text-red-400" />,
    },
    REVOKED: {
      bg: 'bg-red-950/40',
      border: 'border-red-500/40',
      text: 'text-red-300',
      icon: <XCircle className="w-8 h-8 text-red-400" />,
    },
    RETIRED: {
      bg: 'bg-slate-800/60',
      border: 'border-slate-500/30',
      text: 'text-slate-300',
      icon: <Clock className="w-8 h-8 text-slate-400" />,
    },
    SUPERSEDED: {
      bg: 'bg-yellow-950/40',
      border: 'border-yellow-500/40',
      text: 'text-yellow-300',
      icon: <AlertTriangle className="w-8 h-8 text-yellow-400" />,
    },
  };

  const key = !result.valid ? 'INVALID' : (config[status] ? status : 'ACTIVE');
  const c = config[key] ?? config['INVALID'];

  return (
    <div className={`${c.bg} border ${c.border} rounded-2xl p-6 space-y-4`}>
      {/* Status */}
      <div className="flex items-center gap-3">
        {c.icon}
        <div>
          <p className={`text-2xl font-bold ${c.text}`}>
            {result.valid ? (status === 'SUPERSEDED' ? 'SUPERSEDED' : status === 'RETIRED' ? 'RETIRED' : 'VALID') : 'INVALID'}
          </p>
          <p className="text-sm text-slate-400 mt-0.5">{result.verification_message}</p>
        </div>
      </div>

      {/* Details */}
      {result.identifier_value && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          {[
            { label: 'Identifier Value', value: result.identifier_value, mono: true },
            { label: 'Entity Type', value: result.entity_type },
            { label: 'Scheme', value: result.scheme_code },
            { label: 'Issued At', value: result.issued_at ? new Date(result.issued_at).toLocaleString() : undefined },
          ]
            .filter(({ value }) => !!value)
            .map(({ label, value, mono }) => (
              <div key={label} className="bg-slate-950/50 border border-slate-800 rounded-xl p-3">
                <span className="text-xs text-slate-500 font-medium block">{label}</span>
                <span className={`text-sm mt-1 block break-all ${mono ? 'font-mono text-teal-300' : 'text-slate-200'}`}>
                  {value}
                </span>
              </div>
            ))}
        </div>
      )}

      {/* Hierarchy */}
      {result.hierarchy && (
        <div className="pt-2 space-y-1">
          <p className="text-xs text-slate-500 font-medium">Hierarchy</p>
          <div className="flex flex-wrap gap-2">
            {(
              [
                ['Jurisdiction', result.hierarchy.jurisdiction_component],
                ['Parcel', result.hierarchy.parcel_component],
                ['Building', result.hierarchy.building_component],
                ['Floor', result.hierarchy.floor_component],
                ['Unit', result.hierarchy.unit_component],
              ] as [string, string | undefined][]
            )
              .filter(([, v]) => !!v)
              .map(([label, value], idx, arr) => (
                <React.Fragment key={label}>
                  <span className="flex items-center gap-1 text-xs bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 font-mono">
                    <span className="text-slate-500">{label}:</span>
                    <span className="text-teal-300">{value}</span>
                  </span>
                  {idx < arr.length - 1 && (
                    <ArrowRight className="w-3 h-3 text-slate-600 self-center" />
                  )}
                </React.Fragment>
              ))}
          </div>
        </div>
      )}

      {/* Disclaimer from API */}
      {result.disclaimer && (
        <div className="flex items-start gap-2 text-xs text-slate-400 bg-slate-950/60 border border-amber-500/20 rounded-lg p-3 mt-2">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
          <p>{result.disclaimer}</p>
        </div>
      )}
    </div>
  );
}

export const VerifyIdentifierPage: React.FC = () => {
  const { token: routeToken } = useParams<{ token?: string }>();

  const [input, setInput] = useState(routeToken ?? '');
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<VerificationResult | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  const doVerify = async (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    setIsVerifying(true);
    setVerifyResult(null);
    setVerifyError(null);
    try {
      let result: VerificationResult;
      if (isUUID(trimmed)) {
        result = await verifyIdentifier(trimmed);
      } else {
        result = await verifyByToken(trimmed);
      }
      setVerifyResult(result);
    } catch (err: unknown) {
      setVerifyError((err as Error)?.message ?? 'Verification failed');
    } finally {
      setIsVerifying(false);
    }
  };

  // Auto-verify if token comes from route params
  useEffect(() => {
    if (routeToken) {
      doVerify(routeToken);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeToken]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    doVerify(input);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center px-4 py-12">
      <div className="w-full max-w-2xl space-y-6">
        {/* Brand */}
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="w-14 h-14 rounded-2xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center">
            <ShieldCheck className="w-7 h-7 text-teal-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Identifier Verification</h1>
            <p className="text-slate-400 text-sm mt-1">
              GeoVertex Technical 3D Identifier public verification portal
            </p>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="flex items-start gap-3 p-4 bg-slate-900 border border-amber-500/30 rounded-xl text-slate-300">
          <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-xs leading-relaxed">
            <span className="font-semibold text-amber-300">Disclaimer: </span>
            GeoVertex Technical 3D Identifiers are NOT official ULPINs or legal ownership identifiers.
            Verification confirms system-level validity only.
          </p>
        </div>

        {/* Input form */}
        <form
          onSubmit={handleSubmit}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3"
        >
          <label className="text-xs font-medium text-slate-400">
            Enter Identifier Token or UUID
          </label>
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Hash className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Paste identifier token, UUID, or scan QR…"
                className="w-full pl-9 pr-4 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 font-mono focus:outline-none focus:ring-1 focus:ring-teal-500"
                autoFocus={!routeToken}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isVerifying}
              className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-500 disabled:opacity-40 text-white rounded-lg text-sm font-medium transition"
            >
              {isVerifying ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              {isVerifying ? 'Verifying…' : 'Verify'}
            </button>
          </div>
          <p className="text-xs text-slate-500">
            Paste a GeoVertex identifier token or UUID.
            {isUUID(input) ? (
              <span className="ml-1 text-teal-400">→ Will verify as UUID</span>
            ) : input.trim() ? (
              <span className="ml-1 text-blue-400">→ Will verify as public token</span>
            ) : null}
          </p>
        </form>

        {/* Error */}
        {verifyError && (
          <div className="flex items-center gap-3 p-4 bg-red-950/40 border border-red-500/30 rounded-xl text-red-400 text-sm">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            {verifyError}
          </div>
        )}

        {/* Result */}
        {verifyResult && <ResultBanner result={verifyResult} />}

        {/* Link back */}
        <div className="text-center">
          <Link to="/identifiers" className="text-xs text-slate-500 hover:text-teal-400 transition">
            ← Browse Identifier Registry
          </Link>
        </div>
      </div>
    </div>
  );
};
