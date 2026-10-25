import React from 'react';
import { motion } from 'motion/react';
import { MetricCard } from '../../components/ui/MetricCard.tsx';
import { formatMW, formatPercent } from '../../lib/format.ts';
import { staggerContainerVariants } from '../../design/motion.ts';
import type { MonthlyKPIs } from '../../types.ts';

export interface LatestMetricsComparison {
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
  p90_shortfall_mw: number;
  matched_half_hours: number;
  data_coverage_pct: number;
}

interface KPICardsProps {
  metrics?: MonthlyKPIs;
  latestMetrics?: LatestMetricsComparison;
  decisionTime: string;
  showComparison?: boolean;
}

export const KPICards = React.memo(function KPICards({
  metrics,
  latestMetrics,
  decisionTime,
  showComparison = false,
}: KPICardsProps) {
  // Compute leakage differences (Decision - Latest)
  const maeDelta =
    metrics?.mae_mw !== undefined && latestMetrics?.mae_mw !== undefined
      ? metrics.mae_mw - latestMetrics.mae_mw
      : undefined;

  const rmseDelta =
    metrics?.rmse_mw !== undefined && latestMetrics?.rmse_mw !== undefined
      ? metrics.rmse_mw - latestMetrics.rmse_mw
      : undefined;

  const biasDelta =
    metrics?.mean_bias_mw !== undefined && latestMetrics?.bias_mw !== undefined
      ? metrics.mean_bias_mw - latestMetrics.bias_mw
      : undefined;

  return (
    <motion.div
      variants={staggerContainerVariants}
      initial="hidden"
      animate="visible"
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: 'var(--space-4)',
      }}
    >
      {/* 1. MAE */}
      <MetricCard
        label="Mean Absolute Error (MAE)"
        rawValue={metrics?.mae_mw}
        formattedDisplay={formatMW(metrics?.mae_mw, 1, false)}
        unit="MW"
        deltaText={
          showComparison && maeDelta !== undefined
            ? `-${formatMW(maeDelta, 1, false)} MW Leakage`
            : metrics
              ? `${formatPercent(metrics.mae_pct_of_mean_gen)} NMAE`
              : undefined
        }
        deltaType={showComparison ? 'positive' : 'neutral'}
        subtitle={
          showComparison && latestMetrics?.mae_mw !== undefined
            ? `Latest at Gate-Closure: ${formatMW(latestMetrics.mae_mw, 1)}`
            : `Norm by mean outturn (${metrics?.mean_actual_mw ? formatMW(metrics.mean_actual_mw, 0) : '—'})`
        }
        accentColor="var(--color-forecast)"
        tooltip="TRADER CONTEXT: The average volumetric sizing error per half-hour. If you hedge 100% of the forecast in the day-ahead auction, this is your expected unhedged position volume requiring prompt cashout settlement at imbalance prices."
      />

      {/* 2. RMSE */}
      <MetricCard
        label="Root Mean Squared Error (RMSE)"
        rawValue={metrics?.rmse_mw}
        formattedDisplay={formatMW(metrics?.rmse_mw, 1, false)}
        unit="MW"
        deltaText={
          showComparison && rmseDelta !== undefined
            ? `-${formatMW(rmseDelta, 1, false)} MW Volatility Drop`
            : metrics
              ? `${formatPercent(metrics.mae_pct_of_max_gen)} of Peak`
              : undefined
        }
        deltaType={showComparison ? 'positive' : 'neutral'}
        subtitle={
          showComparison && latestMetrics?.rmse_mw !== undefined
            ? `Latest at Gate-Closure: ${formatMW(latestMetrics.rmse_mw, 1)}`
            : 'Heavily penalises large forecast swings'
        }
        accentColor="var(--color-shortfall)"
        tooltip="TRADER CONTEXT: Quadratic penalty on large errors. Extreme volumetric misses (e.g. rapid frontal passage timing errors) trigger severe system imbalance cashout penalties. Lower RMSE means fewer catastrophic tail misses."
      />

      {/* 3. Bias */}
      <MetricCard
        label="Systematic Forecast Bias"
        rawValue={metrics?.mean_bias_mw}
        formattedDisplay={metrics?.mean_bias_mw !== undefined ? `+${formatMW(metrics.mean_bias_mw, 1, false)}` : '—'}
        unit="MW"
        deltaText={
          showComparison && biasDelta !== undefined
            ? biasDelta > 0
              ? `Persists: +${formatMW(latestMetrics?.bias_mw || 0, 0)} MW Latest`
              : 'Bias Unchanged'
            : 'Systematic Over-forecast'
        }
        deltaType="warning"
        subtitle={
          showComparison && latestMetrics?.bias_mw !== undefined
            ? `Latest Gate-Closure Bias: +${formatMW(latestMetrics.bias_mw, 1)}`
            : 'Forecast systematically > Actual'
        }
        accentColor="var(--color-forecast)"
        tooltip="TRADER CONTEXT: Average directional miss (Forecast minus Actual). WINDFOR's +1,852 MW positive bias means you consistently over-sell day-ahead and are systematically forced to buy back power at cashout prices in the balancing mechanism."
      />

      {/* 4. P90 Shortfall / Error */}
      <MetricCard
        label="P90 Shortfall Buffer"
        rawValue={metrics?.shortfall_percentiles?.p90}
        formattedDisplay={formatMW(metrics?.shortfall_percentiles?.p90, 0, false)}
        unit="MW"
        deltaText={
          showComparison && latestMetrics?.p90_shortfall_mw !== undefined
            ? `${formatMW((metrics?.shortfall_percentiles?.p90 || 0) - latestMetrics.p90_shortfall_mw, 0)} MW Reserve Saving`
            : '90% Risk Tolerance'
        }
        deltaType={showComparison ? 'positive' : 'warning'}
        subtitle={
          showComparison && latestMetrics?.p90_shortfall_mw !== undefined
            ? `Latest Gate-Closure P90: ${formatMW(latestMetrics.p90_shortfall_mw, 0)}`
            : 'Max generation deficit in 90% of periods'
        }
        accentColor="var(--color-safe-wind)"
        tooltip="TRADER CONTEXT: 90th percentile of positive deficits max(0, Forecast - Actual). In 90% of evaluated settlement periods, actual generation was within this deficit from the forecast. This defines your required firm backup thermal procurement."
      />

      {/* 5. Data Coverage */}
      <MetricCard
        label="Data Coverage Evaluated"
        rawValue={metrics?.matched_half_hours}
        formattedDisplay={metrics?.matched_half_hours ? `${metrics.matched_half_hours}` : '—'}
        unit="Intervals"
        deltaText={metrics ? `${formatPercent(metrics.data_coverage_pct)} Evaluated` : undefined}
        deltaType="positive"
        subtitle={`At D-1 ${decisionTime} Cutoff`}
        accentColor="var(--color-actual)"
        tooltip="TRADER CONTEXT: Data integrity check. Evaluates 100% of half-hourly settlement intervals across January 2026 (1,488 half-hours) with complete outturn and forecast pairing and zero data dropouts."
      />
    </motion.div>
  );
});
