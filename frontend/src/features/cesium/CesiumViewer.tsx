/// <reference types="vite/client" />
import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { CesiumExtrusionFeature, ThreeDSceneResponse } from '../../api/threed';
import { LayerConfig } from './CesiumLayerControls';
import { cameraService } from './cameraService';

// Initialize Cesium Ion token (optional fallback)
const ionToken = (import.meta as any).env?.VITE_CESIUM_ION_TOKEN;
if (ionToken) {
  Cesium.Ion.defaultAccessToken = ionToken;
}

interface Props {
  sceneData: ThreeDSceneResponse | null;
  selectedBuildingId: string | null;
  selectedParcelId: string | null;
  layerConfig: LayerConfig;
  onSelectBuilding: (buildingId: string | null) => void;
  onSelectParcel: (parcelId: string | null) => void;
  onViewerReady?: (viewer: Cesium.Viewer) => void;
}

const getBasemapProvider = (basemap: string): Cesium.ImageryProvider => {
  switch (basemap) {
    case 'carto_dark':
      return new Cesium.UrlTemplateImageryProvider({
        url: 'https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png',
        subdomains: ['a', 'b', 'c', 'd'],
      });
    case 'carto_positron':
      return new Cesium.UrlTemplateImageryProvider({
        url: 'https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png',
        subdomains: ['a', 'b', 'c', 'd'],
      });
    case 'osm':
    default:
      return new Cesium.UrlTemplateImageryProvider({
        url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      });
  }
};

const getBuildingColor = (
  feature: CesiumExtrusionFeature,
  mode: string,
  isSelected: boolean
): Cesium.Color => {
  if (isSelected) {
    return Cesium.Color.fromCssColorString('#facc15').withAlpha(0.95); // Bright Amber/Yellow
  }

  if (mode === 'height') {
    const h = feature.height;
    if (h < 20) return Cesium.Color.fromCssColorString('#10b981').withAlpha(0.85); // Emerald (<20m)
    if (h < 35) return Cesium.Color.fromCssColorString('#06b6d4').withAlpha(0.85); // Cyan (20-35m)
    if (h < 50) return Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.85); // Amber (35-50m)
    return Cesium.Color.fromCssColorString('#ef4444').withAlpha(0.85); // Red (>50m)
  }

  if (mode === 'type') {
    switch (feature.building_type) {
      case 'COMMERCIAL':
        return Cesium.Color.fromCssColorString('#3b82f6').withAlpha(0.85); // Blue
      case 'RESIDENTIAL':
        return Cesium.Color.fromCssColorString('#10b981').withAlpha(0.85); // Emerald
      case 'MIXED_USE':
        return Cesium.Color.fromCssColorString('#8b5cf6').withAlpha(0.85); // Purple
      case 'INDUSTRIAL':
        return Cesium.Color.fromCssColorString('#64748b').withAlpha(0.85); // Slate
      default:
        return Cesium.Color.fromCssColorString('#0ea5e9').withAlpha(0.85);
    }
  }

  // Neutral architectural
  return Cesium.Color.fromCssColorString('#cbd5e1').withAlpha(0.88);
};

