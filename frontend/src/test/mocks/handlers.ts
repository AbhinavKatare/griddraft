import { http, HttpResponse } from 'msw';

export const mockMeta = {
  service: 'UK Wind Forecast Monitoring',
  version: '1.0.0',
  available_start_date: '2026-01-01',
  available_end_date: '2026-01-31',
  last_ingestion_time: '2026-01-31T23:59:59Z',
  fuelhh_rows: 1488,
  windfor_rows: 25604,
  decision_time_default: '09:00',
};

export const mockTimeseries = {
  start_date: '2026-01-15',
  end_date: '2026-01-15',
  decision_time: '09:00',
  total_points: 4,
  data: [
    {
      start_time: '2026-01-15T00:00:00Z',
      settlement_date: '2026-01-15',
      settlement_period: 1,
      actual_mw: 8200.0,
      decision_forecast_mw: 9500.0,
      latest_forecast_mw: 8400.0,
      error_mw: 1300.0,
      abs_error_mw: 1300.0,
      shortfall_mw: 1300.0,
    },
    {
      start_time: '2026-01-15T00:30:00Z',
      settlement_date: '2026-01-15',
      settlement_period: 2,
      actual_mw: 8500.0,
      decision_forecast_mw: 9600.0,
      latest_forecast_mw: 8600.0,
      error_mw: 1100.0,
      abs_error_mw: 1100.0,
      shortfall_mw: 1100.0,
    },
    {
      start_time: '2026-01-15T01:00:00Z',
      settlement_date: '2026-01-15',
      settlement_period: 3,
      actual_mw: 9100.0,
      decision_forecast_mw: 9000.0,
      latest_forecast_mw: 9050.0,
      error_mw: -100.0,
      abs_error_mw: 100.0,
      shortfall_mw: 0.0,
    },
    {
      start_time: '2026-01-15T01:30:00Z',
      settlement_date: '2026-01-15',
      settlement_period: 4,
      actual_mw: 9400.0,
      decision_forecast_mw: 9200.0,
      latest_forecast_mw: 9300.0,
      error_mw: -200.0,
      abs_error_mw: 200.0,
      shortfall_mw: 0.0,
    },
  ],
};

export const mockSnapshot = {
  delivery_date: '2026-01-15',
  decision_time_str: '09:00',
  cutoff_time: '2026-01-14T09:00:00Z',
  total_periods: 4,
  matched_periods: 4,
  periods: [
    {
      settlement_date: '2026-01-15',
      settlement_period: 1,
      start_time: '2026-01-15T00:00:00Z',
      actual_mw: 8200.0,
      forecast_mw: 9500.0,
      latest_publish_time: '2026-01-14T08:30:00Z',
      lead_time_hours: 15.5,
      error_mw: 1300.0,
      abs_error_mw: 1300.0,
      shortfall_mw: 1300.0,
      has_forecast: true,
    },
    {
      settlement_date: '2026-01-15',
      settlement_period: 2,
      start_time: '2026-01-15T00:30:00Z',
      actual_mw: 8500.0,
      forecast_mw: 9600.0,
      latest_publish_time: '2026-01-14T08:30:00Z',
      lead_time_hours: 16.0,
      error_mw: 1100.0,
      abs_error_mw: 1100.0,
      shortfall_mw: 1100.0,
      has_forecast: true,
    },
  ],
};

export const mockSafeWind = {
  quantile: 0.9,
  mode: 'in_sample',
  shortfall_quantile_mw: 2200.0,
  total_forecast_mwh: 18650.0,
  total_safe_wind_mwh: 14250.0,
  total_thermal_procurement_mwh: 4400.0,
  hedge_ratio_pct: 76.4,
  decomposition: {
    systematic_bias_mw: 1844.75,
    residual_quantile_mw: 355.25,
    total_buffer_mw: 2200.0,
  },
  periods: [
    {
      start_time: '2026-01-15T00:00:00Z',
      settlement_period: 1,
      forecast_mw: 9500.0,
      shortfall_buffer_mw: 2200.0,
      safe_wind_mw: 7300.0,
      thermal_procurement_mw: 2200.0,
      actual_mw: 8200.0,
      is_breached: false,
    },
    {
      start_time: '2026-01-15T00:30:00Z',
      settlement_period: 2,
      forecast_mw: 9600.0,
      shortfall_buffer_mw: 2200.0,
      safe_wind_mw: 7400.0,
      thermal_procurement_mw: 2200.0,
      actual_mw: 8500.0,
      is_breached: false,
    },
  ],
};

