import React, { useState } from 'react';
import {
  FileText,
  Image as ImageIcon,
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
  Download,
  Copy,
  Check,
  Search,
  Hash,
} from 'lucide-react';
import { PropertyDocument, DocumentPage, DocumentExtractedField } from '../../types/document';
import { documentsApi } from '../../api/documents';

interface DocumentViewerProps {
  document: PropertyDocument;
  selectedField?: DocumentExtractedField | null;
  onSelectField?: (field: DocumentExtractedField) => void;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  document,
  selectedField,
  onSelectField,
}) => {
  const [activeTab, setActiveTab] = useState<'visual' | 'text'>('visual');
  const [currentPageIndex, setCurrentPageIndex] = useState<number>(0);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [copiedText, setCopiedText] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const pages = document.pages || [];
  const activePage: DocumentPage | undefined = pages[currentPageIndex];
  const activeVersion = document.versions?.[0];
  const totalPages = pages.length > 0 ? pages.length : (activeVersion?.total_pages || 1);

  // Get OCR result for active page if available
  const activeOcrResult = activePage?.ocr_results?.[0];
  const pageText = activeOcrResult?.extracted_text || '';

  const handleNextPage = () => {
    if (currentPageIndex < totalPages - 1) {
      setCurrentPageIndex(currentPageIndex + 1);
    }
  };

  const handlePrevPage = () => {
    if (currentPageIndex > 0) {
      setCurrentPageIndex(currentPageIndex - 1);
    }
  };

  const handleCopyText = () => {
    if (!pageText) return;
    navigator.clipboard.writeText(pageText);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  // Filter fields on the current page to display overlays
  const currentPageNumber = currentPageIndex + 1;
  const pageFields = (document.extracted_fields || []).filter(
    (f) => f.page_number === currentPageNumber || !f.page_number
  );

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      {/* Top Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950/80 border-b border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          {/* Tab selector */}
          <div className="flex bg-slate-800/80 p-0.5 rounded-lg border border-slate-700/50">
            <button
              onClick={() => setActiveTab('visual')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition ${
                activeTab === 'visual'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <ImageIcon className="w-3.5 h-3.5" />
              Document Preview
            </button>
            <button
              onClick={() => setActiveTab('text')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition ${
                activeTab === 'text'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              OCR Text
            </button>
          </div>

          {/* SHA-256 hash badge */}
          {activeVersion?.file_hash_sha256 && (
            <div
              className="hidden lg:flex items-center gap-1 px-2 py-1 bg-slate-800/50 rounded text-slate-400 font-mono text-[11px]"
              title={`SHA-256: ${activeVersion.file_hash_sha256}`}
            >
              <Hash className="w-3 h-3 text-slate-500" />
              <span>{activeVersion.file_hash_sha256.substring(0, 10)}...</span>
            </div>
          )}
        </div>

        {/* Page navigation & zoom */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-slate-800/60 rounded-lg px-1 py-0.5 border border-slate-700/50">
            <button
              onClick={handlePrevPage}
              disabled={currentPageIndex === 0}
              className="p-1 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-slate-300 px-2 font-mono">
              {currentPageIndex + 1} / {totalPages}
            </span>
            <button
              onClick={handleNextPage}
              disabled={currentPageIndex >= totalPages - 1}
              className="p-1 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {activeTab === 'visual' && (
            <div className="flex items-center gap-1 bg-slate-800/60 rounded-lg px-1 py-0.5 border border-slate-700/50">
              <button
                onClick={() => setZoomLevel(Math.max(50, zoomLevel - 25))}
                className="p-1 text-slate-400 hover:text-white"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-slate-400 font-mono text-[11px] px-1">{zoomLevel}%</span>
              <button
                onClick={() => setZoomLevel(Math.min(200, zoomLevel + 25))}
                className="p-1 text-slate-400 hover:text-white"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <a
            href={documentsApi.getDownloadUrl(document.id)}
            download
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition"
            title="Download Document"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Download</span>
          </a>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto bg-slate-950 p-4 flex items-center justify-center relative select-text">
        {activeTab === 'visual' ? (
          <div
            className="relative transition-transform duration-150 origin-top flex flex-col items-center shadow-2xl"
            style={{ transform: `scale(${zoomLevel / 100})` }}
          >
            {activePage?.image_path ? (
              <div className="relative border border-slate-700 rounded-lg overflow-hidden bg-white shadow-2xl">
                <img
                  src={documentsApi.getPageImageUrl(document.id, currentPageNumber)}
                  alt={`Page ${currentPageNumber}`}
                  className="max-h-[750px] w-auto object-contain block"
                  onError={(e) => {
                    // Fallback to text mode if image not available
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
                {/* Bounding box overlays */}
                {pageFields.map((field) => {
                  const bbox = field.bounding_box;
                  if (!bbox || bbox.x === undefined) return null;
                  const isSelected = selectedField?.id === field.id;
                  return (
                    <div
                      key={field.id}
                      onClick={() => onSelectField && onSelectField(field)}
                      style={{
                        position: 'absolute',
                        left: `${bbox.x}%`,
                        top: `${bbox.y}%`,
                        width: `${bbox.w}%`,
                        height: `${bbox.h}%`,
                      }}
                      className={`cursor-pointer transition-all border-2 rounded ${
                        isSelected
                          ? 'border-indigo-400 bg-indigo-500/30 ring-2 ring-indigo-400'
                          : 'border-amber-400/70 bg-amber-400/10 hover:bg-amber-400/25'
                      }`}
                      title={`${field.field_name}: ${field.raw_value}`}
                    />
                  );
                })}
              </div>
            ) : (
              <div className="w-[595px] min-h-[750px] bg-slate-900 border border-slate-800 rounded-lg p-8 shadow-2xl flex flex-col justify-between text-slate-300">
                <div>
                  <div className="border-b border-slate-800 pb-4 mb-4 flex items-center justify-between">
                    <div>
                      <span className="text-xs uppercase tracking-wider text-indigo-400 font-semibold">
                        Cadastral Legal Record
                      </span>
                      <h3 className="text-base font-bold text-white mt-1">{document.title}</h3>
                      <div className="text-xs text-slate-400 mt-0.5">
                        Type: {document.document_type} | Doc No: {document.document_number || 'N/A'}
                      </div>
                    </div>
                    <div className="text-right text-xs text-slate-500">
                      <div>Page {currentPageNumber} of {totalPages}</div>
                      <div>Hash: {activeVersion?.file_hash_sha256?.substring(0, 8)}...</div>
                    </div>
                  </div>

                  <div className="space-y-4 text-xs font-mono leading-relaxed bg-slate-950/70 p-4 rounded-lg border border-slate-800/80">
                    <div className="text-slate-400 uppercase text-[10px] tracking-wider mb-2 font-sans font-bold">
                      Extracted Page Text Preview:
                    </div>
                    {pageText ? (
                      <p className="whitespace-pre-wrap text-slate-200">
                        {pageText.length > 1200 ? `${pageText.substring(0, 1200)}...` : pageText}
                      </p>
                    ) : (
                      <p className="italic text-slate-500">
                        No OCR text available for page {currentPageNumber}. Run document processing to generate text extraction.
                      </p>
                    )}
                  </div>
                </div>

                {/* Footer of virtual document preview */}
                <div className="border-t border-slate-800/80 pt-3 flex items-center justify-between text-[11px] text-slate-500">
                  <span>Engine: {document.ocr_engine_used || 'pypdf'}</span>
                  <span>Confidence: {Math.round((document.confidence_score || 0) * 100)}%</span>
                  <span>Jurisdiction: {document.jurisdiction_id.substring(0, 8)}...</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="w-full h-full max-w-4xl flex flex-col bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
            {/* OCR Text Header */}
            <div className="flex items-center justify-between px-4 py-2 bg-slate-950 border-b border-slate-800 text-xs">
              <div className="flex items-center gap-3">
                <span className="text-slate-400">
                  Page {currentPageNumber} Character Count:{' '}
                  <span className="text-indigo-300 font-mono font-medium">
                    {pageText.length}
                  </span>
                </span>
                {activeOcrResult?.average_confidence && (
                  <span className="text-slate-400">
                    Confidence:{' '}
                    <span className="text-emerald-400 font-mono font-medium">
                      {Math.round(activeOcrResult.average_confidence * 100)}%
                    </span>
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2 top-1.5" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search in page..."
                    className="pl-7 pr-2 py-0.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
                <button
                  onClick={handleCopyText}
                  className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition text-xs"
                >
                  {copiedText ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Text</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* OCR Content Text */}
            <div className="flex-1 p-6 overflow-auto font-mono text-sm leading-relaxed text-slate-200 bg-slate-950/90 whitespace-pre-wrap select-text">
              {pageText ? (
                pageText
              ) : (
                <div className="text-center text-slate-500 py-12 font-sans">
                  No OCR text extracted yet. Trigger Document Processing from the right panel.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
