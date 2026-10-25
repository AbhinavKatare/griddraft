import { renderHook, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { useUrlState } from '../hooks/useUrlState.ts';

describe('useUrlState hook', () => {
  it('initializes with expected default trading state', () => {
    const { result } = renderHook(() => useUrlState(), {
      wrapper: ({ children }) => <MemoryRouter initialEntries={['/']}>{children}</MemoryRouter>,
    });

    expect(result.current.state.view).toBe('decision');
    expect(result.current.state.deliveryDate).toBe('2026-01-15');
    expect(result.current.state.decisionTime).toBe('09:00');
    expect(result.current.state.quantile).toBe(0.9);
    expect(result.current.state.safeWindMode).toBe('in_sample');
    expect(result.current.state.resolution).toBe('30m');
  });

  it('updates state and syncs to search parameters', () => {
    const { result } = renderHook(() => useUrlState(), {
      wrapper: ({ children }) => <MemoryRouter initialEntries={['/']}>{children}</MemoryRouter>,
    });

    act(() => {
      result.current.updateState({
        deliveryDate: '2026-01-20',
        decisionTime: '08:00',
        safeWindMode: 'prior_days',
      });
    });

    expect(result.current.state.deliveryDate).toBe('2026-01-20');
    expect(result.current.state.decisionTime).toBe('08:00');
    expect(result.current.state.safeWindMode).toBe('prior_days');
  });

  it('steps delivery day forward and backward respecting January 2026 bounds', () => {
    const { result } = renderHook(() => useUrlState(), {
      wrapper: ({ children }) => (
        <MemoryRouter initialEntries={['/?date=2026-01-15']}>{children}</MemoryRouter>
      ),
    });

    act(() => {
      result.current.stepDeliveryDay(1);
    });
    expect(result.current.state.deliveryDate).toBe('2026-01-16');

    act(() => {
      result.current.stepDeliveryDay(-1);
    });
    expect(result.current.state.deliveryDate).toBe('2026-01-15');
  });
});
