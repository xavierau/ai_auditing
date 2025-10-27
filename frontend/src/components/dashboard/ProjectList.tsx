/**
 * ProjectList Component
 *
 * Dashboard view with filtering and market-aware project cards.
 * Follows design system responsive grid pattern.
 */

import { useState, useMemo } from 'react';
import { Search, Filter, Plus } from 'lucide-react';
import { ProjectCard, ProjectCardSkeleton, type ProjectData, type Status } from '@/components';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import type { Jurisdiction } from '@/utils/market';

export interface ProjectListProps {
  projects: ProjectData[];
  isLoading?: boolean;
  onProjectClick?: (project: ProjectData) => void;
  onCreateProject?: () => void;
  className?: string;
}

type FilterStatus = Status | 'all';
type FilterJurisdiction = Jurisdiction | 'all';

/**
 * ProjectList - Dashboard project grid with filtering
 *
 * @example
 * <ProjectList
 *   projects={projects}
 *   onProjectClick={(p) => navigate(`/projects/${p.id}`)}
 *   onCreateProject={() => navigate('/projects/new')}
 * />
 */
export function ProjectList({
  projects,
  isLoading = false,
  onProjectClick,
  onCreateProject,
  className,
}: ProjectListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [jurisdictionFilter, setJurisdictionFilter] = useState<FilterJurisdiction>('all');

  // Filter projects
  const filteredProjects = useMemo(() => {
    return projects.filter((project) => {
      // Search filter
      const matchesSearch =
        searchQuery === '' ||
        project.project_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        project.client_name.toLowerCase().includes(searchQuery.toLowerCase());

      // Status filter
      const matchesStatus = statusFilter === 'all' || project.status === statusFilter;

      // Jurisdiction filter
      const matchesJurisdiction =
        jurisdictionFilter === 'all' || project.jurisdiction === jurisdictionFilter;

      return matchesSearch && matchesStatus && matchesJurisdiction;
    });
  }, [projects, searchQuery, statusFilter, jurisdictionFilter]);

  // Get unique statuses and jurisdictions
  const availableStatuses: FilterStatus[] = ['all', 'draft', 'processing', 'review', 'approved', 'completed', 'failed'];
  const availableJurisdictions: FilterJurisdiction[] = [
    'all',
    ...Array.from(new Set(projects.map((p) => p.jurisdiction))),
  ];

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
          <p className="mt-1 text-sm text-gray-600">
            {filteredProjects.length} of {projects.length} projects
          </p>
        </div>

        {onCreateProject && (
          <Button
            onClick={onCreateProject}
            className="inline-flex items-center gap-2"
            aria-label="Create new project"
          >
            <Plus className="h-5 w-5" />
            New Project
          </Button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        {/* Search */}
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
            aria-hidden="true"
          />
          <Input
            type="text"
            placeholder="Search projects or clients..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
            aria-label="Search projects"
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-500" aria-hidden="true" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as FilterStatus)}
            className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Filter by status"
          >
            {availableStatuses.map((status) => (
              <option key={status} value={status}>
                {status === 'all' ? 'All Statuses' : status.charAt(0).toUpperCase() + status.slice(1)}
              </option>
            ))}
          </select>

          {/* Jurisdiction Filter */}
          <select
            value={jurisdictionFilter}
            onChange={(e) => setJurisdictionFilter(e.target.value as FilterJurisdiction)}
            className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Filter by jurisdiction"
          >
            {availableJurisdictions.map((jurisdiction) => (
              <option key={jurisdiction} value={jurisdiction}>
                {jurisdiction === 'all' ? 'All Markets' : jurisdiction}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Project Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <ProjectCardSkeleton key={i} />
          ))}
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-12 text-center">
          <Filter className="h-12 w-12 text-gray-400" aria-hidden="true" />
          <h3 className="mt-4 text-lg font-semibold text-gray-900">No projects found</h3>
          <p className="mt-2 text-sm text-gray-600">
            {searchQuery || statusFilter !== 'all' || jurisdictionFilter !== 'all'
              ? 'Try adjusting your filters'
              : 'Create your first project to get started'}
          </p>
          {onCreateProject && !searchQuery && statusFilter === 'all' && jurisdictionFilter === 'all' && (
            <Button onClick={onCreateProject} className="mt-4">
              <Plus className="mr-2 h-4 w-4" />
              Create Project
            </Button>
          )}
        </div>
      ) : (
        <div
          className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"
          role="list"
          aria-label="Project list"
        >
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onClick={onProjectClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}
