/**
 * DashboardView Component
 *
 * Main dashboard view with real API data integration using React Query.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProjects } from '@/hooks/useProjects';
import { ProjectCard, ProjectCardSkeleton } from '@/components';
import { NewProjectDialog } from '@/components/project/NewProjectDialog';
import { Button } from '@/components/ui/button';
import { Plus, Search, Filter } from 'lucide-react';
import type { ProjectFilters } from '@/services/projects';
import type { Jurisdiction } from '@/utils/market';
import type { Status } from '@/components/status/StatusBadge';

export function DashboardView() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<ProjectFilters>({
    page: 1,
    page_size: 20,
  });
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);

  const { data, isLoading, error, isError } = useProjects(filters);

  const handleFilterChange = (key: keyof ProjectFilters, value: any) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      page: 1, // Reset to first page on filter change
    }));
  };

  return (
    <div className="p-8">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
            {data && (
              <p className="mt-1 text-sm text-gray-600">
                {data.total} project{data.total !== 1 ? 's' : ''} found
              </p>
            )}
          </div>
          <Button
            onClick={() => setIsNewProjectOpen(true)}
            className="inline-flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            New Project
          </Button>
        </div>

        {/* Filters */}
        <div className="mb-6 flex items-center gap-4">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search projects or clients..."
              className="w-full rounded-md border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              onChange={(e) => handleFilterChange('search', e.target.value || undefined)}
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              className="rounded-md border border-gray-300 py-2 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              onChange={(e) =>
                handleFilterChange('status', e.target.value || undefined)
              }
              defaultValue=""
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="processing">Processing</option>
              <option value="review">Review</option>
              <option value="approved">Approved</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          {/* Jurisdiction Filter */}
          <select
            className="rounded-md border border-gray-300 py-2 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            onChange={(e) =>
              handleFilterChange('jurisdiction', e.target.value || undefined)
            }
            defaultValue=""
          >
            <option value="">All Markets</option>
            <option value="HK">Hong Kong</option>
            <option value="SG">Singapore</option>
            <option value="AU">Australia</option>
          </select>
        </div>

        {/* Error State */}
        {isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
            <p className="text-red-700">
              Failed to load projects. {error?.message || 'Please try again.'}
            </p>
            <Button
              variant="outline"
              onClick={() => window.location.reload()}
              className="mt-4"
            >
              Retry
            </Button>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <ProjectCardSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !isError && data && data.projects.length === 0 && (
          <div className="rounded-lg border border-gray-200 bg-white p-12 text-center">
            <p className="text-gray-600">No projects found.</p>
            <Button
              onClick={() => setIsNewProjectOpen(true)}
              className="mt-4"
            >
              Create Your First Project
            </Button>
          </div>
        )}

        {/* Project Grid */}
        {!isLoading && !isError && data && data.projects.length > 0 && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {data.projects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onClick={(p) => navigate(`/projects/${p.id}`)}
                />
              ))}
            </div>

            {/* Pagination */}
            {data.total > filters.page_size! && (
              <div className="mt-8 flex items-center justify-center gap-2">
                <Button
                  variant="outline"
                  onClick={() =>
                    handleFilterChange('page', Math.max(1, (filters.page || 1) - 1))
                  }
                  disabled={filters.page === 1}
                >
                  Previous
                </Button>
                <span className="text-sm text-gray-600">
                  Page {filters.page} of {Math.ceil(data.total / filters.page_size!)}
                </span>
                <Button
                  variant="outline"
                  onClick={() => handleFilterChange('page', (filters.page || 1) + 1)}
                  disabled={
                    filters.page! >= Math.ceil(data.total / filters.page_size!)
                  }
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}

        {/* New Project Dialog */}
        <NewProjectDialog
          open={isNewProjectOpen}
          onOpenChange={setIsNewProjectOpen}
        />
      </div>
    </div>
  );
}
