/**
 * ProtectedRoute Component
 *
 * Wrapper component that requires authentication to access child components.
 * Redirects to login if user is not authenticated.
 */

import { ReactNode } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { LoginForm } from './LoginForm';

export interface ProtectedRouteProps {
  children: ReactNode;
  /**
   * Optional loading component to show while checking auth
   */
  loadingComponent?: ReactNode;
}

/**
 * ProtectedRoute
 *
 * Protects routes by requiring authentication.
 * Shows login form if not authenticated.
 *
 * @example
 * <ProtectedRoute>
 *   <DashboardView />
 * </ProtectedRoute>
 */
export function ProtectedRoute({ children, loadingComponent }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <>
        {loadingComponent || (
          <div className="flex min-h-screen items-center justify-center bg-gray-50">
            <div className="text-center">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent"></div>
              <p className="mt-4 text-sm text-gray-600">Loading...</p>
            </div>
          </div>
        )}
      </>
    );
  }

  // Show login form if not authenticated
  if (!isAuthenticated) {
    return <LoginForm />;
  }

  // Render protected content
  return <>{children}</>;
}
