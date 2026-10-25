import { useMemo } from 'react';
import { KPICards } from './KPICards.tsx';
import { BiasAlertBanner } from './BiasAlertBanner.tsx';
import { DailyBiasStrip } from './DailyBiasStrip.tsx';
import { ErrorByHorizonChart } from './ErrorByHorizonChart.tsx';
import { ErrorByHourChart } from './ErrorByHourChart.tsx';
import { ErrorHistogram } from './ErrorHistogram.tsx';
import { ErrorBanner } from '../../components/ui/ErrorBanner.tsx';
import { useMetrics, useTimeseries } from '../../api/queries.ts';
import type { AppUrlState, DailyKPI } from '../../types.ts';

interface AccuracyViewProps {
  state: AppUrlState;
  onSelectDate: (date: string) => void;
}

export function AccuracyView({ state, onSelectDate }: AccuracyViewProps) {
  const { data: metrics, error: metricsError, refetch: refetchMetrics } = useMetrics(state.decisionTime);
  const { data: timeseriesData } = useTimeseries('2026-01-01', '2026-01-31', state.decisionTime, '30m');

  // Aggregate daily KPIs across all 31 delivery days from timeseries data
  const dailyKpis: DailyKPI[] = useMemo(() => {
    const points = timeseriesData?.data || [];
    if (!points.length) return [];

    const grouped = new Map<string, typeof points>();
    points.forEach((p) => {
      const d = p.settlement_date;
      if (!grouped.has(d)) grouped.set(d, []);
      grouped.get(d)!.push(p);
    });

    const result: DailyKPI[] = [];
    grouped.forEach((dayPoints, date) => {
      const actuals = dayPoints.map((p) => p.actual_mw).filter((v): v is number => v !== null && v !== undefined);
      const forecasts = dayPoints.map((p) => p.decision_forecast_mw).filter((v): v is number => v !== null && v !== undefined);
      const errors = dayPoints.map((p) => p.error_mw).filter((v): v is number => v !== null && v !== undefined);
      const absErrors = dayPoints.map((p) => p.abs_error_mw).filter((v): v is number => v !== null && v !== undefined);

      const meanActual = actuals.length ? actuals.reduce((a, b) => a + b, 0) / actuals.length : 0;
      const meanForecast = forecasts.length ? forecasts.reduce((a, b) => a + b, 0) / forecasts.length : 0;
      const meanBias = errors.length ? errors.reduce((a, b) => a + b, 0) / errors.length : 0;
      const mae = absErrors.length ? absErrors.reduce((a, b) => a + b, 0) / absErrors.length : 0;
      const rmse = errors.length ? Math.sqrt(errors.reduce((a, b) => a + b * b, 0) / errors.length) : 0;

      result.push({
        date,
        mean_actual_mw: Math.round(meanActual * 10) / 10,
        mean_forecast_mw: Math.round(meanForecast * 10) / 10,
        bias_mw: Math.round(meanBias * 10) / 10,
        mae_mw: Math.round(mae * 10) / 10,
        rmse_mw: Math.round(rmse * 10) / 10,
      });
    });

    return result.sort((a, b) => a.date.localeCompare(b.date));
  }, [timeseriesData]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Error state */}
      {metricsError && <ErrorBanner error={metricsError as Error} onRetry={() => refetchMetrics()} />}

      {/* Systematic Bias Advisory Banner */}
      <BiasAlertBanner metrics={metrics} decisionTime={state.decisionTime} />

      {/* Monthly Trading KPI Cards */}
      <KPICards metrics={metrics} decisionTime={state.decisionTime} />

      {/* Daily Bias Strip across 31 Days */}
      <DailyBiasStrip
        dailyKpis={dailyKpis}
        selectedDate={state.deliveryDate}
        onSelectDate={onSelectDate}
      />

      {/* Horizon Error & Hour of Day Error Side-by-Side Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))',
          gap: 'var(--space-6)',
        }}
      >
        <ErrorByHorizonChart decisionTime={state.decisionTime} />
        <ErrorByHourChart decisionTime={state.decisionTime} />
      </div>

      {/* Error Distribution Histogram */}
      <ErrorHistogram decisionTime={state.decisionTime} />
    </div>
  );
}
