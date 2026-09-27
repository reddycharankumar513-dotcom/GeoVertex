import React, { useState, useRef } from 'react';
import { SurveyEvidence } from '../../types';
import { surveyApi } from '../../api/surveys';
import {
  Camera,
  Upload,
  Image as ImageIcon,
  MapPin,
  ShieldCheck,
  Trash2,
  Maximize2,
  X,
  FileCheck,
  AlertCircle,
  File,
} from 'lucide-react';

interface EvidenceGalleryProps {
  sessionId: string;
  targetType: string;
  targetId: string;
  evidence: SurveyEvidence[];
  currentLocation: {
    latitude: number;
    longitude: number;
    accuracy: number;
  } | null;
  onUploadEvidence: (
    file: File,
    description: string,
    evidenceType: string,
    coords?: { lat: number; lng: number; acc: number }
  ) => Promise<void>;
  onDeleteEvidence?: (id: string) => Promise<void>;
  disabled?: boolean;
}

const EVIDENCE_TYPES = [
  { value: 'BUILDING_FACADE', label: 'Building Facade / Elevation' },
  { value: 'BOUNDARY_MARKER', label: 'Boundary Marker / Peg' },
  { value: 'ACCESS_POINT', label: 'Access Point / Entrance' },
  { value: 'FLOOR_LAYOUT', label: 'Floor Layout / Interior' },
  { value: 'ROOF_STRUCTURE', label: 'Roof / Parapet Structure' },
  { value: 'SURROUNDINGS', label: 'Surroundings / Street Context' },
  { value: 'OTHER', label: 'Other Documentary Evidence' },
];

export const computeFileSha256 = async (file: File): Promise<string> => {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
};

