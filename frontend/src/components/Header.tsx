import { motion } from 'motion/react';
import { BookOpen, Database, Moon, Sun, Wind } from 'lucide-react';
import { useMeta } from '../api/queries.ts';
import { useTheme } from '../hooks/useTheme.ts';
import { motionTokens } from '../design/motion.ts';
import type { ViewTab } from '../types.ts';

interface HeaderProps {
  activeView: ViewTab;
  onSelectView: (view: ViewTab) => void;
  onOpenMethodology: () => void;
}

export function Header({ activeView, onSelectView, onOpenMethodology }: HeaderProps) {
  const { theme, toggleTheme } = useTheme();
  const { data: meta, isLoading: metaLoading } = useMeta();

  const navItems: { id: ViewTab; label: string }[] = [
    { id: 'decision', label: 'Decision View' },
    { id: 'accuracy', label: 'Accuracy & Verification' },
    { id: 'methodology', label: 'Methodology' },
  ];

  const handleNavClick = (id: ViewTab) => {
    if (id === 'methodology') {
      onOpenMethodology();
    } else {
      onSelectView(id);
    }
  };

  return (
    <header
      style={{
        backgroundColor: 'var(--color-surface)',
        borderBottom: '1px solid var(--color-border)',
        padding: 'var(--space-3) var(--space-6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 'var(--space-4)',
        position: 'sticky',
        top: 0,
        zIndex: 30,
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Brand & Data Lineage Pill */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              padding: '6px',
              backgroundColor: 'var(--color-forecast-bg)',
              color: 'var(--color-forecast)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Wind size={20} />
          </div>
          <div>
            <h1
              style={{
                fontSize: 'var(--text-base)',
                fontWeight: 700,
                color: 'var(--color-text-primary)',
                letterSpacing: '-0.02em',
                lineHeight: 1.1,
              }}
            >
              UK Wind Forecast Monitor
            </h1>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 500,
                color: 'var(--color-text-muted)',
              }}
            >
              Day-Ahead EPEX SPOT / Nord Pool Decision Support
            </span>
          </div>
        </div>

        {/* Elexon BMRS Data Status Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '3px 8px',
            backgroundColor: 'var(--color-surface-sunken)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-full)',
            fontSize: '11px',
            color: 'var(--color-text-secondary)',
          }}
        >
          <Database size={12} style={{ color: 'var(--color-actual)' }} />
          <span>Elexon BMRS:</span>
          {metaLoading ? (
            <span style={{ color: 'var(--color-text-muted)' }}>Verifying cache...</span>
          ) : meta ? (
            <span className="tabular-nums" style={{ fontWeight: 600 }}>
              {meta.available_start_date.slice(5)} to {meta.available_end_date.slice(5)} ({meta.fuelhh_rows} HH)
            </span>
          ) : (
            <span style={{ color: 'var(--color-shortfall)' }}>Cache offline</span>
          )}
        </div>
      </div>

      {/* Center Nav Segmented Controls */}
      <nav
        role="tablist"
        aria-label="Application Views"
        style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'var(--color-surface-sunken)',
          padding: '2px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border)',
        }}
      >
        {navItems.map((item) => {
          const isActive = activeView === item.id;
          return (
            <button
              key={item.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => handleNavClick(item.id)}
              style={{
                position: 'relative',
                padding: '6px 14px',
                fontSize: 'var(--text-xs)',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                borderRadius: 'var(--radius-sm)',
                transition: 'color 0.15s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              {isActive && (
                <motion.div
                  layoutId="header-nav-pill"
                  style={{
                    position: 'absolute',
                    inset: 0,
                    backgroundColor: 'var(--color-surface)',
                    borderRadius: 'var(--radius-sm)',
                    boxShadow: 'var(--shadow-sm)',
                    border: '1px solid var(--color-border)',
                    zIndex: 0,
                  }}
                  transition={motionTokens.spring.control}
                />
              )}
              <span style={{ position: 'relative', zIndex: 1 }}>{item.label}</span>
              {item.id === 'methodology' && (
                <BookOpen size={12} style={{ position: 'relative', zIndex: 1, opacity: 0.8 }} />
              )}
            </button>
          );
        })}
      </nav>

      {/* Right Controls: Theme Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          style={{
            padding: '6px 10px',
            backgroundColor: 'var(--color-surface-sunken)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-text-secondary)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: 'var(--text-xs)',
            fontWeight: 500,
          }}
        >
          {theme === 'light' ? <Moon size={14} /> : <Sun size={14} />}
          <span>{theme === 'light' ? 'Dark' : 'Light'}</span>
        </button>
      </div>
    </header>
  );
}
