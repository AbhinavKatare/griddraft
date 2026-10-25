import { Drawer } from '../../components/ui/Drawer.tsx';
import { Shield, Database, Lock, Clock, AlertTriangle } from 'lucide-react';

interface MethodologyDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MethodologyDrawer({ isOpen, onClose }: MethodologyDrawerProps) {
  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title="Methodology & Data Lineage"
      subtitle="Quantitative formulation of point-in-time forecast selection and risk derating"
      width="540px"
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
        {/* Section 1: Objective & Control Room Philosophy */}
        <div>
          <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Shield size={16} style={{ color: 'var(--color-forecast)' }} />
            1. Day-Ahead Power Trading Context
          </h4>
          <p>
            Power traders submitting buy/sell orders into the EPEX SPOT or Nord Pool UK day-ahead hourly auction (closing at 11:00 UTC on D-1)
            rely on National Grid ESO wind forecasts published via Elexon BMRS. Over-forecasting wind generation leaves traders short,
            forcing expensive imbalance cashout settlement or last-minute intraday replacement.
          </p>
        </div>

        {/* Section 2: Causal Leakage Guard */}
        <div>
          <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Lock size={16} style={{ color: 'var(--color-actual)' }} />
            2. Causal Point-in-Time Selection (No Leakage)
          </h4>
          <p>
            To faithfully reflect what information was available when trading decisions were committed, forecasts are filtered by a strict
            point-in-time invariant:
          </p>
          <div
            className="mono tabular-nums"
            style={{
              backgroundColor: 'var(--color-surface-sunken)',
              padding: '8px 12px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              margin: '8px 0',
              fontWeight: 600,
              color: 'var(--color-text-primary)',
            }}
          >
            publishTime &le; decisionCutoff &le; settlementStartTime
          </div>
          <p>
            For a target delivery day D, the default auction decision cutoff is <strong>09:00 UTC on D-1</strong> (cutoff day offset = 1).
            Any revision published after 09:00 UTC is strictly excluded, preventing information leakage.
          </p>
        </div>

        {/* Section 3: Safe Wind Formulation & Decomposition */}
        <div>
          <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Clock size={16} style={{ color: 'var(--color-safe-wind)' }} />
            3. Conservative 'Safe Wind' Derating
          </h4>
          <p>
            Downside shortfall is defined as:
          </p>
          <div
            className="mono tabular-nums"
            style={{
              backgroundColor: 'var(--color-surface-sunken)',
              padding: '6px 10px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              margin: '6px 0',
              fontWeight: 600,
            }}
          >
            Shortfall = max(0, Forecast - Actual)
          </div>
          <p>
            The derating buffer B is the (1 - &alpha;) empirical shortfall quantile (e.g. P90 quantile). The "Safe Wind to Count On" is:
          </p>
          <div
            className="mono tabular-nums"
            style={{
              backgroundColor: 'var(--color-surface-sunken)',
              padding: '6px 10px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              margin: '6px 0',
              fontWeight: 600,
              color: 'var(--color-safe-wind)',
            }}
          >
            SafeWind(t) = max(0, Forecast(t) - Buffer(&alpha;))
          </div>
          <p>
            <strong>Buffer Decomposition:</strong> The buffer decomposes into systematic bias (&mu; shortfall) and stochastic residual risk (Q<sub>&alpha;</sub> residual):
          </p>
          <div
            className="mono tabular-nums"
            style={{
              backgroundColor: 'var(--color-surface-sunken)',
              padding: '6px 10px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              margin: '6px 0',
              fontWeight: 600,
            }}
          >
            Buffer(&alpha;) = SystematicBias + ResidualQuantile(&alpha;)
          </div>
        </div>

        {/* Section 4: In-Sample vs Prior-Days Toggle */}
        <div>
          <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Database size={16} style={{ color: 'var(--color-forecast)' }} />
            4. In-Sample vs. Prior-Days Mode
          </h4>
          <ul style={{ paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <li>
              <strong>In-Sample:</strong> Evaluates quantile across the entire benchmark month (January 2026, 1,488 half-hours).
            </li>
            <li>
              <strong>Prior-Days:</strong> Dynamically calculates buffer using strictly prior days (d &lt; D). On Day 1, falls back to in-sample or zero history.
            </li>
          </ul>
        </div>

        {/* Section 5: Normalisation Standards */}
        <div>
          <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={16} style={{ color: 'var(--color-shortfall)' }} />
            5. Outturn Normalisation Standards
          </h4>
          <p>
            Because UK wind nameplate capacity is not explicitly defined in BMRS stream feeds, NMAE is normalised by observed actuals:
          </p>
          <ul style={{ paddingLeft: '16px', marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <li>
              <strong>NMAE (Mean Actual):</strong> MAE / Mean Actual = 2,145.17 / 11,580.74 MW = <strong>18.52%</strong>
            </li>
            <li>
              <strong>NMAE (Max Actual):</strong> MAE / Max Observed Actual = 2,145.17 / 17,805.00 MW = <strong>12.05%</strong>
            </li>
          </ul>
        </div>
      </div>
    </Drawer>
  );
}
