import React, { useState } from 'react';
import { Upload, X, AlertTriangle, FileText, CheckCircle2, ShieldAlert } from 'lucide-react';
import { DocumentType, PropertyDocument } from '../../types/document';
import { documentsApi } from '../../api/documents';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (document: PropertyDocument) => void;
  defaultJurisdictionId?: string;
  defaultParcelId?: string;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  defaultJurisdictionId = '',
  defaultParcelId = '',
}) => {
  if (!isOpen) return null;

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [documentType, setDocumentType] = useState<DocumentType>('DEED');
  const [documentNumber, setDocumentNumber] = useState('');
  const [jurisdictionId, setJurisdictionId] = useState(defaultJurisdictionId || '00000000-0000-0000-0000-000000000001');
  const [parcelId, setParcelId] = useState(defaultParcelId || '');
  const [propertyId, setPropertyId] = useState('');
  const [buildingId, setBuildingId] = useState('');
  const [unitId, setUnitId] = useState('');
  const [triggerProcessing, setTriggerProcessing] = useState(true);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      if (!title) {
        setTitle(selectedFile.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' '));
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a document file to upload');
      return;
    }
    if (!title.trim()) {
      setError('Document title is required');
      return;
    }
    if (!jurisdictionId.trim()) {
      setError('Jurisdiction ID is required');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setUploadProgress('Uploading and generating cryptographic SHA-256 hash...');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title.trim());
      formData.append('jurisdiction_id', jurisdictionId.trim());
      formData.append('document_type', documentType);
      if (documentNumber.trim()) formData.append('document_number', documentNumber.trim());
      if (parcelId.trim()) formData.append('parcel_id', parcelId.trim());
      if (propertyId.trim()) formData.append('property_id', propertyId.trim());
      if (buildingId.trim()) formData.append('building_id', buildingId.trim());
      if (unitId.trim()) formData.append('unit_id', unitId.trim());

      let doc = await documentsApi.uploadDocument(formData);

      if (triggerProcessing) {
        setUploadProgress('Executing AI Document Intelligence (OCR & Extraction)...');
        try {
          await documentsApi.triggerProcessing(doc.id);
          // Fetch updated document
          doc = await documentsApi.getDocument(doc.id);
        } catch (procErr: any) {
          console.warn('Processing job queued or backgrounded:', procErr);
        }
      }

      onSuccess(doc);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to upload document');
    } finally {
      setIsSubmitting(false);
      setUploadProgress(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl max-w-xl w-full overflow-hidden text-slate-100 my-8">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center gap-2">
            <Upload className="w-5 h-5 text-indigo-400" />
            <h3 className="font-semibold text-lg">Upload Property Document</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {uploadProgress && (
            <div className="flex items-center gap-2 p-3 bg-indigo-500/10 border border-indigo-500/30 rounded-lg text-indigo-300 text-sm animate-pulse">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{uploadProgress}</span>
            </div>
          )}

          {/* File Picker */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Select Document File <span className="text-red-400">*</span>
            </label>
            <div className="border-2 border-dashed border-slate-700 hover:border-indigo-500 rounded-xl p-4 text-center cursor-pointer transition bg-slate-950/40">
              <input
                type="file"
                id="doc-file-input"
                className="hidden"
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                onChange={handleFileChange}
              />
              <label htmlFor="doc-file-input" className="cursor-pointer flex flex-col items-center">
                <FileText className="w-8 h-8 text-indigo-400 mb-2" />
                {file ? (
                  <div className="text-sm font-medium text-indigo-300">
                    {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </div>
                ) : (
                  <>
                    <div className="text-sm font-medium text-slate-200">
                      Click to choose or drag & drop property document
                    </div>
                    <div className="text-xs text-slate-500 mt-1">PDF, TIFF, PNG, or JPEG (up to 50 MB)</div>
                  </>
                )}
              </label>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Document Title <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Registered Sale Deed Doc 4492"
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Document Type</label>
              <select
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value as DocumentType)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="DEED">Deed (Sale / Conveyance)</option>
                <option value="TITLE_CERTIFICATE">Title Certificate / Patta</option>
                <option value="SURVEY_PLAN">Survey Plan / Cadastral Map</option>
                <option value="ENCUMBRANCE_CERTIFICATE">Encumbrance Certificate</option>
                <option value="TAX_RECEIPT">Tax Receipt / Assessment</option>
                <option value="BUILDING_PERMIT">Building / Floor Permit</option>
                <option value="COMPLETION_CERTIFICATE">Completion / Occupancy Certificate</option>
                <option value="COURT_ORDER">Court Order / Legal Decree</option>
                <option value="PARTITION_DEED">Partition Deed</option>
                <option value="GIFT_DEED">Gift Deed</option>
                <option value="LEASE_AGREEMENT">Lease Agreement</option>
                <option value="OTHER">Other Official Record</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Document Number</label>
              <input
                type="text"
                value={documentNumber}
                onChange={(e) => setDocumentNumber(e.target.value)}
                placeholder="e.g. DOC-2026/089"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Jurisdiction ID <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={jurisdictionId}
                onChange={(e) => setJurisdictionId(e.target.value)}
                placeholder="UUID of administrative jurisdiction"
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono text-xs"
              />
            </div>
          </div>

          {/* Cadastral Target Entity Linking (Optional) */}
          <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-3">
            <span className="text-xs font-semibold text-slate-300 block">
              Cadastral Entity Associations (Optional)
            </span>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-0.5">Parcel ID</label>
                <input
                  type="text"
                  value={parcelId}
                  onChange={(e) => setParcelId(e.target.value)}
                  placeholder="Parcel UUID"
                  className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded text-slate-200 font-mono text-xs focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-0.5">Property ID</label>
                <input
                  type="text"
                  value={propertyId}
                  onChange={(e) => setPropertyId(e.target.value)}
                  placeholder="Property UUID"
                  className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded text-slate-200 font-mono text-xs focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-0.5">Building ID</label>
                <input
                  type="text"
                  value={buildingId}
                  onChange={(e) => setBuildingId(e.target.value)}
                  placeholder="Building UUID"
                  className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded text-slate-200 font-mono text-xs focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-0.5">Unit ID</label>
                <input
                  type="text"
                  value={unitId}
                  onChange={(e) => setUnitId(e.target.value)}
                  placeholder="Unit UUID"
                  className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded text-slate-200 font-mono text-xs focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="triggerProcessing"
              checked={triggerProcessing}
              onChange={(e) => setTriggerProcessing(e.target.checked)}
              className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="triggerProcessing" className="text-xs text-slate-300">
              Immediately execute OCR, field extraction, candidate matching, and Phase 7 validation
            </label>
          </div>

          {/* Governance Notice */}
          <div className="flex items-start gap-2.5 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-300/90 leading-relaxed">
            <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
            <div>
              <span className="font-semibold block text-amber-300">Mandatory Human-in-the-Loop Governance:</span>
              AI Document Intelligence performs deterministic OCR & extraction assistance. AI must never
              independently determine legal ownership or alter land rights. Cadastral officer review and
              verification remains mandatory.
            </div>
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
              disabled={isSubmitting || !file}
              className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-indigo-600/20 flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload & Process
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
