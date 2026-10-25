import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server.ts';
import { DecisionView } from '../features/decision/DecisionView.tsx';
import type { AppUrlState } from '../types.ts';

const mockState: AppUrlState = {
  view: 'decision',
  deliveryDate: '2026-01-15',
  decisionTime: '09:00',
  forecastMode: 'decision_time',
  showLeakyLine: false,
  safeWindMode: 'in_sample',
  quantile: 0.90,
  resolution: '30m',
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        retryDelay: 0,
        gcTime: 0,
      },
    },
  });

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('DecisionView integration', () => {
  it('renders happy path data with summary strip, charts, and period ledger', async () => {
    renderWithClient(<DecisionView state={mockState} />);

    // Wait for data to load and assert summary strip presence
    await waitFor(() => {
      expect(screen.getByText(/Auction Decision Snapshot:/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Forecast Day Volume/i)).toBeInTheDocument();
    expect(screen.getByText(/Conservative 'Safe' Volume/i)).toBeInTheDocument();
    expect(screen.getByText(/Peak Extra Procurement/i)).toBeInTheDocument();
    expect(screen.getByText(/Settlement Period Ledger/i)).toBeInTheDocument();
  });

  it('renders empty timeseries without crashing', async () => {
    server.use(
      http.get('/api/v1/timeseries', () => {
        return HttpResponse.json({
          start_date: '2026-01-15',
          end_date: '2026-01-15',
          decision_time: '09:00',
          total_points: 0,
          data: [],
        });
      })
    );

    renderWithClient(<DecisionView state={mockState} />);

    await waitFor(() => {
      expect(screen.getByText(/Settlement Period Ledger \(0 Half-Hours\)/i)).toBeInTheDocument();
    });
  });

  it('renders RFC 7807 error banner on backend failure', async () => {
    server.use(
      http.get('/api/v1/timeseries', () => {
        return HttpResponse.json(
          {
            type: 'https://tools.ietf.org/html/rfc7807',
            title: 'Invalid Date Range',
            status: 400,
            detail: 'start_date cannot be after end_date',
            instance: '/api/v1/timeseries',
          },
          { status: 400 }
        );
      })
    );

    renderWithClient(<DecisionView state={mockState} />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/Invalid Date Range/i)).toBeInTheDocument();
      expect(screen.getByText(/HTTP 400/i)).toBeInTheDocument();
    });
  });
});