export const EvidenceGallery: React.FC<EvidenceGalleryProps> = ({
  sessionId,
  targetType,
  targetId,
  evidence,
  currentLocation,
  onUploadEvidence,
  onDeleteEvidence,
  disabled = false,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [evidenceType, setEvidenceType] = useState('BUILDING_FACADE');
  const [description, setDescription] = useState('');
  const [attachGps, setAttachGps] = useState(true);
  const [calculatedHash, setCalculatedHash] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [zoomedEvidence, setZoomedEvidence] = useState<SurveyEvidence | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelection = async (file: File) => {
    setError(null);
    if (!file) return;

    // Check size (20MB limit)
    if (file.size > 20 * 1024 * 1024) {
      setError('File size exceeds the 20MB limit');
      return;
    }

    setSelectedFile(file);
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }

    try {
      const hash = await computeFileSha256(file);
      setCalculatedHash(hash);
    } catch {
      setCalculatedHash(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select or capture a photo');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const coords =
        attachGps && currentLocation
          ? {
              lat: currentLocation.latitude,
              lng: currentLocation.longitude,
              acc: currentLocation.accuracy,
            }
          : undefined;

      await onUploadEvidence(selectedFile, description, evidenceType, coords);

      // Clean up
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
      setSelectedFile(null);
      setPreviewUrl(null);
      setDescription('');
      setCalculatedHash(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to upload photo evidence');
    } finally {
      setIsUploading(false);
    }
  };

  const cancelSelection = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(null);
    setPreviewUrl(null);
    setCalculatedHash(null);
    setDescription('');
  };

  return (
    <div className="space-y-6">
      {/* Upload / Capture Section */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center space-x-2">
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Capture Photographic Evidence</h3>
              <p className="text-xs text-slate-400">
                Cryptographically hashed (SHA-256) field photography
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-mono">
              Max 20MB
            </span>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-start space-x-2 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* File chooser triggers */}
        {!selectedFile ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="file"
              ref={cameraInputRef}
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.[0]) handleFileSelection(e.target.files[0]);
              }}
            />
            <button
              type="button"
              disabled={disabled}
              onClick={() => cameraInputRef.current?.click()}
              className="flex items-center justify-center space-x-3 p-4 rounded-xl border border-dashed border-sky-500/40 bg-sky-500/5 hover:bg-sky-500/10 text-sky-300 font-medium text-xs transition-all cursor-pointer disabled:opacity-50"
            >
              <Camera className="w-5 h-5 text-sky-400" />
              <span>Use Device Camera</span>
            </button>

            <input
              type="file"
              ref={fileInputRef}
              accept="image/jpeg,image/png,image/webp,application/pdf"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.[0]) handleFileSelection(e.target.files[0]);
              }}
            />
            <button
              type="button"
              disabled={disabled}
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center justify-center space-x-3 p-4 rounded-xl border border-dashed border-slate-700 bg-slate-950/40 hover:bg-slate-800/40 text-slate-300 font-medium text-xs transition-all cursor-pointer disabled:opacity-50"
            >
              <Upload className="w-5 h-5 text-slate-400" />
              <span>Upload from Gallery / Files</span>
            </button>
          </div>
        ) : (
          /* Preview and Metadata Form */
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="flex flex-col md:flex-row gap-4">
              {/* Preview image */}
              <div className="w-full md:w-1/3 flex flex-col items-center justify-center bg-slate-950 rounded-lg border border-slate-800 p-2 overflow-hidden max-h-56">
                {previewUrl ? (
                  <img
                    src={previewUrl}
                    alt="Evidence Preview"
                    className="max-h-52 w-auto object-contain rounded"
                  />
                ) : (
                  <div className="py-12 flex flex-col items-center text-slate-400">
                    <File className="w-12 h-12 mb-2 text-slate-500" />
                    <span className="text-xs">{selectedFile.name}</span>
                  </div>
                )}
              </div>

              {/* Form fields */}
              <div className="w-full md:w-2/3 space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Evidence Category <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={evidenceType}
                    onChange={(e) => setEvidenceType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                  >
                    {EVIDENCE_TYPES.map((et) => (
                      <option key={et.value} value={et.value}>
                        {et.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Caption / Description
                  </label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g. North-facing boundary peg, adjacent to road"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>

                {calculatedHash && (
                  <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-400 font-mono flex items-center space-x-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="truncate">SHA-256: {calculatedHash}</span>
                  </div>
                )}

                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={attachGps}
                      onChange={(e) => setAttachGps(e.target.checked)}
                      disabled={!currentLocation}
                      className="w-4 h-4 rounded border-slate-700 bg-slate-950 text-emerald-500 focus:ring-emerald-500"
                    />
                    <span>Geotag photo with current GPS</span>
                  </label>
                  {currentLocation && attachGps && (
                    <span className="text-[11px] text-slate-400 font-mono">
                      ±{Math.round(currentLocation.accuracy)}m
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={cancelSelection}
                disabled={isUploading}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isUploading}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-2 shadow-lg shadow-emerald-600/20 cursor-pointer disabled:opacity-50"
              >
                <Upload className="w-4 h-4" />
                <span>{isUploading ? 'Uploading...' : 'Save Evidence'}</span>
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Uploaded Evidence Gallery Grid */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center space-x-2">
            <ImageIcon className="w-4 h-4 text-emerald-400" />
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
              Survey Photo Records ({evidence.length})
            </h4>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            Session: {sessionId.slice(0, 8)}
          </span>
        </div>

        {evidence.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            No photographic evidence captured yet for this survey session.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {evidence.map((item) => {
              const fileUrl = surveyApi.getEvidenceFileUrl(item.id);
              return (
                <div
                  key={item.id}
                  className="group relative bg-slate-950 border border-slate-800 rounded-lg overflow-hidden flex flex-col hover:border-slate-700 transition-all"
                >
                  {/* Thumbnail */}
                  <div className="relative aspect-video bg-slate-900 overflow-hidden cursor-pointer" onClick={() => setZoomedEvidence(item)}>
                    <img
                      src={fileUrl}
                      alt={item.description || item.filename}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-between p-2">
                      <span className="text-[10px] text-white flex items-center space-x-1">
                        <Maximize2 className="w-3 h-3" />
                        <span>Zoom</span>
                      </span>
                    </div>
                  </div>

                  {/* Details */}
                  <div className="p-2.5 flex-1 flex flex-col justify-between text-[11px]">
                    <div>
                      <div className="font-semibold text-slate-200 truncate">
                        {item.evidence_type.replace('_', ' ')}
                      </div>
                      {item.description && (
                        <p className="text-slate-400 text-[10px] line-clamp-2 mt-0.5">
                          {item.description}
                        </p>
                      )}
                    </div>

                    <div className="pt-2 mt-2 border-t border-slate-800/80 space-y-1 text-[10px] text-slate-500 font-mono">
                      <div className="flex items-center justify-between">
                        <span>{(item.file_size / 1024).toFixed(0)} KB</span>
                        <span className="text-emerald-400 font-mono text-[9px] truncate max-w-[80px]">
                          {item.sha256_hash.slice(0, 10)}...
                        </span>
                      </div>
                      {item.latitude && item.longitude && (
                        <div className="flex items-center space-x-1 text-slate-400">
                          <MapPin className="w-3 h-3 text-sky-400" />
                          <span>
                            {item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Delete button */}
                  {!disabled && onDeleteEvidence && (
                    <button
                      type="button"
                      onClick={() => onDeleteEvidence(item.id)}
                      className="absolute top-1.5 right-1.5 p-1 bg-slate-900/80 hover:bg-rose-500 text-slate-400 hover:text-white rounded transition-colors shadow-md"
                      title="Delete evidence"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Lightbox Modal */}
      {zoomedEvidence && (
        <div
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4"
          onClick={() => setZoomedEvidence(null)}
        >
          <div
            className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  {zoomedEvidence.evidence_type.replace('_', ' ')}
                </h3>
                <p className="text-xs text-slate-400">{zoomedEvidence.filename}</p>
              </div>
              <button
                type="button"
                onClick={() => setZoomedEvidence(null)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 flex items-center justify-center bg-black/40 overflow-auto">
              <img
                src={surveyApi.getEvidenceFileUrl(zoomedEvidence.id)}
                alt={zoomedEvidence.description || zoomedEvidence.filename}
                className="max-h-[60vh] max-w-full object-contain rounded-lg shadow-lg"
              />
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-950/60 space-y-2 text-xs">
              {zoomedEvidence.description && (
                <p className="text-slate-200">
                  <span className="font-semibold text-slate-400">Description: </span>
                  {zoomedEvidence.description}
                </p>
              )}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-800/80">
                <div>
                  <span className="text-slate-500 block">Captured:</span>
                  {new Date(zoomedEvidence.captured_at).toLocaleString()}
                </div>
                <div>
                  <span className="text-slate-500 block">GPS Coords:</span>
                  {zoomedEvidence.latitude && zoomedEvidence.longitude
                    ? `${zoomedEvidence.latitude.toFixed(5)}, ${zoomedEvidence.longitude.toFixed(5)}`
                    : 'Not attached'}
                </div>
                <div>
                  <span className="text-slate-500 block">File Size:</span>
                  {(zoomedEvidence.file_size / 1024).toFixed(1)} KB
                </div>
                <div className="truncate">
                  <span className="text-slate-500 block">SHA-256 Hash:</span>
                  <span className="text-emerald-400" title={zoomedEvidence.sha256_hash}>
                    {zoomedEvidence.sha256_hash}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
