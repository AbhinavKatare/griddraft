/**
 * Core domain types and API contract types for UK Wind Forecast Monitoring.
 * Types are derived directly from the OpenAPI schema and backend models.
 */

import type { components } from './api/schema.d.ts';

// Extract API schema types directly from openapi-typescript
export type BacktestResult = components['schemas']['BacktestResult'];
export type BufferDecomposition = components['schemas']['BufferDecomposition'];
export type ErrorByHorizonResponse = components['schemas']['ErrorByHorizonResponse'];
export type ErrorByHourResponse = components['schemas']['ErrorByHourResponse'];
export type ForecastSnapshotResponse = components['schemas']['ForecastSnapshotResponse'];
export type HalfHourForecastPoint = components['schemas']['HalfHourForecastPoint'];
export type HealthResponse = components['schemas']['HealthResponse'];
export type MetaResponse = components['schemas']['MetaResponse'];
export type MonthlyKPIs = components['schemas']['MonthlyKPIs'];
export type Percentiles = components['schemas']['Percentiles'];
export type SafeWindPeriod = components['schemas']['SafeWindPeriod'];
export type SafeWindSummary = components['schemas']['SafeWindSummary'];
export type TimeseriesPoint = components['schemas']['TimeseriesPoint'];
export type TimeseriesResponse = components['schemas']['TimeseriesResponse'];

// Stratified Buckets and Diagnostic Models
export interface HorizonBucket {
  min_horizon_hours: number;
  max_horizon_hours: number;
  sample_count: number;
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
  [key: string]: unknown;
}

export interface HourOfDayError {
  hour: number;
  sample_count: number;
  mean_actual_mw: number;
  mean_forecast_mw: number;
  bias_mw: number;
  mae_mw: number;
  rmse_mw: number;
  [key: string]: unknown;
}

export interface DailyKPI {
  date: string;
  mean_actual_mw: number;
  mean_forecast_mw: number;
  bias_mw: number;
  mae_mw: number;
  rmse_mw: number;
}

export interface ProblemDetail {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  invalid_params?: { name: string; reason: string }[];
}

// App UI State Types
export type ViewTab = 'decision' | 'accuracy' | 'methodology';

export type CutoffPreset = '08:00' | '09:00' | '10:00' | 'custom';

export type ForecastMode = 'decision_time' | 'latest' | 'fixed_horizon';

export type SafeWindMode = 'in_sample' | 'prior_days';

export type QuantilePreset = 0.50 | 0.90 | 0.95;

export type TemporalResolution = '30m' | '1h' | '3h';

export interface AppUrlState {
  view: ViewTab;
  deliveryDate: string;        // 'YYYY-MM-DD' (e.g. '2026-01-15')
  decisionTime: string;        // 'HH:MM' (e.g. '09:00')
  forecastMode: ForecastMode;
  showLeakyLine: boolean;
  safeWindMode: SafeWindMode;
  quantile: number;            // 0.50, 0.90, 0.95
  resolution: TemporalResolution;
}

export interface ToastMessage {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  timestamp: number;
}
