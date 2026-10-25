import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import type {
  AppUrlState,
  ForecastMode,
  SafeWindMode,
  TemporalResolution,
  ViewTab,
} from '../types.ts';

const DEFAULT_STATE: AppUrlState = {
  view: 'decision',
  deliveryDate: '2026-01-15',
  decisionTime: '09:00',
  forecastMode: 'decision_time',
  showLeakyLine: false,
  safeWindMode: 'in_sample',
  quantile: 0.90,
  resolution: '30m',
};

export function useUrlState() {
  const [searchParams, setSearchParams] = useSearchParams();

  const state: AppUrlState = useMemo(() => {
    const viewParam = searchParams.get('view') as ViewTab | null;
    const view: ViewTab = viewParam === 'accuracy' || viewParam === 'methodology' ? viewParam : 'decision';

    const deliveryDate = searchParams.get('date') || DEFAULT_STATE.deliveryDate;
    const decisionTime = searchParams.get('cutoff') || DEFAULT_STATE.decisionTime;

    const modeParam = searchParams.get('mode') as ForecastMode | null;
    const forecastMode: ForecastMode =
      modeParam === 'latest' || modeParam === 'fixed_horizon' ? modeParam : 'decision_time';

    const showLeakyLine = searchParams.get('leaky') === 'true';

    const safeParam = searchParams.get('safe_mode') as SafeWindMode | null;
    const safeWindMode: SafeWindMode = safeParam === 'prior_days' ? 'prior_days' : 'in_sample';

    const qParam = parseFloat(searchParams.get('q') || '0.90');
    const quantile = !Number.isNaN(qParam) && [0.5, 0.9, 0.95].includes(qParam) ? qParam : 0.90;

    const resParam = searchParams.get('res') as TemporalResolution | null;
    const resolution: TemporalResolution =
      resParam === '1h' || resParam === '3h' ? resParam : '30m';

    return {
      view,
      deliveryDate,
      decisionTime,
      forecastMode,
      showLeakyLine,
      safeWindMode,
      quantile,
      resolution,
    };
  }, [searchParams]);

  const updateState = useCallback(
    (updates: Partial<AppUrlState>, replace: boolean = false) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);

          if (updates.view !== undefined) next.set('view', updates.view);
          if (updates.deliveryDate !== undefined) next.set('date', updates.deliveryDate);
          if (updates.decisionTime !== undefined) next.set('cutoff', updates.decisionTime);
          if (updates.forecastMode !== undefined) next.set('mode', updates.forecastMode);
          if (updates.showLeakyLine !== undefined) next.set('leaky', String(updates.showLeakyLine));
          if (updates.safeWindMode !== undefined) next.set('safe_mode', updates.safeWindMode);
          if (updates.quantile !== undefined) next.set('q', String(updates.quantile));
          if (updates.resolution !== undefined) next.set('res', updates.resolution);

          return next;
        },
        { replace }
      );
    },
    [setSearchParams]
  );

  /**
   * Navigate delivery day forward or backward with bounds checking (2026-01-01 to 2026-01-31)
   */
  const stepDeliveryDay = useCallback(
    (direction: -1 | 1) => {
      const current = new Date(`${state.deliveryDate}T00:00:00Z`);
      current.setUTCDate(current.getUTCDate() + direction);
      const minDate = new Date('2026-01-01T00:00:00Z');
      const maxDate = new Date('2026-01-31T00:00:00Z');

      if (current >= minDate && current <= maxDate) {
        const nextIso = current.toISOString().slice(0, 10);
        updateState({ deliveryDate: nextIso });
      }
    },
    [state.deliveryDate, updateState]
  );

  return {
    state,
    updateState,
    stepDeliveryDay,
  };
}
