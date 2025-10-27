/**
 * Authentication Context
 *
 * Provides authentication state and methods throughout the application.
 * Manages user login, logout, and token refresh.
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AuthService, type User, type LoginCredentials } from '@/services/auth';

/**
 * Authentication context value
 */
export interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

/**
 * Authentication context
 */
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Authentication provider props
 */
export interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Authentication Provider
 *
 * Wraps the application to provide authentication state and methods.
 *
 * @example
 * <AuthProvider>
 *   <App />
 * </AuthProvider>
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Initialize auth state from localStorage
   */
  useEffect(() => {
    const initializeAuth = () => {
      try {
        const storedUser = AuthService.getUser();
        const isAuthenticated = AuthService.isAuthenticated();

        if (isAuthenticated && storedUser) {
          setUser(storedUser);
        }
      } catch (error) {
        console.error('Failed to initialize auth:', error);
        // Clear invalid auth state
        AuthService.logout();
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  /**
   * Login user with credentials
   */
  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      const response = await AuthService.login(credentials);
      setUser(response.user);
    } catch (error) {
      // Clear any partial auth state on error
      setUser(null);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Logout current user
   */
  const logout = () => {
    AuthService.logout();
    setUser(null);
  };

  /**
   * Refresh user data from token
   */
  const refreshUser = async () => {
    try {
      // In a real implementation, you might fetch fresh user data
      // For now, just get from localStorage
      const storedUser = AuthService.getUser();
      if (storedUser) {
        setUser(storedUser);
      }
    } catch (error) {
      console.error('Failed to refresh user:', error);
      logout();
    }
  };

  const value: AuthContextValue = {
    user,
    isAuthenticated: user !== null,
    isLoading,
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Use authentication context
 *
 * @returns Authentication context value
 * @throws Error if used outside AuthProvider
 *
 * @example
 * function MyComponent() {
 *   const { user, login, logout } = useAuth();
 *   // ...
 * }
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}
