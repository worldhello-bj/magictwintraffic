import type { Point } from "./types";

/** CSS-pixel coordinates relative to the actual A/B render pane. */
export function paneCoordinates(
  clientX: number,
  clientY: number,
  rect: Pick<DOMRect, "left" | "top" | "width" | "height">,
  split: boolean,
) {
  const width = rect.width / (split ? 2 : 1);
  const right = split && clientX - rect.left >= width;
  const x = clientX - rect.left - (right ? width : 0);
  const y = clientY - rect.top;
  return {
    right,
    x,
    y,
    width,
    ndcX: (x / width) * 2 - 1,
    ndcY: 1 - (y / rect.height) * 2,
  };
}

export function polygonBounds(points: Point[]) {
  if (!points.length)
    return { center: [0, 0] as Point, width: 1000, height: 1000 };
  const xs = points.map((p) => p[0]),
    ys = points.map((p) => p[1]);
  const minX = Math.min(...xs),
    maxX = Math.max(...xs),
    minY = Math.min(...ys),
    maxY = Math.max(...ys);
  return {
    center: [(minX + maxX) / 2, (minY + maxY) / 2] as Point,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  };
}

/** Odd/even rule for the source study polygon, including arbitrary future boundaries. */
export function insidePolygon(point: Point, polygon: Point[]) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const a = polygon[i],
      b = polygon[j];
    if (
      a[1] > point[1] !== b[1] > point[1] &&
      point[0] < ((b[0] - a[0]) * (point[1] - a[1])) / (b[1] - a[1]) + a[0]
    )
      inside = !inside;
  }
  return inside;
}
