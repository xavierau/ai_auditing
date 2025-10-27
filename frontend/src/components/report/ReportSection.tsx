/**
 * ReportSection Component
 *
 * Display individual report sections with XSS protection and source referencing.
 * Follows design system with secure content rendering.
 */

import { useState, useMemo } from 'react';
import { Eye, Edit3, ExternalLink, CheckCircle, AlertCircle } from 'lucide-react';
import { marked } from 'marked';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ConfidenceScore } from '@/components';
import { SanitizerService } from '@/services/sanitizer';
import { cn } from '@/lib/utils';

export interface ReportSectionData {
  id: string;
  title: string;
  content: string; // Markdown content (converted to HTML for rendering)
  confidence_score: number;
  source_references?: SourceReference[];
  status: 'generated' | 'edited' | 'approved';
  accounting_standard?: string;
}

export interface SourceReference {
  id: string;
  text: string;
  worksheet: string;
  cell_reference: string;
}

export interface ReportSectionProps {
  section: ReportSectionData;
  onEdit?: (sectionId: string) => void;
  onApprove?: (sectionId: string) => void;
  onViewSource?: (reference: SourceReference) => void;
  className?: string;
  editable?: boolean;
}

/**
 * ReportSection - Secure disclosure section display
 *
 * @example
 * <ReportSection
 *   section={sectionData}
 *   onEdit={(id) => openEditor(id)}
 *   onApprove={(id) => approveSection(id)}
 *   onViewSource={(ref) => highlightSource(ref)}
 * />
 */
export function ReportSection({
  section,
  onEdit,
  onApprove,
  onViewSource,
  className,
  editable = true,
}: ReportSectionProps) {
  const [showSources, setShowSources] = useState(false);

  // Convert markdown to HTML and sanitize to prevent XSS
  const sanitizedContent = useMemo(() => {
    // Parse markdown to HTML
    const htmlContent = marked.parse(section.content, { async: false }) as string;

    // Sanitize HTML to prevent XSS attacks
    return SanitizerService.sanitizeRichText(htmlContent);
  }, [section.content]);

  const statusConfig = {
    generated: {
      label: 'AI Generated',
      color: 'bg-blue-50 text-blue-700 ring-blue-700/10',
      icon: AlertCircle,
    },
    edited: {
      label: 'Manually Edited',
      color: 'bg-yellow-50 text-yellow-800 ring-yellow-800/10',
      icon: Edit3,
    },
    approved: {
      label: 'Approved',
      color: 'bg-green-50 text-green-700 ring-green-700/10',
      icon: CheckCircle,
    },
  };

  const status = statusConfig[section.status];
  const StatusIcon = status.icon;

  return (
    <Card
      className={cn(
        'rounded-lg border border-gray-200 bg-white shadow-sm',
        className
      )}
      aria-label={`Report section: ${section.title}`}
    >
      {/* Header */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-gray-900">{section.title}</h3>
            {section.accounting_standard && (
              <p className="mt-1 text-sm text-gray-600">
                Standard: {section.accounting_standard}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Confidence Score */}
            <ConfidenceScore score={section.confidence_score} />

            {/* Status Badge */}
            <span
              className={cn(
                'inline-flex items-center gap-1.5 rounded-md px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset',
                status.color
              )}
              aria-label={`Section status: ${status.label}`}
            >
              <StatusIcon className="h-3 w-3" aria-hidden="true" />
              {status.label}
            </span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        <div
          className="prose prose-sm max-w-none text-gray-700"
          dangerouslySetInnerHTML={{ __html: sanitizedContent }}
          aria-label="Section content"
        />
      </div>

      {/* Source References */}
      {section.source_references && section.source_references.length > 0 && (
        <div className="border-t border-gray-200 p-6">
          <button
            onClick={() => setShowSources(!showSources)}
            className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            aria-expanded={showSources}
            aria-controls={`sources-${section.id}`}
          >
            <ExternalLink className="h-4 w-4" aria-hidden="true" />
            {section.source_references.length} Source Reference
            {section.source_references.length !== 1 ? 's' : ''}
          </button>

          {showSources && (
            <div
              id={`sources-${section.id}`}
              className="mt-4 space-y-2"
              role="region"
              aria-label="Source references"
            >
              {section.source_references.map((ref) => (
                <button
                  key={ref.id}
                  onClick={() => onViewSource?.(ref)}
                  className="flex w-full items-start gap-3 rounded-md border border-gray-200 bg-gray-50 p-3 text-left transition-colors hover:border-blue-300 hover:bg-blue-50"
                  aria-label={`View source: ${ref.worksheet} ${ref.cell_reference}`}
                >
                  <ExternalLink className="mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400" aria-hidden="true" />
                  <div className="flex-1 text-sm">
                    <p className="font-medium text-gray-900">
                      {ref.worksheet} • {ref.cell_reference}
                    </p>
                    <p className="mt-1 text-gray-600 line-clamp-2">{ref.text}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4">
        {editable && onEdit && section.status !== 'approved' && (
          <Button
            variant="outline"
            onClick={() => onEdit(section.id)}
            className="inline-flex items-center gap-2"
            aria-label="Edit section"
          >
            <Edit3 className="h-4 w-4" />
            Edit
          </Button>
        )}

        {onApprove && section.status !== 'approved' && (
          <Button
            onClick={() => onApprove(section.id)}
            className="inline-flex items-center gap-2"
            aria-label="Approve section"
          >
            <CheckCircle className="h-4 w-4" />
            Approve
          </Button>
        )}

        {section.status === 'approved' && (
          <Button
            variant="ghost"
            onClick={() => onEdit?.(section.id)}
            className="inline-flex items-center gap-2"
            aria-label="View section"
          >
            <Eye className="h-4 w-4" />
            View
          </Button>
        )}
      </div>
    </Card>
  );
}
