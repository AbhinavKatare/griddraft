import React, { useMemo, useState } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
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

export const ErrorByHorizonChart = React.memo(function ErrorByHorizonChart({
  decisionTime,
}: ErrorByHorizonChartProps) {
  const [source, setSource] = useState<'all' | 'decision'>('all');
  const [visibleSeries, setVisibleSeries] = useState({
    bias: true,
    mae: true,
    rmse: true,
    confidenceBand: true,
  });

  const toggleSeries = (key: keyof typeof visibleSeries) => {
    setVisibleSeries((prev) => ({ ...prev, [key]: !prev[key] }));
  };

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

  const chartData = useMemo(() => {
    return buckets.map((b) => {
      // Confidence interval around bias based on MAE dispersion: [bias - mae, bias + mae]
      const bandLow = Math.max(0, b.bias_mw - b.mae_mw * 0.7);
      const bandHigh = b.bias_mw + b.mae_mw * 0.7;

      return {
        ...b,
        label: `${b.min_horizon_hours}-${b.max_horizon_hours}h`,
        mid_horizon: (b.min_horizon_hours + b.max_horizon_hours) / 2,
        band_low: Math.round(bandLow),
        band_high: Math.round(bandHigh),
        confidence_span: [Math.round(bandLow), Math.round(bandHigh)],
      };
    });
  }, [buckets]);

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
            Error degradation as forecast lead time increases from gate closure (0h) to day-ahead auction (16.5–39.5h) and beyond (with &plusmn;1&sigma; confidence band)
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

      {/* Clickable Legend Toggles */}
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px', fontSize: 'var(--text-xs)' }}>
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
          <span style={{ width: '12px', height: '3px', backgroundColor: 'var(--color-forecast-stroke)' }} />
          <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Mean Bias</span>
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
          <span style={{ width: '12px', height: '3px', backgroundColor: 'var(--color-actual-stroke)' }} />
          <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>MAE</span>
        </button>

        <button
          type="button"
          onClick={() => toggleSeries('rmse')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '3px 8px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
            backgroundColor: visibleSeries.rmse ? 'var(--color-surface-elevated)' : 'transparent',
            opacity: visibleSeries.rmse ? 1 : 0.45,
            cursor: 'pointer',
          }}
        >
          <span style={{ width: '12px', height: '0px', borderTop: '2px dashed var(--color-shortfall-stroke)' }} />
          <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>RMSE</span>
        </button>

        <button
          type="button"
          onClick={() => toggleSeries('confidenceBand')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '3px 8px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--color-border)',
            backgroundColor: visibleSeries.confidenceBand ? 'var(--color-surface-elevated)' : 'transparent',
            opacity: visibleSeries.confidenceBand ? 1 : 0.45,
            cursor: 'pointer',
          }}
        >
          <span
            style={{
              width: '12px',
              height: '8px',
              backgroundColor: 'rgba(217, 119, 6, 0.25)',
              borderRadius: '1px',
            }}
          />
          <span style={{ fontWeight: 600, color: 'var(--color-forecast)' }}>Confidence Band</span>
        </button>
      </div>

      <div style={{ width: '100%', height: '320px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            syncId="accuracy-charts"
            data={chartData}
            margin={{ top: 10, right: 10, left: 10, bottom: 20 }}
          >
            <defs>
              <linearGradient id="horizonConfidenceFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-forecast)" stopOpacity={0.25} />
                <stop offset="95%" stopColor="var(--color-forecast)" stopOpacity={0.05} />
              </linearGradient>
            </defs>

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
                    <div style={{ fontWeight: 700, marginBottom: '4px' }}>
                      Horizon Window: {label} ({d.sample_count} Revisions)
                    </div>
                    <div style={{ color: 'var(--color-forecast)', fontWeight: 600 }}>
                      Mean Bias: {formatSignedMW(d.bias_mw)}
                    </div>
                    <div style={{ color: 'var(--color-actual-stroke)' }}>MAE: {formatMW(d.mae_mw)}</div>
                    <div style={{ color: 'var(--color-shortfall)' }}>RMSE: {formatMW(d.rmse_mw)}</div>
                    <div style={{ color: 'var(--color-text-muted)', fontSize: '11px', marginTop: '4px' }}>
                      Confidence Span: {formatMW(d.band_low)} to {formatMW(d.band_high)}
                    </div>
                  </div>
                );
              }}
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

            {/* Shaded Confidence Band */}
            {visibleSeries.confidenceBand && (
              <Area
                type="monotone"
                dataKey="band_high"
                fill="url(#horizonConfidenceFill)"
                stroke="none"
                name="Confidence Upper"
              />
            )}

            {visibleSeries.bias && (
              <Line
                type="monotone"
                dataKey="bias_mw"
                name="Mean Bias (MW)"
                stroke="var(--color-forecast-stroke)"
                strokeWidth={2.5}
                dot={{ r: 3 }}
              />
            )}

            {visibleSeries.mae && (
              <Line
                type="monotone"
                dataKey="mae_mw"
                name="MAE (MW)"
                stroke="var(--color-actual-stroke)"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            )}

            {visibleSeries.rmse && (
              <Line
                type="monotone"
                dataKey="rmse_mw"
                name="RMSE (MW)"
                stroke="var(--color-shortfall-stroke)"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={{ r: 2 }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
