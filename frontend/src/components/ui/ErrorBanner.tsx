import { AlertCircle, RefreshCw } from 'lucide-react';
import type { ProblemDetail } from '../../types.ts';

interface ErrorBannerProps {
  error: Error | null;
  onRetry?: () => void;
  title?: string;
}

export function ErrorBanner({ error, onRetry, title = 'Data Request Failed' }: ErrorBannerProps) {
  if (!error) return null;

  // Extract possible RFC 7807 problem details
  const problem: ProblemDetail | undefined = (error as any).problem;
  const status = (error as any).status || 500;
  const displayTitle = problem?.title || error.message || title;
  const detail = problem?.detail;
  const invalidParams = problem?.invalid_params;

  return (
    <div
      role="alert"
      style={{
        backgroundColor: 'var(--color-shortfall-bg)',
        border: '1px solid var(--color-shortfall-stroke)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-4) var(--space-5)',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 'var(--space-4)',
        boxShadow: 'var(--shadow-sm)',
        margin: 'var(--space-4) 0',
      }}
    >
      <div
        style={{
          color: 'var(--color-shortfall)',
          marginTop: '2px',
          flexShrink: 0,
        }}
      >
        <AlertCircle size={20} />
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h3
            style={{
              fontSize: 'var(--text-sm)',
              fontWeight: 700,
              color: 'var(--color-shortfall)',
            }}
          >
            {displayTitle}
          </h3>
          <span
            className="tabular-nums"
            style={{
              fontSize: '11px',
              padding: '1px 6px',
              backgroundColor: 'rgba(225, 29, 72, 0.15)',
              color: 'var(--color-shortfall)',
              borderRadius: 'var(--radius-sm)',
              fontWeight: 600,
            }}
          >
            HTTP {status}
          </span>
        </div>

        {detail && (
          <p
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--color-text-secondary)',
              marginTop: '4px',
              lineHeight: 1.5,
            }}
          >
            {detail}
          </p>
        )}

        {invalidParams && invalidParams.length > 0 && (
          <ul
            style={{
              marginTop: '6px',
              paddingLeft: '16px',
              fontSize: '11px',
              color: 'var(--color-text-muted)',
            }}
          >
            {invalidParams.map((p, idx) => (
              <li key={idx}>
                <strong style={{ color: 'var(--color-text-secondary)' }}>{p.name}</strong>: {p.reason}
              </li>
            ))}
          </ul>
        )}
      </div>

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            padding: '6px 12px',
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-shortfall-stroke)',
            color: 'var(--color-shortfall)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-sm)',
            cursor: 'pointer',
            flexShrink: 0,
          }}
        >
          <RefreshCw size={14} />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
}
