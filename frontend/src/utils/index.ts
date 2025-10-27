/**
 * GenReport Utility Functions
 *
 * Market-aware utilities for currency, date formatting, and market configuration.
 */

// Currency utilities
export {
  CurrencyFormatter,
  CURRENCY_SYMBOLS,
  JURISDICTION_CURRENCY_MAP,
  type Currency,
  type Jurisdiction as CurrencyJurisdiction,
} from './currency';

// Date utilities
export {
  DateFormatter,
  DATE_FORMAT_PATTERNS,
  LOCALE_CODES,
  type Jurisdiction as DateJurisdiction,
} from './date';

// Market utilities
export {
  MarketUtils,
  MARKET_CONFIGS,
  JURISDICTION_COLORS,
  ACCOUNTING_STANDARD_NAMES,
  type MarketConfig,
  type AccountingStandard,
} from './market';

// Re-export unified Jurisdiction type from currency
export type { Jurisdiction } from './currency';
