/**
 * useFiles Hook
 *
 * React Query hooks for file operations (upload, list, delete).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/react-query';
import {
  uploadFile,
  listProjectFiles,
  deleteFile,
  type FileUploadResponse,
  type FileMetadata,
} from '@/services/files';

/**
 * Hook to list files for a project
 *
 * @param projectId - ID of project
 * @returns React Query result with files list
 */
export function useProjectFiles(projectId: number) {
  return useQuery({
    queryKey: queryKeys.files.project(projectId),
    queryFn: () => listProjectFiles(projectId),
    select: (data) => data.files,
  });
}

/**
 * Hook to upload a file
 *
 * @returns Mutation object for file upload
 */
export function useUploadFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, projectId }: { file: File; projectId: number }) =>
      uploadFile(file, projectId),
    onSuccess: (_data, variables) => {
      // Invalidate project files query to refetch the list
      queryClient.invalidateQueries({
        queryKey: queryKeys.files.project(variables.projectId),
      });
    },
  });
}

/**
 * Hook to delete a file
 *
 * @returns Mutation object for file deletion
 */
export function useDeleteFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ fileId, projectId }: { fileId: string; projectId: number }) =>
      deleteFile(fileId),
    onSuccess: (_data, variables) => {
      // Invalidate project files query to refetch the list
      queryClient.invalidateQueries({
        queryKey: queryKeys.files.project(variables.projectId),
      });
    },
  });
}
