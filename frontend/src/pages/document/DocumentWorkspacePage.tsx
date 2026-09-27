import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  FileText,
  ArrowLeft,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Link2,
  ShieldAlert,
  Edit3,
  Calendar,
  Layers,
  MapPin,
  Check,
  X,
  FileCheck,
  Send,
  Eye,
} from 'lucide-react';
import {
  DocumentExtractedField,
  DocumentStatus,
  FieldReviewPayload,
  PropertyDocument,
  DocumentEntityLink,
  TargetEntityType,
} from '../../types/document';
import { documentsApi } from '../../api/documents';
import { DocumentViewer } from '../../features/document/DocumentViewer';
import { FieldCorrectionModal } from '../../features/document/FieldCorrectionModal';
import { DocumentLinkModal } from '../../features/document/DocumentLinkModal';

export const DocumentWorkspacePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [document, setDocument] = useState<PropertyDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Field Review Modal State
  const [selectedField, setSelectedField] = useState<DocumentExtractedField | null>(null);
  const [isFieldModalOpen, setIsFieldModalOpen] = useState(false);

  // Link Modal State
  const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);

  // Verification Decision State
  const [verificationNotes, setVerificationNotes] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchDocument = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await documentsApi.getDocument(id);
      setDocument(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocument();
  }, [id]);

  const handleTriggerProcessing = async () => {
    if (!id) return;
    try {
      setProcessing(true);
      setError(null);
      await documentsApi.triggerProcessing(id);
      // Reload document details after processing
      const updated = await documentsApi.getDocument(id);
      setDocument(updated);
      setActionSuccess('AI Document intelligence pipeline completed successfully.');
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setError(err?.message || 'Processing failed');
    } finally {
      setProcessing(false);
    }
  };

  const handleFieldSubmit = async (fieldId: string, payload: FieldReviewPayload) => {
    if (!id) return;
    await documentsApi.reviewField(id, fieldId, payload);
    // Refresh document state
    const updated = await documentsApi.getDocument(id);
    setDocument(updated);
  };

  const handleConfirmLink = async (linkId: string) => {
    if (!id) return;
    try {
      const updated = await documentsApi.confirmEntityLink(id, linkId);
      setDocument(updated);
    } catch (err: any) {
      setError(err?.message || 'Failed to confirm entity link');
    }
  };

  const handleRejectLink = async (linkId: string) => {
    if (!id) return;
    try {
      const updated = await documentsApi.rejectEntityLink(id, linkId);
      setDocument(updated);
    } catch (err: any) {
      setError(err?.message || 'Failed to reject entity link');
    }
  };

  const handleCreateLink = async (payload: any) => {
    if (!id) return;
    const updated = await documentsApi.createEntityLink(id, payload);
    setDocument(updated);
  };

  const handleVerificationAction = async (action: 'VERIFY' | 'REJECT' | 'REQUEST_CORRECTION') => {
    if (!id) return;
    try {
      setIsVerifying(true);
      setError(null);
      const updated = await documentsApi.verifyDocument(id, {
        action,
        review_notes: verificationNotes.trim() || undefined,
        rejection_reason: action === 'REJECT' ? verificationNotes.trim() || 'Cadastral verification rejected' : undefined,
      });
      setDocument(updated);
      setActionSuccess(`Document successfully marked as ${action}`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setError(err?.message || `Failed to perform verification action: ${action}`);
    } finally {
      setIsVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[70vh] text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500 mr-3" />
        <span>Loading document intelligence workspace...</span>
      </div>
    );
  }

  if (error && !document) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Error Loading Document</h2>
        <p className="text-slate-400 text-sm">{error}</p>
        <button
          onClick={() => navigate('/documents')}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm inline-flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Documents
        </button>
      </div>
    );
  }

  if (!document) return null;

  const fields = document.extracted_fields || [];
  const entityLinks = document.entity_links || [];

  // Group fields by category
  const categorizedFields: Record<string, DocumentExtractedField[]> = {};
  fields.forEach((f) => {
    const cat = f.field_category || 'GENERAL';
    if (!categorizedFields[cat]) categorizedFields[cat] = [];
    categorizedFields[cat].push(f);
  });

  // Collect all validation issues across links (Phase 7 integration)
  const validationIssues: any[] = [];
  entityLinks.forEach((link) => {
    if (link.validation_issues && Array.isArray(link.validation_issues)) {
      link.validation_issues.forEach((issue) => {
        validationIssues.push({ ...issue, entity_type: link.entity_type, entity_id: link.entity_id });
      });
    }
  });

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] p-4 overflow-hidden text-slate-100">
      {/* Top Navigation Bar */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/documents')}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition"
            title="Back to Documents"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white flex items-center gap-2">
                {document.title}
              </h1>
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                {document.document_type}
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                  document.status === 'VERIFIED'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : document.status === 'UNDER_REVIEW'
                    ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                    : document.status === 'REQUIRES_CORRECTION'
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : document.status === 'REJECTED'
                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {document.status}
              </span>
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-3 mt-0.5 font-mono">
              {document.document_number && <span>Doc #: {document.document_number}</span>}
              <span>Jurisdiction: {document.jurisdiction_id.substring(0, 8)}...</span>
              {document.ocr_engine_used && <span>Engine: {document.ocr_engine_used}</span>}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {actionSuccess && (
            <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> {actionSuccess}
            </span>
          )}

          <button
            onClick={handleTriggerProcessing}
            disabled={processing}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 rounded-lg text-xs font-medium transition border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${processing ? 'animate-spin text-indigo-400' : ''}`} />
            {processing ? 'Processing AI...' : 'Re-run Extraction'}
          </button>
        </div>
      </div>

      {/* Main Split Screen Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 mt-3 overflow-hidden">
        {/* Left Side: Document Viewer (7 cols) */}
        <div className="lg:col-span-7 h-full overflow-hidden">
          <DocumentViewer
            document={document}
            selectedField={selectedField}
            onSelectField={(f) => {
              setSelectedField(f);
              setIsFieldModalOpen(true);
            }}
          />
        </div>

        {/* Right Side: Extraction, Cadastral Matcher, Validation, Human Review (5 cols) */}
        <div className="lg:col-span-5 h-full overflow-y-auto space-y-4 pr-1">
          {/* Governance Notice */}
          <div className="p-3 bg-slate-900 border border-amber-500/30 rounded-xl text-xs text-slate-300 flex items-start gap-2.5">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-amber-300">Mandatory Cadastral Governance:</span> AI
              provides deterministic field extraction & candidate matching with confidence scoring.
              Final land rights determination and verification must be confirmed by authorized officers.
            </div>
          </div>

          {/* Validation Discrepancies (Phase 7 Integration) */}
          {validationIssues.length > 0 && (
            <div className="p-3.5 bg-red-950/30 border border-red-800/60 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-red-400 flex items-center gap-1.5 uppercase tracking-wider">
                  <AlertTriangle className="w-4 h-4 text-red-400" /> Cadastral Validation Discrepancies (Phase 7)
                </span>
                <span className="text-[11px] px-2 py-0.5 bg-red-500/20 text-red-300 rounded font-bold">
                  {validationIssues.length} Found
                </span>
              </div>
              <div className="space-y-1.5 mt-2">
                {validationIssues.map((issue, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-slate-950 border border-red-900/40 rounded-lg text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-red-300">{issue.rule_code}</span>
                      <span
                        className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                          issue.severity === 'CRITICAL'
                            ? 'bg-red-500/30 text-red-200'
                            : 'bg-amber-500/30 text-amber-200'
                        }`}
                      >
                        {issue.severity}
                      </span>
                    </div>
                    <p className="text-slate-300">{issue.message}</p>
                    {issue.expected_value && (
                      <div className="text-[11px] text-slate-400 font-mono">
                        Registry: {issue.expected_value} | Doc: {issue.actual_value}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cadastral Entity Links */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Link2 className="w-4 h-4 text-indigo-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Cadastral Entity Links
                </h3>
              </div>
              <button
                onClick={() => setIsLinkModalOpen(true)}
                className="px-2.5 py-1 bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 rounded text-xs font-medium transition"
              >
                + Link Entity
              </button>
            </div>

            {entityLinks.length === 0 ? (
              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg text-xs text-slate-500 text-center">
                No cadastral entities linked. Link a Parcel, Property, Building, or Unit to verify consistency.
              </div>
            ) : (
              <div className="space-y-2">
                {entityLinks.map((link) => (
                  <div
                    key={link.id}
                    className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2 font-mono">
                        <span className="font-bold text-slate-200">{link.entity_type}:</span>
                        <span className="text-slate-400">{link.entity_id}</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                            link.status === 'CONFIRMED'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : link.status === 'REJECTED'
                              ? 'bg-red-500/20 text-red-300'
                              : 'bg-amber-500/20 text-amber-300'
                          }`}
                        >
                          {link.status}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-2">
                        <span>Rel: {link.relationship_type}</span>
                        <span>•</span>
                        <span>Match: {link.match_method} ({Math.round((link.match_confidence || 1) * 100)}%)</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {link.status !== 'CONFIRMED' && (
                        <button
                          onClick={() => handleConfirmLink(link.id)}
                          className="p-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 rounded border border-emerald-500/30 transition"
                          title="Confirm Cadastral Link"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {link.status !== 'REJECTED' && (
                        <button
                          onClick={() => handleRejectLink(link.id)}
                          className="p-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded border border-red-500/30 transition"
                          title="Reject Link"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Structured Fields with Provenance & Review */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Extracted Structured Fields ({fields.length})
                </h3>
              </div>
              <span className="text-[11px] text-slate-400">Click field to review / correct</span>
            </div>

            {fields.length === 0 ? (
              <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg text-xs text-slate-500 text-center">
                No structured fields extracted yet. Click "Re-run Extraction" to execute field extractors.
              </div>
            ) : (
              Object.entries(categorizedFields).map(([category, catFields]) => (
                <div key={category} className="space-y-2">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    {category}
                  </div>
                  <div className="space-y-2">
                    {catFields.map((f) => {
                      const isPending = f.review_status === 'PENDING';
                      const isCorrected = f.review_status === 'CORRECTED';
                      const isAccepted = f.review_status === 'ACCEPTED';
                      const isRejected = f.review_status === 'REJECTED';

                      return (
                        <div
                          key={f.id}
                          onClick={() => {
                            setSelectedField(f);
                            setIsFieldModalOpen(true);
                          }}
                          className={`p-3 bg-slate-950 border rounded-lg cursor-pointer transition hover:border-indigo-500/60 ${
                            selectedField?.id === f.id
                              ? 'border-indigo-500 bg-indigo-950/20'
                              : 'border-slate-800'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-xs font-bold text-slate-200">
                              {f.field_name}
                            </span>
                            <div className="flex items-center gap-1.5">
                              {/* Confidence badge */}
                              <span
                                className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${
                                  f.confidence_level === 'HIGH'
                                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                                    : f.confidence_level === 'MEDIUM'
                                    ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                                    : 'bg-red-500/20 text-red-400 border-red-500/30'
                                }`}
                              >
                                {Math.round((f.confidence || 0) * 100)}% {f.confidence_level}
                              </span>

                              {/* Review status badge */}
                              <span
                                className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${
                                  isAccepted
                                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                    : isCorrected
                                    ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
                                    : isRejected
                                    ? 'bg-red-500/10 text-red-400 border-red-500/30'
                                    : 'bg-slate-800 text-slate-400 border-slate-700'
                                }`}
                              >
                                {f.review_status}
                              </span>
                            </div>
                          </div>

                          {/* Values */}
                          <div className="mt-1.5 text-xs">
                            <div className="flex items-baseline gap-2">
                              <span className="text-slate-500 text-[11px]">Value:</span>
                              <span
                                className={`font-mono ${
                                  isCorrected
                                    ? 'text-indigo-300 font-semibold'
                                    : 'text-slate-100 font-medium'
                                }`}
                              >
                                {f.reviewed_value || f.normalized_value || f.raw_value}
                              </span>
                            </div>

                            {f.normalized_value && f.normalized_value !== f.raw_value && !isCorrected && (
                              <div className="flex items-baseline gap-2 mt-0.5 text-[11px] text-slate-500 font-mono">
                                <span>Raw: {f.raw_value}</span>
                              </div>
                            )}

                            {f.evidence_text && (
                              <div className="text-[11px] text-slate-500 italic mt-1 truncate">
                                Context: "{f.evidence_text}"
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Cadastral Officer Verification & Action Center */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-emerald-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Cadastral Officer Verification
              </h3>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Verification Notes / Officer Audit Rationale
              </label>
              <textarea
                value={verificationNotes}
                onChange={(e) => setVerificationNotes(e.target.value)}
                rows={2}
                placeholder="Enter justification for verification, correction requirements, or rejection..."
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div className="grid grid-cols-3 gap-2 pt-1">
              <button
                onClick={() => handleVerificationAction('VERIFY')}
                disabled={isVerifying}
                className="flex items-center justify-center gap-1.5 py-2 px-3 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition shadow-md shadow-emerald-600/20"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Verify
              </button>
              <button
                onClick={() => handleVerificationAction('REQUEST_CORRECTION')}
                disabled={isVerifying}
                className="flex items-center justify-center gap-1.5 py-2 px-3 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition shadow-md shadow-amber-600/20"
              >
                <AlertTriangle className="w-3.5 h-3.5" /> Correction
              </button>
              <button
                onClick={() => handleVerificationAction('REJECT')}
                disabled={isVerifying}
                className="flex items-center justify-center gap-1.5 py-2 px-3 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition shadow-md shadow-red-600/20"
              >
                <XCircle className="w-3.5 h-3.5" /> Reject
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Field Review Modal */}
      <FieldCorrectionModal
        field={selectedField}
        isOpen={isFieldModalOpen}
        onClose={() => {
          setIsFieldModalOpen(false);
          setSelectedField(null);
        }}
        onSubmit={handleFieldSubmit}
      />

      {/* Cadastral Entity Link Modal */}
      <DocumentLinkModal
        documentId={document.id}
        isOpen={isLinkModalOpen}
        onClose={() => setIsLinkModalOpen(false)}
        onSubmit={handleCreateLink}
        prefilledEntityId={document.parcel_id || ''}
      />
    </div>
  );
};
