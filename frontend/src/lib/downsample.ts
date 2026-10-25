/**
 * Largest-Triangle-Three-Buckets (LTTB) Downsampling Algorithm
 *
 * Downsamples numeric or timeseries data to a target point threshold while preserving
 * local visual extrema (peaks and troughs) and area profiles.
 */

export interface Point2D {
  x: number;
  y: number;
  [key: string]: any;
}

/**
 * Downsamples an array of items to `threshold` points using the LTTB algorithm.
 *
 * @param data Array of objects containing x (time/index) and y (value) coordinates.
 * @param threshold Target number of output points (must be >= 3 and < data.length).
 * @param xAccessor Function extracting numeric x coordinate from data item.
 * @param yAccessor Function extracting numeric y coordinate from data item.
 */
export function lttb<T>(
  data: T[],
  threshold: number,
  xAccessor: (item: T) => number,
  yAccessor: (item: T) => number
): T[] {
  const dataLen = data.length;
  if (threshold >= dataLen || threshold <= 2) {
    return data;
  }

  const sampled: T[] = [];
  const bucketSize = (dataLen - 2) / (threshold - 2);

  let a = 0; // Initially the first point in the dataset
  sampled.push(data[a]);

  for (let i = 0; i < threshold - 2; i++) {
    // Calculate point average for next bucket (c)
    let avgX = 0;
    let avgY = 0;
    let avgCount = 0;

    const nextBucketStart = Math.floor((i + 1) * bucketSize) + 1;
    const nextBucketEnd = Math.min(Math.floor((i + 2) * bucketSize) + 1, dataLen);

    for (let j = nextBucketStart; j < nextBucketEnd; j++) {
      avgX += xAccessor(data[j]);
      const yVal = yAccessor(data[j]);
      if (!Number.isNaN(yVal)) {
        avgY += yVal;
        avgCount++;
      }
    }

    if (avgCount > 0) {
      avgX /= avgCount;
      avgY /= avgCount;
    }

    // Get the range for this bucket (b)
    const currentBucketStart = Math.floor(i * bucketSize) + 1;
    const currentBucketEnd = Math.min(Math.floor((i + 1) * bucketSize) + 1, dataLen);

    // Point a
    const pointAX = xAccessor(data[a]);
    const pointAY = yAccessor(data[a]);

    let maxArea = -1;
    let maxAreaIndex = currentBucketStart;

    for (let j = currentBucketStart; j < currentBucketEnd; j++) {
      // Calculate triangle area over points a, b (data[j]), and c (avg point)
      const currentX = xAccessor(data[j]);
      const currentY = yAccessor(data[j]);

      const area =
        Math.abs(
          (pointAX - avgX) * (currentY - pointAY) - (pointAX - currentX) * (avgY - pointAY)
        ) * 0.5;

      if (area > maxArea) {
        maxArea = area;
        maxAreaIndex = j;
      }
    }

    sampled.push(data[maxAreaIndex]);
    a = maxAreaIndex; // Next a is the selected point
  }

  // Always include the last point in the dataset
  sampled.push(data[dataLen - 1]);

  return sampled;
}
