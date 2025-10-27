/**
 * Projects API Service
 *
 * API functions for project management endpoints.
 */

import { apiClient } from './api';
import type { ProjectData } from '@/components';
import type { Jurisdiction } from '@/utils/market';
import type { Currency } from '@/utils/currency';
import type { Status } from '@/components/status/StatusBadge';

/**
 * API response types
 */
export interface ProjectListResponse {
  projects: ProjectData[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProjectDetailResponse extends ProjectData {
  description?: string;
  entity_type?: string;
  auditor_name?: string;
  files?: FileInfo[];
}

export interface FileInfo {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  uploaded_at: string;
}

export interface CreateProjectRequest {
  project_name: string;
  client_id: number;
  jurisdiction: Jurisdiction;
  currency: Currency;
  financial_year_end: string; // ISO date string
  entity_type?: string;
  description?: string;
}

export interface UpdateProjectRequest {
  project_name?: string;
  client_id?: number;
  jurisdiction?: Jurisdiction;
  currency?: Currency;
  financial_year_end?: string;
  entity_type?: string;
  description?: string;
  status?: Status;
}

export interface ProjectFilters {
  jurisdiction?: Jurisdiction;
  status?: Status;
  search?: string;
  page?: number;
  page_size?: number;
}

/**
 * ProjectsAPI - CRUD operations for projects
 */
export class ProjectsAPI {
  /**
   * Get all projects with optional filters
   *
   * @example
   * const projects = await ProjectsAPI.list({ jurisdiction: 'HK', status: 'draft' })
   */
  static async list(filters?: ProjectFilters): Promise<ProjectListResponse> {
    const params: Record<string, string | number> = {};

    if (filters?.jurisdiction) params.jurisdiction = filters.jurisdiction;
    if (filters?.status) params.status = filters.status;
    if (filters?.search) params.search = filters.search;
    if (filters?.page) params.page = filters.page;
    if (filters?.page_size) params.page_size = filters.page_size;

    return apiClient.get<ProjectListResponse>('/api/v1/projects', { params });
  }

  /**
   * Get single project by ID
   *
   * @example
   * const project = await ProjectsAPI.get(123)
   */
  static async get(id: number): Promise<ProjectDetailResponse> {
    return apiClient.get<ProjectDetailResponse>(`/api/v1/projects/${id}`);
  }

  /**
   * Create new project
   *
   * @example
   * const project = await ProjectsAPI.create({
   *   project_name: 'ABC Holdings - Annual Audit 2024',
   *   client_id: 5,
   *   jurisdiction: 'HK',
   *   currency: 'HKD',
   *   financial_year_end: '2024-12-31',
   * })
   */
  static async create(data: CreateProjectRequest): Promise<ProjectDetailResponse> {
    return apiClient.post<ProjectDetailResponse>('/api/v1/projects', data);
  }

  /**
   * Update existing project
   *
   * @example
   * const updated = await ProjectsAPI.update(123, { status: 'approved' })
   */
  static async update(id: number, data: UpdateProjectRequest): Promise<ProjectDetailResponse> {
    return apiClient.patch<ProjectDetailResponse>(`/api/v1/projects/${id}`, data);
  }

  /**
   * Delete project
   *
   * @example
   * await ProjectsAPI.delete(123)
   */
  static async delete(id: number): Promise<void> {
    return apiClient.delete<void>(`/api/v1/projects/${id}`);
  }

  /**
   * Upload file to project
   *
   * @example
   * const result = await ProjectsAPI.uploadFile(123, file)
   */
  static async uploadFile(projectId: number, file: File): Promise<FileInfo> {
    return apiClient.upload<FileInfo>(
      `/api/v1/projects/${projectId}/files`,
      file,
      { project_id: String(projectId) }
    );
  }

  /**
   * Get project files
   *
   * @example
   * const files = await ProjectsAPI.getFiles(123)
   */
  static async getFiles(projectId: number): Promise<FileInfo[]> {
    return apiClient.get<FileInfo[]>(`/api/v1/projects/${projectId}/files`);
  }

  /**
   * Delete project file
   *
   * @example
   * await ProjectsAPI.deleteFile(123, 456)
   */
  static async deleteFile(projectId: number, fileId: number): Promise<void> {
    return apiClient.delete<void>(`/api/v1/projects/${projectId}/files/${fileId}`);
  }
}
