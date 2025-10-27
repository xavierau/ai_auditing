/**
 * GenReport UI Components
 *
 * Core components following the design system.
 */

// Jurisdiction components
export { JurisdictionBadge, type JurisdictionBadgeProps } from './jurisdiction/JurisdictionBadge';

// Status components
export { StatusBadge, type StatusBadgeProps, type Status } from './status/StatusBadge';

// Confidence components
export {
  ConfidenceScore,
  ConfidenceBar,
  type ConfidenceScoreProps,
  type ConfidenceBarProps,
} from './confidence/ConfidenceScore';

// Project components
export {
  ProjectCard,
  ProjectCardSkeleton,
  type ProjectCardProps,
  type ProjectData,
} from './project/ProjectCard';

// Upload components
export { FileUpload, type FileUploadProps } from './upload/FileUpload';

// Dashboard components
export { ProjectList, type ProjectListProps } from './dashboard/ProjectList';

// Report components
export {
  ReportSection,
  type ReportSectionProps,
  type ReportSectionData,
  type SourceReference,
} from './report/ReportSection';

export {
  ReportComparison,
  type ReportComparisonProps,
  type ComparisonData,
} from './report/ReportComparison';

// Navigation components
export { Navigation, type NavigationProps } from './navigation/Navigation';

// Error components
export {
  ErrorBoundary,
  withErrorBoundary,
  type ErrorBoundaryProps,
} from './errors/ErrorBoundary';

// Auth components
export { LoginForm } from './auth/LoginForm';
export { ProtectedRoute, type ProtectedRouteProps } from './auth/ProtectedRoute';
