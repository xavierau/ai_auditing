/**
 * ReportComparison Component
 *
 * Side-by-side comparison view for generated vs manual sections.
 * Follows design system responsive grid pattern.
 */

import { useState } from 'react';
import { ArrowLeftRight, Copy, Check } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ConfidenceScore } from '@/components';
import { SanitizerService } from '@/services/sanitizer';
import { cn } from '@/lib/utils';

export interface ComparisonData {
  sectionTitle: string;
  generated: {
    content: string;
    confidence_score: number;
    sources_count: number;
  };
  manual?: {
    content: string;
    author: string;
    edited_at: string;
  };
}

export interface ReportComparisonProps {
  comparison: ComparisonData;
  onAcceptGenerated?: () => void;
  onEditManual?: () => void;
  onViewSources?: () => void;
  className?: string;
}

/**
 * ReportComparison - Side-by-side generated vs manual comparison
 *
 * @example
 * <ReportComparison
 *   comparison={comparisonData}
 *   onAcceptGenerated={() => acceptAIVersion()}
 *   onEditManual={() => openEditor()}
 * />
 */
export function ReportComparison({
  comparison,
  onAcceptGenerated,
  onEditManual,
  onViewSources,
  className,
}: ReportComparisonProps) {
  const [copiedSide, setCopiedSide] = useState<'generated' | 'manual' | null>(null);

  // Sanitize HTML content
  const sanitizedGenerated = SanitizerService.sanitizeHTML(comparison.generated.content);
  const sanitizedManual = comparison.manual
    ? SanitizerService.sanitizeHTML(comparison.manual.content)
    : null;

  const handleCopy = async (content: string, side: 'generated' | 'manual') => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedSide(side);
      setTimeout(() => setCopiedSide(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-gray-900">{comparison.sectionTitle}</h2>
        <ArrowLeftRight className="h-6 w-6 text-gray-400" aria-hidden="true" />
      </div>

      {/* Side-by-Side Comparison */}
      <div
        className="grid grid-cols-1 gap-6 lg:grid-cols-2"
        role="region"
        aria-label="Content comparison"
      >
        {/* Generated Content */}
        <Card className="flex flex-col rounded-lg border border-gray-200 bg-white shadow-sm">
          {/* Generated Header */}
          <div className="flex items-center justify-between border-b border-gray-200 bg-blue-50 p-4">
            <div className="flex items-center gap-3">
              <h3 className="font-semibold text-gray-900">AI Generated</h3>
              <ConfidenceScore score={comparison.generated.confidence_score} size="sm" />
            </div>
            {comparison.generated.sources_count > 0 && onViewSources && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onViewSources}
                className="text-sm"
                aria-label={`View ${comparison.generated.sources_count} sources`}
              >
                {comparison.generated.sources_count} Source{comparison.generated.sources_count !== 1 ? 's' : ''}
              </Button>
            )}
          </div>

          {/* Generated Content */}
          <div className="flex-1 overflow-y-auto p-6">
            <div
              className="prose prose-sm max-w-none text-gray-700"
              dangerouslySetInnerHTML={{ __html: sanitizedGenerated }}
              aria-label="AI generated content"
            />
          </div>

          {/* Generated Actions */}
          <div className="flex items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 p-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleCopy(comparison.generated.content, 'generated')}
              className="inline-flex items-center gap-2"
              aria-label="Copy generated content"
            >
              {copiedSide === 'generated' ? (
                <>
                  <Check className="h-4 w-4" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  Copy
                </>
              )}
            </Button>
            {onAcceptGenerated && (
              <Button
                size="sm"
                onClick={onAcceptGenerated}
                className="inline-flex items-center gap-2"
                aria-label="Accept generated content"
              >
                <Check className="h-4 w-4" />
                Accept
              </Button>
            )}
          </div>
        </Card>

        {/* Manual Content */}
        <Card
          className={cn(
            'flex flex-col rounded-lg border border-gray-200 shadow-sm',
            comparison.manual ? 'bg-white' : 'bg-gray-50'
          )}
        >
          {/* Manual Header */}
          <div
            className={cn(
              'flex items-center justify-between border-b border-gray-200 p-4',
              comparison.manual ? 'bg-green-50' : 'bg-gray-100'
            )}
          >
            <div>
              <h3 className="font-semibold text-gray-900">Manual Version</h3>
              {comparison.manual && (
                <p className="mt-1 text-xs text-gray-600">
                  By {comparison.manual.author} •{' '}
                  {new Date(comparison.manual.edited_at).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>

          {/* Manual Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {comparison.manual && sanitizedManual ? (
              <div
                className="prose prose-sm max-w-none text-gray-700"
                dangerouslySetInnerHTML={{ __html: sanitizedManual }}
                aria-label="Manual content"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-center">
                <div>
                  <p className="text-sm text-gray-500">No manual version yet</p>
                  {onEditManual && (
                    <Button
                      onClick={onEditManual}
                      variant="outline"
                      size="sm"
                      className="mt-4"
                      aria-label="Create manual version"
                    >
                      Create Manual Version
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Manual Actions */}
          {comparison.manual && (
            <div className="flex items-center justify-end gap-2 border-t border-gray-200 bg-gray-50 p-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCopy(comparison.manual!.content, 'manual')}
                className="inline-flex items-center gap-2"
                aria-label="Copy manual content"
              >
                {copiedSide === 'manual' ? (
                  <>
                    <Check className="h-4 w-4" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    Copy
                  </>
                )}
              </Button>
              {onEditManual && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onEditManual}
                  aria-label="Edit manual content"
                >
                  Edit
                </Button>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Comparison Info */}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
        <p className="text-sm text-blue-900">
          <strong>Review Tip:</strong> Compare the AI-generated content with your manual version. You can
          accept the AI version, copy content between versions, or edit the manual version to combine the
          best of both.
        </p>
      </div>
    </div>
  );
}
