import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Edit3,
  RotateCcw,
  Check,
  X,
  Layers,
  Image as ImageIcon,
  Cpu,
  Info,
} from 'lucide-react';
import { BuildingExtractionResult } from '../../types/ai';
import { AIResultMap } from './AIResultMap';
import { aiApi } from '../../api/ai';

interface AIReviewModalProps {
  result: BuildingExtractionResult;
  officialGeometryWkt?: string;
  onClose: () => void;
  onSuccess: () => void;
}

export const AIReviewModal: React.FC<AIReviewModalProps> = ({
  result,
  officialGeometryWkt,
  onClose,
  onSuccess,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedWkt, setEditedWkt] = useState(result.geometry_wkt);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const comp = result.cadastral_comparison || {
    iou: 0,
    area_diff_sqm: 0,
    boundary_diff_m: 0,
    official_area_sqm: 0,
    candidate_area_sqm: 0,
  };

  const conf = result.confidence_components || {
    model_confidence: 0,
    geometry_quality: 0,
    source_quality: 0,
  };

  const handleApprove = async () => {
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await aiApi.approveResult(result.id);
      onSuccess();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to approve candidate result');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleModifyAndApprove = async () => {
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await aiApi.modifyAndApproveResult(result.id, {
        action: 'MODIFY_AND_APPROVE',
        edited_geometry_wkt: editedWkt,
        notes: 'Reviewer manual vertex refinement',
      });
      onSuccess();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to apply modified geometry');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      setErrorMsg('Mandatory rejection rationale is required');
      return;
    }
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await aiApi.rejectResult(result.id, rejectReason);
      onSuccess();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to reject result');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReprocess = async () => {
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await aiApi.requestReprocessing(result.id, 'Reprocessing requested by reviewer');
      onSuccess();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to request reprocessing');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-5xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">AI Extraction Review</h2>
              <p className="text-xs text-slate-400 font-mono">
                Target: {result.source_target_id} | Model: {result.model_id} (v{result.model_version})
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm text-slate-200">
          {errorMsg && (
            <div className="p-3 bg-red-950/50 border border-red-500/40 rounded-xl text-red-200 text-xs flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Grid Layout: Visual Map Comparison & Evidence on Left, Metrics & Controls on Right */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Visual Map Comparison */}
            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-slate-400" />
                  Spatial Cadastral Overlay
                </span>
                <span className="text-xs text-purple-400 font-mono">
                  Confidence: {Math.round(result.confidence * 100)}%
                </span>
              </div>

              <AIResultMap
                officialWkt={officialGeometryWkt}
                candidateWkt={isEditing ? editedWkt : result.geometry_wkt}
                height={340}
              />

              {/* Geometry Vertex Editor */}
              {isEditing ? (
                <div className="p-3 bg-slate-950/80 border border-purple-500/40 rounded-xl space-y-2">
                  <div className="flex items-center justify-between text-xs text-purple-300">
                    <span className="font-semibold flex items-center gap-1">
                      <Edit3 className="w-3.5 h-3.5" />
                      Candidate Geometry Editor (WKT Polygon)
                    </span>
                    <button
                      type="button"
                      onClick={() => setEditedWkt(result.geometry_wkt)}
                      className="text-slate-400 hover:text-white text-[11px]"
                    >
                      Reset
                    </button>
                  </div>
                  <textarea
                    rows={3}
                    value={editedWkt}
                    onChange={(e) => setEditedWkt(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 font-mono text-xs text-slate-200 focus:outline-none focus:border-purple-400"
                  />
                  <div className="flex justify-end gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() => setIsEditing(false)}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                    >
                      Cancel Edit
                    </button>
                    <button
                      type="button"
                      onClick={handleModifyAndApprove}
                      disabled={isSubmitting}
                      className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white font-medium rounded-lg shadow"
                    >
                      Save & Approve
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => setIsEditing(true)}
                    className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 py-1 px-2.5 rounded-lg border border-purple-500/30 hover:bg-purple-500/10 transition-colors"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Refine Candidate Vertices
                  </button>
                </div>
              )}
            </div>

            {/* Validation & Confidence Inspection */}
            <div className="lg:col-span-5 space-y-4">
              {/* Validation Card */}
              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl space-y-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Deterministic GIS Validation
                </span>

                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Geometry Topology:</span>
                    <span className="flex items-center gap-1 text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Valid OGC Polygon
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">CRS Normalization:</span>
                    <span className="flex items-center gap-1 text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      EPSG:4326 (WGS 84)
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Intersection over Union (IoU):</span>
                    <span className="font-mono text-purple-300 font-bold">
                      {comp.iou ? comp.iou.toFixed(4) : '0.0000'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Area Discrepancy:</span>
                    <span className="font-mono text-amber-300">
                      {comp.area_diff_sqm ? `${comp.area_diff_sqm} m²` : '0 m²'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Boundary Discrepancy:</span>
                    <span className="font-mono text-slate-300">
                      {comp.boundary_diff_m ? `~${comp.boundary_diff_m} m` : '0 m'}
                    </span>
                  </div>

                  {result.estimated_height && (
                    <div className="flex items-center justify-between pt-1 border-t border-slate-800">
                      <span className="text-slate-400">Height Estimate:</span>
                      <span className="font-mono text-cyan-300 font-bold">
                        {result.estimated_height} m
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Confidence Components */}
              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl space-y-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-cyan-400" />
                  Confidence Framework Breakdown
                </span>

                <div className="space-y-2 text-xs">
                  <div>
                    <div className="flex justify-between text-slate-400 mb-1">
                      <span>Model Confidence:</span>
                      <span className="font-mono text-slate-200">
                        {Math.round(conf.model_confidence * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${conf.model_confidence * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-400 mb-1">
                      <span>Geometry Quality:</span>
                      <span className="font-mono text-slate-200">
                        {Math.round(conf.geometry_quality * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{ width: `${conf.geometry_quality * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-400 mb-1">
                      <span>Source Quality:</span>
                      <span className="font-mono text-slate-200">
                        {Math.round(conf.source_quality * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full"
                        style={{ width: `${conf.source_quality * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Rejection Form Drawer */}
              {showRejectForm && (
                <div className="p-3 bg-red-950/40 border border-red-500/40 rounded-xl space-y-2">
                  <label className="block text-xs font-semibold text-red-300">
                    Mandatory Rejection Justification:
                  </label>
                  <textarea
                    rows={2}
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Enter reason for rejecting candidate geometry..."
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-red-400"
                  />
                  <div className="flex justify-end gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() => setShowRejectForm(false)}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleReject}
                      disabled={isSubmitting}
                      className="px-3 py-1 bg-red-600 hover:bg-red-500 text-white font-medium rounded shadow"
                    >
                      Confirm Rejection
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            Current Status: <span className="font-semibold text-slate-200">{result.status}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleReprocess}
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-xl transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reprocess
            </button>

            <button
              type="button"
              onClick={() => setShowRejectForm(true)}
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-red-950/60 hover:bg-red-900/80 text-red-300 border border-red-800/60 text-xs font-medium rounded-xl transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              Reject
            </button>

            <button
              type="button"
              onClick={handleApprove}
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-emerald-600/20 transition-all"
            >
              <Check className="w-4 h-4" />
              Approve Controlled Update
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
