// Phase 12 — Generate Identifier Page (Officer/Admin Only)
// DISCLAIMER: GeoVertex Technical 3D Identifiers are NOT official ULPINs or legal ownership identifiers.

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Hash,
  ArrowLeft,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  ShieldAlert,
  QrCode,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import { fetchSchemes, previewIdentifier, generateIdentifier } from '../api/identifier';
import { QRViewModal } from '../components/identifiers/QRViewModal';
import type { PreviewResult, PropertyIdentifier } from '../types/identifier';

type Step = 1 | 2 | 3;
type EntityType = 'PARCEL' | 'BUILDING' | 'FLOOR' | 'UNIT';

const ENTITY_TYPES: EntityType[] = ['PARCEL', 'BUILDING', 'FLOOR', 'UNIT'];

export const GenerateIdentifierPage: React.FC = () => {
  const navigate = useNavigate();

  const [step, setStep] = useState<Step>(1);
  const [entityType, setEntityType] = useState<EntityType>('UNIT');
  const [entityId, setEntityId] = useState('');
  const [schemeId, setSchemeId] = useState('');
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [generated, setGenerated] = useState<PropertyIdentifier | null>(null);
  const [qrOpen, setQrOpen] = useState(false);

  const { data: schemes } = useQuery({
    queryKey: ['identifier-schemes'],
    queryFn: fetchSchemes,
  });

  const previewMutation = useMutation({
    mutationFn: () =>
      previewIdentifier({
        entity_type: entityType,
        entity_id: entityId.trim(),
        scheme_id: schemeId || undefined,
      }),
    onSuccess: (data) => {
      setPreview(data);
      setStep(2);
    },
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      generateIdentifier({
        entity_type: entityType,
        entity_id: entityId.trim(),
        scheme_id: schemeId || undefined,
      }),
    onSuccess: (data) => {
      setGenerated(data);
      setStep(3);
    },
  });

  const activeSchemes = schemes?.filter((s) => s.active) ?? [];

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6 text-slate-100">
      {/* Back */}
      <Link
        to="/identifiers"
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-teal-400 transition"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Registry
      </Link>

      {/* Header */}
      <div className="flex items-center gap-2">
        <Hash className="w-7 h-7 text-teal-400" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Generate Technical 3D Identifier</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Officer / Admin — Phase 12 identifier generation engine
          </p>
        </div>
      </div>

      {/* Warning banner */}
      <div className="flex items-start gap-3 p-4 bg-slate-900 border border-amber-500/40 rounded-xl text-slate-300">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-xs leading-relaxed">
          <span className="font-semibold text-amber-300">Warning: </span>
          This generates a <strong>GeoVertex Technical 3D Identifier</strong> — NOT an official ULPIN or
          legal property identifier. Generated identifiers are recorded in the system and cannot be
          quietly deleted.
        </p>
      </div>

      {/* Step breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-slate-400">
        {(['Select Entity', 'Preview', 'Confirm & Generate'] as const).map((label, idx) => {
          const s = (idx + 1) as Step;
          return (
            <React.Fragment key={label}>
              <span
                className={`font-medium ${step === s ? 'text-teal-400' : step > s ? 'text-slate-300' : 'text-slate-500'}`}
              >
                {s}. {label}
              </span>
              {idx < 2 && <ChevronRight className="w-3 h-3 text-slate-600" />}
            </React.Fragment>
          );
        })}
      </div>

      {/* ── Step 1: Select Entity ── */}
      {step === 1 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5">
          <h2 className="text-sm font-semibold text-slate-200">Step 1: Select Entity</h2>

          {/* Entity type */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-400">Entity Type</label>
            <div className="flex flex-wrap gap-2">
              {ENTITY_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => setEntityType(t)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium border transition ${
                    entityType === t
                      ? 'bg-teal-600 border-teal-500 text-white'
                      : 'bg-slate-950 border-slate-700 text-slate-300 hover:border-teal-600/50'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Entity UUID */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-400">Entity UUID</label>
            <input
              type="text"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              placeholder="Paste UUID of the parcel / building / floor / unit..."
              className="w-full px-3 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 font-mono focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
          </div>

          {/* Scheme selector */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-400">Identifier Scheme (optional)</label>
            <select
              value={schemeId}
              onChange={(e) => setSchemeId(e.target.value)}
              className="w-full px-3 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-teal-500"
            >
              <option value="">Use default active scheme</option>
              {activeSchemes.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.scheme_code}) v{s.version}
                </option>
              ))}
            </select>
          </div>

          {/* Preview button */}
          {previewMutation.isError && (
            <div className="flex items-center gap-2 p-3 bg-red-950/40 border border-red-500/30 rounded-lg text-red-400 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              {(previewMutation.error as Error).message}
            </div>
          )}

          <button
            onClick={() => previewMutation.mutate()}
            disabled={!entityId.trim() || previewMutation.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-teal-600 hover:bg-teal-500 disabled:opacity-40 text-white rounded-lg text-sm font-medium transition"
          >
            {previewMutation.isPending ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowRight className="w-4 h-4" />
            )}
            {previewMutation.isPending ? 'Fetching Preview…' : 'Preview Identifier'}
          </button>
        </div>
      )}

      {/* ── Step 2: Preview ── */}
      {step === 2 && preview && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h2 className="text-sm font-semibold text-slate-200">Step 2: Preview</h2>

            {/* Eligible / blocked */}
            <div
              className={`flex items-center gap-3 px-4 py-3 rounded-xl border text-sm font-medium ${
                preview.eligible
                  ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300'
                  : 'bg-red-950/30 border-red-500/30 text-red-300'
              }`}
            >
              {preview.eligible ? (
                <CheckCircle2 className="w-5 h-5 shrink-0" />
              ) : (
                <AlertTriangle className="w-5 h-5 shrink-0" />
              )}
              {preview.eligible
                ? preview.already_assigned
                  ? 'Already assigned — existing identifier will be returned'
                  : 'Eligible for generation'
                : `Blocked — ${preview.errors.join('; ')}`}
            </div>

            {/* Preview identifier value */}
            {preview.preview_identifier && (
              <div className="space-y-1">
                <span className="text-xs text-slate-500 font-medium">Preview Identifier Value</span>
                <div className="font-mono text-teal-300 text-lg bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 break-all">
                  {preview.preview_identifier}
                </div>
              </div>
            )}

            {/* Components */}
            {Object.keys(preview.components).length > 0 && (
              <div className="space-y-1">
                <span className="text-xs text-slate-500 font-medium">Components</span>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(preview.components)
                    .filter(([, v]) => v !== null && v !== undefined)
                    .map(([k, v]) => (
                      <div key={k} className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2">
                        <span className="text-xs text-slate-500 capitalize">{k.replace(/_/g, ' ')}</span>
                        <span className="block font-mono text-sm text-teal-300">{v}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Errors */}
            {preview.errors.length > 0 && (
              <div className="space-y-1">
                {preview.errors.map((e, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-red-400">
                    <AlertTriangle className="w-3 h-3 shrink-0" />
                    {e}
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setStep(1)}
                className="flex-1 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition border border-slate-700"
              >
                ← Back
              </button>
              {preview.eligible && (
                <button
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-500 disabled:opacity-40 text-white rounded-lg text-sm font-medium transition"
                >
                  {generateMutation.isPending ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : null}
                  {generateMutation.isPending ? 'Generating…' : 'Confirm & Generate →'}
                </button>
              )}
            </div>

            {generateMutation.isError && (
              <div className="flex items-center gap-2 p-3 bg-red-950/40 border border-red-500/30 rounded-lg text-red-400 text-sm">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                {(generateMutation.error as Error).message}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Step 3: Success ── */}
      {step === 3 && generated && (
        <div className="bg-slate-900 border border-emerald-500/30 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
            <h2 className="text-lg font-bold">Identifier Generated Successfully</h2>
          </div>

          <div className="space-y-1">
            <span className="text-xs text-slate-500 font-medium">GeoVertex Technical 3D Identifier</span>
            <div className="font-mono text-teal-300 text-xl bg-slate-950 border border-teal-500/30 rounded-xl px-4 py-4 break-all text-center">
              {generated.identifier_value}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-2.5">
              <span className="text-slate-500 block">Entity Type</span>
              <span className="text-slate-200 font-medium">{generated.entity_type}</span>
            </div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-2.5">
              <span className="text-slate-500 block">Status</span>
              <span className="text-emerald-400 font-medium">{generated.status}</span>
            </div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-2.5">
              <span className="text-slate-500 block">Version</span>
              <span className="text-slate-200 font-medium">{generated.version}</span>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setQrOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium border border-slate-700 transition"
            >
              <QrCode className="w-4 h-4" />
              View QR
            </button>
            <Link
              to={`/identifiers/${generated.id}`}
              className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-sm font-medium transition"
            >
              <ExternalLink className="w-4 h-4" />
              View Details
            </Link>
          </div>

          <QRViewModal
            isOpen={qrOpen}
            onClose={() => setQrOpen(false)}
            identifierId={generated.id}
            identifierValue={generated.identifier_value}
          />
        </div>
      )}
    </div>
  );
};
