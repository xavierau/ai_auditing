/**
 * useReports Hook
 *
 * React Query hooks for report operations (list, get).
 */

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/react-query';
import {
  listProjectReports,
  getReport,
  type GeneratedReport,
} from '@/services/reports';

/**
 * Hook to list reports for a project
 *
 * @param projectId - ID of project
 * @returns React Query result with reports list
 */
export function useProjectReports(projectId: number) {
  return useQuery({
    queryKey: queryKeys.reports.list(projectId),
    queryFn: () => listProjectReports(projectId),
    enabled: !!projectId && projectId > 0,
  });
}

/**
 * Hook to get a single report by ID
 *
 * @param reportId - ID of report
 * @returns React Query result with report details
 */
export function useReport(reportId: number) {
  return useQuery({
    queryKey: queryKeys.reports.detail(reportId),
    queryFn: () => getReport(reportId),
    enabled: !!reportId && reportId > 0,
  });
}
