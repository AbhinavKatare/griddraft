import { motion } from 'motion/react';
import { MetricCard } from '../../components/ui/MetricCard.tsx';
import { formatMW, formatPercent } from '../../lib/format.ts';
import { staggerContainerVariants } from '../../design/motion.ts';
import type { MonthlyKPIs } from '../../types.ts';

interface KPICardsProps {
  metrics?: MonthlyKPIs;
  decisionTime: string;
}

export function KPICards({ metrics, decisionTime }: KPICardsProps) {
  return (
    <motion.div
      variants={staggerContainerVariants}
      initial="hidden"
      animate="visible"
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 'var(--space-4)',
      }}
    >
      {/* 1. MAE */}
      <MetricCard
        label="Mean Absolute Error (MAE)"
        rawValue={metrics?.mae_mw}
        formattedDisplay={formatMW(metrics?.mae_mw, 1, false)}
        unit="MW"
        deltaText={metrics ? `${formatPercent(metrics.mae_pct_of_mean_gen)} NMAE` : undefined}
        deltaType="neutral"
        subtitle={`Norm by mean outturn (${metrics?.mean_actual_mw ? formatMW(metrics.mean_actual_mw, 0) : '—'})`}
        accentColor="var(--color-forecast)"
        tooltip="Average absolute magnitude of forecast error across all evaluated half-hours. Lower is better."
      />

      {/* 2. RMSE */}
      <MetricCard
        label="Root Mean Squared Error"
        rawValue={metrics?.rmse_mw}
        formattedDisplay={formatMW(metrics?.rmse_mw, 1, false)}
        unit="MW"
        deltaText={metrics ? `${formatPercent(metrics.mae_pct_of_max_gen)} of Max` : undefined}
        deltaType="neutral"
        subtitle="Heavily penalises large volumetric swings"
        accentColor="var(--color-shortfall)"
        tooltip="Root Mean Squared Error. By squaring errors, this metric penalises large extreme volumetric swings."
      />

      {/* 3. Bias */}
      <MetricCard
        label="Systematic Bias"
        rawValue={metrics?.mean_bias_mw}
        formattedDisplay={metrics?.mean_bias_mw !== undefined ? `+${formatMW(metrics.mean_bias_mw, 1, false)}` : '—'}
        unit="MW"
        deltaText="Over-forecast"
        deltaType="warning"
        subtitle="Positive = Forecast > Actual"
        accentColor="var(--color-forecast)"
        tooltip="Mean signed error (Forecast - Actual). A positive value indicates that WINDFOR systematically overestimated outturn."
      />

      {/* 4. P90 Shortfall */}
      <MetricCard
        label="P90 Deficit Shortfall"
        rawValue={metrics?.shortfall_percentiles?.p90}
        formattedDisplay={formatMW(metrics?.shortfall_percentiles?.p90, 0, false)}
        unit="MW"
        deltaText="90% Confidence"
        deltaType="warning"
        subtitle="Max deficit in 90% of intervals"
        accentColor="var(--color-safe-wind)"
        tooltip="90th percentile of positive deficits max(0, Forecast - Actual). In 90% of half-hours, the generation deficit was below this figure."
      />

      {/* 5. Safe Commitment Coverage */}
      <MetricCard
        label="Delivery Intervals Evaluated"
        rawValue={metrics?.matched_half_hours}
        formattedDisplay={metrics?.matched_half_hours ? `${metrics.matched_half_hours}` : '—'}
        unit="Intervals"
        deltaText={metrics ? `${formatPercent(metrics.data_coverage_pct)} Coverage` : undefined}
        deltaType="positive"
        subtitle={`At D-1 ${decisionTime} Cutoff`}
        accentColor="var(--color-actual)"
        tooltip="Number of settlement half-hours evaluated in January 2026. Deficit-free intervals had actual generation >= forecast."
      />
    </motion.div>
  );
}
