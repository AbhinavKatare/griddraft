import { useMemo } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatMW, formatUtcTime } from '../../lib/format.ts';
import type { SafeWindSummary, TimeseriesPoint } from '../../types.ts';

interface HeroChartProps {
  timeseriesPoints: TimeseriesPoint[];
  safeWind?: SafeWindSummary;
  showLeakyLine: boolean;
  safeWindMode: 'in_sample' | 'prior_days';
  quantile: number;
  deliveryDate: string;
}

export function HeroChart({
  timeseriesPoints,
  safeWind,
  showLeakyLine,
  safeWindMode,
  quantile,
  deliveryDate,
}: HeroChartProps) {
  // Join safe-wind values to timeseries points for charting
  const chartData = useMemo(() => {
    const safeMap = new Map<string, number>();
    safeWind?.periods?.forEach((p) => {
      safeMap.set(p.start_time, p.safe_wind_mw);
    });

    return timeseriesPoints.map((pt) => {
      const safeMw = safeMap.get(pt.start_time);
      return {
        ...pt,
        safe_wind_mw: safeMw !== undefined ? safeMw : null,
        time_label: formatUtcTime(pt.start_time),
      };
    });
  }, [timeseriesPoints, safeWind]);

  // Disable animation if total data points exceeds 1,500
  const isLargeDataset = chartData.length > 1500;
  const animationDuration = isLargeDataset ? 0 : 500;

  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-6)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-4)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Chart Header & Interactive Legend */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-4)',
        }}
      >
        <div>
          <h2
            style={{
              fontSize: 'var(--text-base)',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              letterSpacing: '-0.01em',
            }}
          >
            Delivery Day Generation & Risk Envelope
          </h2>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
            Comparing D-1 decision forecast against metered actuals and derated commitment band ({deliveryDate})
          </p>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '14px', fontSize: 'var(--text-xs)' }}>
          {/* Actuals */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                width: '12px',
                height: '3px',
                backgroundColor: 'var(--color-actual)',
                borderRadius: '1px',
              }}
            />
            <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Actual Metered (FUELHH)</span>
          </div>

          {/* Decision Forecast */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                width: '12px',
                height: '3px',
                backgroundColor: 'var(--color-forecast)',
                borderRadius: '1px',
              }}
            />
            <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Decision Forecast (D-1)</span>
          </div>

          {/* Safe Wind Band */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                width: '12px',
                height: '10px',
                backgroundColor: 'var(--color-safe-wind-bg)',
                border: '1px solid var(--color-safe-wind-stroke)',
                borderRadius: '2px',
              }}
            />
            <span style={{ fontWeight: 600, color: 'var(--color-safe-wind)' }}>
              Safe Wind (P{Math.round(quantile * 100)} {safeWindMode === 'prior_days' ? 'prior-days' : 'in-sample'})
            </span>
          </div>

          {/* Leaky line toggle legend */}
          {showLeakyLine && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span
                style={{
                  width: '12px',
                  height: '0px',
                  borderTop: '2px dashed var(--color-latest)',
                }}
              />
              <span style={{ color: 'var(--color-latest)', fontWeight: 500 }}>Latest Revision (Leaky)</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Chart Canvas */}
      <div style={{ width: '100%', height: '380px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
            <defs>
              <linearGradient id="safeWindFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-safe-wind-stroke)" stopOpacity={0.25} />
                <stop offset="95%" stopColor="var(--color-safe-wind-stroke)" stopOpacity={0.03} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.6} />

            <XAxis
              dataKey="time_label"
              stroke="var(--color-text-muted)"
              fontSize={11}
              tickLine={false}
              dy={8}
            />

            <YAxis
              stroke="var(--color-text-muted)"
              fontSize={11}
              tickLine={false}
              dx={-6}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              unit=" MW"
            />

            <Tooltip
              content={<CustomTooltip safeWindMode={safeWindMode} quantile={quantile} />}
              cursor={{ stroke: 'var(--color-border-hover)', strokeWidth: 1, strokeDasharray: '4 4' }}
            />

            {/* Shaded Safe-Wind Derated Band */}
            <Area
              type="monotone"
              dataKey="safe_wind_mw"
              fill="url(#safeWindFill)"
              stroke="var(--color-safe-wind-stroke)"
              strokeWidth={1.5}
              isAnimationActive={!isLargeDataset}
              animationDuration={animationDuration}
              name={`Safe Wind P${Math.round(quantile * 100)}`}
            />

            {/* Decision-Time Forecast Line */}
            <Line
              type="monotone"
              dataKey="decision_forecast_mw"
              stroke="var(--color-forecast)"
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={!isLargeDataset}
              animationDuration={animationDuration}
              name="Decision Forecast"
            />

            {/* Actual Outturn Line */}
            <Line
              type="monotone"
              dataKey="actual_mw"
              stroke="var(--color-actual)"
              strokeWidth={2}
              dot={false}
              isAnimationActive={!isLargeDataset}
              animationDuration={animationDuration}
              name="Actual Generation"
            />

            {/* Ghost Leaky Line (Optional Toggle) */}
            {showLeakyLine && (
              <Line
                type="monotone"
                dataKey="latest_forecast_mw"
                stroke="var(--color-latest)"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                isAnimationActive={!isLargeDataset}
                animationDuration={animationDuration}
                name="Latest (Leaky)"
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/**
 * Custom Tooltip with tabular data and crosshair breakdown
 */
function CustomTooltip({
  active,
  payload,
  label,
  safeWindMode,
  quantile,
}: any) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface-elevated)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        padding: '10px 14px',
        boxShadow: 'var(--shadow-lg)',
        fontSize: 'var(--text-xs)',
        minWidth: '220px',
      }}
    >
      <div
        style={{
          borderBottom: '1px solid var(--color-border)',
          paddingBottom: '4px',
          marginBottom: '8px',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <span style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>{label}</span>
        <span className="tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
          SP {data.settlement_period}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
        {data.actual_mw !== null && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--color-actual)', fontWeight: 600 }}>Actual:</span>
            <span className="tabular-nums" style={{ fontWeight: 700 }}>
              {formatMW(data.actual_mw)}
            </span>
          </div>
        )}

        {data.decision_forecast_mw !== null && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--color-forecast)', fontWeight: 600 }}>Decision Forecast:</span>
            <span className="tabular-nums" style={{ fontWeight: 700 }}>
              {formatMW(data.decision_forecast_mw)}
            </span>
          </div>
        )}

        {data.safe_wind_mw !== null && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--color-safe-wind)', fontWeight: 600 }}>
              Safe Wind (P{Math.round(quantile * 100)} {safeWindMode}):
            </span>
            <span className="tabular-nums" style={{ fontWeight: 700 }}>
              {formatMW(data.safe_wind_mw)}
            </span>
          </div>
        )}

        {data.latest_forecast_mw !== null && (
          <div style={{ display: 'flex', justifyContent: 'space-between', opacity: 0.85 }}>
            <span style={{ color: 'var(--color-latest)' }}>Latest Revision:</span>
            <span className="tabular-nums">{formatMW(data.latest_forecast_mw)}</span>
          </div>
        )}

        {data.shortfall_mw !== null && data.shortfall_mw > 0 && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              borderTop: '1px solid var(--color-border)',
              paddingTop: '4px',
              marginTop: '4px',
            }}
          >
            <span style={{ color: 'var(--color-shortfall)', fontWeight: 600 }}>Deficit Shortfall:</span>
            <span className="tabular-nums" style={{ color: 'var(--color-shortfall)', fontWeight: 700 }}>
              {formatMW(data.shortfall_mw)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
