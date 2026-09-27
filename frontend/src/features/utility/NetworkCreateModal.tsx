import React, { useState } from 'react';
import { UtilityNetworkCreatePayload, UtilityType } from '../../types/utility';
import { utilityApi } from '../../api/utility';

interface NetworkCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNetworkCreated: () => void;
}

export const NetworkCreateModal: React.FC<NetworkCreateModalProps> = ({
  isOpen,
  onClose,
  onNetworkCreated,
}) => {
  const [name, setName] = useState('');
  const [utilityType, setUtilityType] = useState<UtilityType>('WATER');
  const [owner, setOwner] = useState('');
  const [operator, setOperator] = useState('');
  const [jurisdictionId, setJurisdictionId] = useState('');
  const [coordinateSystem, setCoordinateSystem] = useState('EPSG:4326');
  const [verticalDatum, setVerticalDatum] = useState('WGS84');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Network name is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload: UtilityNetworkCreatePayload = {
        name: name.trim(),
        utility_type: utilityType,
        owner: owner.trim() || undefined,
        operator: operator.trim() || undefined,
        jurisdiction_id: jurisdictionId.trim() || undefined,
        coordinate_system: coordinateSystem.trim() || 'EPSG:4326',
        vertical_datum: verticalDatum.trim() || 'WGS84',
      };

      await utilityApi.createNetwork(payload);
      onNetworkCreated();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create utility network');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-lg shadow-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-lg">🌐</span>
            <h2 className="text-base font-semibold text-white">Create Utility Network</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {error && (
            <div className="p-3 rounded bg-rose-950/60 border border-rose-800 text-rose-300">
              {error}
            </div>
          )}

          <div className="p-3 rounded-lg bg-sky-950/30 border border-sky-800/40 text-sky-300 text-[11px] leading-relaxed">
            <strong>Subsurface Infrastructure:</strong> Utility networks define the domain, ownership, and vertical coordinate datum for all underground pipelines, cables, manholes, and multi-utility corridors.
          </div>

          <div className="space-y-1">
            <label className="block text-slate-300 font-medium">Network Name *</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Central City Water Main Network"
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="block text-slate-300 font-medium">Utility Domain *</label>
              <select
                value={utilityType}
                onChange={(e) => setUtilityType(e.target.value as UtilityType)}
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-sky-500"
              >
                <option value="WATER">Water (Potable / Distribution)</option>
                <option value="SEWER">Sewer (Sanitary / Trunk)</option>
                <option value="STORMWATER">Stormwater (Drainage / Culvert)</option>
                <option value="GAS">Gas (Natural / Distribution)</option>
                <option value="ELECTRICITY">Electricity (HV / MV / LV)</option>
                <option value="TELECOM">Telecom (Copper / Conduit)</option>
                <option value="FIBER">Fiber Optic (Broadband)</option>
                <option value="DRAINAGE">Drainage (General)</option>
                <option value="OTHER">Other / Multi-Utility</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="block text-slate-300 font-medium">Jurisdiction ID</label>
              <input
                type="text"
                value={jurisdictionId}
                onChange={(e) => setJurisdictionId(e.target.value)}
                placeholder="Optional Jurisdiction UUID"
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="block text-slate-300 font-medium">Asset Owner</label>
              <input
                type="text"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                placeholder="e.g. Water Resources Dept"
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-slate-300 font-medium">Asset Operator</label>
              <input
                type="text"
                value={operator}
                onChange={(e) => setOperator(e.target.value)}
                placeholder="e.g. Municipal Utility Services"
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="block text-slate-300 font-medium">CRS</label>
              <input
                type="text"
                value={coordinateSystem}
                onChange={(e) => setCoordinateSystem(e.target.value)}
                placeholder="EPSG:4326"
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-slate-300 font-medium">Vertical Datum</label>
              <input
                type="text"
                value={verticalDatum}
                onChange={(e) => setVerticalDatum(e.target.value)}
                placeholder="WGS84 / NAVD88"
                className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-white focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 text-slate-300 hover:bg-slate-700 rounded font-medium transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded font-medium transition flex items-center space-x-1"
            >
              {loading && <span className="animate-spin mr-1">⌛</span>}
              <span>Create Network</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
