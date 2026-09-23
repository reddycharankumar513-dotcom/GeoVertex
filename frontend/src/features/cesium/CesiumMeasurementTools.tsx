import React, { useState, useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import { Ruler, ArrowUpDown, Trash2 } from 'lucide-react';

interface Props {
  viewer: Cesium.Viewer | null;
}

type ToolMode = 'none' | 'distance' | 'height';

export const CesiumMeasurementTools: React.FC<Props> = ({ viewer }) => {
  const [activeTool, setActiveTool] = useState<ToolMode>('none');
  const [measurementResult, setMeasurementResult] = useState<string | null>(null);

  const activePointsRef = useRef<Cesium.Cartesian3[]>([]);
  const tempEntitiesRef = useRef<Cesium.Entity[]>([]);
  const handlerRef = useRef<Cesium.ScreenSpaceEventHandler | null>(null);

  const clearMeasurements = () => {
    if (viewer && !viewer.isDestroyed()) {
      tempEntitiesRef.current.forEach((entity) => {
        viewer.entities.remove(entity);
      });
    }
    tempEntitiesRef.current = [];
    activePointsRef.current = [];
    setMeasurementResult(null);
  };

  useEffect(() => {
    if (!viewer || viewer.isDestroyed()) return;

    if (handlerRef.current) {
      handlerRef.current.destroy();
      handlerRef.current = null;
    }

    if (activeTool === 'none') {
      return;
    }

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handlerRef.current = handler;

    handler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
      // Pick position on ellipsoid or 3D feature
      let cartesian: Cesium.Cartesian3 | undefined = viewer.scene.pickPosition(click.position);
      if (!cartesian) {
        const ray = viewer.camera.getPickRay(click.position);
        if (ray) {
          const picked = viewer.scene.globe.pick(ray, viewer.scene);
          if (picked) {
            cartesian = picked;
          }
        }
      }

      if (!cartesian) return;

      activePointsRef.current.push(cartesian);

      // Add marker point
      const pointEntity = viewer.entities.add({
        position: cartesian,
        point: {
          pixelSize: 8,
          color: Cesium.Color.YELLOW,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      });
      tempEntitiesRef.current.push(pointEntity);

      if (activeTool === 'distance' && activePointsRef.current.length === 2) {
        const p1 = activePointsRef.current[0];
        const p2 = activePointsRef.current[1];
        const distance = Cesium.Cartesian3.distance(p1, p2);

        // Add line
        const lineEntity = viewer.entities.add({
          polyline: {
            positions: [p1, p2],
            width: 3,
            material: new Cesium.PolylineDashMaterialProperty({
              color: Cesium.Color.YELLOW,
            }),
            depthFailMaterial: Cesium.Color.YELLOW.withAlpha(0.5),
          },
        });
        tempEntitiesRef.current.push(lineEntity);

        // Add label at midpoint
        const midPoint = Cesium.Cartesian3.midpoint(p1, p2, new Cesium.Cartesian3());
        const labelEntity = viewer.entities.add({
          position: midPoint,
          label: {
            text: `${distance.toFixed(2)} m`,
            font: '14px Inter, sans-serif',
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 3,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          },
        });
        tempEntitiesRef.current.push(labelEntity);

        setMeasurementResult(`Distance: ${distance.toFixed(2)} m`);
        activePointsRef.current = [];
      } else if (activeTool === 'height' && activePointsRef.current.length === 2) {
        const p1 = activePointsRef.current[0];
        const p2 = activePointsRef.current[1];

        const c1 = Cesium.Cartographic.fromCartesian(p1);
        const c2 = Cesium.Cartographic.fromCartesian(p2);
        const deltaHeight = Math.abs(c2.height - c1.height);

        // Create vertical line from ground of p2 to height of p2
        const p1Projected = Cesium.Cartesian3.fromRadians(c2.longitude, c2.latitude, c1.height);

        const lineEntity = viewer.entities.add({
          polyline: {
            positions: [p1Projected, p2],
            width: 3,
            material: Cesium.Color.CYAN,
          },
        });
        tempEntitiesRef.current.push(lineEntity);

        const midPoint = Cesium.Cartesian3.midpoint(p1Projected, p2, new Cesium.Cartesian3());
        const labelEntity = viewer.entities.add({
          position: midPoint,
          label: {
            text: `Height: ${deltaHeight.toFixed(2)} m`,
            font: '14px Inter, sans-serif',
            fillColor: Cesium.Color.CYAN,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 3,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          },
        });
        tempEntitiesRef.current.push(labelEntity);

        setMeasurementResult(`Height Delta: ${deltaHeight.toFixed(2)} m`);
        activePointsRef.current = [];
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    return () => {
      if (handlerRef.current) {
        handlerRef.current.destroy();
        handlerRef.current = null;
      }
    };
  }, [viewer, activeTool]);

  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/60 rounded-lg p-2.5 shadow-xl text-xs space-y-2">
      <div className="font-semibold text-slate-300 flex items-center justify-between pb-1 border-b border-slate-700/60">
        <span>3D Tools</span>
        {measurementResult && (
          <span className="text-emerald-400 font-mono text-[11px] font-normal">{measurementResult}</span>
        )}
      </div>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => {
            setActiveTool(activeTool === 'distance' ? 'none' : 'distance');
            activePointsRef.current = [];
          }}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded transition-all ${
            activeTool === 'distance'
              ? 'bg-amber-600 text-white font-medium shadow-sm'
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
          }`}
          title="Measure 3D Distance (Click 2 points)"
        >
          <Ruler className="w-3.5 h-3.5" />
          <span>Distance</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveTool(activeTool === 'height' ? 'none' : 'height');
            activePointsRef.current = [];
          }}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded transition-all ${
            activeTool === 'height'
              ? 'bg-cyan-600 text-white font-medium shadow-sm'
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
          }`}
          title="Measure Vertical Height (Click base & top points)"
        >
          <ArrowUpDown className="w-3.5 h-3.5" />
          <span>Height</span>
        </button>

        <button
          type="button"
          onClick={clearMeasurements}
          className="flex items-center gap-1 px-2 py-1.5 rounded bg-slate-800 text-rose-400 hover:bg-rose-950/40 hover:text-rose-300 ml-auto transition-all"
          title="Clear measurements"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>Clear</span>
        </button>
      </div>

      {activeTool !== 'none' && (
        <div className="text-[11px] text-amber-300/80 bg-amber-950/30 px-2 py-1 rounded border border-amber-800/40">
          Click two points on 3D terrain/buildings to measure.
        </div>
      )}
    </div>
  );
};
