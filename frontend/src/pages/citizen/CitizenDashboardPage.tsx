import React, { useEffect, useState } from 'react';
import {
  Building2,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Plus,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Search,
  ArrowRight,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { workflowApi } from '../../api/workflow';
import {
  CitizenDashboardMetrics,
  CitizenProperty,
  ServiceRequest,
} from '../../types/workflow';
import { RequestCreateModal } from '../../features/workflow/RequestCreateModal';

export const CitizenDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<CitizenDashboardMetrics | null>(null);
  const [properties, setProperties] = useState<CitizenProperty[]>([]);
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedPropertyForRequest, setSelectedPropertyForRequest] = useState<string | undefined>();
  const [searchTerm, setSearchTerm] = useState('');

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [m, p, r] = await Promise.all([
        workflowApi.getCitizenDashboard(),
        workflowApi.listCitizenProperties(),
        workflowApi.listServiceRequests({ limit: 10 }),
      ]);
      setMetrics(m);
      setProperties(p);
      setRequests(r.items);
    } catch (err: any) {
      setError(err?.message || 'Failed to load citizen portal data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
      case 'COMPLETED':
        return 'bg-emerald-900/40 text-emerald-400 border-emerald-700/50';
      case 'REJECTED':
      case 'CANCELLED':
        return 'bg-red-900/40 text-red-400 border-red-700/50';
      case 'MORE_INFO_REQUESTED':
        return 'bg-amber-900/40 text-amber-300 border-amber-700/50 animate-pulse';
      case 'SURVEY_COMMISSIONED':
      case 'FIELD_VERIFIED':
        return 'bg-purple-900/40 text-purple-300 border-purple-700/50';
      default:
        return 'bg-blue-900/40 text-blue-300 border-blue-700/50';
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'URGENT':
        return 'text-red-400 font-bold';
      case 'HIGH':
        return 'text-amber-400 font-semibold';
      case 'MEDIUM':
        return 'text-blue-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-800 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-900/60 text-blue-300 border border-blue-700/50">
              Citizen Portal
            </span>
            <span className="text-gray-500 text-xs">• Official Public Cadastre Services</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">My Property Dashboard</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Manage your verified cadastral holdings, submit mutation and survey requests, and track real-time government review.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="p-2.5 rounded-xl border border-gray-800 text-gray-300 hover:text-white hover:bg-gray-800 transition"
            title="Refresh dashboard"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => {
              setSelectedPropertyForRequest(undefined);
              setIsCreateModalOpen(true);
            }}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition shadow-lg shadow-blue-600/30 flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>New Service Request</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-900/30 border border-red-700/50 text-red-200 text-sm flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">My Properties</span>
            <Building2 className="w-5 h-5 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {metrics ? metrics.total_properties : '—'}
          </div>
          <div className="text-xs text-gray-500 mt-1">Verified cadastral records</div>
        </div>

        <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Requests</span>
            <FileText className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {metrics ? metrics.active_requests : '—'}
          </div>
          <div className="text-xs text-gray-500 mt-1">Under government review</div>
        </div>

        <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Pending Action</span>
            <Clock className="w-5 h-5 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">
            {metrics ? metrics.pending_action_requests : '—'}
          </div>
          <div className="text-xs text-gray-500 mt-1">Revisions / responses required</div>
        </div>

        <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Completed</span>
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {metrics ? metrics.completed_requests : '—'}
          </div>
          <div className="text-xs text-gray-500 mt-1">Successfully resolved cases</div>
        </div>
      </div>

      {/* Verified Properties Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Verified Properties</h2>
            <p className="text-xs text-gray-400">
              Only properties with verified ownership or authorized representative links can submit requests
            </p>
          </div>
          <span className="text-xs text-gray-500">{properties.length} linked properties</span>
        </div>

        {properties.length === 0 ? (
          <div className="p-8 rounded-2xl bg-gray-900/60 border border-gray-800 text-center space-y-3">
            <Building2 className="w-10 h-10 text-gray-600 mx-auto" />
            <h3 className="text-base font-semibold text-gray-300">No Verified Properties Found</h3>
            <p className="text-xs text-gray-500 max-w-md mx-auto">
              You do not currently have any linked properties. Please visit your local Cadastre Office with
              your registered deed to link your citizen profile to your title record.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {properties.map((p) => (
              <div
                key={p.property_id || p.id}
                className="p-5 rounded-2xl bg-gray-900 border border-gray-800 hover:border-gray-700 transition flex flex-col justify-between space-y-4"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-gray-800 text-blue-400 border border-gray-700">
                      {p.property_reference}
                    </span>
                    <span className="flex items-center space-x-1 text-emerald-400 text-xs font-medium">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>{p.link_status}</span>
                    </span>
                  </div>

                  <h3 className="font-semibold text-white text-base line-clamp-1">{p.address}</h3>
                  <p className="text-xs text-gray-400 mt-1">
                    {p.locality ? `${p.locality}, ` : ''}{p.postal_code || 'Cadastral Zone'}
                  </p>

                  <div className="flex items-center space-x-4 text-xs text-gray-500 mt-3 pt-3 border-t border-gray-800/80">
                    <div>
                      <span className="text-gray-400 font-medium">Type: </span>
                      <span className="capitalize">{p.property_type.toLowerCase()}</span>
                    </div>
                    <div>
                      <span className="text-gray-400 font-medium">Auth: </span>
                      <span className="capitalize">{p.authorization_type.replace('_', ' ').toLowerCase()}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 pt-2">
                  <button
                    onClick={() => navigate(`/workflows/properties/${p.property_id || p.id}`)}
                    className="flex-1 px-3 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-white text-xs font-medium transition flex items-center justify-center space-x-1.5"
                  >
                    <span>View Property Twin</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => {
                      setSelectedPropertyForRequest(p.property_id || p.id);
                      setIsCreateModalOpen(true);
                    }}
                    className="px-3 py-2 rounded-xl bg-blue-900/40 hover:bg-blue-900/60 border border-blue-700/50 text-blue-300 text-xs font-medium transition"
                    title="Submit Request for this Property"
                  >
                    Request Service
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Requests Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">My Service Requests</h2>
            <p className="text-xs text-gray-400">Track current status, messages from review officers, and scheduled surveys</p>
          </div>
        </div>

        {requests.length === 0 ? (
          <div className="p-8 rounded-2xl bg-gray-900/60 border border-gray-800 text-center space-y-3">
            <FileText className="w-10 h-10 text-gray-600 mx-auto" />
            <h3 className="text-base font-semibold text-gray-300">No Service Requests Filed</h3>
            <p className="text-xs text-gray-500 max-w-md mx-auto">
              You haven't submitted any service requests yet. Use the "New Service Request" button above to file a request.
            </p>
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-950/80 text-gray-400 text-xs uppercase tracking-wider border-b border-gray-800">
                  <tr>
                    <th className="px-5 py-3.5">Reference</th>
                    <th className="px-5 py-3.5">Title & Type</th>
                    <th className="px-5 py-3.5">Priority</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5">Submitted</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800 text-gray-300">
                  {requests.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => navigate(`/workflows/requests/${r.id}`)}
                      className="hover:bg-gray-800/40 cursor-pointer transition"
                    >
                      <td className="px-5 py-4 font-mono text-xs font-semibold text-blue-400">
                        {r.request_reference}
                      </td>
                      <td className="px-5 py-4">
                        <div className="font-medium text-white">{r.title}</div>
                        <div className="text-xs text-gray-500">{r.request_type.replace('_', ' ')}</div>
                      </td>
                      <td className="px-5 py-4 text-xs">
                        <span className={getPriorityBadge(r.priority)}>{r.priority}</span>
                      </td>
                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getStatusBadge(
                            r.status
                          )}`}
                        >
                          {r.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-xs text-gray-400">
                        {new Date(r.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/workflows/requests/${r.id}`);
                          }}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition"
                          title="View Case Tracker"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Request Create Modal */}
      <RequestCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        defaultPropertyId={selectedPropertyForRequest}
        onRequestCreated={() => loadDashboardData()}
      />
    </div>
  );
};
