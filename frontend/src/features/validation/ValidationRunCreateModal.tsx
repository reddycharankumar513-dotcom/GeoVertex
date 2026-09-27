import React, { useState } from 'react';
import { ValidationRunCreatePayload, ValidationTargetType } from '../../types/validation';
import { validationApi } from '../../api/validation';

interface ValidationRunCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunCreated: () => void;
}

export const ValidationRunCreateModal: React.FC<ValidationRunCreateModalProps> = ({
  isOpen,
  onClose,
  onRunCreated,
}) => {
  const [targetType, setTargetType] = useState<ValidationTargetType>('BUILDING');
  const [targetId, setTargetId] = useState('');
  const [validationType, setValidationType] = useState('SINGLE_ENTITY');
  const [geometryWkt, setGeometryWkt] = useState('');
  const [showTolerances, setShowTolerances] = useState(false);

  // Tolerance overrides
  const [areaOverlapTol, setAreaOverlapTol] = useState('0.05');
  const [outsideParcelTol, setOutsideParcelTol] = useState('0.02');
  const [verticalElevationTol, setVerticalElevationTol] = useState('0.05');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload: ValidationRunCreatePayload = {
        target_type: targetType,
        target_id: targetId.trim() || undefined,
        validation_type: validationType,
        geometry_wkt: geometryWkt.trim() || undefined,
      };

      if (showTolerances) {
        payload.tolerance_overrides = {
          area_overlap_tolerance_sqm: parseFloat(areaOverlapTol),
          outside_parcel_tolerance_ratio: parseFloat(outsideParcelTol),
          vertical_elevation_tolerance_m: parseFloat(verticalElevationTol),
        };
      }

      await validationApi.createRun(payload);
      onRunCreated();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to dispatch validation run');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-xl shadow-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-lg">📐</span>
            <h2 className="text-base font-semibold text-white">Dispatch Topology Validation Run</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {error && (
            <div className="p-3 rounded bg-rose-950/60 border border-rose-800 text-rose-300">
              {error}
            </div>
          )}

          {/* Target Type */}
          <div className="space-y-1">
            <label className="block text-slate-300 font-medium">Target Scope / Entity Type</label>
            <select
              value={targetType}
              onChange={(e) => setTargetType(e.target.value as ValidationTargetType)}
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-sky-500"
            >
              <option value="BUILDING">Building (Footprint & Vertical Slices)</option>
              <option value="PARCEL">Parcel (Cadastral Boundaries & Adjacencies)</option>
              <option value="FLOOR">Floor (Elevation Interval & Slab Stack)</option>
              <option value="UNIT">Property Unit (Spatial Containment & Co-planarity)</option>
              <option value="AI_RESULT">AI Candidate Footprint (Cadastral Congruency)</option>
              <option value="SURVEY_SUBMISSION">Survey Submission (Field vs Official Cadastre)</option>
              <option value="JURISDICTION">Jurisdiction (Administrative Boundary Containment)</option>
              <option value="SYSTEM">System-Wide Comprehensive Scan</option>
            </select>
          </div>

          {/* Target ID */}
          {targetType !== 'SYSTEM' && (
            <div className="space-y-1">
              <label className="block text-slate-300 font-medium">
                Target Entity ID or Code (Optional if validating raw geometry)
              </label>
              <input
                type="text"
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                placeholder="e.g. BLD-001, Parcel UUID, or leave blank for broad check"
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white font-mono focus:outline-none focus:border-sky-500"
              />
            </div>
          )}

          {/* Ad-hoc WKT input */}
          <div className="space-y-1">
            <label className="block text-slate-300 font-medium">
              Direct WKT Geometry (Optional for ad-hoc polygon verification)
            </label>
            <textarea
              rows={2}
              value={geometryWkt}
              onChange={(e) => setGeometryWkt(e.target.value)}
              placeholder="POLYGON((...))"
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white font-mono text-[11px] focus:outline-none focus:border-sky-500"
            />
          </div>

          {/* Tolerance Overrides Accordion */}
          <div className="pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setShowTolerances(!showTolerances)}
              className="text-sky-400 hover:text-sky-300 flex items-center space-x-1.5 font-medium"
            >
              <span>{showTolerances ? '▼' : '▶'}</span>
              <span>Advanced Numerical Tolerance Configuration</span>
            </button>

            {showTolerances && (
              <div className="mt-3 p-3 bg-slate-950/60 rounded border border-slate-800 grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-[11px] text-slate-400">Area Overlap (m²)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={areaOverlapTol}
                    onChange={(e) => setAreaOverlapTol(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-white font-mono mt-1"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400">Outside Parcel Ratio</label>
                  <input
                    type="number"
                    step="0.01"
                    value={outsideParcelTol}
                    onChange={(e) => setOutsideParcelTol(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-white font-mono mt-1"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400">Vertical Tol (m)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={verticalElevationTol}
                    onChange={(e) => setVerticalElevationTol(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-white font-mono mt-1"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Buttons */}
          <div className="pt-3 border-t border-slate-800 flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-white font-medium disabled:opacity-50 transition"
            >
              {loading ? 'Dispatching...' : 'Dispatch Validation Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
