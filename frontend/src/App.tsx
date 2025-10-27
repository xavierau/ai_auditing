/**
 * GenReport - Component Demo Page
 *
 * Showcases Phase 4 and Phase 5 components for verification.
 */

import { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { CSRFService } from '@/services/csrf';
import {
  JurisdictionBadge,
  StatusBadge,
  ConfidenceScore,
  ConfidenceBar,
  ProjectCard,
  ProjectCardSkeleton,
  FileUpload,
  ProjectList,
  ReportSection,
  ReportComparison,
  Navigation,
  ProtectedRoute,
  type ProjectData,
  type Status,
  type ReportSectionData,
  type ComparisonData,
} from '@/components';
import { DashboardView } from '@/components/dashboard/DashboardView';
import { ProjectDetailPage } from '@/pages/ProjectDetailPage';
import { ReportDetailPage } from '@/pages/ReportDetailPage';
import { useAuth } from '@/contexts/AuthContext';

function App() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Initialize CSRF protection on app mount
  useEffect(() => {
    // Initialize CSRF service (will attempt to fetch token from backend)
    CSRFService.initialize('/api/v1/csrf-token').catch((error) => {
      console.warn('CSRF initialization failed, continuing without token:', error);
    });
  }, []);

  // Sample project data for demonstration
  const sampleProjects: ProjectData[] = [
    {
      id: 1,
      project_name: 'ABC Holdings Limited - Annual Audit 2024',
      client_name: 'ABC Holdings Limited',
      jurisdiction: 'HK',
      currency: 'HKD',
      financial_year_end: new Date('2024-12-31'),
      status: 'processing' as Status,
      revenue: 15000000,
      created_at: new Date('2024-09-15'),
    },
    {
      id: 2,
      project_name: 'Singapore Tech Pte Ltd - Q3 Review',
      client_name: 'Singapore Tech Pte Ltd',
      jurisdiction: 'SG',
      currency: 'SGD',
      status: 'review' as Status,
      revenue: 8500000,
      created_at: new Date('2024-10-01'),
      financial_year_end: new Date('2024-09-30'),
    },
    {
      id: 3,
      project_name: 'Melbourne Retail Pty - Year End Audit',
      client_name: 'Melbourne Retail Pty',
      jurisdiction: 'AU',
      currency: 'AUD',
      status: 'approved' as Status,
      revenue: 12000000,
      created_at: new Date('2024-08-20'),
      financial_year_end: new Date('2025-06-30'),
    },
    {
      id: 4,
      project_name: 'Kowloon Manufacturing Co - Interim Report',
      client_name: 'Kowloon Manufacturing Co',
      jurisdiction: 'HK',
      currency: 'HKD',
      status: 'draft' as Status,
      revenue: 6200000,
      created_at: new Date('2024-10-15'),
      financial_year_end: new Date('2024-12-31'),
    },
  ];

  // Sample report section
  const sampleSection: ReportSectionData = {
    id: 'revenue-recognition',
    title: 'Revenue Recognition',
    content: `
      <p>The Company recognizes revenue when control of goods or services is transferred to customers. Revenue from product sales is recognized at the point of delivery.</p>
      <p>For the year ended 31 December 2024, total revenue amounted to <strong>HK$15,000,000</strong> (2023: HK$12,500,000), representing an increase of 20% year-over-year.</p>
      <ul>
        <li>Product sales: HK$12,000,000</li>
        <li>Service revenue: HK$3,000,000</li>
      </ul>
    `,
    confidence_score: 92,
    source_references: [
      {
        id: 'ref-1',
        text: 'Total Revenue: 15,000,000',
        worksheet: 'Trial Balance',
        cell_reference: 'B45',
      },
      {
        id: 'ref-2',
        text: 'Product Sales: 12,000,000',
        worksheet: 'Revenue Analysis',
        cell_reference: 'C12',
      },
    ],
    status: 'generated',
    accounting_standard: 'HKFRS 15',
  };

  // Sample comparison data
  const sampleComparison: ComparisonData = {
    sectionTitle: 'Revenue Recognition',
    generated: {
      content: `<p>The Company recognizes revenue in accordance with HKFRS 15. Revenue from product sales is recognized when control transfers to customers, typically at delivery.</p><p>Total revenue for FY2024: <strong>HK$15,000,000</strong></p>`,
      confidence_score: 92,
      sources_count: 2,
    },
    manual: {
      content: `<p>Revenue is recognized when the Company satisfies performance obligations by transferring promised goods or services to customers.</p><p>Total revenue: <strong>HK$15,000,000</strong></p>`,
      author: 'John Audit',
      edited_at: new Date().toISOString(),
    },
  };

  const handleFileSelect = (file: File) => {
    console.log('File selected:', file.name);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation - only show if authenticated */}
      {user && (
        <Navigation
          currentUser={{
            name: user.name,
            email: user.email,
            tenant_name: user.tenant_name,
            jurisdiction: user.jurisdiction as 'HK' | 'SG' | 'AU',
          }}
          onNavigate={(path) => navigate(path)}
          onLogout={logout}
        />
      )}

      {/* View Switcher */}
      <div className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-8">
          <div className="flex gap-4">
            <button
              onClick={() => navigate('/components')}
              className={`border-b-2 px-4 py-3 text-sm font-medium ${
                location.pathname === '/components'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-900'
              }`}
            >
              Phase 4: Core Components
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className={`border-b-2 px-4 py-3 text-sm font-medium ${
                location.pathname === '/dashboard' || location.pathname.startsWith('/projects/')
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-900'
              }`}
            >
              Phase 5: Dashboard
            </button>
            <button
              onClick={() => navigate('/report')}
              className={`border-b-2 px-4 py-3 text-sm font-medium ${
                location.pathname === '/report'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-900'
              }`}
            >
              Phase 5: Report Review
            </button>
          </div>
        </div>
      </div>

      {/* Routes */}
      <Routes>
        {/* Redirect root to dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Components demo page */}
        <Route path="/components" element={(
        <div className="p-8">
          <div className="mx-auto max-w-7xl space-y-12">
            {/* Header */}
            <div className="text-center">
              <h1 className="text-4xl font-bold text-gray-900">GenReport UI Components</h1>
              <p className="mt-2 text-lg text-gray-600">Phase 4 - Core Components Demo</p>
            </div>

        {/* Jurisdiction Badges */}
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Jurisdiction Badges</h2>
          <div className="flex flex-wrap gap-4">
            <div>
              <p className="text-sm text-gray-600 mb-2">Short Form</p>
              <div className="flex gap-2">
                <JurisdictionBadge jurisdiction="HK" />
                <JurisdictionBadge jurisdiction="SG" />
                <JurisdictionBadge jurisdiction="AU" />
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-2">Full Name</p>
              <div className="flex gap-2">
                <JurisdictionBadge jurisdiction="HK" showFullName />
                <JurisdictionBadge jurisdiction="SG" showFullName />
                <JurisdictionBadge jurisdiction="AU" showFullName />
              </div>
            </div>
          </div>
        </section>

        {/* Status Badges */}
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Status Badges</h2>
          <div className="flex flex-wrap gap-3">
            <StatusBadge status="draft" />
            <StatusBadge status="processing" />
            <StatusBadge status="review" />
            <StatusBadge status="approved" />
            <StatusBadge status="completed" />
            <StatusBadge status="failed" />
          </div>
        </section>

        {/* Confidence Scores */}
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Confidence Scores</h2>

          <div className="space-y-6">
            <div>
              <p className="text-sm text-gray-600 mb-2">Score Badges</p>
              <div className="flex flex-wrap gap-3">
                <ConfidenceScore score={95} />
                <ConfidenceScore score={75} />
                <ConfidenceScore score={45} />
              </div>
            </div>

            <div>
              <p className="text-sm text-gray-600 mb-2">Size Variants</p>
              <div className="flex flex-wrap items-center gap-3">
                <ConfidenceScore score={85} size="sm" />
                <ConfidenceScore score={85} size="md" />
                <ConfidenceScore score={85} size="lg" />
              </div>
            </div>

            <div>
              <p className="text-sm text-gray-600 mb-2">Progress Bars</p>
              <div className="space-y-4 max-w-md">
                <ConfidenceBar score={95} />
                <ConfidenceBar score={75} />
                <ConfidenceBar score={45} />
                <ConfidenceBar score={65} showLabel={false} />
              </div>
            </div>
          </div>
        </section>

        {/* Project Cards */}
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Project Cards</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <ProjectCard
              project={sampleProjects[0]}
              onClick={(p) => console.log('Clicked project:', p.id)}
            />
            <ProjectCard
              project={sampleProjects[1]}
              onClick={(p) => console.log('Clicked project:', p.id)}
            />
            <ProjectCard
              project={sampleProjects[2]}
              onClick={(p) => console.log('Clicked project:', p.id)}
            />
            <ProjectCardSkeleton />
          </div>
        </section>

        {/* File Upload */}
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">File Upload</h2>

          <div className="max-w-2xl">
            <FileUpload
              onFileSelect={handleFileSelect}
              accept=".xlsx"
              maxSize={50 * 1024 * 1024}
            />
          </div>
        </section>

            {/* Footer */}
            <footer className="text-center text-sm text-gray-500 pt-8 border-t">
              <p>GenReport UI Components - Built with React + TypeScript + Tailwind CSS v4</p>
            </footer>
          </div>
        </div>
      )} />

        {/* Dashboard */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardView />
            </ProtectedRoute>
          }
        />

        {/* Project Detail */}
        <Route
          path="/projects/:projectId"
          element={
            <ProtectedRoute>
              <ProjectDetailPage />
            </ProtectedRoute>
          }
        />

        {/* Report Detail */}
        <Route
          path="/reports/:reportId"
          element={
            <ProtectedRoute>
              <ReportDetailPage />
            </ProtectedRoute>
          }
        />

        {/* Report Review */}
        <Route
          path="/report"
          element={
            <ProtectedRoute>
              <div className="p-8">
                <div className="mx-auto max-w-7xl space-y-8">
                  <h1 className="text-3xl font-bold text-gray-900">Report Review</h1>

                  {/* Report Section */}
                  <ReportSection
                    section={sampleSection}
                    onEdit={(id) => console.log('Edit section:', id)}
                    onApprove={(id) => console.log('Approve section:', id)}
                    onViewSource={(ref) => console.log('View source:', ref)}
                  />

                  {/* Report Comparison */}
                  <ReportComparison
                    comparison={sampleComparison}
                    onAcceptGenerated={() => console.log('Accept AI version')}
                    onEditManual={() => console.log('Edit manual version')}
                    onViewSources={() => console.log('View sources')}
                  />
                </div>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  );
}

export default App;
