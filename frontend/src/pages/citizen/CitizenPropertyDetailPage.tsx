import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Building2,
  FileText,
  MapPin,
  ShieldCheck,
  Calendar,
  Layers,
  Box,
  Plus,
  ExternalLink,
  AlertCircle,
  FileCheck,
} from 'lucide-react';
import { workflowApi } from '../../api/workflow';
import { CitizenProperty, ServiceRequest } from '../../types/workflow';
import { RequestCreateModal } from '../../features/workflow/RequestCreateModal';

export const CitizenPropertyDetailPage: React.FC = () => {
  const { propertyId } = useParams<{ propertyId: string }>();
  const navigate = useNavigate();

  const [property, setProperty] = useState<CitizenProperty | null>(null);
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  useEffect(() => {
    if (propertyId) {
      loadPropertyDetail();
    }
  }, [propertyId]);

  const loadPropertyDetail = async () => {
    try {
      setLoading(true);
      setError(null);

      // Find from citizen's verified list
      const props = await workflowApi.listCitizenProperties();
      const matched = props.find((p) => (p.property_id || p.id) === propertyId);
      if (!matched) {
        throw new Error('Property record not found or unauthorized for this citizen profile.');
      }
      setProperty(matched);

      // Load related requests
      const reqList = await workflowApi.listServiceRequests();
      const filtered = reqList.items.filter((r) => r.property_id === propertyId);
      setRequests(filtered);
    } catch (err: any) {
      setError(err?.message || 'Failed to load property details');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-gray-500">
        <div className="inline-block animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mb-3" />
        <div>Loading verified property twin...</div>
      </div>
    );
  }

  if (error || !property) {
    return (
      <div className="p-8 max-w-4xl mx-auto space-y-4">
        <button
          onClick={() => navigate('/citizen/dashboard')}
          className="flex items-center space-x-2 text-sm text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </button>
        <div className="p-6 rounded-2xl bg-red-950/40 border border-red-800 text-red-200 text-sm flex items-center space-x-3">
          <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
          <span>{error || 'Property not found'}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      {/* Header & Breadcrumb */}
      <div className="space-y-3">
        <button
          onClick={() => navigate('/citizen/dashboard')}
          className="flex items-center space-x-2 text-xs text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to My Properties</span>
        </button>

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-800 pb-6">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-sm px-2.5 py-0.5 rounded-lg bg-blue-950 border border-blue-800 text-blue-300 font-semibold">
                {property.property_reference}
              </span>
              <span className="flex items-center space-x-1 text-emerald-400 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/60">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>{property.link_status} — {property.authorization_type}</span>
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white mt-2">{property.address}</h1>
            <p className="text-xs text-gray-400 mt-1 flex items-center space-x-2">
              <MapPin className="w-3.5 h-3.5 text-gray-500" />
              <span>
                {property.locality ? `${property.locality}, ` : ''}{property.postal_code || 'Cadastral Zone'}
              </span>
              <span>•</span>
              <span>Parcel ID: {property.parcel_id}</span>
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition shadow-lg shadow-blue-600/30 flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Request Service for This Property</span>
            </button>
          </div>
        </div>
      </div>

      {/* Grid: 3D Twin & Property Data */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Digital Twin & Map */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-white font-semibold text-sm">
                <Box className="w-4 h-4 text-blue-400" />
                <span>Cadastral Digital Twin Visualizer</span>
              </div>
              <span className="text-xs text-emerald-400 bg-emerald-950/60 px-2.5 py-0.5 rounded-full border border-emerald-800/50">
                Verified 3D Volume
              </span>
            </div>

            <div className="h-72 rounded-xl bg-gray-950 border border-gray-800 flex flex-col items-center justify-center text-center p-6 space-y-3 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-tr from-blue-950/20 to-purple-950/20 pointer-events-none" />
              <Layers className="w-12 h-12 text-blue-500/60 animate-pulse" />
              <div className="space-y-1 z-10">
                <h4 className="text-white font-medium text-sm">3D Cadastral Digital Twin Active</h4>
                <p className="text-xs text-gray-400 max-w-sm">
                  Property parcel footprint, vertical rights boundary, and building extrusion volume
                  synchronized from official registry geometry.
                </p>
              </div>
              <button
                onClick={() => navigate('/3d/viewer')}
                className="z-10 px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-white text-xs font-medium transition flex items-center space-x-1.5"
              >
                <span>Launch Full 3D Platform Viewer</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Related Requests Table */}
          <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-white text-sm">Service & Mutation History</h3>
              <span className="text-xs text-gray-500">{requests.length} requests filed</span>
            </div>

            {requests.length === 0 ? (
              <div className="p-6 text-center text-gray-500 text-xs">
                No past service or mutation requests on record for this property.
              </div>
            ) : (
              <div className="divide-y divide-gray-800 text-xs">
                {requests.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => navigate(`/workflows/requests/${r.id}`)}
                    className="py-3 flex items-center justify-between hover:bg-gray-800/40 p-2 rounded-xl cursor-pointer transition"
                  >
                    <div>
                      <div className="font-medium text-white">{r.title}</div>
                      <div className="text-gray-500 font-mono mt-0.5">
                        {r.request_reference} • {r.request_type.replace(/_/g, ' ')}
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="px-2 py-0.5 rounded-full bg-blue-900/40 text-blue-300 border border-blue-700/50">
                        {r.status.replace(/_/g, ' ')}
                      </span>
                      <span className="text-gray-500">
                        {new Date(r.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Property Attributes Card */}
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-gray-900 border border-gray-800 space-y-4">
            <h3 className="font-semibold text-white text-sm border-b border-gray-800 pb-3">
              Cadastral Record Summary
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-gray-400 block mb-0.5">Property Type</span>
                <span className="text-white font-medium capitalize">{property.property_type.toLowerCase()}</span>
              </div>
              <div>
                <span className="text-gray-400 block mb-0.5">Status</span>
                <span className="text-emerald-400 font-medium">{property.status}</span>
              </div>
              <div>
                <span className="text-gray-400 block mb-0.5">Associated Parcel</span>
                <span className="font-mono text-gray-300">{property.parcel_number || property.parcel_id}</span>
              </div>
              <div>
                <span className="text-gray-400 block mb-0.5">Units / Subdivisions</span>
                <span className="text-white font-medium">{property.units_count} unit(s)</span>
              </div>
              <div>
                <span className="text-gray-400 block mb-0.5">Verification Date</span>
                <span className="text-gray-300">{new Date(property.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-blue-950/30 border border-blue-900/50 space-y-3">
            <div className="flex items-center space-x-2 text-blue-400 text-xs font-semibold uppercase tracking-wider">
              <FileCheck className="w-4 h-4" />
              <span>Certified Ownership</span>
            </div>
            <p className="text-xs text-gray-300 leading-relaxed">
              This property is cryptographically linked to your citizen identity. All mutation requests,
              subdivision petitions, and boundary certifications are formally timestamped in the Cadastre
              Audit Trail.
            </p>
          </div>
        </div>
      </div>

      <RequestCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        defaultPropertyId={property.property_id || property.id}
        onRequestCreated={() => loadPropertyDetail()}
      />
    </div>
  );
};
