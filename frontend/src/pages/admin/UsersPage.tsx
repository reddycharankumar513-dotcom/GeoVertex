import React, { useEffect, useState } from 'react';
import { Shield, UserX, UserCheck, RefreshCw, AlertCircle, Search, Edit3 } from 'lucide-react';
import { api, ApiClientError } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import { PaginatedResult, User, UserRole } from '../../types';

export const UsersPage: React.FC = () => {
  const { user: currentUser, role: currentRole } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Role edit modal state
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [newRole, setNewRole] = useState<UserRole>('CITIZEN');

  const isAdmin = currentRole === 'ADMIN';

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<PaginatedResult<User>>('/users?size=50');
      setUsers(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load user directory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleToggleStatus = async (user: User) => {
    if (!isAdmin) return;
    setError(null);
    setActionSuccess(null);
    try {
      const updated = await api.patch<User>(`/users/${user.id}/status`, {
        is_active: !user.is_active,
      });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      setActionSuccess(
        `User ${updated.email} successfully ${updated.is_active ? 'activated' : 'deactivated'}.`
      );
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        setError(`[${err.code}] ${err.message}`);
      } else {
        setError(err.message || 'Status update failed.');
      }
    }
  };

  const handleUpdateRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser || !isAdmin) return;

    setError(null);
    setActionSuccess(null);
    try {
      const updated = await api.patch<User>(`/users/${editingUser.id}/role`, {
        role: newRole,
      });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      setActionSuccess(`Role for ${updated.email} updated to ${updated.role}.`);
      setEditingUser(null);
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        setError(`[${err.code}] ${err.message}`);
      } else {
        setError(err.message || 'Role update failed.');
      }
    }
  };

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Cadastral User Directory</h1>
          <p className="text-sm text-slate-400 mt-1">
            Role-Based Access Control and user identity management for GeoVertex nodes.
          </p>
        </div>
        <button
          onClick={fetchUsers}
          disabled={loading}
          className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center space-x-2 text-xs font-semibold transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {actionSuccess && (
        <div className="p-4 rounded-xl bg-emerald-950/50 border border-emerald-800/80 text-emerald-300 text-xs flex items-center space-x-2">
          <Shield className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-950/60 text-slate-400 text-[11px] font-mono uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-6">User / Email</th>
                <th className="py-3.5 px-4">Role</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Registered</th>
                {isAdmin && <th className="py-3.5 px-6 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {loading && users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500 text-xs">
                    Loading users from PostgreSQL database...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500 text-xs">
                    No users found in database.
                  </td>
                </tr>
              ) : (
                users.map((u) => {
                  const isSelf = u.id === currentUser?.id;
                  return (
                    <tr key={u.id} className="hover:bg-slate-850/40 transition-colors">
                      <td className="py-4 px-6">
                        <div className="font-semibold text-slate-100">{u.full_name}</div>
                        <div className="text-xs text-slate-400 font-mono">{u.email}</div>
                      </td>
                      <td className="py-4 px-4">
                        <span className="inline-block px-2 py-0.5 rounded text-[11px] font-mono border bg-slate-950 border-slate-800 text-emerald-300">
                          {u.role}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <span
                          className={`inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium ${
                            u.is_active
                              ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
                              : 'bg-rose-950/60 text-rose-400 border border-rose-800/60'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              u.is_active ? 'bg-emerald-500' : 'bg-rose-500'
                            }`}
                          ></span>
                          <span>{u.is_active ? 'Active' : 'Deactivated'}</span>
                        </span>
                      </td>
                      <td className="py-4 px-4 text-xs text-slate-400 font-mono">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      {isAdmin && (
                        <td className="py-4 px-6 text-right space-x-2">
                          <button
                            onClick={() => {
                              setEditingUser(u);
                              setNewRole(u.role);
                            }}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                            title="Change Role"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>

                          <button
                            onClick={() => handleToggleStatus(u)}
                            disabled={isSelf}
                            className={`p-1.5 rounded-lg transition-colors ${
                              isSelf
                                ? 'opacity-30 cursor-not-allowed bg-slate-800 text-slate-500'
                                : u.is_active
                                ? 'bg-rose-950/40 text-rose-400 hover:bg-rose-900/60 border border-rose-900'
                                : 'bg-emerald-950/40 text-emerald-400 hover:bg-emerald-900/60 border border-emerald-900'
                            }`}
                            title={isSelf ? 'Cannot deactivate self' : u.is_active ? 'Deactivate User' : 'Activate User'}
                          >
                            {u.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Role Change Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Modify User Role</h3>
            <p className="text-xs text-slate-400">
              Assign a new authoritative role to <strong>{editingUser.email}</strong>.
            </p>

            <form onSubmit={handleUpdateRole} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Select Role
                </label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as UserRole)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  <option value="CITIZEN">CITIZEN</option>
                  <option value="SURVEYOR">SURVEYOR</option>
                  <option value="GOVERNMENT_OFFICER">GOVERNMENT_OFFICER</option>
                  <option value="URBAN_PLANNER">URBAN_PLANNER</option>
                  <option value="ADMIN">ADMIN</option>
                </select>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-md shadow-emerald-500/20"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
