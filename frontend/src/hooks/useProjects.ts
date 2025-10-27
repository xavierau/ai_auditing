/**
 * useProjects Hook
 *
 * React Query hooks for project data fetching and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ProjectsAPI } from '@/services/projects';
import { queryKeys } from '@/lib/react-query';
import type {
  ProjectFilters,
  CreateProjectRequest,
  UpdateProjectRequest,
} from '@/services/projects';

/**
 * Hook to fetch list of projects
 *
 * @example
 * const { data, isLoading, error } = useProjects({ jurisdiction: 'HK' })
 */
export function useProjects(filters?: ProjectFilters) {
  return useQuery({
    queryKey: queryKeys.projects.list(filters),
    queryFn: () => ProjectsAPI.list(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Hook to fetch single project
 *
 * @example
 * const { data: project, isLoading } = useProject(123)
 */
export function useProject(id: number, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.projects.detail(id),
    queryFn: () => ProjectsAPI.get(id),
    enabled: options?.enabled !== false && id > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to create new project
 *
 * @example
 * const createProject = useCreateProject()
 * createProject.mutate({ project_name: '...', ... })
 */
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateProjectRequest) => ProjectsAPI.create(data),
    onSuccess: () => {
      // Invalidate projects list to refetch
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.lists() });
    },
  });
}

/**
 * Hook to update existing project
 *
 * @example
 * const updateProject = useUpdateProject()
 * updateProject.mutate({ id: 123, data: { status: 'approved' } })
 */
export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateProjectRequest }) =>
      ProjectsAPI.update(id, data),
    onSuccess: (updatedProject) => {
      // Update cache for specific project
      queryClient.setQueryData(
        queryKeys.projects.detail(updatedProject.id),
        updatedProject
      );

      // Invalidate projects list
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.lists() });
    },
  });
}

/**
 * Hook to delete project
 *
 * @example
 * const deleteProject = useDeleteProject()
 * deleteProject.mutate(123)
 */
export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => ProjectsAPI.delete(id),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: queryKeys.projects.detail(id) });

      // Invalidate projects list
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.lists() });
    },
  });
}

/**
 * Hook to upload file to project
 *
 * @example
 * const uploadFile = useUploadProjectFile()
 * uploadFile.mutate({ projectId: 123, file: fileObject })
 */
export function useUploadProjectFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, file }: { projectId: number; file: File }) =>
      ProjectsAPI.uploadFile(projectId, file),
    onSuccess: (_, variables) => {
      // Invalidate project details to refetch files
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.detail(variables.projectId),
      });

      // Invalidate files list
      queryClient.invalidateQueries({
        queryKey: queryKeys.files.project(variables.projectId),
      });
    },
  });
}

/**
 * Hook to get project files
 *
 * @example
 * const { data: files } = useProjectFiles(123)
 */
export function useProjectFiles(projectId: number) {
  return useQuery({
    queryKey: queryKeys.files.project(projectId),
    queryFn: () => ProjectsAPI.getFiles(projectId),
    enabled: projectId > 0,
  });
}

/**
 * Hook to delete project file
 *
 * @example
 * const deleteFile = useDeleteProjectFile()
 * deleteFile.mutate({ projectId: 123, fileId: 456 })
 */
export function useDeleteProjectFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, fileId }: { projectId: number; fileId: number }) =>
      ProjectsAPI.deleteFile(projectId, fileId),
    onSuccess: (_, variables) => {
      // Invalidate project files
      queryClient.invalidateQueries({
        queryKey: queryKeys.files.project(variables.projectId),
      });

      // Invalidate project details
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.detail(variables.projectId),
      });
    },
  });
}
