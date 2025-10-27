/**
 * Currency Formatting Utilities
 *
 * Market-aware currency formatting for GenReport multi-jurisdiction support.
 * Supports HKD (Hong Kong), SGD (Singapore), AUD (Australia).
 */

export type Currency = 'HKD' | 'SGD' | 'AUD';
export type Jurisdiction = 'HK' | 'SG' | 'AU';

/**
 * Map jurisdictions to their respective currencies
 */
export const JURISDICTION_CURRENCY_MAP: Record<Jurisdiction, Currency> = {
  HK: 'HKD',
  SG: 'SGD',
  AU: 'AUD',
};

/**
 * Currency symbols for display
 */
export const CURRENCY_SYMBOLS: Record<Currency, string> = {
  HKD: 'HK$',
  SGD: 'S$',
  AUD: 'A$',
};

/**
 * CurrencyFormatter - Market-aware currency formatting utility
 */
export class CurrencyFormatter {
  /**
   * Format amount with full currency symbol and thousands separators
   *
   * @example
   * CurrencyFormatter.format(1234567.89, 'HKD') // "HK$1,234,567.89"
   * CurrencyFormatter.format(1234567.89, 'SGD') // "S$1,234,567.89"
   */
  static format(amount: number, currency: Currency): string {
    const symbol = CURRENCY_SYMBOLS[currency];

    return new Intl.NumberFormat('en', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
      .format(amount)
      .replace(currency, symbol); // Replace ISO code with custom symbol
  }

  /**
   * Format amount in compact notation (e.g., 1.2M, 3.4K)
   *
   * @example
   * CurrencyFormatter.formatCompact(1234567, 'HKD') // "HK$1.2M"
   * CurrencyFormatter.formatCompact(1234, 'SGD') // "S$1.2K"
   */
  static formatCompact(amount: number, currency: Currency): string {
    const symbol = CURRENCY_SYMBOLS[currency];

    return new Intl.NumberFormat('en', {
      style: 'currency',
      currency: currency,
      notation: 'compact',
      maximumFractionDigits: 1,
    })
      .format(amount)
      .replace(currency, symbol);
  }

  /**
   * Format amount without currency symbol (numbers only)
   *
   * @example
   * CurrencyFormatter.formatNumber(1234567.89) // "1,234,567.89"
   */
  static formatNumber(amount: number): string {
    return new Intl.NumberFormat('en', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  }

  /**
   * Get currency for a given jurisdiction
   *
   * @example
   * CurrencyFormatter.getCurrency('HK') // 'HKD'
   */
  static getCurrency(jurisdiction: Jurisdiction): Currency {
    return JURISDICTION_CURRENCY_MAP[jurisdiction];
  }

  /**
   * Format amount by jurisdiction (convenience method)
   *
   * @example
   * CurrencyFormatter.formatByJurisdiction(1234567.89, 'HK') // "HK$1,234,567.89"
   */
  static formatByJurisdiction(amount: number, jurisdiction: Jurisdiction): string {
    const currency = this.getCurrency(jurisdiction);
    return this.format(amount, currency);
  }

  /**
   * Format amount in compact notation by jurisdiction
   *
   * @example
   * CurrencyFormatter.formatCompactByJurisdiction(1234567, 'HK') // "HK$1.2M"
   */
  static formatCompactByJurisdiction(amount: number, jurisdiction: Jurisdiction): string {
    const currency = this.getCurrency(jurisdiction);
    return this.formatCompact(amount, currency);
  }
}
