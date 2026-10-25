import { useState } from 'react';
import { SummaryStrip } from './SummaryStrip.tsx';
import { HeroChart } from './HeroChart.tsx';
import { ProcurementBars } from './ProcurementBars.tsx';
import { DayDataTable } from './DayDataTable.tsx';
import { Drawer } from '../../components/ui/Drawer.tsx';
import { ErrorBanner } from '../../components/ui/ErrorBanner.tsx';
import { HeroChartSkeleton } from '../../components/ui/LoadingSkeleton.tsx';
import { useForecastSnapshot, useSafeWind, useTimeseries } from '../../api/queries.ts';
import { formatMW, formatSignedMW, formatUtcDateTime, formatUtcTime } from '../../lib/format.ts';
import type { AppUrlState, TimeseriesPoint } from '../../types.ts';

interface DecisionViewProps {
  state: AppUrlState;
}

export function DecisionView({ state }: DecisionViewProps) {
  const [selectedPeriod, setSelectedPeriod] = useState<
    (TimeseriesPoint & { safe_wind_mw?: number | null }) | null
  >(null);

  // Queries for delivery day
  const {
    data: tsData,
    isLoading: tsLoading,
    error: tsError,
    refetch: refetchTs,
  } = useTimeseries(state.deliveryDate, state.deliveryDate, state.decisionTime, state.resolution);

  const {
    data: snapshotData,
    isLoading: snapshotLoading,
    error: snapshotError,
  } = useForecastSnapshot(state.deliveryDate, state.decisionTime);

  const {
    data: safeWindData,
    isLoading: safeWindLoading,
    error: safeWindError,
    refetch: refetchSafeWind,
  } = useSafeWind(state.deliveryDate, state.decisionTime, state.quantile, state.safeWindMode);

  const isLoading = tsLoading || snapshotLoading || safeWindLoading;
  const anyError = tsError || snapshotError || safeWindError;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Error state */}
      {anyError && (
        <ErrorBanner
          error={anyError as Error}
          onRetry={() => {
            refetchTs();
            refetchSafeWind();
          }}
        />
      )}

      {/* Summary Strip (MWh volumes & procurement peak) */}
      <SummaryStrip
        snapshot={snapshotData}
        safeWind={safeWindData}
        safeWindMode={state.safeWindMode}
        quantile={state.quantile}
      />

      {/* Hero Chart */}
      {isLoading && !tsData ? (
        <HeroChartSkeleton />
      ) : (
        <HeroChart
          timeseriesPoints={tsData?.data || []}
          safeWind={safeWindData}
          showLeakyLine={state.showLeakyLine}
          safeWindMode={state.safeWindMode}
          quantile={state.quantile}
          deliveryDate={state.deliveryDate}
        />
      )}

      {/* Procurement Bars (Coral) */}
      <ProcurementBars
        periods={safeWindData?.periods}
        quantile={state.quantile}
        safeWindMode={state.safeWindMode === 'prior_days' ? 'Prior-Days' : 'In-Sample'}
      />

      {/* Settlement Period Ledger Table */}
      <DayDataTable
        timeseriesPoints={tsData?.data || []}
        safeWindPeriods={safeWindData?.periods}
        deliveryDate={state.deliveryDate}
        onSelectPeriod={(pt) => setSelectedPeriod(pt)}
      />

      {/* Slide-over Drawer for Period Details */}
      <Drawer
        isOpen={Boolean(selectedPeriod)}
        onClose={() => setSelectedPeriod(null)}
        title={selectedPeriod ? `Settlement Period ${selectedPeriod.settlement_period}` : ''}
        subtitle={selectedPeriod ? formatUtcDateTime(selectedPeriod.start_time) : ''}
      >
        {selectedPeriod && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div
              style={{
                backgroundColor: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-4)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <h4 style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                Period Quantities
              </h4>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Interval Window:</span>
                <span className="tabular-nums" style={{ fontWeight: 600 }}>
                  {formatUtcTime(selectedPeriod.start_time)} – {formatUtcTime(new Date(new Date(selectedPeriod.start_time).getTime() + 30 * 60000))}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-forecast)', fontWeight: 600 }}>Decision Forecast:</span>
                <span className="tabular-nums" style={{ fontWeight: 700 }}>
                  {formatMW(selectedPeriod.decision_forecast_mw)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-safe-wind)', fontWeight: 600 }}>
                  Safe Wind Commitment (P{Math.round(state.quantile * 100)}):
                </span>
                <span className="tabular-nums" style={{ fontWeight: 700 }}>
                  {formatMW(selectedPeriod.safe_wind_mw)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-actual)', fontWeight: 600 }}>Metered Actual:</span>
                <span className="tabular-nums" style={{ fontWeight: 700 }}>
                  {formatMW(selectedPeriod.actual_mw)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--color-border)', paddingTop: '6px' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Error (Forecast - Actual):</span>
                <span className="tabular-nums" style={{ fontWeight: 700 }}>
                  {formatSignedMW(selectedPeriod.error_mw)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-shortfall)', fontWeight: 600 }}>Deficit Shortfall:</span>
                <span className="tabular-nums" style={{ color: 'var(--color-shortfall)', fontWeight: 700 }}>
                  {formatMW(selectedPeriod.shortfall_mw)}
                </span>
              </div>
            </div>

            <div
              style={{
                backgroundColor: 'var(--color-surface-sunken)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-3) var(--space-4)',
                fontSize: 'var(--text-xs)',
                color: 'var(--color-text-secondary)',
                lineHeight: 1.5,
              }}
            >
              <strong>Trading Context:</strong>
              <p style={{ marginTop: '4px' }}>
                At the {state.decisionTime} UTC decision cutoff on D-1, this period was committed based on WINDFOR.
                Derating by the {state.safeWindMode === 'prior_days' ? 'prior-days' : 'in-sample'} buffer of{' '}
                {safeWindData?.shortfall_quantile_mw ? formatMW(safeWindData.shortfall_quantile_mw) : '—'} ensures that thermal replacement
                reserves can be secured before delivery.
              </p>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