export const mockMonthlyKPIs = {
  month: '2026-01',
  decision_time_str: '09:00',
  decision_time: '09:00',
  total_possible_half_hours: 1488,
  total_half_hours: 1488,
  matched_half_hours: 1488,
  data_coverage_pct: 100.0,
  mae_mw: 2145.2,
  rmse_mw: 2615.8,
  mean_bias_mw: 1851.9,
  bias_direction: 'OVER_FORECAST',
  mae_pct_of_mean_gen: 18.52,
  mae_pct_of_max_gen: 12.05,
  mean_actual_mw: 11580.7,
  mean_forecast_mw: 13432.6,
  max_actual_mw: 17805.0,
  max_forecast_mw: 21064.0,
  abs_error_percentiles: {
    p50: 1795.5,
    p90: 4274.9,
    p99: 6359.9,
  },
  shortfall_percentiles: {
    p50: 1703.0,
    p90: 4274.9,
    p95: 4982.0,
    p99: 6359.9,
  },
};

export const mockErrorByHorizon = {
  source: 'all',
  decision_time: '09:00',
  total_revisions: 25604,
  buckets: [
    { min_horizon_hours: 0, max_horizon_hours: 6, sample_count: 3200, mae_mw: 1420.0, rmse_mw: 1810.0, bias_mw: 1210.0 },
    { min_horizon_hours: 6, max_horizon_hours: 12, sample_count: 3200, mae_mw: 1750.0, rmse_mw: 2180.0, bias_mw: 1540.0 },
    { min_horizon_hours: 12, max_horizon_hours: 18, sample_count: 3100, mae_mw: 1980.0, rmse_mw: 2450.0, bias_mw: 1720.0 },
    { min_horizon_hours: 18, max_horizon_hours: 24, sample_count: 3100, mae_mw: 2150.0, rmse_mw: 2680.0, bias_mw: 1850.0 },
    { min_horizon_hours: 24, max_horizon_hours: 36, sample_count: 5900, mae_mw: 2340.0, rmse_mw: 2920.0, bias_mw: 1940.0 },
    { min_horizon_hours: 36, max_horizon_hours: 48, sample_count: 4200, mae_mw: 2580.0, rmse_mw: 3210.0, bias_mw: 2060.0 },
    { min_horizon_hours: 48, max_horizon_hours: 66.5, sample_count: 2904, mae_mw: 2840.0, rmse_mw: 3510.0, bias_mw: 2180.0 },
  ],
};

export const mockErrorByHour = {
  decision_time: '09:00',
  total_samples: 1488,
  hours: Array.from({ length: 24 }, (_, i) => ({
    hour: i,
    mean_forecast_mw: 13000 + (i % 6) * 200,
    mean_actual_mw: 11200 + (i % 6) * 180,
    bias_mw: 1800 + (i % 4) * 50,
    mae_mw: 2100 + (i % 4) * 40,
    rmse_mw: 2650 + (i % 4) * 50,
  })),
};

export const handlers = [
  http.get('*/api/v1/meta', () => {
    return HttpResponse.json(mockMeta);
  }),

  http.get('*/api/v1/timeseries', () => {
    return HttpResponse.json(mockTimeseries);
  }),

  http.get('*/api/v1/forecast-snapshot', () => {
    return HttpResponse.json(mockSnapshot);
  }),

  http.get('*/api/v1/forecast/snapshot', () => {
    return HttpResponse.json(mockSnapshot);
  }),

  http.get('*/api/v1/risk/safe-wind', () => {
    return HttpResponse.json(mockSafeWind);
  }),

  http.get('*/api/v1/metrics', () => {
    return HttpResponse.json(mockMonthlyKPIs);
  }),

  http.get('*/api/v1/error-by-horizon', () => {
    return HttpResponse.json(mockErrorByHorizon);
  }),

  http.get('*/api/v1/metrics/error-by-horizon', () => {
    return HttpResponse.json(mockErrorByHorizon);
  }),

  http.get('*/api/v1/error-by-hour', () => {
    return HttpResponse.json(mockErrorByHour);
  }),

  http.get('*/api/v1/metrics/error-by-hour', () => {
    return HttpResponse.json(mockErrorByHour);
  }),

  http.get('*/health', () => {
    return HttpResponse.json({ status: 'healthy', version: '1.0.0', cache_loaded: true });
  }),
];
