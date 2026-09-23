import React, { useState } from 'react';
import {
  X,
  Upload,
  Download,
  FileCode,
  CheckCircle,
  AlertTriangle,
  Copy,
  Check,
  Loader2,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { gisApi } from '../../api/gis';
import { Jurisdiction, GISImportSummary, GeoJSONFeatureCollection } from '../../types';

interface ImportExportModalProps {
  jurisdictions: Jurisdiction[];
  selectedJurisdictionId?: string;
  onClose: () => void;
  onImportCompleted: () => void;
}

export const ImportExportModal: React.FC<ImportExportModalProps> = ({
  jurisdictions,
  selectedJurisdictionId,
  onClose,
  onImportCompleted,
}) => {
  const [activeTab, setActiveTab] = useState<'import' | 'export'>('import');

  // Import states
  const [importJurisdictionId, setImportJurisdictionId] = useState(
    selectedJurisdictionId || (jurisdictions.length > 0 ? jurisdictions[0].id : '')
  );
  const [geoJsonInput, setGeoJsonInput] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [importSummary, setImportSummary] = useState<GISImportSummary | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // Export states
  const [exportJurisdictionId, setExportJurisdictionId] = useState('');
  const [exportStatus, setExportStatus] = useState('ACTIVE');
  const [isExporting, setIsExporting] = useState(false);
  const [exportedData, setExportedData] = useState<GeoJSONFeatureCollection | null>(null);
  const [copied, setCopied] = useState(false);

  // Sample GeoJSON template for testing
  const loadSampleGeoJson = () => {
    const sample = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [78.4870, 17.3880],
                [78.4875, 17.3880],
                [78.4875, 17.3885],
                [78.4870, 17.3885],
                [78.4870, 17.3880],
              ],
            ],
          },
          properties: {
            parcel_number: `IMP-${Math.floor(Math.random() * 900 + 100)}`,
            land_use: 'COMMERCIAL',
            survey_number: 'IMP-SY10',
            ownership_status: 'TITLED',
          },
        },
      ],
    };
    setGeoJsonInput(JSON.stringify(sample, null, 2));
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        // Basic parse check
        JSON.parse(text);
        setGeoJsonInput(text);
        setImportError(null);
      } catch (err: any) {
        setImportError('Invalid JSON file format: ' + err.message);
      }
    };
    reader.readAsText(file);
  };

  const handleRunImport = async () => {
    if (!importJurisdictionId) {
      setImportError('Please select an administrative jurisdiction for import.');
      return;
    }
    if (!geoJsonInput.trim()) {
      setImportError('Please paste or upload GeoJSON FeatureCollection payload.');
      return;
    }

    let parsedPayload;
    try {
      parsedPayload = JSON.parse(geoJsonInput);
    } catch (err: any) {
      setImportError('Invalid JSON format: ' + err.message);
      return;
    }

    try {
      setIsImporting(true);
      setImportError(null);
      setImportSummary(null);

      const summary = await gisApi.importGeoJSON(importJurisdictionId, parsedPayload);
      setImportSummary(summary);
      if (summary.records_accepted > 0) {
        onImportCompleted();
      }
    } catch (err: any) {
      setImportError(err?.message || 'Import execution failed');
    } finally {
      setIsImporting(false);
    }
  };

  const handleRunExport = async () => {
    try {
      setIsExporting(true);
      const data = await gisApi.exportGeoJSON(
        exportJurisdictionId || undefined,
        exportStatus === 'ALL' ? undefined : exportStatus
      );
      setExportedData(data);
    } catch (err: any) {
      alert('Export failed: ' + (err?.message || 'Unknown error'));
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownloadExport = () => {
    if (!exportedData) return;
    const blob = new Blob([JSON.stringify(exportedData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `geovertex_cadastre_${exportJurisdictionId || 'all'}_${Date.now()}.geojson`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyExport = () => {
    if (!exportedData) return;
    navigator.clipboard.writeText(JSON.stringify(exportedData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl animate-fade-in flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center space-x-2">
              <FileCode className="w-5 h-5 text-emerald-400" />
              <span>Cadastral Data Exchange (GIS GeoJSON)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Standards-compliant GeoJSON FeatureCollection ingest and spatial export.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Headers */}
        <div className="flex border-b border-slate-800 bg-slate-950/30 text-xs">
          <button
            onClick={() => setActiveTab('import')}
            className={`flex-1 py-3 px-4 font-semibold flex items-center justify-center space-x-2 border-b-2 transition ${
              activeTab === 'import'
                ? 'border-emerald-400 text-emerald-400 bg-emerald-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Upload className="w-4 h-4" />
            <span>Import GeoJSON Parcels</span>
          </button>
          <button
            onClick={() => setActiveTab('export')}
            className={`flex-1 py-3 px-4 font-semibold flex items-center justify-center space-x-2 border-b-2 transition ${
              activeTab === 'export'
                ? 'border-emerald-400 text-emerald-400 bg-emerald-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Download className="w-4 h-4" />
            <span>Export Cadastre</span>
          </button>
        </div>

        {/* Tab Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4 text-xs">
          {activeTab === 'import' && (
            <div className="space-y-4">
              {/* Jurisdiction selection */}
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Target Administrative Jurisdiction <span className="text-rose-400">*</span>
                </label>
                <select
                  value={importJurisdictionId}
                  onChange={(e) => setImportJurisdictionId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="">Select Target Jurisdiction...</option>
                  {jurisdictions.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.name} ({j.code})
                    </option>
                  ))}
                </select>
              </div>

              {/* Upload Controls */}
              <div className="flex items-center justify-between">
                <label className="text-slate-300 font-medium">GeoJSON FeatureCollection Payload</label>
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={loadSampleGeoJson}
                    className="text-[11px] text-emerald-400 hover:underline"
                  >
                    Load Valid Sample
                  </button>
                  <span className="text-slate-600">|</span>
                  <label className="text-[11px] text-sky-400 hover:underline cursor-pointer">
                    Upload .geojson file
                    <input
                      type="file"
                      accept=".json,.geojson"
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>

              {/* Code Textarea */}
              <textarea
                value={geoJsonInput}
                onChange={(e) => setGeoJsonInput(e.target.value)}
                placeholder='Paste FeatureCollection JSON with Polygon or MultiPolygon features here...'
                rows={8}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 font-mono text-[11px] text-slate-200 focus:outline-none focus:border-emerald-500"
              />

              {/* Import Button */}
              <button
                onClick={handleRunImport}
                disabled={isImporting || !geoJsonInput.trim() || !importJurisdictionId}
                className="w-full py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/20"
              >
                {isImporting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Validating & Importing...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    <span>Validate & Ingest Parcels</span>
                  </>
                )}
              </button>

              {/* Import Error */}
              {importError && (
                <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg text-rose-300">
                  {importError}
                </div>
              )}

              {/* Import Summary Result */}
              {importSummary && (
                <div className="p-4 rounded-xl border bg-slate-950/80 border-slate-800 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="font-semibold text-white uppercase font-mono">Import Report</span>
                    <div className="flex space-x-2">
                      <span className="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/30">
                        Accepted: {importSummary.records_accepted}
                      </span>
                      <span className="bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded border border-rose-500/30">
                        Rejected: {importSummary.records_rejected}
                      </span>
                    </div>
                  </div>

                  {importSummary.records_rejected > 0 && (
                    <div className="space-y-1.5 max-h-36 overflow-y-auto">
                      <span className="text-[10px] uppercase font-mono text-rose-400 block">
                        Rejection Details:
                      </span>
                      {importSummary.errors.map((err, i) => (
                        <div
                          key={i}
                          className="bg-rose-950/30 p-2 rounded border border-rose-900/40 text-[11px] text-rose-300 flex items-start space-x-2"
                        >
                          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-rose-400" />
                          <div>
                            <span className="font-mono font-bold">
                              Feature #{err.feature_index} [{err.code}]:
                            </span>{' '}
                            {err.message}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'export' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Filter Jurisdiction</label>
                  <select
                    value={exportJurisdictionId}
                    onChange={(e) => setExportJurisdictionId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="">All Jurisdictions</option>
                    {jurisdictions.map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.name} ({j.code})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Status Filter</label>
                  <select
                    value={exportStatus}
                    onChange={(e) => setExportStatus(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="ACTIVE">ACTIVE only</option>
                    <option value="ALL">All statuses</option>
                  </select>
                </div>
              </div>

              <button
                onClick={handleRunExport}
                disabled={isExporting}
                className="w-full py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition flex items-center justify-center space-x-2 disabled:opacity-50 shadow-lg shadow-emerald-500/20"
              >
                {isExporting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Extracting Cadastral Features...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    <span>Generate Cadastre GeoJSON</span>
                  </>
                )}
              </button>

              {exportedData && (
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                    <div>
                      <span className="font-semibold text-white">
                        {exportedData.features?.length || 0} Features Extracted
                      </span>
                      <p className="text-[11px] text-slate-400">CRS: EPSG:4326 (WGS84)</p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={handleCopyExport}
                        className="p-1.5 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 hover:text-white flex items-center space-x-1"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span className="text-[11px]">{copied ? 'Copied' : 'Copy'}</span>
                      </button>
                      <button
                        onClick={handleDownloadExport}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-slate-950 font-bold text-[11px] flex items-center space-x-1"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download .geojson</span>
                      </button>
                    </div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[10px] text-slate-400 max-h-48 overflow-y-auto">
                    <pre>{JSON.stringify(exportedData, null, 2).slice(0, 1500)}...</pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
