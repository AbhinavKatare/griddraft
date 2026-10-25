import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatMW, formatUtcTime } from '../../lib/format.ts';
import type { SafeWindPeriod } from '../../types.ts';

interface ProcurementBarsProps {
  periods?: SafeWindPeriod[];
  quantile: number;
  safeWindMode: string;
}

export function ProcurementBars({ periods = [], quantile, safeWindMode }: ProcurementBarsProps) {
  const chartData = periods.map((p) => ({
    ...p,
    time_label: formatUtcTime(p.start_time),
    procurement_mw: p.thermal_procurement_mw,
  }));

  const maxProcurement = Math.max(...chartData.map((d) => d.procurement_mw || 0), 0);

  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-5)',
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
              fontSize: 'var(--text-sm)',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
            }}
          >
            Required Thermal & Storage Reserve Procurement (MW)
          </h3>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Extra capacity needed to protect against P{Math.round(quantile * 100)} wind shortfalls ({safeWindMode})
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="tabular-nums" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
            Peak Procurement: <strong style={{ color: 'var(--color-shortfall)' }}>{formatMW(maxProcurement)}</strong>
          </span>
        </div>
      </div>

      <div style={{ width: '100%', height: '180px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.6} />
            <XAxis dataKey="time_label" stroke="var(--color-text-muted)" fontSize={10} tickLine={false} />
            <YAxis
              stroke="var(--color-text-muted)"
              fontSize={10}
              tickLine={false}
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
                      {label} (SP {d.settlement_period})
                    </div>
                    <div style={{ color: 'var(--color-shortfall)', fontWeight: 600 }}>
                      Procurement: {formatMW(d.procurement_mw)}
                    </div>
                    <div style={{ color: 'var(--color-text-muted)', fontSize: '11px', marginTop: '2px' }}>
                      Forecast: {formatMW(d.forecast_mw)} | Safe: {formatMW(d.safe_wind_mw)}
                    </div>
                  </div>
                );
              }}
            />
            <Bar
              dataKey="procurement_mw"
              fill="var(--color-shortfall-stroke)"
              radius={[3, 3, 0, 0]}
              name="Thermal Procurement"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
