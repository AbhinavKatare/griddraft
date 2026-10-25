import { useEffect } from 'react';
import { Calendar, ChevronLeft, ChevronRight, Clock, Eye, Layers, ShieldCheck } from 'lucide-react';
import { SegmentedControl } from './ui/SegmentedControl.tsx';
import type { AppUrlState, CutoffPreset, SafeWindMode, TemporalResolution } from '../types.ts';

interface ControlBarProps {
  state: AppUrlState;
  updateState: (updates: Partial<AppUrlState>) => void;
  stepDeliveryDay: (direction: -1 | 1) => void;
}

export function ControlBar({ state, updateState, stepDeliveryDay }: ControlBarProps) {
  // Arrow key navigation for delivery day
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        return;
      }
      if (e.key === 'ArrowLeft') {
        stepDeliveryDay(-1);
      } else if (e.key === 'ArrowRight') {
        stepDeliveryDay(1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [stepDeliveryDay]);

  const cutoffPresets: { value: CutoffPreset; label: string }[] = [
    { value: '08:00', label: '08:00 UTC' },
    { value: '09:00', label: '09:00 UTC' },
    { value: '10:00', label: '10:00 UTC' },
  ];

  const handleCutoffChange = (val: string) => {
    updateState({ decisionTime: val });
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface)',
        borderBottom: '1px solid var(--color-border)',
        padding: 'var(--space-3) var(--space-6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 'var(--space-4)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* 1. Delivery Date Selector with Prev/Next Day buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <button
            type="button"
            onClick={() => stepDeliveryDay(-1)}
            disabled={state.deliveryDate <= '2026-01-01'}
            aria-label="Previous day (Left Arrow)"
            title="Previous delivery day (Left Arrow)"
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-surface-sunken)',
              color: state.deliveryDate <= '2026-01-01' ? 'var(--color-text-disabled)' : 'var(--color-text-secondary)',
              cursor: state.deliveryDate <= '2026-01-01' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <ChevronLeft size={16} />
          </button>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--color-surface-sunken)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: '4px 10px',
            }}
          >
            <Calendar size={14} style={{ color: 'var(--color-forecast)' }} />
            <input
              type="date"
              aria-label="Delivery Date"
              min="2026-01-01"
              max="2026-01-31"
              value={state.deliveryDate}
              onChange={(e) => updateState({ deliveryDate: e.target.value })}
              className="tabular-nums"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--color-text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
            />
          </div>

          <button
            type="button"
            onClick={() => stepDeliveryDay(1)}
            disabled={state.deliveryDate >= '2026-01-31'}
            aria-label="Next day (Right Arrow)"
            title="Next delivery day (Right Arrow)"
            style={{
              padding: '6px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-surface-sunken)',
              color: state.deliveryDate >= '2026-01-31' ? 'var(--color-text-disabled)' : 'var(--color-text-secondary)',
              cursor: state.deliveryDate >= '2026-01-31' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* 2. Decision Cutoff Selector & Preset Snaps */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Clock size={14} style={{ color: 'var(--color-forecast)' }} />
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
            D-1 Cutoff:
          </span>
        </div>

        <SegmentedControl<string>
          name="cutoff-presets"
          size="sm"
          options={cutoffPresets}
          value={state.decisionTime}
          onChange={handleCutoffChange}
        />

        {/* Custom time picker */}
        <input
          type="time"
          step="1800"
          value={state.decisionTime}
          onChange={(e) => handleCutoffChange(e.target.value)}
          aria-label="Custom decision cutoff time"
          className="tabular-nums"
          style={{
            padding: '4px 8px',
            fontSize: 'var(--text-xs)',
            fontFamily: 'var(--font-mono)',
            fontWeight: 600,
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border)',
            backgroundColor: 'var(--color-surface-sunken)',
            color: 'var(--color-text-primary)',
            outline: 'none',
          }}
        />
      </div>

      {/* 3. Safe-Wind Mode & Quantile Selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ShieldCheck size={14} style={{ color: 'var(--color-safe-wind)' }} />
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
            Safe Wind:
          </span>
        </div>

        <SegmentedControl<SafeWindMode>
          name="safe-wind-mode"
          size="sm"
          options={[
            { value: 'in_sample', label: 'In-Sample' },
            { value: 'prior_days', label: 'Prior-Days' },
          ]}
          value={state.safeWindMode}
          onChange={(val) => updateState({ safeWindMode: val })}
        />

        <SegmentedControl<number>
          name="quantile-preset"
          size="sm"
          options={[
            { value: 0.50, label: 'P50' },
            { value: 0.90, label: 'P90' },
            { value: 0.95, label: 'P95' },
          ]}
          value={state.quantile}
          onChange={(val) => updateState({ quantile: val })}
        />
      </div>

      {/* 4. Downsampling & Leaky Line Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Resolution selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Layers size={14} style={{ color: 'var(--color-text-muted)' }} />
          <SegmentedControl<TemporalResolution>
            name="temporal-resolution"
            size="sm"
            options={[
              { value: '30m', label: '30m' },
              { value: '1h', label: '1h' },
              { value: '3h', label: '3h' },
            ]}
            value={state.resolution}
            onChange={(res) => updateState({ resolution: res })}
          />
        </div>

        {/* Leaky ghost line toggle */}
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: 'var(--text-xs)',
            fontWeight: 500,
            color: state.showLeakyLine ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
            cursor: 'pointer',
            padding: '4px 8px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: state.showLeakyLine ? 'var(--color-surface-hover)' : 'transparent',
            border: '1px solid var(--color-border)',
            userSelect: 'none',
          }}
        >
          <input
            type="checkbox"
            checked={state.showLeakyLine}
            onChange={(e) => updateState({ showLeakyLine: e.target.checked })}
            style={{ accentColor: 'var(--color-forecast)' }}
          />
          <Eye size={12} />
          <span>Show Latest (Leaky)</span>
        </label>
      </div>
    </div>
  );
}
