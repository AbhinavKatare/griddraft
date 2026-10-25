import { describe, expect, it } from 'vitest';
import {
  formatHorizonHours,
  formatMW,
  formatMWh,
  formatNumber,
  formatPercent,
  formatSettlementPeriod,
  formatSignedMW,
  formatUtcDateTime,
  formatUtcTime,
} from '../lib/format.ts';

describe('format utilities', () => {
  it('formats numbers with standard separators', () => {
    expect(formatNumber(12500)).toBe('12,500');
    expect(formatNumber(12500.67, 1)).toBe('12,500.7');
    expect(formatNumber(null)).toBe('—');
    expect(formatNumber(undefined)).toBe('—');
  });

  it('formats power in Megawatts (MW)', () => {
    expect(formatMW(14250)).toBe('14,250 MW');
    expect(formatMW(14250, 0, false)).toBe('14,250');
    expect(formatMW(null)).toBe('—');
  });

  it('formats energy in Megawatt-hours (MWh)', () => {
    expect(formatMWh(285000)).toBe('285,000 MWh');
    expect(formatMWh(null)).toBe('—');
  });

  it('formats signed error with explicit +/- prefix', () => {
    expect(formatSignedMW(1450)).toBe('+1,450 MW');
    expect(formatSignedMW(-320)).toBe('-320 MW');
    expect(formatSignedMW(0)).toBe('0 MW');
    expect(formatSignedMW(null)).toBe('—');
  });

  it('formats percentages correctly', () => {
    expect(formatPercent(18.52)).toBe('18.5%');
    expect(formatPercent(18.52, 2)).toBe('18.52%');
    expect(formatPercent(null)).toBe('—');
  });

  it('formats UTC date times with explicit UTC label', () => {
    const iso = '2026-01-15T09:30:00Z';
    expect(formatUtcDateTime(iso)).toBe('2026-01-15 09:30 UTC');
    expect(formatUtcDateTime(null)).toBe('—');
  });

  it('formats UTC clock time with explicit UTC label', () => {
    const iso = '2026-01-15T14:00:00Z';
    expect(formatUtcTime(iso)).toBe('14:00 UTC');
    expect(formatUtcTime(null)).toBe('—');
  });

  it('formats settlement periods with interval windows', () => {
    expect(formatSettlementPeriod(1, '2026-01-15T00:00:00Z')).toBe('SP 1 (00:00–00:30 UTC)');
    expect(formatSettlementPeriod(17, '2026-01-15T08:00:00Z')).toBe('SP 17 (08:00–08:30 UTC)');
  });

  it('formats lead time horizon hours', () => {
    expect(formatHorizonHours(21.5)).toBe('21.5h ahead');
    expect(formatHorizonHours(null)).toBe('—');
  });
});
