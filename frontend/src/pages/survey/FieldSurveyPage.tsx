import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  SurveyAssignment,
  SurveyEvidence,
  SurveyObservation,
  SurveySession,
  SurveyValidationSummary,
} from '../../types';
import { surveyApi } from '../../api/surveys';
import { offlineStorage } from '../../utils/offlineStorage';
import { useOnlineStatus } from '../../hooks/useOnlineStatus';
import { SurveyMap } from '../../features/survey/SurveyMap';
import { SurveyFormEngine } from '../../features/survey/SurveyFormEngine';
import { EvidenceGallery } from '../../features/survey/EvidenceGallery';
import { ValidationChecklist } from '../../features/survey/ValidationChecklist';
import {
  ArrowLeft,
  MapPin,
  Camera,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Wifi,
  WifiOff,
  Pause,
  Play,
  RotateCcw,
  Scale,
  Building2,
  Calendar,
  Save,
  Check,
} from 'lucide-react';

export const FieldSurveyPage: React.FC = () => {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const navigate = useNavigate();
  const { isOnline, isSyncing, pendingSyncCount, syncNow } = useOnlineStatus();

  const [assignment, setAssignment] = useState<SurveyAssignment | null>(null);
  const [session, setSession] = useState<SurveySession | null>(null);
  const [observations, setObservations] = useState<SurveyObservation[]>([]);
  const [evidence, setEvidence] = useState<SurveyEvidence[]>([]);
  const [validation, setValidation] = useState<SurveyValidationSummary | null>(null);

  const [activeTab, setActiveTab] = useState<'map' | 'observations' | 'evidence' | 'checklist'>('map');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  // Real-time GPS State
  const [currentLocation, setCurrentLocation] = useState<{
    latitude: number;
    longitude: number;
    accuracy: number;
    altitude?: number | null;
    verticalAccuracy?: number | null;
  } | null>(null);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const watchIdRef = useRef<number | null>(null);

  // Initialize Geolocation Tracking
  useEffect(() => {
    if (typeof navigator !== 'undefined' && 'geolocation' in navigator) {
      watchIdRef.current = navigator.geolocation.watchPosition(
        (pos) => {
          setCurrentLocation({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            altitude: pos.coords.altitude,
            verticalAccuracy: pos.coords.altitudeAccuracy,
          });
          setGpsError(null);
        },
        (err) => {
          console.warn('Geolocation error:', err.message);
          setGpsError('GPS signal weak or unavailable');
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0,
        }
      );
    } else {
      setGpsError('Geolocation is not supported by this browser');
    }

    return () => {
      if (watchIdRef.current !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
  }, []);

  // Fetch Assignment and Active Session
  const loadSurveyData = useCallback(async () => {
    if (!assignmentId) return;
    setIsLoading(true);
    setError(null);

    try {
      let assignData: SurveyAssignment | null = null;

      if (isOnline) {
        try {
          assignData = await surveyApi.getAssignment(assignmentId);
          await offlineStorage.cacheAssignments([assignData]);
        } catch {
          assignData = await offlineStorage.getLocalAssignment(assignmentId);
        }
      } else {
        assignData = await offlineStorage.getLocalAssignment(assignmentId);
      }

      if (!assignData) {
        setError('Assignment could not be found.');
        setIsLoading(false);
        return;
      }
      setAssignment(assignData);

      // Start or retrieve session
      let sessData: SurveySession | null = null;
      if (isOnline) {
        try {
          sessData = await surveyApi.startSurvey(assignmentId);
          await offlineStorage.cacheSession(sessData);
        } catch {
          // Fallback to checking local session
          sessData = await offlineStorage.getLocalSession(`sess_${assignmentId}`);
        }
      } else {
        sessData = await offlineStorage.getLocalSession(`sess_${assignmentId}`);
      }

      // If still no session, create local stub session
      if (!sessData) {
        sessData = {
          id: `sess_local_${assignmentId}_${Date.now()}`,
          assignment_id: assignmentId,
          surveyor_id: assignData.surveyor_id,
          started_at: new Date().toISOString(),
          status: 'ACTIVE',
          sync_status: 'LOCAL',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        await offlineStorage.cacheSession(sessData);
      }
      setSession(sessData);

      // Load Observations
      if (isOnline && sessData.id && !sessData.id.startsWith('sess_local_')) {
        try {
          const obsData = await surveyApi.getObservations(sessData.id);
          setObservations(obsData);
        } catch {
          const localObs = await offlineStorage.getLocalObservations(sessData.id);
          setObservations(localObs);
        }
      } else {
        const localObs = await offlineStorage.getLocalObservations(sessData.id);
        setObservations(localObs);
      }

      // Load Evidence
      if (isOnline && sessData.id && !sessData.id.startsWith('sess_local_')) {
        try {
          const evData = await surveyApi.getEvidence(sessData.id);
          setEvidence(evData);
        } catch {
          setEvidence([]);
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to initialize survey session');
    } finally {
      setIsLoading(false);
    }
  }, [assignmentId, isOnline]);

  useEffect(() => {
    loadSurveyData();
  }, [loadSurveyData]);

  // Handle Save Observation
  const handleSaveObservation = async (
    obsInput: Omit<SurveyObservation, 'id' | 'created_at' | 'updated_at'> & { id?: string }
  ) => {
    if (!session) return;
    setError(null);

    const now = new Date().toISOString();
    const tempId = obsInput.id || `obs_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const fullObs: SurveyObservation = {
      ...obsInput,
      id: tempId,
      created_at: now,
      updated_at: now,
    };

    if (isOnline && !session.id.startsWith('sess_local_')) {
      try {
        const saved = await surveyApi.createObservation(session.id, {
          observation_type: obsInput.observation_type,
          target_type: obsInput.target_type,
          target_id: obsInput.target_id,
          value: obsInput.value,
          unit: obsInput.unit || undefined,
          notes: obsInput.notes || undefined,
          latitude: obsInput.latitude || undefined,
          longitude: obsInput.longitude || undefined,
          horizontal_accuracy: obsInput.horizontal_accuracy || undefined,
          altitude: obsInput.altitude || undefined,
          vertical_accuracy: obsInput.vertical_accuracy || undefined,
          source: obsInput.source,
        });
        setObservations((prev) => [...prev, saved]);
        await offlineStorage.saveDraftObservation(saved);
        setInfoMessage('Observation saved to server.');
      } catch (err) {
        // Enqueue offline
        await offlineStorage.saveDraftObservation(fullObs);
        await offlineStorage.enqueueSyncOperation({
          client_operation_id: `sync_obs_${tempId}`,
          session_id: session.id,
          operation_type: 'CREATE',
          entity_type: 'SURVEY_OBSERVATION',
          entity_id: tempId,
          payload: fullObs,
        });
        setObservations((prev) => [...prev, fullObs]);
        setInfoMessage('Observation saved locally in offline sync queue.');
      }
    } else {
      await offlineStorage.saveDraftObservation(fullObs);
      await offlineStorage.enqueueSyncOperation({
        client_operation_id: `sync_obs_${tempId}`,
        session_id: session.id,
        operation_type: 'CREATE',
        entity_type: 'SURVEY_OBSERVATION',
        entity_id: tempId,
        payload: fullObs,
      });
      setObservations((prev) => [...prev, fullObs]);
      setInfoMessage('Saved locally (Offline Mode).');
    }

    setTimeout(() => setInfoMessage(null), 3500);
  };

  // Handle Photo Evidence Upload
  const handleUploadEvidence = async (
    file: File,
    description: string,
    evidenceType: string,
    coords?: { lat: number; lng: number; acc: number }
  ) => {
    if (!session) return;
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('evidence_type', evidenceType);
    formData.append('target_type', assignment?.building_id ? 'BUILDING' : 'PARCEL');
    formData.append('target_id', assignment?.building_id || assignment?.parcel_id || assignment?.id || '');
    if (description) formData.append('description', description);
    if (coords) {
      formData.append('latitude', coords.lat.toString());
      formData.append('longitude', coords.lng.toString());
      formData.append('accuracy', coords.acc.toString());
    }

    if (isOnline && !session.id.startsWith('sess_local_')) {
      const saved = await surveyApi.uploadEvidence(session.id, formData);
      setEvidence((prev) => [...prev, saved]);
      setInfoMessage('Photo evidence uploaded and cryptographically verified.');
    } else {
      setError('Photo upload requires an active network connection for secure hashing and object storage.');
    }

    setTimeout(() => setInfoMessage(null), 3500);
  };

  // Run Pre-Submission Cadastral Validation
  const handleRunValidation = async () => {
    if (!session) return;
    setIsValidating(true);
    setError(null);

    try {
      if (isOnline && !session.id.startsWith('sess_local_')) {
        const valSummary = await surveyApi.validateSession(session.id);
        setValidation(valSummary);
      } else {
        // Local deterministic validation calculation
        const hasObs = observations.length > 0;
        const hasEv = evidence.length > 0;
        const gpsAccOK = !observations.some((o) => (o.horizontal_accuracy || 0) > 25);
        const canSub = hasObs && hasEv;

        setValidation({
          is_valid: canSub,
          can_submit: canSub,
          total_errors: canSub ? 0 : (!hasObs ? 1 : 0) + (!hasEv ? 1 : 0),
          total_warnings: gpsAccOK ? 0 : 1,
          issues: [
            ...(!hasObs
              ? [{ code: 'NO_OBSERVATIONS', severity: 'ERROR' as const, message: 'At least one field observation is required.' }]
              : []),
            ...(!hasEv
              ? [{ code: 'NO_EVIDENCE', severity: 'ERROR' as const, message: 'At least one photograph is required.' }]
              : []),
          ],
          checklist: {
            has_observations: hasObs,
            has_evidence: hasEv,
            gps_accuracy_acceptable: gpsAccOK,
            targets_valid: true,
          },
          comparisons: [],
        });
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to run validation engine');
    } finally {
      setIsValidating(false);
    }
  };

  // Submit Survey for Review
  const handleSubmitSurvey = async () => {
    if (!session) return;
    setIsSubmitting(true);
    setError(null);

    try {
      if (isOnline && !session.id.startsWith('sess_local_')) {
        await surveyApi.submitSurvey(session.id);
        setInfoMessage('Survey submitted successfully for Cadastral Officer review!');
        setTimeout(() => navigate('/surveyor'), 2000);
      } else {
        setError('Cannot submit to official review while offline. Please connect and sync your session first.');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to submit survey');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Pause / Resume Session
  const toggleSessionPause = async () => {
    if (!session || !isOnline) return;
    try {
      if (session.status === 'PAUSED') {
        const resumed = await surveyApi.resumeSession(session.id);
        setSession(resumed);
        setInfoMessage('Survey session resumed.');
      } else {
        const paused = await surveyApi.pauseSession(session.id);
        setSession(paused);
        setInfoMessage('Survey session paused.');
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to toggle session state');
    }
  };

  const isReadOnly = assignment?.status === 'APPROVED' || assignment?.status === 'SUBMITTED';

  if (isLoading) {
    return (
      <div className="py-24 text-center text-slate-400 text-xs">
        <div className="animate-spin w-6 h-6 border-2 border-sky-500 border-t-transparent rounded-full mx-auto mb-3" />
        Initializing Field Survey Console...
      </div>
    );
  }

  if (!assignment) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400">
        Assignment not found or inaccessible.
        <div className="mt-4">
          <button
            onClick={() => navigate('/surveyor')}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-6xl mx-auto pb-12">
      {/* Top Navigation & Status Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={() => navigate('/surveyor')}
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors cursor-pointer"
              title="Back to assignments"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[11px] font-mono text-sky-400 font-bold uppercase">
                  {assignment.project_code || 'SURVEY'}
                </span>
                <span className="text-slate-600">•</span>
                <span className="text-xs font-semibold text-white">
                  {assignment.parcel_code || assignment.building_reference || 'Target Survey'}
                </span>
                <span
                  className={`px-2 py-0.2 rounded text-[10px] font-mono font-medium ${
                    assignment.status === 'APPROVED'
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : assignment.status === 'REVISION_REQUIRED'
                      ? 'bg-amber-500/20 text-amber-300'
                      : 'bg-sky-500/20 text-sky-300'
                  }`}
                >
                  {assignment.status.replace('_', ' ')}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {assignment.jurisdiction_name || 'Cadastral Territory'} • Assignment ID: {assignment.id.slice(0, 8)}
              </p>
            </div>
          </div>

          {/* Quick controls */}
          <div className="flex items-center space-x-2">
            {/* GPS Pill */}
            {currentLocation ? (
              <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-800 text-xs font-mono border border-slate-700">
                <MapPin className="w-3.5 h-3.5 text-sky-400" />
                <span className="text-slate-300 text-[11px]">
                  {currentLocation.latitude.toFixed(4)}, {currentLocation.longitude.toFixed(4)}
                </span>
                <span
                  className={`ml-1 px-1.5 rounded text-[10px] ${
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
            ) : (
              <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-800 text-xs text-amber-400 border border-slate-700">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span className="text-[11px]">{gpsError || 'Acquiring GPS...'}</span>
              </div>
            )}

            {/* Online / Offline status */}
            <div
              className={`p-1.5 rounded-lg border text-xs flex items-center justify-center ${
                isOnline
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
              }`}
              title={isOnline ? 'Online' : 'Offline Mode'}
            >
              {isOnline ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            </div>

            {/* Session Pause/Resume */}
            {session && isOnline && !isReadOnly && (
              <button
                type="button"
                onClick={toggleSessionPause}
                className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors cursor-pointer"
                title={session.status === 'PAUSED' ? 'Resume Session' : 'Pause Session'}
              >
                {session.status === 'PAUSED' ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
              </button>
            )}
          </div>
        </div>

        {/* Revision Required Alert Banner */}
        {assignment.status === 'REVISION_REQUIRED' && (
          <div className="mt-3 p-3 bg-amber-500/15 border border-amber-500/30 rounded-lg flex items-start space-x-2.5 text-xs text-amber-300">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Reviewer Revision Requested: </span>
              {assignment.notes || 'Please adjust the recorded observations or take supplementary photo evidence.'}
            </div>
          </div>
        )}

        {/* Read-Only Status Banner */}
        {isReadOnly && (
          <div className="mt-3 p-3 bg-sky-500/10 border border-sky-500/30 rounded-lg flex items-center space-x-2 text-xs text-sky-300">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>
              This survey is in <strong className="font-mono">{assignment.status}</strong> status and cannot be modified.
            </span>
          </div>
        )}

        {/* Info or Error Banner */}
        {infoMessage && (
          <div className="mt-3 p-2.5 bg-emerald-500/15 border border-emerald-500/30 rounded-lg text-xs text-emerald-300 flex items-center space-x-2">
            <Check className="w-4 h-4 shrink-0" />
            <span>{infoMessage}</span>
          </div>
        )}
        {error && (
          <div className="mt-3 p-2.5 bg-rose-500/15 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('map')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'map'
              ? 'bg-sky-600 text-white shadow-sm'
              : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          <MapPin className="w-3.5 h-3.5" />
          <span>Interactive Map</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('observations')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'observations'
              ? 'bg-sky-600 text-white shadow-sm'
              : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Observations ({observations.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('evidence')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'evidence'
              ? 'bg-sky-600 text-white shadow-sm'
              : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          <Camera className="w-3.5 h-3.5" />
          <span>Photo Evidence ({evidence.length})</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveTab('checklist');
            handleRunValidation();
          }}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'checklist'
              ? 'bg-sky-600 text-white shadow-sm'
              : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Review & Submit</span>
        </button>
      </div>

      {/* Main Tab Content */}
      <div>
        {activeTab === 'map' && (
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg">
            <SurveyMap
              parcelWkt={null}
              buildingWkt={null}
              currentLat={currentLocation?.latitude}
              currentLon={currentLocation?.longitude}
              accuracy={currentLocation?.accuracy}
              observations={observations}
              evidence={evidence}
              onCaptureCoordinate={(lat, lon, acc) => {
                setActiveTab('observations');
              }}
            />
          </div>
        )}

        {activeTab === 'observations' && session && (
          <SurveyFormEngine
            assignment={assignment}
            session={session}
            currentLocation={currentLocation}
            observations={observations}
            onSaveObservation={handleSaveObservation}
            disabled={isReadOnly}
          />
        )}

        {activeTab === 'evidence' && session && (
          <EvidenceGallery
            sessionId={session.id}
            targetType={assignment.building_id ? 'BUILDING' : 'PARCEL'}
            targetId={assignment.building_id || assignment.parcel_id || assignment.id}
            evidence={evidence}
            currentLocation={currentLocation}
            onUploadEvidence={handleUploadEvidence}
            disabled={isReadOnly}
          />
        )}

        {activeTab === 'checklist' && (
          <ValidationChecklist
            validation={validation}
            isLoading={isValidating}
            onRunValidation={handleRunValidation}
            onSubmitSurvey={handleSubmitSurvey}
            isSubmitting={isSubmitting}
            disabled={isReadOnly}
          />
        )}
      </div>
    </div>
  );
};
