import React, { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { X } from 'lucide-react';
import { drawerVariants, motionTokens } from '../../design/motion.ts';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  width?: string;
}

export function Drawer({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  width = '480px',
}: DrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;

  // ESC key handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Trap focus or prevent body scroll
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: motionTokens.duration.ui }}
            onClick={onClose}
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(9, 13, 22, 0.65)',
              backdropFilter: 'blur(2px)',
              zIndex: 50,
            }}
          />

          {/* Drawer Container */}
          <motion.div
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="drawer-title"
            variants={drawerVariants}
            initial={isMobile ? 'hiddenBottom' : 'hiddenRight'}
            animate={isMobile ? 'visibleBottom' : 'visibleRight'}
            exit={isMobile ? 'hiddenBottom' : 'hiddenRight'}
            style={{
              position: 'fixed',
              top: isMobile ? 'auto' : 0,
              bottom: 0,
              right: 0,
              left: isMobile ? 0 : 'auto',
              width: isMobile ? '100%' : width,
              maxHeight: isMobile ? '85vh' : '100vh',
              height: isMobile ? 'auto' : '100%',
              backgroundColor: 'var(--color-surface-elevated)',
              borderLeft: isMobile ? 'none' : '1px solid var(--color-border)',
              borderTop: isMobile ? '1px solid var(--color-border)' : 'none',
              borderRadius: isMobile ? 'var(--radius-xl) var(--radius-xl) 0 0' : '0',
              boxShadow: 'var(--shadow-lg)',
              zIndex: 51,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {/* Header */}
            <div
              style={{
                padding: 'var(--space-4) var(--space-6)',
                borderBottom: '1px solid var(--color-border)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: 'var(--color-surface)',
              }}
            >
              <div>
                <h2
                  id="drawer-title"
                  style={{
                    fontSize: 'var(--text-lg)',
                    fontWeight: 700,
                    color: 'var(--color-text-primary)',
                    letterSpacing: '-0.01em',
                  }}
                >
                  {title}
                </h2>
                {subtitle && (
                  <p
                    style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--color-text-muted)',
                      marginTop: '2px',
                    }}
                  >
                    {subtitle}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close drawer"
                style={{
                  padding: '6px',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--color-text-muted)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: 'var(--color-surface-sunken)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Scrollable Body */}
            <div
              style={{
                padding: 'var(--space-6)',
                overflowY: 'auto',
                flex: 1,
              }}
            >
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
