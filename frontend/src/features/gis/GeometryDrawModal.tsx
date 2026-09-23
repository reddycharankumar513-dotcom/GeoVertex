import React, { useState, useEffect } from 'react';
import { X, CheckCircle, AlertTriangle, Maximize2, ShieldAlert, Sparkles, Loader2 } from 'lucide-react';
import { gisApi } from '../../api/gis';
import { Jurisdiction, Parcel, GeometryValidationResponse } from '../../types';

interface GeometryDrawModalProps {
  points: [number, number][];
  jurisdictions: Jurisdiction[];
  selectedJurisdictionId?: string;
  onClose: () => void;
  onSaved: (parcel: Parcel) => void;
}

export const GeometryDrawModal: React.FC<GeometryDrawModalProps> = ({
  points,
  jurisdictions,
  selectedJurisdictionId,
  onClose,
  onSaved,
}) => {
  const [jurisdictionId, setJurisdictionId] = useState(
    selectedJurisdictionId || (jurisdictions.length > 0 ? jurisdictions[0].id : '')
  );
  const [parcelNumber, setParcelNumber] = useState('');
  const [parcelCode, setParcelCode] = useState('');
  const [surveyNumber, setSurveyNumber] = useState('');
  const [subdivisionNumber, setSubdivisionNumber] = useState('');
  const [landUse, setLandUse] = useState('RESIDENTIAL');
  const [ownershipStatus, setOwnershipStatus] = useState('TITLED');
  const [source, setSource] = useState('DIGITIZED');

  const [isValidating, setIsValidating] = useState(true);
  const [validationResult, setValidationResult] = useState<GeometryValidationResponse | null>(null);
  const [overlapWarning, setOverlapWarning] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Construct closed polygon GeoJSON
  const closedCoordinates = [...points];
  if (
    closedCoordinates.length > 0 &&
    (closedCoordinates[0][0] !== closedCoordinates[closedCoordinates.length - 1][0] ||
      closedCoordinates[0][1] !== closedCoordinates[closedCoordinates.length - 1][1])
  ) {
    closedCoordinates.push(closedCoordinates[0]);
  }

  const polygonGeoJSON = {
    type: 'Polygon',
    coordinates: [closedCoordinates],
  };

  useEffect(() => {
    let isMounted = true;
    const runValidation = async () => {
      setIsValidating(true);
      setErrorMessage(null);
      setOverlapWarning(null);

      try {
        const valRes = await gisApi.validateGeometry(polygonGeoJSON, 'POLYGON');
        if (!isMounted) return;
        setValidationResult(valRes);

        // If geometry is geometrically valid and jurisdiction is selected, check overlap
        if (valRes.valid && jurisdictionId) {
          try {
            const overlapRes = await gisApi.checkOverlap(polygonGeoJSON, jurisdictionId);
            if (overlapRes.has_conflicts) {
              setOverlapWarning(
                `Geometry overlaps with ${overlapRes.conflicts.length} existing parcel(s) in this jurisdiction.`
              );
            }
          } catch (oErr) {
            console.warn('Overlap check failed:', oErr);
          }
        }
      } catch (err: any) {
        if (!isMounted) return;
        setErrorMessage(err?.message || 'Failed to validate geometry');
      } finally {
        if (isMounted) setIsValidating(false);
      }
    };

    if (points.length >= 3) {
      runValidation();
    } else {
      setIsValidating(false);
      setValidationResult({
        valid: false,
        errors: [{ code: 'INSUFFICIENT_VERTICES', message: 'Polygon must have at least 3 distinct vertices.' }],
        warnings: [],
      });
    }

    return () => {
      isMounted = false;
    };
  }, [points, jurisdictionId]);

  // Auto-generate code when number changes
  const handleNumberChange = (val: string) => {
    setParcelNumber(val);
    if (!parcelCode || parcelCode.startsWith('P-') || parcelCode.includes('-')) {
      const selectedJur = jurisdictions.find((j) => j.id === jurisdictionId);
      const jurPrefix = selectedJur?.code ? `${selectedJur.code}-` : '';
      setParcelCode(`${jurPrefix}${val.toUpperCase()}`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validationResult?.valid) {
      alert('Cannot save invalid geometry. Please resolve validation errors.');
      return;
    }
    if (!jurisdictionId) {
      alert('Please select a jurisdiction.');
      return;
    }

    try {
      setIsSaving(true);
      setErrorMessage(null);

      const created = await gisApi.createParcel({
        jurisdiction_id: jurisdictionId,
        parcel_number: parcelNumber,
        parcel_code: parcelCode,
        survey_number: surveyNumber || undefined,
        subdivision_number: subdivisionNumber || undefined,
        land_use: landUse,
        geometry: polygonGeoJSON,
        source: source,
      });

      onSaved(created);
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to create parcel');
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl animate-fade-in flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-emerald-400"></span>
              <span>Register New Cadastral Parcel</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Verify digitized geometry and record authoritative property attributes.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Form Content */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-5 flex-1">
          {/* Spatial Validation Banner */}
          <div className="p-3.5 rounded-xl border bg-slate-950/60 border-slate-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
                Authoritative Geometry Validation
              </span>
              {isValidating ? (
                <span className="flex items-center text-xs text-sky-400">
                  <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> Validating...
                </span>
              ) : validationResult?.valid ? (
                <span className="flex items-center text-xs font-semibold text-emerald-400">
                  <CheckCircle className="w-4 h-4 mr-1 text-emerald-400" /> Geometrically Valid
                </span>
              ) : (
                <span className="flex items-center text-xs font-semibold text-rose-400">
                  <AlertTriangle className="w-4 h-4 mr-1 text-rose-400" /> Invalid Geometry
                </span>
              )}
            </div>

            {validationResult?.valid && (
              <div className="grid grid-cols-2 gap-3 text-xs bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80">
                <div>
                  <span className="text-slate-400 block text-[11px]">Geodesic WGS84 Area:</span>
                  <span className="text-white font-mono font-bold text-sm">
                    {validationResult.area_sq_m?.toLocaleString(undefined, { maximumFractionDigits: 2 })} m²
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Perimeter:</span>
                  <span className="text-white font-mono font-bold text-sm">
                    {validationResult.perimeter_m?.toLocaleString(undefined, { maximumFractionDigits: 2 })} m
                  </span>
                </div>
              </div>
            )}

            {validationResult?.errors && validationResult.errors.length > 0 && (
              <div className="mt-2 text-xs space-y-1">
                {validationResult.errors.map((err, i) => (
                  <div key={i} className="text-rose-400 flex items-start space-x-1.5 bg-rose-950/30 p-2 rounded border border-rose-900/50">
                    <ShieldAlert className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold font-mono text-[11px] block">[{err.code}]</span>
                      <span>{err.message}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {overlapWarning && (
              <div className="mt-2 text-xs text-amber-400 flex items-start space-x-1.5 bg-amber-950/30 p-2 rounded border border-amber-900/50">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{overlapWarning}</span>
              </div>
            )}
          </div>

          {/* Form Fields */}
          <div className="space-y-4 text-xs">
            {/* Jurisdiction */}
            <div>
              <label className="block text-slate-300 font-medium mb-1">
                Cadastral Jurisdiction <span className="text-rose-400">*</span>
              </label>
              <select
                value={jurisdictionId}
                onChange={(e) => setJurisdictionId(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
              >
                <option value="">Select Jurisdiction...</option>
                {jurisdictions.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.name} ({j.code}) - {j.level}
                  </option>
                ))}
              </select>
            </div>

            {/* Parcel Number & Code */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Parcel Number <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. P-205"
                  value={parcelNumber}
                  onChange={(e) => handleNumberChange(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Parcel Code <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. W101-P205"
                  value={parcelCode}
                  onChange={(e) => setParcelCode(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
            </div>

            {/* Land Use & Ownership */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Land Use</label>
                <select
                  value={landUse}
                  onChange={(e) => setLandUse(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="RESIDENTIAL">Residential</option>
                  <option value="COMMERCIAL">Commercial</option>
                  <option value="MIXED_USE">Mixed Use</option>
                  <option value="INDUSTRIAL">Industrial</option>
                  <option value="PUBLIC">Public / Civic</option>
                  <option value="AGRICULTURAL">Agricultural</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Ownership Status</label>
                <select
                  value={ownershipStatus}
                  onChange={(e) => setOwnershipStatus(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="TITLED">Titled</option>
                  <option value="LEASEHOLD">Leasehold</option>
                  <option value="GOVERNMENT">Government Owned</option>
                  <option value="DISPUTED">Disputed</option>
                </select>
              </div>
            </div>

            {/* Survey & Subdivision Numbers */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Survey Number</label>
                <input
                  type="text"
                  placeholder="e.g. SY-402"
                  value={surveyNumber}
                  onChange={(e) => setSurveyNumber(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Subdivision</label>
                <input
                  type="text"
                  placeholder="e.g. SUB-B"
                  value={subdivisionNumber}
                  onChange={(e) => setSubdivisionNumber(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
            </div>

            {/* Data Source */}
            <div>
              <label className="block text-slate-300 font-medium mb-1">Data Source</label>
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
              >
                <option value="DIGITIZED">Interactive Digitization</option>
                <option value="FIELD_SURVEY">Field Survey (GNSS/Total Station)</option>
                <option value="CAD_IMPORT">CAD / DXF Migration</option>
                <option value="SATELLITE_DERIVED">High-Res Ortho Derived</option>
              </select>
            </div>
          </div>

          {/* General Error Message */}
          {errorMessage && (
            <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg text-xs text-rose-300">
              {errorMessage}
            </div>
          )}

          {/* Footer Buttons */}
          <div className="pt-2 flex items-center justify-end space-x-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="px-4 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition text-xs font-medium"
            >
              Discard
            </button>
            <button
              type="submit"
              disabled={isSaving || !validationResult?.valid}
              className="px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition text-xs flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/20"
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving Parcel...</span>
                </>
              ) : (
                <span>Register Parcel</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
