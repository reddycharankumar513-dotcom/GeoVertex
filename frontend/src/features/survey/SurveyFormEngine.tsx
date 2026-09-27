import React, { useState } from 'react';
import {
  SurveyAssignment,
  SurveyObservation,
  SurveySession,
} from '../../types';
import {
  Ruler,
  Layers,
  Home,
  FileText,
  MapPin,
  Plus,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Compass,
} from 'lucide-react';

interface SurveyFormEngineProps {
  assignment: SurveyAssignment;
  session: SurveySession;
  currentLocation: {
    latitude: number;
    longitude: number;
    accuracy: number;
    altitude?: number | null;
    verticalAccuracy?: number | null;
  } | null;
  observations: SurveyObservation[];
  onSaveObservation: (
    obs: Omit<SurveyObservation, 'id' | 'created_at' | 'updated_at'> & { id?: string }
  ) => Promise<void>;
  onDeleteObservation?: (id: string) => Promise<void>;
  disabled?: boolean;
}

export const OBSERVATION_TYPES = [
  { value: 'BUILDING_HEIGHT', label: 'Building Height (m)', icon: Ruler, defaultUnit: 'm' },
  { value: 'FLOOR_COUNT', label: 'Floor Count', icon: Layers, defaultUnit: 'floors' },
  { value: 'UNIT_AREA', label: 'Unit Area (sq m)', icon: Home, defaultUnit: 'sq_m' },
  { value: 'BUILDING_TYPE', label: 'Building Type / Classification', icon: Home, defaultUnit: '' },
  { value: 'LAND_USE', label: 'Land Use Classification', icon: Compass, defaultUnit: '' },
  { value: 'STRUCTURAL_CONDITION', label: 'Structural Condition', icon: Activity, defaultUnit: '' },
  { value: 'BOUNDARY_VERIFICATION', label: 'Boundary Verification', icon: MapPin, defaultUnit: '' },
  { value: 'GENERAL_NOTE', label: 'General Field Note', icon: FileText, defaultUnit: '' },
];

const BUILDING_TYPES = [
  'RESIDENTIAL',
  'COMMERCIAL',
  'INDUSTRIAL',
  'MIXED_USE',
  'GOVERNMENT',
  'RELIGIOUS',
  'EDUCATIONAL',
  'HEALTHCARE',
  'OTHER',
];

const LAND_USES = [
  'RESIDENTIAL',
  'COMMERCIAL',
  'INDUSTRIAL',
  'AGRICULTURAL',
  'PUBLIC_OPEN_SPACE',
  'TRANSPORT',
  'SPECIAL_USE',
];

const STRUCTURAL_CONDITIONS = [
  'EXCELLENT',
  'GOOD',
  'FAIR',
  'POOR',
  'DILAPIDATED',
  'UNDER_CONSTRUCTION',
];

