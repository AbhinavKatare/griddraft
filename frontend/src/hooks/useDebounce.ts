import { useEffect, useState } from 'react';

/**
 * Custom hook to debounce any fast-changing value (e.g. search inputs, range sliders).
 *
 * @param value The raw input value
 * @param delay Milliseconds to wait after the last change before updating debounced value
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}
