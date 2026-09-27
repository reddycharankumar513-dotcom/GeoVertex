import React, { useState } from 'react';
import { CheckCircle2, XCircle, Edit3, X, AlertTriangle, FileText } from 'lucide-react';
import { DocumentExtractedField, FieldReviewPayload, FieldReviewStatus } from '../../types/document';

interface FieldCorrectionModalProps {
  field: DocumentExtractedField | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (fieldId: string, payload: FieldReviewPayload) => Promise<void>;
}

export const FieldCorrectionModal: React.FC<FieldCorrectionModalProps> = ({
  field,
  isOpen,
  onClose,
  onSubmit,
}) => {
  if (!isOpen || !field) return null;

  const [reviewStatus, setReviewStatus] = useState<FieldReviewStatus>(
    field.review_status === 'PENDING' ? 'ACCEPTED' : field.review_status
  );
  const [correctedValue, setCorrectedValue] = useState<string>(
    field.reviewed_value || field.normalized_value || field.raw_value
  );
  const [reviewComment, setReviewComment] = useState<string>(field.review_comment || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit(field.id, {
        review_status: reviewStatus,
        reviewed_value: reviewStatus === 'CORRECTED' ? correctedValue : undefined,
        review_comment: reviewComment.trim() || undefined,
      });
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to submit review');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getConfidenceBadgeColor = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'MEDIUM':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      default:
        return 'bg-red-500/20 text-red-400 border-red-500/30';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl max-w-lg w-full overflow-hidden text-slate-100 animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
          <div className="flex items-center gap-2">
            <Edit3 className="w-5 h-5 text-indigo-400" />
            <h3 className="font-semibold text-lg">Review Field: {field.field_name}</h3>
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

          <div className="grid grid-cols-2 gap-3 text-xs bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
            <div>
              <span className="text-slate-500 block">Category</span>
              <span className="font-medium text-slate-300">{field.field_category}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Data Type</span>
              <span className="font-medium text-slate-300">{field.data_type}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Method</span>
              <span className="font-medium text-slate-300">{field.extraction_method}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Confidence</span>
              <span
                className={`inline-block px-1.5 py-0.5 mt-0.5 rounded border text-[11px] font-semibold ${getConfidenceBadgeColor(
                  field.confidence_level
                )}`}
              >
                {field.confidence_level} ({Math.round((field.confidence || 0) * 100)}%)
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Raw Extracted Value</label>
            <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-sm font-mono text-slate-300 break-all select-all">
              {field.raw_value || '<empty>'}
            </div>
          </div>

          {field.normalized_value && field.normalized_value !== field.raw_value && (
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Deterministic Normalized Value
              </label>
              <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-sm font-mono text-indigo-300 break-all">
                {field.normalized_value}
              </div>
            </div>
          )}

          {field.evidence_text && (
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1 flex items-center gap-1">
                <FileText className="w-3.5 h-3.5" /> Text Evidence / Context (Page {field.page_number || 1})
              </label>
              <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs text-slate-400 italic">
                "{field.evidence_text}"
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-2">Review Action</label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setReviewStatus('ACCEPTED')}
                className={`flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border text-xs font-medium transition ${
                  reviewStatus === 'ACCEPTED'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50'
                    : 'bg-slate-800/40 text-slate-400 border-slate-700/60 hover:bg-slate-800'
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Accept
              </button>
              <button
                type="button"
                onClick={() => setReviewStatus('CORRECTED')}
                className={`flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border text-xs font-medium transition ${
                  reviewStatus === 'CORRECTED'
                    ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/50'
                    : 'bg-slate-800/40 text-slate-400 border-slate-700/60 hover:bg-slate-800'
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" /> Correct
              </button>
              <button
                type="button"
                onClick={() => setReviewStatus('REJECTED')}
                className={`flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border text-xs font-medium transition ${
                  reviewStatus === 'REJECTED'
                    ? 'bg-red-500/20 text-red-300 border-red-500/50'
                    : 'bg-slate-800/40 text-slate-400 border-slate-700/60 hover:bg-slate-800'
                }`}
              >
                <XCircle className="w-3.5 h-3.5" /> Reject
              </button>
            </div>
          </div>

          {reviewStatus === 'CORRECTED' && (
            <div>
              <label className="block text-xs font-medium text-indigo-300 mb-1">
                Human Corrected Value <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={correctedValue}
                onChange={(e) => setCorrectedValue(e.target.value)}
                required
                className="w-full px-3 py-2 bg-slate-950 border border-indigo-500/50 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                placeholder="Enter verified correct value"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">
              Reviewer Notes / Justification
            </label>
            <textarea
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="e.g. Corrected survey number based on deed schedule on page 2"
            />
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
              {isSubmitting ? 'Saving...' : 'Save Review'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
