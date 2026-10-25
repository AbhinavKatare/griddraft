import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axe from 'axe-core';
import { Header } from '../components/Header.tsx';
import { ControlBar } from '../components/ControlBar.tsx';
import { MetricCard } from '../components/ui/MetricCard.tsx';
import { ErrorBanner } from '../components/ui/ErrorBanner.tsx';
import { BiasAlertBanner } from '../features/accuracy/BiasAlertBanner.tsx';
import type { AppUrlState } from '../types.ts';

const mockState: AppUrlState = {
  view: 'decision',
  deliveryDate: '2026-01-15',
  decisionTime: '09:00',
  resolution: '30m',
  safeWindMode: 'in_sample',
  quantile: 0.9,
  showLeakyLine: false,
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('Axe Accessibility Checks (WCAG 2.1 AA)', () => {
  it('Header component has no serious or critical accessibility violations', async () => {
    const { container } = renderWithClient(
      <Header activeView="decision" onSelectView={() => {}} onOpenMethodology={() => {}} />
    );

    const results = await axe.run(container, {
      runOnly: {
        type: 'tag',
        values: ['wcag2a', 'wcag2aa'],
      },
    });

    const seriousViolations = results.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical'
    );
    expect(seriousViolations).toHaveLength(0);
  });

  it('ControlBar component has no serious or critical accessibility violations', async () => {
    const { container } = render(
      <ControlBar state={mockState} updateState={() => {}} stepDeliveryDay={() => {}} />
    );

    const results = await axe.run(container, {
      runOnly: {
        type: 'tag',
        values: ['wcag2a', 'wcag2aa'],
      },
    });

    const seriousViolations = results.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical'
    );
    expect(seriousViolations).toHaveLength(0);
  });

  it('MetricCard component is accessible with valid aria and contrast', async () => {
    const { container } = render(
      <MetricCard
        label="Mean Absolute Error (MAE)"
        rawValue={2145.2}
        formattedDisplay="2,145.2"
        unit="MW"
        deltaText="18.5% NMAE"
        deltaType="neutral"
        accentColor="var(--color-forecast)"
        tooltip="Average absolute forecast sizing error per half-hour."
      />
    );

    const results = await axe.run(container, {
      runOnly: {
        type: 'tag',
        values: ['wcag2a', 'wcag2aa'],
      },
    });

    const seriousViolations = results.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical'
    );
    expect(seriousViolations).toHaveLength(0);
  });

  it('BiasAlertBanner and ErrorBanner have valid alert/region semantics', async () => {
    const { container: bannerContainer } = render(
      <BiasAlertBanner decisionTime="09:00" />
    );

    const bannerResults = await axe.run(bannerContainer, {
      runOnly: {
        type: 'tag',
        values: ['wcag2a', 'wcag2aa'],
      },
    });
    expect(
      bannerResults.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
    ).toHaveLength(0);

    const { container: errorContainer } = render(
      <ErrorBanner
        error={new Error('Failed to load settlement data from Elexon')}
        onRetry={() => {}}
      />
    );

    const errorResults = await axe.run(errorContainer, {
      runOnly: {
        type: 'tag',
        values: ['wcag2a', 'wcag2aa'],
      },
    });
    expect(
      errorResults.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
    ).toHaveLength(0);
  });
});
