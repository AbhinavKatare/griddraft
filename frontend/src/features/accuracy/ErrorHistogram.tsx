import React, { useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTimeseries } from '../../api/queries.ts';

interface ErrorHistogramProps {
  decisionTime: string;
  showComparison?: boolean;
}

export const ErrorHistogram = React.memo(function ErrorHistogram({
  decisionTime,
  showComparison = false,
}: ErrorHistogramProps) {
  const [activeSeries, setActiveSeries] = useState<'both' | 'decision' | 'latest'>('both');
  const { data } = useTimeseries('2026-01-01', '2026-01-31', decisionTime, '30m');

  const histData = useMemo(() => {
    const points = data?.data || [];
    const decisionErrors = points
      .map((p) => p.error_mw)
      .filter((e): e is number => e !== null && !Number.isNaN(e));

    const latestErrors = points
      .map((p) => {
        if (
          p.latest_forecast_mw !== null &&
          p.latest_forecast_mw !== undefined &&
          p.actual_mw !== null &&
          p.actual_mw !== undefined
        ) {
          return p.latest_forecast_mw - p.actual_mw;
        }
        return null;
      })
      .filter((e): e is number => e !== null && !Number.isNaN(e));

    if (!decisionErrors.length) return [];

    const binSize = 500;
    const minVal = -3000;
    const maxVal = 7000;
    const bins: {
      range: string;
      binMid: number;
      decisionCount: number;
      latestCount: number;
      decisionPct: number;
      latestPct: number;
    }[] = [];

    for (let start = minVal; start < maxVal; start += binSize) {
      const end = start + binSize;
      const decCount = decisionErrors.filter((v) => v >= start && v < end).length;
      const latCount = latestErrors.filter((v) => v >= start && v < end).length;

      bins.push({
        range: `${start < 0 ? start : `+${start}`} to ${end < 0 ? end : `+${end}`}`,
        binMid: start + binSize / 2,
        decisionCount: decCount,
        latestCount: latCount,
        decisionPct: (decCount / decisionErrors.length) * 100,
        latestPct: latestErrors.length ? (latCount / latestErrors.length) * 100 : 0,
      });
    }

    return bins;
  }, [data]);

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
            Forecast Error Distribution (500 MW Bins)
          </h3>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Distribution of signed errors (Forecast - Actual). Note the pronounced right skew towards positive over-forecasting.
            {showComparison && ' Comparing D-1 Decision distribution against Latest Pre-Delivery distribution.'}
          </p>
        </div>

        {showComparison && (
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              type="button"
              onClick={() => setActiveSeries(activeSeries === 'decision' ? 'both' : 'decision')}
              style={{
                fontSize: 'var(--text-xs)',
                padding: '3px 8px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                backgroundColor: activeSeries === 'decision' || activeSeries === 'both' ? 'var(--color-surface-elevated)' : 'transparent',
                cursor: 'pointer',
              }}
            >
              <span style={{ color: 'var(--color-forecast)', fontWeight: 600 }}>D-1 Decision</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveSeries(activeSeries === 'latest' ? 'both' : 'latest')}
              style={{
                fontSize: 'var(--text-xs)',
                padding: '3px 8px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
                backgroundColor: activeSeries === 'latest' || activeSeries === 'both' ? 'var(--color-surface-elevated)' : 'transparent',
                cursor: 'pointer',
              }}
            >
              <span style={{ color: 'var(--color-latest)', fontWeight: 600 }}>Latest Pre-Delivery</span>
            </button>
          </div>
        )}
      </div>

      <div style={{ width: '100%', height: '280px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={histData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.6} />

            <XAxis
              dataKey="binMid"
              stroke="var(--color-text-muted)"
              fontSize={11}
              tickLine={false}
              tickFormatter={(v) => `${v > 0 ? '+' : ''}${v}`}
              dy={8}
            />

            <YAxis stroke="var(--color-text-muted)" fontSize={11} tickLine={false} dx={-6} unit=" HH" />

            <ReferenceLine x={0} stroke="var(--color-text-secondary)" strokeWidth={1.5} />

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
                      padding: '8px 12px',
                      boxShadow: 'var(--shadow-md)',
                      fontSize: 'var(--text-xs)',
                    }}
                  >
                    <div style={{ fontWeight: 700, marginBottom: '4px' }}>Error Range: {d.range} MW</div>
                    <div style={{ color: 'var(--color-forecast)', fontWeight: 600 }}>
                      D-1 Decision: {d.decisionCount} Half-Hours ({d.decisionPct.toFixed(1)}%)
                    </div>
                    {showComparison && (
                      <div style={{ color: 'var(--color-latest)', fontWeight: 600, marginTop: '2px' }}>
                        Latest Pre-Delivery: {d.latestCount} Half-Hours ({d.latestPct.toFixed(1)}%)
                      </div>
                    )}
                  </div>
                );
              }}
            />

            {(activeSeries === 'both' || activeSeries === 'decision') && (
              <Bar dataKey="decisionCount" name="Decision Forecast Errors" radius={[2, 2, 0, 0]}>
                {histData.map((entry, index) => (
                  <Cell
                    key={`hist-dec-${index}`}
                    fill={entry.binMid >= 0 ? 'var(--color-forecast-stroke)' : 'var(--color-actual-stroke)'}
                    opacity={0.85}
                  />
                ))}
              </Bar>
            )}

            {showComparison && (activeSeries === 'both' || activeSeries === 'latest') && (
              <Bar dataKey="latestCount" name="Latest Forecast Errors" fill="var(--color-latest)" opacity={0.6} radius={[2, 2, 0, 0]} />
            )}

            {showComparison && <Legend verticalAlign="top" height={30} wrapperStyle={{ fontSize: '11px' }} />}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
