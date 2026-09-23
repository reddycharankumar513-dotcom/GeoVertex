import React from 'react';
import { Layers, Eye, Palette, Map as MapIcon } from 'lucide-react';

export type ColorMode = 'height' | 'type' | 'neutral';
export type BasemapMode = 'osm' | 'carto_dark' | 'carto_positron';

export interface LayerConfig {
  showBuildings: boolean;
  showParcels: boolean;
  colorMode: ColorMode;
  basemap: BasemapMode;
  wireframe: boolean;
}

interface Props {
  config: LayerConfig;
  onChange: (newConfig: LayerConfig) => void;
}

export const CesiumLayerControls: React.FC<Props> = ({ config, onChange }) => {
  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/60 rounded-lg p-3 shadow-xl text-xs space-y-3 w-64">
      <div className="font-semibold text-slate-300 flex items-center gap-1.5 pb-1.5 border-b border-slate-700/60">
        <Layers className="w-3.5 h-3.5 text-blue-400" />
        <span>3D Scene & Layers</span>
      </div>

      {/* Layer Visibility */}
      <div className="space-y-1.5">
        <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1">
          <Eye className="w-3 h-3" /> Visibility
        </div>
        <label className="flex items-center justify-between p-1.5 rounded hover:bg-slate-800 cursor-pointer">
          <span className="text-slate-200">3D Buildings</span>
          <input
            type="checkbox"
            checked={config.showBuildings}
            onChange={(e) => onChange({ ...config, showBuildings: e.target.checked })}
            className="rounded border-slate-700 bg-slate-800 text-blue-600 focus:ring-blue-500"
          />
        </label>
        <label className="flex items-center justify-between p-1.5 rounded hover:bg-slate-800 cursor-pointer">
          <span className="text-slate-200">Cadastral Parcels</span>
          <input
            type="checkbox"
            checked={config.showParcels}
            onChange={(e) => onChange({ ...config, showParcels: e.target.checked })}
            className="rounded border-slate-700 bg-slate-800 text-blue-600 focus:ring-blue-500"
          />
        </label>
        <label className="flex items-center justify-between p-1.5 rounded hover:bg-slate-800 cursor-pointer">
          <span className="text-slate-200">Wireframe Edges</span>
          <input
            type="checkbox"
            checked={config.wireframe}
            onChange={(e) => onChange({ ...config, wireframe: e.target.checked })}
            className="rounded border-slate-700 bg-slate-800 text-blue-600 focus:ring-blue-500"
          />
        </label>
      </div>

      {/* Color Mode */}
      <div className="space-y-1.5">
        <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1">
          <Palette className="w-3 h-3" /> Building Symbology
        </div>
        <div className="grid grid-cols-3 gap-1">
          {(['height', 'type', 'neutral'] as ColorMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => onChange({ ...config, colorMode: mode })}
              className={`py-1 px-1.5 rounded text-center capitalize transition-all ${
                config.colorMode === mode
                  ? 'bg-blue-600 text-white font-medium shadow-sm'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Basemap Selection */}
      <div className="space-y-1.5">
        <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1">
          <MapIcon className="w-3 h-3" /> Basemap
        </div>
        <select
          value={config.basemap}
          onChange={(e) => onChange({ ...config, basemap: e.target.value as BasemapMode })}
          className="w-full bg-slate-800 border border-slate-700 rounded p-1.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="carto_dark">Carto Dark Matter (3D Glow)</option>
          <option value="carto_positron">Carto Positron (Light)</option>
          <option value="osm">OpenStreetMap Standard</option>
        </select>
      </div>
    </div>
  );
};
