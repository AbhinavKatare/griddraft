import { motion } from 'motion/react';
import { motionTokens } from '../../design/motion.ts';

export interface SegmentOption<T extends string | number> {
  value: T;
  label: string;
  badge?: string;
  description?: string;
}

interface SegmentedControlProps<T extends string | number> {
  name: string;
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  size?: 'sm' | 'md';
  ariaLabel?: string;
}

export function SegmentedControl<T extends string | number>({
  name,
  options,
  value,
  onChange,
  size = 'md',
  ariaLabel,
}: SegmentedControlProps<T>) {
  const isSm = size === 'sm';

  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel || name}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px',
        backgroundColor: 'var(--color-surface-sunken)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        position: 'relative',
        userSelect: 'none',
      }}
    >
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={String(opt.value)}
            role="radio"
            aria-checked={isSelected}
            onClick={() => onChange(opt.value)}
            style={{
              position: 'relative',
              zIndex: 1,
              padding: isSm ? '4px 8px' : '6px 12px',
              fontSize: isSm ? 'var(--text-xs)' : 'var(--text-sm)',
              fontWeight: isSelected ? 600 : 500,
              color: isSelected ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
              borderRadius: 'var(--radius-sm)',
              transition: 'color 0.15s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            {isSelected && (
              <motion.div
                layoutId={`pill-${name}`}
                style={{
                  position: 'absolute',
                  inset: 0,
                  backgroundColor: 'var(--color-surface)',
                  borderRadius: 'var(--radius-sm)',
                  boxShadow: 'var(--shadow-sm)',
                  border: '1px solid var(--color-border)',
                  zIndex: -1,
                }}
                transition={motionTokens.spring.control}
              />
            )}
            <span>{opt.label}</span>
            {opt.badge && (
              <span
                style={{
                  fontSize: '10px',
                  padding: '1px 4px',
                  backgroundColor: isSelected ? 'var(--color-forecast-bg)' : 'var(--color-border)',
                  color: isSelected ? 'var(--color-forecast)' : 'var(--color-text-muted)',
                  borderRadius: 'var(--radius-full)',
                  fontWeight: 600,
                }}
              >
                {opt.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
