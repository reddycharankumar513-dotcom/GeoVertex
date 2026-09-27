import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { DashboardLayout } from './layouts/DashboardLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { ProfilePage } from './pages/ProfilePage';
import { CadastreMapPage } from './pages/gis/CadastreMapPage';
import { DigitalTwin3DPage } from './pages/gis/DigitalTwin3DPage';
import { UsersPage } from './pages/admin/UsersPage';
import { AuditLogsPage } from './pages/admin/AuditLogsPage';
import { SurveyorDashboardPage } from './pages/survey/SurveyorDashboardPage';
import { FieldSurveyPage } from './pages/survey/FieldSurveyPage';
import { OfficerReviewPage } from './pages/survey/OfficerReviewPage';
import { AIJobsDashboardPage } from './pages/ai/AIJobsDashboardPage';
import { AICandidateReviewListPage } from './pages/ai/AICandidateReviewListPage';
import { ValidationDashboardPage } from './pages/validation/ValidationDashboardPage';
import { DocumentListPage } from './pages/document/DocumentListPage';
import { DocumentWorkspacePage } from './pages/document/DocumentWorkspacePage';
import { TemporalIntelligencePage } from './pages/temporal/TemporalIntelligencePage';
import { UndergroundExplorerPage } from './pages/utility/UndergroundExplorerPage';
import { CitizenDashboardPage } from './pages/citizen/CitizenDashboardPage';
import { CitizenPropertyDetailPage } from './pages/citizen/CitizenPropertyDetailPage';
import { CitizenRequestDetailPage } from './pages/citizen/CitizenRequestDetailPage';
import { GovernmentDashboardPage } from './pages/government/GovernmentDashboardPage';
import { GovernmentCaseWorkspacePage } from './pages/government/GovernmentCaseWorkspacePage';
import { GovernmentReviewQueuePage } from './pages/government/GovernmentReviewQueuePage';
import { UnauthorizedPage } from './pages/UnauthorizedPage';
import { NotFoundPage } from './pages/NotFoundPage';
// Phase 12 — Technical 3D Property Identifier Engine
import { IdentifierRegistryPage } from './pages/IdentifierRegistryPage';
import { IdentifierDetailPage } from './pages/IdentifierDetailPage';
import { IdentifierHistoryPage } from './pages/IdentifierHistoryPage';
import { GenerateIdentifierPage } from './pages/GenerateIdentifierPage';
import { BulkGeneratePage } from './pages/BulkGeneratePage';
import { SchemeManagementPage } from './pages/SchemeManagementPage';
import { VerifyIdentifierPage } from './pages/VerifyIdentifierPage';
// Phase 13 — Governance, Versioning & Notifications
import { GovernanceDashboardPage } from './pages/admin/GovernanceDashboardPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { EntityHistoryPage } from './pages/EntityHistoryPage';
import { VersionComparePage } from './pages/VersionComparePage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/unauthorized" element={<UnauthorizedPage />} />

            {/* Protected Application Routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<DashboardLayout />}>
                <Route path="/" element={<Navigate to="/cadastre" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/cadastre" element={<CadastreMapPage />} />
                <Route path="/digital-twin" element={<DigitalTwin3DPage />} />
                <Route path="/profile" element={<ProfilePage />} />

                {/* Phase 5 Field Surveyor Routes */}
                <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR']} />}>
                  <Route path="/surveyor" element={<SurveyorDashboardPage />} />
                  <Route path="/surveyor/field/:assignmentId" element={<FieldSurveyPage />} />
                </Route>

                {/* Phase 6 AI Spatial Intelligence Routes */}
                <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR', 'URBAN_PLANNER']} />}>
                  <Route path="/ai/dashboard" element={<AIJobsDashboardPage />} />
                  <Route path="/ai/reviews" element={<AICandidateReviewListPage />} />
                </Route>

                {/* Phase 7 Topology Validation Routes */}
                <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR', 'URBAN_PLANNER']} />}>
                  <Route path="/validation" element={<ValidationDashboardPage />} />
                </Route>

                {/* Phase 8 AI Document Intelligence Routes */}
                <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR', 'URBAN_PLANNER']} />}>
                  <Route path="/documents" element={<DocumentListPage />} />
                  <Route path="/documents/:id" element={<DocumentWorkspacePage />} />
                </Route>

                {/* Phase 9 AI Change Detection & Temporal Intelligence Routes */}
                <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR', 'URBAN_PLANNER']} />}>
                  <Route path="/temporal" element={<TemporalIntelligencePage />} />
                </Route>

                {/* Phase 10 Underground Infrastructure & Subsurface Utility Intelligence Routes */}
                <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR', 'URBAN_PLANNER']} />}>
                  <Route path="/utilities" element={<UndergroundExplorerPage />} />
                </Route>

                {/* Phase 11 Citizen Portal Routes */}
                <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'CITIZEN', 'GOVERNMENT_OFFICER']} />}>
                  <Route path="/citizen/dashboard" element={<CitizenDashboardPage />} />
                  <Route path="/workflows/properties/:propertyId" element={<CitizenPropertyDetailPage />} />
                  <Route path="/workflows/requests/:id" element={<CitizenRequestDetailPage />} />
                </Route>

                {/* Phase 11 Government Operations Routes */}
                <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'GOVERNMENT_OFFICER', 'URBAN_PLANNER']} />}>
                  <Route path="/government/dashboard" element={<GovernmentDashboardPage />} />
                  <Route path="/government/workspace/:id" element={<GovernmentCaseWorkspacePage />} />
                  <Route path="/government/queues" element={<GovernmentReviewQueuePage />} />
                </Route>

                {/* Administration & Review Routes */}

                <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'GOVERNMENT_OFFICER']} />}>
                  <Route path="/admin/users" element={<UsersPage />} />
                  <Route path="/admin/survey-review" element={<OfficerReviewPage />} />
                  <Route path="/admin/governance" element={<GovernanceDashboardPage />} />
                  <Route path="/admin/audit" element={<AuditLogsPage />} />
                  <Route path="/audit" element={<AuditLogsPage />} />
                </Route>

                {/* Phase 12 — Technical 3D Property Identifier Engine */}
                {/* All authenticated users can view/verify */}
                <Route path="/identifiers" element={<IdentifierRegistryPage />} />
                <Route path="/identifiers/generate" element={<GenerateIdentifierPage />} />
                <Route path="/identifiers/bulk-generate" element={<BulkGeneratePage />} />
                <Route path="/identifiers/schemes" element={<SchemeManagementPage />} />
                <Route path="/identifiers/verify" element={<VerifyIdentifierPage />} />
                <Route path="/identifiers/:id/history" element={<IdentifierHistoryPage />} />
                <Route path="/identifiers/:id" element={<IdentifierDetailPage />} />

                {/* Phase 13 — Governance, Versioning & Notifications */}
                <Route path="/notifications" element={<NotificationsPage />} />
                <Route path="/history/:entityType/:entityId" element={<EntityHistoryPage />} />
                <Route path="/versions/compare" element={<VersionComparePage />} />
                {/* Public verification route (token-based, no auth needed) */}
              </Route>
            </Route>

            {/* Public verification — no auth required */}
            <Route path="/verify/:token" element={<VerifyIdentifierPage />} />

            {/* Catch-all 404 */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};
