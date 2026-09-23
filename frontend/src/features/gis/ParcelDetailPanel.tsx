import React, { useState } from 'react';
import {
  X,
  MapPin,
  Maximize2,
  Building as BuildingIcon,
  Home,
  FileText,
  Trash2,
  Edit,
  ExternalLink,
  Shield,
  Layers,
} from 'lucide-react';
import { Parcel, PropertySummary, BuildingSummary, UserRole } from '../../types';

interface ParcelDetailPanelProps {
  parcel: Parcel;
  userRole?: UserRole | null;
  onClose: () => void;
  onDeleteParcel?: (id: string) => Promise<void>;
  onSelectProperty?: (propertyId: string) => void;
  onSelectBuilding?: (buildingId: string) => void;
  onRefresh?: () => void;
}

export const ParcelDetailPanel: React.FC<ParcelDetailPanelProps> = ({
  parcel,
  userRole,
  onClose,
  onDeleteParcel,
  onSelectProperty,
  onSelectBuilding,
  onRefresh,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'properties' | 'buildings'>('details');

  const canEdit =
    userRole === 'ADMIN' || userRole === 'GOVERNMENT_OFFICER' || userRole === 'SURVEYOR';

  const handleDelete = async () => {
    if (!onDeleteParcel) return;
    if (window.confirm(`Are you sure you want to delete Parcel ${parcel.parcel_code}? This action cannot be undone.`)) {
      try {
        setIsDeleting(true);
        await onDeleteParcel(parcel.id);
      } catch (err: any) {
        alert(`Failed to delete parcel: ${err?.message || 'Unknown error'}`);
        setIsDeleting(false);
      }
    }
  };

  const getLandUseBadge = (use: string) => {
    switch (use?.toUpperCase()) {
      case 'RESIDENTIAL':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'COMMERCIAL':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'MIXED_USE':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'PUBLIC':
      case 'INSTITUTIONAL':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <div className="bg-slate-900/95 border border-slate-800 rounded-xl shadow-2xl backdrop-blur-md w-96 max-h-[85vh] flex flex-col overflow-hidden text-slate-200">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-start justify-between bg-slate-950/40">
        <div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-400"></span>
            <span className="text-[10px] font-mono tracking-wider text-emerald-400 uppercase font-semibold">
              Cadastral Parcel
            </span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">
            {parcel.parcel_code || parcel.parcel_number}
          </h2>
          <p className="text-xs text-slate-400">
            {parcel.jurisdiction_name ? `${parcel.jurisdiction_name} (${parcel.jurisdiction_code || ''})` : `Jurisdiction: ${parcel.jurisdiction_id}`}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 bg-slate-950/20 text-xs">
        <button
          onClick={() => setActiveTab('details')}
          className={`flex-1 py-2.5 px-3 font-medium transition text-center border-b-2 ${
            activeTab === 'details'
              ? 'border-emerald-400 text-emerald-300 bg-emerald-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Attributes
        </button>
        <button
          onClick={() => setActiveTab('properties')}
          className={`flex-1 py-2.5 px-3 font-medium transition text-center border-b-2 flex items-center justify-center space-x-1 ${
            activeTab === 'properties'
              ? 'border-emerald-400 text-emerald-300 bg-emerald-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Properties</span>
          <span className="bg-slate-800 text-slate-300 text-[10px] px-1.5 py-0.2 rounded-full">
            {parcel.properties?.length || 0}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('buildings')}
          className={`flex-1 py-2.5 px-3 font-medium transition text-center border-b-2 flex items-center justify-center space-x-1 ${
            activeTab === 'buildings'
              ? 'border-emerald-400 text-emerald-300 bg-emerald-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Footprints</span>
          <span className="bg-slate-800 text-slate-300 text-[10px] px-1.5 py-0.2 rounded-full">
            {parcel.buildings?.length || 0}
          </span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-4 overflow-y-auto flex-1 space-y-4 text-xs">
        {activeTab === 'details' && (
          <>
            {/* Status & Land Use */}
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800">
                <span className="text-[10px] uppercase font-mono text-slate-400 block mb-1">
                  Land Use
                </span>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold border ${getLandUseBadge(
                    parcel.land_use
                  )}`}
                >
                  {parcel.land_use}
                </span>
              </div>
              <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800">
                <span className="text-[10px] uppercase font-mono text-slate-400 block mb-1">
                  Status
                </span>
                <span className="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase">
                  {parcel.status}
                </span>
              </div>
            </div>

            {/* Geodesic Metrics */}
            <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 flex items-center space-x-1.5">
                  <Maximize2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Geodesic Area:</span>
                </span>
                <span className="font-mono font-semibold text-white">
                  {parcel.area ? parcel.area.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '0'} m²
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400 flex items-center space-x-1.5">
                  <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Centroid (Lon, Lat):</span>
                </span>
                <span className="font-mono text-slate-300">
                  {parcel.centroid_lon != null && parcel.centroid_lat != null
                    ? `${parcel.centroid_lon.toFixed(6)}, ${parcel.centroid_lat.toFixed(6)}`
                    : 'N/A'}
                </span>
              </div>
            </div>

            {/* Survey & Subdivision */}
            <div className="space-y-1.5 bg-slate-800/40 p-3 rounded-lg border border-slate-800">
              <div className="flex justify-between">
                <span className="text-slate-400">Parcel Number:</span>
                <span className="font-mono text-white">{parcel.parcel_number}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Survey Number:</span>
                <span className="font-mono text-slate-200">{parcel.survey_number || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Subdivision:</span>
                <span className="font-mono text-slate-200">{parcel.subdivision_number || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Ownership Status:</span>
                <span className="font-medium text-slate-200">{parcel.ownership_status || 'TITLED'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Source:</span>
                <span className="font-mono text-slate-300">{parcel.source}</span>
              </div>
            </div>
          </>
        )}

        {activeTab === 'properties' && (
          <div className="space-y-2">
            {(!parcel.properties || parcel.properties.length === 0) ? (
              <p className="text-slate-500 text-center py-4">No properties linked to this parcel.</p>
            ) : (
              parcel.properties.map((prop) => (
                <div
                  key={prop.id}
                  onClick={() => onSelectProperty && onSelectProperty(prop.id)}
                  className="p-2.5 rounded-lg bg-slate-800/50 hover:bg-slate-800 border border-slate-700/60 cursor-pointer transition flex items-start justify-between group"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-1.5">
                      <Home className="w-3.5 h-3.5 text-indigo-400" />
                      <span className="font-medium text-white group-hover:text-indigo-300 transition">
                        {prop.property_reference}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">{prop.address}</p>
                    <span className="inline-block text-[10px] text-slate-400 bg-slate-900/60 px-1.5 py-0.5 rounded mt-1 font-mono">
                      {prop.property_type}
                    </span>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300" />
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'buildings' && (
          <div className="space-y-2">
            {(!parcel.buildings || parcel.buildings.length === 0) ? (
              <p className="text-slate-500 text-center py-4">No building footprints on this parcel.</p>
            ) : (
              parcel.buildings.map((bldg) => (
                <div
                  key={bldg.id}
                  onClick={() => onSelectBuilding && onSelectBuilding(bldg.id)}
                  className="p-2.5 rounded-lg bg-slate-800/50 hover:bg-slate-800 border border-slate-700/60 cursor-pointer transition flex items-start justify-between group"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-1.5">
                      <BuildingIcon className="w-3.5 h-3.5 text-sky-400" />
                      <span className="font-medium text-white group-hover:text-sky-300 transition">
                        {bldg.building_reference}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">
                      Footprint: {bldg.area ? bldg.area.toLocaleString(undefined, { maximumFractionDigits: 1 }) : 0} m²
                      {bldg.height_estimate ? ` • Ht: ${bldg.height_estimate}m` : ''}
                    </p>
                    <span className="inline-block text-[10px] text-slate-400 bg-slate-900/60 px-1.5 py-0.5 rounded mt-1 font-mono">
                      {bldg.building_type}
                    </span>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300" />
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      {canEdit && (
        <div className="p-3 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between">
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="flex items-center space-x-1.5 text-red-400 hover:text-red-300 hover:bg-red-950/30 px-2.5 py-1.5 rounded-lg transition disabled:opacity-50 text-xs"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>{isDeleting ? 'Deleting...' : 'Delete Parcel'}</span>
          </button>
          <div className="text-[10px] text-slate-500 font-mono">ID: {parcel.id.substring(0, 8)}...</div>
        </div>
      )}
    </div>
  );
};
