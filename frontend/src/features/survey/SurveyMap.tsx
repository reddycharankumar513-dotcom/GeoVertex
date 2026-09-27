import React, { useEffect, useRef, useState } from 'react';
import { Crosshair, MapPin, Navigation, ZoomIn, ZoomOut, AlertCircle } from 'lucide-react';
import { SurveyEvidence, SurveyObservation } from '../../types';

interface SurveyMapProps {
  parcelWkt?: string | null;
  buildingWkt?: string | null;
  currentLat?: number | null;
  currentLon?: number | null;
  accuracy?: number | null;
  observations?: SurveyObservation[];
  evidence?: SurveyEvidence[];
  onCaptureCoordinate?: (lat: number, lon: number, accuracy: number | null) => void;
}

export const SurveyMap: React.FC<SurveyMapProps> = ({
  parcelWkt,
  buildingWkt,
  currentLat,
  currentLon,
  accuracy,
  observations = [],
  evidence = [],
  onCaptureCoordinate,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Parse WKT polygons into coordinate pairs [[lon, lat], ...]
  const parsePolygonWkt = (wkt?: string | null): [number, number][] => {
    if (!wkt) return [];
    try {
      const match = wkt.match(/\(\((.*?)\)\)/);
      if (!match) return [];
      const parts = match[1].split(',');
      return parts.map((p) => {
        const [x, y] = p.trim().split(/\s+/).map(Number);
        return [x, y];
      });
    } catch {
      return [];
    }
  };

  const parcelCoords = parsePolygonWkt(parcelWkt);
  const buildingCoords = parsePolygonWkt(buildingWkt);

  // Compute bounding box
  const allCoords: [number, number][] = [...parcelCoords, ...buildingCoords];
  if (currentLon && currentLat) allCoords.push([currentLon, currentLat]);
  for (const o of observations) {
    if (o.longitude && o.latitude) allCoords.push([o.longitude, o.latitude]);
  }
  for (const e of evidence) {
    if (e.longitude && e.latitude) allCoords.push([e.longitude, e.latitude]);
  }

  const minX = allCoords.length > 0 ? Math.min(...allCoords.map((c) => c[0])) : 78.48;
  const maxX = allCoords.length > 0 ? Math.max(...allCoords.map((c) => c[0])) : 78.49;
  const minY = allCoords.length > 0 ? Math.min(...allCoords.map((c) => c[1])) : 17.38;
  const maxY = allCoords.length > 0 ? Math.max(...allCoords.map((c) => c[1])) : 17.39;

  const spanX = Math.max(maxX - minX, 0.002);
  const spanY = Math.max(maxY - minY, 0.002);

  // Canvas drawing routine
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;

    ctx.clearRect(0, 0, width, height);

    // Coordinate conversion
    const project = (lon: number, lat: number): [number, number] => {
      const normX = (lon - minX) / spanX;
      const normY = (lat - minY) / spanY;
      const px = padding + normX * (width - 2 * padding);
      const py = height - padding - normY * (height - 2 * padding);
      return [(px + pan.x) * zoom, (py + pan.y) * zoom];
    };

    // Draw Grid
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Draw Parcel Boundary (Emerald)
    if (parcelCoords.length > 2) {
      ctx.beginPath();
      const [startX, startY] = project(parcelCoords[0][0], parcelCoords[0][1]);
      ctx.moveTo(startX, startY);
      for (let i = 1; i < parcelCoords.length; i++) {
        const [px, py] = project(parcelCoords[i][0], parcelCoords[i][1]);
        ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fillStyle = 'rgba(16, 185, 129, 0.12)';
      ctx.fill();
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Draw Building Footprint (Amber)
    if (buildingCoords.length > 2) {
      ctx.beginPath();
      const [bStartX, bStartY] = project(buildingCoords[0][0], buildingCoords[0][1]);
      ctx.moveTo(bStartX, bStartY);
      for (let i = 1; i < buildingCoords.length; i++) {
        const [bx, by] = project(buildingCoords[i][0], buildingCoords[i][1]);
        ctx.lineTo(bx, by);
      }
      ctx.closePath();
      ctx.fillStyle = 'rgba(245, 158, 11, 0.2)';
      ctx.fill();
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Draw Observation Points (Blue Pins)
    for (const obs of observations) {
      if (obs.longitude && obs.latitude) {
        const [ox, oy] = project(obs.longitude, obs.latitude);
        ctx.fillStyle = '#3b82f6';
        ctx.beginPath();
        ctx.arc(ox, oy, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.fillStyle = '#93c5fd';
        ctx.font = '10px monospace';
        ctx.fillText(obs.observation_type.slice(0, 8), ox + 7, oy + 3);
      }
    }

    // Draw Photo Evidence Points (Purple Markers)
    for (const ev of evidence) {
      if (ev.longitude && ev.latitude) {
        const [ex, ey] = project(ev.longitude, ev.latitude);
        ctx.fillStyle = '#a855f7';
        ctx.beginPath();
        ctx.arc(ex, ey, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.fillStyle = '#d8b4fe';
        ctx.font = '10px monospace';
        ctx.fillText('📷 Photo', ex + 7, ey + 3);
      }
    }

    // Draw Current Surveyor Location (Cyan Target with Accuracy Halo)
    if (currentLon && currentLat) {
      const [cx, cy] = project(currentLon, currentLat);

      // Accuracy halo
      if (accuracy) {
        const pixelRadius = Math.max(accuracy * 1.5 * zoom, 12);
        ctx.beginPath();
        ctx.arc(cx, cy, pixelRadius, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(6, 182, 212, 0.15)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(6, 182, 212, 0.4)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Center dot
      ctx.beginPath();
      ctx.arc(cx, cy, 6, 0, Math.PI * 2);
      ctx.fillStyle = '#06b6d4';
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }, [minX, minY, spanX, spanY, parcelCoords, buildingCoords, currentLon, currentLat, accuracy, observations, evidence, zoom, pan]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const getAccuracyBadge = () => {
    if (accuracy === undefined || accuracy === null) {
      return <span className="text-slate-400 font-mono text-xs">Accuracy: Unknown</span>;
    }
    if (accuracy <= 5) {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-800">
          <span>Optimal ±{accuracy.toFixed(1)}m</span>
        </span>
      );
    }
    if (accuracy <= 15) {
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono bg-amber-950/80 text-amber-300 border border-amber-800">
          <span>Acceptable ±{accuracy.toFixed(1)}m</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono bg-rose-950/80 text-rose-300 border border-rose-800">
        <AlertCircle className="w-3 h-3 text-rose-400 shrink-0" />
        <span>Low Accuracy ±{accuracy.toFixed(1)}m</span>
      </span>
    );
  };

  return (
    <div className="relative w-full h-80 rounded-xl overflow-hidden border border-slate-800 bg-slate-950 shadow-inner flex flex-col justify-between">
      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={700}
        height={320}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        className="w-full h-full cursor-grab active:cursor-grabbing block"
      />

      {/* Top HUD Controls */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none">
        <div className="bg-slate-900/90 backdrop-blur border border-slate-800 rounded-lg px-3 py-1.5 flex items-center space-x-3 pointer-events-auto shadow-md">
          <Crosshair className="w-4 h-4 text-cyan-400 shrink-0 animate-pulse" />
          <div className="text-xs font-mono">
            {currentLat && currentLon ? (
              <span className="text-slate-200">
                {currentLat.toFixed(5)}°N, {currentLon.toFixed(5)}°E
              </span>
            ) : (
              <span className="text-slate-400">Position Not Acquired</span>
            )}
          </div>
          <span className="text-slate-700">|</span>
          {getAccuracyBadge()}
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center space-x-1 bg-slate-900/90 backdrop-blur border border-slate-800 rounded-lg p-1 pointer-events-auto shadow-md">
          <button
            onClick={() => setZoom((z) => Math.min(z + 0.3, 4))}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z - 0.3, 0.6))}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setZoom(1);
              setPan({ x: 0, y: 0 });
            }}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white"
            title="Reset View"
          >
            <Navigation className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Bottom Map Legend */}
      <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between pointer-events-none">
        <div className="bg-slate-900/90 backdrop-blur border border-slate-800 rounded-lg px-3 py-1 flex items-center space-x-4 text-[11px] font-mono pointer-events-auto">
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500/40 border border-emerald-400"></span>
            <span className="text-slate-300">Parcel</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-amber-500/40 border border-amber-400"></span>
            <span className="text-slate-300">Building</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            <span className="text-slate-300">Surveyor GPS</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
            <span className="text-slate-300">Observations ({observations.length})</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-purple-500"></span>
            <span className="text-slate-300">Photos ({evidence.length})</span>
          </div>
        </div>
      </div>
    </div>
  );
};
