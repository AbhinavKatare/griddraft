import { useMemo, useState } from 'react';
import { KPICards, type LatestMetricsComparison } from './KPICards.tsx';
import { BiasAlertBanner } from './BiasAlertBanner.tsx';
import { DailyMaeTrendChart, type DailyComparisonPoint } from './DailyMaeTrendChart.tsx';
import { DailyBiasStrip } from './DailyBiasStrip.tsx';
import { ErrorByHorizonChart } from './ErrorByHorizonChart.tsx';
import { ErrorByHourChart } from './ErrorByHourChart.tsx';
import { ErrorHistogram } from './ErrorHistogram.tsx';
import { ErrorBanner } from '../../components/ui/ErrorBanner.tsx';
import { SegmentedControl } from '../../components/ui/SegmentedControl.tsx';
import { useMetrics, useTimeseries } from '../../api/queries.ts';
import type { AppUrlState } from '../../types.ts';

interface AccuracyViewProps {
  state: AppUrlState;
  onSelectDate: (date: string) => void;
}

export function AccuracyView({ state, onSelectDate }: AccuracyViewProps) {
  // Comparison toggle between "Decision-Time Forecast" and "Latest Pre-Delivery Forecast"
  const [evaluationMode, setEvaluationMode] = useState<'decision' | 'compare'>('compare');
  const showComparison = evaluationMode === 'compare';

  const { data: metrics, error: metricsError, refetch: refetchMetrics } = useMetrics(state.decisionTime);
  const { data: timeseriesData } = useTimeseries('2026-01-01', '2026-01-31', state.decisionTime, '30m');

  // Compute aggregate Latest Forecast metrics across all 1,488 intervals to demonstrate leakage difference
  const latestMetrics: LatestMetricsComparison | undefined = useMemo(() => {
    const points = timeseriesData?.data || [];
    if (!points.length) return undefined;

    const validPairs = points.filter(
      (p) => p.actual_mw !== null && p.latest_forecast_mw !== null
    );

    if (!validPairs.length) return undefined;

    let sumAbsErr = 0;
    let sumSqErr = 0;
    let sumBias = 0;
    const shortfalls: number[] = [];

    validPairs.forEach((p) => {
      const err = p.latest_forecast_mw! - p.actual_mw!;
      const absErr = Math.abs(err);
      const sf = Math.max(0, err);

      sumAbsErr += absErr;
      sumSqErr += err * err;
      sumBias += err;
      shortfalls.push(sf);
    });

    const count = validPairs.length;
    shortfalls.sort((a, b) => a - b);
    const p90Idx = Math.floor(0.9 * shortfalls.length);
    const p90Shortfall = shortfalls[Math.min(p90Idx, shortfalls.length - 1)];

    return {
      mae_mw: Math.round((sumAbsErr / count) * 10) / 10,
      rmse_mw: Math.round(Math.sqrt(sumSqErr / count) * 10) / 10,
      bias_mw: Math.round((sumBias / count) * 10) / 10,
      p90_shortfall_mw: Math.round(p90Shortfall),
      matched_half_hours: count,
      data_coverage_pct: 1.0,
    };
  }, [timeseriesData]);

  // Aggregate daily KPIs across all 31 delivery days from timeseries data (including latest forecast for comparison)
  const dailyKpis: DailyComparisonPoint[] = useMemo(() => {
    const points = timeseriesData?.data || [];
    if (!points.length) return [];

    const grouped = new Map<string, typeof points>();
    points.forEach((p) => {
      const d = p.settlement_date;
      if (!grouped.has(d)) grouped.set(d, []);
      grouped.get(d)!.push(p);
    });

    const result: DailyComparisonPoint[] = [];
    grouped.forEach((dayPoints, date) => {
      const actuals = dayPoints.map((p) => p.actual_mw).filter((v): v is number => v !== null);
      const decForecasts = dayPoints.map((p) => p.decision_forecast_mw).filter((v): v is number => v !== null);
      const decErrors = dayPoints.map((p) => p.error_mw).filter((v): v is number => v !== null);
      const decAbsErrors = dayPoints.map((p) => p.abs_error_mw).filter((v): v is number => v !== null);

      const latErrors = dayPoints
        .filter((p) => p.latest_forecast_mw !== null && p.actual_mw !== null)
        .map((p) => p.latest_forecast_mw! - p.actual_mw!);
      const latAbsErrors = latErrors.map((e) => Math.abs(e));

      const meanActual = actuals.length ? actuals.reduce((a, b) => a + b, 0) / actuals.length : 0;
      const meanForecast = decForecasts.length ? decForecasts.reduce((a, b) => a + b, 0) / decForecasts.length : 0;
      const meanBias = decErrors.length ? decErrors.reduce((a, b) => a + b, 0) / decErrors.length : 0;
      const decMae = decAbsErrors.length ? decAbsErrors.reduce((a, b) => a + b, 0) / decAbsErrors.length : 0;
      const decRmse = decErrors.length ? Math.sqrt(decErrors.reduce((a, b) => a + b * b, 0) / decErrors.length) : 0;

      const latMae = latAbsErrors.length ? latAbsErrors.reduce((a, b) => a + b, 0) / latAbsErrors.length : 0;
      const latBias = latErrors.length ? latErrors.reduce((a, b) => a + b, 0) / latErrors.length : 0;

      result.push({
        date,
        day_num: parseInt(date.slice(8), 10),
        is_selected: date === state.deliveryDate,
        mean_actual_mw: Math.round(meanActual * 10) / 10,
        mean_forecast_mw: Math.round(meanForecast * 10) / 10,
        bias_mw: Math.round(meanBias * 10) / 10,
        mae_mw: Math.round(decMae * 10) / 10,
        rmse_mw: Math.round(decRmse * 10) / 10,
        latest_mae_mw: Math.round(latMae * 10) / 10,
        latest_bias_mw: Math.round(latBias * 10) / 10,
        leakage_mae_mw: Math.round((decMae - latMae) * 10) / 10,
      });
    });

    return result.sort((a, b) => a.date.localeCompare(b.date));
  }, [timeseriesData, state.deliveryDate]);

  // Compute dynamic count of days with positive bias (forecast > actual) from daily KPIs
  const positiveDays = useMemo(
    () => dailyKpis.filter((d) => d.bias_mw > 0).length,
    [dailyKpis]
  );
  const totalDays = dailyKpis.length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Error state */}
      {metricsError && <ErrorBanner error={metricsError as Error} onRetry={() => refetchMetrics()} />}

      {/* Accuracy Evaluation Controls & Comparison Mode Toggle */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-4)',
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-4) var(--space-6)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div>
          <h2 style={{ fontSize: 'var(--text-base)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            Accuracy & Verification Suite
          </h2>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Evaluating National Grid ESO / Elexon WINDFOR forecasts against settlement metered actuals across January 2026
          </p>
        </div>

        {/* Comparison Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
            Forecast Baseline:
          </span>
          <SegmentedControl<'decision' | 'compare'>
            name="accuracy-mode"
            size="sm"
            options={[
              { value: 'decision', label: `D-1 ${state.decisionTime} Decision Cutoff Only` },
              {
                value: 'compare',
                label: 'Compare with Latest Pre-Delivery',
                badge: 'Leakage Delta',
              },
            ]}
            value={evaluationMode}
            onChange={(val) => setEvaluationMode(val)}
          />
        </div>
      </div>

      {/* Systematic Bias Advisory Banner (dynamically computed from data) */}
      <BiasAlertBanner
        metrics={metrics}
        decisionTime={state.decisionTime}
        positiveDays={totalDays > 0 ? positiveDays : undefined}
        totalDays={totalDays > 0 ? totalDays : undefined}
      />

      {/* Monthly Trading KPI Cards with Trader Tooltips & Leakage Difference */}
      <KPICards
        metrics={metrics}
        latestMetrics={latestMetrics}
        decisionTime={state.decisionTime}
        showComparison={showComparison}
      />

      {/* Daily MAE Trend Across January 2026 */}
      <DailyMaeTrendChart
        dailyKpis={dailyKpis}
        selectedDate={state.deliveryDate}
        onSelectDate={onSelectDate}
        showComparison={showComparison}
      />

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
      <ErrorHistogram decisionTime={state.decisionTime} showComparison={showComparison} />
    </div>
  );
}
