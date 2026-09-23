import React from 'react';
import { Layers, Eye, EyeOff, ShieldAlert, Building2, Grid, Map } from 'lucide-react';

interface LayerControlsProps {
  layers: {
    boundaries: boolean;
    parcels: boolean;
    buildings: boolean;
    grid: boolean;
  };
  onToggleLayer: (layerName: keyof LayerControlsProps['layers']) => void;
}

export const LayerControls: React.FC<LayerControlsProps> = ({ layers, onToggleLayer }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur">
      <div className="flex items-center space-x-2 pb-3 mb-3 border-b border-slate-800">
        <Layers className="w-4 h-4 text-emerald-400" />
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
          Cadastral Layers
        </h3>
      </div>

      <div className="space-y-2">
        {/* Boundaries */}
        <button
          onClick={() => onToggleLayer('boundaries')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
            layers.boundaries
              ? 'bg-indigo-950/40 text-indigo-300 border border-indigo-800/60'
              : 'text-slate-500 hover:text-slate-400 hover:bg-slate-800/40'
          }`}
        >
          <div className="flex items-center space-x-2.5">
            <span className="w-3 h-0.5 border-t-2 border-dashed border-indigo-400"></span>
            <span>Administrative Boundaries</span>
          </div>
          {layers.boundaries ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
        </button>

        {/* Parcels */}
        <button
          onClick={() => onToggleLayer('parcels')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
            layers.parcels
              ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/60'
              : 'text-slate-500 hover:text-slate-400 hover:bg-slate-800/40'
          }`}
        >
          <div className="flex items-center space-x-2.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500/40 border border-emerald-400"></span>
            <span>Cadastral Parcels</span>
          </div>
          {layers.parcels ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
        </button>

        {/* Buildings */}
        <button
          onClick={() => onToggleLayer('buildings')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
            layers.buildings
              ? 'bg-sky-950/40 text-sky-300 border border-sky-800/60'
              : 'text-slate-500 hover:text-slate-400 hover:bg-slate-800/40'
          }`}
        >
          <div className="flex items-center space-x-2.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-sky-500/60 border border-sky-400"></span>
            <span>Building Footprints</span>
          </div>
          {layers.buildings ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
        </button>

        {/* Base Grid */}
        <button
          onClick={() => onToggleLayer('grid')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
            layers.grid
              ? 'bg-slate-800/60 text-slate-300 border border-slate-700'
              : 'text-slate-500 hover:text-slate-400 hover:bg-slate-800/40'
          }`}
        >
          <div className="flex items-center space-x-2.5">
            <Grid className="w-3.5 h-3.5 text-slate-400" />
            <span>Reference Grid</span>
          </div>
          {layers.grid ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] space-y-1.5 text-slate-400">
        <span className="block text-[10px] uppercase font-mono tracking-wider text-slate-500 mb-1">
          Land Use Legend
        </span>
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span>Residential</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-amber-400"></span>
          <span>Commercial</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-blue-400"></span>
          <span>Public / Civic</span>
        </div>
      </div>
    </div>
  );
};