export const SurveyFormEngine: React.FC<SurveyFormEngineProps> = ({
  assignment,
  session,
  currentLocation,
  observations,
  onSaveObservation,
  onDeleteObservation,
  disabled = false,
}) => {
  const [selectedType, setSelectedType] = useState('BUILDING_HEIGHT');
  const [value, setValue] = useState('');
  const [unit, setUnit] = useState('m');
  const [notes, setNotes] = useState('');
  const [targetType, setTargetType] = useState<string>(
    assignment.building_id ? 'BUILDING' : assignment.parcel_id ? 'PARCEL' : 'PROPERTY'
  );
  const [targetId, setTargetId] = useState<string>(
    assignment.building_id || assignment.parcel_id || assignment.property_id || assignment.id
  );
  const [attachGps, setAttachGps] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTypeChange = (typeVal: string) => {
    setSelectedType(typeVal);
    setError(null);
    const def = OBSERVATION_TYPES.find((t) => t.value === typeVal);
    if (def) {
      setUnit(def.defaultUnit);
    }
    if (typeVal === 'BUILDING_TYPE') {
      setValue(BUILDING_TYPES[0]);
    } else if (typeVal === 'LAND_USE') {
      setValue(LAND_USES[0]);
    } else if (typeVal === 'STRUCTURAL_CONDITION') {
      setValue(STRUCTURAL_CONDITIONS[1]); // GOOD
    } else {
      setValue('');
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) {
      setError('Please provide a valid observation value');
      return;
    }

    if (
      (selectedType === 'BUILDING_HEIGHT' ||
        selectedType === 'FLOOR_COUNT' ||
        selectedType === 'UNIT_AREA') &&
      (isNaN(Number(value)) || Number(value) < 0)
    ) {
      setError('Value must be a positive number');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onSaveObservation({
        session_id: session.id,
        observation_type: selectedType,
        target_type: targetType,
        target_id: targetId,
        value: value.trim(),
        unit: unit || null,
        notes: notes.trim() || null,
        captured_at: new Date().toISOString(),
        latitude: attachGps && currentLocation ? currentLocation.latitude : null,
        longitude: attachGps && currentLocation ? currentLocation.longitude : null,
        horizontal_accuracy: attachGps && currentLocation ? currentLocation.accuracy : null,
        altitude: attachGps && currentLocation ? currentLocation.altitude || null : null,
        vertical_accuracy: attachGps && currentLocation ? currentLocation.verticalAccuracy || null : null,
        source: attachGps && currentLocation ? 'GPS' : 'MANUAL',
      });

      // Reset form
      if (selectedType === 'BUILDING_TYPE') {
        setValue(BUILDING_TYPES[0]);
      } else if (selectedType === 'LAND_USE') {
        setValue(LAND_USES[0]);
      } else if (selectedType === 'STRUCTURAL_CONDITION') {
        setValue(STRUCTURAL_CONDITIONS[1]);
      } else {
        setValue('');
      }
      setNotes('');
    } catch (err: any) {
      setError(err?.message || 'Failed to save observation');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedDef = OBSERVATION_TYPES.find((t) => t.value === selectedType);
  const IconComponent = selectedDef?.icon || FileText;

  return (
    <div className="space-y-6">
      {/* Observation Entry Form */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center space-x-2">
            <div className="p-2 bg-sky-500/10 text-sky-400 rounded-lg">
              <IconComponent className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Record Field Observation</h3>
              <p className="text-xs text-slate-400">Capture verifiable cadastre measurements</p>
            </div>
          </div>
          {currentLocation && (
            <div className="flex items-center space-x-1.5 text-xs bg-slate-800/80 px-2.5 py-1 rounded-full border border-slate-700">
              <MapPin className="w-3.5 h-3.5 text-sky-400" />
              <span className="text-slate-300 font-mono text-[11px]">
                {currentLocation.latitude.toFixed(5)}, {currentLocation.longitude.toFixed(5)}
              </span>
              <span
                className={`ml-1 px-1.5 py-0.2 rounded text-[10px] font-mono ${
                  currentLocation.accuracy <= 5
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : currentLocation.accuracy <= 15
                    ? 'bg-amber-500/20 text-amber-300'
                    : 'bg-rose-500/20 text-rose-300'
                }`}
              >
                ±{Math.round(currentLocation.accuracy)}m
              </span>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-start space-x-2 text-rose-300 text-xs">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-4">
          {/* Observation Type Selector */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Observation Type
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {OBSERVATION_TYPES.map((type) => {
                const isSelected = selectedType === type.value;
                const TypeIcon = type.icon;
                return (
                  <button
                    key={type.value}
                    type="button"
                    disabled={disabled}
                    onClick={() => handleTypeChange(type.value)}
                    className={`flex items-center space-x-2 p-2.5 rounded-lg border text-left text-xs transition-all ${
                      isSelected
                        ? 'border-sky-500 bg-sky-500/15 text-white font-medium shadow-sm'
                        : 'border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                    }`}
                  >
                    <TypeIcon
                      className={`w-3.5 h-3.5 shrink-0 ${
                        isSelected ? 'text-sky-400' : 'text-slate-500'
                      }`}
                    />
                    <span className="truncate">{type.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Dynamic Value Input */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Measured Value <span className="text-rose-400">*</span>
              </label>

              {selectedType === 'BUILDING_TYPE' ? (
                <select
                  disabled={disabled}
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
                >
                  {BUILDING_TYPES.map((bt) => (
                    <option key={bt} value={bt}>
                      {bt}
                    </option>
                  ))}
                </select>
              ) : selectedType === 'LAND_USE' ? (
                <select
                  disabled={disabled}
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
                >
                  {LAND_USES.map((lu) => (
                    <option key={lu} value={lu}>
                      {lu}
                    </option>
                  ))}
                </select>
              ) : selectedType === 'STRUCTURAL_CONDITION' ? (
                <select
                  disabled={disabled}
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
                >
                  {STRUCTURAL_CONDITIONS.map((sc) => (
                    <option key={sc} value={sc}>
                      {sc}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="flex space-x-2">
                  <input
                    type={
                      selectedType === 'BUILDING_HEIGHT' ||
                      selectedType === 'FLOOR_COUNT' ||
                      selectedType === 'UNIT_AREA'
                        ? 'number'
                        : 'text'
                    }
                    step={selectedType === 'FLOOR_COUNT' ? '1' : '0.01'}
                    disabled={disabled}
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    placeholder={
                      selectedType === 'BUILDING_HEIGHT'
                        ? 'e.g. 15.5'
                        : selectedType === 'FLOOR_COUNT'
                        ? 'e.g. 4'
                        : selectedType === 'UNIT_AREA'
                        ? 'e.g. 120.5'
                        : 'Enter observation details...'
                    }
                    className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                  />
                  {unit && (
                    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-300 flex items-center">
                      {unit}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Target Selector */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Target Entity</label>
              <div className="flex space-x-2">
                <select
                  disabled={disabled}
                  value={targetType}
                  onChange={(e) => {
                    const nt = e.target.value;
                    setTargetType(nt);
                    if (nt === 'BUILDING') setTargetId(assignment.building_id || assignment.id);
                    else if (nt === 'PARCEL') setTargetId(assignment.parcel_id || assignment.id);
                    else if (nt === 'PROPERTY') setTargetId(assignment.property_id || assignment.id);
                    else if (nt === 'FLOOR') setTargetId(assignment.floor_id || assignment.id);
                    else if (nt === 'UNIT') setTargetId(assignment.unit_id || assignment.id);
                  }}
                  className="w-1/3 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
                >
                  <option value="BUILDING">Building</option>
                  <option value="PARCEL">Parcel</option>
                  <option value="PROPERTY">Property</option>
                  <option value="FLOOR">Floor</option>
                  <option value="UNIT">Unit</option>
                </select>
                <input
                  type="text"
                  disabled={disabled}
                  value={targetId}
                  onChange={(e) => setTargetId(e.target.value)}
                  placeholder="Target identifier or ID"
                  className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-300 font-mono focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>
          </div>

          {/* Notes & GPS Attachment */}
          <div className="space-y-2">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Field Notes / Surveyor Remarks (Optional)
              </label>
              <textarea
                rows={2}
                disabled={disabled}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Field observations, method of measurement, visible discrepancies..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={attachGps}
                  onChange={(e) => setAttachGps(e.target.checked)}
                  disabled={disabled || !currentLocation}
                  className="w-4 h-4 rounded border-slate-700 bg-slate-950 text-sky-500 focus:ring-sky-500"
                />
                <span>Attach current GPS position to observation</span>
              </label>

              {currentLocation && currentLocation.accuracy > 15 && attachGps && (
                <span className="text-[11px] text-amber-400 flex items-center space-x-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>GPS accuracy is &gt;15m</span>
                </span>
              )}
            </div>
          </div>

          <button
            type="submit"
            disabled={disabled || isSubmitting}
            className="w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 shadow-lg shadow-sky-600/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>{isSubmitting ? 'Recording...' : 'Add Field Observation'}</span>
          </button>
        </form>
      </div>

      {/* Captured Observations List */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-md">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
              Recorded Observations ({observations.length})
            </h4>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            Session: {session.id.slice(0, 8)}
          </span>
        </div>

        {observations.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            No observations recorded yet. Fill out the form above to add measurements.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {observations.map((obs) => {
              const def = OBSERVATION_TYPES.find((t) => t.value === obs.observation_type);
              const ObsIcon = def?.icon || FileText;

              return (
                <div
                  key={obs.id}
                  className="py-3 flex items-start justify-between space-x-3 hover:bg-slate-800/20 px-2 rounded-lg transition-colors"
                >
                  <div className="flex items-start space-x-3 min-w-0">
                    <div className="p-1.5 bg-slate-800 rounded-md text-sky-400 shrink-0 mt-0.5">
                      <ObsIcon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-semibold text-white">
                          {def?.label || obs.observation_type}
                        </span>
                        <span className="text-xs font-bold text-sky-300 font-mono">
                          {obs.value} {obs.unit || ''}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-[11px] text-slate-400">
                        <span>
                          Target:{' '}
                          <span className="font-mono text-slate-300">
                            {obs.target_type}:{obs.target_id.slice(0, 8)}
                          </span>
                        </span>
                        {obs.latitude && obs.longitude && (
                          <span className="flex items-center space-x-1 font-mono text-slate-400">
                            <MapPin className="w-3 h-3 text-sky-400" />
                            <span>
                              {obs.latitude.toFixed(5)}, {obs.longitude.toFixed(5)}
                            </span>
                            {obs.horizontal_accuracy && (
                              <span className="text-slate-500">
                                (±{Math.round(obs.horizontal_accuracy)}m)
                              </span>
                            )}
                          </span>
                        )}
                        <span className="text-slate-500">
                          {new Date(obs.captured_at).toLocaleTimeString()}
                        </span>
                      </div>

                      {obs.notes && (
                        <p className="mt-1 text-xs text-slate-300 italic bg-slate-950/40 p-1.5 rounded border border-slate-800/50">
                          "{obs.notes}"
                        </p>
                      )}
                    </div>
                  </div>

                  {!disabled && onDeleteObservation && (
                    <button
                      type="button"
                      onClick={() => onDeleteObservation(obs.id)}
                      className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition-colors"
                      title="Delete observation"
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
    </div>
  );
};
