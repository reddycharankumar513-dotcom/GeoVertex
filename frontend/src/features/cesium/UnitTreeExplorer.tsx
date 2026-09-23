import React, { useState } from 'react';
import {
  FolderTree,
  ChevronRight,
  ChevronDown,
  Building,
  Layers,
  Home,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Search,
  Filter,
} from 'lucide-react';
import { CesiumFloorFeature, CesiumUnitFeature } from '../../api/threed';

interface Props {
  buildingReference?: string;
  floors: CesiumFloorFeature[];
  units: CesiumUnitFeature[];
  selectedFloorId: string | null;
  selectedUnitId: string | null;
  onSelectFloor: (floorId: string | null) => void;
  onSelectUnit: (unitId: string | null) => void;
  onClose?: () => void;
}

export const UnitTreeExplorer: React.FC<Props> = ({
  buildingReference = 'Building',
  floors,
  units,
  selectedFloorId,
  selectedUnitId,
  onSelectFloor,
  onSelectUnit,
  onClose,
}) => {
  const [expandedFloors, setExpandedFloors] = useState<Record<string, boolean>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [ownershipFilter, setOwnershipFilter] = useState<string>('ALL');

  const toggleFloor = (floorId: string) => {
    setExpandedFloors((prev) => ({
      ...prev,
      [floorId]: !prev[floorId],
    }));
  };

  // Group units by floor_id
  const unitsByFloor: Record<string, CesiumUnitFeature[]> = {};
  units.forEach((u) => {
    if (!unitsByFloor[u.floor_id]) {
      unitsByFloor[u.floor_id] = [];
    }
    unitsByFloor[u.floor_id].push(u);
  });

  // Filtered floors
  const sortedFloors = [...floors].sort((a, b) => b.floor_number - a.floor_number);

  const getOwnershipBadge = (status: string) => {
    switch (status) {
      case 'OWNED':
      case 'OCCUPIED':
        return { label: 'Occupied', color: 'bg-emerald-950 text-emerald-300 border-emerald-800/60' };
      case 'VACANT':
        return { label: 'Vacant', color: 'bg-amber-950 text-amber-300 border-amber-800/60' };
      case 'LEASED':
        return { label: 'Leased', color: 'bg-blue-950 text-blue-300 border-blue-800/60' };
      case 'MORTGAGED':
        return { label: 'Mortgaged', color: 'bg-purple-950 text-purple-300 border-purple-800/60' };
      default:
        return { label: status, color: 'bg-slate-800 text-slate-400 border-slate-700' };
    }
  };

  return (
    <div className="bg-slate-900/95 backdrop-blur-md border border-slate-700/80 rounded-xl p-4 shadow-2xl text-slate-200 w-80 sm:w-96 flex flex-col max-h-[80vh]">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
        <div className="flex items-center gap-2">
          <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400">
            <FolderTree className="w-4 h-4" />
          </span>
          <div>
            <h3 className="font-bold text-sm text-white">Cadastral Hierarchy</h3>
            <p className="text-[11px] text-slate-400 font-mono">{buildingReference}</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800"
          >
            ✕
          </button>
        )}
      </div>

      {/* Filter and Search */}
      <div className="py-2.5 space-y-2 border-b border-slate-700/60">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search unit / floor..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-800/80 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] pb-1">
          {['ALL', 'VACANT', 'OCCUPIED', 'LEASED'].map((filter) => (
            <button
              key={filter}
              onClick={() => setOwnershipFilter(filter)}
              className={`px-2 py-0.5 rounded-full border transition-colors whitespace-nowrap ${
                ownershipFilter === filter
                  ? 'bg-indigo-600 border-indigo-500 text-white font-medium'
                  : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {/* Tree Content */}
      <div className="flex-1 overflow-y-auto pt-2 space-y-1.5 pr-1">
        {/* Building Root Node */}
        <div className="flex items-center gap-2 p-1.5 rounded-lg bg-slate-800/40 text-xs font-semibold text-slate-300">
          <Building className="w-4 h-4 text-blue-400" />
          <span>{buildingReference}</span>
          <span className="ml-auto text-[10px] font-normal text-slate-500">
            {floors.length} Floors · {units.length} Units
          </span>
        </div>

        {/* Nested Floors */}
        <div className="pl-3 space-y-1">
          {sortedFloors.map((floor) => {
            const isFloorSelected = selectedFloorId === floor.floor_id;
            const isExpanded = expandedFloors[floor.floor_id] ?? (isFloorSelected || searchTerm !== '');
            const floorUnits = unitsByFloor[floor.floor_id] || [];

            const filteredUnits = floorUnits.filter((u) => {
              const matchesSearch =
                !searchTerm ||
                u.unit_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
                u.unit_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
                (floor.floor_name && floor.floor_name.toLowerCase().includes(searchTerm.toLowerCase()));

              const matchesFilter =
                ownershipFilter === 'ALL' ||
                u.ownership_status === ownershipFilter ||
                (ownershipFilter === 'OCCUPIED' && (u.ownership_status === 'OWNED' || u.ownership_status === 'OCCUPIED'));

              return matchesSearch && matchesFilter;
            });

            if (searchTerm && filteredUnits.length === 0 && !floor.floor_name?.toLowerCase().includes(searchTerm.toLowerCase())) {
              return null;
            }

            return (
              <div key={floor.floor_id} className="space-y-1">
                {/* Floor Node */}
                <div
                  className={`flex items-center justify-between p-1.5 rounded-lg cursor-pointer transition-colors text-xs ${
                    isFloorSelected
                      ? 'bg-cyan-950/80 border border-cyan-500/80 text-cyan-200'
                      : 'hover:bg-slate-800/60 text-slate-300'
                  }`}
                  onClick={() => {
                    toggleFloor(floor.floor_id);
                    onSelectFloor(isFloorSelected ? null : floor.floor_id);
                  }}
                >
                  <div className="flex items-center gap-1.5 truncate">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFloor(floor.floor_id);
                      }}
                      className="p-0.5 text-slate-400 hover:text-white"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5" />
                      )}
                    </button>
                    <Layers className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                    <span className="font-medium truncate">
                      {floor.floor_name || `Floor ${floor.floor_number}`}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 flex-shrink-0 text-[10px]">
                    <span className="font-mono text-slate-400">
                      {floor.elevation_min_m.toFixed(1)}–{floor.elevation_max_m.toFixed(1)}m
                    </span>
                    <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      {floorUnits.length}
                    </span>
                  </div>
                </div>

                {/* Subdivided Units */}
                {isExpanded && (
                  <div className="pl-6 space-y-1 border-l border-slate-700/40 ml-2">
                    {filteredUnits.length === 0 ? (
                      <div className="text-[11px] text-slate-500 italic py-1 pl-1">
                        No property units on this floor
                      </div>
                    ) : (
                      filteredUnits.map((u) => {
                        const isUnitSelected = selectedUnitId === u.unit_id;
                        const badge = getOwnershipBadge(u.ownership_status);

                        return (
                          <div
                            key={u.unit_id}
                            onClick={() => onSelectUnit(isUnitSelected ? null : u.unit_id)}
                            className={`flex items-center justify-between p-1.5 rounded-lg cursor-pointer transition-colors text-xs ${
                              isUnitSelected
                                ? 'bg-amber-950/80 border border-amber-500/80 text-amber-200'
                                : 'hover:bg-slate-800/60 text-slate-300'
                            }`}
                          >
                            <div className="flex items-center gap-1.5 truncate">
                              <Home className="w-3 h-3 text-amber-400 flex-shrink-0" />
                              <span className="font-medium truncate">{u.unit_number}</span>
                              <span className="text-[10px] text-slate-400 font-mono">
                                ({u.use_category})
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5 flex-shrink-0">
                              <span className="text-[10px] font-mono text-slate-400">
                                {u.gross_area_sqm.toFixed(1)}m²
                              </span>
                              <span
                                className={`text-[9px] px-1.5 py-0.5 rounded border font-medium ${badge.color}`}
                              >
                                {badge.label}
                              </span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
