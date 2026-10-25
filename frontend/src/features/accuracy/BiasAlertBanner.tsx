import { AlertCircle } from 'lucide-react';
import { formatMW, formatPercent } from '../../lib/format.ts';
import type { MonthlyKPIs } from '../../types.ts';

interface BiasAlertBannerProps {
  metrics?: MonthlyKPIs;
  decisionTime: string;
  positiveDays?: number;
  totalDays?: number;
}

export function BiasAlertBanner({
  metrics,
  decisionTime,
  positiveDays = 27,
  totalDays = 31,
}: BiasAlertBannerProps) {
  const biasMw = metrics?.mean_bias_mw ?? 1851.9;
  const nmaeMean = metrics?.mae_pct_of_mean_gen ?? 18.52;

  return (
    <div
      role="region"
      aria-label="Systematic Over-forecast Bias Warning"
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderLeft: '4px solid var(--color-forecast)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-4) var(--space-5)',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 'var(--space-4)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div style={{ color: 'var(--color-forecast)', marginTop: '2px', flexShrink: 0 }}>
        <AlertCircle size={20} />
      </div>

      <div style={{ flex: 1, fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            Systematic Over-Forecast Offset (D-1 {decisionTime} Cutoff)
          </h3>
          <span
            className="tabular-nums"
            style={{
              padding: '2px 8px',
              backgroundColor: 'var(--color-forecast-bg)',
              color: 'var(--color-forecast)',
              borderRadius: 'var(--radius-sm)',
              fontWeight: 600,
              fontSize: '11px',
            }}
          >
            Bias: +{formatMW(biasMw)} ({formatPercent(nmaeMean)} NMAE)
          </span>
        </div>

        <p>
          Throughout January 2026, National Grid ESO WINDFOR forecasts systematically exceeded metered FUELHH wind generation
          across <strong>{positiveDays} of {totalDays} days</strong> ({formatPercent((positiveDays / (totalDays || 1)) * 100)}).
          This bias persists across both long lead times and short delivery horizons (0–2h).
        </p>
        <p style={{ marginTop: '4px', fontStyle: 'italic', color: 'var(--color-text-muted)' }}>
          <strong>Note on causality:</strong> The underlying physical cause of this offset cannot be determined solely from public
          BMRS aggregate feeds; plausible hypotheses include embedded unmetered distribution-connected wind generation,
          system operator balancing actions under Bid-Offer Acceptances (BOAs), or NWP turbine power curve calibration differences.
        </p>
      </div>
    </div>
  );
}
