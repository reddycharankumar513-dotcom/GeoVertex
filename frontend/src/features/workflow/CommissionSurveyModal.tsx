import React, { useState } from 'react';
import { X, AlertCircle, Compass, Calendar, CheckCircle } from 'lucide-react';
import { workflowApi } from '../../api/workflow';

interface CommissionSurveyModalProps {
  requestId: string;
  requestReference: string;
  isOpen: boolean;
  onClose: () => void;
  onCommissioned: (detail: any) => void;
}

export const CommissionSurveyModal: React.FC<CommissionSurveyModalProps> = ({
  requestId,
  requestReference,
  isOpen,
  onClose,
  onCommissioned,
}) => {
  const [surveyorId, setSurveyorId] = useState('');
  const [instructions, setInstructions] = useState('');
  const [dueDays, setDueDays] = useState(7);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!surveyorId.trim() || !instructions.trim()) {
      setError('Please provide surveyor identifier and field instructions.');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      const res = await workflowApi.commissionFieldSurvey(requestId, {
        surveyor_id: surveyorId.trim(),
        instructions: instructions.trim(),
        due_days: dueDays,
      });
      onCommissioned(res);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to commission field survey');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-lg shadow-2xl">
        <div className="flex items-center justify-between p-6 border-b border-gray-800 bg-gray-950/70">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-blue-900/40 text-blue-400 border border-blue-700/50">
              <Compass className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Commission Field Survey</h2>
              <p className="text-xs text-gray-400">Case Ref: {requestReference}</p>
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
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Assigned Registered Surveyor ID *
            </label>
            <input
              type="text"
              value={surveyorId}
              onChange={(e) => setSurveyorId(e.target.value)}
              placeholder="e.g., Surveyor UUID or Registered License ID"
              className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition text-sm"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Field Completion Due (Days)
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="number"
                min={1}
                max={60}
                value={dueDays}
                onChange={(e) => setDueDays(parseInt(e.target.value) || 7)}
                className="w-32 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition text-sm"
              />
              <span className="text-xs text-gray-400 flex items-center space-x-1">
                <Calendar className="w-4 h-4 text-gray-500" />
                <span>Working days from commission date</span>
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Field Survey Instructions & Verification Scope *
            </label>
            <textarea
              rows={4}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Specify benchmark control points, boundary conflict edges to measure, monument pins to verify, and photo capture requirements..."
              className="w-full bg-gray-800 border border-gray-700 rounded-xl p-4 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition text-sm resize-none"
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
              className="px-6 py-2.5 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-500 transition shadow-lg shadow-blue-600/30 text-sm disabled:opacity-50 flex items-center space-x-2"
            >
              {submitting ? (
                <span>Commissioning...</span>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  <span>Commission Survey</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
