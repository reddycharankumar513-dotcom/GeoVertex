import React, { useMemo, useState } from 'react';
import { ValidationIssue } from '../../types/validation';

interface ValidationMapViewerProps {
  issue?: ValidationIssue | null;
  entityWkt?: string | null;
  relatedEntityWkt?: string | null;
  height?: string;
}

interface Point {
  x: number;
  y: number;
}

export const ValidationMapViewer: React.FC<ValidationMapViewerProps> = ({
  issue,
  entityWkt,
  relatedEntityWkt,
  height = '360px',
}) => {
  const [showIssueLayer, setShowIssueLayer] = useState(true);
  const [showEntityLayer, setShowEntityLayer] = useState(true);
  const [showRelatedLayer, setShowRelatedLayer] = useState(true);

  // Parse WKT polygons into coordinate arrays
  const parseWktPolygon = (wkt?: string | null): Point[][] => {
    if (!wkt) return [];
    try {
      const clean = wkt.trim().toUpperCase();
      if (!clean.includes('POLYGON')) return [];

      // Extract rings inside parentheses
      const ringsMatch = clean.match(/\(\s*\((.+?)\)\s*\)/);
      if (!ringsMatch && !clean.includes('((')) return [];

      const rawContent = clean.replace(/^[A-Z\s]+\(\(/, '').replace(/\)\)$/, '');
      const ringStrings = rawContent.split(/\)\s*,\s*\(/);

      return ringStrings.map((r) => {
        const coordPairs = r.split(',');
        return coordPairs
          .map((pair) => {
            const parts = pair.trim().split(/\s+/);
            if (parts.length >= 2) {
              const x = parseFloat(parts[0]);
              const y = parseFloat(parts[1]);
              if (!isNaN(x) && !isNaN(y)) {
                return { x, y };
              }
            }
            return null;
          })
          .filter((p): p is Point => p !== null);
      });
    } catch {
      return [];
    }
  };

  const issueRings = useMemo(() => parseWktPolygon(issue?.geometry_wkt), [issue?.geometry_wkt]);
  const entityRings = useMemo(() => parseWktPolygon(entityWkt), [entityWkt]);
  const relatedRings = useMemo(() => parseWktPolygon(relatedEntityWkt), [relatedEntityWkt]);

  // Compute unified bounding box
  const bbox = useMemo(() => {
    const allPoints: Point[] = [
      ...issueRings.flat(),
      ...entityRings.flat(),
      ...relatedRings.flat(),
    ];

    if (allPoints.length === 0) {
      return { minX: 0, maxX: 10, minY: 0, maxY: 10 };
    }

    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    for (const p of allPoints) {
      if (p.x < minX) minX = p.x;
      if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.y > maxY) maxY = p.y;
    }

    const padX = Math.max((maxX - minX) * 0.15, 0.0001);
    const padY = Math.max((maxY - minY) * 0.15, 0.0001);

    return {
      minX: minX - padX,
      maxX: maxX + padX,
      minY: minY - padY,
      maxY: maxY + padY,
    };
  }, [issueRings, entityRings, relatedRings]);

  // Coordinate projection to SVG canvas (width: 600, height: 400)
  const svgWidth = 600;
  const svgHeight = 400;

  const projectPoint = (p: Point): Point => {
    const spanX = bbox.maxX - bbox.minX || 1;
    const spanY = bbox.maxY - bbox.minY || 1;

    const x = ((p.x - bbox.minX) / spanX) * (svgWidth - 40) + 20;
    // Invert Y for cartographic latitude
    const y = svgHeight - 20 - ((p.y - bbox.minY) / spanY) * (svgHeight - 40);
    return { x, y };
  };

  const toSvgPath = (rings: Point[][]): string => {
    return rings
      .map((ring) => {
        if (ring.length === 0) return '';
        const pts = ring.map(projectPoint);
        return `M ${pts[0].x} ${pts[0].y} ` + pts.slice(1).map((pt) => `L ${pt.x} ${pt.y}`).join(' ') + ' Z';
      })
      .join(' ');
  };

  const issuePath = useMemo(() => toSvgPath(issueRings), [issueRings, bbox]);
  const entityPath = useMemo(() => toSvgPath(entityRings), [entityRings, bbox]);
  const relatedPath = useMemo(() => toSvgPath(relatedRings), [relatedRings, bbox]);

  return (
    <div className="relative border border-slate-700 rounded-lg overflow-hidden bg-slate-950 flex flex-col" style={{ height }}>
      {/* Layer Toggles & Toolbar */}
      <div className="absolute top-2 left-2 z-10 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded border border-slate-700 flex items-center space-x-3 text-xs text-slate-300 shadow">
        <label className="flex items-center space-x-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={showIssueLayer}
            onChange={(e) => setShowIssueLayer(e.target.checked)}
            className="rounded border-rose-500 text-rose-500 focus:ring-rose-500 focus:ring-offset-slate-900"
          />
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span>
            <span>Issue Defect Geometry</span>
          </span>
        </label>

        {entityWkt && (
          <label className="flex items-center space-x-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={showEntityLayer}
              onChange={(e) => setShowEntityLayer(e.target.checked)}
              className="rounded border-sky-500 text-sky-500 focus:ring-sky-500 focus:ring-offset-slate-900"
            />
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-500 inline-block"></span>
              <span>Target Entity</span>
            </span>
          </label>
        )}

        {relatedEntityWkt && (
          <label className="flex items-center space-x-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={showRelatedLayer}
              onChange={(e) => setShowRelatedLayer(e.target.checked)}
              className="rounded border-emerald-500 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-slate-900"
            />
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
              <span>Related Entity</span>
            </span>
          </label>
        )}
      </div>

      {/* SVG Vector Canvas */}
      <div className="flex-1 w-full h-full relative">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-full select-none"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Subtle Grid Lines */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.75" />
            </pattern>
            <pattern id="issue-hatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="8" stroke="#f43f5e" strokeWidth="1.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Related Entity (e.g. Parcel boundary or official footprint) */}
          {showRelatedLayer && relatedPath && (
            <path
              d={relatedPath}
              fill="rgba(16, 185, 129, 0.12)"
              stroke="#10b981"
              strokeWidth="2"
              strokeDasharray="4 2"
            />
          )}

          {/* Target Entity Footprint */}
          {showEntityLayer && entityPath && (
            <path
              d={entityPath}
              fill="rgba(14, 165, 233, 0.15)"
              stroke="#0284c7"
              strokeWidth="2"
            />
          )}

          {/* Conflicting / Defect Geometry Slice */}
          {showIssueLayer && issuePath && (
            <path
              d={issuePath}
              fill="url(#issue-hatch)"
              stroke="#f43f5e"
              strokeWidth="2.5"
            />
          )}
        </svg>

        {/* Fallback Notice if No Geometry Available */}
        {!issuePath && !entityPath && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 text-xs">
            <svg className="w-8 h-8 text-slate-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            <span>No explicit polygon coordinates available for spatial preview</span>
          </div>
        )}
      </div>

      {/* Coordinate & Metric Bar */}
      <div className="bg-slate-900 border-t border-slate-800 px-3 py-1.5 text-[11px] text-slate-400 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <span>CRS: <strong className="text-slate-200">WGS 84 (EPSG:4326)</strong></span>
          {issue?.measured_value && (
            <span>Measured: <strong className="text-rose-400">{issue.measured_value}</strong></span>
          )}
          {issue?.tolerance && (
            <span>Tolerance: <strong className="text-amber-400">{issue.tolerance}</strong></span>
          )}
        </div>
        <div className="text-slate-500">
          Bounds: [{bbox.minX.toFixed(4)}, {bbox.minY.toFixed(4)}] to [{bbox.maxX.toFixed(4)}, {bbox.maxY.toFixed(4)}]
        </div>
      </div>
    </div>
  );
};
