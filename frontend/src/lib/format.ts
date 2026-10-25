/**
 * Formatting utilities for UK Power Trading analytics.
 * Enforces explicit UTC labeling, consistent decimal precision, and tabular numerals.
 */

/**
 * Format a number with thousands separators and optional decimals.
 */
export function formatNumber(
  value: number | null | undefined,
  decimals: number = 0,
  fallback: string = '—'
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return fallback;
  }
  return new Intl.NumberFormat('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format power generation in Megawatts (MW).
 */
export function formatMW(
  mw: number | null | undefined,
  decimals: number = 0,
  includeUnit: boolean = true
): string {
  if (mw === null || mw === undefined || Number.isNaN(mw)) return '—';
  const formatted = formatNumber(mw, decimals);
  return includeUnit ? `${formatted} MW` : formatted;
}

/**
 * Format energy volume in Megawatt-hours (MWh).
 * (For 30-minute settlement periods, Energy MWh = MW * 0.5)
 */
export function formatMWh(
  mwh: number | null | undefined,
  decimals: number = 0,
  includeUnit: boolean = true
): string {
  if (mwh === null || mwh === undefined || Number.isNaN(mwh)) return '—';
  const formatted = formatNumber(mwh, decimals);
  return includeUnit ? `${formatted} MWh` : formatted;
}

/**
 * Format signed error in Megawatts (e.g. +1,250 MW or -420 MW).
 */
export function formatSignedMW(
  mw: number | null | undefined,
  decimals: number = 0
): string {
  if (mw === null || mw === undefined || Number.isNaN(mw)) return '—';
  const prefix = mw > 0 ? '+' : '';
  return `${prefix}${formatNumber(mw, decimals)} MW`;
}

/**
 * Format percentage (e.g. 18.5%).
 */
export function formatPercent(
  value: number | null | undefined,
  decimals: number = 1,
  includeSymbol: boolean = true
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const formatted = formatNumber(value, decimals);
  return includeSymbol ? `${formatted}%` : formatted;
}

/**
 * Format ISO datetime string or Date object to explicit UTC timestamp.
 * Example: '2026-01-15 09:00 UTC'
 */
export function formatUtcDateTime(
  isoDateOrObj: string | Date | null | undefined,
  includeSeconds: boolean = false
): string {
  if (!isoDateOrObj) return '—';
  const date = typeof isoDateOrObj === 'string' ? new Date(isoDateOrObj) : isoDateOrObj;
  if (Number.isNaN(date.getTime())) return '—';

  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');

  if (includeSeconds) {
    const seconds = String(date.getUTCSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} UTC`;
  }
  return `${year}-${month}-${day} ${hours}:${minutes} UTC`;
}

/**
 * Format ISO datetime or Date to clock time with explicit UTC.
 * Example: '09:00 UTC'
 */
export function formatUtcTime(
  isoDateOrObj: string | Date | null | undefined
): string {
  if (!isoDateOrObj) return '—';
  const date = typeof isoDateOrObj === 'string' ? new Date(isoDateOrObj) : isoDateOrObj;
  if (Number.isNaN(date.getTime())) return '—';

  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  return `${hours}:${minutes} UTC`;
}

/**
 * Format settlement period label with time interval.
 * Example: 'SP 17 (08:00 – 08:30 UTC)'
 */
export function formatSettlementPeriod(
  periodNumber: number,
  startTimeIso?: string
): string {
  if (startTimeIso) {
    const date = new Date(startTimeIso);
    if (!Number.isNaN(date.getTime())) {
      const startH = String(date.getUTCHours()).padStart(2, '0');
      const startM = String(date.getUTCMinutes()).padStart(2, '0');
      // Half-hour period end
      const endDate = new Date(date.getTime() + 30 * 60 * 1000);
      const endH = String(endDate.getUTCHours()).padStart(2, '0');
      const endM = String(endDate.getUTCMinutes()).padStart(2, '0');
      return `SP ${periodNumber} (${startH}:${startM}–${endH}:${endM} UTC)`;
    }
  }
  return `SP ${periodNumber}`;
}

/**
 * Format lead time in hours.
 * Example: '21.5h ahead'
 */
export function formatHorizonHours(hours: number | null | undefined): string {
  if (hours === null || hours === undefined || Number.isNaN(hours)) return '—';
  return `${formatNumber(hours, 1)}h ahead`;
}
