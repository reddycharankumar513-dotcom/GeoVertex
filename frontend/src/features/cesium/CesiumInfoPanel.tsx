import React, { useState } from 'react';
import {
  X,
  Building2,
  MapPin,
  Home,
  Layers,
  ArrowUpRight,
  Edit2,
  Check,
  AlertCircle,
  Maximize2,
} from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { Building3DDetailResponse, Parcel3DDetailResponse, threedApi } from '../../api/threed';
import { useNavigate } from 'react-router-dom';

interface Props {
  buildingDetail: Building3DDetailResponse | null;
  parcelDetail: Parcel3DDetailResponse | null;
  isLoading: boolean;
  onClose: () => void;
  onHeightUpdated?: (buildingId: string, newHeight: number, newBaseElevation: number) => void;
  onSelectBuilding?: (buildingId: string) => void;
}

export const CesiumInfoPanel: React.FC<Props> = ({
  buildingDetail,
  parcelDetail,
  isLoading,
  onClose,
  onHeightUpdated,
  onSelectBuilding,
}) => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Edit Height State
  const [isEditing, setIsEditing] = useState(false);
  const [heightInput, setHeightInput] = useState<string>('');
  const [baseElevationInput, setBaseElevationInput] = useState<string>('0.0');
  const [sourceInput, setSourceInput] = useState<string>('MANUAL');
  const [isSaving, setIsSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const canEdit =
    user?.role === 'ADMIN' ||
    user?.role === 'GOVERNMENT_OFFICER' ||
    user?.role === 'SURVEYOR';

  const startEdit = () => {
    if (buildingDetail) {
      setHeightInput(buildingDetail.representation_3d.height.toString());
      setBaseElevationInput(buildingDetail.representation_3d.base_elevation.toString());
      setSourceInput(buildingDetail.representation_3d.height_source || 'MANUAL');
      setErrorMsg(null);
      setIsEditing(true);
    }
  };

  const handleSaveHeight = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!buildingDetail) return;

    const parsedHeight = parseFloat(heightInput);
    const parsedBase = parseFloat(baseElevationInput);

    if (isNaN(parsedHeight) || parsedHeight <= 0) {
      setErrorMsg('Height must be a positive number');
      return;
    }

    try {
      setIsSaving(true);
      setErrorMsg(null);
      const updated = await threedApi.updateBuildingHeight(buildingDetail.building.id, {
        height: parsedHeight,
        base_elevation: isNaN(parsedBase) ? 0.0 : parsedBase,
        height_source: sourceInput,
        height_confidence: 0.95,
      });

      if (onHeightUpdated) {
        onHeightUpdated(buildingDetail.building.id, updated.height, updated.base_elevation);
      }
      setIsEditing(false);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update building height');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-slate-900/95 backdrop-blur-md border border-slate-700/80 rounded-xl p-6 shadow-2xl text-slate-200 w-80 sm:w-96 animate-pulse">
        <div className="h-5 bg-slate-800 rounded w-2/3 mb-4"></div>
        <div className="h-4 bg-slate-800 rounded w-1/2 mb-6"></div>
        <div className="space-y-3">
          <div className="h-10 bg-slate-800 rounded"></div>
          <div className="h-10 bg-slate-800 rounded"></div>
        </div>
      </div>
    );
  }

  // Case 1: Building Selected
  if (buildingDetail) {
    const { building, representation_3d, parcel, properties, cesium_extrusion } = buildingDetail;
    const isCommercial = building.building_type === 'COMMERCIAL';

    return (
      <div className="bg-slate-900/95 backdrop-blur-md border border-slate-700/80 rounded-xl p-5 shadow-2xl text-slate-200 w-80 sm:w-96 max-h-[85vh] overflow-y-auto space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-700/60 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400">
                <Building2 className="w-4 h-4" />
              </span>
              <h3 className="font-bold text-base text-white tracking-wide">
                {building.building_reference}
              </h3>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                  isCommercial
                    ? 'bg-blue-950/80 text-blue-300 border border-blue-800/60'
                    : 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60'
                }`}
              >
                {building.building_type}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {building.status}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 3D Geometry Metrics Grid */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="bg-slate-800/70 p-2.5 rounded-lg border border-slate-700/50">
            <span className="text-slate-400 text-[11px] block">Vertical Height</span>
            <span className="text-base font-bold text-cyan-400 font-mono">
              {representation_3d.height.toFixed(1)} m
            </span>
          </div>

          <div className="bg-slate-800/70 p-2.5 rounded-lg border border-slate-700/50">
            <span className="text-slate-400 text-[11px] block">3D Volume</span>
            <span className="text-base font-bold text-amber-400 font-mono">
              {cesium_extrusion.volume_cu_m.toLocaleString()} m³
            </span>
          </div>

          <div className="bg-slate-800/70 p-2.5 rounded-lg border border-slate-700/50">
            <span className="text-slate-400 text-[11px] block">Footprint Area</span>
            <span className="text-sm font-semibold text-slate-200 font-mono">
              {building.area_sq_m.toLocaleString()} m²
            </span>
          </div>

          <div className="bg-slate-800/70 p-2.5 rounded-lg border border-slate-700/50">
            <span className="text-slate-400 text-[11px] block">Base Elevation</span>
            <span className="text-sm font-semibold text-slate-200 font-mono">
              {representation_3d.base_elevation.toFixed(1)} m
            </span>
          </div>
        </div>

        {/* Height Metadata / Edit Section */}
        {isEditing ? (
          <form onSubmit={handleSaveHeight} className="bg-slate-800/90 p-3 rounded-lg border border-blue-500/40 space-y-2.5">
            <div className="flex items-center justify-between text-xs font-semibold text-blue-300">
              <span>Edit Vertical Parameters</span>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="text-slate-400 hover:text-white"
              >
                Cancel
              </button>
            </div>

            {errorMsg && (
              <div className="flex items-center gap-1.5 p-2 bg-rose-950/60 border border-rose-800/60 rounded text-rose-300 text-[11px]">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div>
              <label className="text-[11px] text-slate-400 block mb-1">Height (meters)</label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                max="500"
                value={heightInput}
                onChange={(e) => setHeightInput(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="text-[11px] text-slate-400 block mb-1">Base Elevation (meters)</label>
              <input
                type="number"
                step="0.1"
                value={baseElevationInput}
                onChange={(e) => setBaseElevationInput(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="text-[11px] text-slate-400 block mb-1">Height Measurement Source</label>
              <select
                value={sourceInput}
                onChange={(e) => setSourceInput(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="SURVEY">SURVEY (Authoritative Field Measurement)</option>
                <option value="GOVERNMENT_DATA">GOVERNMENT_DATA (Municipal Approval Plan)</option>
                <option value="MANUAL">MANUAL (Manual Engineering Entry)</option>
                <option value="ESTIMATED">ESTIMATED (Formula Derived)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isSaving}
              className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs shadow-md transition-all disabled:opacity-50"
            >
              <Check className="w-3.5 h-3.5" />
              <span>{isSaving ? 'Saving Audit Record...' : 'Commit 3D Height Update'}</span>
            </button>
          </form>
        ) : (
          <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-700/40 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Source:</span>
              <span className="font-medium text-slate-200">{representation_3d.height_source}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Vertical Datum:</span>
              <span className="text-slate-300 font-mono text-[11px]">{representation_3d.vertical_reference}</span>
            </div>
            {representation_3d.height_confidence && (
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Confidence:</span>
                <span className="text-emerald-400 font-medium">
                  {(representation_3d.height_confidence * 100).toFixed(0)}%
                </span>
              </div>
            )}
            {canEdit && (
              <button
                type="button"
                onClick={startEdit}
                className="w-full mt-2 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded bg-slate-800 hover:bg-slate-700 text-blue-400 text-xs font-medium border border-slate-700 transition-colors"
              >
                <Edit2 className="w-3.5 h-3.5" />
                <span>Edit 3D Vertical Height</span>
              </button>
            )}
          </div>
        )}

        {/* Linked Cadastral Parcel Section */}
        {parcel && (
          <div className="border-t border-slate-700/60 pt-3 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
                <MapPin className="w-3.5 h-3.5 text-amber-400" />
                <span>Cadastral Parcel</span>
              </div>
              <button
                onClick={() => navigate(`/map?parcel_id=${parcel.id}`)}
                className="text-[11px] text-blue-400 hover:text-blue-300 flex items-center gap-0.5"
                title="View in 2D Cadastre Map"
              >
                <span>2D Map</span>
                <ArrowUpRight className="w-3 h-3" />
              </button>
            </div>
            <div className="bg-slate-800/50 p-2.5 rounded-lg border border-slate-700/40 space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-400">Parcel Code:</span>
                <span className="font-mono text-white font-medium">{parcel.parcel_code}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Parcel Number:</span>
                <span className="text-slate-200">{parcel.parcel_number}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Land Use:</span>
                <span className="text-slate-300">{parcel.land_use}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Ground Area:</span>
                <span className="text-slate-300">{parcel.area_sq_m.toLocaleString()} m²</span>
              </div>
            </div>
          </div>
        )}

        {/* Associated Legal Properties */}
        {properties && properties.length > 0 && (
          <div className="border-t border-slate-700/60 pt-3 space-y-2 text-xs">
            <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
              <Home className="w-3.5 h-3.5 text-emerald-400" />
              <span>Legal Property ({properties.length})</span>
            </div>
            <div className="space-y-1.5">
              {properties.map((prop) => (
                <div
                  key={prop.id}
                  className="bg-slate-800/40 p-2 rounded border border-slate-700/40 text-[11px]"
                >
                  <div className="flex justify-between font-medium text-slate-200">
                    <span>{prop.property_reference}</span>
                    <span className="text-emerald-400">{prop.property_type}</span>
                  </div>
                  <div className="text-slate-400 mt-0.5 truncate">{prop.address}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Case 2: Parcel Selected (No Building)
  if (parcelDetail) {
    const { parcel, buildings, properties } = parcelDetail;
    return (
      <div className="bg-slate-900/95 backdrop-blur-md border border-slate-700/80 rounded-xl p-5 shadow-2xl text-slate-200 w-80 sm:w-96 max-h-[85vh] overflow-y-auto space-y-4">
        <div className="flex items-start justify-between border-b border-slate-700/60 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-amber-500/20 text-amber-400">
                <MapPin className="w-4 h-4" />
              </span>
              <h3 className="font-bold text-base text-white tracking-wide">
                {parcel.parcel_code}
              </h3>
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Parcel #{parcel.parcel_number} • {parcel.land_use}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="bg-slate-800/70 p-2.5 rounded-lg border border-slate-700/50">
            <span className="text-slate-400 text-[11px] block">Ground Area</span>
            <span className="text-base font-bold text-white font-mono">
              {parcel.area_sq_m.toLocaleString()} m²
            </span>
          </div>

          <div className="bg-slate-800/70 p-2.5 rounded-lg border border-slate-700/50">
            <span className="text-slate-400 text-[11px] block">3D Buildings</span>
            <span className="text-base font-bold text-cyan-400 font-mono">
              {buildings.length}
            </span>
          </div>
        </div>

        {/* Buildings on Parcel */}
        {buildings.length > 0 && (
          <div className="space-y-1.5 text-xs">
            <span className="font-semibold text-slate-300 block">Footprints on Parcel:</span>
            <div className="space-y-1">
              {buildings.map((b) => (
                <button
                  key={b.building_id}
                  type="button"
                  onClick={() => onSelectBuilding && onSelectBuilding(b.building_id)}
                  className="w-full flex items-center justify-between p-2 rounded bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 text-left transition-colors"
                >
                  <div>
                    <span className="font-medium text-blue-400 block">{b.building_reference}</span>
                    <span className="text-[11px] text-slate-400">{b.building_type}</span>
                  </div>
                  <div className="text-right font-mono text-cyan-400 text-xs">
                    {b.height.toFixed(1)}m
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={() => navigate(`/map?parcel_id=${parcel.id}`)}
          className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-blue-400 font-medium text-xs border border-slate-700 transition-colors"
        >
          <Maximize2 className="w-3.5 h-3.5" />
          <span>Inspect in 2D Cadastre Map</span>
        </button>
      </div>
    );
  }

  // Case 3: Empty state
  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/60 rounded-xl p-4 shadow-xl text-slate-400 text-xs w-72 flex items-center gap-2.5">
      <Layers className="w-5 h-5 text-blue-400 flex-shrink-0" />
      <span>Click any 3D building extrusion or parcel ground outline to inspect vertical metrics.</span>
    </div>
  );
};
