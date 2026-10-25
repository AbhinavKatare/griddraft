import { AnimatePresence, motion } from 'motion/react';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';
import type { ToastMessage } from '../../types.ts';
import { motionTokens } from '../../design/motion.ts';

interface ToastContainerProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  return (
    <div
      style={{
        position: 'fixed',
        top: '16px',
        right: '16px',
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        pointerEvents: 'none',
      }}
    >
      <AnimatePresence>
        {toasts.map((toast) => {
          const isError = toast.type === 'error';
          const isSuccess = toast.type === 'success';

          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: -16, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95, transition: { duration: motionTokens.duration.micro } }}
              transition={motionTokens.spring.control}
              style={{
                pointerEvents: 'auto',
                backgroundColor: 'var(--color-surface-elevated)',
                border: '1px solid var(--color-border)',
                borderLeft: isError
                  ? '3px solid var(--color-shortfall)'
                  : isSuccess
                  ? '3px solid var(--color-safe-wind)'
                  : '3px solid var(--color-forecast)',
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-lg)',
                padding: '10px 14px',
                width: '320px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
              }}
            >
              <div
                style={{
                  color: isError
                    ? 'var(--color-shortfall)'
                    : isSuccess
                    ? 'var(--color-safe-wind)'
                    : 'var(--color-forecast)',
                  marginTop: '1px',
                  flexShrink: 0,
                }}
              >
                {isError ? (
                  <AlertCircle size={16} />
                ) : isSuccess ? (
                  <CheckCircle2 size={16} />
                ) : (
                  <Info size={16} />
                )}
              </div>

              <div style={{ flex: 1 }}>
                <div
                  style={{
                    fontSize: 'var(--text-xs)',
                    fontWeight: 600,
                    color: 'var(--color-text-primary)',
                  }}
                >
                  {toast.title}
                </div>
                {toast.message && (
                  <div
                    style={{
                      fontSize: '11px',
                      color: 'var(--color-text-muted)',
                      marginTop: '2px',
                    }}
                  >
                    {toast.message}
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={() => onDismiss(toast.id)}
                style={{
                  color: 'var(--color-text-muted)',
                  padding: '2px',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <X size={14} />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
