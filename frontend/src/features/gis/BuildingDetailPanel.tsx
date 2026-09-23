import React from 'react';
import { X, Building2, MapPin, Layers, Maximize2, ArrowUp, Calendar } from 'lucide-react';
import { Building } from '../../types';

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
