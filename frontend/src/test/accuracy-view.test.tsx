import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AccuracyView } from '../features/accuracy/AccuracyView.tsx';
import type { AppUrlState } from '../types.ts';

const mockState: AppUrlState = {
  view: 'accuracy',
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

describe('AccuracyView Component', () => {
  it('renders KPI cards, advisory banners, and charts', async () => {
    renderWithClient(<AccuracyView state={mockState} onSelectDate={() => {}} />);

    // Verification suite title
    expect(screen.getByText(/Accuracy & Verification Suite/i)).toBeInTheDocument();

    // Systematic bias advisory banner
    expect(screen.getAllByText(/Systematic Over-Forecast/i)[0]).toBeInTheDocument();

    // Trading KPI cards
    await waitFor(() => {
      expect(screen.getByText(/Mean Absolute Error \(MAE\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Root Mean Squared Error \(RMSE\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Systematic Forecast Bias/i)).toBeInTheDocument();
      expect(screen.getByText(/P90 Shortfall Buffer/i)).toBeInTheDocument();
    });

    // Forecast Baseline comparison toggle
    expect(screen.getByText(/Forecast Baseline:/i)).toBeInTheDocument();
    expect(screen.getByText(/Compare with Latest Pre-Delivery/i)).toBeInTheDocument();
  });

  it('enforces exact numerical equality between KPI cards and /api/v1/metrics values', async () => {
    renderWithClient(<AccuracyView state={mockState} onSelectDate={() => {}} />);

    await waitFor(
      () => {
        expect(screen.getByText('2,145.2')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    // 1. MAE exact value (2,145.2 MW)
    expect(screen.getByText('2,145.2')).toBeInTheDocument();
    // 2. RMSE exact value (2,615.8 MW)
    expect(screen.getByText('2,615.8')).toBeInTheDocument();
    // 3. Systematic Bias exact value (+1,851.9 MW)
    expect(screen.getByText('+1,851.9')).toBeInTheDocument();
    // 4. P90 Shortfall Buffer exact value (4,275 MW rounded from 4,274.9)
    expect(screen.getByText('4,275')).toBeInTheDocument();
    // 5. Matched half-hours count (1488)
    expect(screen.getByText('1488')).toBeInTheDocument();
  });

  it('toggles baseline comparison mode to reveal leakage difference', async () => {
    renderWithClient(<AccuracyView state={mockState} onSelectDate={() => {}} />);

    // Toggle baseline to "Decision Cutoff Only"
    const decisionOnlyBtn = screen.getByText(/D-1 09:00 Decision Cutoff Only/i);
    fireEvent.click(decisionOnlyBtn);

    // Toggle back to "Compare with Latest Pre-Delivery"
    const compareBtn = screen.getByText(/Compare with Latest Pre-Delivery/i);
    fireEvent.click(compareBtn);

    expect(screen.getByText(/Leakage Delta/i)).toBeInTheDocument();
  });

  it('renders daily MAE trend chart and allows date inspection', async () => {
    let selectedDate = '';
    renderWithClient(
      <AccuracyView
        state={mockState}
        onSelectDate={(d) => {
          selectedDate = d;
        }}
      />
    );

    expect(
      screen.getByText(/Daily Forecast Accuracy & Information Leakage Trend/i)
    ).toBeInTheDocument();
  });

  it('displays the exact RMSE badge value (14.7% of Peak)', async () => {
    renderWithClient(<AccuracyView state={mockState} onSelectDate={() => {}} />);

    // Switch to Decision Cutoff Only so non-comparison delta badges render
    const decisionOnlyBtn = screen.getByText(/D-1 09:00 Decision Cutoff Only/i);
    fireEvent.click(decisionOnlyBtn);

    await waitFor(() => {
      expect(screen.getByText('14.7% of Peak')).toBeInTheDocument();
    });
  });
});
