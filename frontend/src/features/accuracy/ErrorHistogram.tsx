import { useMemo } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useTimeseries } from '../../api/queries.ts';

interface ErrorHistogramProps {
  decisionTime: string;
}

export function ErrorHistogram({ decisionTime }: ErrorHistogramProps) {
  const { data } = useTimeseries('2026-01-01', '2026-01-31', decisionTime, '30m');

  const histData = useMemo(() => {
    const points = data?.data || [];
    const validErrors = points
      .map((p) => p.error_mw)
      .filter((e): e is number => e !== null && !Number.isNaN(e));

    if (!validErrors.length) return [];

    const binSize = 500;
    const minVal = -3000;
    const maxVal = 7000;
    const bins: { range: string; binMid: number; count: number; pct: number }[] = [];

    for (let start = minVal; start < maxVal; start += binSize) {
      const end = start + binSize;
      const count = validErrors.filter((v) => v >= start && v < end).length;
      bins.push({
        range: `${start < 0 ? start : `+${start}`} to ${end < 0 ? end : `+${end}`}`,
        binMid: start + binSize / 2,
        count,
        pct: (count / validErrors.length) * 100,
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
        </p>
      </div>

      <div style={{ width: '100%', height: '260px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={histData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.6} />
            <XAxis dataKey="binMid" stroke="var(--color-text-muted)" fontSize={11} tickLine={false} tickFormatter={(v) => `${v > 0 ? '+' : ''}${v}`} dy={8} />
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
                    <div style={{ fontWeight: 700 }}>Error Range: {d.range} MW</div>
                    <div style={{ color: 'var(--color-forecast)', fontWeight: 600 }}>
                      Count: {d.count} Half-Hours ({d.pct.toFixed(1)}%)
                    </div>
                  </div>
                );
              }}
            />
            <Bar dataKey="count" radius={[2, 2, 0, 0]}>
              {histData.map((entry, index) => (
                <Cell
                  key={`hist-cell-${index}`}
                  fill={entry.binMid >= 0 ? 'var(--color-forecast-stroke)' : 'var(--color-actual-stroke)'}
                  opacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
