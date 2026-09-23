import React, { useState, useEffect, useCallback } from 'react';
import {
  Layers,
  Search,
  Plus,
  FileCode,
  RefreshCw,
  MapPin,
  Compass,
  AlertCircle,
  Check,
  X,
  Maximize,
  Filter,
} from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { gisApi } from '../../api/gis';
import {
  GeoJSONFeatureCollection,
  Jurisdiction,
  Parcel,
  Property,
  Building,
  SpatialIdentifyResponse,
} from '../../types';
import { MapCanvas } from '../../features/gis/MapCanvas';
import { LayerControls } from '../../features/gis/LayerControls';
import { SearchBar } from '../../features/gis/SearchBar';
import { ParcelDetailPanel } from '../../features/gis/ParcelDetailPanel';
import { PropertyDetailPanel } from '../../features/gis/PropertyDetailPanel';
import { BuildingDetailPanel } from '../../features/gis/BuildingDetailPanel';
import { GeometryDrawModal } from '../../features/gis/GeometryDrawModal';
import { ImportExportModal } from '../../features/gis/ImportExportModal';

export const CadastreMapPage: React.FC = () => {
  const { user } = useAuth();
  const canEdit =
    user?.role === 'ADMIN' || user?.role === 'GOVERNMENT_OFFICER' || user?.role === 'SURVEYOR';

  // State: Jurisdictions
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [selectedJurisdictionId, setSelectedJurisdictionId] = useState<string>('');

  // State: Map Data Layers
  const [boundaries, setBoundaries] = useState<GeoJSONFeatureCollection | null>(null);
  const [parcels, setParcels] = useState<GeoJSONFeatureCollection | null>(null);
  const [buildings, setBuildings] = useState<GeoJSONFeatureCollection | null>(null);
  const [isLoadingLayers, setIsLoadingLayers] = useState<boolean>(true);

  // State: Layer Visibility
  const [visibleLayers, setVisibleLayers] = useState({
    boundaries: true,
    parcels: true,
    buildings: true,
    grid: true,
  });
  const [showLayerControls, setShowLayerControls] = useState<boolean>(true);

  // State: Selected Feature
  const [selectedFeature, setSelectedFeature] = useState<{ type: string; id: string } | null>(null);
  const [selectedParcel, setSelectedParcel] = useState<Parcel | null>(null);
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [selectedBuilding, setSelectedBuilding] = useState<Building | null>(null);
  const [identifyResults, setIdentifyResults] = useState<SpatialIdentifyResponse | null>(null);

  // State: Map Navigation / Focus
  const [focusBounds, setFocusBounds] = useState<[number, number, number, number] | null>(null);

  // State: Interactive Digitization / Drawing
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);
  const [showDrawModal, setShowDrawModal] = useState<boolean>(false);

  // State: Import/Export Modal
  const [showImportExportModal, setShowImportExportModal] = useState<boolean>(false);

  // Load Jurisdictions
  useEffect(() => {
    const fetchJurisdictions = async () => {
      try {
        const res = await gisApi.listJurisdictions();
        setJurisdictions(res.items);
        if (res.items.length > 0 && !selectedJurisdictionId) {
          // Default to first jurisdiction
          setSelectedJurisdictionId(res.items[0].id);
        }
      } catch (err) {
        console.error('Failed to load jurisdictions:', err);
      }
    };
    fetchJurisdictions();
  }, []);

  // Fetch Map Layers
  const loadMapData = useCallback(async () => {
    setIsLoadingLayers(true);
    try {
      const [boundRes, parcRes, bldgRes] = await Promise.all([
        gisApi.getMapBoundaries(selectedJurisdictionId || undefined),
        gisApi.getMapParcels(undefined, selectedJurisdictionId || undefined),
        gisApi.getMapBuildings(undefined),
      ]);
      setBoundaries(boundRes);
      setParcels(parcRes);
      setBuildings(bldgRes);
    } catch (err) {
      console.error('Failed to load cadastral map layers:', err);
    } finally {
      setIsLoadingLayers(false);
    }
  }, [selectedJurisdictionId]);

  useEffect(() => {
    loadMapData();
  }, [loadMapData]);

  // Handle Layer Visibility Toggle
  const handleToggleLayer = (layerName: keyof typeof visibleLayers) => {
    setVisibleLayers((prev) => ({ ...prev, [layerName]: !prev[layerName] }));
  };

  // Handle Feature Selection
  const handleSelectFeature = async (type: string, id: string, featureData?: any) => {
    setSelectedFeature({ type, id });
    setIdentifyResults(null);

    try {
      if (type === 'PARCEL') {
        const p = await gisApi.getParcel(id);
        setSelectedParcel(p);
        setSelectedProperty(null);
        setSelectedBuilding(null);

        // Zoom to parcel bounds if geometry coordinates available
        if (featureData?.geometry?.coordinates?.[0]) {
          const coords = featureData.geometry.coordinates[0];
          let minLon = coords[0][0], maxLon = coords[0][0];
          let minLat = coords[0][1], maxLat = coords[0][1];
          coords.forEach(([lon, lat]: [number, number]) => {
            if (lon < minLon) minLon = lon;
            if (lon > maxLon) maxLon = lon;
            if (lat < minLat) minLat = lat;
            if (lat > maxLat) maxLat = lat;
          });
          setFocusBounds([minLon, minLat, maxLon, maxLat]);
        }
      } else if (type === 'BUILDING') {
        const b = await gisApi.getBuilding(id);
        setSelectedBuilding(b);
        setSelectedParcel(null);
        setSelectedProperty(null);
      } else if (type === 'PROPERTY') {
        const pr = await gisApi.getProperty(id);
        setSelectedProperty(pr);
        setSelectedParcel(null);
        setSelectedBuilding(null);
      }
    } catch (err) {
      console.error('Failed to load feature details:', err);
    }
  };

  // Handle Map Coordinate Click (Identify tool)
  const handleMapClick = async (lon: number, lat: number) => {
    if (isDrawing) return; // In drawing mode, clicks add vertices
    try {
      const identify = await gisApi.identify(lon, lat, 40);
      if (identify.parcels.length > 0) {
        // Auto-select nearest parcel
        handleSelectFeature('PARCEL', identify.parcels[0].id);
      } else if (identify.buildings.length > 0) {
        handleSelectFeature('BUILDING', identify.buildings[0].id);
      } else {
        // No features clicked: clear selection
        setSelectedFeature(null);
        setSelectedParcel(null);
        setSelectedProperty(null);
        setSelectedBuilding(null);
        setIdentifyResults(identify);
      }
    } catch (err) {
      console.error('Identify failed:', err);
    }
  };

  // Drawing tools
  const handleStartDrawing = () => {
    setIsDrawing(true);
    setDrawnPoints([]);
    setSelectedFeature(null);
    setSelectedParcel(null);
  };

  const handleCancelDrawing = () => {
    setIsDrawing(false);
    setDrawnPoints([]);
  };

  const handleAddDrawnPoint = (lon: number, lat: number) => {
    setDrawnPoints((prev) => [...prev, [lon, lat]]);
  };

  const handleFinishDrawing = () => {
    if (drawnPoints.length < 3) {
      alert('A parcel polygon requires at least 3 vertices.');
      return;
    }
    setShowDrawModal(true);
  };

  const handleParcelSaved = (newParcel: Parcel) => {
    setShowDrawModal(false);
    setIsDrawing(false);
    setDrawnPoints([]);
    loadMapData();
    handleSelectFeature('PARCEL', newParcel.id);
  };

  const handleDeleteParcel = async (id: string) => {
    await gisApi.deleteParcel(id);
    setSelectedFeature(null);
    setSelectedParcel(null);
    loadMapData();
  };

  return (
    <div className="relative h-full flex flex-col bg-slate-950 overflow-hidden select-none">
      {/* Top Controls Header */}
      <header className="h-14 bg-slate-900/90 border-b border-slate-800 px-4 flex items-center justify-between z-20 backdrop-blur-md">
        {/* Left: Jurisdiction Selector & Search */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 text-xs text-slate-300">
            <Filter className="w-3.5 h-3.5 text-emerald-400" />
            <select
              value={selectedJurisdictionId}
              onChange={(e) => setSelectedJurisdictionId(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-emerald-500 font-medium"
            >
              <option value="">All Jurisdictions</option>
              {jurisdictions.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.name} ({j.code})
                </option>
              ))}
            </select>
          </div>

          <SearchBar
            onSelectResult={(type: 'PARCEL' | 'PROPERTY' | 'BUILDING', id: string, item: any) =>
              handleSelectFeature(type, id, item)
            }
          />
        </div>

        {/* Right: Tools & Actions */}
        <div className="flex items-center space-x-2.5">
          {/* Layer Toggle */}
          <button
            onClick={() => setShowLayerControls(!showLayerControls)}
            className={`px-2.5 py-1.5 rounded-lg border text-xs font-medium flex items-center space-x-1.5 transition ${
              showLayerControls
                ? 'bg-slate-800 text-white border-slate-600'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-emerald-400" />
            <span>Layers</span>
          </button>

          {/* Digitize Parcel (Editor role only) */}
          {canEdit && !isDrawing && (
            <button
              onClick={handleStartDrawing}
              className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold flex items-center space-x-1.5 transition shadow-sm shadow-emerald-500/20"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Digitize Parcel</span>
            </button>
          )}

          {/* Import / Export (Editor role only) */}
          {canEdit && (
            <button
              onClick={() => setShowImportExportModal(true)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 flex items-center space-x-1.5 transition"
            >
              <FileCode className="w-3.5 h-3.5 text-sky-400" />
              <span>Import / Export</span>
            </button>
          )}

          {/* Refresh */}
          <button
            onClick={loadMapData}
            title="Refresh Map Layers"
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingLayers ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>
      </header>

      {/* Interactive Drawing Mode Banner */}
      {isDrawing && (
        <div className="bg-emerald-950/90 border-b border-emerald-800/80 px-4 py-2 flex items-center justify-between text-xs text-emerald-200 z-20 backdrop-blur">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span className="font-semibold">Interactive Digitization Mode:</span>
            <span>
              Click on the map canvas to place parcel boundary vertices ({drawnPoints.length} vertices placed).
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleFinishDrawing}
              disabled={drawnPoints.length < 3}
              className="px-3 py-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded text-xs transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Finish Polygon ({drawnPoints.length} pts)
            </button>
            <button
              onClick={handleCancelDrawing}
              className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Main Map Viewport */}
      <div className="relative flex-1 w-full h-full overflow-hidden">
        <MapCanvas
          boundaries={boundaries}
          parcels={parcels}
          buildings={buildings}
          visibleLayers={visibleLayers}
          selectedFeature={selectedFeature}
          onSelectFeature={handleSelectFeature}
          onMapClick={handleMapClick}
          isDrawing={isDrawing}
          drawnPoints={drawnPoints}
          onAddDrawnPoint={handleAddDrawnPoint}
          focusBounds={focusBounds}
        />

        {/* Floating Layer Controls (Top-Left) */}
        {showLayerControls && (
          <div className="absolute top-4 left-4 z-10 w-64">
            <LayerControls layers={visibleLayers} onToggleLayer={handleToggleLayer} />
          </div>
        )}

        {/* Floating Feature Detail Panel (Top-Right) */}
        {selectedParcel && (
          <div className="absolute top-4 right-4 z-10">
            <ParcelDetailPanel
              parcel={selectedParcel}
              userRole={user?.role}
              onClose={() => {
                setSelectedParcel(null);
                setSelectedFeature(null);
              }}
              onDeleteParcel={handleDeleteParcel}
              onSelectProperty={(propId) => handleSelectFeature('PROPERTY', propId)}
              onSelectBuilding={(bldgId) => handleSelectFeature('BUILDING', bldgId)}
              onRefresh={loadMapData}
            />
          </div>
        )}

        {selectedProperty && (
          <div className="absolute top-4 right-4 z-10">
            <PropertyDetailPanel
              property={selectedProperty}
              onClose={() => {
                setSelectedProperty(null);
                setSelectedFeature(null);
              }}
              onSelectParcel={(parcelId) => handleSelectFeature('PARCEL', parcelId)}
            />
          </div>
        )}

        {selectedBuilding && (
          <div className="absolute top-4 right-4 z-10">
            <BuildingDetailPanel
              building={selectedBuilding}
              onClose={() => {
                setSelectedBuilding(null);
                setSelectedFeature(null);
              }}
              onSelectParcel={(parcelId) => handleSelectFeature('PARCEL', parcelId)}
            />
          </div>
        )}

        {/* Identify Empty Result Notification */}
        {identifyResults && identifyResults.parcels.length === 0 && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 bg-slate-900/90 border border-slate-800 text-slate-300 px-4 py-2 rounded-xl shadow-lg backdrop-blur text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            <span>
              No cadastral parcels identified at ({identifyResults.point.longitude.toFixed(5)},{' '}
              {identifyResults.point.latitude.toFixed(5)}).
            </span>
            <button
              onClick={() => setIdentifyResults(null)}
              className="text-slate-400 hover:text-white ml-2"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Modals */}
      {showDrawModal && (
        <GeometryDrawModal
          points={drawnPoints}
          jurisdictions={jurisdictions}
          selectedJurisdictionId={selectedJurisdictionId}
          onClose={() => setShowDrawModal(false)}
          onSaved={handleParcelSaved}
        />
      )}

      {showImportExportModal && (
        <ImportExportModal
          jurisdictions={jurisdictions}
          selectedJurisdictionId={selectedJurisdictionId}
          onClose={() => setShowImportExportModal(false)}
          onImportCompleted={loadMapData}
        />
      )}
    </div>
  );
};
export default CadastreMapPage;
