import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Building2, MapPin, Layers, Maximize2, ArrowUp, Calendar, Box, Home } from 'lucide-react';
import { Building } from '../../types';
import { floorsApi, FloorResponse } from '../../api/floors';

interface BuildingDetailPanelProps {
  building: Building;
  onClose: () => void;
  onSelectParcel?: (parcelId: string) => void;
}

export const BuildingDetailPanel: React.FC<BuildingDetailPanelProps> = ({
  building,
  onClose,
  onSelectParcel,
}) => {
  const navigate = useNavigate();
  const [floors, setFloors] = useState<FloorResponse[]>([]);
  const [isLoadingFloors, setIsLoadingFloors] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const loadFloors = async () => {
      try {
        setIsLoadingFloors(true);
        const data = await floorsApi.listByBuilding(building.id);
        if (isMounted) {
          setFloors(data || []);
        }
      } catch (err) {
        console.error('Failed to load building floors:', err);
      } finally {
        if (isMounted) {
          setIsLoadingFloors(false);
        }
      }
    };
    loadFloors();
    return () => {
      isMounted = false;
    };
  }, [building.id]);
  return (
    <div className="bg-slate-900/95 border border-slate-800 rounded-xl shadow-2xl backdrop-blur-md w-96 max-h-[85vh] flex flex-col overflow-hidden text-slate-200">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-start justify-between bg-slate-950/40">
        <div>
          <div className="flex items-center space-x-2">
            <Building2 className="w-4 h-4 text-sky-400" />
            <span className="text-[10px] font-mono tracking-wider text-sky-400 uppercase font-semibold">
              Building Footprint
            </span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">
            {building.building_reference}
          </h2>
          <p className="text-xs text-slate-400">Type: {building.building_type}</p>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Body */}
      <div className="p-4 overflow-y-auto flex-1 space-y-4 text-xs">
        {/* 3D Digital Twin Navigation */}
        <button
          type="button"
          onClick={() => navigate(`/digital-twin?building_id=${building.id}`)}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-gradient-to-r from-cyan-950 to-blue-950 hover:from-cyan-900 hover:to-blue-900 text-cyan-300 border border-cyan-800/60 font-medium text-xs shadow-md transition-all"
        >
          <Box className="w-4 h-4 text-cyan-400" />
          <span>View in 3D Digital Twin</span>
        </button>

        {/* Status & Type */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Building Type</span>
            <span className="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/30">
              {building.building_type}
            </span>
          </div>
          <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Status</span>
            <span className="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase">
              {building.status}
            </span>
          </div>
        </div>

        {/* Footprint Metrics */}
        <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center space-x-1.5">
              <Maximize2 className="w-3.5 h-3.5 text-sky-400" />
              <span>Footprint Area:</span>
            </span>
            <span className="font-mono font-semibold text-white">
              {building.area ? building.area.toLocaleString(undefined, { maximumFractionDigits: 2 }) : 0} m²
            </span>
          </div>
          {building.height_estimate != null && (
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center space-x-1.5">
                <ArrowUp className="w-3.5 h-3.5 text-sky-400" />
                <span>Estimated Height:</span>
              </span>
              <span className="font-mono text-white">{building.height_estimate} meters</span>
            </div>
          )}
        </div>

        {/* Underlying Parcel Link */}
        {building.parcel_id && (
          <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5 text-emerald-400" />
                <span>Contained in Parcel:</span>
              </span>
              <button
                onClick={() => onSelectParcel && onSelectParcel(building.parcel_id!)}
                className="text-emerald-400 hover:text-emerald-300 font-mono font-medium underline"
              >
                {building.parcel_code || building.parcel_number || building.parcel_id.substring(0, 8)}
              </button>
            </div>
          </div>
        )}

        {/* Floors & Vertical Units (Phase 4) */}
        <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-slate-300 font-semibold flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-cyan-400" />
              <span>Vertical Floors ({floors.length})</span>
            </span>
            <span className="text-[10px] text-cyan-400 font-mono">
              {floors.length > 0 ? `${floors[0].elevation_min_m}m - ${floors[floors.length - 1].elevation_max_m}m` : 'Unassigned'}
            </span>
          </div>

          {isLoadingFloors ? (
            <div className="text-[11px] text-slate-500 py-1 italic">Loading floors...</div>
          ) : floors.length === 0 ? (
            <div className="text-[11px] text-slate-500 py-1 italic">No vertical floors recorded yet</div>
          ) : (
            <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
              {[...floors]
                .sort((a, b) => b.floor_number - a.floor_number)
                .map((f) => (
                  <div
                    key={f.id}
                    className="p-2 rounded bg-slate-900/80 border border-slate-700/60 flex items-center justify-between text-[11px]"
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="w-5 h-5 rounded bg-slate-800 text-cyan-400 font-mono font-semibold flex items-center justify-center text-[10px]">
                        {f.floor_number >= 0 ? `L${f.floor_number}` : `B${Math.abs(f.floor_number)}`}
                      </span>
                      <div>
                        <div className="font-medium text-slate-200">{f.floor_name || `Floor ${f.floor_number}`}</div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {f.elevation_min_m.toFixed(1)}–{f.elevation_max_m.toFixed(1)}m (Δ{f.height_m.toFixed(1)}m)
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => navigate(`/digital-twin?building_id=${building.id}&floor_id=${f.id}`)}
                      className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 text-[10px] hover:bg-cyan-900 transition-colors"
                    >
                      3D Slab
                    </button>
                  </div>
                ))}
            </div>
          )}
        </div>

        {/* Source Tracking */}
        <div className="space-y-1.5 bg-slate-800/40 p-3 rounded-lg border border-slate-800">
          <div className="flex justify-between">
            <span className="text-slate-400">Data Source:</span>
            <span className="font-mono text-slate-200">{building.source}</span>
          </div>
          {building.source_reference && (
            <div className="flex justify-between">
              <span className="text-slate-400">Source Ref:</span>
              <span className="font-mono text-slate-200">{building.source_reference}</span>
            </div>
          )}
        </div>

        {/* Metadata */}
        <div className="text-[11px] text-slate-500 space-y-1 px-1">
          <div className="flex justify-between">
            <span>Created:</span>
            <span>{new Date(building.created_at).toLocaleDateString()}</span>
          </div>
          <div className="flex justify-between">
            <span>Building ID:</span>
            <span className="font-mono">{building.id.substring(0, 12)}...</span>
          </div>
        </div>
      </div>
    </div>
  );
};
