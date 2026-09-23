import React, { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Crosshair, MapPin } from 'lucide-react';
import { GeoJSONFeatureCollection } from '../../types';

interface MapCanvasProps {
  boundaries?: GeoJSONFeatureCollection | null;
  parcels?: GeoJSONFeatureCollection | null;
  buildings?: GeoJSONFeatureCollection | null;
  visibleLayers: {
    boundaries: boolean;
    parcels: boolean;
    buildings: boolean;
    grid: boolean;
  };
  selectedFeature: { type: string; id: string } | null;
  onSelectFeature: (type: string, id: string, feature: any) => void;
  onMapClick: (lon: number, lat: number) => void;
  isDrawing: boolean;
  drawnPoints: [number, number][];
  onAddDrawnPoint: (lon: number, lat: number) => void;
  focusBounds?: [number, number, number, number] | null; // [minLon, minLat, maxLon, maxLat]
}

export const MapCanvas: React.FC<MapCanvasProps> = ({
  boundaries,
  parcels,
  buildings,
  visibleLayers,
  selectedFeature,
  onSelectFeature,
  onMapClick,
  isDrawing,
  drawnPoints,
  onAddDrawnPoint,
  focusBounds,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Center & Zoom state (EPSG:4326 center)
  const [center, setCenter] = useState<[number, number]>([78.4880, 17.3855]);
  const [zoom, setZoom] = useState<number>(18000); // Scale factor for projection
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [mouseCoord, setMouseCoord] = useState<[number, number] | null>(null);

  // Resize listener
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // Projection: [lon, lat] -> [x, y] in container pixels
  const project = useCallback(
    (lon: number, lat: number): [number, number] => {
      const x = dimensions.width / 2 + (lon - center[0]) * zoom;
      // Latitude is inverted in screen space
      const y = dimensions.height / 2 - (lat - center[1]) * zoom * 1.05;
      return [x, y];
    },
    [dimensions, center, zoom]
  );

  // Inverse projection: [x, y] -> [lon, lat]
  const unproject = useCallback(
    (x: number, y: number): [number, number] => {
      const lon = center[0] + (x - dimensions.width / 2) / zoom;
      const lat = center[1] - (y - dimensions.height / 2) / (zoom * 1.05);
      return [Number(lon.toFixed(6)), Number(lat.toFixed(6))];
    },
    [dimensions, center, zoom]
  );

  // Handle focusBounds changes
  useEffect(() => {
    if (focusBounds) {
      const [minLon, minLat, maxLon, maxLat] = focusBounds;
      const midLon = (minLon + maxLon) / 2;
      const midLat = (minLat + maxLat) / 2;
      setCenter([midLon, midLat]);
      const spanLon = Math.max(maxLon - minLon, 0.002);
      const spanLat = Math.max(maxLat - minLat, 0.002);
      const newZoom = Math.min(
        (dimensions.width * 0.7) / spanLon,
        (dimensions.height * 0.7) / (spanLat * 1.05)
      );
      setZoom(Math.max(12000, Math.min(newZoom, 80000)));
    }
  }, [focusBounds, dimensions]);

  // Mouse wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.2 : 0.83;
    setZoom((prev) => Math.max(4000, Math.min(prev * factor, 150000)));
  };

  // Mouse pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0 && !isDrawing) {
      setIsPanning(true);
      setPanStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setMouseCoord(unproject(x, y));
    }

    if (isPanning && !isDrawing) {
      const dx = e.clientX - panStart.x;
      const dy = e.clientY - panStart.y;
      setPanStart({ x: e.clientX, y: e.clientY });
      setCenter(([cLon, cLat]) => [
        cLon - dx / zoom,
        cLat + dy / (zoom * 1.05),
      ]);
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  const handleClick = (e: React.MouseEvent) => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const [lon, lat] = unproject(x, y);

      if (isDrawing) {
        onAddDrawnPoint(lon, lat);
      } else {
        onMapClick(lon, lat);
      }
    }
  };

  // SVG path generator for GeoJSON Polygon / MultiPolygon
  const geojsonToPath = (geometry: any): string => {
    if (!geometry) return '';
    const renderRings = (rings: number[][][]) => {
      return rings
        .map((ring) => {
          return ring
            .map((coord, i) => {
              const [px, py] = project(coord[0], coord[1]);
              return `${i === 0 ? 'M' : 'L'} ${px.toFixed(1)} ${py.toFixed(1)}`;
            })
            .join(' ') + ' Z';
        })
        .join(' ');
    };

    if (geometry.type === 'Polygon') {
      return renderRings(geometry.coordinates);
    } else if (geometry.type === 'MultiPolygon') {
      return geometry.coordinates.map((poly: number[][][]) => renderRings(poly)).join(' ');
    }
    return '';
  };

  // Drawing preview path
  const drawingPath = useMemo(() => {
    if (drawnPoints.length === 0) return '';
    return (
      drawnPoints
        .map((pt, i) => {
          const [px, py] = project(pt[0], pt[1]);
          return `${i === 0 ? 'M' : 'L'} ${px.toFixed(1)} ${py.toFixed(1)}`;
        })
        .join(' ') + (drawnPoints.length >= 3 ? ' Z' : '')
    );
  }, [drawnPoints, project]);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full bg-slate-950 overflow-hidden select-none ${
        isDrawing ? 'cursor-crosshair' : isPanning ? 'cursor-grabbing' : 'cursor-grab'
      }`}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onClick={handleClick}
    >
      {/* SVG GIS Layer Render */}
      <svg className="w-full h-full absolute inset-0 pointer-events-none">
        <defs>
          <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.5" strokeOpacity="0.4" />
          </pattern>
        </defs>

        {/* 1. Base Grid Layer */}
        {visibleLayers.grid && <rect width="100%" height="100%" fill="url(#gridPattern)" />}

        {/* 2. Administrative Boundaries */}
        {visibleLayers.boundaries &&
          boundaries?.features?.map((feat) => {
            const pathData = geojsonToPath(feat.geometry);
            return (
              <g key={`boundary-${feat.properties.id || feat.id}`}>
                <path
                  d={pathData}
                  fill="rgba(99, 102, 241, 0.05)"
                  stroke="#818cf8"
                  strokeWidth="2.5"
                  strokeDasharray="6 4"
                  className="transition-all"
                />
              </g>
            );
          })}

        {/* 3. Cadastral Parcels */}
        {visibleLayers.parcels &&
          parcels?.features?.map((feat) => {
            const pId = feat.properties.id || feat.id;
            const isSelected = selectedFeature?.type === 'PARCEL' && selectedFeature?.id === pId;
            const pathData = geojsonToPath(feat.geometry);

            let fillColor = 'rgba(16, 185, 129, 0.22)';
            let strokeColor = '#10b981';
            if (feat.properties.land_use === 'COMMERCIAL') {
              fillColor = 'rgba(245, 158, 11, 0.22)';
              strokeColor = '#f59e0b';
            } else if (feat.properties.land_use === 'PUBLIC') {
              fillColor = 'rgba(59, 130, 246, 0.22)';
              strokeColor = '#3b82f6';
            } else if (feat.properties.status === 'DRAFT') {
              fillColor = 'rgba(148, 163, 184, 0.15)';
              strokeColor = '#94a3b8';
            }

            return (
              <g
                key={`parcel-${pId}`}
                className="pointer-events-auto cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectFeature('PARCEL', pId, feat.properties);
                }}
              >
                <path
                  d={pathData}
                  fill={isSelected ? 'rgba(52, 211, 153, 0.45)' : fillColor}
                  stroke={isSelected ? '#34d399' : strokeColor}
                  strokeWidth={isSelected ? '3' : '1.5'}
                  className="transition-all hover:brightness-125"
                />
              </g>
            );
          })}

        {/* 4. Building Footprints */}
        {visibleLayers.buildings &&
          buildings?.features?.map((feat) => {
            const bId = feat.properties.id || feat.id;
            const isSelected = selectedFeature?.type === 'BUILDING' && selectedFeature?.id === bId;
            const pathData = geojsonToPath(feat.geometry);

            return (
              <g
                key={`bld-${bId}`}
                className="pointer-events-auto cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectFeature('BUILDING', bId, feat.properties);
                }}
              >
                <path
                  d={pathData}
                  fill={isSelected ? 'rgba(14, 165, 233, 0.65)' : 'rgba(2, 132, 199, 0.4)'}
                  stroke={isSelected ? '#38bdf8' : '#0284c7'}
                  strokeWidth={isSelected ? '2.5' : '1.2'}
                  className="transition-all hover:brightness-125"
                />
              </g>
            );
          })}

        {/* 5. In-Progress Drawn Polygon */}
        {isDrawing && drawnPoints.length > 0 && (
          <g>
            <path
              d={drawingPath}
              fill="rgba(249, 115, 22, 0.25)"
              stroke="#f97316"
              strokeWidth="2"
              strokeDasharray="4 2"
            />
            {drawnPoints.map(([ptLon, ptLat], idx) => {
              const [px, py] = project(ptLon, ptLat);
              return (
                <circle
                  key={`pt-${idx}`}
                  cx={px}
                  cy={py}
                  r={5}
                  fill="#ea580c"
                  stroke="#ffffff"
                  strokeWidth="2"
                />
              );
            })}
          </g>
        )}
      </svg>

      {/* Floating HUD Controls */}
      <div className="absolute top-4 right-4 flex flex-col space-y-2 z-10 pointer-events-auto">
        <button
          onClick={() => setZoom((z) => Math.min(z * 1.3, 150000))}
          title="Zoom In"
          className="w-9 h-9 rounded-lg bg-slate-900/90 border border-slate-700/80 text-slate-200 hover:text-emerald-400 hover:border-emerald-500/50 flex items-center justify-center shadow-lg transition-all"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(z * 0.77, 4000))}
          title="Zoom Out"
          className="w-9 h-9 rounded-lg bg-slate-900/90 border border-slate-700/80 text-slate-200 hover:text-emerald-400 hover:border-emerald-500/50 flex items-center justify-center shadow-lg transition-all"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            setCenter([78.4880, 17.3855]);
            setZoom(18000);
          }}
          title="Reset View"
          className="w-9 h-9 rounded-lg bg-slate-900/90 border border-slate-700/80 text-slate-200 hover:text-emerald-400 hover:border-emerald-500/50 flex items-center justify-center shadow-lg transition-all"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Coordinate & Scale HUD footer */}
      <div className="absolute bottom-3 left-4 flex items-center space-x-4 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] font-mono text-slate-400 z-10 backdrop-blur">
        <div className="flex items-center space-x-1.5">
          <Crosshair className="w-3.5 h-3.5 text-emerald-400" />
          <span>
            {mouseCoord ? `${mouseCoord[0].toFixed(5)}° E, ${mouseCoord[1].toFixed(5)}° N` : 'Hover to inspect'}
          </span>
        </div>
        <span className="text-slate-600">|</span>
        <span>EPSG:4326</span>
        <span className="text-slate-600">|</span>
        <span>Scale 1:{(1000000 / (zoom / 18)).toFixed(0)}</span>
      </div>
    </div>
  );
};
