/**
 * CSRF Protection Service
 *
 * Cross-Site Request Forgery protection for GenReport.
 * Manages CSRF tokens for API requests and form submissions.
 */

/**
 * CSRF token storage key
 */
const CSRF_TOKEN_KEY = 'genreport_csrf_token';
const CSRF_HEADER_NAME = 'X-CSRF-Token';

/**
 * CSRFService - CSRF token management and validation
 */
export class CSRFService {
  private static token: string | null = null;

  /**
   * Initialize CSRF protection by fetching token from server
   *
   * @example
   * await CSRFService.initialize('/api/v1/csrf-token')
   */
  static async initialize(endpoint: string = '/api/v1/csrf-token'): Promise<void> {
    try {
      const response = await fetch(endpoint, {
        method: 'GET',
        credentials: 'include', // Include cookies
      });

      if (!response.ok) {
        throw new Error('Failed to fetch CSRF token');
      }

      const data = await response.json();
      this.token = data.csrf_token || data.token;

      // Store in sessionStorage as backup
      if (this.token) {
        sessionStorage.setItem(CSRF_TOKEN_KEY, this.token);
      }
    } catch (error) {
      console.error('CSRF initialization failed:', error);
      // Try to recover from sessionStorage
      this.token = sessionStorage.getItem(CSRF_TOKEN_KEY);
    }
  }

  /**
   * Get current CSRF token
   *
   * @example
   * const token = CSRFService.getToken()
   */
  static getToken(): string | null {
    // Try memory first
    if (this.token) {
      return this.token;
    }

    // Fall back to sessionStorage
    this.token = sessionStorage.getItem(CSRF_TOKEN_KEY);
    return this.token;
  }

  /**
   * Set CSRF token manually
   *
   * @example
   * CSRFService.setToken('abc123')
   */
  static setToken(token: string): void {
    this.token = token;
    sessionStorage.setItem(CSRF_TOKEN_KEY, token);
  }

  /**
   * Clear CSRF token (e.g., on logout)
   *
   * @example
   * CSRFService.clearToken()
   */
  static clearToken(): void {
    this.token = null;
    sessionStorage.removeItem(CSRF_TOKEN_KEY);
  }

  /**
   * Get CSRF token as headers object for fetch requests
   *
   * @example
   * fetch('/api/v1/projects', {
   *   method: 'POST',
   *   headers: {
   *     ...CSRFService.getHeaders(),
   *     'Content-Type': 'application/json',
   *   },
   *   body: JSON.stringify(data),
   * })
   */
  static getHeaders(): Record<string, string> {
    const token = this.getToken();
    if (!token) {
      console.warn('CSRF token not available');
      return {};
    }

    return {
      [CSRF_HEADER_NAME]: token,
    };
  }

  /**
   * Add CSRF token to FormData
   *
   * @example
   * const formData = new FormData()
   * formData.append('file', file)
   * CSRFService.addToFormData(formData)
   */
  static addToFormData(formData: FormData): void {
    const token = this.getToken();
    if (token) {
      formData.append('csrf_token', token);
    }
  }

  /**
   * Create a protected fetch wrapper with automatic CSRF token
   *
   * @example
   * const response = await CSRFService.fetch('/api/v1/projects', {
   *   method: 'POST',
   *   body: JSON.stringify(data),
   * })
   */
  static async fetch(url: string, options: RequestInit = {}): Promise<Response> {
    const headers = new Headers(options.headers || {});

    // Add CSRF token for state-changing requests
    if (this.requiresCSRF(options.method || 'GET')) {
      const token = this.getToken();
      if (token) {
        headers.set(CSRF_HEADER_NAME, token);
      } else {
        console.warn('CSRF token not available for protected request');
      }
    }

    return fetch(url, {
      ...options,
      headers,
      credentials: options.credentials || 'include', // Include cookies by default
    });
  }

  /**
   * Check if HTTP method requires CSRF protection
   */
  private static requiresCSRF(method: string): boolean {
    const safeMethods = ['GET', 'HEAD', 'OPTIONS', 'TRACE'];
    return !safeMethods.includes(method.toUpperCase());
  }

  /**
   * Validate CSRF token format (basic check)
   */
  static isValidTokenFormat(token: string): boolean {
    // Token should be a non-empty string with minimum length
    return typeof token === 'string' && token.length >= 16;
  }

  /**
   * Refresh CSRF token (e.g., after long session)
   *
   * @example
   * await CSRFService.refresh('/api/v1/csrf-token')
   */
  static async refresh(endpoint: string = '/api/v1/csrf-token'): Promise<void> {
    this.clearToken();
    await this.initialize(endpoint);
  }

  /**
   * Check if CSRF token is available
   */
  static hasToken(): boolean {
    return this.getToken() !== null;
  }

  /**
   * Get CSRF header name (for reference)
   */
  static getHeaderName(): string {
    return CSRF_HEADER_NAME;
  }
}
