/**
 * ProjectCard Component
 *
 * At-a-glance project status card with market-aware formatting.
 * Follows design system project card pattern.
 */

import { Card } from '@/components/ui/card';
import { JurisdictionBadge } from '@/components/jurisdiction/JurisdictionBadge';
import { StatusBadge, type Status } from '@/components/status/StatusBadge';
import { cn } from '@/lib/utils';
import { DateFormatter } from '@/utils/date';
import { CurrencyFormatter, type Currency } from '@/utils/currency';
import { MarketUtils, type Jurisdiction } from '@/utils/market';

export interface ProjectData {
  id: number;
  project_name: string;
  client_name: string;
  jurisdiction: Jurisdiction;
  currency?: Currency; // Optional, will be derived from jurisdiction if missing
  financial_year_end: string | Date;
  status: Status;
  revenue?: number;
  created_at?: string | Date; // Optional to handle backend responses
}

export interface ProjectCardProps {
  project: ProjectData;
  className?: string;
  onClick?: (project: ProjectData) => void;
}

/**
 * ProjectCard - Display project overview with quick actions
 *
 * @example
 * <ProjectCard
 *   project={projectData}
 *   onClick={(p) => navigate(`/projects/${p.id}`)}
 * />
 */
export function ProjectCard({ project, className, onClick }: ProjectCardProps) {
  // Derive currency from jurisdiction if not provided
  const currency = project.currency || MarketUtils.getCurrency(project.jurisdiction);

  const handleClick = () => {
    if (onClick) {
      onClick(project);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (onClick && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onClick(project);
    }
  };

  return (
    <Card
      className={cn(
        'group relative cursor-pointer rounded-lg border border-gray-200 bg-white p-6',
        'shadow-sm transition-all hover:shadow-md hover:border-gray-300',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
        className
      )}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? 'button' : undefined}
      aria-label={`Project: ${project.project_name}`}
    >
      {/* Project Name */}
      <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
        {project.project_name}
      </h3>

      {/* Jurisdiction & Status */}
      <div className="mt-2 flex flex-wrap gap-2">
        <JurisdictionBadge jurisdiction={project.jurisdiction} />
        <StatusBadge status={project.status} />
      </div>

      {/* Metadata */}
      <div className="mt-3 space-y-1 text-sm text-gray-600">
        <p className="flex items-center justify-between">
          <span className="font-medium">Client:</span>
          <span className="text-gray-900 line-clamp-1">{project.client_name}</span>
        </p>

        <p className="flex items-center justify-between">
          <span className="font-medium">FYE:</span>
          <span className="font-mono text-gray-900">
            {DateFormatter.formatByJurisdiction(
              project.financial_year_end,
              project.jurisdiction
            )}
          </span>
        </p>

        {project.revenue !== undefined && (
          <p className="flex items-center justify-between">
            <span className="font-medium">Revenue:</span>
            <span className="font-mono text-gray-900 tabular-nums">
              {CurrencyFormatter.formatCompact(project.revenue, currency)}
            </span>
          </p>
        )}

        {project.created_at && (
          <p className="flex items-center justify-between text-xs text-gray-500">
            <span>Created:</span>
            <span>
              {DateFormatter.formatRelative(project.created_at, project.jurisdiction)}
            </span>
          </p>
        )}
      </div>

      {/* Hover indicator */}
      <div
        className="absolute inset-0 rounded-lg border-2 border-transparent transition-colors group-hover:border-blue-500/20"
        aria-hidden="true"
      />
    </Card>
  );
}

/**
 * ProjectCardSkeleton - Loading skeleton for ProjectCard
 */
export function ProjectCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn('rounded-lg border border-gray-200 bg-white p-6', className)}>
      <div className="animate-pulse">
        {/* Title skeleton */}
        <div className="h-6 w-3/4 rounded bg-gray-200" />

        {/* Badges skeleton */}
        <div className="mt-2 flex gap-2">
          <div className="h-5 w-12 rounded bg-gray-200" />
          <div className="h-5 w-20 rounded bg-gray-200" />
        </div>

        {/* Metadata skeleton */}
        <div className="mt-3 space-y-2">
          <div className="h-4 w-full rounded bg-gray-200" />
          <div className="h-4 w-2/3 rounded bg-gray-200" />
          <div className="h-4 w-1/2 rounded bg-gray-200" />
        </div>
      </div>
    </Card>
  );
}