export const CesiumViewer: React.FC<Props> = ({
  sceneData,
  selectedBuildingId,
  selectedParcelId,
  layerConfig,
  onSelectBuilding,
  onSelectParcel,
  onViewerReady,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const buildingEntitiesRef = useRef<Map<string, Cesium.Entity>>(new Map());
  const parcelEntitiesRef = useRef<Map<string, Cesium.Entity>>(new Map());

  // Mouse HUD coordinates
  const [hudCoords, setHudCoords] = useState<{ lon: number; lat: number; alt: number } | null>(null);

  // 1. Initialize Cesium Viewer
  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return;

    const viewer = new Cesium.Viewer(containerRef.current, {
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      selectionIndicator: false,
      navigationHelpButton: false,
      animation: false,
      timeline: false,
      sceneModePicker: false,
      fullscreenButton: false,
      scene3DOnly: true,
      baseLayer: new Cesium.ImageryLayer(getBasemapProvider(layerConfig.basemap)),
    });

    // Remove credits container clutter
    const creditContainer = viewer.bottomContainer as HTMLElement | undefined;
    if (creditContainer && creditContainer.style) {
      creditContainer.style.display = 'none';
    }

    viewer.scene.globe.depthTestAgainstTerrain = false;
    viewerRef.current = viewer;

    if (onViewerReady) {
      onViewerReady(viewer);
    }

    // Interactive Click Handler
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

    handler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
      const picked = viewer.scene.pick(click.position);
      if (Cesium.defined(picked) && picked.id && picked.id.properties) {
        const entityType = picked.id.properties.entityType?.getValue();
        if (entityType === 'building') {
          const bId = picked.id.properties.buildingId?.getValue();
          onSelectBuilding(bId);
          return;
        }
        if (entityType === 'parcel') {
          const pId = picked.id.properties.parcelId?.getValue();
          onSelectParcel(pId);
          return;
        }
      }
      // Clicked background / empty ground
      onSelectBuilding(null);
      onSelectParcel(null);
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    // Mouse Move HUD
    handler.setInputAction((movement: { endPosition: Cesium.Cartesian2 }) => {
      const ray = viewer.camera.getPickRay(movement.endPosition);
      if (!ray) return;
      const cartesian = viewer.scene.globe.pick(ray, viewer.scene);
      if (cartesian) {
        const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
        setHudCoords({
          lon: parseFloat(Cesium.Math.toDegrees(cartographic.longitude).toFixed(6)),
          lat: parseFloat(Cesium.Math.toDegrees(cartographic.latitude).toFixed(6)),
          alt: parseFloat(cartographic.height.toFixed(1)),
        });
      }
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

    return () => {
      handler.destroy();
      if (viewer && !viewer.isDestroyed()) {
        viewer.destroy();
      }
      viewerRef.current = null;
    };
  }, []);

  // 2. Basemap update
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    viewer.imageryLayers.removeAll();
    viewer.imageryLayers.add(new Cesium.ImageryLayer(getBasemapProvider(layerConfig.basemap)));
  }, [layerConfig.basemap]);

  // 3. Render Entities (Buildings and Parcels)
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed() || !sceneData) return;

    // Clear previous entities
    buildingEntitiesRef.current.forEach((entity) => viewer.entities.remove(entity));
    buildingEntitiesRef.current.clear();

    parcelEntitiesRef.current.forEach((entity) => viewer.entities.remove(entity));
    parcelEntitiesRef.current.clear();

    // A. Render 2D Parcels
    if (layerConfig.showParcels && sceneData.parcels) {
      sceneData.parcels.forEach((p) => {
        if (!p.geometry || !p.geometry.coordinates) return;

        const rings =
          p.geometry.type === 'Polygon'
            ? [p.geometry.coordinates[0]]
            : p.geometry.type === 'MultiPolygon'
            ? p.geometry.coordinates.map((poly: any) => poly[0])
            : [];

        rings.forEach((ringCoords: number[][], idx: number) => {
          const flatCoords: number[] = [];
          ringCoords.forEach((pt: number[]) => {
            flatCoords.push(pt[0], pt[1]);
          });

          const isSelected = selectedParcelId === p.id;
          const entity = viewer.entities.add({
            name: `Parcel ${p.properties?.parcel_code || p.id}`,
            properties: new Cesium.PropertyBag({
              entityType: 'parcel',
              parcelId: p.id,
              parcelCode: p.properties?.parcel_code,
            }),
            polygon: {
              hierarchy: Cesium.Cartesian3.fromDegreesArray(flatCoords),
              height: 0.1,
              material: isSelected
                ? Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.35)
                : Cesium.Color.fromCssColorString('#0284c7').withAlpha(0.12),
              outline: true,
              outlineColor: isSelected
                ? Cesium.Color.YELLOW
                : Cesium.Color.fromCssColorString('#38bdf8').withAlpha(0.7),
              outlineWidth: 2,
            },
          });
          parcelEntitiesRef.current.set(`${p.id}_${idx}`, entity);
        });
      });
    }

    // B. Render 3D Extruded Buildings
    if (layerConfig.showBuildings && sceneData.buildings) {
      sceneData.buildings.forEach((bldg) => {
        bldg.rings.forEach((polyRing, rIdx) => {
          const exterior = Cesium.Cartesian3.fromDegreesArray(polyRing.exterior);
          const holes = polyRing.holes
            ? polyRing.holes.map((h) => new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(h)))
            : [];
          const hierarchy = new Cesium.PolygonHierarchy(exterior, holes);

          const isSelected = selectedBuildingId === bldg.building_id;
          const fillColor = getBuildingColor(bldg, layerConfig.colorMode, isSelected);

          const entity = viewer.entities.add({
            name: bldg.building_reference,
            properties: new Cesium.PropertyBag({
              entityType: 'building',
              buildingId: bldg.building_id,
              buildingReference: bldg.building_reference,
              height: bldg.height,
            }),
            polygon: {
              hierarchy: hierarchy,
              height: bldg.base_elevation,
              extrudedHeight: bldg.extruded_height,
              material: fillColor,
              outline: true,
              outlineColor: isSelected
                ? Cesium.Color.WHITE
                : layerConfig.wireframe
                ? Cesium.Color.fromCssColorString('#0f172a')
                : Cesium.Color.fromCssColorString('#334155').withAlpha(0.6),
              outlineWidth: isSelected ? 3 : 1,
            },
          });

          buildingEntitiesRef.current.set(`${bldg.building_id}_${rIdx}`, entity);
        });
      });
    }

    // Initialize initial camera preset if available and first load
    if (sceneData.scene && sceneData.scene.center) {
      cameraService.resetCamera(viewer, sceneData.scene.center);
    }
  }, [sceneData, layerConfig, selectedBuildingId, selectedParcelId]);

  return (
    <div className="relative w-full h-full overflow-hidden select-none bg-slate-950">
      <div ref={containerRef} className="w-full h-full" />

      {/* Coordinate & Altitude HUD */}
      {hudCoords && (
        <div className="absolute bottom-3 left-3 z-10 bg-slate-900/85 backdrop-blur border border-slate-700/60 rounded px-2.5 py-1 text-[11px] font-mono text-slate-300 pointer-events-none shadow-md flex items-center gap-3">
          <span>Lon: {hudCoords.lon}°</span>
          <span>Lat: {hudCoords.lat}°</span>
          <span className="text-cyan-400">Alt: {hudCoords.alt} m</span>
          <span className="text-slate-500">EPSG:4326</span>
        </div>
      )}
    </div>
  );
};
