/**
 * StatusBadge Component
 *
 * Status indicator for projects and reports.
 * Follows design system semantic colors.
 */

import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export type Status = 'draft' | 'processing' | 'review' | 'approved' | 'failed' | 'completed';

export interface StatusBadgeProps {
  status: Status;
  className?: string;
  showIcon?: boolean;
}

/**
 * Status styles mapping
 */
const STATUS_STYLES: Record<Status, string> = {
  draft: 'bg-gray-100 text-gray-700',
  processing: 'bg-blue-100 text-blue-700',
  review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
};

/**
 * Status display text mapping
 */
const STATUS_TEXT: Record<Status, string> = {
  draft: 'Draft',
  processing: 'Processing',
  review: 'Review',
  approved: 'Approved',
  completed: 'Completed',
  failed: 'Failed',
};

/**
 * StatusBadge - Display status with semantic colors
 *
 * @example
 * <StatusBadge status="processing" showIcon />
 * <StatusBadge status="approved" />
 */
export function StatusBadge({
  status,
  className,
  showIcon = true,
}: StatusBadgeProps) {
  const isProcessing = status === 'processing';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-3 py-1',
        'text-xs font-medium',
        STATUS_STYLES[status],
        isProcessing && 'animate-pulse',
        className
      )}
      aria-label={`Status: ${STATUS_TEXT[status]}`}
    >
      {showIcon && isProcessing && (
        <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
      )}
      {STATUS_TEXT[status]}
    </span>
  );
}
