import React from 'react';
import { Layers, ChevronUp, ChevronDown, Split, Eye, EyeOff } from 'lucide-react';
import { CesiumFloorFeature } from '../../api/threed';

interface Props {
  floors: CesiumFloorFeature[];
  selectedFloorId: string | null;
  onSelectFloor: (floorId: string | null) => void;
  isExploded?: boolean;
  onToggleExploded?: (exploded: boolean) => void;
  isIsolated?: boolean;
  onToggleIsolated?: (isolated: boolean) => void;
}

export const FloorSelector: React.FC<Props> = ({
  floors,
  selectedFloorId,
  onSelectFloor,
  isExploded = false,
  onToggleExploded,
  isIsolated = false,
  onToggleIsolated,
}) => {
  if (!floors || floors.length === 0) return null;

  // Sort floors descending (top floor first, ground at bottom)
  const sortedFloors = [...floors].sort((a, b) => b.floor_number - a.floor_number);

  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/60 rounded-xl p-3 shadow-xl text-xs space-y-3 w-64">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-700/60">
        <div className="flex items-center gap-1.5 font-semibold text-slate-200">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>Vertical Floors ({floors.length})</span>
        </div>
        {selectedFloorId && (
          <button
            onClick={() => onSelectFloor(null)}
            className="text-[11px] text-cyan-400 hover:text-cyan-300 font-medium"
          >
            Reset
          </button>
        )}
      </div>

      {/* View Mode Controls */}
      <div className="flex items-center gap-2">
        {onToggleIsolated && (
          <button
            type="button"
            onClick={() => onToggleIsolated(!isIsolated)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-[11px] font-medium transition-all ${
              isIsolated
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700'
            }`}
            title="Isolate selected floor slab and hide other levels"
          >
            {isIsolated ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span>Isolate Floor</span>
          </button>
        )}

        {onToggleExploded && (
          <button
            type="button"
            onClick={() => onToggleExploded(!isExploded)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-[11px] font-medium transition-all ${
              isExploded
                ? 'bg-amber-600 text-white shadow-sm'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700'
            }`}
            title="Exploded vertical view separating each floor slab"
          >
            <Split className="w-3.5 h-3.5" />
            <span>Explode (Stack)</span>
          </button>
        )}
      </div>

      {/* Floor Stack List */}
      <div className="space-y-1 max-h-52 overflow-y-auto pr-1">
        {sortedFloors.map((floor) => {
          const isSelected = selectedFloorId === floor.floor_id;
          return (
            <button
              key={floor.floor_id}
              type="button"
              onClick={() => onSelectFloor(isSelected ? null : floor.floor_id)}
              className={`w-full text-left p-2 rounded-lg transition-all flex items-center justify-between ${
                isSelected
                  ? 'bg-cyan-950/80 border border-cyan-500/80 text-cyan-200'
                  : 'bg-slate-800/60 hover:bg-slate-800 border border-slate-700/40 text-slate-300'
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`w-6 h-6 flex items-center justify-center rounded text-xs font-mono font-bold ${
                    isSelected ? 'bg-cyan-500 text-slate-950' : 'bg-slate-700 text-slate-200'
                  }`}
                >
                  {floor.floor_number >= 0 ? `L${floor.floor_number}` : `B${Math.abs(floor.floor_number)}`}
                </span>
                <div>
                  <div className="font-medium text-xs truncate max-w-[110px]">
                    {floor.floor_name || `Level ${floor.floor_number}`}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    {floor.elevation_min_m.toFixed(1)}m – {floor.elevation_max_m.toFixed(1)}m (Δ{floor.height_m.toFixed(1)}m)
                  </div>
                </div>
              </div>

              <div className="text-right">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400">
                  {floor.floor_type}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
