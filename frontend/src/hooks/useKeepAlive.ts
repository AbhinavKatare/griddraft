import { useEffect } from 'react';

/**
 * 14-minute keep-alive heartbeat hook.
 *
 * Sends a lightweight GET /health request immediately on mount and every 14 minutes
 * (840,000 ms) while the browser tab is open to prevent Render free-tier containers
 * from sleeping due to the 15-minute idle cutoff.
 */
export function useKeepAlive(intervalMinutes = 14) {
  useEffect(() => {
    const ping = async () => {
      try {
        const res = await fetch('/health');
        if (!res.ok) {
          // Fallback to /api/v1/meta if /health rewrite isn't active
          await fetch('/api/v1/meta');
        }
      } catch {
        // Silent catch for temporary offline/network drops
      }
    };

    // Ping immediately on initial load to wake or confirm backend status
    ping();

    // Schedule 14-minute recurring heartbeat
    const intervalMs = intervalMinutes * 60 * 1000;
    const intervalId = window.setInterval(ping, intervalMs);

    return () => window.clearInterval(intervalId);
  }, [intervalMinutes]);
}
