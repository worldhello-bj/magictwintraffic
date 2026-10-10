/** Road-only aggregates of recorded SUMO samples. Never infer flow on empty roads. */
import type { Network, Vehicle, Point, Manifest } from "./types";
export type HeatMetric = "speed" | "stopped" | "loss";
export type HeatScope = "frame" | "minute" | "total";
// observations, sum speed (m/s), stopped observations (<0.1 m/s), sum lane-limit loss
export type EdgeStats = [number, number, number, number, number];
export interface HeatWindow {
  start: number;
  end: number;
  frames: number;
  edges: Record<string, EdgeStats>;
}
export interface HeatData {
  schema_version: string;
  run_id: string;
  network_hash: string;
  demand_hash: string;
  windows: HeatWindow[];
  total: HeatWindow;
}
export interface HeatSegment {
  edge_id: string;
  shape: Point[];
  width: number;
  elevation: number;
  value: number | null;
  observations: number;
  otherObservations?: number;
  color: string;
  status: "observed" | "missing" | "one-sided";
}
export const heatLabels = {
  speed: "路段均速",
  stopped: "停等车辆",
  loss: "速度损失",
};
export const heatUnits = { speed: "km/h", stopped: "辆", loss: "%" };
export const NO_DATA = "#a6adb1",
  ONE_SIDED = "#937ab7";
export function aggregateFrame(
  network: Network,
  vehicles: Vehicle[],
  time: number,
  recorded: boolean,
): HeatWindow {
  const edges: Record<string, EdgeStats> = {};
  for (const v of vehicles) {
    const lane = network.lanes[v.lane];
    if (
      !lane ||
      lane.id.startsWith(":") ||
      !Number.isFinite(v.speed) ||
      v.speed < 0
    )
      continue;
    const row = (edges[lane.edge_id] ??= [0, 0, 0, 0, 0]);
    row[0]++;
    row[1] += v.speed;
    row[2] += Number(v.speed < 0.1);
    // Proxy against the lane speed limit, NOT vehicle-specific free-flow travel delay.
    if (Number.isFinite(lane.speed) && lane.speed > 0) {
      row[3] += Math.max(0, 1 - v.speed / lane.speed);
      row[4]++;
    }
  }
  return { start: time, end: time, frames: recorded ? 1 : 0, edges };
}
export function heatValue(
  row: EdgeStats | undefined,
  metric: HeatMetric,
  frames: number,
): number | null {
  if (!row || !row[0] || !frames) return null;
  return metric === "speed"
    ? (row[1] / row[0]) * 3.6
    : metric === "stopped"
      ? row[2] / frames
      : row[4]
        ? (row[3] / row[4]) * 100
        : null;
}
const blend = (a: number[], b: number[], t: number) =>
  "#" +
  a
    .map((v, i) =>
      Math.round(v + (b[i] - v) * t)
        .toString(16)
        .padStart(2, "0"),
    )
    .join("");
export function heatColor(
  value: number | null,
  metric: HeatMetric,
  delta = false,
): string {
  if (value === null) return NO_DATA;
  const red = [201, 65, 55],
    teal = [17, 137, 125],
    neutral = [234, 231, 216];
  if (delta) {
    const cap = metric === "speed" ? 20 : metric === "stopped" ? 10 : 50;
    const worse = metric === "speed" ? -value : value;
    return blend(
      neutral,
      worse > 0 ? red : teal,
      Math.min(1, Math.abs(value) / cap),
    );
  }
  const cap = metric === "speed" ? 50 : metric === "stopped" ? 20 : 100;
  const t = Math.max(0, Math.min(1, value / cap));
  const low = metric === "speed" ? red : teal,
    high = metric === "speed" ? teal : red;
  return t < 0.5
    ? blend(low, neutral, t * 2)
    : blend(neutral, high, (t - 0.5) * 2);
}
export function heatSegments(
  network: Network,
  window: HeatWindow | undefined,
  metric: HeatMetric,
  other?: HeatWindow,
  delta = false,
): HeatSegment[] {
  return network.lanes
    .filter((l) => !l.id.startsWith(":"))
    .map((lane) => {
      const row = window?.edges[lane.edge_id],
        b = other?.edges[lane.edge_id];
      const aValue = heatValue(row, metric, window?.frames ?? 0),
        bValue = heatValue(b, metric, other?.frames ?? 0);
      const paired =
        !!window &&
        !!other &&
        window.start === other.start &&
        window.end === other.end &&
        window.frames === other.frames;
      const one = delta && paired && (aValue === null) !== (bValue === null);
      const value = delta
        ? paired && aValue !== null && bValue !== null
          ? bValue - aValue
          : null
        : aValue;
      return {
        edge_id: lane.edge_id,
        shape: lane.shape,
        width: lane.width + 1.3,
        elevation: lane.display_elevation ?? 0,
        value,
        observations: row?.[0] ?? 0,
        otherObservations: delta ? (b?.[0] ?? 0) : undefined,
        status: one ? "one-sided" : value === null ? "missing" : "observed",
        color: one ? ONE_SIDED : heatColor(value, metric, delta),
      };
    });
}
export function validateHeatData(data: HeatData, manifest: Manifest): HeatData {
  if (
    data.schema_version !== "1.0" ||
    data.run_id !== manifest.run_id ||
    data.network_hash !== manifest.network_hash ||
    data.demand_hash !== manifest.demand_hash
  )
    throw new Error("热力图身份与运行不一致");
  for (const w of [...data.windows, data.total]) {
    if (
      !Number.isFinite(w.start) ||
      !Number.isFinite(w.end) ||
      w.end < w.start ||
      !Number.isFinite(w.frames) ||
      w.frames < 0
    )
      throw new Error("热力图时间窗无效");
    for (const r of Object.values(w.edges))
      if (
        r.length !== 5 ||
        r.some((v) => !Number.isFinite(v) || v < 0) ||
        r[2] > r[0] ||
        r[4] > r[0] ||
        r[3] > r[4] + 0.001
      )
        throw new Error("热力图观测值无效");
  }
  return data;
}
export function heatWindow(
  data: HeatData | undefined,
  scope: HeatScope,
  time: number,
): HeatWindow | undefined {
  return scope === "total"
    ? data?.total
    : data?.windows.find((w) => time > w.start && time <= w.end);
}
