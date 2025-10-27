/**
 * Authentication Service
 *
 * Handles user authentication including login, logout, token management,
 * and token refresh. Integrates with the backend JWT authentication system.
 */

import { apiClient } from './api';

/**
 * User data returned from authentication
 */
export interface User {
  id: number;
  email: string;
  name: string;
  tenant_id: string;
  tenant_name: string;
  jurisdiction: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

/**
 * Login credentials
 */
export interface LoginCredentials {
  email: string;
  password: string;
}

/**
 * Authentication response with tokens
 */
export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

/**
 * Token refresh response
 */
export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * Local storage keys for tokens
 */
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'genreport_access_token',
  REFRESH_TOKEN: 'genreport_refresh_token',
  USER: 'genreport_user',
} as const;

/**
 * Authentication Service
 *
 * Provides methods for user authentication and token management.
 */
export class AuthService {
  /**
   * Login with email and password
   *
   * @param credentials - User email and password
   * @returns Authentication response with tokens and user data
   */
  static async login(credentials: LoginCredentials): Promise<AuthResponse> {
    // Send as form data (OAuth2 standard)
    const formData = new URLSearchParams();
    formData.append('username', credentials.email); // OAuth2 uses 'username' field
    formData.append('password', credentials.password);

    const response = await apiClient.post<AuthResponse>(
      '/api/v1/auth/login',
      formData,
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    );

    // Store tokens and user data
    this.setTokens(response.access_token, response.refresh_token);
    this.setUser(response.user);

    return response;
  }

  /**
   * Logout the current user
   *
   * Clears all authentication data from local storage.
   */
  static logout(): void {
    this.clearTokens();
    this.clearUser();
  }

  /**
   * Refresh the access token using the refresh token
   *
   * @returns New access token
   */
  static async refreshToken(): Promise<string> {
    const refreshToken = this.getRefreshToken();

    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await apiClient.post<RefreshTokenResponse>(
        '/api/v1/auth/refresh',
        { refresh_token: refreshToken }
      );

      // Update access token
      this.setAccessToken(response.access_token);

      return response.access_token;
    } catch (error) {
      // If refresh fails, logout user
      this.logout();
      throw error;
    }
  }

  /**
   * Get the current access token
   *
   * @returns Access token or null if not authenticated
   */
  static getAccessToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  }

  /**
   * Get the current refresh token
   *
   * @returns Refresh token or null if not available
   */
  static getRefreshToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
  }

  /**
   * Get the current user data
   *
   * @returns User object or null if not authenticated
   */
  static getUser(): User | null {
    const userJson = localStorage.getItem(STORAGE_KEYS.USER);
    if (!userJson) return null;

    try {
      return JSON.parse(userJson) as User;
    } catch {
      return null;
    }
  }

  /**
   * Check if user is authenticated
   *
   * @returns True if user has valid access token
   */
  static isAuthenticated(): boolean {
    return this.getAccessToken() !== null;
  }

  /**
   * Set access token in local storage
   *
   * @param token - Access token
   */
  static setAccessToken(token: string): void {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token);
  }

  /**
   * Set tokens in local storage
   *
   * @param accessToken - Access token
   * @param refreshToken - Refresh token
   */
  static setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
  }

  /**
   * Set user data in local storage
   *
   * @param user - User object
   */
  static setUser(user: User): void {
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
  }

  /**
   * Clear all tokens from local storage
   */
  static clearTokens(): void {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
  }

  /**
   * Clear user data from local storage
   */
  static clearUser(): void {
    localStorage.removeItem(STORAGE_KEYS.USER);
  }

  /**
   * Get authorization header value
   *
   * @returns Bearer token header value or null
   */
  static getAuthHeader(): string | null {
    const token = this.getAccessToken();
    return token ? `Bearer ${token}` : null;
  }
}
