import { useState } from 'react';
import { motion } from 'motion/react';
import { Info } from 'lucide-react';
import { useAnimatedNumber } from '../../hooks/useAnimatedNumber.ts';
import { formatNumber } from '../../lib/format.ts';
import { staggerItemVariants } from '../../design/motion.ts';

interface MetricCardProps {
  label: string;
  rawValue: number | null | undefined;
  formattedDisplay?: string;
  unit?: string;
  decimals?: number;
  deltaText?: string;
  deltaType?: 'positive' | 'negative' | 'neutral' | 'warning';
  tooltip?: string;
  accentColor?: string;
  subtitle?: string;
}

export function MetricCard({
  label,
  rawValue,
  formattedDisplay,
  unit,
  decimals = 0,
  deltaText,
  deltaType = 'neutral',
  tooltip,
  accentColor,
  subtitle,
}: MetricCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const animatedValue = useAnimatedNumber(rawValue, 400);

  // Determine display number
  const displayNumber = formattedDisplay
    ? formattedDisplay
    : animatedValue !== null
    ? formatNumber(animatedValue, decimals)
    : '—';

  // Delta badge styling
  const getDeltaBadgeStyle = () => {
    switch (deltaType) {
      case 'positive':
        return {
          bg: 'var(--color-safe-wind-bg)',
          color: 'var(--color-safe-wind)',
          border: 'rgba(16, 185, 129, 0.2)',
        };
      case 'negative':
      case 'warning':
        return {
          bg: 'var(--color-shortfall-bg)',
          color: 'var(--color-shortfall)',
          border: 'rgba(225, 29, 72, 0.2)',
        };
      default:
        return {
          bg: 'var(--color-surface-sunken)',
          color: 'var(--color-text-muted)',
          border: 'var(--color-border)',
        };
    }
  };

  const deltaStyle = getDeltaBadgeStyle();

  return (
    <motion.div
      variants={staggerItemVariants}
      style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-4)',
        boxShadow: 'var(--shadow-sm)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
        position: 'relative',
        borderLeft: accentColor ? `3px solid ${accentColor}` : undefined,
      }}
    >
      {/* Top Header: Label & Tooltip trigger */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
        <span
          style={{
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-text-muted)',
          }}
        >
          {label}
        </span>
        {tooltip && (
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              aria-label={`More info on ${label}`}
              onClick={() => setShowTooltip((p) => !p)}
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              style={{
                color: 'var(--color-text-muted)',
                padding: '2px',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <Info size={14} />
            </button>
            {showTooltip && (
              <div
                role="tooltip"
                style={{
                  position: 'absolute',
                  top: '100%',
                  right: 0,
                  zIndex: 40,
                  width: '220px',
                  padding: '8px 12px',
                  backgroundColor: 'var(--color-surface-elevated)',
                  border: '1px solid var(--color-border-hover)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-lg)',
                  fontSize: 'var(--text-xs)',
                  color: 'var(--color-text-secondary)',
                  lineHeight: '1.4',
                  marginTop: '4px',
                }}
              >
                {tooltip}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Main KPI Value */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span
          className="stat-value tabular-nums"
          style={{
            fontSize: 'var(--text-xl)',
            fontWeight: 700,
            color: 'var(--color-text-primary)',
            letterSpacing: '-0.02em',
          }}
        >
          {displayNumber}
        </span>
        {unit && (
          <span
            style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 500,
              color: 'var(--color-text-muted)',
            }}
          >
            {unit}
          </span>
        )}
      </div>

      {/* Subtitle / Delta Chip */}
      {(deltaText || subtitle) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
          {deltaText && (
            <motion.span
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '2px 6px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: deltaStyle.bg,
                color: deltaStyle.color,
                border: `1px solid ${deltaStyle.border}`,
                display: 'inline-flex',
                alignItems: 'center',
              }}
            >
              {deltaText}
            </motion.span>
          )}
          {subtitle && (
            <span
              style={{
                fontSize: '11px',
                color: 'var(--color-text-muted)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {subtitle}
            </span>
          )}
        </div>
      )}
    </motion.div>
  );
}
