/**
 * ErrorBoundary Component
 *
 * React Error Boundary for graceful error handling.
 * Catches JavaScript errors anywhere in the child component tree.
 */

import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary - Catch and display component errors gracefully
 *
 * @example
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 *
 * @example
 * <ErrorBoundary fallback={(error, reset) => (
 *   <CustomErrorDisplay error={error} onReset={reset} />
 * )}>
 *   <YourComponent />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to error reporting service
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // In production, you would log to an error reporting service like Sentry:
    // Sentry.captureException(error, { contexts: { react: { componentStack: errorInfo.componentStack } } });
  }

  resetErrorBoundary = (): void => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      // Custom fallback provided
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.resetErrorBoundary);
      }

      // Default fallback UI
      return <DefaultErrorFallback error={this.state.error} reset={this.resetErrorBoundary} />;
    }

    return this.props.children;
  }
}

/**
 * DefaultErrorFallback - Default error display component
 */
interface DefaultErrorFallbackProps {
  error: Error;
  reset: () => void;
}

function DefaultErrorFallback({ error, reset }: DefaultErrorFallbackProps) {
  const isDevelopment = import.meta.env.DEV;

  return (
    <div
      className="flex min-h-[400px] flex-col items-center justify-center rounded-lg border border-red-200 bg-red-50 p-8"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-center gap-3 text-red-600">
        <AlertCircle className="h-12 w-12" aria-hidden="true" />
        <h2 className="text-2xl font-semibold">Something went wrong</h2>
      </div>

      <p className="mt-4 max-w-md text-center text-gray-700">
        We're sorry, but something unexpected happened. Please try refreshing the page or contact support if the problem
        persists.
      </p>

      {isDevelopment && (
        <div className="mt-6 w-full max-w-2xl rounded-md bg-gray-900 p-4 text-left">
          <p className="font-mono text-sm text-red-400">
            <strong>Error:</strong> {error.message}
          </p>
          {error.stack && (
            <pre className="mt-2 overflow-auto text-xs text-gray-400">
              <code>{error.stack}</code>
            </pre>
          )}
        </div>
      )}

      <Button
        onClick={reset}
        className="mt-6 inline-flex items-center gap-2"
        aria-label="Try again"
      >
        <RefreshCw className="h-4 w-4" />
        Try Again
      </Button>
    </div>
  );
}

/**
 * withErrorBoundary - HOC to wrap components with ErrorBoundary
 *
 * @example
 * export default withErrorBoundary(MyComponent)
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name || 'Component'})`;

  return WrappedComponent;
}
