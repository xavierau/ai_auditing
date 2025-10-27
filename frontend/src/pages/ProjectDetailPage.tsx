/**
 * ProjectDetailPage Component
 *
 * Displays detailed information about a specific project.
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useRef, useState } from 'react';
import { useProject } from '@/hooks/useProjects';
import { useProjectFiles, useUploadFile, useDeleteFile } from '@/hooks/useFiles';
import { useProjectReports } from '@/hooks/useReports';
import { Button } from '@/components/ui/button';
import { JurisdictionBadge } from '@/components/jurisdiction/JurisdictionBadge';
import { StatusBadge } from '@/components/status/StatusBadge';
import { DateFormatter } from '@/utils/date';
import { CurrencyFormatter } from '@/utils/currency';
import { MarketUtils, type Jurisdiction } from '@/utils/market';
import { ArrowLeft, FileText, Upload, Download, Trash2, Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const { data: project, isLoading, isError, error } = useProject(parseInt(projectId || '0'));
  const { data: files, isLoading: filesLoading } = useProjectFiles(parseInt(projectId || '0'));
  const { data: reports, isLoading: reportsLoading } = useProjectReports(parseInt(projectId || '0'));
  const uploadMutation = useUploadFile();
  const deleteMutation = useDeleteFile();

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="mx-auto max-w-5xl">
          <div className="animate-pulse space-y-6">
            <div className="h-8 w-48 rounded bg-gray-200" />
            <div className="h-64 rounded-lg bg-gray-200" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !project) {
    return (
      <div className="p-8">
        <div className="mx-auto max-w-5xl">
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-red-700">
              Failed to load project. {error?.message || 'Project not found.'}
            </p>
            <Button
              variant="outline"
              onClick={() => navigate('/dashboard')}
              className="mt-4"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const currency = MarketUtils.getCurrency(project.jurisdiction as Jurisdiction);

  // Handle file upload button click
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  // Handle file selection
  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !projectId) return;

    setSelectedFile(file);

    try {
      await uploadMutation.mutateAsync({
        file,
        projectId: parseInt(projectId),
      });

      console.log(`File "${file.name}" uploaded successfully.`);
      alert(`File "${file.name}" uploaded successfully.`);

      setSelectedFile(null);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to upload file.';
      console.error('Upload failed:', message);
      alert(`Upload failed: ${message}`);
    }
  };

  // Handle file deletion
  const handleDeleteFile = async (fileId: string, filename: string) => {
    if (!projectId) return;

    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      await deleteMutation.mutateAsync({
        fileId,
        projectId: parseInt(projectId),
      });

      console.log(`File "${filename}" deleted successfully.`);
      alert(`File "${filename}" deleted successfully.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete file.';
      console.error('Delete failed:', message);
      alert(`Delete failed: ${message}`);
    }
  };

  // Handle generate report
  const handleGenerateReport = async () => {
    if (!projectId) return;

    const confirmed = confirm(
      'This will parse the uploaded Excel file and generate an audit report. This may take a few minutes. Continue?'
    );

    if (!confirmed) return;

    try {
      console.log('Starting report generation...');

      // Step 1: Trigger parsing
      const parseResponse = await fetch(`http://localhost:8000/api/v1/parsing/projects/${projectId}/parse`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('genreport_access_token')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!parseResponse.ok) {
        throw new Error(`Parsing failed: ${parseResponse.statusText}`);
      }

      console.log('Parsing initiated successfully');
      alert('Excel parsing started. This will run in the background. Please wait a moment before generating the report.');

      // Step 2: Wait a bit for parsing (in production, you'd poll for status or use WebSocket)
      await new Promise(resolve => setTimeout(resolve, 3000));

      // Step 3: Trigger report generation
      const reportResponse = await fetch(`http://localhost:8000/api/v1/reports/generate/${projectId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('genreport_access_token')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!reportResponse.ok) {
        const errorData = await reportResponse.json().catch(() => null);
        throw new Error(errorData?.detail || `Report generation failed: ${reportResponse.statusText}`);
      }

      const reportData = await reportResponse.json();
      console.log('Report generated successfully:', reportData);
      alert(`Report generated successfully! Report ID: ${reportData.report_id}\nCompleteness: ${(reportData.overall_completeness * 100).toFixed(1)}%`);

      // TODO: Navigate to report view or refresh page to show report
      // navigate(`/reports/${reportData.report_id}`);

    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to generate report.';
      console.error('Report generation failed:', message);
      alert(`Report generation failed: ${message}`);
    }
  };

  return (
    <div className="p-8">
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => navigate('/dashboard')}
            className="inline-flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Projects
          </Button>

          <div className="flex gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileChange}
              className="hidden"
            />
            <Button
              variant="outline"
              className="inline-flex items-center gap-2"
              onClick={handleUploadClick}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Upload Files
                </>
              )}
            </Button>
            <Button variant="outline" className="inline-flex items-center gap-2">
              <Download className="h-4 w-4" />
              Export
            </Button>
            <Button
              className="inline-flex items-center gap-2"
              onClick={handleGenerateReport}
              disabled={!files || files.length === 0}
            >
              <FileText className="h-4 w-4" />
              Generate Report
            </Button>
          </div>
        </div>

        {/* Project Title */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {project.project_name || 'Untitled Project'}
          </h1>
          <div className="mt-2 flex items-center gap-3">
            <JurisdictionBadge jurisdiction={project.jurisdiction as Jurisdiction} showFullName />
            <StatusBadge status={project.status} />
          </div>
        </div>

        {/* Project Information Card */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Project Information</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <p className="text-sm font-medium text-gray-600">Client</p>
              <p className="mt-1 text-base text-gray-900">{project.client_name || 'N/A'}</p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-600">Accounting Standard</p>
              <p className="mt-1 text-base text-gray-900">{project.accounting_standard}</p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-600">Financial Year End</p>
              <p className="mt-1 font-mono text-base text-gray-900">
                {DateFormatter.formatByJurisdiction(
                  project.financial_year_end,
                  project.jurisdiction as Jurisdiction
                )}
              </p>
            </div>

            {project.revenue !== undefined && (
              <div>
                <p className="text-sm font-medium text-gray-600">Revenue</p>
                <p className="mt-1 font-mono text-base text-gray-900 tabular-nums">
                  {CurrencyFormatter.format(project.revenue, currency)}
                </p>
              </div>
            )}

            {project.created_at && (
              <div>
                <p className="text-sm font-medium text-gray-600">Created</p>
                <p className="mt-1 text-base text-gray-900">
                  {DateFormatter.formatByJurisdiction(
                    project.created_at,
                    project.jurisdiction as Jurisdiction
                  )}
                </p>
              </div>
            )}

            {project.updated_at && (
              <div>
                <p className="text-sm font-medium text-gray-600">Last Updated</p>
                <p className="mt-1 text-base text-gray-900">
                  {DateFormatter.formatRelative(
                    project.updated_at,
                    project.jurisdiction as Jurisdiction
                  )}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Uploaded Files */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Uploaded Files</h2>

          {filesLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : files && files.length > 0 ? (
            <div className="space-y-3">
              {files.map((file) => (
                <div
                  key={file.file_id}
                  className="flex items-center justify-between rounded-lg border border-gray-200 p-4 hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{file.filename}</p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024 / 1024).toFixed(2)} MB •{' '}
                        {DateFormatter.formatByJurisdiction(
                          file.uploaded_at,
                          project.jurisdiction as Jurisdiction
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="inline-flex items-center gap-2"
                      onClick={() => {
                        const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                        window.open(`${baseURL}/api/v1/files/${file.file_id}`, '_blank');
                      }}
                    >
                      <Download className="h-4 w-4" />
                      Download
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="inline-flex items-center gap-2 text-red-600 hover:text-red-700"
                      onClick={() => handleDeleteFile(file.file_id, file.filename)}
                      disabled={deleteMutation.isPending}
                    >
                      {deleteMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                      Delete
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-600">No files uploaded yet.</p>
          )}
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Generated Reports</h2>

          {reportsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : reports && reports.length > 0 ? (
            <div className="space-y-3">
              {reports.map((report) => (
                <div
                  key={report.id}
                  className="flex items-center justify-between rounded-lg border border-gray-200 p-4 hover:bg-gray-50"
                >
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-3">
                      <p className="text-sm font-medium text-gray-900">
                        Report #{report.id}
                      </p>
                      {report.status === 'completed' && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-success-50 px-2 py-1 text-xs font-medium text-success-700">
                          <CheckCircle2 className="h-3 w-3" />
                          Completed
                        </span>
                      )}
                      {report.status === 'failed' && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-error-50 px-2 py-1 text-xs font-medium text-error-700">
                          <XCircle className="h-3 w-3" />
                          Failed
                        </span>
                      )}
                      {report.status === 'processing' && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-warning-50 px-2 py-1 text-xs font-medium text-warning-700">
                          <Clock className="h-3 w-3" />
                          Processing
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-gray-600">
                      <div>
                        <span className="font-medium">Completeness:</span>{' '}
                        <span className="font-mono tabular-nums">
                          {report.overall_completeness != null
                            ? `${(report.overall_completeness * 100).toFixed(1)}%`
                            : 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="font-medium">Time:</span>{' '}
                        <span className="font-mono tabular-nums">
                          {report.generation_time_seconds != null
                            ? `${report.generation_time_seconds.toFixed(1)}s`
                            : 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="font-medium">Cost:</span>{' '}
                        <span className="font-mono tabular-nums">
                          {report.cost_usd != null
                            ? `$${report.cost_usd.toFixed(2)}`
                            : 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="font-medium">Created:</span>{' '}
                        {DateFormatter.formatByJurisdiction(
                          report.created_at,
                          project.jurisdiction as Jurisdiction
                        )}
                      </div>
                    </div>

                    {report.sections && report.sections.length > 0 && (
                      <div className="text-xs text-gray-500">
                        {report.sections.length} section{report.sections.length !== 1 ? 's' : ''} generated
                      </div>
                    )}

                    {report.error_message && (
                      <div className="text-xs text-error-600 mt-2">
                        Error: {report.error_message}
                      </div>
                    )}
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    className="inline-flex items-center gap-2"
                    onClick={() => navigate(`/reports/${report.id}`)}
                  >
                    <FileText className="h-4 w-4" />
                    View Details
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-600">No reports generated yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
