import React from 'react';

interface SkeletonProps {
  height?: string | number;
  width?: string | number;
  borderRadius?: string;
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({
  height = '20px',
  width = '100%',
  borderRadius = 'var(--radius-sm)',
  className = '',
  style,
}: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{
        height,
        width,
        borderRadius,
        ...style,
      }}
    />
  );
}

export function HeroChartSkeleton() {
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
        height: '420px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Skeleton width="220px" height="24px" />
        <Skeleton width="180px" height="32px" borderRadius="var(--radius-md)" />
      </div>
      <Skeleton width="100%" height="320px" borderRadius="var(--radius-md)" />
    </div>
  );
}
