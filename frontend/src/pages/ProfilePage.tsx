import React from 'react';
import { Mail, Phone, Shield, User as UserIcon, Calendar, CheckCircle, Clock } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export const ProfilePage: React.FC = () => {
  const { user, role } = useAuth();

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">User Profile</h1>
        <p className="text-sm text-slate-400 mt-1">
          Identity credentials, assigned cadastral role, and jurisdiction affiliations.
        </p>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur space-y-6">
        {/* Profile Card Top */}
        <div className="flex items-center space-x-4 pb-6 border-b border-slate-800">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-2xl">
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">{user?.full_name}</h2>
            <p className="text-xs text-slate-400 font-mono">@{user?.username}</p>
            <span className="inline-block px-2.5 py-0.5 mt-2 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              Role: {role}
            </span>
          </div>
        </div>

        {/* Detailed Fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-850 space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Mail className="w-3.5 h-3.5" />
              <span>Email Address</span>
            </span>
            <p className="font-medium text-slate-200">{user?.email}</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-850 space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Phone className="w-3.5 h-3.5" />
              <span>Contact Telephone</span>
            </span>
            <p className="font-medium text-slate-200">{user?.phone || 'Not provided'}</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-850 space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Shield className="w-3.5 h-3.5" />
              <span>Account UUID</span>
            </span>
            <p className="font-mono text-xs text-slate-300 break-all">{user?.id}</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-850 space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              <span>Status</span>
            </span>
            <p className="font-medium text-emerald-400">
              {user?.is_active ? 'Active & Permitted' : 'Deactivated'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-850 space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Calendar className="w-3.5 h-3.5" />
              <span>Registered On</span>
            </span>
            <p className="font-mono text-xs text-slate-300">
              {user?.created_at ? new Date(user.created_at).toLocaleString() : 'N/A'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-850 space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Clock className="w-3.5 h-3.5" />
              <span>Last Login</span>
            </span>
            <p className="font-mono text-xs text-slate-300">
              {user?.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'First session'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
