import React, { useState } from 'react';
import { Layers, Eye, EyeOff, ZoomIn, ZoomOut } from 'lucide-react';

interface AIResultMapProps {
  officialWkt?: string;
  candidateWkt?: string;
  surveyPoints?: Array<{ latitude: number; longitude: number; label?: string }>;
  evidenceLocations?: Array<{ latitude: number; longitude: number; filename?: string }>;
  width?: number;
  height?: number;
}

export const AIResultMap: React.FC<AIResultMapProps> = ({
  officialWkt,
  candidateWkt,
  surveyPoints = [],
  evidenceLocations = [],
  width = 600,
  height = 400,
}) => {
  const [showOfficial, setShowOfficial] = useState(true);
  const [showCandidate, setShowCandidate] = useState(true);
  const [showSurvey, setShowSurvey] = useState(true);
  const [showEvidence, setShowEvidence] = useState(true);
  const [zoom, setZoom] = useState(1);

  // Helper to parse WKT POLYGON coordinates into [[lon, lat], ...]
  const parseWktPolygon = (wktStr?: string): [number, number][] => {
    if (!wktStr) return [];
    try {
      const match = wktStr.match(/\(\((.*?)\)\)/);
      if (!match || !match[1]) return [];
      return match[1]
        .split(',')
        .map((coord) => {
          const parts = coord.trim().split(/\s+/).map(Number);
          return [parts[0], parts[1]] as [number, number];
        })
        .filter((pt) => !isNaN(pt[0]) && !isNaN(pt[1]));
    } catch {
      return [];
    }
  };

  const offCoords = parseWktPolygon(officialWkt);
  const candCoords = parseWktPolygon(candidateWkt);

  // Calculate bounding box across all active geometries
  const allPoints: [number, number][] = [
    ...(showOfficial ? offCoords : []),
    ...(showCandidate ? candCoords : []),
    ...(showSurvey ? surveyPoints.map((p) => [p.longitude, p.latitude] as [number, number]) : []),
    ...(showEvidence ? evidenceLocations.map((p) => [p.longitude, p.latitude] as [number, number]) : []),
  ];

  let minX = 78.38;
  let maxX = 78.39;
  let minY = 17.44;
  let maxY = 17.45;

  if (allPoints.length > 0) {
    minX = Math.min(...allPoints.map((p) => p[0]));
    maxX = Math.max(...allPoints.map((p) => p[0]));
    minY = Math.min(...allPoints.map((p) => p[1]));
    maxY = Math.max(...allPoints.map((p) => p[1]));
  }

  // Add 15% padding
  const paddingX = (maxX - minX) * 0.15 || 0.001;
  const paddingY = (maxY - minY) * 0.15 || 0.001;
  minX -= paddingX;
  maxX += paddingX;
  minY -= paddingY;
  maxY += paddingY;

  const toSvgX = (lon: number) => {
    const norm = (lon - minX) / (maxX - minX || 1);
    const cx = width / 2;
    return cx + (norm * (width - 40) + 20 - cx) * zoom;
  };

  const toSvgY = (lat: number) => {
    const norm = (lat - minY) / (maxY - minY || 1);
    const cy = height / 2;
    // Invert Y for SVG coordinates
    return cy + ((1 - norm) * (height - 40) + 20 - cy) * zoom;
  };

  const coordsToPath = (coords: [number, number][]) => {
    if (coords.length === 0) return '';
    return (
      coords.reduce((acc, pt, idx) => {
        const x = toSvgX(pt[0]);
        const y = toSvgY(pt[1]);
        return idx === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
      }, '') + ' Z'
    );
  };

  return (
    <div className="relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-inner">
      {/* Layer Controls Toolbar */}
      <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-1.5 bg-slate-950/85 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-700/60 shadow-lg text-xs">
        <div className="flex items-center text-slate-400 mr-1 font-semibold">
          <Layers className="w-3.5 h-3.5 mr-1 text-slate-300" />
          Layers:
        </div>

        <button
          type="button"
          onClick={() => setShowOfficial(!showOfficial)}
          className={`flex items-center gap-1 px-2 py-1 rounded font-medium transition-all ${
            showOfficial
              ? 'bg-blue-600/30 text-blue-300 border border-blue-500/50'
              : 'text-slate-500 hover:text-slate-300 bg-slate-800/40'
          }`}
        >
          <span className="w-2.5 h-2.5 rounded-sm bg-blue-500 inline-block" />
          Official Cadastre
        </button>

        <button
          type="button"
          onClick={() => setShowCandidate(!showCandidate)}
          className={`flex items-center gap-1 px-2 py-1 rounded font-medium transition-all ${
            showCandidate
              ? 'bg-purple-600/30 text-purple-300 border border-purple-500/50'
              : 'text-slate-500 hover:text-slate-300 bg-slate-800/40'
          }`}
        >
          <span className="w-2.5 h-2.5 rounded-sm bg-purple-500 inline-block" />
          AI Candidate
        </button>

        <button
          type="button"
          onClick={() => setShowSurvey(!showSurvey)}
          className={`flex items-center gap-1 px-2 py-1 rounded font-medium transition-all ${
            showSurvey
              ? 'bg-amber-600/30 text-amber-300 border border-amber-500/50'
              : 'text-slate-500 hover:text-slate-300 bg-slate-800/40'
          }`}
        >
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block" />
          Survey Observations
        </button>

        <button
          type="button"
          onClick={() => setShowEvidence(!showEvidence)}
          className={`flex items-center gap-1 px-2 py-1 rounded font-medium transition-all ${
            showEvidence
              ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/50'
              : 'text-slate-500 hover:text-slate-300 bg-slate-800/40'
          }`}
        >
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block" />
          Photo Evidence
        </button>
      </div>

      {/* Zoom Toolbar */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-1 bg-slate-950/80 backdrop-blur-md p-1 rounded-lg border border-slate-700/60 shadow">
        <button
          type="button"
          onClick={() => setZoom((z) => Math.min(z + 0.25, 3))}
          className="p-1 hover:bg-slate-800 rounded text-slate-300 hover:text-white"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={() => setZoom((z) => Math.max(z - 0.25, 0.5))}
          className="p-1 hover:bg-slate-800 rounded text-slate-300 hover:text-white"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
      </div>

      {/* Canvas / SVG Map View */}
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-full block cursor-crosshair"
      >
        {/* Grid Background */}
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(51, 65, 85, 0.25)" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />

        {/* Official Geometry (Blue Boundary) */}
        {showOfficial && offCoords.length > 0 && (
          <path
            d={coordsToPath(offCoords)}
            fill="rgba(59, 130, 246, 0.15)"
            stroke="#3b82f6"
            strokeWidth="2.5"
            strokeDasharray="none"
            className="transition-all"
          />
        )}

        {/* AI Candidate Geometry (Purple Boundary) */}
        {showCandidate && candCoords.length > 0 && (
          <path
            d={coordsToPath(candCoords)}
            fill="rgba(168, 85, 247, 0.25)"
            stroke="#a855f7"
            strokeWidth="2.5"
            strokeDasharray="4 2"
            className="transition-all"
          />
        )}

        {/* Survey Observations Markers (Amber Dots) */}
        {showSurvey &&
          surveyPoints.map((pt, i) => (
            <g key={`survey-${i}`} transform={`translate(${toSvgX(pt.longitude)}, ${toSvgY(pt.latitude)})`}>
              <circle r="5" fill="#f59e0b" stroke="#ffffff" strokeWidth="1.5" />
              {pt.label && (
                <text x="7" y="3" fontSize="10" fill="#fde68a" fontFamily="sans-serif">
                  {pt.label}
                </text>
              )}
            </g>
          ))}

        {/* Photo Evidence Markers (Emerald Dots) */}
        {showEvidence &&
          evidenceLocations.map((ev, i) => (
            <g key={`ev-${i}`} transform={`translate(${toSvgX(ev.longitude)}, ${toSvgY(ev.latitude)})`}>
              <circle r="4.5" fill="#10b981" stroke="#ffffff" strokeWidth="1.5" />
            </g>
          ))}
      </svg>

      {/* Coordinate & Scale Footer */}
      <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between text-[11px] text-slate-400 bg-slate-950/80 backdrop-blur-sm px-2.5 py-1 rounded border border-slate-800">
        <div>CRS: EPSG:4326 (WGS 84)</div>
        <div className="flex items-center gap-4">
          <span>Zoom: {Math.round(zoom * 100)}%</span>
          <span>Cadastral Coordinate Space</span>
        </div>
      </div>
    </div>
  );
};
