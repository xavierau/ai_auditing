/**
 * ReportDetailPage Component
 *
 * Displays the full details of a generated report including all sections.
 */

import { useParams, useNavigate } from 'react-router-dom';
import React, { useMemo } from 'react';
import { marked } from 'marked';
import { useReport } from '@/hooks/useReports';
import { Button } from '@/components/ui/button';
import { JurisdictionBadge } from '@/components/jurisdiction/JurisdictionBadge';
import { DateFormatter } from '@/utils/date';
import { type Jurisdiction } from '@/utils/market';
import { SanitizerService } from '@/services/sanitizer';
import {
  ArrowLeft,
  FileText,
  Download,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  Eye,
  Code,
  ChevronDown,
  ChevronUp,
  Database,
} from 'lucide-react';

/**
 * SectionContent - Renders markdown content as sanitized HTML with raw view toggle
 */
function SectionContent({ content }: { content: string }) {
  const [showRaw, setShowRaw] = React.useState(false);

  const htmlContent = useMemo(() => {
    // Parse markdown to HTML
    const html = marked.parse(content, { async: false }) as string;

    // Sanitize HTML to prevent XSS attacks
    return SanitizerService.sanitizeRichText(html);
  }, [content]);

  return (
    <div>
      {/* Toggle Button */}
      <div className="mb-4 flex justify-end">
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          {showRaw ? (
            <>
              <Eye className="h-4 w-4" />
              Show Rendered
            </>
          ) : (
            <>
              <Code className="h-4 w-4" />
              Show Raw Markdown
            </>
          )}
        </button>
      </div>

      {/* Content Display */}
      {showRaw ? (
        <pre className="rounded-md border border-gray-300 bg-gray-50 p-4 text-sm text-gray-900 overflow-x-auto whitespace-pre-wrap font-mono">
          {content}
        </pre>
      ) : (
        <div
          className="prose prose-sm max-w-none text-gray-900"
          dangerouslySetInnerHTML={{ __html: htmlContent }}
        />
      )}
    </div>
  );
}

/**
 * RawDataSection - Displays document parsing and worksheet analysis data
 */
