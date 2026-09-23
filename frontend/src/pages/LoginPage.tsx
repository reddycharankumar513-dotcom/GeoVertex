import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Key, Mail, AlertCircle, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { ApiClientError } from '../api/client';

export const LoginPage: React.FC = () => {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier || !password) {
      setError('Please provide both username/email and password.');
      return;
    }

    setError(null);
    setLoading(true);
    try {
      await login(identifier, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        setError(`[${err.code}] ${err.message}`);
      } else {
        setError(err.message || 'Authentication failed. Please verify credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (email: string, pass: string) => {
    setIdentifier(email);
    setPassword(pass);
    setError(null);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4 py-12 relative overflow-hidden">
      {/* Background Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b15_1px,transparent_1px),linear-gradient(to_bottom,#1e293b15_1px,transparent_1px)] bg-[size:32px_32px]"></div>

      <div className="max-w-md w-full space-y-8 relative z-10">
        {/* Header */}
        <div className="text-center">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-4 shadow-xl shadow-emerald-500/10">
            <Shield className="w-7 h-7" />
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight text-white">
            GeoVertex Cadastre
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            3D Cadastral Intelligence & Vertical Property Mapping
          </p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-8 backdrop-blur-xl shadow-2xl space-y-6">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-start space-x-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
              <div className="leading-relaxed">{error}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Username or Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                <input
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="admin@geovertex.local"
                  required
                  className="w-full bg-slate-950/70 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <Key className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  className="w-full bg-slate-950/70 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 transition-colors"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold py-2.5 px-4 rounded-xl flex items-center justify-center space-x-2 shadow-lg shadow-emerald-500/20 transition-all cursor-pointer"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <span>Sign In to Cadastre</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick-Fill Demo Credentials */}
          <div className="pt-4 border-t border-slate-800/80">
            <span className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-2.5">
              Phase 1 Development Demo Accounts:
            </span>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => handleQuickFill('admin@geovertex.local', 'GeoVertexAdmin2026!')}
                className="p-2 rounded-lg bg-slate-950 border border-purple-800/60 hover:border-purple-600 text-purple-300 text-left transition-colors"
              >
                <div className="font-semibold">Admin</div>
                <div className="text-[10px] text-slate-400 truncate">admin@geovertex.local</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill('officer@geovertex.local', 'GeoVertexOfficer2026!')}
                className="p-2 rounded-lg bg-slate-950 border border-amber-800/60 hover:border-amber-600 text-amber-300 text-left transition-colors"
              >
                <div className="font-semibold">Gov Officer</div>
                <div className="text-[10px] text-slate-400 truncate">officer@geovertex.local</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill('surveyor@geovertex.local', 'GeoVertexSurveyor2026!')}
                className="p-2 rounded-lg bg-slate-950 border border-blue-800/60 hover:border-blue-600 text-blue-300 text-left transition-colors"
              >
                <div className="font-semibold">Surveyor</div>
                <div className="text-[10px] text-slate-400 truncate">surveyor@geovertex.local</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill('citizen@geovertex.local', 'GeoVertexCitizen2026!')}
                className="p-2 rounded-lg bg-slate-950 border border-emerald-800/60 hover:border-emerald-600 text-emerald-300 text-left transition-colors"
              >
                <div className="font-semibold">Citizen</div>
                <div className="text-[10px] text-slate-400 truncate">citizen@geovertex.local</div>
              </button>
            </div>
          </div>
        </div>

        {/* Security Notice */}
        <p className="text-center text-xs text-slate-400">
          Enforcing Server-Side RBAC, JWT Token Rotation & Immutable Audit Logging
        </p>
      </div>
    </div>
  );
};
