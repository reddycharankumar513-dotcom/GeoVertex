import React, { useState } from 'react';
import { X, AlertCircle, ShieldAlert, CheckCircle, Database } from 'lucide-react';
import { workflowApi } from '../../api/workflow';

interface ControlledUpdateModalProps {
  requestId: string;
  property: any;
  isOpen: boolean;
  onClose: () => void;
  onUpdated: (result: any) => void;
}

export const ControlledUpdateModal: React.FC<ControlledUpdateModalProps> = ({
  requestId,
  property,
  isOpen,
  onClose,
  onUpdated,
}) => {
  const [address, setAddress] = useState(property?.address || '');
  const [locality, setLocality] = useState(property?.locality || '');
  const [postalCode, setPostalCode] = useState(property?.postal_code || '');
  const [propertyType, setPropertyType] = useState(property?.property_type || 'FREEHOLD');
  const [status, setStatus] = useState(property?.status || 'ACTIVE');

  const [auditReason, setAuditReason] = useState('');
  const [sourceReference, setSourceReference] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!auditReason.trim() || !sourceReference.trim()) {
      setError('Audit reason and legal source reference are mandatory for controlled official record updates.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const updates: Record<string, any> = {};
      if (address !== property?.address) updates.address = address.trim();
      if (locality !== property?.locality) updates.locality = locality.trim();
      if (postalCode !== property?.postal_code) updates.postal_code = postalCode.trim();
      if (propertyType !== property?.property_type) updates.property_type = propertyType;
      if (status !== property?.status) updates.status = status;

      if (Object.keys(updates).length === 0) {
        setError('No attributes were modified.');
        setSubmitting(false);
        return;
      }

      const res = await workflowApi.executeControlledUpdate(requestId, {
        updates,
        audit_reason: auditReason.trim(),
        source_reference: sourceReference.trim(),
      });
      onUpdated(res);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to execute official record update');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-gray-900 border border-amber-900/60 rounded-2xl w-full max-w-xl shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-gray-800 bg-amber-950/20">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-amber-900/40 text-amber-400 border border-amber-700/50">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Execute Controlled Official Update</h2>
              <p className="text-xs text-amber-300/80">
                Audited Cadastral Mutation — Changes directly modify official registry records
              </p>
            </div>
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

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                Property Type
              </label>
              <select
                value={propertyType}
                onChange={(e) => setPropertyType(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-amber-500 transition text-sm"
              >
                <option value="FREEHOLD">Freehold</option>
                <option value="LEASEHOLD">Leasehold</option>
                <option value="MUNICIPAL">Municipal</option>
                <option value="RESIDENTIAL">Residential</option>
                <option value="COMMERCIAL">Commercial</option>
                <option value="INDUSTRIAL">Industrial</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                Cadastral Status
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-amber-500 transition text-sm"
              >
                <option value="ACTIVE">Active</option>
                <option value="REGISTERED">Registered</option>
                <option value="PENDING">Pending</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Official Property Address
            </label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-amber-500 transition text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                Locality / Ward
              </label>
              <input
                type="text"
                value={locality}
                onChange={(e) => setLocality(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-amber-500 transition text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                Postal Code
              </label>
              <input
                type="text"
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-amber-500 transition text-sm"
              />
            </div>
          </div>

          <div className="pt-2 border-t border-gray-800">
            <label className="block text-xs font-semibold uppercase tracking-wider text-amber-300 mb-2">
              Mandatory Legal Source Reference *
            </label>
            <input
              type="text"
              value={sourceReference}
              onChange={(e) => setSourceReference(e.target.value)}
              placeholder="e.g., Registered Partition Deed No. 4482/2026 or Gazette Order"
              className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 transition text-sm"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-amber-300 mb-2">
              Officer Audit Reasoning *
            </label>
            <textarea
              rows={3}
              value={auditReason}
              onChange={(e) => setAuditReason(e.target.value)}
              placeholder="Document the legal and factual justification for overriding or updating this property record..."
              className="w-full bg-gray-800 border border-gray-700 rounded-xl p-3 text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 transition text-sm resize-none"
              required
            />
          </div>

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
              disabled={submitting}
              className="px-6 py-2.5 rounded-xl bg-amber-600 text-white font-medium hover:bg-amber-500 transition shadow-lg shadow-amber-600/30 text-sm disabled:opacity-50 flex items-center space-x-2"
            >
              {submitting ? (
                <span>Executing Update...</span>
              ) : (
                <>
                  <Database className="w-4 h-4" />
                  <span>Execute Official Update</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
