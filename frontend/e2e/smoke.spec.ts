import { test, expect } from '@playwright/test';

test.describe('UK Wind Forecast Decision Tool - Main Trading Flow', () => {
  test('open app, change decision cutoff, verify URL sync and chart update', async ({ page }) => {
    // 1. Open the application
    await page.goto('/');

    // Verify Title & Header
    await expect(page).toHaveTitle(/UK Wind Forecast/i);
    await expect(page.getByText(/UK Wind Forecast Monitor/i)).toBeVisible();
    await expect(page.getByText(/Elexon BMRS:/i)).toBeVisible();

    // 2. Verify Initial Decision View & Summary Strip
    await expect(page.getByText(/Auction Decision Snapshot:/i)).toBeVisible();
    await expect(page.getByText(/Settlement Period Ledger/i)).toBeVisible();

    // Check that D-1 09:00 Cutoff is active by default
    const cutoffButton09 = page.getByRole('radio', { name: /09:00 UTC/i });
    await expect(cutoffButton09).toHaveAttribute('aria-checked', 'true');

    // 3. Change Cutoff to 08:00 UTC
    const cutoffButton08 = page.getByRole('radio', { name: /08:00 UTC/i });
    await cutoffButton08.click();

    // Verify Cutoff selection updated
    await expect(cutoffButton08).toHaveAttribute('aria-checked', 'true');

    // Verify URL synced with cutoff parameter
    await expect(page).toHaveURL(/cutoff=08%3A00|cutoff=08:00/);

    // Verify snapshot summary updated with new cutoff time
    await expect(page.getByText(/Cutoff at 08:00 UTC on D-1/i)).toBeVisible();

    // 4. Verify Delivery Day Generation & Risk Envelope Chart is rendered
    await expect(page.getByText(/Delivery Day Generation & Risk Envelope/i)).toBeVisible();

    // 5. Navigate to Accuracy view via Header Navigation Tab
    const accuracyNavTab = page.getByRole('tab', { name: /Accuracy/i });
    await accuracyNavTab.click();

    // Verify Accuracy view loaded and URL synced
    await expect(page).toHaveURL(/view=accuracy/);
    await expect(page.getByText(/Accuracy & Verification Suite/i)).toBeVisible();
    await expect(page.getByText(/Mean Absolute Error \(MAE\)/i)).toBeVisible();

    // 6. Toggle Comparison Baseline to Latest Pre-Delivery
    const compareToggle = page.getByText(/Compare with Latest Pre-Delivery/i);
    await compareToggle.click();
    await expect(page.getByText(/Leakage Delta/i)).toBeVisible();
  });
});
