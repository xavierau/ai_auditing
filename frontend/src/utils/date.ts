/**
 * Date Formatting Utilities
 *
 * Market-aware date formatting for GenReport multi-jurisdiction support.
 * Supports HK, SG, AU date formats following local conventions.
 */

export type Jurisdiction = 'HK' | 'SG' | 'AU';

/**
 * Date format patterns by jurisdiction
 *
 * HK/SG: DD/MM/YYYY (day-first)
 * AU: DD/MM/YYYY (day-first)
 */
export const DATE_FORMAT_PATTERNS: Record<Jurisdiction, string> = {
  HK: 'DD/MM/YYYY',
  SG: 'DD/MM/YYYY',
  AU: 'DD/MM/YYYY',
};

/**
 * Locale codes for Intl.DateTimeFormat
 */
export const LOCALE_CODES: Record<Jurisdiction, string> = {
  HK: 'en-HK',
  SG: 'en-SG',
  AU: 'en-AU',
};

/**
 * DateFormatter - Market-aware date formatting utility
 */
export class DateFormatter {
  /**
   * Format date by jurisdiction with proper locale formatting
   *
   * @example
   * DateFormatter.formatByJurisdiction(new Date('2025-10-18'), 'HK') // "18/10/2025"
   * DateFormatter.formatByJurisdiction(new Date('2025-10-18'), 'AU') // "18/10/2025"
   */
  static formatByJurisdiction(date: Date | string, jurisdiction: Jurisdiction): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    const locale = LOCALE_CODES[jurisdiction];

    return new Intl.DateTimeFormat(locale, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(dateObj);
  }

  /**
   * Format date in long format (e.g., "18 October 2025")
   *
   * @example
   * DateFormatter.formatLong(new Date('2025-10-18'), 'HK') // "18 October 2025"
   */
  static formatLong(date: Date | string, jurisdiction: Jurisdiction): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    const locale = LOCALE_CODES[jurisdiction];

    return new Intl.DateTimeFormat(locale, {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(dateObj);
  }

  /**
   * Format date with month abbreviation (e.g., "18 Oct 2025")
   *
   * @example
   * DateFormatter.formatMedium(new Date('2025-10-18'), 'HK') // "18 Oct 2025"
   */
  static formatMedium(date: Date | string, jurisdiction: Jurisdiction): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    const locale = LOCALE_CODES[jurisdiction];

    return new Intl.DateTimeFormat(locale, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }).format(dateObj);
  }

  /**
   * Format date and time
   *
   * @example
   * DateFormatter.formatDateTime(new Date('2025-10-18T14:30:00'), 'HK') // "18/10/2025, 2:30 PM"
   */
  static formatDateTime(date: Date | string, jurisdiction: Jurisdiction): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    const locale = LOCALE_CODES[jurisdiction];

    return new Intl.DateTimeFormat(locale, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(dateObj);
  }

  /**
   * Format relative time (e.g., "2 hours ago", "3 days ago")
   *
   * @example
   * DateFormatter.formatRelative(new Date(Date.now() - 2 * 60 * 60 * 1000), 'HK') // "2 hours ago"
   */
  static formatRelative(date: Date | string, jurisdiction: Jurisdiction): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    const now = new Date();
    const diffMs = now.getTime() - dateObj.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return 'just now';
    if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
    if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
    if (diffDay < 30) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;

    // Fall back to standard format for older dates
    return this.formatByJurisdiction(dateObj, jurisdiction);
  }

  /**
   * Format financial year end (FYE) date
   *
   * @example
   * DateFormatter.formatFYE(new Date('2025-12-31'), 'HK') // "FYE 31/12/2025"
   */
  static formatFYE(date: Date | string, jurisdiction: Jurisdiction): string {
    const formatted = this.formatByJurisdiction(date, jurisdiction);
    return `FYE ${formatted}`;
  }

  /**
   * Parse ISO date string to Date object
   *
   * @example
   * DateFormatter.parseISO('2025-10-18') // Date object
   */
  static parseISO(dateString: string): Date {
    return new Date(dateString);
  }

  /**
   * Check if date is valid
   *
   * @example
   * DateFormatter.isValid(new Date('2025-10-18')) // true
   * DateFormatter.isValid(new Date('invalid')) // false
   */
  static isValid(date: Date | string): boolean {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return !isNaN(dateObj.getTime());
  }
}
