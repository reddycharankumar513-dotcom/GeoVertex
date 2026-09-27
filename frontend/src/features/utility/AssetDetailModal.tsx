import React, { useState } from 'react';
import {
  UtilityAsset,
  UtilityReviewPayload,
  UtilityReviewStatus,
} from '../../types/utility';
import { utilityApi } from '../../api/utility';

interface AssetDetailModalProps {
  assetId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onAssetUpdated: () => void;
  canReview: boolean;
}

export const AssetDetailModal: React.FC<AssetDetailModalProps> = ({
  assetId,
  isOpen,
  onClose,
  onAssetUpdated,
  canReview,
}) => {
  const [details, setDetails] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState<'VERIFY' | 'REJECT' | 'REVISION_REQUIRED'>('VERIFY');
  const [reviewNotes, setReviewNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Controlled update state
  const [showControlledUpdate, setShowControlledUpdate] = useState(false);
  const [updateReason, setUpdateReason] = useState('');
  const [updateSourceRef, setUpdateSourceRef] = useState('');
  const [updateDepth, setUpdateDepth] = useState('');
  const [updateCapacity, setUpdateCapacity] = useState('');

  React.useEffect(() => {
    if (isOpen && assetId) {
      setLoading(true);
      setError(null);
      utilityApi.getAssetDetails(assetId)
        .then((data) => setDetails(data))
        .catch((err) => setError(err.message || 'Failed to load asset details'))
        .finally(() => setLoading(false));
    } else {
      setDetails(null);
    }
  }, [isOpen, assetId]);

  if (!isOpen || !assetId) return null;

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewNotes.trim()) {
      setError('Review notes are required for official adjudication.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await utilityApi.reviewCandidate(assetId, {
        action,
        review_notes: reviewNotes.trim(),
      });
      onAssetUpdated();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit review');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleControlledUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!updateReason.trim() || !updateSourceRef.trim()) {
      setError('Reason and source reference are required for controlled update.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const updates: Record<string, any> = {};
      if (updateDepth.trim()) updates.depth = parseFloat(updateDepth);
      if (updateCapacity.trim()) updates.capacity = updateCapacity.trim();

      await utilityApi.controlledUpdate(assetId, {
        reason: updateReason.trim(),
        source_reference: updateSourceRef.trim(),
        updates,
      });
      onAssetUpdated();
      setShowControlledUpdate(false);
      // Reload details
      const fresh = await utilityApi.getAssetDetails(assetId);
      setDetails(fresh);
    } catch (err: any) {
      setError(err.message || 'Failed to submit controlled update');
    } finally {
      setIsSubmitting(false);
    }
  };

  const asset: UtilityAsset | undefined = details?.asset;
  const network = details?.network;
  const parcelRel = details?.parcel_relation;
  const bldRel = details?.building_relation;
  const inspections = details?.inspections || [];
  const clashes = details?.clashes || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-4xl shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40 shrink-0">
          <div className="flex items-center space-x-3">
            <span className="text-xl">🚰</span>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base font-semibold text-white font-mono">
                  {asset?.asset_reference || 'Loading Asset...'}
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-950/80 text-sky-300 border border-sky-800">
                  {asset?.asset_type || 'PIPE'}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
                  {network?.utility_type || 'UTILITY'}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Network: {network?.name || 'Unknown'} &bull; Status: {asset?.status || 'ACTIVE'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1 text-xs">
          {error && (
            <div className="p-3 rounded bg-rose-950/60 border border-rose-800 text-rose-300">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center py-12 text-slate-400">Loading asset intelligence...</div>
          ) : asset ? (
            <>
              {/* Technical Specifications Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/60 p-4 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Depth of Cover</span>
                  <div className="text-sm font-bold text-white mt-0.5">
                    {asset.depth !== null && asset.depth !== undefined ? `${asset.depth.toFixed(2)} m` : 'UNKNOWN'}
                  </div>
                  <span className="text-[10px] text-slate-400">Ref: {asset.elevation_reference}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Centerline Elevation</span>
                  <div className="text-sm font-bold text-white mt-0.5">
                    {asset.centerline_elevation !== null && asset.centerline_elevation !== undefined
                      ? `${asset.centerline_elevation.toFixed(2)} m`
                      : '-'}
                  </div>
                  <span className="text-[10px] text-slate-400">Ground: {asset.ground_elevation?.toFixed(2) ?? '-'} m</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Material & Diameter</span>
                  <div className="text-sm font-bold text-white mt-0.5">
                    {asset.material || 'Standard'} ({asset.diameter ? `${(asset.diameter * 1000).toFixed(0)} mm` : '-'})
                  </div>
                  <span className="text-[10px] text-slate-400">Cap: {asset.capacity || '-'}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-semibold">Review Status</span>
                  <div className="text-sm font-bold mt-0.5 text-amber-400 font-mono">
                    {asset.review_status}
                  </div>
                  <span className="text-[10px] text-slate-400">Confidence: {asset.confidence}</span>
                </div>
              </div>

              {/* Spatial Cadastral & Building Relations */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Parcel Relationship */}
                <div className="bg-slate-950/40 p-4 rounded-lg border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="font-semibold text-white flex items-center space-x-1.5">
                      <span>📐</span>
                      <span>Cadastral Parcel Interaction</span>
                    </span>
                    {parcelRel?.intersects ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        CROSSES PARCEL
                      </span>
                    ) : (
                      <span className="text-slate-500 text-[11px]">No Intersection</span>
                    )}
                  </div>
                  {parcelRel ? (
                    <div className="space-y-1 text-slate-300">
                      <div>Parcel Number: <strong className="text-white">{parcelRel.parcel_number}</strong></div>
                      <div>Intersection Length: <strong className="text-sky-400">{parcelRel.intersection_length_m} m</strong></div>
                      <div>Is Boundary Crossing: <strong className="text-white">{parcelRel.is_crossing ? 'Yes' : 'No'}</strong></div>
                      <div className="text-[10px] text-slate-500 italic mt-2 border-t border-slate-800 pt-1">
                        {parcelRel.legal_disclaimer}
                      </div>
                    </div>
                  ) : (
                    <div className="text-slate-500 text-xs py-2">No linked parcel spatial record.</div>
                  )}
                </div>

                {/* Building Relationship */}
                <div className="bg-slate-950/40 p-4 rounded-lg border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="font-semibold text-white flex items-center space-x-1.5">
                      <span>🏢</span>
                      <span>3D Building Footprint Interaction</span>
                    </span>
                    {bldRel?.intersects_footprint ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        UNDER FOOTPRINT
                      </span>
                    ) : (
                      <span className="text-slate-500 text-[11px]">Clear</span>
                    )}
                  </div>
                  {bldRel ? (
                    <div className="space-y-1 text-slate-300">
                      <div>Building Ref: <strong className="text-white">{bldRel.building_reference}</strong></div>
                      <div>Passes Beneath Footprint: <strong className="text-white">{bldRel.passes_beneath ? 'Yes' : 'No'}</strong></div>
                      <div>Vertical Clearance: <strong className="text-sky-400">{bldRel.vertical_clearance_m ? `${bldRel.vertical_clearance_m} m` : 'Unknown'}</strong></div>
                      <div className="text-[10px] text-slate-500 italic mt-2 border-t border-slate-800 pt-1">
                        {bldRel.technical_disclaimer}
                      </div>
                    </div>
                  ) : (
                    <div className="text-slate-500 text-xs py-2">No linked building footprint record.</div>
                  )}
                </div>
              </div>

              {/* Clashes Section */}
              {clashes.length > 0 && (
                <div className="space-y-2">
                  <h3 className="font-semibold text-rose-400 flex items-center space-x-2">
                    <span>⚠️</span>
                    <span>3D Spatial Clashes Detected ({clashes.length})</span>
                  </h3>
                  <div className="divide-y divide-slate-800 bg-slate-950/60 rounded-lg border border-rose-950">
                    {clashes.map((c: any) => (
                      <div key={c.id} className="p-3 flex items-center justify-between">
                        <div>
                          <div className="font-medium text-white">
                            Relationship: {c.horizontal_relationship} / {c.vertical_relationship}
                          </div>
                          <div className="text-[11px] text-slate-400">
                            Measured: H={c.measured_horizontal_separation_m}m, V={c.measured_vertical_separation_m}m &bull; Required: H={c.required_horizontal_separation_m}m, V={c.required_vertical_separation_m}m
                          </div>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                          {c.severity}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Controlled Official Update Form (Collapsible) */}
              {canReview && (
                <div className="border-t border-slate-800 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowControlledUpdate(!showControlledUpdate)}
                    className="text-xs text-sky-400 hover:text-sky-300 flex items-center space-x-1"
                  >
                    <span>{showControlledUpdate ? '▼' : '▶'}</span>
                    <span className="font-semibold">Perform Controlled Official Record Update</span>
                  </button>

                  {showControlledUpdate && (
                    <form onSubmit={handleControlledUpdateSubmit} className="mt-3 bg-slate-950/80 p-4 rounded-lg border border-slate-800 space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-slate-400 text-[10px]">Justification / Reason</label>
                          <input
                            type="text"
                            value={updateReason}
                            onChange={(e) => setUpdateReason(e.target.value)}
                            placeholder="e.g. As-built survey correction"
                            className="w-full bg-slate-800 border border-slate-700 rounded p-1.5 text-white text-xs"
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-slate-400 text-[10px]">Source Reference</label>
                          <input
                            type="text"
                            value={updateSourceRef}
                            onChange={(e) => setUpdateSourceRef(e.target.value)}
                            placeholder="e.g. DWG-HYD-2026-01"
                            className="w-full bg-slate-800 border border-slate-700 rounded p-1.5 text-white text-xs"
                            required
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-slate-400 text-[10px]">Updated Depth (m)</label>
                          <input
                            type="number"
                            step="0.01"
                            value={updateDepth}
                            onChange={(e) => setUpdateDepth(e.target.value)}
                            placeholder="Leave blank to keep unchanged"
                            className="w-full bg-slate-800 border border-slate-700 rounded p-1.5 text-white text-xs"
                          />
                        </div>
                        <div>
                          <label className="block text-slate-400 text-[10px]">Updated Capacity / Rating</label>
                          <input
                            type="text"
                            value={updateCapacity}
                            onChange={(e) => setUpdateCapacity(e.target.value)}
                            placeholder="e.g. 5000 LPM"
                            className="w-full bg-slate-800 border border-slate-700 rounded p-1.5 text-white text-xs"
                          />
                        </div>
                      </div>

                      <div className="flex justify-end">
                        <button
                          type="submit"
                          disabled={isSubmitting}
                          className="px-3 py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-white font-medium transition disabled:opacity-50"
                        >
                          {isSubmitting ? 'Saving...' : 'Apply Controlled Update'}
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              )}

              {/* Cadastral Officer Verification Action */}
              {canReview && asset.review_status !== 'VERIFIED' && (
                <form onSubmit={handleReviewSubmit} className="bg-slate-950/80 p-4 rounded-lg border border-slate-800 space-y-3">
                  <div className="font-semibold text-white flex items-center space-x-2">
                    <span>⚖️</span>
                    <span>Cadastral Officer Verification Gate</span>
                  </div>

                  <div className="flex items-center space-x-4">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        name="reviewAction"
                        checked={action === 'VERIFY'}
                        onChange={() => setAction('VERIFY')}
                      />
                      <span className="text-emerald-400 font-semibold">Verify Official Record</span>
                    </label>
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        name="reviewAction"
                        checked={action === 'REVISION_REQUIRED'}
                        onChange={() => setAction('REVISION_REQUIRED')}
                      />
                      <span className="text-amber-400 font-semibold">Request Revision</span>
                    </label>
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        name="reviewAction"
                        checked={action === 'REJECT'}
                        onChange={() => setAction('REJECT')}
                      />
                      <span className="text-rose-400 font-semibold">Reject Candidate</span>
                    </label>
                  </div>

                  <div>
                    <label className="block text-slate-400 text-[10px]">Adjudication Notes (Mandatory for audit trail)</label>
                    <textarea
                      rows={2}
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      placeholder="Detail physical survey verification or reason for determination..."
                      className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white text-xs focus:outline-none focus:border-sky-500"
                      required
                    />
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-white font-medium transition disabled:opacity-50"
                    >
                      {isSubmitting ? 'Submitting...' : 'Submit Verification Decision'}
                    </button>
                  </div>
                </form>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};
