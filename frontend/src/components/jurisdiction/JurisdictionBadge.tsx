/**
 * JurisdictionBadge Component
 *
 * Market-aware badge for displaying jurisdiction (HK, SG, AU).
 * Follows design system color conventions.
 */

import { cn } from '@/lib/utils';
import type { Jurisdiction } from '@/utils/market';
import { MarketUtils } from '@/utils/market';

export interface JurisdictionBadgeProps {
  jurisdiction: Jurisdiction;
  className?: string;
  showFullName?: boolean;
}

/**
 * JurisdictionBadge - Display market jurisdiction with color coding
 *
 * @example
 * <JurisdictionBadge jurisdiction="HK" />
 * <JurisdictionBadge jurisdiction="SG" showFullName />
 */
export function JurisdictionBadge({
  jurisdiction,
  className,
  showFullName = false,
}: JurisdictionBadgeProps) {
  const displayText = showFullName
    ? MarketUtils.getDisplayName(jurisdiction)
    : jurisdiction;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2.5 py-0.5',
        'text-xs font-medium ring-1 ring-inset',
        MarketUtils.getJurisdictionColor(jurisdiction),
        className
      )}
      aria-label={`Jurisdiction: ${MarketUtils.getDisplayName(jurisdiction)}`}
    >
      {displayText}
    </span>
  );
}
