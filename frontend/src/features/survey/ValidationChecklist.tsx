import React from 'react';
import { SurveyValidationSummary } from '../../types';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Send,
  Scale,
  ShieldCheck,
  AlertCircle,
  ChevronRight,
} from 'lucide-react';

interface ValidationChecklistProps {
  validation: SurveyValidationSummary | null;
  isLoading: boolean;
  onRunValidation: () => Promise<void>;
  onSubmitSurvey: () => Promise<void>;
  isSubmitting: boolean;
  disabled?: boolean;
}

export const ValidationChecklist: React.FC<ValidationChecklistProps> = ({
  validation,
  isLoading,
  onRunValidation,
  onSubmitSurvey,
  isSubmitting,
  disabled = false,
}) => {
  return (
    <div className="space-y-6">
      {/* Top Status Banner */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div
              className={`p-2.5 rounded-xl ${
                !validation
                  ? 'bg-slate-800 text-slate-400'
                  : validation.can_submit
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
              }`}
            >
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Cadastral Validation & Quality Engine</h3>
              <p className="text-xs text-slate-400">
                Pre-submission integrity checks against official cadastral records
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onRunValidation}
              disabled={isLoading || disabled}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>{isLoading ? 'Validating...' : 'Re-check Rules'}</span>
            </button>
          </div>
        </div>

        {/* Validation Overview Metrics */}
        {validation ? (
          <div className="mt-4 space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div
                className={`p-3 rounded-xl border flex items-center space-x-3 ${
                  validation.total_errors === 0
                    ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-950/20 border-rose-500/30 text-rose-300'
                }`}
              >
                {validation.total_errors === 0 ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-400" />
                )}
                <div>
                  <div className="text-lg font-bold font-mono leading-none">
                    {validation.total_errors}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">Blocking Errors</div>
                </div>
              </div>

              <div
                className={`p-3 rounded-xl border flex items-center space-x-3 ${
                  validation.total_warnings === 0
                    ? 'bg-slate-950/40 border-slate-800 text-slate-300'
                    : 'bg-amber-950/20 border-amber-500/30 text-amber-300'
                }`}
              >
                <AlertTriangle
                  className={`w-5 h-5 ${
                    validation.total_warnings === 0 ? 'text-slate-500' : 'text-amber-400'
                  }`}
                />
                <div>
                  <div className="text-lg font-bold font-mono leading-none">
                    {validation.total_warnings}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">Advisory Warnings</div>
                </div>
              </div>

              <div
                className={`p-3 rounded-xl border flex items-center space-x-3 ${
                  validation.can_submit
                    ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300'
                    : 'bg-slate-950/40 border-slate-800 text-slate-400'
                }`}
              >
                <ShieldCheck
                  className={`w-5 h-5 ${
                    validation.can_submit ? 'text-emerald-400' : 'text-slate-500'
                  }`}
                />
                <div>
                  <div className="text-xs font-bold leading-none">
                    {validation.can_submit ? 'READY FOR REVIEW' : 'ACTION REQUIRED'}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    {validation.can_submit ? 'Validation Passed' : 'Resolve Errors Below'}
                  </div>
                </div>
              </div>
            </div>

            {/* Checklist Items */}
            <div className="bg-slate-950/50 rounded-xl p-4 border border-slate-800/80 space-y-2.5">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Mandatory Verification Checklist
              </h4>
              {Object.entries(validation.checklist).map(([key, passed]) => {
                const labelMap: Record<string, string> = {
                  has_observations: 'At least one field observation recorded',
                  has_evidence: 'At least one photo evidence record uploaded with SHA-256 hash',
                  gps_accuracy_acceptable: 'GPS coordinates within operational accuracy standards',
                  targets_valid: 'Target entities mapped to official cadastre registry',
                };
                const label = labelMap[key] || key.replace(/_/g, ' ');

                return (
                  <div key={key} className="flex items-center justify-between text-xs py-1">
                    <span className="text-slate-300 flex items-center space-x-2">
                      <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                      <span>{label}</span>
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium flex items-center space-x-1 ${
                        passed
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {passed ? (
                        <>
                          <CheckCircle2 className="w-3 h-3" />
                          <span>PASS</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="w-3 h-3" />
                          <span>FAIL</span>
                        </>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Cadastral Comparisons (Official vs Survey) */}
            {validation.comparisons && validation.comparisons.length > 0 && (
              <div className="bg-slate-950/50 rounded-xl p-4 border border-slate-800/80 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Official Cadastre vs Field Survey Comparison
                  </h4>
                  <span className="text-[10px] text-slate-500">
                    Cadastre is immutable until official officer approval
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 font-mono text-[11px]">
                        <th className="py-2 pr-3">Property</th>
                        <th className="py-2 px-3">Official Record</th>
                        <th className="py-2 px-3">Survey Measurement</th>
                        <th className="py-2 px-3">Difference</th>
                        <th className="py-2 pl-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                      {validation.comparisons.map((comp, idx) => {
                        const isMatch = comp.status === 'MATCH';
                        const isWarn = comp.status === 'DISCREPANCY';
                        return (
                          <tr key={idx} className="hover:bg-slate-800/30">
                            <td className="py-2 pr-3 text-slate-300 font-sans font-medium">
                              {comp.property}
                            </td>
                            <td className="py-2 px-3 text-slate-400">{comp.official_value}</td>
                            <td className="py-2 px-3 text-sky-300 font-bold">
                              {comp.survey_value}
                            </td>
                            <td className="py-2 px-3 text-slate-400">{comp.difference}</td>
                            <td className="py-2 pl-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  isMatch
                                    ? 'bg-emerald-500/10 text-emerald-400'
                                    : isWarn
                                    ? 'bg-amber-500/10 text-amber-400'
                                    : 'bg-slate-800 text-slate-300'
                                }`}
                              >
                                {comp.status}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Validation Issues / Alerts */}
            {validation.issues && validation.issues.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Detailed Findings & Advisories
                </h4>
                <div className="space-y-2">
                  {validation.issues.map((issue, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border text-xs flex items-start space-x-2.5 ${
                        issue.severity === 'ERROR'
                          ? 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                          : issue.severity === 'WARNING'
                          ? 'bg-amber-500/10 border-amber-500/20 text-amber-300'
                          : 'bg-sky-500/10 border-sky-500/20 text-sky-300'
                      }`}
                    >
                      {issue.severity === 'ERROR' ? (
                        <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      ) : issue.severity === 'WARNING' ? (
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                      ) : (
                        <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      )}
                      <div>
                        <div className="font-semibold">{issue.code}</div>
                        <div className="text-slate-300 mt-0.5">{issue.message}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-slate-500">
            Click "Re-check Rules" to evaluate session data quality against cadastral validation rules.
          </div>
        )}

        {/* Submit Action */}
        <div className="pt-5 mt-5 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-400">
            {validation?.can_submit
              ? 'Survey meets all requirements. Ready to submit to municipal cadastral review queue.'
              : 'Review blocking errors before submitting to official review queue.'}
          </p>

          <button
            type="button"
            onClick={onSubmitSurvey}
            disabled={!validation?.can_submit || isSubmitting || disabled}
            className="w-full sm:w-auto px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 shadow-lg shadow-emerald-600/20 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
            <span>{isSubmitting ? 'Submitting to Cadastre...' : 'Submit for Officer Review'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