function RawDataSection({ rawData }: { rawData: any }) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [expandedWorksheets, setExpandedWorksheets] = React.useState<Set<number>>(new Set());
  const [expandedMaps, setExpandedMaps] = React.useState<Set<number>>(new Set());

  if (!rawData) return null;

  const toggleWorksheet = (id: number) => {
    setExpandedWorksheets(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleMap = (id: number) => {
    setExpandedMaps(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-6 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Database className="h-5 w-5 text-gray-600" />
          <h2 className="text-xl font-semibold text-gray-900">Raw Document Data</h2>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-5 w-5 text-gray-600" />
        ) : (
          <ChevronDown className="h-5 w-5 text-gray-600" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-6 space-y-6">
          {/* File Metadata */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">File Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 rounded-md border border-gray-200 bg-gray-50 p-4">
              <div>
                <p className="text-sm font-medium text-gray-600">Filename</p>
                <p className="mt-1 text-sm text-gray-900">{rawData.original_filename}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">File Size</p>
                <p className="mt-1 font-mono text-sm text-gray-900 tabular-nums">
                  {(rawData.file_size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Parsing Status</p>
                <p className={`mt-1 text-sm font-medium ${
                  rawData.parsing_status === 'completed' ? 'text-success-700' :
                  rawData.parsing_status === 'failed' ? 'text-error-700' :
                  'text-warning-700'
                }`}>
                  {rawData.parsing_status}
                </p>
              </div>
              {rawData.parsing_error && (
                <div className="col-span-full">
                  <p className="text-sm font-medium text-gray-600">Parsing Error</p>
                  <p className="mt-1 text-sm text-error-700">{rawData.parsing_error}</p>
                </div>
              )}
            </div>
          </div>

          {/* Worksheet Analyses */}
          {rawData.worksheet_analyses && rawData.worksheet_analyses.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Worksheet Analyses ({rawData.worksheet_analyses.length})
              </h3>
              <div className="space-y-3">
                {rawData.worksheet_analyses.map((worksheet: any) => (
                  <div key={worksheet.id} className="rounded-md border border-gray-200 bg-white">
                    <button
                      onClick={() => toggleWorksheet(worksheet.id)}
                      className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <p className="font-medium text-gray-900">{worksheet.worksheet_name}</p>
                          {worksheet.is_summary && (
                            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
                              Summary
                            </span>
                          )}
                          {worksheet.is_supporting && (
                            <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700 ring-1 ring-inset ring-gray-700/10">
                              Supporting
                            </span>
                          )}
                        </div>
                        {worksheet.importance_score !== null && (
                          <p className="mt-1 text-sm text-gray-600">
                            Importance: <span className="font-mono tabular-nums">{(worksheet.importance_score * 100).toFixed(0)}%</span>
                          </p>
                        )}
                      </div>
                      {expandedWorksheets.has(worksheet.id) ? (
                        <ChevronUp className="h-4 w-4 text-gray-600" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-gray-600" />
                      )}
                    </button>

                    {expandedWorksheets.has(worksheet.id) && (
                      <div className="border-t border-gray-200 p-4 bg-gray-50 space-y-3">
                        {worksheet.summary && (
                          <div>
                            <p className="text-sm font-medium text-gray-700 mb-2">Summary:</p>
                            <p className="text-sm text-gray-900 leading-relaxed rounded-md border border-gray-300 bg-white p-3">
                              {worksheet.summary}
                            </p>
                          </div>
                        )}
                        {worksheet.referenced_codes && worksheet.referenced_codes.length > 0 && (
                          <div>
                            <p className="text-sm font-medium text-gray-700 mb-2">Referenced Codes:</p>
                            <div className="flex flex-wrap gap-2">
                              {worksheet.referenced_codes.map((code: string, idx: number) => (
                                <span key={idx} className="inline-flex items-center rounded-md bg-white border border-gray-300 px-2.5 py-0.5 text-xs font-mono text-gray-700">
                                  {code}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {worksheet.analysis_metadata && (
                          <div>
                            <p className="text-sm font-medium text-gray-700 mb-2">Analysis Metadata:</p>
                            <pre className="rounded-md border border-gray-300 bg-white p-3 text-xs text-gray-900 overflow-x-auto whitespace-pre-wrap font-mono">
                              {JSON.stringify(worksheet.analysis_metadata, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Relationship Maps */}
          {rawData.relationship_maps && rawData.relationship_maps.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Relationship Maps ({rawData.relationship_maps.length})
              </h3>
              <div className="space-y-3">
                {rawData.relationship_maps.map((map: any) => (
                  <div key={map.id} className="rounded-md border border-gray-200 bg-white">
                    <button
                      onClick={() => toggleMap(map.id)}
                      className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">
                          Coding System: {map.coding_system || 'Not specified'}
                        </p>
                        {map.confidence_score !== null && (
                          <p className="mt-1 text-sm text-gray-600">
                            Confidence: <span className="font-mono tabular-nums">{(map.confidence_score * 100).toFixed(0)}%</span>
                          </p>
                        )}
                      </div>
                      {expandedMaps.has(map.id) ? (
                        <ChevronUp className="h-4 w-4 text-gray-600" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-gray-600" />
                      )}
                    </button>

                    {expandedMaps.has(map.id) && (
                      <div className="border-t border-gray-200 p-4 bg-gray-50 space-y-3">
                        {map.recommended_sheets && map.recommended_sheets.length > 0 && (
                          <div>
                            <p className="text-sm font-medium text-gray-700 mb-2">Recommended Sheets:</p>
                            <div className="flex flex-wrap gap-2">
                              {map.recommended_sheets.map((sheet: string, idx: number) => (
                                <span key={idx} className="inline-flex items-center rounded-md bg-white border border-gray-300 px-2.5 py-0.5 text-xs font-mono text-gray-700">
                                  {sheet}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {map.code_families && (
                          <div>
                            <p className="text-sm font-medium text-gray-700 mb-2">Code Families:</p>
                            <pre className="rounded-md border border-gray-300 bg-white p-3 text-xs text-gray-900 overflow-x-auto whitespace-pre-wrap font-mono">
                              {JSON.stringify(map.code_families, null, 2)}
                            </pre>
                          </div>
                        )}
                        {map.relationships && (
                          <div>
                            <p className="text-sm font-medium text-gray-700 mb-2">Relationships:</p>
                            <pre className="rounded-md border border-gray-300 bg-white p-3 text-xs text-gray-900 overflow-x-auto whitespace-pre-wrap font-mono">
                              {JSON.stringify(map.relationships, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();

  const { data: report, isLoading, isError, error } = useReport(parseInt(reportId || '0'));

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

  if (isError || !report) {
    return (
      <div className="p-8">
        <div className="mx-auto max-w-5xl">
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-red-700">
              Failed to load report. {error?.message || 'Report not found.'}
            </p>
            <Button
              variant="outline"
              onClick={() => navigate(-1)}
              className="mt-4"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Go Back
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>

          <Button variant="outline" className="inline-flex items-center gap-2">
            <Download className="h-4 w-4" />
            Export Report
          </Button>
        </div>

        {/* Report Title */}
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">
              Report #{report.id}
            </h1>
            {report.status === 'completed' && (
              <span className="inline-flex items-center gap-1 rounded-full bg-success-50 px-3 py-1 text-sm font-medium text-success-700">
                <CheckCircle2 className="h-4 w-4" />
                Completed
              </span>
            )}
            {report.status === 'failed' && (
              <span className="inline-flex items-center gap-1 rounded-full bg-error-50 px-3 py-1 text-sm font-medium text-error-700">
                <XCircle className="h-4 w-4" />
                Failed
              </span>
            )}
            {report.status === 'processing' && (
              <span className="inline-flex items-center gap-1 rounded-full bg-warning-50 px-3 py-1 text-sm font-medium text-warning-700">
                <Clock className="h-4 w-4" />
                Processing
              </span>
            )}
          </div>
          <div className="mt-2">
            <JurisdictionBadge
              jurisdiction={report.jurisdiction as Jurisdiction}
              showFullName
            />
          </div>
        </div>

        {/* Report Metadata */}
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Report Information</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <p className="text-sm font-medium text-gray-600">Accounting Standard</p>
              <p className="mt-1 text-base text-gray-900">{report.accounting_standard}</p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-600">Overall Completeness</p>
              <p className="mt-1 font-mono text-base text-gray-900 tabular-nums">
                {report.overall_completeness != null
                  ? `${(report.overall_completeness * 100).toFixed(1)}%`
                  : 'N/A'}
              </p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-600">Generation Time</p>
              <p className="mt-1 font-mono text-base text-gray-900 tabular-nums">
                {report.generation_time_seconds != null
                  ? `${report.generation_time_seconds.toFixed(1)}s`
                  : 'N/A'}
              </p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-600">Cost</p>
              <p className="mt-1 font-mono text-base text-gray-900 tabular-nums">
                {report.cost_usd != null
                  ? `$${report.cost_usd.toFixed(2)}`
                  : 'N/A'}
              </p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-600">Created</p>
              <p className="mt-1 text-base text-gray-900">
                {DateFormatter.formatByJurisdiction(
                  report.created_at,
                  report.jurisdiction as Jurisdiction
                )}
              </p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-600">Sections Generated</p>
              <p className="mt-1 text-base text-gray-900">
                {report.sections?.length || 0} section{report.sections?.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>

          {report.error_message && (
            <div className="mt-6 rounded-md border border-error-200 bg-error-50 p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-error-700 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-error-900">Error</p>
                  <p className="mt-1 text-sm text-error-700">{report.error_message}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Raw Document Data */}
        <RawDataSection rawData={report.raw_data} />

        {/* Report Sections */}
        <div className="space-y-6">
          <h2 className="text-2xl font-semibold text-gray-900">Report Sections</h2>

          {report.sections && report.sections.length > 0 ? (
            report.sections.map((section) => (
              <div
                key={section.id}
                className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
              >
                {/* Section Header */}
                <div className="mb-4 border-b border-gray-200 pb-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-xl font-semibold text-gray-900">
                        {section.section_name}
                      </h3>
                      <p className="mt-1 text-sm text-gray-600">
                        Agent: {section.agent_name} • Standard: {section.standard_used}
                      </p>
                    </div>
                    {section.confidence_score !== undefined && section.confidence_score !== null && (
                      <div className="ml-4">
                        <div
                          className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${
                            section.confidence_score >= 80
                              ? 'bg-success-50 text-success-700'
                              : section.confidence_score >= 60
                              ? 'bg-warning-50 text-warning-700'
                              : 'bg-error-50 text-error-700'
                          }`}
                        >
                          Confidence: {section.confidence_score.toFixed(0)}%
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Metrics */}
                  <div className="mt-3 flex flex-wrap gap-4 text-sm text-gray-600">
                    {section.completeness_score !== undefined && section.completeness_score !== null && (
                      <span>
                        <span className="font-medium">Completeness:</span>{' '}
                        <span className="font-mono tabular-nums">
                          {(section.completeness_score * 100).toFixed(1)}%
                        </span>
                      </span>
                    )}
                    <span>
                      <span className="font-medium">Sources:</span>{' '}
                      {section.source_references?.length || 0}
                    </span>
                    {section.pii_detected && (
                      <span className="text-warning-700">
                        <AlertCircle className="inline h-4 w-4 mr-1" />
                        PII Detected
                      </span>
                    )}
                  </div>

                  {/* Warnings */}
                  {section.warnings && section.warnings.length > 0 && (
                    <div className="mt-3 rounded-md border border-warning-200 bg-warning-50 p-3">
                      <p className="text-sm font-medium text-warning-900">Warnings:</p>
                      <ul className="mt-1 list-disc list-inside text-sm text-warning-700">
                        {section.warnings.map((warning, idx) => (
                          <li key={idx}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Section Content */}
                <SectionContent content={section.content} />

                {/* Source References */}
                {section.source_references && section.source_references.length > 0 && (
                  <div className="mt-6 border-t border-gray-200 pt-4">
                    <p className="text-sm font-medium text-gray-900 mb-3">
                      Source References ({section.source_references.length})
                    </p>
                    <div className="space-y-2">
                      {section.source_references.map((ref, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm"
                        >
                          <span className="text-gray-700">
                            KB Chunk #{ref.kb_chunk_id}
                          </span>
                          <span className="font-mono text-gray-600">
                            Similarity: {(ref.similarity_score * 100).toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-3 text-gray-600">No sections available for this report.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
