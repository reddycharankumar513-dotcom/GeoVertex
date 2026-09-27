import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Upload,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  ExternalLink,
  RefreshCw,
  Eye,
  ShieldCheck,
  Building,
  MapPin,
  TrendingUp,
} from 'lucide-react';
import {
  DocumentMetrics,
  DocumentStatus,
  DocumentType,
  PropertyDocument,
} from '../../types/document';
import { documentsApi } from '../../api/documents';
import { DocumentUploadModal } from '../../features/document/DocumentUploadModal';

export const DocumentListPage: React.FC = () => {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<PropertyDocument[]>([]);
  const [metrics, setMetrics] = useState<DocumentMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [requiresReviewOnly, setRequiresReviewOnly] = useState(false);

  // Modal
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const [docsData, metricsData] = await Promise.all([
        documentsApi.listDocuments({
          status: statusFilter ? (statusFilter as DocumentStatus) : undefined,
          document_type: typeFilter ? (typeFilter as DocumentType) : undefined,
          requires_review: requiresReviewOnly ? true : undefined,
          limit: 100,
        }),
        documentsApi.getMetrics().catch(() => null),
      ]);
      setDocuments(docsData);
      if (metricsData) setMetrics(metricsData);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch property documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [statusFilter, typeFilter, requiresReviewOnly]);

  const filteredDocs = documents.filter((doc) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      doc.title.toLowerCase().includes(q) ||
      (doc.document_number && doc.document_number.toLowerCase().includes(q)) ||
      (doc.parcel_id && doc.parcel_id.toLowerCase().includes(q))
    );
  });

  const getStatusBadge = (status: DocumentStatus) => {
    switch (status) {
      case 'VERIFIED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> Verified
          </span>
        );
      case 'UNDER_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Eye className="w-3 h-3" /> Under Review
          </span>
        );
      case 'REQUIRES_CORRECTION':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3 h-3" /> Needs Correction
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
            <XCircle className="w-3 h-3" /> Rejected
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">
            <RefreshCw className="w-3 h-3 animate-spin" /> Processing
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            <Clock className="w-3 h-3" /> {status}
          </span>
        );
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="w-7 h-7 text-indigo-400" />
            <h1 className="text-2xl font-bold tracking-tight">Property Document Intelligence</h1>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Deterministic OCR, structured field extraction with provenance, and Phase 7 cadastral consistency verification.
          </p>
        </div>

        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-indigo-600/20"
        >
          <Upload className="w-4 h-4" />
          Upload Document
        </button>
      </div>

      {/* Governance Notice */}
      <div className="flex items-start gap-3 p-4 bg-slate-900 border border-amber-500/30 rounded-xl text-slate-300">
        <ShieldCheck className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed">
          <span className="font-semibold text-amber-300 mr-1">Mandatory Human Review Governance:</span>
          AI Document Intelligence processes unstructured title deeds, survey plans, and permits to generate structured candidate data and cross-reference cadastral boundaries. AI never alters property ownership or issues legal verdicts autonomously. All verifications require review by authorized cadastral officers.
        </div>
      </div>

      {/* Metrics Banner */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
            <span className="text-slate-500 text-xs font-medium block">Total Documents</span>
            <span className="text-xl font-bold text-white mt-1 block">{metrics.total_documents}</span>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
            <span className="text-slate-500 text-xs font-medium block">Verified</span>
            <span className="text-xl font-bold text-emerald-400 mt-1 block">{metrics.verified_documents}</span>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
            <span className="text-slate-500 text-xs font-medium block">Under Review</span>
            <span className="text-xl font-bold text-indigo-400 mt-1 block">{metrics.under_review}</span>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
            <span className="text-slate-500 text-xs font-medium block">Corrections Needed</span>
            <span className="text-xl font-bold text-amber-400 mt-1 block">{metrics.requires_correction}</span>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
            <span className="text-slate-500 text-xs font-medium block">OCR Success</span>
            <span className="text-xl font-bold text-blue-400 mt-1 block">
              {Math.round(metrics.ocr_success_rate * 100)}%
            </span>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-3.5 rounded-xl">
            <span className="text-slate-500 text-xs font-medium block">Extraction Conf.</span>
            <span className="text-xl font-bold text-cyan-400 mt-1 block">
              {Math.round(metrics.avg_extraction_confidence * 100)}%
            </span>
          </div>
        </div>
      )}

      {/* Filters & Search */}
      <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by document title, document number, or parcel ID..."
            className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Document Types</option>
            <option value="DEED">Deed</option>
            <option value="TITLE_CERTIFICATE">Title Certificate</option>
            <option value="SURVEY_PLAN">Survey Plan</option>
            <option value="ENCUMBRANCE_CERTIFICATE">Encumbrance</option>
            <option value="TAX_RECEIPT">Tax Receipt</option>
            <option value="BUILDING_PERMIT">Building Permit</option>
            <option value="COMPLETION_CERTIFICATE">Completion Cert</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="UPLOADED">Uploaded</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="VERIFIED">Verified</option>
            <option value="REQUIRES_CORRECTION">Requires Correction</option>
            <option value="REJECTED">Rejected</option>
          </select>

          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300 whitespace-nowrap pl-2">
            <input
              type="checkbox"
              checked={requiresReviewOnly}
              onChange={(e) => setRequiresReviewOnly(e.target.checked)}
              className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
            />
            Needs Review
          </label>

          <button
            onClick={fetchDocuments}
            className="p-2 text-slate-400 hover:text-slate-200 bg-slate-950 border border-slate-800 rounded-lg transition"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
            <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
            <span>Loading property documents...</span>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-400">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-80" />
            <span>{error}</span>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="p-12 text-center text-slate-500 flex flex-col items-center gap-2">
            <FileText className="w-12 h-12 text-slate-600 stroke-[1.5]" />
            <p className="text-base font-medium text-slate-400 mt-2">No documents found</p>
            <p className="text-xs text-slate-500">
              Upload a property deed, survey plan, or title certificate to initiate AI extraction.
            </p>
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="mt-3 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition"
            >
              Upload Document
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/70 border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Document Title & Number</th>
                  <th className="py-3.5 px-4 font-semibold">Type</th>
                  <th className="py-3.5 px-4 font-semibold">Status</th>
                  <th className="py-3.5 px-4 font-semibold">Confidence</th>
                  <th className="py-3.5 px-4 font-semibold">Cadastral Links</th>
                  <th className="py-3.5 px-4 font-semibold">Date</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {filteredDocs.map((doc) => {
                  const linksCount = doc.entity_links?.length || 0;
                  const confidencePct = Math.round((doc.confidence_score || 0) * 100);

                  return (
                    <tr
                      key={doc.id}
                      onClick={() => navigate(`/documents/${doc.id}`)}
                      className="hover:bg-slate-800/40 cursor-pointer transition"
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-100 flex items-center gap-2">
                          <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                          <span className="truncate max-w-xs">{doc.title}</span>
                        </div>
                        {doc.document_number && (
                          <div className="text-xs text-slate-400 font-mono mt-0.5">
                            Doc #{doc.document_number}
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-xs">
                        <span className="px-2 py-0.5 bg-slate-800 border border-slate-700/60 rounded text-slate-300">
                          {doc.document_type}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">{getStatusBadge(doc.status)}</td>

                      <td className="py-3.5 px-4">
                        {doc.confidence_score !== null && doc.confidence_score !== undefined ? (
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  confidencePct >= 80
                                    ? 'bg-emerald-500'
                                    : confidencePct >= 60
                                    ? 'bg-amber-500'
                                    : 'bg-red-500'
                                }`}
                                style={{ width: `${confidencePct}%` }}
                              />
                            </div>
                            <span className="text-xs font-mono text-slate-400">{confidencePct}%</span>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-500 font-mono">--</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-xs">
                        {linksCount > 0 ? (
                          <span className="inline-flex items-center gap-1 text-indigo-300 font-medium bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                            <MapPin className="w-3 h-3" /> {linksCount} Linked
                          </span>
                        ) : (
                          <span className="text-slate-500">Unlinked</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-xs text-slate-400">
                        {doc.document_date || new Date(doc.created_at).toLocaleDateString()}
                      </td>

                      <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => navigate(`/documents/${doc.id}`)}
                          className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded text-xs font-medium transition inline-flex items-center gap-1"
                        >
                          Workspace <ExternalLink className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={(newDoc) => {
          fetchDocuments();
          navigate(`/documents/${newDoc.id}`);
        }}
      />
    </div>
  );
};
