import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatMW, formatSignedMW } from '../../lib/format.ts';
import type { DailyKPI } from '../../types.ts';

interface DailyBiasStripProps {
  dailyKpis?: DailyKPI[];
  selectedDate?: string;
  onSelectDate: (date: string) => void;
}

export function DailyBiasStrip({ dailyKpis = [], selectedDate, onSelectDate }: DailyBiasStripProps) {
  const chartData = dailyKpis.map((d) => ({
    ...d,
    day_num: parseInt(d.date.slice(8), 10),
    is_selected: d.date === selectedDate,
  }));

  const positiveDays = dailyKpis.filter((d) => d.bias_mw > 0).length;
  const negativeDays = dailyKpis.filter((d) => d.bias_mw <= 0).length;

  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-6)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3)',
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
            Daily Mean Forecast Bias Strip (January 1–31, 2026)
          </h3>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Signed daily bias (Forecast - Actual). Click any bar to inspect that delivery day in Decision View.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: 'var(--text-xs)' }}>
          <span style={{ color: 'var(--color-forecast)', fontWeight: 600 }}>
            {positiveDays} Over-forecast Days
          </span>
          <span style={{ color: 'var(--color-actual)', fontWeight: 600 }}>
            {negativeDays} Under-forecast Days
          </span>
        </div>
      </div>

      <div style={{ width: '100%', height: '220px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
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
            />
            <YAxis
              stroke="var(--color-text-muted)"
              fontSize={11}
              tickLine={false}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              unit=" MW"
            />
            <ReferenceLine y={0} stroke="var(--color-text-secondary)" strokeWidth={1} />
            <Tooltip
              cursor={{ fill: 'var(--color-surface-hover)' }}
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
                    <div style={{ fontWeight: 700, marginBottom: '4px' }}>
                      {d.date} (Click to inspect)
                    </div>
                    <div style={{ color: d.bias_mw > 0 ? 'var(--color-forecast)' : 'var(--color-actual)', fontWeight: 600 }}>
                      Mean Bias: {formatSignedMW(d.bias_mw)}
                    </div>
                    <div style={{ color: 'var(--color-text-muted)', fontSize: '11px', marginTop: '2px' }}>
                      MAE: {formatMW(d.mae_mw)} | Forecast: {formatMW(d.mean_forecast_mw)} | Actual: {formatMW(d.mean_actual_mw)}
                    </div>
                  </div>
                );
              }}
            />
            <Bar dataKey="bias_mw" radius={[2, 2, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.bias_mw > 0 ? 'var(--color-forecast-stroke)' : 'var(--color-actual-stroke)'}
                  opacity={entry.is_selected ? 1 : 0.85}
                  stroke={entry.is_selected ? 'var(--color-text-primary)' : 'none'}
                  strokeWidth={entry.is_selected ? 2 : 0}
                  cursor="pointer"
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
