import React, { useState } from 'react';
import { Cpu, AlertTriangle, X, Play, Layers } from 'lucide-react';
import { aiApi } from '../../api/ai';

interface AIJobCreateModalProps {
  onClose: () => void;
  onSuccess: () => void;
  defaultBuildingId?: string;
}

export const AIJobCreateModal: React.FC<AIJobCreateModalProps> = ({
  onClose,
  onSuccess,
  defaultBuildingId = '',
}) => {
  const [jobType, setJobType] = useState('BUILDING_EXTRACTION');
  const [targetType, setTargetType] = useState('BUILDING');
  const [targetId, setTargetId] = useState(defaultBuildingId);
  const [modelId, setModelId] = useState('building-segmentation-v1');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isFloorModel = modelId === 'floor-extraction-v1' || jobType === 'FLOOR_EXTRACTION';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetId.trim()) {
      setErrorMsg('Target feature ID is required');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const clientReqId = `job-req-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      await aiApi.createJob({
        client_request_id: clientReqId,
        job_type: isFloorModel ? 'FLOOR_EXTRACTION' : jobType,
        target_type: targetType,
        target_id: targetId.trim(),
        model_id: modelId,
        model_version: '1.0.0',
        parameters: {
          confidence_threshold: 0.65,
          min_building_area: 10.0,
        },
      });
      onSuccess();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to dispatch AI job');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">Run AI Spatial Extraction</h2>
              <p className="text-xs text-slate-400">Enqueue inference job for survey evidence processing</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-sm text-slate-200">
          {errorMsg && (
            <div className="p-3 bg-red-950/50 border border-red-500/40 rounded-xl text-red-200 text-xs">
              {errorMsg}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Extraction Pipeline
            </label>
            <select
              value={jobType}
              onChange={(e) => {
                const val = e.target.value;
                setJobType(val);
                if (val === 'FLOOR_EXTRACTION') {
                  setModelId('floor-extraction-v1');
                } else {
                  setModelId('building-segmentation-v1');
                }
              }}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-purple-400"
            >
              <option value="BUILDING_EXTRACTION">Building Footprint Extraction</option>
              <option value="FLOOR_EXTRACTION">Floor Stack & Vertical Extraction</option>
              <option value="HEIGHT_ESTIMATION">Building Height Estimation</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Registered Model
            </label>
            <select
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-purple-400"
            >
              <option value="building-segmentation-v1">building-segmentation-v1 (Development Baseline)</option>
              <option value="floor-extraction-v1">floor-extraction-v1 (Neural Model - Unconfigured)</option>
            </select>
          </div>

          {/* Section 77 Warning Banner for Unconfigured Model */}
          {isFloorModel && (
            <div className="p-3 bg-amber-950/40 border border-amber-500/40 rounded-xl flex items-start gap-2.5 text-xs text-amber-200">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block text-amber-300">AI Model Unavailable</span>
                No trained neural weights are configured for floor extraction. Job will stop safely at{' '}
                <code className="bg-amber-900/50 px-1 py-0.5 rounded font-mono text-[11px]">
                  MODEL_NOT_CONFIGURED
                </code>{' '}
                to prevent fabricating fake cadastral records.
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Target Identifier (Building UUID / Reference)
            </label>
            <input
              type="text"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              placeholder="e.g. b8f5d027-e431-419b-a7e6-e9185a73229b"
              required
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white font-mono placeholder:text-slate-500 focus:outline-none focus:border-purple-400"
            />
          </div>

          <div className="pt-2 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium text-xs transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl font-semibold text-xs shadow-lg shadow-purple-600/20 transition-all"
            >
              <Play className="w-3.5 h-3.5" />
              {isSubmitting ? 'Dispatching...' : 'Dispatch AI Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
