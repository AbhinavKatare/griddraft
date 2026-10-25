import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ControlBar } from '../components/ControlBar.tsx';
import type { AppUrlState } from '../types.ts';

const initialMockState: AppUrlState = {
  view: 'decision',
  deliveryDate: '2026-01-15',
  decisionTime: '09:00',
  resolution: '30m',
  safeWindMode: 'in_sample',
  quantile: 0.9,
  showLeakyLine: false,
};

describe('ControlBar Component', () => {
  it('renders all control sections with current state values', () => {
    const updateState = vi.fn();
    const stepDeliveryDay = vi.fn();

    render(
      <ControlBar
        state={initialMockState}
        updateState={updateState}
        stepDeliveryDay={stepDeliveryDay}
      />
    );

    // Delivery date input
    const dateInput = screen.getByLabelText('Delivery Date') as HTMLInputElement;
    expect(dateInput.value).toBe('2026-01-15');

    // Prev / Next buttons
    expect(screen.getByTitle(/Previous delivery day/i)).toBeInTheDocument();
    expect(screen.getByTitle(/Next delivery day/i)).toBeInTheDocument();

    // Cutoff presets
    expect(screen.getByText('08:00 UTC')).toBeInTheDocument();
    expect(screen.getByText('09:00 UTC')).toBeInTheDocument();
    expect(screen.getByText('10:00 UTC')).toBeInTheDocument();

    // Safe wind mode & quantiles
    expect(screen.getByText('In-Sample')).toBeInTheDocument();
    expect(screen.getByText('Prior-Days')).toBeInTheDocument();
    expect(screen.getByText('P50')).toBeInTheDocument();
    expect(screen.getByText('P90')).toBeInTheDocument();
    expect(screen.getByText('P95')).toBeInTheDocument();

    // Resolution and leaky line toggle
    expect(screen.getByText('30m')).toBeInTheDocument();
    expect(screen.getByText('1h')).toBeInTheDocument();
    expect(screen.getByText('3h')).toBeInTheDocument();
    expect(screen.getByText('Show Latest (Leaky)')).toBeInTheDocument();
  });

  it('triggers stepDeliveryDay on button click and keyboard arrows', () => {
    const updateState = vi.fn();
    const stepDeliveryDay = vi.fn();

    render(
      <ControlBar
        state={initialMockState}
        updateState={updateState}
        stepDeliveryDay={stepDeliveryDay}
      />
    );

    // Click Previous day button
    fireEvent.click(screen.getByTitle(/Previous delivery day/i));
    expect(stepDeliveryDay).toHaveBeenCalledWith(-1);

    // Click Next day button
    fireEvent.click(screen.getByTitle(/Next delivery day/i));
    expect(stepDeliveryDay).toHaveBeenCalledWith(1);

    // Keyboard ArrowLeft
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(stepDeliveryDay).toHaveBeenCalledWith(-1);

    // Keyboard ArrowRight
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(stepDeliveryDay).toHaveBeenCalledWith(1);
  });

  it('updates cutoff time when preset or custom time changes', () => {
    const updateState = vi.fn();
    const stepDeliveryDay = vi.fn();

    render(
      <ControlBar
        state={initialMockState}
        updateState={updateState}
        stepDeliveryDay={stepDeliveryDay}
      />
    );

    // Select 08:00 UTC cutoff
    fireEvent.click(screen.getByText('08:00 UTC'));
    expect(updateState).toHaveBeenCalledWith({ decisionTime: '08:00' });

    // Change custom time
    const customTimeInput = screen.getByLabelText('Custom decision cutoff time');
    fireEvent.change(customTimeInput, { target: { value: '07:30' } });
    expect(updateState).toHaveBeenCalledWith({ decisionTime: '07:30' });
  });

  it('updates safe wind mode and quantile presets', () => {
    const updateState = vi.fn();
    const stepDeliveryDay = vi.fn();

    render(
      <ControlBar
        state={initialMockState}
        updateState={updateState}
        stepDeliveryDay={stepDeliveryDay}
      />
    );

    // Change safe wind mode to prior_days
    fireEvent.click(screen.getByText('Prior-Days'));
    expect(updateState).toHaveBeenCalledWith({ safeWindMode: 'prior_days' });

    // Change quantile to P95
    fireEvent.click(screen.getByText('P95'));
    expect(updateState).toHaveBeenCalledWith({ quantile: 0.95 });
  });

  it('toggles leaky line visibility and temporal resolution', () => {
    const updateState = vi.fn();
    const stepDeliveryDay = vi.fn();

    render(
      <ControlBar
        state={initialMockState}
        updateState={updateState}
        stepDeliveryDay={stepDeliveryDay}
      />
    );

    // Change resolution to 1h
    fireEvent.click(screen.getByText('1h'));
    expect(updateState).toHaveBeenCalledWith({ resolution: '1h' });

    // Toggle leaky line
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    expect(updateState).toHaveBeenCalledWith({ showLeakyLine: true });
  });

  it('disables prev button on Jan 1 and next button on Jan 31', () => {
    const updateState = vi.fn();
    const stepDeliveryDay = vi.fn();

    // At Jan 1
    const { rerender } = render(
      <ControlBar
        state={{ ...initialMockState, deliveryDate: '2026-01-01' }}
        updateState={updateState}
        stepDeliveryDay={stepDeliveryDay}
      />
    );

    const prevBtn = screen.getByTitle(/Previous delivery day/i) as HTMLButtonElement;
    expect(prevBtn.disabled).toBe(true);

    // At Jan 31
    rerender(
      <ControlBar
        state={{ ...initialMockState, deliveryDate: '2026-01-31' }}
        updateState={updateState}
        stepDeliveryDay={stepDeliveryDay}
      />
    );

    const nextBtn = screen.getByTitle(/Next delivery day/i) as HTMLButtonElement;
    expect(nextBtn.disabled).toBe(true);
  });
});
