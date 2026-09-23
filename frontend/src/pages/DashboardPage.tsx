import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle, Database, Layers, Lock, ShieldCheck, UserCheck, AlertTriangle } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { api } from '../api/client';

export const DashboardPage: React.FC = () => {
  const { user, role } = useAuth();
  const [healthData, setHealthData] = useState<any>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await api.get('/health/ready');
        setHealthData(res);
      } catch (err) {
        console.error('Failed to query health probe:', err);
      } finally {
        setLoadingHealth(false);
      }
    };
    fetchHealth();
  }, []);

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Top Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950/40 via-slate-900/60 to-slate-900/40 border border-emerald-500/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              CURRENT PHASE: 1 ONLY
            </span>
            <span className="text-xs text-slate-400 font-mono">PLATFORM FOUNDATION</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-2">
            Welcome, {user?.full_name}
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            You are authenticated under the <strong className="text-emerald-400 font-mono">{role}</strong> role. GeoVertex provides 3D Cadastral Intelligence, extending 2D parcel polygons into structured vertical property digital twins.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-right shrink-0">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
            Cadastral Authority Node
          </span>
          <span className="text-sm font-semibold text-slate-200">
            {healthData?.database?.postgis_available ? 'PostGIS Active' : 'Relational Engine Active'}
          </span>
        </div>
      </div>

      {/* System Infrastructure Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Database & PostGIS</span>
            <Database className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>
            <span>Connected</span>
          </div>
          <p className="text-xs text-slate-400">
            PostgreSQL engine with PostGIS geometry types (PointZ, PolygonZ, MultiPolygon).
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Security & RBAC</span>
            <ShieldCheck className="w-5 h-5 text-purple-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>
            <span>5 Roles Active</span>
          </div>
          <p className="text-xs text-slate-400">
            Citizen, Surveyor, Officer, Admin & Planner enforced with server-side dependencies.
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Audit & Session</span>
            <Lock className="w-5 h-5 text-blue-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>
            <span>JWT Rotation</span>
          </div>
          <p className="text-xs text-slate-400">
            Append-only audit trail logging user creations, role updates, and logins.
          </p>
        </div>
      </div>

      {/* Phase Roadmap Matrix */}
      <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4">
        <h2 className="text-lg font-bold text-slate-100 flex items-center space-x-2">
          <Layers className="w-5 h-5 text-emerald-400" />
          <span>Cadastral Architecture Phase Matrix</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/40">
            <div className="text-xs font-bold text-emerald-400 uppercase">Phase 1 (Complete)</div>
            <div className="text-sm font-semibold text-slate-100 mt-1">Platform Foundation</div>
            <p className="text-xs text-slate-400 mt-1">PostGIS, JWT, RBAC, User Management, Audit Logs.</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 opacity-70">
            <div className="text-xs font-mono text-slate-400 uppercase">Phase 2 (Planned)</div>
            <div className="text-sm font-semibold text-slate-300 mt-1">2D Parcel GIS</div>
            <p className="text-xs text-slate-400 mt-1">MapLibre parcel boundary viewer, CRS normalization.</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 opacity-70">
            <div className="text-xs font-mono text-slate-400 uppercase">Phase 3 (Planned)</div>
            <div className="text-sm font-semibold text-slate-300 mt-1">3D Digital Twin</div>
            <p className="text-xs text-slate-400 mt-1">CesiumJS 3D extruded parcels, terrain clipping.</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 opacity-70">
            <div className="text-xs font-mono text-slate-400 uppercase">Phase 4-15 (Roadmap)</div>
            <div className="text-sm font-semibold text-slate-300 mt-1">Vertical Hierarchy</div>
            <p className="text-xs text-slate-400 mt-1">Building, Floor, Unit, AI extraction, Reviews.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
