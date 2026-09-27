import React, { useState, useEffect } from 'react';
import { X, AlertCircle, FileText, Clock, ShieldCheck, Check } from 'lucide-react';
import { workflowApi } from '../../api/workflow';
import { CitizenProperty, ServiceType, RequestPriority } from '../../types/workflow';

interface RequestCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRequestCreated: (req: any) => void;
  defaultPropertyId?: string;
}

export const RequestCreateModal: React.FC<RequestCreateModalProps> = ({
  isOpen,
  onClose,
  onRequestCreated,
  defaultPropertyId,
}) => {
  const [serviceTypes, setServiceTypes] = useState<ServiceType[]>([]);
  const [properties, setProperties] = useState<CitizenProperty[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>(defaultPropertyId || '');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<RequestPriority>('MEDIUM');

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  useEffect(() => {
    if (defaultPropertyId) {
      setSelectedPropertyId(defaultPropertyId);
    }
  }, [defaultPropertyId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [stList, props] = await Promise.all([
        workflowApi.listServiceTypes(true),
        workflowApi.listCitizenProperties(),
      ]);
      setServiceTypes(stList);
      if (stList.length > 0 && !selectedType) {
        setSelectedType(stList[0].code);
      }
      setProperties(props);
      if (props.length > 0 && !selectedPropertyId && !defaultPropertyId) {
        setSelectedPropertyId(props[0].property_id || props[0].id);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load request options');
    } finally {
      setLoading(false);
    }
  };

  const currentServiceType = serviceTypes.find((s) => s.code === selectedType);
  const selectedProperty = properties.find(
    (p) => (p.property_id || p.id) === selectedPropertyId
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedType || !title.trim() || !description.trim() || !selectedPropertyId) {
      setError('Please fill all mandatory fields and select a verified property.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const payload = {
        request_type: selectedType,
        title: title.trim(),
        description: description.trim(),
        jurisdiction_id: selectedProperty?.parcel_id || '00000000-0000-0000-0000-000000000000', // fallback if needed
        property_id: selectedPropertyId,
        parcel_id: selectedProperty?.parcel_id,
        priority,
      };

      const res = await workflowApi.createServiceRequest(payload);
      onRequestCreated(res);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to submit service request');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-gray-800 bg-gray-950/70">
          <div>
            <h2 className="text-xl font-bold text-white">Submit Public Service Request</h2>
            <p className="text-xs text-gray-400 mt-1">
              File a formal cadastral mutation, boundary survey, or certification request
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="m-6 p-4 rounded-xl bg-red-900/30 border border-red-700/50 flex items-start space-x-3 text-red-200 text-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-400 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Service Type Selection */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Service Category *
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition text-sm"
              disabled={loading}
              required
            >
              {serviceTypes.map((st) => (
                <option key={st.code} value={st.code}>
                  {st.name} ({st.code})
                </option>
              ))}
            </select>

            {currentServiceType && (
              <div className="mt-3 p-3.5 rounded-xl bg-gray-950 border border-gray-800 space-y-2 text-xs">
                <p className="text-gray-300">{currentServiceType.description}</p>
                <div className="flex items-center space-x-6 text-gray-400 pt-1">
                  <div className="flex items-center space-x-1.5">
                    <Clock className="w-3.5 h-3.5 text-blue-400" />
                    <span>Response SLA: {currentServiceType.response_sla_hours}h</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <Clock className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Target Completion: {currentServiceType.completion_sla_hours}h</span>
                  </div>
                </div>
                {currentServiceType.required_documents.length > 0 && (
                  <div className="pt-1">
                    <span className="text-gray-400 font-medium">Required Documents: </span>
                    <span className="text-amber-300">
                      {currentServiceType.required_documents.join(', ')}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Property Selection */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Verified Authorized Property *
            </label>
            {properties.length === 0 ? (
              <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-800/40 text-amber-300 text-xs">
                No verified property links found for your account. You can only submit requests for
                verified properties linked by the Cadastre Office.
              </div>
            ) : (
              <select
                value={selectedPropertyId}
                onChange={(e) => setSelectedPropertyId(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition text-sm"
                required
              >
                {properties.map((p) => (
                  <option key={p.property_id || p.id} value={p.property_id || p.id}>
                    {p.property_reference} — {p.address} ({p.authorization_type})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Title & Priority */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                Request Title *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Boundary Resurvey for North Partition"
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as RequestPriority)}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition text-sm"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Detailed Description & Objectives *
            </label>
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="State the purpose of this request, reason for mutation or survey, and reference relevant registered deed numbers..."
              className="w-full bg-gray-800 border border-gray-700 rounded-xl p-4 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition text-sm resize-none"
              required
            />
          </div>

          {/* Footer buttons */}
          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-800">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 rounded-xl border border-gray-700 text-gray-300 hover:text-white hover:bg-gray-800 transition text-sm font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || properties.length === 0}
              className="px-6 py-2.5 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-500 transition shadow-lg shadow-blue-600/30 text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {submitting ? (
                <span>Submitting...</span>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Submit Request</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
