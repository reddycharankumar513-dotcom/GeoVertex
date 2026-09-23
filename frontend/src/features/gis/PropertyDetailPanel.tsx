import React from 'react';
import { X, Home, MapPin, Layers, Building, Calendar, Info } from 'lucide-react';
import { Property } from '../../types';

interface PropertyDetailPanelProps {
  property: Property;
  onClose: () => void;
  onSelectParcel?: (parcelId: string) => void;
}

export const PropertyDetailPanel: React.FC<PropertyDetailPanelProps> = ({
  property,
  onClose,
  onSelectParcel,
}) => {
  return (
    <div className="bg-slate-900/95 border border-slate-800 rounded-xl shadow-2xl backdrop-blur-md w-96 max-h-[85vh] flex flex-col overflow-hidden text-slate-200">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-start justify-between bg-slate-950/40">
        <div>
          <div className="flex items-center space-x-2">
            <Home className="w-4 h-4 text-indigo-400" />
            <span className="text-[10px] font-mono tracking-wider text-indigo-400 uppercase font-semibold">
              Property Record
            </span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">
            {property.property_reference}
          </h2>
          <p className="text-xs text-slate-400">{property.address}</p>
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
            <span className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Type</span>
            <span className="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
              {property.property_type}
            </span>
          </div>
          <div className="bg-slate-800/40 p-2.5 rounded-lg border border-slate-800">
            <span className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Status</span>
            <span className="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 uppercase">
              {property.status}
            </span>
          </div>
        </div>

        {/* Cadastral Parcel Link */}
        <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              <span>Underlying Parcel:</span>
            </span>
            <button
              onClick={() => onSelectParcel && onSelectParcel(property.parcel_id)}
              className="text-emerald-400 hover:text-emerald-300 font-mono font-medium underline flex items-center space-x-1"
            >
              <span>{property.parcel_code || property.parcel_number || property.parcel_id.substring(0, 8)}</span>
            </button>
          </div>
          {property.jurisdiction_name && (
            <div className="flex items-center justify-between text-slate-400">
              <span>Jurisdiction:</span>
              <span className="text-slate-200">{property.jurisdiction_name}</span>
            </div>
          )}
        </div>

        {/* Address & Locality */}
        <div className="space-y-2 bg-slate-800/40 p-3 rounded-lg border border-slate-800">
          <div className="flex items-start space-x-2">
            <MapPin className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-mono">Full Address</span>
              <span className="text-white font-medium">{property.address}</span>
            </div>
          </div>
          {property.locality && (
            <div className="flex justify-between pl-6">
              <span className="text-slate-400">Locality:</span>
              <span className="text-slate-200">{property.locality}</span>
            </div>
          )}
          {property.postal_code && (
            <div className="flex justify-between pl-6">
              <span className="text-slate-400">Postal Code:</span>
              <span className="font-mono text-slate-200">{property.postal_code}</span>
            </div>
          )}
        </div>

        {/* Description */}
        {property.description && (
          <div className="bg-slate-800/40 p-3 rounded-lg border border-slate-800 space-y-1">
            <span className="text-[10px] uppercase font-mono text-slate-400 block">Description / Notes</span>
            <p className="text-slate-300 leading-relaxed">{property.description}</p>
          </div>
        )}

        {/* Metadata */}
        <div className="text-[11px] text-slate-500 space-y-1 px-1">
          <div className="flex justify-between">
            <span>Created:</span>
            <span>{new Date(property.created_at).toLocaleDateString()}</span>
          </div>
          <div className="flex justify-between">
            <span>Property ID:</span>
            <span className="font-mono">{property.id.substring(0, 12)}...</span>
          </div>
        </div>
      </div>
    </div>
  );
};
