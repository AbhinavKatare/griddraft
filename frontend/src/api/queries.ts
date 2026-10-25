/**
 * TanStack React Query hooks for UK Wind Forecast Monitoring API endpoints.
 * Configured with keepPreviousData, sensible cache retention, and error typing.
 */

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { apiClient } from './client.ts';
import type {
  ErrorByHorizonResponse,
  ErrorByHourResponse,
  ForecastSnapshotResponse,
  MetaResponse,
  MonthlyKPIs,
  SafeWindSummary,
  TemporalResolution,
  TimeseriesResponse,
} from '../types.ts';

// 5 minutes stale time for read-heavy analytical cache
const ANALYTICS_STALE_TIME = 5 * 60 * 1000;
const META_STALE_TIME = 15 * 60 * 1000;

export const queryKeys = {
  meta: () => ['meta'] as const,
  health: () => ['health'] as const,
  timeseries: (start: string, end: string, decisionTime: string, res: TemporalResolution) =>
    ['timeseries', start, end, decisionTime, res] as const,
  forecastSnapshot: (date: string, decisionTime: string) =>
    ['forecastSnapshot', date, decisionTime] as const,
  metrics: (decisionTime: string, start?: string, end?: string) =>
    ['metrics', decisionTime, start || 'all', end || 'all'] as const,
  errorByHorizon: (source: string, decisionTime: string) =>
    ['errorByHorizon', source, decisionTime] as const,
  errorByHour: (decisionTime: string) =>
    ['errorByHour', decisionTime] as const,
  safeWind: (date: string, decisionTime: string, quantile: number, mode: string) =>
    ['safeWind', date, decisionTime, quantile, mode] as const,
};

/**
 * Hook: Ingestion Metadata & Coverage Boundaries
 */
export function useMeta() {
  return useQuery<MetaResponse>({
    queryKey: queryKeys.meta(),
    queryFn: () => apiClient<MetaResponse>('/api/v1/meta'),
    staleTime: META_STALE_TIME,
    retry: 2,
  });
}

/**
 * Hook: Aligned Timeseries (with Downsampling)
 */
export function useTimeseries(
  startDate: string = '2026-01-01',
  endDate: string = '2026-01-31',
  decisionTime: string = '09:00',
  resolution: TemporalResolution = '30m'
) {
  return useQuery<TimeseriesResponse>({
    queryKey: queryKeys.timeseries(startDate, endDate, decisionTime, resolution),
    queryFn: () =>
      apiClient<TimeseriesResponse>('/api/v1/timeseries', {
        params: {
          start_date: startDate,
          end_date: endDate,
          decision_time: decisionTime,
          resolution,
        },
      }),
    staleTime: ANALYTICS_STALE_TIME,
    placeholderData: keepPreviousData,
    retry: (count, err: any) => Boolean(err?.status >= 500 && count < 1),
  });
}

/**
 * Hook: Point-in-time Day-Ahead Forecast Snapshot for Single Delivery Day
 */
export function useForecastSnapshot(
  deliveryDate: string = '2026-01-15',
  decisionTime: string = '09:00'
) {
  return useQuery<ForecastSnapshotResponse>({
    queryKey: queryKeys.forecastSnapshot(deliveryDate, decisionTime),
    queryFn: () =>
      apiClient<ForecastSnapshotResponse>('/api/v1/forecast-snapshot', {
        params: {
          delivery_date: deliveryDate,
          decision_time: decisionTime,
        },
      }),
    staleTime: ANALYTICS_STALE_TIME,
    placeholderData: keepPreviousData,
    retry: (count, err: any) => Boolean(err?.status >= 500 && count < 1),
  });
}

/**
 * Hook: Aggregate Forecast Accuracy KPIs
 */
export function useMetrics(
  decisionTime: string = '09:00',
  startDate?: string,
  endDate?: string
) {
  return useQuery<MonthlyKPIs>({
    queryKey: queryKeys.metrics(decisionTime, startDate, endDate),
    queryFn: () =>
      apiClient<MonthlyKPIs>('/api/v1/metrics', {
        params: {
          decision_time: decisionTime,
          start_date: startDate,
          end_date: endDate,
        },
      }),
    staleTime: ANALYTICS_STALE_TIME,
    placeholderData: keepPreviousData,
    retry: (count, err: any) => Boolean(err?.status >= 500 && count < 1),
  });
}

/**
 * Hook: Error Stratified across Horizon Buckets
 */
export function useErrorByHorizon(
  source: 'all' | 'decision' = 'all',
  decisionTime: string = '09:00'
) {
  return useQuery<ErrorByHorizonResponse>({
    queryKey: queryKeys.errorByHorizon(source, decisionTime),
    queryFn: () =>
      apiClient<ErrorByHorizonResponse>('/api/v1/error-by-horizon', {
        params: {
          source,
          decision_time: decisionTime,
        },
      }),
    staleTime: ANALYTICS_STALE_TIME,
    placeholderData: keepPreviousData,
    retry: (count, err: any) => Boolean(err?.status >= 500 && count < 1),
  });
}

/**
 * Hook: Diurnal Error across Hours of Day (0-23)
 */
export function useErrorByHour(decisionTime: string = '09:00') {
  return useQuery<ErrorByHourResponse>({
    queryKey: queryKeys.errorByHour(decisionTime),
    queryFn: () =>
      apiClient<ErrorByHourResponse>('/api/v1/error-by-hour', {
        params: {
          decision_time: decisionTime,
        },
      }),
    staleTime: ANALYTICS_STALE_TIME,
    placeholderData: keepPreviousData,
    retry: (count, err: any) => Boolean(err?.status >= 500 && count < 1),
  });
}

/**
 * Hook: Safe Wind Commitment & Backup Procurement Profile
 */
export function useSafeWind(
  deliveryDate: string = '2026-01-15',
  decisionTime: string = '09:00',
  quantile: number = 0.90,
  mode: 'in_sample' | 'prior_days' = 'in_sample'
) {
  return useQuery<SafeWindSummary>({
    queryKey: queryKeys.safeWind(deliveryDate, decisionTime, quantile, mode),
    queryFn: () =>
      apiClient<SafeWindSummary>('/api/v1/risk/safe-wind', {
        params: {
          delivery_date: deliveryDate,
          decision_time: decisionTime,
          quantile,
          mode,
        },
      }),
    staleTime: ANALYTICS_STALE_TIME,
    placeholderData: keepPreviousData,
    retry: 1,
  });
}

/**
 * Hook: Service Health Check
 */
export function useHealth() {
  return useQuery<{ status: string; environment?: string }>({
    queryKey: queryKeys.health(),
    queryFn: () => apiClient('/health'),
    staleTime: 60 * 1000,
    retry: 1,
  });
}
