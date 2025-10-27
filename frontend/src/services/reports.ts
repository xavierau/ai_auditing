/**
 * Reports Service
 *
 * API service for fetching and managing generated reports.
 */

import { apiClient } from './api';

/**
 * Generated report response from API
 */
export interface GeneratedReport {
  id: number;
  tenant_id: string;
  project_id: number;
  generated_by: number;
  jurisdiction: string;
  accounting_standard: string;
  overall_completeness: number | null;
  generation_time_seconds: number | null;
  cost_usd: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
  sections: ReportSection[];
  raw_data: FileMetadata | null;
}

export interface ReportSection {
  id: number;
  section_name: string;
  agent_name: string;
  content: string;
  standard_used: string;
  confidence_score: number | null;
  completeness_score: number | null;
  required_disclosures_met: Record<string, unknown> | null;
  warnings: string[];
  pii_detected: boolean;
  pii_types: Record<string, unknown> | null;
  source_references: SourceReference[];
}

export interface SourceReference {
  kb_chunk_id: number;
  similarity_score: number;
}

export interface WorksheetAnalysis {
  id: number;
  worksheet_name: string;
  is_summary: boolean;
  is_supporting: boolean;
  referenced_codes: string[] | null;
  importance_score: number | null;
  summary: string | null;  // LLM-generated worksheet summary
  analysis_metadata: Record<string, unknown> | null;
}

export interface RelationshipMap {
  id: number;
  coding_system: string | null;
  code_families: Record<string, unknown> | null;
  relationships: Record<string, unknown> | null;
  recommended_sheets: string[] | null;
  confidence_score: number | null;
}

export interface FileMetadata {
  id: string;
  original_filename: string;
  file_size: number;
  mime_type: string | null;
  parsing_status: string;
  parsing_error: string | null;
  created_at: string;
  worksheet_analyses: WorksheetAnalysis[];
  relationship_maps: RelationshipMap[];
}

/**
 * List reports for a project
 *
 * @param projectId - ID of project
 * @returns List of generated reports
 */
export async function listProjectReports(
  projectId: number
): Promise<GeneratedReport[]> {
  return apiClient.get(`/api/v1/reports/project/${projectId}`);
}

/**
 * Get a single report by ID
 *
 * @param reportId - ID of report
 * @returns Report details
 */
export async function getReport(reportId: number): Promise<GeneratedReport> {
  return apiClient.get(`/api/v1/reports/${reportId}`);
}
