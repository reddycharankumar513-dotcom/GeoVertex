import React, { useState } from 'react';
import { Link2, X, AlertTriangle } from 'lucide-react';
import {
  EntityLinkCreatePayload,
  LinkRelationshipType,
  TargetEntityType,
} from '../../types/document';

interface DocumentLinkModalProps {
  documentId: string;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: EntityLinkCreatePayload) => Promise<void>;
  prefilledEntityId?: string;
  prefilledEntityType?: TargetEntityType;
}

export const DocumentLinkModal: React.FC<DocumentLinkModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  prefilledEntityId = '',
  prefilledEntityType = 'PARCEL',
}) => {
  if (!isOpen) return null;

  const [entityType, setEntityType] = useState<TargetEntityType>(prefilledEntityType);
  const [entityId, setEntityId] = useState<string>(prefilledEntityId);
  const [relationshipType, setRelationshipType] = useState<LinkRelationshipType>('PRIMARY_TITLE');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entityId.trim()) {
      setError('Entity ID is required');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit({
        entity_type: entityType,
        entity_id: entityId.trim(),
        relationship_type: relationshipType,
        match_confidence: 1.0,
        match_method: 'MANUAL_LINK',
      });
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to link document');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl max-w-md w-full overflow-hidden text-slate-100 animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
          <div className="flex items-center gap-2">
            <Link2 className="w-5 h-5 text-indigo-400" />
            <h3 className="font-semibold text-lg">Link Document to Cadastre</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Target Cadastral Entity</label>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value as TargetEntityType)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="PARCEL">Cadastral Parcel</option>
              <option value="PROPERTY">Property Record</option>
              <option value="BUILDING">3D Building Footprint / Volume</option>
              <option value="UNIT">Vertical Unit / Condominium</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Entity Identifier (UUID or Cadastral Number) <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              placeholder="e.g. 11111111-1111-1111-1111-111111111111"
              required
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Relationship Type</label>
            <select
              value={relationshipType}
              onChange={(e) => setRelationshipType(e.target.value as LinkRelationshipType)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="PRIMARY_TITLE">Primary Title Deed</option>
              <option value="SUPPORTING_DEED">Supporting / Link Deed</option>
              <option value="SURVEY_REFERENCE">Survey Reference / Plan</option>
              <option value="MORTGAGE_LIEN">Mortgage / Encumbrance</option>
              <option value="TAX_RECORD">Tax / Assessment Record</option>
              <option value="PERMIT_APPROVAL">Building / Floor Permit</option>
              <option value="LEGAL_DISPUTE">Legal / Court Order</option>
              <option value="HISTORICAL_RECORD">Historical Record</option>
            </select>
          </div>

          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-300/90 leading-relaxed">
            Linking binds this legal document to the cadastral intelligence registry. Cadastral validation rules (Phase 7) will verify boundary, area, and reference consistency against this entity.
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-indigo-600/20"
            >
              {isSubmitting ? 'Linking...' : 'Confirm Link'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
