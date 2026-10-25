import { useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { SegmentedControl } from '../../components/ui/SegmentedControl.tsx';
import { useErrorByHorizon } from '../../api/queries.ts';
import { formatMW, formatSignedMW } from '../../lib/format.ts';
import type { HorizonBucket } from '../../types.ts';

interface ErrorByHorizonChartProps {
  decisionTime: string;
}

export function ErrorByHorizonChart({ decisionTime }: ErrorByHorizonChartProps) {
  const [source, setSource] = useState<'all' | 'decision'>('all');
  const { data } = useErrorByHorizon(source, decisionTime);

  const rawBuckets = data?.buckets || [];
  const buckets: HorizonBucket[] = rawBuckets.map((b: any) => ({
    min_horizon_hours: Number(b.min_horizon_hours),
    max_horizon_hours: Number(b.max_horizon_hours),
    sample_count: Number(b.sample_count),
    mae_mw: Number(b.mae_mw),
    rmse_mw: Number(b.rmse_mw),
    bias_mw: Number(b.bias_mw),
  }));

  const chartData = buckets.map((b) => ({
    ...b,
    label: `${b.min_horizon_hours}-${b.max_horizon_hours}h`,
    mid_horizon: (b.min_horizon_hours + b.max_horizon_hours) / 2,
  }));

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
            Forecast Accuracy Across Lead-Time Horizons
          </h3>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Error degradation as forecast lead time increases from gate closure (0h) to day-ahead auction (16.5–39.5h) and beyond
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <SegmentedControl<'all' | 'decision'>
            name="horizon-source"
            size="sm"
            options={[
              { value: 'all', label: 'All Pre-delivery Revisions', badge: '25.6k' },
              { value: 'decision', label: `D-1 ${decisionTime} Snapshot Only`, badge: '1.4k' },
            ]}
            value={source}
            onChange={(val) => setSource(val)}
          />
        </div>
      </div>

      <div style={{ width: '100%', height: '300px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.6} />

            <XAxis
              dataKey="label"
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
              tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
              unit=" MW"
            />

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
                    <div style={{ fontWeight: 700, marginBottom: '4px' }}>
                      Horizon Window: {label} ({d.sample_count} Revisions)
                    </div>
                    <div style={{ color: 'var(--color-forecast)', fontWeight: 600 }}>
                      Mean Bias: {formatSignedMW(d.bias_mw)}
                    </div>
                    <div style={{ color: 'var(--color-text-primary)' }}>MAE: {formatMW(d.mae_mw)}</div>
                    <div style={{ color: 'var(--color-shortfall)' }}>RMSE: {formatMW(d.rmse_mw)}</div>
                  </div>
                );
              }}
            />

            <Legend
              verticalAlign="top"
              height={36}
              iconType="plainline"
              wrapperStyle={{ fontSize: '12px' }}
            />

            {/* Auction Decision Window (16.5h – 39.5h) Reference Band */}
            {source === 'all' && (
              <ReferenceArea
                x1="12-18h"
                x2="36-42h"
                fill="var(--color-forecast-bg)"
                stroke="var(--color-forecast)"
                strokeOpacity={0.3}
                label={{
                  value: 'Day-Ahead Auction Window (16.5–39.5h)',
                  position: 'insideTop',
                  fill: 'var(--color-forecast)',
                  fontSize: 10,
                  fontWeight: 600,
                }}
              />
            )}

            <Line
              type="monotone"
              dataKey="bias_mw"
              name="Mean Bias (MW)"
              stroke="var(--color-forecast-stroke)"
              strokeWidth={2.5}
              dot={{ r: 3 }}
            />

            <Line
              type="monotone"
              dataKey="mae_mw"
              name="MAE (MW)"
              stroke="var(--color-actual-stroke)"
              strokeWidth={2}
              dot={{ r: 3 }}
            />

            <Line
              type="monotone"
              dataKey="rmse_mw"
              name="RMSE (MW)"
              stroke="var(--color-shortfall-stroke)"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={{ r: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
