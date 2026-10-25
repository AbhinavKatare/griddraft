import { describe, it, expect } from 'vitest';

/**
 * Calculates WCAG 2.1 relative luminance for an sRGB hex colour.
 */
function getLuminance(hex: string): number {
  const cleanHex = hex.replace('#', '');
  const r = parseInt(cleanHex.substring(0, 2), 16) / 255;
  const g = parseInt(cleanHex.substring(2, 4), 16) / 255;
  const b = parseInt(cleanHex.substring(4, 6), 16) / 255;

  const toLinear = (c: number) =>
    c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);

  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

/**
 * Calculates WCAG contrast ratio between two hex colours.
 */
function getContrastRatio(hex1: string, hex2: string): number {
  const lum1 = getLuminance(hex1);
  const lum2 = getLuminance(hex2);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe('Design Tokens WCAG 2.1 AA/AAA Colour Contrast Review', () => {
  // Light Theme Palette
  const lightSurface = '#ffffff';
  const lightBg = '#f8fafc';

  const lightTokens = {
    textPrimary: '#0f172a',
    textSecondary: '#334155',
    textMuted: '#64748b',
    actualTeal: '#0f766e',
    forecastAmber: '#b45309',
    safeWindGreen: '#047857',
    shortfallCrimson: '#be123c',
  };

  // Dark Theme Palette
  const darkSurface = '#111827';
  const darkBg = '#090d16';

  const darkTokens = {
    textPrimary: '#f8fafc',
    textSecondary: '#cbd5e1',
    textMuted: '#8292ab',
    actualTeal: '#14b8a6',
    forecastAmber: '#f59e0b',
    safeWindGreen: '#10b981',
    shortfallCrimson: '#f43f5e',
  };

  describe('Light Theme Contrast Ratios', () => {
    it('primary text satisfies WCAG AAA (>= 7.0:1)', () => {
      const ratio = getContrastRatio(lightTokens.textPrimary, lightSurface);
      expect(ratio).toBeGreaterThanOrEqual(7.0);
    });

    it('secondary text satisfies WCAG AAA (>= 7.0:1)', () => {
      const ratio = getContrastRatio(lightTokens.textSecondary, lightSurface);
      expect(ratio).toBeGreaterThanOrEqual(7.0);
    });

    it('muted text satisfies WCAG AA normal text (>= 4.5:1)', () => {
      const ratio = getContrastRatio(lightTokens.textMuted, lightSurface);
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('domain accents satisfy WCAG AA (>= 4.5:1 on light background)', () => {
      // Actual Teal (#0f766e on #ffffff)
      expect(getContrastRatio(lightTokens.actualTeal, lightSurface)).toBeGreaterThanOrEqual(4.5);

      // Forecast Amber (#b45309 on #ffffff)
      expect(getContrastRatio(lightTokens.forecastAmber, lightSurface)).toBeGreaterThanOrEqual(4.5);

      // Safe Wind Emerald (#047857 on #ffffff)
      expect(getContrastRatio(lightTokens.safeWindGreen, lightSurface)).toBeGreaterThanOrEqual(4.5);

      // Shortfall Crimson (#be123c on #ffffff)
      expect(getContrastRatio(lightTokens.shortfallCrimson, lightSurface)).toBeGreaterThanOrEqual(4.5);
    });
  });

  describe('Dark Theme Contrast Ratios', () => {
    it('primary text on dark surface satisfies WCAG AAA (>= 7.0:1)', () => {
      const ratio = getContrastRatio(darkTokens.textPrimary, darkSurface);
      expect(ratio).toBeGreaterThanOrEqual(7.0);
    });

    it('secondary text on dark surface satisfies WCAG AAA (>= 7.0:1)', () => {
      const ratio = getContrastRatio(darkTokens.textSecondary, darkSurface);
      expect(ratio).toBeGreaterThanOrEqual(7.0);
    });

    it('muted text on dark surface satisfies WCAG AA (>= 4.5:1)', () => {
      const ratio = getContrastRatio(darkTokens.textMuted, darkSurface);
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    });

    it('domain chart strokes satisfy graphical component requirements (>= 3.0:1 on dark surface)', () => {
      expect(getContrastRatio(darkTokens.actualTeal, darkSurface)).toBeGreaterThanOrEqual(3.0);
      expect(getContrastRatio(darkTokens.forecastAmber, darkSurface)).toBeGreaterThanOrEqual(3.0);
      expect(getContrastRatio(darkTokens.safeWindGreen, darkSurface)).toBeGreaterThanOrEqual(3.0);
      expect(getContrastRatio(darkTokens.shortfallCrimson, darkSurface)).toBeGreaterThanOrEqual(3.0);
    });
  });
});
