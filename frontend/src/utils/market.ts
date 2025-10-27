/**
 * Market Configuration Utilities
 *
 * Central configuration for market-specific settings across GenReport.
 * Provides jurisdiction-aware defaults and formatting helpers.
 */

import type { Currency, Jurisdiction } from './currency';
import { JURISDICTION_CURRENCY_MAP, CURRENCY_SYMBOLS } from './currency';

// Re-export Jurisdiction type for convenience
export type { Jurisdiction, Currency };

export type AccountingStandard = 'HKFRS' | 'SME-FRS' | 'SFRS' | 'AASB';

/**
 * Market configuration interface
 */
export interface MarketConfig {
  jurisdiction: Jurisdiction;
  currency: Currency;
  currencySymbol: string;
  accountingStandards: AccountingStandard[];
  dateFormat: string;
  locale: string;
  displayName: string;
}

/**
 * Jurisdiction colors for UI badges (matching design system)
 */
export const JURISDICTION_COLORS: Record<Jurisdiction, string> = {
  HK: 'bg-blue-50 text-blue-700 ring-blue-700/10', // Blue
  SG: 'bg-green-50 text-green-700 ring-green-700/10', // Green
  AU: 'bg-amber-50 text-amber-700 ring-amber-700/10', // Amber
};

/**
 * Market configurations by jurisdiction
 */
export const MARKET_CONFIGS: Record<Jurisdiction, MarketConfig> = {
  HK: {
    jurisdiction: 'HK',
    currency: 'HKD',
    currencySymbol: 'HK$',
    accountingStandards: ['HKFRS', 'SME-FRS'],
    dateFormat: 'DD/MM/YYYY',
    locale: 'en-HK',
    displayName: 'Hong Kong',
  },
  SG: {
    jurisdiction: 'SG',
    currency: 'SGD',
    currencySymbol: 'S$',
    accountingStandards: ['SFRS'],
    dateFormat: 'DD/MM/YYYY',
    locale: 'en-SG',
    displayName: 'Singapore',
  },
  AU: {
    jurisdiction: 'AU',
    currency: 'AUD',
    currencySymbol: 'A$',
    accountingStandards: ['AASB'],
    dateFormat: 'DD/MM/YYYY',
    locale: 'en-AU',
    displayName: 'Australia',
  },
};

/**
 * Accounting standard display names
 */
export const ACCOUNTING_STANDARD_NAMES: Record<AccountingStandard, string> = {
  HKFRS: 'Hong Kong Financial Reporting Standards',
  'SME-FRS': 'SME Financial Reporting Standard',
  SFRS: 'Singapore Financial Reporting Standards',
  AASB: 'Australian Accounting Standards Board',
};

/**
 * MarketUtils - Helper utilities for market-specific operations
 */
export class MarketUtils {
  /**
   * Get market configuration for a jurisdiction
   */
  static getConfig(jurisdiction: Jurisdiction): MarketConfig {
    return MARKET_CONFIGS[jurisdiction];
  }

  /**
   * Get jurisdiction color classes for badges
   */
  static getJurisdictionColor(jurisdiction: Jurisdiction): string {
    return JURISDICTION_COLORS[jurisdiction];
  }

  /**
   * Get currency for a jurisdiction
   */
  static getCurrency(jurisdiction: Jurisdiction): Currency {
    return JURISDICTION_CURRENCY_MAP[jurisdiction];
  }

  /**
   * Get currency symbol for a jurisdiction
   */
  static getCurrencySymbol(jurisdiction: Jurisdiction): string {
    return CURRENCY_SYMBOLS[this.getCurrency(jurisdiction)];
  }

  /**
   * Get accounting standards for a jurisdiction
   */
  static getAccountingStandards(jurisdiction: Jurisdiction): AccountingStandard[] {
    return MARKET_CONFIGS[jurisdiction].accountingStandards;
  }

  /**
   * Get accounting standard display name
   */
  static getAccountingStandardName(standard: AccountingStandard): string {
    return ACCOUNTING_STANDARD_NAMES[standard];
  }

  /**
   * Get all supported jurisdictions
   */
  static getSupportedJurisdictions(): Jurisdiction[] {
    return Object.keys(MARKET_CONFIGS) as Jurisdiction[];
  }

  /**
   * Check if a jurisdiction is supported
   */
  static isSupported(jurisdiction: string): jurisdiction is Jurisdiction {
    return jurisdiction in MARKET_CONFIGS;
  }

  /**
   * Get display name for jurisdiction
   */
  static getDisplayName(jurisdiction: Jurisdiction): string {
    return MARKET_CONFIGS[jurisdiction].displayName;
  }
}
