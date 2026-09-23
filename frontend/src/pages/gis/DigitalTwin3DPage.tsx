import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import * as Cesium from 'cesium';
import {
  Box,
  Map,
  RotateCcw,
  Compass,
  Layers,
  ChevronRight,
  Filter,
  RefreshCw,
  Info,
  FolderTree,
} from 'lucide-react';
import {
  threedApi,
  ThreeDSceneResponse,
  Building3DDetailResponse,
  Parcel3DDetailResponse,
  CesiumFloorFeature,
  CesiumUnitFeature,
} from '../../api/threed';
import { gisApi } from '../../api/gis';
import { Jurisdiction } from '../../types';
import { CesiumViewer } from '../../features/cesium/CesiumViewer';
import { CesiumInfoPanel } from '../../features/cesium/CesiumInfoPanel';
import { FloorSelector } from '../../features/cesium/FloorSelector';
import { UnitTreeExplorer } from '../../features/cesium/UnitTreeExplorer';
import {
  CesiumLayerControls,
  LayerConfig,
} from '../../features/cesium/CesiumLayerControls';
import { CesiumMeasurementTools } from '../../features/cesium/CesiumMeasurementTools';
import { cameraService } from '../../features/cesium/cameraService';

export const DigitalTwin3DPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const buildingIdParam = searchParams.get('building_id');
  const parcelIdParam = searchParams.get('parcel_id');
  const floorIdParam = searchParams.get('floor_id');
  const unitIdParam = searchParams.get('unit_id');

  // State: Jurisdictions
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [selectedJurisdictionId, setSelectedJurisdictionId] = useState<string>('');

  // State: 3D Scene Data
  const [sceneData, setSceneData] = useState<ThreeDSceneResponse | null>(null);
  const [isLoadingScene, setIsLoadingScene] = useState<boolean>(true);

  // State: Selected Entities & Details
  const [selectedBuildingId, setSelectedBuildingId] = useState<string | null>(buildingIdParam);
  const [selectedParcelId, setSelectedParcelId] = useState<string | null>(parcelIdParam);
  const [selectedFloorId, setSelectedFloorId] = useState<string | null>(floorIdParam);
  const [selectedUnitId, setSelectedUnitId] = useState<string | null>(unitIdParam);
  const [buildingDetail, setBuildingDetail] = useState<Building3DDetailResponse | null>(null);
  const [parcelDetail, setParcelDetail] = useState<Parcel3DDetailResponse | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);

  // Phase 4: Slicing & Vertical view controls
  const [isExploded, setIsExploded] = useState<boolean>(false);
  const [isIsolated, setIsIsolated] = useState<boolean>(false);
  const [showTreeExplorer, setShowTreeExplorer] = useState<boolean>(false);

  // State: Layer Configuration
  const [layerConfig, setLayerConfig] = useState<LayerConfig>({
    showBuildings: true,
    showParcels: true,
    showFloors: true,
    showUnits: true,
    colorMode: 'height',
    basemap: 'carto_dark',
    wireframe: true,
  });

  const viewerInstanceRef = useRef<Cesium.Viewer | null>(null);

  // 1. Fetch Jurisdictions
  useEffect(() => {
    const loadJurisdictions = async () => {
      try {
        const res = await gisApi.listJurisdictions();
        setJurisdictions(res.items || []);
      } catch (err) {
        console.error('Failed to load jurisdictions:', err);
      }
    };
    loadJurisdictions();
  }, []);

  // 2. Fetch 3D Scene
  const loadScene = useCallback(async () => {
    try {
      setIsLoadingScene(true);
      const data = await threedApi.getScene({
        jurisdiction_id: selectedJurisdictionId || undefined,
        limit: 200,
      });
      setSceneData(data);
    } catch (err) {
      console.error('Failed to fetch 3D scene:', err);
    } finally {
      setIsLoadingScene(false);
    }
  }, [selectedJurisdictionId]);

  useEffect(() => {
    loadScene();
  }, [loadScene]);

  // 3. Handle Building Selection
  const handleSelectBuilding = useCallback(
    async (buildingId: string | null) => {
      setSelectedBuildingId(buildingId);
      setSelectedParcelId(null);
      setParcelDetail(null);

      if (!buildingId) {
        setBuildingDetail(null);
        setSearchParams({});
        return;
      }

      setSearchParams({ building_id: buildingId });

      try {
        setIsLoadingDetail(true);
        const detail = await threedApi.getBuilding(buildingId);
        setBuildingDetail(detail);

        if (viewerInstanceRef.current && detail.cesium_extrusion) {
          cameraService.flyToBuilding(
            viewerInstanceRef.current,
            detail.cesium_extrusion.centroid,
            detail.cesium_extrusion.height
          );
        }
      } catch (err) {
        console.error('Failed to fetch building 3D detail:', err);
      } finally {
        setIsLoadingDetail(false);
      }
    },
    [setSearchParams]
  );

  // 4. Handle Parcel Selection
  const handleSelectParcel = useCallback(
    async (parcelId: string | null) => {
      setSelectedParcelId(parcelId);
      setSelectedBuildingId(null);
      setBuildingDetail(null);

      if (!parcelId) {
        setParcelDetail(null);
        setSearchParams({});
        return;
      }

      setSearchParams({ parcel_id: parcelId });

      try {
        setIsLoadingDetail(true);
        const detail = await threedApi.getParcel(parcelId);
        setParcelDetail(detail);

        if (viewerInstanceRef.current && detail.parcel.centroid) {
          cameraService.flyToParcel(viewerInstanceRef.current, detail.parcel.centroid);
        }
      } catch (err) {
        console.error('Failed to fetch parcel 3D detail:', err);
      } finally {
        setIsLoadingDetail(false);
      }
    },
    [setSearchParams]
  );

  // Sync initial URL params
  useEffect(() => {
    if (buildingIdParam && buildingIdParam !== selectedBuildingId) {
      handleSelectBuilding(buildingIdParam);
    } else if (parcelIdParam && parcelIdParam !== selectedParcelId) {
      handleSelectParcel(parcelIdParam);
    }
  }, [buildingIdParam, parcelIdParam]);

  // Height Updated Callback
  const handleHeightUpdated = (
    buildingId: string,
    newHeight: number,
    newBaseElevation: number
  ) => {
    // 1. Update sceneData locally for instant re-render
    if (sceneData) {
      const updatedBuildings = sceneData.buildings.map((b) => {
        if (b.building_id === buildingId) {
          return {
            ...b,
            height: newHeight,
            base_elevation: newBaseElevation,
            extruded_height: newBaseElevation + newHeight,
          };
        }
        return b;
      });
      setSceneData({
        ...sceneData,
        buildings: updatedBuildings,
      });
    }

    // 2. Refresh detail inspector
    handleSelectBuilding(buildingId);
  };

  const handleResetCamera = () => {
    if (viewerInstanceRef.current && sceneData?.scene?.center) {
      cameraService.resetCamera(viewerInstanceRef.current, sceneData.scene.center);
    }
  };

  return (
    <div className="relative w-full h-full flex flex-col bg-slate-950 overflow-hidden">
      {/* Top Floating Header HUD */}
      <div className="absolute top-3 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-3 pointer-events-auto">
          <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/70 rounded-xl px-4 py-2 shadow-2xl flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400">
              <Box className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold text-white tracking-wide">
                  3D Digital Twin Platform
                </h1>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 font-semibold">
                  LOD1 Extrusion
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Authoritative 2.5D Building Extrusions & Cadastral Vertices
              </p>
            </div>
          </div>

          {/* Jurisdiction Filter */}
          <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/70 rounded-xl px-3 py-1.5 shadow-xl flex items-center gap-2 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedJurisdictionId}
              onChange={(e) => setSelectedJurisdictionId(e.target.value)}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="" className="bg-slate-900">
                All Jurisdictions
              </option>
              {jurisdictions.map((j) => (
                <option key={j.id} value={j.id} className="bg-slate-900">
                  {j.name} ({j.code})
                </option>
              ))}
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={loadScene}
            disabled={isLoadingScene}
            className="bg-slate-900/90 backdrop-blur-md border border-slate-700/70 rounded-xl p-2.5 shadow-xl text-slate-300 hover:text-white hover:bg-slate-800 transition-all disabled:opacity-50"
            title="Refresh 3D Scene"
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingScene ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>

        {/* Right Action Controls */}
        <div className="flex items-center gap-2 pointer-events-auto">
          {selectedBuildingId && (
            <button
              onClick={() => setShowTreeExplorer(!showTreeExplorer)}
              className={`flex items-center gap-1.5 backdrop-blur-md border rounded-xl px-3.5 py-2 shadow-xl text-xs font-medium transition-all ${
                showTreeExplorer
                  ? 'bg-indigo-600 border-indigo-500 text-white'
                  : 'bg-slate-900/90 border-slate-700/70 text-slate-200 hover:text-white hover:bg-slate-800'
              }`}
              title="Toggle Building-Floor-Unit Hierarchy Tree"
            >
              <FolderTree className="w-3.5 h-3.5" />
              <span>Hierarchy Tree</span>
            </button>
          )}

          <button
            onClick={handleResetCamera}
            className="flex items-center gap-1.5 bg-slate-900/90 backdrop-blur-md border border-slate-700/70 rounded-xl px-3 py-2 shadow-xl text-xs text-slate-200 hover:text-white hover:bg-slate-800 transition-all"
            title="Reset Camera Preset"
          >
            <RotateCcw className="w-3.5 h-3.5 text-cyan-400" />
            <span>Reset View</span>
          </button>

          <button
            onClick={() => navigate('/cadastre')}
            className="flex items-center gap-1.5 bg-blue-600/90 hover:bg-blue-500 backdrop-blur-md rounded-xl px-3.5 py-2 shadow-xl text-xs text-white font-medium transition-all"
            title="Switch to 2D Cadastral Map"
          >
            <Map className="w-3.5 h-3.5" />
            <span>2D Cadastre Map</span>
          </button>
        </div>
      </div>

      {/* Main Cesium Viewport */}
      <div className="flex-1 w-full h-full relative">
        <CesiumViewer
          sceneData={sceneData}
          selectedBuildingId={selectedBuildingId}
          selectedParcelId={selectedParcelId}
          selectedFloorId={selectedFloorId}
          selectedUnitId={selectedUnitId}
          layerConfig={layerConfig}
          isExploded={isExploded}
          isIsolated={isIsolated}
          onSelectBuilding={handleSelectBuilding}
          onSelectParcel={handleSelectParcel}
          onSelectFloor={setSelectedFloorId}
          onSelectUnit={setSelectedUnitId}
          onViewerReady={(viewer) => {
            viewerInstanceRef.current = viewer;
          }}
        />

        {/* Loading Overlay */}
        {isLoadingScene && (
          <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm z-30 flex items-center justify-center">
            <div className="bg-slate-900 border border-slate-700/80 rounded-2xl p-6 shadow-2xl flex flex-col items-center gap-3">
              <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
              <div className="text-center">
                <h4 className="text-sm font-semibold text-white">Loading 3D Digital Twin...</h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Extruding cadastral footprints & vertical heights
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Left Inspector Panel Overlay */}
        <div className="absolute top-20 left-4 z-20 max-w-sm pointer-events-auto space-y-3">
          <CesiumInfoPanel
            buildingDetail={buildingDetail}
            parcelDetail={parcelDetail}
            selectedFloorId={selectedFloorId}
            selectedUnitId={selectedUnitId}
            isLoading={isLoadingDetail}
            onClose={() => {
              setSelectedBuildingId(null);
              setSelectedParcelId(null);
              setSelectedFloorId(null);
              setSelectedUnitId(null);
              setBuildingDetail(null);
              setParcelDetail(null);
              setSearchParams({});
            }}
            onHeightUpdated={handleHeightUpdated}
            onSelectBuilding={handleSelectBuilding}
            onSelectFloor={setSelectedFloorId}
            onSelectUnit={setSelectedUnitId}
          />

          {/* Vertical Floor Slicing / Isolation Selector */}
          {selectedBuildingId && sceneData?.floors && sceneData.floors.filter(f => f.building_id === selectedBuildingId).length > 0 && (
            <FloorSelector
              floors={sceneData.floors.filter(f => f.building_id === selectedBuildingId)}
              selectedFloorId={selectedFloorId}
              onSelectFloor={setSelectedFloorId}
              isExploded={isExploded}
              onToggleExploded={setIsExploded}
              isIsolated={isIsolated}
              onToggleIsolated={setIsIsolated}
            />
          )}
        </div>

        {/* Hierarchy Tree Overlay (Collapsible) */}
        {showTreeExplorer && selectedBuildingId && (
          <div className="absolute top-20 right-4 z-20 pointer-events-auto">
            <UnitTreeExplorer
              buildingReference={buildingDetail?.building.building_reference || 'Building'}
              floors={sceneData?.floors?.filter(f => f.building_id === selectedBuildingId) || []}
              units={sceneData?.units?.filter(u => (sceneData.floors || []).some(f => f.building_id === selectedBuildingId && f.floor_id === u.floor_id)) || []}
              selectedFloorId={selectedFloorId}
              selectedUnitId={selectedUnitId}
              onSelectFloor={setSelectedFloorId}
              onSelectUnit={setSelectedUnitId}
              onClose={() => setShowTreeExplorer(false)}
            />
          </div>
        )}

        {/* Right Floating Controls Overlay */}
        <div className="absolute bottom-6 right-4 z-20 flex flex-col items-end gap-3 pointer-events-auto">
          <CesiumMeasurementTools viewer={viewerInstanceRef.current} />
          <CesiumLayerControls config={layerConfig} onChange={setLayerConfig} />
        </div>
      </div>
    </div>
  );
};
