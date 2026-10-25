import { useEffect, useState } from 'react';

/**
 * Animated counter hook that smoothly interpolates from previous to next numeric value.
 * Instantly updates if user has enabled prefers-reduced-motion.
 */
export function useAnimatedNumber(
  targetValue: number | null | undefined,
  durationMs: number = 400
): number | null {
  const [currentValue, setCurrentValue] = useState<number | null>(targetValue ?? null);

  useEffect(() => {
    if (targetValue === null || targetValue === undefined || Number.isNaN(targetValue)) {
      setCurrentValue(null);
      return;
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion || durationMs <= 0) {
      setCurrentValue(targetValue);
      return;
    }

    const startValue = currentValue ?? 0;
    const diff = targetValue - startValue;
    if (diff === 0) return;

    const startTime = performance.now();
    let animationFrameId: number;

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / durationMs, 1);
      // Ease out cubic
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      setCurrentValue(startValue + diff * easedProgress);

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(tick);
      } else {
        setCurrentValue(targetValue);
      }
    };

    animationFrameId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [targetValue, durationMs]);

  return currentValue;
}
