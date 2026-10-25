import React, { useMemo, useState } from 'react';
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useErrorByHour } from '../../api/queries.ts';
import { formatMW, formatSignedMW } from '../../lib/format.ts';

interface ErrorByHourChartProps {
  decisionTime: string;
}

export const ErrorByHourChart = React.memo(function ErrorByHourChart({
  decisionTime,
}: ErrorByHourChartProps) {
  const [visibleSeries, setVisibleSeries] = useState({
    forecast: true,
    actual: true,
    bias: true,
    mae: false,
  });

  const toggleSeries = (key: keyof typeof visibleSeries) => {
    setVisibleSeries((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const { data } = useErrorByHour(decisionTime);
  const rawHours = data?.hours || [];

  const hours = useMemo(() => {
    return rawHours.map((h: any) => ({
      hour: Number(h.hour),
      mean_forecast_mw: Number(h.mean_forecast_mw),
      mean_actual_mw: Number(h.mean_actual_mw),
      bias_mw: Number(h.bias_mw),
      mae_mw: Number(h.mae_mw),
      rmse_mw: Number(h.rmse_mw),
      hour_label: `${String(h.hour).padStart(2, '0')}:00`,
    }));
  }, [rawHours]);

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
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <h3
            style={{
              fontSize: 'var(--text-base)',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
            }}
          >
            Diurnal Error Profile Across Hours of Day (00:00 – 23:00 UTC)
          </h3>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Hourly aggregated mean forecast, metered generation, and persistent over-forecast bias
          </p>
        </div>

        {/* Clickable Legend Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px', fontSize: 'var(--text-xs)' }}>
          <button
            type="button"
            onClick={() => toggleSeries('forecast')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              backgroundColor: visibleSeries.forecast ? 'var(--color-surface-elevated)' : 'transparent',
              opacity: visibleSeries.forecast ? 1 : 0.45,
              cursor: 'pointer',
            }}
          >
            <span style={{ width: '12px', height: '3px', backgroundColor: 'var(--color-forecast)' }} />
            <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Mean Forecast</span>
          </button>

          <button
            type="button"
            onClick={() => toggleSeries('actual')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              backgroundColor: visibleSeries.actual ? 'var(--color-surface-elevated)' : 'transparent',
              opacity: visibleSeries.actual ? 1 : 0.45,
              cursor: 'pointer',
            }}
          >
            <span style={{ width: '12px', height: '3px', backgroundColor: 'var(--color-actual)' }} />
            <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Mean Actual</span>
          </button>

          <button
            type="button"
            onClick={() => toggleSeries('bias')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              backgroundColor: visibleSeries.bias ? 'var(--color-surface-elevated)' : 'transparent',
              opacity: visibleSeries.bias ? 1 : 0.45,
              cursor: 'pointer',
            }}
          >
            <span style={{ width: '12px', height: '0px', borderTop: '2px dashed var(--color-shortfall-stroke)' }} />
            <span style={{ fontWeight: 600, color: 'var(--color-shortfall)' }}>Bias</span>
          </button>

          <button
            type="button"
            onClick={() => toggleSeries('mae')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              backgroundColor: visibleSeries.mae ? 'var(--color-surface-elevated)' : 'transparent',
              opacity: visibleSeries.mae ? 1 : 0.45,
              cursor: 'pointer',
            }}
          >
            <span style={{ width: '12px', height: '2px', backgroundColor: 'var(--color-text-secondary)' }} />
            <span style={{ fontWeight: 600, color: 'var(--color-text-secondary)' }}>MAE</span>
          </button>
        </div>
      </div>

      <div style={{ width: '100%', height: '320px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            syncId="accuracy-charts"
            data={hours}
            margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.6} />

            <XAxis dataKey="hour_label" stroke="var(--color-text-muted)" fontSize={11} tickLine={false} dy={8} />

            <YAxis
              stroke="var(--color-text-muted)"
              fontSize={11}
              tickLine={false}
              dx={-6}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              unit=" MW"
            />

            <ReferenceLine y={0} stroke="var(--color-text-secondary)" strokeWidth={1} />

            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div
                    style={{
                      backgroundColor: 'var(--color-surface-elevated)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-md)',
                      padding: '8px 12px',
                      boxShadow: 'var(--shadow-md)',
                      fontSize: 'var(--text-xs)',
                    }}
                  >
                    <div style={{ fontWeight: 700, marginBottom: '4px' }}>Clock Hour: {label} UTC</div>
                    <div style={{ color: 'var(--color-forecast)', fontWeight: 600 }}>
                      Mean Forecast: {formatMW(d.mean_forecast_mw)}
                    </div>
                    <div style={{ color: 'var(--color-actual)', fontWeight: 600 }}>
                      Mean Actual: {formatMW(d.mean_actual_mw)}
                    </div>
                    <div style={{ color: 'var(--color-text-primary)', marginTop: '4px' }}>
                      Mean Bias: {formatSignedMW(d.bias_mw)}
                    </div>
                    <div style={{ color: 'var(--color-text-muted)', fontSize: '11px', marginTop: '2px' }}>
                      MAE: {formatMW(d.mae_mw)} | RMSE: {formatMW(d.rmse_mw)}
                    </div>
                  </div>
                );
              }}
            />

            {visibleSeries.forecast && (
              <Line
                type="monotone"
                dataKey="mean_forecast_mw"
                name="Mean Forecast (MW)"
                stroke="var(--color-forecast)"
                strokeWidth={2}
                dot={{ r: 2 }}
              />
            )}

            {visibleSeries.actual && (
              <Line
                type="monotone"
                dataKey="mean_actual_mw"
                name="Mean Actual (MW)"
                stroke="var(--color-actual)"
                strokeWidth={2}
                dot={{ r: 2 }}
              />
            )}

            {visibleSeries.bias && (
              <Line
                type="monotone"
                dataKey="bias_mw"
                name="Mean Bias (MW)"
                stroke="var(--color-shortfall-stroke)"
                strokeWidth={1.5}
                strokeDasharray="3 3"
                dot={{ r: 2 }}
              />
            )}

            {visibleSeries.mae && (
              <Line
                type="monotone"
                dataKey="mae_mw"
                name="MAE (MW)"
                stroke="var(--color-text-secondary)"
                strokeWidth={1.5}
                dot={{ r: 2 }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
