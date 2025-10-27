/**
 * API Client Service
 *
 * Secure HTTP client for GenReport with automatic CSRF protection,
 * authentication, and error handling.
 */

import { CSRFService } from './csrf';
import { SanitizerService } from './sanitizer';

/**
 * API configuration
 */
export interface APIConfig {
  baseURL: string;
  timeout?: number;
  withCredentials?: boolean;
}

/**
 * API request options
 */
export interface APIRequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>;
  sanitize?: boolean; // Whether to sanitize response data
}

/**
 * API error response
 */
export class APIError extends Error {
  public readonly status: number;
  public readonly statusText: string;
  public readonly data?: any;

  constructor(message: string, status: number, statusText: string, data?: any) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.statusText = statusText;
    this.data = data;
  }
}

/**
 * Default API configuration
 */
const DEFAULT_CONFIG: APIConfig = {
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000, // 30 seconds
  withCredentials: true,
};

/**
 * APIClient - Secure HTTP client with CSRF and auth
 */
export class APIClient {
  private config: APIConfig;
  private authToken: string | null = null;

  constructor(config: Partial<APIConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Set authentication token (JWT)
   *
   * @example
   * apiClient.setAuthToken('eyJhbGciOiJIUzI1NiIs...')
   */
  setAuthToken(token: string | null): void {
    this.authToken = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  /**
   * Get authentication token
   *
   * Now delegates to AuthService for centralized token management
   */
  getAuthToken(): string | null {
    // Import dynamically to avoid circular dependencies
    // AuthService manages tokens centrally
    const token = localStorage.getItem('genreport_access_token');
    if (token) {
      this.authToken = token;
    }
    return this.authToken || token;
  }

  /**
   * Clear authentication token
   */
  clearAuthToken(): void {
    this.setAuthToken(null);
  }

  /**
   * Build full URL with base URL and query parameters
   */
  private buildURL(endpoint: string, params?: Record<string, string | number | boolean>): string {
    const url = new URL(endpoint, this.config.baseURL);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, String(value));
      });
    }

    return url.toString();
  }

  /**
   * Build headers with auth and CSRF tokens
   */
  private buildHeaders(options: APIRequestOptions = {}): Headers {
    const headers = new Headers(options.headers || {});

    // Add Content-Type if not present and body exists
    // Skip for FormData and URLSearchParams (browser sets these automatically)
    if (options.body && !headers.has('Content-Type')) {
      const isFormData = options.body instanceof FormData;
      const isURLSearchParams = options.body instanceof URLSearchParams;

      if (!isFormData && !isURLSearchParams && typeof options.body === 'string') {
        headers.set('Content-Type', 'application/json');
      }
    }

    // Add authentication token
    const authToken = this.getAuthToken();
    if (authToken) {
      headers.set('Authorization', `Bearer ${authToken}`);
    }

    // Add CSRF token for state-changing requests
    const method = (options.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const csrfHeaders = CSRFService.getHeaders();
      Object.entries(csrfHeaders).forEach(([key, value]) => {
        headers.set(key, value);
      });
    }

    return headers;
  }

  /**
   * Make HTTP request
   */
  private async request<T = any>(
    endpoint: string,
    options: APIRequestOptions = {}
  ): Promise<T> {
    const url = this.buildURL(endpoint, options.params);
    const headers = this.buildHeaders(options);

    const controller = new AbortController();
    const timeout = setTimeout(() => {
      controller.abort();
    }, this.config.timeout || 30000);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        credentials: this.config.withCredentials ? 'include' : 'same-origin',
        signal: options.signal || controller.signal,
      });

      clearTimeout(timeout);

      // Handle non-OK responses
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new APIError(
          errorData?.detail || response.statusText,
          response.status,
          response.statusText,
          errorData
        );
      }

      // Parse response
      const contentType = response.headers.get('Content-Type');
      let data: T;

      if (contentType?.includes('application/json')) {
        data = await response.json();

        // Sanitize response if requested
        if (options.sanitize && typeof data === 'object') {
          data = this.sanitizeData(data) as T;
        }
      } else {
        data = (await response.text()) as T;
      }

      return data;
    } catch (error) {
      clearTimeout(timeout);

      if (error instanceof APIError) {
        throw error;
      }

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new APIError('Request timeout', 408, 'Request Timeout');
        }
        throw new APIError(error.message, 0, 'Network Error');
      }

      throw new APIError('Unknown error', 0, 'Unknown Error');
    }
  }

  /**
   * Sanitize response data (recursive)
   */
  private sanitizeData(data: any): any {
    if (typeof data === 'string') {
      return SanitizerService.sanitizeHTML(data);
    }

    if (Array.isArray(data)) {
      return data.map((item) => this.sanitizeData(item));
    }

    if (data !== null && typeof data === 'object') {
      const sanitized: Record<string, any> = {};
      for (const [key, value] of Object.entries(data)) {
        sanitized[key] = this.sanitizeData(value);
      }
      return sanitized;
    }

    return data;
  }

  /**
   * HTTP GET request
   */
  async get<T = any>(endpoint: string, options: APIRequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  /**
   * HTTP POST request
   */
  async post<T = any>(
    endpoint: string,
    data?: any,
    options: APIRequestOptions = {}
  ): Promise<T> {
    // Don't JSON.stringify FormData or URLSearchParams
    let body: any = undefined;
    if (data) {
      if (data instanceof FormData || data instanceof URLSearchParams) {
        body = data;
      } else {
        body = JSON.stringify(data);
      }
    }

    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body,
    });
  }

  /**
   * HTTP PUT request
   */
  async put<T = any>(
    endpoint: string,
    data?: any,
    options: APIRequestOptions = {}
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * HTTP PATCH request
   */
  async patch<T = any>(
    endpoint: string,
    data?: any,
    options: APIRequestOptions = {}
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * HTTP DELETE request
   */
  async delete<T = any>(endpoint: string, options: APIRequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }

  /**
   * Upload file with multipart/form-data
   */
  async upload<T = any>(
    endpoint: string,
    file: File,
    additionalData?: Record<string, string>,
    options: APIRequestOptions = {}
  ): Promise<T> {
    const formData = new FormData();
    formData.append('file', file);

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    // Add CSRF token to form data
    CSRFService.addToFormData(formData);

    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: formData,
      // Don't set Content-Type - browser will set it with boundary
      headers: {
        ...options.headers,
      },
    });
  }
}

/**
 * Default API client instance
 */
export const apiClient = new APIClient();
