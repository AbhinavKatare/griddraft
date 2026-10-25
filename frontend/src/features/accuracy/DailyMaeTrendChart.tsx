import React, { useMemo, useState } from 'react';
import {
  Brush,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatMW, formatSignedMW } from '../../lib/format.ts';
import type { DailyKPI } from '../../types.ts';

export interface DailyComparisonPoint extends DailyKPI {
  latest_mae_mw?: number;
  latest_bias_mw?: number;
  leakage_mae_mw?: number;
  day_num: number;
  is_selected: boolean;
}

interface DailyMaeTrendChartProps {
  dailyKpis: DailyComparisonPoint[];
  selectedDate?: string;
  onSelectDate: (date: string) => void;
  showComparison?: boolean;
}

export const DailyMaeTrendChart = React.memo(function DailyMaeTrendChart({
  dailyKpis,
  selectedDate,
  onSelectDate,
  showComparison = false,
}: DailyMaeTrendChartProps) {
  const [visibleSeries, setVisibleSeries] = useState({
    decisionMae: true,
    latestMae: true,
    decisionBias: true,
  });

  const toggleSeries = (key: keyof typeof visibleSeries) => {
    setVisibleSeries((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const chartData = useMemo(() => {
    return dailyKpis.map((d) => ({
      ...d,
      day_num: parseInt(d.date.slice(8), 10),
      is_selected: d.date === selectedDate,
    }));
  }, [dailyKpis, selectedDate]);

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
            Daily Forecast Accuracy & Information Leakage Trend (January 2026)
          </h3>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Daily MAE evolution across the month. {showComparison ? 'Comparing D-1 decision MAE against latest pre-delivery MAE to reveal information leakage.' : 'Click any date to inspect in Decision View.'}
          </p>
        </div>

        {/* Clickable Legend Series Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px', fontSize: 'var(--text-xs)' }}>
          <button
            type="button"
            onClick={() => toggleSeries('decisionMae')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              backgroundColor: visibleSeries.decisionMae ? 'var(--color-surface-elevated)' : 'transparent',
              opacity: visibleSeries.decisionMae ? 1 : 0.45,
              cursor: 'pointer',
            }}
          >
            <span style={{ width: '12px', height: '3px', backgroundColor: 'var(--color-forecast)' }} />
            <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>D-1 Decision MAE</span>
          </button>

          {showComparison && (
            <button
              type="button"
              onClick={() => toggleSeries('latestMae')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 8px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                backgroundColor: visibleSeries.latestMae ? 'var(--color-surface-elevated)' : 'transparent',
                opacity: visibleSeries.latestMae ? 1 : 0.45,
                cursor: 'pointer',
              }}
            >
              <span style={{ width: '12px', height: '0px', borderTop: '2px dashed var(--color-latest)' }} />
              <span style={{ fontWeight: 600, color: 'var(--color-latest)' }}>Latest Pre-Delivery MAE</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => toggleSeries('decisionBias')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
              backgroundColor: visibleSeries.decisionBias ? 'var(--color-surface-elevated)' : 'transparent',
              opacity: visibleSeries.decisionBias ? 1 : 0.45,
              cursor: 'pointer',
            }}
          >
            <span style={{ width: '12px', height: '2px', backgroundColor: 'var(--color-actual)' }} />
            <span style={{ fontWeight: 600, color: 'var(--color-actual)' }}>Daily Bias</span>
          </button>
        </div>
      </div>

      <div style={{ width: '100%', height: '320px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            syncId="accuracy-charts"
            data={chartData}
            margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
            onClick={(state: any) => {
              if (state && state.activePayload && state.activePayload[0]) {
                const clickedDate = state.activePayload[0].payload.date;
                onSelectDate(clickedDate);
              }
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.6} />

            <XAxis
              dataKey="day_num"
              stroke="var(--color-text-muted)"
              fontSize={11}
              tickLine={false}
              tickFormatter={(d) => `Jan ${d}`}
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

            <ReferenceLine y={0} stroke="var(--color-text-secondary)" strokeWidth={1} />

            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div
                    style={{
                      backgroundColor: 'var(--color-surface-elevated)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-md)',
                      padding: '10px 14px',
                      boxShadow: 'var(--shadow-md)',
                      fontSize: 'var(--text-xs)',
                    }}
                  >
                    <div style={{ fontWeight: 700, marginBottom: '6px' }}>
                      {d.date} {d.is_selected ? '(Selected)' : '(Click to inspect)'}
                    </div>
                    <div style={{ color: 'var(--color-forecast)', fontWeight: 600 }}>
                      D-1 Decision MAE: {formatMW(d.mae_mw)}
                    </div>
                    {showComparison && d.latest_mae_mw !== undefined && (
                      <div style={{ color: 'var(--color-latest)', fontWeight: 600, marginTop: '2px' }}>
                        Latest MAE: {formatMW(d.latest_mae_mw)} (Leakage: -{formatMW((d.mae_mw - d.latest_mae_mw))})
                      </div>
                    )}
                    <div style={{ color: 'var(--color-actual)', fontWeight: 600, marginTop: '2px' }}>
                      Daily Mean Bias: {formatSignedMW(d.bias_mw)}
                    </div>
                    <div style={{ color: 'var(--color-text-muted)', fontSize: '11px', marginTop: '4px' }}>
                      Actual: {formatMW(d.mean_actual_mw)} | Forecast: {formatMW(d.mean_forecast_mw)}
                    </div>
                  </div>
                );
              }}
            />

            {/* Decision-Time MAE Line */}
            {visibleSeries.decisionMae && (
              <Line
                type="monotone"
                dataKey="mae_mw"
                name="Decision MAE (MW)"
                stroke="var(--color-forecast)"
                strokeWidth={2.5}
                dot={{ r: 3 }}
                activeDot={{ r: 6 }}
              />
            )}

            {/* Latest Pre-Delivery MAE Line (Comparison Mode) */}
            {showComparison && visibleSeries.latestMae && (
              <Line
                type="monotone"
                dataKey="latest_mae_mw"
                name="Latest Pre-Delivery MAE (MW)"
                stroke="var(--color-latest)"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={{ r: 3 }}
                activeDot={{ r: 6 }}
              />
            )}

            {/* Daily Bias Line */}
            {visibleSeries.decisionBias && (
              <Line
                type="monotone"
                dataKey="bias_mw"
                name="Daily Bias (MW)"
                stroke="var(--color-actual)"
                strokeWidth={1.5}
                strokeDasharray="3 3"
                dot={{ r: 2 }}
              />
            )}

            {/* Interactive Brush/Zoom Slider */}
            <Brush
              dataKey="day_num"
              height={24}
              stroke="var(--color-border)"
              fill="var(--color-surface-sunken)"
              tickFormatter={(d) => `Jan ${d}`}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
