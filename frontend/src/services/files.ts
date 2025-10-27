/**
 * Files Service
 *
 * Secure file upload/download operations with tenant isolation.
 */

import { apiClient } from './api';

/**
 * File metadata response from API
 */
export interface FileMetadata {
  file_id: string;
  filename: string;
  size: number;
  uploaded_at: string;
  uploaded_by: number;
}

/**
 * File upload response
 */
export interface FileUploadResponse {
  file_id: string;
  filename: string;
  size: number;
}

/**
 * Upload file to a project
 *
 * @param file - File to upload (Excel workbook)
 * @param projectId - ID of project to associate file with
 * @returns File metadata
 */
export async function uploadFile(
  file: File,
  projectId: number
): Promise<FileUploadResponse> {
  return apiClient.upload<FileUploadResponse>(
    '/api/v1/files/upload',
    file,
    { project_id: String(projectId) }
  );
}

/**
 * List files for a project
 *
 * @param projectId - ID of project
 * @returns List of file metadata
 */
export async function listProjectFiles(
  projectId: number
): Promise<{ files: FileMetadata[] }> {
  return apiClient.get(`/api/v1/files/project/${projectId}`);
}

/**
 * Delete a file
 *
 * @param fileId - ID of file to delete
 * @returns Success message
 */
export async function deleteFile(fileId: string): Promise<{ message: string }> {
  return apiClient.delete(`/api/v1/files/${fileId}`);
}

/**
 * Get download URL for a file
 *
 * @param fileId - ID of file
 * @returns Download URL
 */
export function getFileDownloadUrl(fileId: string): string {
  const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${baseURL}/api/v1/files/${fileId}`;
}
