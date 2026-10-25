import { motion } from 'motion/react';
import { Clock } from 'lucide-react';
import { MetricCard } from '../../components/ui/MetricCard.tsx';
import { formatMWh, formatMW, formatUtcDateTime } from '../../lib/format.ts';
import { staggerContainerVariants } from '../../design/motion.ts';
import type { ForecastSnapshotResponse, SafeWindSummary } from '../../types.ts';

interface SummaryStripProps {
  snapshot?: ForecastSnapshotResponse;
  safeWind?: SafeWindSummary;
  safeWindMode: 'in_sample' | 'prior_days';
  quantile: number;
}

export function SummaryStrip({
  snapshot,
  safeWind,
  safeWindMode,
  quantile,
}: SummaryStripProps) {
  // Compute volumes directly from data (NO hardcoding!)
  const periods = safeWind?.periods || [];

  // Energy in MWh: each half-hour interval represents 0.5 hours
  const totalForecastMWh = periods.reduce((acc, p) => acc + (p.forecast_mw || 0) * 0.5, 0);
  const totalSafeMWh = periods.reduce((acc, p) => acc + (p.safe_wind_mw || 0) * 0.5, 0);
  const totalProcurementMWh = periods.reduce((acc, p) => acc + (p.thermal_procurement_mw || 0) * 0.5, 0);
  const peakProcurementMW = Math.max(...periods.map((p) => p.thermal_procurement_mw || 0), 0);

  // Metadata about the forecast run
  const samplePeriod = snapshot?.periods?.find((p) => p.has_forecast && p.latest_publish_time);
  const publishedAt = samplePeriod?.latest_publish_time;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      {/* Run Lineage Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          padding: '8px 12px',
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          fontSize: 'var(--text-xs)',
          color: 'var(--color-text-secondary)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Clock size={14} style={{ color: 'var(--color-forecast)' }} />
          <span>
            <strong>Auction Decision Snapshot:</strong> Cutoff at{' '}
            <span className="tabular-nums" style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
              {snapshot?.decision_time_str || '09:00'} UTC on D-1
            </span>{' '}
            ({formatUtcDateTime(snapshot?.cutoff_time)})
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {publishedAt && (
            <span className="tabular-nums">
              Latest Run Published:{' '}
              <strong style={{ color: 'var(--color-text-primary)' }}>{formatUtcDateTime(publishedAt)}</strong> (Lead Time: 16.5–39.5h)
            </span>
          )}
          <span
            style={{
              padding: '2px 8px',
              backgroundColor: 'var(--color-safe-wind-bg)',
              color: 'var(--color-safe-wind)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              borderRadius: 'var(--radius-sm)',
              fontWeight: 600,
              fontSize: '11px',
            }}
          >
            Safe Wind: P{Math.round(quantile * 100)} ({safeWindMode === 'prior_days' ? 'Prior-Days' : 'In-Sample'})
          </span>
        </div>
      </div>

      {/* KPI Cards Grid */}
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
        <MetricCard
          label="Forecast Day Volume"
          rawValue={totalForecastMWh}
          formattedDisplay={formatMWh(totalForecastMWh, 0, false)}
          unit="MWh"
          subtitle="Total Day-Ahead WINDFOR"
          accentColor="var(--color-forecast)"
          tooltip="Integrated day-ahead forecast energy volume (MW * 0.5h across 48 settlement periods)."
        />

        <MetricCard
          label="Conservative 'Safe' Volume"
          rawValue={totalSafeMWh}
          formattedDisplay={formatMWh(totalSafeMWh, 0, false)}
          unit="MWh"
          deltaText={`P${Math.round(quantile * 100)} Derated`}
          deltaType="positive"
          subtitle={`Derated by ${safeWind?.shortfall_quantile_mw ? formatMW(safeWind.shortfall_quantile_mw, 0) : 'buffer'}`}
          accentColor="var(--color-safe-wind)"
          tooltip="Guaranteed generation volume counting on wind after subtracting the empirical shortfall buffer."
        />

        <MetricCard
          label="Peak Extra Procurement"
          rawValue={peakProcurementMW}
          formattedDisplay={formatMW(peakProcurementMW, 0, false)}
          unit="MW"
          deltaText={peakProcurementMW > 0 ? 'Thermal Backup' : 'Zero Deficit'}
          deltaType={peakProcurementMW > 0 ? 'warning' : 'positive'}
          subtitle="Max required backup in single SP"
          accentColor="var(--color-shortfall)"
          tooltip="Maximum single-period deficit between the nominal forecast and the safe commitment, requiring flexible thermal/battery reserve."
        />

        <MetricCard
          label="Total Backup Energy"
          rawValue={totalProcurementMWh}
          formattedDisplay={formatMWh(totalProcurementMWh, 0, false)}
          unit="MWh"
          subtitle="Total procurement volume"
          accentColor="var(--color-shortfall)"
          tooltip="Cumulative volume of replacement thermal generation or storage required across the 24-hour delivery schedule."
        />
      </motion.div>
    </div>
  );
}
