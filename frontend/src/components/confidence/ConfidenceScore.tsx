/**
 * ConfidenceScore Component
 *
 * Visual AI confidence indicator with semantic colors.
 * Follows design system confidence badge patterns.
 */

import { CheckCircle, AlertCircle, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ConfidenceScoreProps {
  score: number; // 0-100
  className?: string;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

/**
 * Get confidence level from score
 */
function getConfidenceLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 80) return 'high';
  if (score >= 60) return 'medium';
  return 'low';
}

/**
 * Confidence level styles
 */
const CONFIDENCE_STYLES = {
  high: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-red-100 text-red-700',
};

/**
 * Size variants
 */
const SIZE_VARIANTS = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
  lg: 'px-4 py-1.5 text-base',
};

/**
 * Icon sizes
 */
const ICON_SIZES = {
  sm: 'h-3 w-3',
  md: 'h-4 w-4',
  lg: 'h-5 w-5',
};

/**
 * ConfidenceScore - Display AI confidence with visual indicators
 *
 * @example
 * <ConfidenceScore score={85} showIcon />
 * <ConfidenceScore score={45} size="lg" />
 */
export function ConfidenceScore({
  score,
  className,
  showIcon = true,
  size = 'md',
}: ConfidenceScoreProps) {
  const level = getConfidenceLevel(score);
  const Icon =
    level === 'high'
      ? CheckCircle
      : level === 'medium'
      ? AlertTriangle
      : AlertCircle;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-semibold',
        CONFIDENCE_STYLES[level],
        SIZE_VARIANTS[size],
        className
      )}
      aria-label={`Confidence: ${score}% (${level})`}
      role="status"
    >
      {showIcon && <Icon className={ICON_SIZES[size]} aria-hidden="true" />}
      {score}%
    </span>
  );
}

/**
 * ConfidenceBar - Linear progress bar for confidence
 *
 * @example
 * <ConfidenceBar score={75} />
 */
export interface ConfidenceBarProps {
  score: number;
  className?: string;
  showLabel?: boolean;
}

export function ConfidenceBar({
  score,
  className,
  showLabel = true,
}: ConfidenceBarProps) {
  const level = getConfidenceLevel(score);

  const BAR_COLORS = {
    high: 'bg-green-500',
    medium: 'bg-yellow-500',
    low: 'bg-red-500',
  };

  return (
    <div className={cn('w-full', className)}>
      {showLabel && (
        <div className="mb-1 flex items-center justify-between text-sm">
          <span className="text-gray-700">Confidence</span>
          <span className="font-semibold">{score}%</span>
        </div>
      )}
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className={cn(
            'h-full transition-all duration-300',
            BAR_COLORS[level]
          )}
          style={{ width: `${score}%` }}
          role="progressbar"
          aria-valuenow={score}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Confidence: ${score}%`}
        />
      </div>
    </div>
  );
}
