import React from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  Compass,
  FileCheck,
  History,
  Layers,
  LogOut,
  Map,
  MapPin,
  Shield,
  User as UserIcon,
  Users,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { UserRole } from '../types';

export const DashboardLayout: React.FC = () => {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isMapPage = location.pathname.startsWith('/cadastre');

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const getRoleBadge = (userRole?: UserRole) => {
    switch (userRole) {
      case 'ADMIN':
        return 'bg-purple-950/80 text-purple-300 border-purple-800';
      case 'GOVERNMENT_OFFICER':
        return 'bg-amber-950/80 text-amber-300 border-amber-800';
      case 'SURVEYOR':
        return 'bg-blue-950/80 text-blue-300 border-blue-800';
      case 'URBAN_PLANNER':
        return 'bg-cyan-950/80 text-cyan-300 border-cyan-800';
      case 'CITIZEN':
      default:
        return 'bg-emerald-950/80 text-emerald-300 border-emerald-800';
    }
  };

  return (
    <div className="min-h-screen flex bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800/80 bg-slate-900/60 flex flex-col justify-between shrink-0">
        <div>
          {/* Brand */}
          <div className="h-16 px-6 flex items-center space-x-3 border-b border-slate-800/80">
            <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center text-slate-950 font-black text-xl shadow-lg shadow-emerald-500/20">
              G
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-emerald-400 to-teal-200 bg-clip-text text-transparent">
                GeoVertex
              </span>
              <span className="block text-[10px] uppercase font-mono tracking-wider text-slate-400">
                Phase 2 Cadastre GIS
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5">
            <NavLink
              to="/cadastre"
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`
              }
            >
              <Map className="w-4 h-4 shrink-0" />
              <span>2D Cadastral Map</span>
            </NavLink>

            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`
              }
            >
              <Activity className="w-4 h-4 shrink-0" />
              <span>Foundation Dashboard</span>
            </NavLink>

            <NavLink
              to="/profile"
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`
              }
            >
              <UserIcon className="w-4 h-4 shrink-0" />
              <span>User Profile</span>
            </NavLink>

            {/* Admin & Officer Navigation */}
            {(role === 'ADMIN' || role === 'GOVERNMENT_OFFICER') && (
              <div className="pt-4 pb-1">
                <span className="px-3.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Administration
                </span>
              </div>
            )}

            {(role === 'ADMIN' || role === 'GOVERNMENT_OFFICER') && (
              <NavLink
                to="/admin/users"
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <Users className="w-4 h-4 shrink-0" />
                <span>User Directory</span>
              </NavLink>
            )}

            {role === 'ADMIN' && (
              <NavLink
                to="/admin/audit"
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <History className="w-4 h-4 shrink-0" />
                <span>Security Audit Logs</span>
              </NavLink>
            )}
          </nav>
        </div>

        {/* User Card & Logout in Sidebar Footer */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 min-w-0">
              <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-semibold text-sm">
                {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-slate-200 truncate">{user?.full_name}</p>
                <span
                  className={`inline-block px-1.5 py-0.5 mt-0.5 rounded text-[10px] font-mono border ${getRoleBadge(
                    role || undefined
                  )}`}
                >
                  {role}
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign Out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col min-w-0 ${isMapPage ? 'overflow-hidden h-screen' : 'overflow-y-auto'}`}>
        {/* Top Header */}
        <header className="h-14 px-6 border-b border-slate-800/80 bg-slate-900/30 backdrop-blur flex items-center justify-between shrink-0 z-10">
          <div className="flex items-center space-x-3">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-xs font-mono text-slate-400">PostGIS Core Engine Active</span>
            <span className="text-xs text-slate-600">|</span>
            <span className="text-xs text-slate-400">
              {isMapPage ? (
                <span>CRS: <span className="text-emerald-400 font-mono">EPSG:4326 (WGS84)</span></span>
              ) : (
                <span>API Gateway: <span className="text-emerald-400 font-mono">200 OK</span></span>
              )}
            </span>
          </div>

          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-xs text-slate-400 font-mono">{user?.email}</p>
              <p className="text-[10px] text-slate-500 font-mono">{user?.role}</p>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className={isMapPage ? 'flex-1 flex flex-col min-h-0 overflow-hidden relative' : 'p-8 flex-1'}>
          <Outlet />
        </main>
      </div>
    </div>
  );
};
