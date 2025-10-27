/**
 * Input Sanitization Service
 *
 * XSS protection for GenReport using DOMPurify.
 * Sanitizes user input and generated content to prevent XSS attacks.
 */

import DOMPurify from 'dompurify';

/**
 * Sanitization configuration options
 */
export interface SanitizerConfig {
  allowedTags?: string[];
  allowedAttributes?: Record<string, string[]>;
  allowedSchemes?: string[];
  stripComments?: boolean;
}

/**
 * Default sanitization configuration (strict mode)
 */
const DEFAULT_CONFIG = {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'u', 'p', 'br', 'span', 'div'],
  ALLOWED_ATTR: ['class'],
  ALLOW_DATA_ATTR: false,
  ALLOW_UNKNOWN_PROTOCOLS: false,
  SAFE_FOR_TEMPLATES: true,
  WHOLE_DOCUMENT: false,
  RETURN_DOM: false,
  RETURN_DOM_FRAGMENT: false,
  RETURN_TRUSTED_TYPE: false,
  FORCE_BODY: false,
  SANITIZE_DOM: true,
  KEEP_CONTENT: true,
  IN_PLACE: false,
};

/**
 * Rich text configuration (allows more formatting)
 */
const RICH_TEXT_CONFIG = {
  ALLOWED_TAGS: [
    'b', 'i', 'em', 'strong', 'u', 'p', 'br', 'span', 'div',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'table', 'thead', 'tbody', 'tr', 'td', 'th',
    'a', 'code', 'pre',
  ],
  ALLOWED_ATTR: ['class', 'href', 'target', 'rel'],
  ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  ALLOW_DATA_ATTR: false,
  ALLOW_UNKNOWN_PROTOCOLS: false,
  SAFE_FOR_TEMPLATES: true,
  WHOLE_DOCUMENT: false,
  RETURN_DOM: false,
  RETURN_DOM_FRAGMENT: false,
  RETURN_TRUSTED_TYPE: false,
  FORCE_BODY: false,
  SANITIZE_DOM: true,
  KEEP_CONTENT: true,
  IN_PLACE: false,
};

/**
 * SanitizerService - XSS protection and input sanitization
 */
export class SanitizerService {
  /**
   * Sanitize HTML content with strict mode (default)
   *
   * @example
   * SanitizerService.sanitizeHTML('<script>alert("XSS")</script><p>Safe content</p>')
   * // Returns: '<p>Safe content</p>'
   */
  static sanitizeHTML(dirty: string, config: any = DEFAULT_CONFIG): string {
    return DOMPurify.sanitize(dirty, config) as unknown as string;
  }

  /**
   * Sanitize rich text content (allows more formatting tags)
   *
   * @example
   * SanitizerService.sanitizeRichText('<h1>Title</h1><p>Content</p>')
   * // Returns: '<h1>Title</h1><p>Content</p>'
   */
  static sanitizeRichText(dirty: string): string {
    return DOMPurify.sanitize(dirty, RICH_TEXT_CONFIG) as unknown as string;
  }

  /**
   * Sanitize plain text (strips all HTML tags)
   *
   * @example
   * SanitizerService.sanitizePlainText('<p>Hello <script>alert("XSS")</script></p>')
   * // Returns: 'Hello '
   */
  static sanitizePlainText(dirty: string): string {
    return DOMPurify.sanitize(dirty, {
      ALLOWED_TAGS: [],
      ALLOWED_ATTR: [],
      KEEP_CONTENT: true,
    });
  }

  /**
   * Sanitize URL to prevent javascript: and data: schemes
   *
   * @example
   * SanitizerService.sanitizeURL('javascript:alert("XSS")')
   * // Returns: 'about:blank'
   *
   * SanitizerService.sanitizeURL('https://example.com')
   * // Returns: 'https://example.com'
   */
  static sanitizeURL(url: string): string {
    const sanitized = DOMPurify.sanitize(url, {
      ALLOWED_TAGS: [],
      ALLOWED_ATTR: [],
      ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
    });

    // Additional check for dangerous protocols
    const lowerUrl = sanitized.toLowerCase().trim();
    if (
      lowerUrl.startsWith('javascript:') ||
      lowerUrl.startsWith('data:') ||
      lowerUrl.startsWith('vbscript:')
    ) {
      return 'about:blank';
    }

    return sanitized;
  }

  /**
   * Sanitize filename to prevent path traversal
   *
   * @example
   * SanitizerService.sanitizeFilename('../../../etc/passwd')
   * // Returns: 'passwd'
   *
   * SanitizerService.sanitizeFilename('report<script>.xlsx')
   * // Returns: 'reportscript.xlsx'
   */
  static sanitizeFilename(filename: string): string {
    // Remove path separators
    let sanitized = filename.replace(/[\/\\]/g, '');

    // Remove HTML tags
    sanitized = this.sanitizePlainText(sanitized);

    // Remove special characters (keep alphanumeric, dash, underscore, dot)
    sanitized = sanitized.replace(/[^a-zA-Z0-9._-]/g, '');

    // Remove leading dots (prevent hidden files)
    sanitized = sanitized.replace(/^\.+/, '');

    // Limit length
    if (sanitized.length > 255) {
      const ext = sanitized.substring(sanitized.lastIndexOf('.'));
      const name = sanitized.substring(0, 255 - ext.length);
      sanitized = name + ext;
    }

    return sanitized || 'unnamed';
  }

  /**
   * Sanitize JSON input (prevents prototype pollution)
   *
   * @example
   * const safe = SanitizerService.sanitizeJSON('{"__proto__": {"admin": true}}')
   * // Returns: {} (dangerous keys removed)
   */
  static sanitizeJSON(json: string): Record<string, unknown> | null {
    try {
      const parsed = JSON.parse(json);

      if (typeof parsed !== 'object' || parsed === null) {
        return null;
      }

      // Remove dangerous keys
      const dangerousKeys = ['__proto__', 'constructor', 'prototype'];
      const sanitize = (obj: any): any => {
        if (Array.isArray(obj)) {
          return obj.map(sanitize);
        }

        if (obj !== null && typeof obj === 'object') {
          const sanitized: Record<string, unknown> = {};
          for (const [key, value] of Object.entries(obj)) {
            if (!dangerousKeys.includes(key)) {
              sanitized[key] = sanitize(value);
            }
          }
          return sanitized;
        }

        return obj;
      };

      return sanitize(parsed);
    } catch {
      return null;
    }
  }

  /**
   * Sanitize attribute value for use in HTML attributes
   *
   * @example
   * SanitizerService.sanitizeAttribute('value" onclick="alert(1)')
   * // Returns: 'value&quot; onclick=&quot;alert(1)'
   */
  static sanitizeAttribute(value: string): string {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\//g, '&#x2F;');
  }

  /**
   * Check if content is safe (doesn't contain dangerous patterns)
   *
   * @example
   * SanitizerService.isSafe('<p>Hello</p>') // true
   * SanitizerService.isSafe('<script>alert(1)</script>') // false
   */
  static isSafe(content: string): boolean {
    const sanitized = this.sanitizeHTML(content);
    return sanitized === content;
  }

  /**
   * Configure DOMPurify with custom settings
   */
  static configure(config: any): void {
    DOMPurify.setConfig(config);
  }

  /**
   * Add a hook to DOMPurify for custom processing
   */
  static addHook(
    hookName: string,
    hook: (node: Element, data: any, config: any) => void
  ): void {
    DOMPurify.addHook(hookName as any, hook);
  }

  /**
   * Remove all hooks from DOMPurify
   */
  static removeAllHooks(): void {
    DOMPurify.removeAllHooks();
  }
}
