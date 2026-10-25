import { useEffect, useRef, useState, type ReactNode } from 'react';

interface VirtualTableProps<T> {
  items: T[];
  rowHeight: number;
  containerHeight?: number;
  buffer?: number;
  renderHeader?: () => ReactNode;
  renderRow: (item: T, index: number) => ReactNode;
  emptyState?: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * Lightweight, zero-dependency virtualized table list for rendering high-density
 * settlement period ledger rows smoothly without DOM bloating.
 */
export function VirtualTable<T>({
  items,
  rowHeight,
  containerHeight = 440,
  buffer = 5,
  renderHeader,
  renderRow,
  emptyState,
  style,
}: VirtualTableProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const totalCount = items.length;
  const totalHeight = totalCount * rowHeight;

  const onScroll = () => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
    }
  };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, []);

  if (totalCount === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  // Calculate visible range with buffer
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - buffer);
  const endIndex = Math.min(totalCount, Math.ceil((scrollTop + containerHeight) / rowHeight) + buffer);

  const visibleItems = items.slice(startIndex, endIndex);
  const offsetY = startIndex * rowHeight;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        ...style,
      }}
    >
      {/* Sticky Table Header */}
      {renderHeader && (
        <div
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 2,
            backgroundColor: 'var(--color-surface-sunken)',
            borderBottom: '1px solid var(--color-border)',
          }}
        >
          {renderHeader()}
        </div>
      )}

      {/* Virtual Scroll Viewport */}
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          height: `${containerHeight}px`,
          overflowY: 'auto',
          overflowX: 'auto',
          WebkitOverflowScrolling: 'touch',
        }}
      >
        <div style={{ height: `${totalHeight}px`, width: '100%', position: 'relative' }}>
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              transform: `translateY(${offsetY}px)`,
            }}
          >
            {visibleItems.map((item, index) => renderRow(item, startIndex + index))}
          </div>
        </div>
      </div>
    </div>
  );
}
