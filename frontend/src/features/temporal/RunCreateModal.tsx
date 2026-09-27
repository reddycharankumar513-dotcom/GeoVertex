import React, { useState } from 'react';
import { ChangeRunCreatePayload, DetectionMethod } from '../../types/temporal';
import { temporalApi } from '../../api/temporal';

interface RunCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunCreated: () => void;
}

export const RunCreateModal: React.FC<RunCreateModalProps> = ({
  isOpen,
  onClose,
  onRunCreated,
}) => {
  const [targetType, setTargetType] = useState('BUILDING');
  const [targetId, setTargetId] = useState('');
  const [detectionMethod, setDetectionMethod] = useState<DetectionMethod>('COMPOSITE');
  const [baselineReference, setBaselineReference] = useState('CURRENT');
  const [comparisonReference, setComparisonReference] = useState('SURVEY_LATEST');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Thresholds
  const [areaThreshold, setAreaThreshold] = useState('1.0');
  const [heightThreshold, setHeightThreshold] = useState('0.5');
  const [displacementThreshold, setDisplacementThreshold] = useState('0.3');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload: ChangeRunCreatePayload = {
        target_type: targetType,
        target_id: targetId.trim() || undefined,
        detection_method: detectionMethod,
        baseline_reference: baselineReference.trim(),
        comparison_reference: comparisonReference.trim(),
      };

      if (showAdvanced) {
        payload.parameters = {
          area_threshold_sqm: parseFloat(areaThreshold) || 1.0,
          height_threshold_m: parseFloat(heightThreshold) || 0.5,
          displacement_threshold_m: parseFloat(displacementThreshold) || 0.3,
        };
      }

      await temporalApi.createRun(payload);
      onRunCreated();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to dispatch change detection run');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-xl shadow-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-lg">⏱️</span>
            <h2 className="text-base font-semibold text-white">Dispatch Change Detection Run</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {error && (
            <div className="p-3 rounded bg-rose-950/60 border border-rose-800 text-rose-300">
              {error}
            </div>
          )}

          <div className="p-3 rounded-lg bg-sky-950/30 border border-sky-800/40 text-sky-300 text-[11px] leading-relaxed">
            <strong>Mandatory Governance:</strong> Change detection compares temporal snapshots and generates candidate changes with topological validation and evidence linkage. Human verification is strictly required.
          </div>

          {/* Target Type */}
          <div className="space-y-1">
            <label className="block text-slate-300 font-medium">Target Entity Scope</label>
            <select
              value={targetType}
              onChange={(e) => setTargetType(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-sky-500"
            >
              <option value="BUILDING">Building (Footprints & Vertical Volume Changes)</option>
              <option value="PARCEL">Parcel (Cadastral Boundary & Attribute Discrepancies)</option>
              <option value="FLOOR">Floor (Floor Slices & Vertical Elevation Stacks)</option>
              <option value="UNIT">Property Unit (Unit Boundary & Containment)</option>
              <option value="SYSTEM">System-Wide Comprehensive Scan</option>
            </select>
          </div>

          {/* Target ID */}
          {targetType !== 'SYSTEM' && (
            <div className="space-y-1">
              <label className="block text-slate-300 font-medium">
                Target Entity ID (Optional - leave blank to scan all in scope)
              </label>
              <input
                type="text"
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                placeholder="e.g. bld-uuid-1234 or leave blank"
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white font-mono focus:outline-none focus:border-sky-500"
              />
            </div>
          )}

          {/* Detection Method */}
          <div className="space-y-1">
            <label className="block text-slate-300 font-medium">Detection Method</label>
            <select
              value={detectionMethod}
              onChange={(e) => setDetectionMethod(e.target.value as DetectionMethod)}
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-sky-500"
            >
              <option value="COMPOSITE">Composite (Deterministic Geometry + Attribute + Evidence)</option>
              <option value="GEOMETRY_DIFF">Deterministic Geometry Diff (Metric Area & IoU)</option>
              <option value="ATTRIBUTE_DIFF">Attribute Diff (Use Type, Heights, Statuses)</option>
              <option value="SURVEY_COMPARISON">Survey Comparison (Field Observations vs Official)</option>
              <option value="DOCUMENT_COMPARISON">Document Comparison (Deed vs Cadastral Geometry)</option>
              <option value="IMAGE_AI">Image AI (Pairwise Satellite/Aerial Comparison)</option>
            </select>
          </div>

          {/* Baseline & Comparison References */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="block text-slate-300 font-medium">Baseline Reference</label>
              <input
                type="text"
                value={baselineReference}
                onChange={(e) => setBaselineReference(e.target.value)}
                placeholder="CURRENT or snapshot-id"
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white font-mono focus:outline-none focus:border-sky-500"
                required
              />
              <span className="text-[10px] text-slate-500">e.g. CURRENT, snapshot UUID, or date</span>
            </div>

            <div className="space-y-1">
              <label className="block text-slate-300 font-medium">Comparison Reference</label>
              <input
                type="text"
                value={comparisonReference}
                onChange={(e) => setComparisonReference(e.target.value)}
                placeholder="SURVEY_LATEST or date"
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white font-mono focus:outline-none focus:border-sky-500"
                required
              />
              <span className="text-[10px] text-slate-500">e.g. SURVEY_LATEST or snapshot UUID</span>
            </div>
          </div>

          {/* Advanced Thresholds Toggle */}
          <div className="pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-sky-400 hover:text-sky-300 text-xs flex items-center space-x-1"
            >
              <span>{showAdvanced ? '▼' : '▶'}</span>
              <span>Advanced Metric Thresholds</span>
            </button>

            {showAdvanced && (
              <div className="mt-3 grid grid-cols-3 gap-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                <div>
                  <label className="block text-slate-400 text-[10px]">Min Area Delta (m²)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={areaThreshold}
                    onChange={(e) => setAreaThreshold(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded p-1.5 text-white font-mono text-xs"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 text-[10px]">Min Height Delta (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={heightThreshold}
                    onChange={(e) => setHeightThreshold(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded p-1.5 text-white font-mono text-xs"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 text-[10px]">Min Centroid Shift (m)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={displacementThreshold}
                    onChange={(e) => setDisplacementThreshold(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded p-1.5 text-white font-mono text-xs"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-white font-medium flex items-center space-x-2 transition disabled:opacity-50"
            >
              {loading && <div className="w-3 h-3 border-2 border-white/20 border-t-white rounded-full animate-spin" />}
              <span>{loading ? 'Dispatching...' : 'Dispatch Change Detection'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
