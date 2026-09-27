import React, { useEffect, useState } from 'react';
import {
  UtilityAsset,
  UtilityNetwork,
  UtilityClash,
  UtilityMetrics,
  Utility3DFeature,
  UtilityType,
} from '../../types/utility';
import { utilityApi } from '../../api/utility';
import { AssetDetailModal } from '../../features/utility/AssetDetailModal';
import { NetworkCreateModal } from '../../features/utility/NetworkCreateModal';
import { ClashDetailModal } from '../../features/utility/ClashDetailModal';
import { useAuth } from '../../auth/AuthContext';

export const UndergroundExplorerPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'ASSETS' | 'NETWORKS' | 'CLASHES' | '3D_SUBSURFACE' | '2D_MAP'>('ASSETS');

  // Core Data State
  const [assets, setAssets] = useState<UtilityAsset[]>([]);
  const [networks, setNetworks] = useState<UtilityNetwork[]>([]);
  const [clashes, setClashes] = useState<UtilityClash[]>([]);
  const [metrics, setMetrics] = useState<UtilityMetrics | null>(null);
  const [scene3D, setScene3D] = useState<Utility3DFeature[]>([]);
  const [loading, setLoading] = useState(false);
  const [clashDetecting, setClashDetecting] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Filters
  const [utilityTypeFilter, setUtilityTypeFilter] = useState<string>('');
  const [reviewStatusFilter, setReviewStatusFilter] = useState<string>('');
  const [networkFilter, setNetworkFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected entities for modals
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [isAssetModalOpen, setIsAssetModalOpen] = useState(false);
  const [selectedClash, setSelectedClash] = useState<UtilityClash | null>(null);
  const [isClashModalOpen, setIsClashModalOpen] = useState(false);
  const [isNetworkModalOpen, setIsNetworkModalOpen] = useState(false);

  // Network topology view state
  const [selectedTopologyNetworkId, setSelectedTopologyNetworkId] = useState<string | null>(null);
  const [topologyData, setTopologyData] = useState<any | null>(null);
  const [topologyLoading, setTopologyLoading] = useState(false);

  // Fetch all utility data
  const fetchData = async () => {
    setLoading(true);
    try {
      const [assetsData, networksData, clashesData, metricsData] = await Promise.all([
        utilityApi.listAssets({
          network_id: networkFilter || undefined,
          review_status: reviewStatusFilter || undefined,
          limit: 100,
        }),
        utilityApi.listNetworks({
          utility_type: utilityTypeFilter || undefined,
          limit: 50,
        }),
        utilityApi.listClashes({ limit: 100 }),
        utilityApi.getMetrics(),
      ]);

      setAssets(assetsData);
      setNetworks(networksData);
      setClashes(clashesData);
      setMetrics(metricsData);
    } catch (err: any) {
      console.error('Error fetching underground infrastructure data:', err);
      setMessage({ text: err.message || 'Failed to fetch subsurface data', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [utilityTypeFilter, reviewStatusFilter, networkFilter]);

  // Load 3D scene when tab changes
  useEffect(() => {
    if (activeTab === '3D_SUBSURFACE' && scene3D.length === 0) {
      load3DScene();
    }
  }, [activeTab]);

  const load3DScene = async () => {
    try {
      const resp = await utilityApi.get3DScene({
        utility_type: utilityTypeFilter || undefined,
        network_id: networkFilter || undefined,
      });
      setScene3D(resp.features || []);
    } catch (err: any) {
      console.error('Failed to load 3D subsurface scene:', err);
    }
  };

  const handleInspectTopology = async (networkId: string) => {
    setSelectedTopologyNetworkId(networkId);
    setTopologyLoading(true);
    try {
      const topo = await utilityApi.getNetworkTopology(networkId);
      setTopologyData(topo);
    } catch (err: any) {
      setMessage({ text: err.message || 'Failed to inspect network topology', type: 'error' });
    } finally {
      setTopologyLoading(false);
    }
  };

  const handleRunClashDetection = async () => {
    setClashDetecting(true);
    setMessage({ text: 'Analyzing 3D spatial separation and detecting subsurface clashes...', type: 'info' });
    try {
      const detected = await utilityApi.runClashDetection({
        network_id: networkFilter || undefined,
      });
      setMessage({
        text: `3D Clash Detection finished. ${detected.length} conflict(s) evaluated and recorded.`,
        type: 'success',
      });
      fetchData();
    } catch (err: any) {
      setMessage({ text: err.message || 'Error executing clash detection', type: 'error' });
    } finally {
      setClashDetecting(false);
    }
  };

  const getDomainColor = (type?: string) => {
    switch (type) {
      case 'WATER':
        return 'text-blue-400 border-blue-800 bg-blue-950/40';
      case 'SEWER':
        return 'text-amber-500 border-amber-800 bg-amber-950/40';
      case 'STORMWATER':
        return 'text-cyan-400 border-cyan-800 bg-cyan-950/40';
      case 'GAS':
        return 'text-yellow-400 border-yellow-800 bg-yellow-950/40';
      case 'ELECTRICITY':
        return 'text-rose-400 border-rose-800 bg-rose-950/40';
      case 'TELECOM':
        return 'text-indigo-400 border-indigo-800 bg-indigo-950/40';
      case 'FIBER':
        return 'text-purple-400 border-purple-800 bg-purple-950/40';
      case 'DRAINAGE':
        return 'text-teal-400 border-teal-800 bg-teal-950/40';
      default:
        return 'text-slate-400 border-slate-700 bg-slate-800/40';
    }
  };

  const getReviewStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED':
        return 'bg-emerald-950/60 text-emerald-300 border-emerald-800';
      case 'CANDIDATE':
        return 'bg-amber-950/60 text-amber-300 border-amber-800';
      case 'REJECTED':
        return 'bg-rose-950/60 text-rose-300 border-rose-800';
      case 'REVISION_REQUIRED':
        return 'bg-purple-950/60 text-purple-300 border-purple-800';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  // Filtered Assets for Table
  const filteredAssets = assets.filter((asset) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      asset.id.toLowerCase().includes(q) ||
      asset.asset_type.toLowerCase().includes(q) ||
      (asset.material && asset.material.toLowerCase().includes(q)) ||
      (asset.network?.name && asset.network.name.toLowerCase().includes(q))
    );
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-2xl">🚇</span>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Underground Infrastructure & Subsurface Utility Intelligence
            </h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic 3D depth geometry, subsurface networks, clash detection, and cadastral spatial interactions.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {(user?.role === 'ADMIN' || user?.role === 'GOVERNMENT_OFFICER') && (
            <button
              onClick={() => setIsNetworkModalOpen(true)}
              className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center space-x-2 transition"
            >
              <span>+ New Network</span>
            </button>
          )}
          <button
            disabled={clashDetecting}
            onClick={handleRunClashDetection}
            className="px-3.5 py-2 bg-rose-600/90 hover:bg-rose-600 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center space-x-2 transition shadow-lg shadow-rose-900/20"
          >
            <span>{clashDetecting ? '⌛ Detecting Clashes...' : '⚠️ Run Clash Detection'}</span>
          </button>
          <button
            onClick={fetchData}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Notification Toast */}
      {message && (
        <div
          className={`p-3 rounded-lg text-xs flex justify-between items-center border ${
            message.type === 'error'
              ? 'bg-rose-950/60 border-rose-800 text-rose-300'
              : message.type === 'success'
              ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
              : 'bg-sky-950/60 border-sky-800 text-sky-300'
          }`}
        >
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="text-slate-400 hover:text-white ml-4">
            ✕
          </button>
        </div>
      )}

      {/* Executive KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium block">Total Assets</span>
          <span className="text-2xl font-bold text-white mt-1 block">
            {metrics?.total_assets ?? assets.length}
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">Pipelines, Nodes, Vaults</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium block">Active Networks</span>
          <span className="text-2xl font-bold text-sky-400 mt-1 block">
            {metrics?.total_networks ?? networks.length}
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">Configured domains</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium block">Review Queue</span>
          <span className="text-2xl font-bold text-amber-400 mt-1 block">
            {metrics?.candidates_requiring_review ?? (metrics?.by_review_status?.['CANDIDATE'] ?? 0)}
          </span>
          <span className="text-[11px] text-amber-500/80 mt-1 block">Requires official verification</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium block">3D Clashes Detected</span>
          <span className="text-2xl font-bold text-rose-400 mt-1 block">
            {metrics?.total_clashes ?? clashes.length}
          </span>
          <span className="text-[11px] text-rose-500/80 mt-1 block">
            {metrics?.open_clashes ?? clashes.filter((c) => c.status === 'DETECTED' || c.status === 'OPEN').length} unresolved
          </span>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <span className="text-xs text-slate-400 font-medium block">Unknown Depth</span>
          <span className="text-2xl font-bold text-purple-400 mt-1 block">
            {metrics?.unknown_depth_assets ?? (metrics?.assets_with_unknown_depth ?? 0)}
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">Missing vertical elevation</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-800 flex space-x-6 text-sm">
        <button
          onClick={() => setActiveTab('ASSETS')}
          className={`pb-3 font-semibold transition border-b-2 flex items-center space-x-2 ${
            activeTab === 'ASSETS'
              ? 'text-sky-400 border-sky-400'
              : 'text-slate-400 border-transparent hover:text-slate-300'
          }`}
        >
          <span>📦 Subsurface Assets ({assets.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('NETWORKS')}
          className={`pb-3 font-semibold transition border-b-2 flex items-center space-x-2 ${
            activeTab === 'NETWORKS'
              ? 'text-sky-400 border-sky-400'
              : 'text-slate-400 border-transparent hover:text-slate-300'
          }`}
        >
          <span>🕸️ Networks & Topology ({networks.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('CLASHES')}
          className={`pb-3 font-semibold transition border-b-2 flex items-center space-x-2 ${
            activeTab === 'CLASHES'
              ? 'text-rose-400 border-rose-400'
              : 'text-slate-400 border-transparent hover:text-slate-300'
          }`}
        >
          <span>⚠️ 3D Clashes & Clearances ({clashes.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('3D_SUBSURFACE')}
          className={`pb-3 font-semibold transition border-b-2 flex items-center space-x-2 ${
            activeTab === '3D_SUBSURFACE'
              ? 'text-sky-400 border-sky-400'
              : 'text-slate-400 border-transparent hover:text-slate-300'
          }`}
        >
          <span>🧊 3D Subsurface Scene</span>
        </button>
        <button
          onClick={() => setActiveTab('2D_MAP')}
          className={`pb-3 font-semibold transition border-b-2 flex items-center space-x-2 ${
            activeTab === '2D_MAP'
              ? 'text-sky-400 border-sky-400'
              : 'text-slate-400 border-transparent hover:text-slate-300'
          }`}
        >
          <span>🗺️ 2D Cadastral Overlay</span>
        </button>
      </div>

      {/* TAB 1: ASSETS */}
      {activeTab === 'ASSETS' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center gap-4 text-xs">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by Asset ID, material, type, network..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-slate-400">Domain:</span>
              <select
                value={utilityTypeFilter}
                onChange={(e) => setUtilityTypeFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white focus:outline-none focus:border-sky-500"
              >
                <option value="">All Domains</option>
                <option value="WATER">Water</option>
                <option value="SEWER">Sewer</option>
                <option value="STORMWATER">Stormwater</option>
                <option value="GAS">Gas</option>
                <option value="ELECTRICITY">Electricity</option>
                <option value="TELECOM">Telecom</option>
                <option value="FIBER">Fiber</option>
                <option value="DRAINAGE">Drainage</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-slate-400">Review Status:</span>
              <select
                value={reviewStatusFilter}
                onChange={(e) => setReviewStatusFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white focus:outline-none focus:border-sky-500"
              >
                <option value="">All Review Statuses</option>
                <option value="CANDIDATE">Candidate (Pending Review)</option>
                <option value="VERIFIED">Verified</option>
                <option value="REVISION_REQUIRED">Revision Required</option>
                <option value="REJECTED">Rejected</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-slate-400">Network:</span>
              <select
                value={networkFilter}
                onChange={(e) => setNetworkFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white focus:outline-none focus:border-sky-500"
              >
                <option value="">All Networks</option>
                {networks.map((net) => (
                  <option key={net.id} value={net.id}>
                    {net.name} ({net.utility_type})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Assets Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Asset ID / Network</th>
                    <th className="px-4 py-3">Domain & Type</th>
                    <th className="px-4 py-3">Depth Model</th>
                    <th className="px-4 py-3">Specification</th>
                    <th className="px-4 py-3">Quality</th>
                    <th className="px-4 py-3">Review Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                        Loading underground infrastructure assets...
                      </td>
                    </tr>
                  ) : filteredAssets.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                        No subsurface assets match the current filters.
                      </td>
                    </tr>
                  ) : (
                    filteredAssets.map((asset) => {
                      const domain = asset.network?.utility_type || 'OTHER';
                      const effectiveDepth = asset.depth ?? asset.depth_m;
                      const effectiveElevation = asset.ground_elevation ?? asset.elevation_m;
                      return (
                        <tr key={asset.id} className="hover:bg-slate-800/40 transition">
                          <td className="px-4 py-3">
                            <span className="font-mono text-white font-medium block">
                              {asset.id.slice(0, 8)}...
                            </span>
                            <span className="text-[11px] text-slate-400 block truncate max-w-[180px]">
                              {asset.network?.name || 'Unassigned Network'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold border ${getDomainColor(
                                domain
                              )}`}
                            >
                              {domain}
                            </span>
                            <span className="text-slate-300 block mt-0.5 font-medium">
                              {asset.asset_type}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {effectiveDepth !== undefined && effectiveDepth !== null ? (
                              <div>
                                <span className="text-white font-mono font-medium block">
                                  {effectiveDepth.toFixed(2)} m depth
                                </span>
                                <span className="text-[10px] text-slate-400 block">
                                  Elev: {effectiveElevation !== undefined && effectiveElevation !== null ? `${effectiveElevation.toFixed(2)}m` : 'N/A'}
                                </span>
                              </div>
                            ) : (
                              <span className="text-purple-400 font-mono text-[11px]">
                                Unknown / Unspecified
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-slate-300">
                            <div>
                              <span>{asset.material || 'Material unrecorded'}</span>
                              {(asset.diameter || asset.diameter_mm) && (
                                <span className="text-slate-400 block text-[10px]">
                                  Ø {asset.diameter ?? asset.diameter_mm} mm
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[11px]">
                              {asset.quality_level || 'QL-D'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold border ${getReviewStatusBadge(
                                asset.review_status
                              )}`}
                            >
                              {asset.review_status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => {
                                setSelectedAssetId(asset.id);
                                setIsAssetModalOpen(true);
                              }}
                              className="px-2.5 py-1 bg-sky-600/80 hover:bg-sky-600 text-white rounded font-medium text-xs transition"
                            >
                              Inspect & Review
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: NETWORKS & TOPOLOGY */}
      {activeTab === 'NETWORKS' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {networks.map((net) => (
              <div
                key={net.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`px-2.5 py-0.5 rounded text-xs font-semibold border ${getDomainColor(
                      net.utility_type
                    )}`}
                  >
                    {net.utility_type}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    CRS: {net.coordinate_system || 'EPSG:4326'}
                  </span>
                </div>

                <div>
                  <h3 className="text-base font-semibold text-white">{net.name}</h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Owner: {net.owner_organization || net.owner || 'Unassigned'} • Operator: {net.operator_organization || net.operator || 'Unassigned'}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs bg-slate-800/40 p-2.5 rounded-lg border border-slate-800">
                  <div>
                    <span className="text-slate-400 block text-[11px]">Vertical Datum</span>
                    <span className="text-slate-200 font-mono">{net.vertical_datum || 'WGS84'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Status</span>
                    <span className="text-emerald-400 font-medium">{net.status}</span>
                  </div>
                </div>

                <button
                  onClick={() => handleInspectTopology(net.id)}
                  className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 rounded-lg text-xs font-semibold transition flex items-center justify-center space-x-1"
                >
                  <span>🕸️ Inspect Network Graph & Topology</span>
                </button>
              </div>
            ))}
          </div>

          {/* Topology Detail View */}
          {selectedTopologyNetworkId && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">📊</span>
                  <h3 className="text-base font-semibold text-white">
                    Topology Graph Analysis: {networks.find((n) => n.id === selectedTopologyNetworkId)?.name}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedTopologyNetworkId(null)}
                  className="text-slate-400 hover:text-white"
                >
                  ✕
                </button>
              </div>

              {topologyLoading ? (
                <div className="py-8 text-center text-slate-400">Computing graph topology...</div>
              ) : topologyData ? (
                <div className="space-y-4 text-xs">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/60">
                      <span className="text-slate-400 block text-[11px]">Nodes (Junctions)</span>
                      <span className="text-lg font-bold text-white mt-1 block">
                        {topologyData.total_nodes ?? 0}
                      </span>
                    </div>
                    <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/60">
                      <span className="text-slate-400 block text-[11px]">Linear Segments</span>
                      <span className="text-lg font-bold text-sky-400 mt-1 block">
                        {topologyData.total_segments ?? 0}
                      </span>
                    </div>
                    <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/60">
                      <span className="text-slate-400 block text-[11px]">Connected Components</span>
                      <span className="text-lg font-bold text-amber-400 mt-1 block">
                        {topologyData.connected_components ?? 1}
                      </span>
                    </div>
                    <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/60">
                      <span className="text-slate-400 block text-[11px]">Dangling Endpoints</span>
                      <span className="text-lg font-bold text-purple-400 mt-1 block">
                        {topologyData.dangling_endpoints?.length ?? 0}
                      </span>
                    </div>
                  </div>

                  {topologyData.dangling_endpoints && topologyData.dangling_endpoints.length > 0 && (
                    <div className="bg-slate-800/40 border border-slate-700/60 p-3 rounded-lg">
                      <h4 className="font-semibold text-slate-300 text-xs mb-2">
                        Dangling Endpoints (No connected junction node)
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {topologyData.dangling_endpoints.map((ep: any, idx: number) => (
                          <span
                            key={idx}
                            className="px-2 py-1 bg-purple-950/60 border border-purple-800 text-purple-300 rounded font-mono text-[11px]"
                          >
                            Segment: {ep.segment_id?.slice(0, 8)}... (at {ep.position})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: 3D CLASHES */}
      {activeTab === 'CLASHES' && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex justify-between items-center text-xs">
            <p className="text-slate-300">
              Deterministic 3D spatial collision engine detects minimum separation clearances between utilities and subsurface structures.
            </p>
            <button
              disabled={clashDetecting}
              onClick={handleRunClashDetection}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white rounded font-medium transition"
            >
              {clashDetecting ? 'Running Clash Analysis...' : 'Re-Run Clash Detection'}
            </button>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Clash ID</th>
                    <th className="px-4 py-3">Severity & Type</th>
                    <th className="px-4 py-3">Conflicting Assets</th>
                    <th className="px-4 py-3">Measured Clearance</th>
                    <th className="px-4 py-3">Separation Rule</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {clashes.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                        No 3D spatial clashes recorded. Run Clash Detection to evaluate candidate network intersections.
                      </td>
                    </tr>
                  ) : (
                    clashes.map((c) => {
                      const asset1 = c.asset_1_id || c.asset_a_id;
                      const asset2 = c.asset_2_id || c.asset_b_id;
                      const measured = c.clearance_distance_m ?? c.distance_m ?? c.measured_horizontal_separation_m;
                      const isUnresolved = c.status === 'DETECTED' || c.status === 'OPEN';
                      return (
                        <tr key={c.id} className="hover:bg-slate-800/40 transition">
                          <td className="px-4 py-3 font-mono text-white">{c.id.slice(0, 8)}...</td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold border ${
                                c.severity === 'CRITICAL'
                                  ? 'bg-rose-950/80 text-rose-300 border-rose-700'
                                  : c.severity === 'MAJOR' || c.severity === 'ERROR'
                                  ? 'bg-amber-950/80 text-amber-300 border-amber-700'
                                  : 'bg-yellow-950/80 text-yellow-300 border-yellow-700'
                              }`}
                            >
                              {c.severity}
                            </span>
                            <span className="text-slate-400 block text-[10px] mt-0.5">
                              {c.clash_type || `${c.horizontal_relationship || 'INTERSECTION'}`}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono text-[11px]">
                            <span className="text-sky-400 block">{asset1 ? `${asset1.slice(0, 8)}...` : 'Unknown A'}</span>
                            <span className="text-amber-400 block">{asset2 ? `${asset2.slice(0, 8)}...` : 'Unknown B'}</span>
                          </td>
                          <td className="px-4 py-3 font-mono text-white">
                            {measured !== undefined && measured !== null
                              ? `${measured.toFixed(2)} m`
                              : '0.00 m (Physical Direct)'}
                          </td>
                          <td className="px-4 py-3 text-slate-300 font-mono text-[11px]">
                            {c.rule_code || 'SEPARATION_RULE_NOT_CONFIGURED'}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold border ${
                                isUnresolved
                                  ? 'bg-rose-900/40 text-rose-300 border-rose-800'
                                  : c.status === 'RESOLVED'
                                  ? 'bg-emerald-900/40 text-emerald-300 border-emerald-800'
                                  : 'bg-slate-800 text-slate-300 border-slate-700'
                              }`}
                            >
                              {c.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => {
                                setSelectedClash(c);
                                setIsClashModalOpen(true);
                              }}
                              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded font-medium text-xs transition"
                            >
                              Review & Mitigate
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: 3D SUBSURFACE SCENE */}
      {activeTab === '3D_SUBSURFACE' && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-semibold text-white">3D Underground Volumetric Explorer</h3>
                <p className="text-xs text-slate-400">
                  Volumetric extrusions rendered with explicit vertical datum: z_ground - z_centerline = depth.
                </p>
              </div>
              <button
                onClick={load3DScene}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 rounded-lg text-xs font-semibold transition"
              >
                🔄 Reload 3D Scene
              </button>
            </div>

            {/* Depth Strata Breakdown */}
            <div className="grid grid-cols-4 gap-3 text-xs">
              <div className="bg-slate-800/60 p-3 rounded border border-slate-700/60">
                <span className="text-sky-300 font-semibold block">Surface / Ground (0.0 m)</span>
                <span className="text-slate-400 text-[11px] block mt-1">Ground reference datum</span>
              </div>
              <div className="bg-slate-800/60 p-3 rounded border border-slate-700/60">
                <span className="text-amber-300 font-semibold block">Shallow Zone (0.0 - 1.2 m)</span>
                <span className="text-slate-400 text-[11px] block mt-1">Telecom, fiber, low-voltage power</span>
              </div>
              <div className="bg-slate-800/60 p-3 rounded border border-slate-700/60">
                <span className="text-blue-300 font-semibold block">Intermediate Zone (1.2 - 2.5 m)</span>
                <span className="text-slate-400 text-[11px] block mt-1">Gas, water mains, high-voltage</span>
              </div>
              <div className="bg-slate-800/60 p-3 rounded border border-slate-700/60">
                <span className="text-purple-300 font-semibold block">Deep Subsurface (&gt; 2.5 m)</span>
                <span className="text-slate-400 text-[11px] block mt-1">Sanitary sewers, trunk stormwater</span>
              </div>
            </div>

            {/* 3D Feature Grid */}
            <div className="bg-slate-950/80 rounded-lg border border-slate-800 p-4">
              <h4 className="text-slate-300 font-semibold text-xs mb-3">
                Extruded 3D Features ({scene3D.length})
              </h4>
              <div className="max-h-80 overflow-y-auto space-y-2">
                {scene3D.map((f, idx) => {
                  const featureId = f.asset_id || f.id || `f-${idx}`;
                  const centerline = f.centerline_elevation ?? f.centerline_elevation_m;
                  const depthVal = f.depth ?? f.depth_m;
                  const diameterVal = f.diameter_m ? f.diameter_m : f.diameter_mm ? f.diameter_mm / 1000 : null;
                  return (
                    <div
                      key={idx}
                      className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between text-xs hover:border-slate-700 transition"
                    >
                      <div className="flex items-center space-x-3">
                        <span className="font-mono text-white font-medium">{featureId.slice(0, 8)}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getDomainColor(
                            f.utility_type
                          )}`}
                        >
                          {f.utility_type}
                        </span>
                        <span className="text-slate-400 text-[11px]">{f.asset_type || f.feature_type}</span>
                      </div>
                      <div className="flex items-center space-x-4 font-mono text-[11px]">
                        <span className="text-sky-300">
                          Centerline: {centerline !== undefined && centerline !== null ? `${centerline.toFixed(2)}m` : 'N/A'}
                        </span>
                        <span className="text-amber-300">
                          Depth: {depthVal !== undefined && depthVal !== null ? `${depthVal.toFixed(2)}m` : 'Unknown'}
                        </span>
                        <span className="text-slate-500">
                          Ø {diameterVal ? `${diameterVal.toFixed(2)}m` : 'N/A'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: 2D MAP OVERLAY */}
      {activeTab === '2D_MAP' && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="border-b border-slate-800 pb-3">
              <h3 className="text-base font-semibold text-white">Subsurface 2D Cadastral Overlay</h3>
              <p className="text-xs text-slate-400">
                Subsurface linear networks and junction nodes mapped across surface cadastral parcels.
              </p>
            </div>

            {/* Simulated 2D Map Canvas Canvas Visual */}
            <div className="w-full h-96 bg-slate-950 rounded-lg border border-slate-800 relative flex items-center justify-center overflow-hidden">
              {/* Grid Background */}
              <div
                className="absolute inset-0 opacity-20 pointer-events-none"
                style={{
                  backgroundImage: 'radial-gradient(circle, #38bdf8 1px, transparent 1px)',
                  backgroundSize: '24px 24px',
                }}
              />

              <div className="text-center space-y-2 z-10 p-6 bg-slate-900/90 border border-slate-800 rounded-xl shadow-xl max-w-md">
                <span className="text-3xl block">🗺️</span>
                <h4 className="text-white font-semibold text-sm">Interactive Subsurface GIS View</h4>
                <p className="text-xs text-slate-400">
                  {assets.length} utility assets mapped to cadastral parcels. Use the Assets table to inspect individual technical spatial relationships and crossings.
                </p>
                <div className="pt-2 flex justify-center space-x-2">
                  <button
                    onClick={() => setActiveTab('ASSETS')}
                    className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-medium transition"
                  >
                    View Asset Technical Properties
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Asset Detail Modal */}
      <AssetDetailModal
        assetId={selectedAssetId}
        isOpen={isAssetModalOpen}
        canReview={user?.role === 'ADMIN' || user?.role === 'GOVERNMENT_OFFICER'}
        onClose={() => {
          setIsAssetModalOpen(false);
          setSelectedAssetId(null);
        }}
        onAssetUpdated={() => {
          fetchData();
        }}
      />

      {/* Clash Detail Modal */}
      <ClashDetailModal
        clash={selectedClash}
        isOpen={isClashModalOpen}
        onClose={() => {
          setIsClashModalOpen(false);
          setSelectedClash(null);
        }}
        onClashUpdated={() => {
          fetchData();
        }}
      />

      {/* Network Create Modal */}
      <NetworkCreateModal
        isOpen={isNetworkModalOpen}
        onClose={() => setIsNetworkModalOpen(false)}
        onNetworkCreated={() => {
          fetchData();
        }}
      />
    </div>
  );
};
