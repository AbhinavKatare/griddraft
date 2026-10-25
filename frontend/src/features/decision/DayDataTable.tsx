import { useMemo, useState } from 'react';
import { Download, Eye } from 'lucide-react';
import { VirtualTable } from '../../components/ui/VirtualTable.tsx';
import { formatMW, formatSignedMW, formatUtcTime } from '../../lib/format.ts';
import type { SafeWindPeriod, TimeseriesPoint } from '../../types.ts';

interface DayDataTableProps {
  timeseriesPoints: TimeseriesPoint[];
  safeWindPeriods?: SafeWindPeriod[];
  deliveryDate: string;
  onSelectPeriod?: (period: TimeseriesPoint & { safe_wind_mw?: number | null }) => void;
}

type SortColumn = 'settlement_period' | 'decision_forecast_mw' | 'actual_mw' | 'safe_wind_mw' | 'error_mw' | 'shortfall_mw';

export function DayDataTable({
  timeseriesPoints,
  safeWindPeriods = [],
  deliveryDate,
  onSelectPeriod,
}: DayDataTableProps) {
  const [sortCol, setSortCol] = useState<SortColumn>('settlement_period');
  const [sortAsc, setSortAsc] = useState<boolean>(true);

  // Combine timeseries and safe wind
  const mergedRows = useMemo(() => {
    const safeMap = new Map<string, number>();
    safeWindPeriods.forEach((p) => safeMap.set(p.start_time, p.safe_wind_mw));

    return timeseriesPoints.map((pt) => ({
      ...pt,
      safe_wind_mw: safeMap.get(pt.start_time) ?? null,
    }));
  }, [timeseriesPoints, safeWindPeriods]);

  // Sort rows
  const sortedRows = useMemo(() => {
    return [...mergedRows].sort((a, b) => {
      const valA = (a as any)[sortCol] ?? -Infinity;
      const valB = (b as any)[sortCol] ?? -Infinity;
      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [mergedRows, sortCol, sortAsc]);

  const handleSort = (col: SortColumn) => {
    if (sortCol === col) {
      setSortAsc((prev) => !prev);
    } else {
      setSortCol(col);
      setSortAsc(true);
    }
  };

  // Export CSV
  const handleExportCsv = () => {
    const headers = [
      'Settlement Date',
      'Settlement Period',
      'Start Time (UTC)',
      'Decision Forecast (MW)',
      'Safe Wind Commitment (MW)',
      'Actual Metered (MW)',
      'Error (Forecast - Actual, MW)',
      'Deficit Shortfall (MW)',
    ];

    const rows = sortedRows.map((r) => [
      r.settlement_date,
      r.settlement_period,
      r.start_time,
      r.decision_forecast_mw ?? '',
      r.safe_wind_mw ?? '',
      r.actual_mw ?? '',
      r.error_mw ?? '',
      r.shortfall_mw ?? '',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `uk_wind_decision_${deliveryDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-sm)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Table Toolbar */}
      <div
        style={{
          padding: 'var(--space-4) var(--space-6)',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-3)',
        }}
      >
        <div>
          <h3
            style={{
              fontSize: 'var(--text-sm)',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
            }}
          >
            Settlement Period Ledger ({sortedRows.length} Half-Hours)
          </h3>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Audit trail of forecasts, derated safe commitments, and metered actuals (virtualized for high-speed scrolling)
          </p>
        </div>

        <button
          type="button"
          onClick={handleExportCsv}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            padding: '6px 12px',
            backgroundColor: 'var(--color-surface-sunken)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-text-secondary)',
            cursor: 'pointer',
          }}
        >
          <Download size={14} />
          <span>Export CSV</span>
        </button>
      </div>

      {/* Virtualized Table View */}
      <VirtualTable
        items={sortedRows}
        rowHeight={40}
        containerHeight={400}
        style={{ border: 'none', borderRadius: 0 }}
        renderHeader={() => (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '70px 110px 1fr 1fr 1fr 1fr 1fr 60px',
              padding: '8px 12px',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              color: 'var(--color-text-muted)',
              borderBottom: '1px solid var(--color-border)',
            }}
          >
            <div onClick={() => handleSort('settlement_period')} style={{ cursor: 'pointer' }}>
              SP {sortCol === 'settlement_period' && (sortAsc ? '▲' : '▼')}
            </div>
            <div>Start Time (UTC)</div>
            <div
              onClick={() => handleSort('decision_forecast_mw')}
              style={{ cursor: 'pointer', textAlign: 'right', color: 'var(--color-forecast)' }}
            >
              Forecast (MW) {sortCol === 'decision_forecast_mw' && (sortAsc ? '▲' : '▼')}
            </div>
            <div
              onClick={() => handleSort('safe_wind_mw')}
              style={{ cursor: 'pointer', textAlign: 'right', color: 'var(--color-safe-wind)' }}
            >
              Safe Wind (MW) {sortCol === 'safe_wind_mw' && (sortAsc ? '▲' : '▼')}
            </div>
            <div
              onClick={() => handleSort('actual_mw')}
              style={{ cursor: 'pointer', textAlign: 'right', color: 'var(--color-actual)' }}
            >
              Actual (MW) {sortCol === 'actual_mw' && (sortAsc ? '▲' : '▼')}
            </div>
            <div
              onClick={() => handleSort('error_mw')}
              style={{ cursor: 'pointer', textAlign: 'right' }}
            >
              Error (MW) {sortCol === 'error_mw' && (sortAsc ? '▲' : '▼')}
            </div>
            <div
              onClick={() => handleSort('shortfall_mw')}
              style={{ cursor: 'pointer', textAlign: 'right', color: 'var(--color-shortfall)' }}
            >
              Shortfall (MW) {sortCol === 'shortfall_mw' && (sortAsc ? '▲' : '▼')}
            </div>
            <div style={{ textAlign: 'center' }}>Action</div>
          </div>
        )}
        renderRow={(row) => {
          const hasNoForecast = row.decision_forecast_mw === null;
          return (
            <div
              key={row.start_time}
              style={{
                display: 'grid',
                gridTemplateColumns: '70px 110px 1fr 1fr 1fr 1fr 1fr 60px',
                padding: '0 12px',
                height: '40px',
                alignItems: 'center',
                fontSize: 'var(--text-xs)',
                borderBottom: '1px solid var(--color-border)',
                backgroundColor: hasNoForecast ? 'rgba(225, 29, 72, 0.05)' : 'transparent',
                transition: 'background-color 0.12s ease',
              }}
            >
              <div className="tabular-nums" style={{ fontWeight: 600 }}>
                {row.settlement_period}
              </div>
              <div className="tabular-nums" style={{ color: 'var(--color-text-secondary)' }}>
                {formatUtcTime(row.start_time)}
              </div>
              <div
                className="tabular-nums"
                style={{ textAlign: 'right', fontWeight: 600, color: 'var(--color-forecast)' }}
              >
                {hasNoForecast ? (
                  <span style={{ color: 'var(--color-shortfall)', fontStyle: 'italic' }}>Missing</span>
                ) : (
                  formatMW(row.decision_forecast_mw, 0, false)
                )}
              </div>
              <div
                className="tabular-nums"
                style={{ textAlign: 'right', fontWeight: 600, color: 'var(--color-safe-wind)' }}
              >
                {formatMW(row.safe_wind_mw, 0, false)}
              </div>
              <div
                className="tabular-nums"
                style={{ textAlign: 'right', fontWeight: 600, color: 'var(--color-actual)' }}
              >
                {formatMW(row.actual_mw, 0, false)}
              </div>
              <div
                className="tabular-nums"
                style={{ textAlign: 'right', color: 'var(--color-text-secondary)' }}
              >
                {formatSignedMW(row.error_mw, 0)}
              </div>
              <div
                className="tabular-nums"
                style={{
                  textAlign: 'right',
                  fontWeight: 600,
                  color: (row.shortfall_mw || 0) > 0 ? 'var(--color-shortfall)' : 'var(--color-text-muted)',
                }}
              >
                {formatMW(row.shortfall_mw, 0, false)}
              </div>
              <div style={{ textAlign: 'center' }}>
                <button
                  type="button"
                  onClick={() => onSelectPeriod && onSelectPeriod(row)}
                  aria-label={`View period ${row.settlement_period} details`}
                  style={{
                    padding: '4px',
                    color: 'var(--color-text-muted)',
                    borderRadius: 'var(--radius-sm)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    cursor: 'pointer',
                  }}
                >
                  <Eye size={14} />
                </button>
              </div>
            </div>
          );
        }}
      />
    </div>
  );
}
